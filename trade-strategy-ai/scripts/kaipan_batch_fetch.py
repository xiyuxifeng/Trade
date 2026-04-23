from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Literal

import pandas as pd

from src.common.config import load_app_config
from src.common.utils import append_jsonl, ensure_dir, write_json
from src.providers.kaipan_provider import KaipanAuth, KaipanProvider

LOGGER = logging.getLogger(__name__)

RunMode = Literal["daily", "last"]


@dataclass(slots=True)
class BatchContext:
    """单次批量抓取运行上下文。"""

    trading_dates: list[date]
    current_index: int
    current_date: date
    interval_window_days: int
    theme_id: str
    stock_id: str


@dataclass(slots=True)
class RequestSpec:
    """单次接口请求描述。"""

    name: str
    dataset: str
    api_name: str
    controller: str
    slot: str
    method: str = "GET"
    base_url_key: str | None = None
    page_key: str | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FetchJob:
    """批量抓取任务定义。"""

    name: str
    builder: Callable[[BatchContext, int, int], RequestSpec]
    run_mode: RunMode = "daily"
    paginated: bool = False
    page_size: int = 20
    max_pages: int = 2
    stop_on_short_page: bool = True


def _setup_logging(level: str, log_path: Path) -> None:
    """配置控制台和文件日志。"""

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root.addHandler(console)
    root.addHandler(file_handler)


def _parse_date(value: str | None) -> date:
    """解析日期参数。"""

    if not value:
        return date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()  # noqa: DTZ007


def _parse_int_csv(value: str) -> tuple[int, ...]:
    """解析逗号分隔整数列表。"""

    items = [part.strip() for part in value.split(",")]
    return tuple(int(item) for item in items if item)


def _project_root(config_path: Path) -> Path:
    """推导项目根目录。"""

    resolved = config_path.expanduser().resolve()
    if resolved.parent.name == "config":
        return resolved.parent.parent
    return resolved.parent


def _pick_trade_date_column(df: pd.DataFrame) -> str | None:
    for candidate in ("trade_date", "tradeDate", "日期", "date", "交易日期"):
        if candidate in df.columns:
            return candidate
    return None


def _load_recent_trading_dates_from_akshare(*, end_date: date, count: int) -> list[date] | None:
    """优先使用 AkShare 交易日历。"""

    try:
        import akshare as ak  # type: ignore
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("AkShare 不可用，改用工作日回退逻辑: %s", exc)
        return None

    try:
        df = ak.tool_trade_date_hist_sina()
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("读取 AkShare 交易日历失败，改用工作日回退逻辑: %s", exc)
        return None

    if df is None or df.empty:
        LOGGER.warning("AkShare 交易日历为空，改用工作日回退逻辑")
        return None

    date_col = _pick_trade_date_column(df)
    if date_col is None:
        LOGGER.warning("AkShare 交易日历没有可识别日期列，改用工作日回退逻辑")
        return None

    series = pd.to_datetime(df[date_col], errors="coerce").dropna().dt.date
    dates = sorted({d for d in series if d <= end_date})
    if not dates:
        LOGGER.warning("AkShare 交易日历没有命中 end_date=%s 之前的日期，改用工作日回退逻辑", end_date)
        return None
    return dates[-count:]


def _fallback_recent_weekdays(*, end_date: date, count: int) -> list[date]:
    """退回到周末过滤逻辑。"""

    dates: list[date] = []
    current = end_date
    while len(dates) < count:
        if current.weekday() < 5:
            dates.append(current)
        current -= timedelta(days=1)
    dates.reverse()
    return dates


def get_recent_trading_dates(*, end_date: date, count: int) -> list[date]:
    """获取最近 N 个交易日。"""

    dates = _load_recent_trading_dates_from_akshare(end_date=end_date, count=count)
    if dates is not None:
        return dates
    return _fallback_recent_weekdays(end_date=end_date, count=count)


def _history_or_today_base_url(trade_date: date) -> str:
    """按交易日自动选择历史/今日域名。"""

    return "apphwhq" if trade_date == date.today() else "apphis"


def _infer_item_count(payload: Any) -> int | None:
    """粗略推断分页返回的数据条数。"""

    if isinstance(payload, list):
        return len(payload)
    if not isinstance(payload, dict):
        return None

    for key in ("list", "List", "StockList", "GroupList", "DongXiang", "info"):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
    return None


def _response_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        return sorted(payload.keys())
    if isinstance(payload, list):
        return ["<list>"]
    return [type(payload).__name__]


def _build_board_strength_spec(context: BatchContext, page_index: int, page_size: int) -> RequestSpec:
    index = page_index * page_size
    return RequestSpec(
        name="board_strength",
        dataset="hot_topics",
        api_name="RealRankingInfo",
        controller="ZhiShuRanking",
        slot="09-25",
        method="POST",
        params={
            "Date": context.current_date.strftime("%Y-%m-%d"),
            "Type": "1",
            "Order": "1",
            "ZSType": "7",
            "Index": index,
            "st": page_size,
        },
        page_key=f"page{page_index + 1}_idx{index}",
    )


def _build_industry_ranking_spec(context: BatchContext, page_index: int, page_size: int) -> RequestSpec:
    index = page_index * page_size
    return RequestSpec(
        name="industry_ranking",
        dataset="hot_topics",
        api_name="RealRankingInfo",
        controller="ZhiShuRanking",
        slot="09-25",
        method="POST",
        params={
            "Date": context.current_date.strftime("%Y-%m-%d"),
            "Type": "2",
            "Order": "1",
            "ZSType": "4",
            "Index": index,
            "st": page_size,
        },
        page_key=f"page{page_index + 1}_idx{index}",
    )


def _build_concept_fengkou_spec(context: BatchContext, page_index: int, page_size: int) -> RequestSpec:
    del page_index, page_size
    return RequestSpec(
        name="concept_fengkou",
        dataset="hot_topics",
        api_name="GetFengKYDPlate",
        controller="StockFengKData",
        slot="09-25",
        method="POST",
        base_url_key="apphis",
        params={"Day": context.current_date.strftime("%Y%m%d")},
    )


def _build_theme_detail_spec(context: BatchContext, page_index: int, page_size: int) -> RequestSpec:
    del page_index, page_size
    return RequestSpec(
        name="theme_detail",
        dataset="topic_constituents",
        api_name="InfoGet",
        controller="Theme",
        slot="09-25",
        method="POST",
        base_url_key="applhb",
        params={"ID": context.theme_id},
    )


def _build_stock_sector_v2_spec(context: BatchContext, page_index: int, page_size: int) -> RequestSpec:
    del page_index, page_size
    return RequestSpec(
        name="stock_sector_v2",
        dataset="topic_constituents",
        api_name="GetFeaturedSection",
        controller="StockL2Data",
        slot="09-25",
        method="GET",
        base_url_key="apphwshhq",
        params={"StockID": context.stock_id},
    )


def _build_strong_fengkou_spec(context: BatchContext, page_index: int, page_size: int) -> RequestSpec:
    del page_index, page_size
    return RequestSpec(
        name="strong_fengkou",
        dataset="strong_symbols",
        api_name="GetFengKListBest",
        controller="StockFengKData",
        slot="09-25",
        method="POST",
        params={
            "Day": context.current_date.strftime("%Y%m%d"),
            "Time": "",
        },
    )


def _build_interval_stats_stock_spec(context: BatchContext, page_index: int, page_size: int) -> RequestSpec:
    index = page_index * page_size
    window_start_index = max(0, context.current_index - context.interval_window_days + 1)
    start_date = context.trading_dates[window_start_index]
    return RequestSpec(
        name="interval_stats_stock",
        dataset="strong_symbols",
        api_name="GetInterviewsByDateStock",
        controller="StockLineData",
        slot="09-25",
        method="POST",
        params={
            "DStart": start_date.strftime("%Y-%m-%d"),
            "DEnd": context.current_date.strftime("%Y-%m-%d"),
            "Type": "2",
            "FilterBJS": "1",
            "Order": "1",
            "Index": index,
            "st": page_size,
        },
        page_key=f"page{page_index + 1}_idx{index}",
    )


def _build_morning_bidding_list_spec(pid_type: int) -> Callable[[BatchContext, int, int], RequestSpec]:
    def _builder(context: BatchContext, page_index: int, page_size: int) -> RequestSpec:
        index = page_index * page_size
        return RequestSpec(
            name=f"morning_bidding_list_pid{pid_type}",
            dataset="strong_symbols",
            api_name="MorningBiddingList",
            controller="HisHomeDingPan",
            slot="09-25",
            method="GET",
            base_url_key="apphis",
            params={
                "Date": context.current_date.strftime("%Y-%m-%d"),
                "PidType": pid_type,
                "Type": 4,
                "Index": index,
                "Order": 1,
                "st": page_size,
            },
            page_key=f"pid{pid_type}_page{page_index + 1}_idx{index}",
        )

    return _builder


def _build_limit_up_reason_spec(context: BatchContext, page_index: int, page_size: int) -> RequestSpec:
    index = page_index * page_size
    return RequestSpec(
        name="limit_up_reason",
        dataset="topic_constituents",
        api_name="GetPlateInfo_w38",
        controller="HisLimitResumption",
        slot="09-25",
        method="POST",
        base_url_key="apphis",
        params={
            "Date": context.current_date.strftime("%Y-%m-%d"),
            "Index": index,
            "st": page_size,
        },
        page_key=f"page{page_index + 1}_idx{index}",
    )


def _build_pre_market_bid_spec(context: BatchContext, page_index: int, page_size: int) -> RequestSpec:
    del page_index, page_size
    return RequestSpec(
        name="pre_market_bid",
        dataset="market_context",
        api_name="MorningBidding",
        controller="HisHomeDingPan",
        slot="09-25",
        method="GET",
        base_url_key="apphis",
        params={"Date": context.current_date.strftime("%Y-%m-%d")},
    )


def _build_pre_market_stats_spec(context: BatchContext, page_index: int, page_size: int) -> RequestSpec:
    del page_index, page_size
    return RequestSpec(
        name="pre_market_stats",
        dataset="market_context",
        api_name="MorningBiddingNum",
        controller="HisHomeDingPan",
        slot="09-25",
        method="GET",
        base_url_key="apphis",
        params={"Date": context.current_date.strftime("%Y-%m-%d")},
    )


def _build_limit_up_info_spec(context: BatchContext, page_index: int, page_size: int) -> RequestSpec:
    index = page_index * page_size
    return RequestSpec(
        name="limit_up_info",
        dataset="topic_constituents",
        api_name="GetZhangTingTianTi",
        controller="FuPanLa",
        slot="09-25",
        method="POST",
        params={
            "Date": context.current_date.strftime("%Y-%m-%d"),
            "Index": index,
            "st": page_size,
        },
        page_key=f"page{page_index + 1}_idx{index}",
    )


def _build_lhb_list_spec(context: BatchContext, page_index: int, page_size: int) -> RequestSpec:
    index = page_index * page_size
    return RequestSpec(
        name="lhb_list",
        dataset="topic_constituents",
        api_name="GetStockList",
        controller="LongHuBang",
        slot="17-30",
        method="POST",
        base_url_key="applhb",
        params={
            "Time": context.current_date.strftime("%Y-%m-%d"),
            "Index": index,
            "st": page_size,
        },
        page_key=f"page{page_index + 1}_idx{index}",
    )


def build_jobs(*, include_auxiliary: bool, morning_pid_types: tuple[int, ...], max_pages: int) -> list[FetchJob]:
    """构造默认抓取任务列表。"""

    jobs: list[FetchJob] = [
        FetchJob(name="board_strength", builder=_build_board_strength_spec, paginated=True, max_pages=max_pages),
        FetchJob(name="industry_ranking", builder=_build_industry_ranking_spec, paginated=True, max_pages=max_pages),
        FetchJob(name="concept_fengkou", builder=_build_concept_fengkou_spec, run_mode="daily"),
        FetchJob(name="theme_detail", builder=_build_theme_detail_spec, run_mode="last"),
        FetchJob(name="stock_sector_v2", builder=_build_stock_sector_v2_spec, run_mode="last"),
        FetchJob(name="strong_fengkou", builder=_build_strong_fengkou_spec, run_mode="daily"),
        FetchJob(
            name="interval_stats_stock",
            builder=_build_interval_stats_stock_spec,
            paginated=True,
            max_pages=max_pages,
        ),
    ]

    for pid_type in morning_pid_types:
        jobs.append(
            FetchJob(
                name=f"morning_bidding_list_pid{pid_type}",
                builder=_build_morning_bidding_list_spec(pid_type),
                paginated=True,
                max_pages=max_pages,
                stop_on_short_page=False,
            )
        )

    if include_auxiliary:
        jobs.extend(
            [
                FetchJob(
                    name="limit_up_reason",
                    builder=_build_limit_up_reason_spec,
                    paginated=True,
                    max_pages=max_pages,
                ),
                FetchJob(name="pre_market_bid", builder=_build_pre_market_bid_spec, run_mode="daily"),
                FetchJob(name="pre_market_stats", builder=_build_pre_market_stats_spec, run_mode="daily"),
                FetchJob(
                    name="limit_up_info",
                    builder=_build_limit_up_info_spec,
                    paginated=True,
                    max_pages=max_pages,
                ),
                FetchJob(
                    name="lhb_list",
                    builder=_build_lhb_list_spec,
                    run_mode="last",
                    paginated=True,
                    max_pages=max_pages,
                    page_size=300,
                ),
            ]
        )

    return jobs


def _execute_request(provider: KaipanProvider, context: BatchContext, spec: RequestSpec) -> Any:
    """执行单次请求并落盘。"""

    base_url_key = spec.base_url_key or _history_or_today_base_url(context.current_date)
    LOGGER.info(
        "抓取开始 job=%s date=%s slot=%s base_url=%s api=%s params=%s",
        spec.name,
        context.current_date,
        spec.slot,
        base_url_key,
        spec.api_name,
        json.dumps(spec.params, ensure_ascii=False, default=str),
    )
    return provider.fetch_custom(
        trade_date=context.current_date,
        slot=spec.slot,
        dataset=spec.dataset,
        api_name=spec.api_name,
        controller=spec.controller,
        base_url_key=base_url_key,
        method=spec.method,
        page_key=spec.page_key,
        **spec.params,
    )


def run_batch_fetch(
    *,
    config_path: Path,
    end_date: date,
    days: int,
    output_dir: Path,
    log_level: str,
    theme_id: str,
    stock_id: str,
    interval_window_days: int,
    morning_pid_types: tuple[int, ...],
    max_pages: int,
    include_auxiliary: bool,
    dry_run: bool,
) -> dict[str, Any]:
    """执行批量抓取。"""

    loaded = load_app_config(config_path)
    project_root = _project_root(config_path)
    run_dir = ensure_dir(output_dir / datetime.now().strftime("%Y%m%d-%H%M%S"))
    log_path = run_dir / "run.log"
    records_path = run_dir / "records.jsonl"
    summary_path = run_dir / "summary.json"
    _setup_logging(log_level, log_path)

    config = loaded.config
    kaipan_cfg = config.kaipan
    provider = KaipanProvider(
        auth=KaipanAuth(),
        raw_dir=project_root / kaipan_cfg.data_dir / "raw",
        normalized_dir=project_root / kaipan_cfg.data_dir / "snapshots",
        snapshots_dir=project_root / kaipan_cfg.data_dir / "snapshots",
        kaipan_config=kaipan_cfg,
    )

    trading_dates = get_recent_trading_dates(end_date=end_date, count=days)
    jobs = build_jobs(include_auxiliary=include_auxiliary, morning_pid_types=morning_pid_types, max_pages=max_pages)
    summary: dict[str, Any] = {
        "config_path": str(config_path),
        "output_dir": str(run_dir),
        "end_date": end_date.isoformat(),
        "days": days,
        "trading_dates": [d.isoformat() for d in trading_dates],
        "job_names": [job.name for job in jobs],
        "theme_id": theme_id,
        "stock_id": stock_id,
        "interval_window_days": interval_window_days,
        "morning_pid_types": list(morning_pid_types),
        "max_pages": max_pages,
        "include_auxiliary": include_auxiliary,
        "dry_run": dry_run,
        "success_count": 0,
        "failure_count": 0,
        "request_count": 0,
        "planned_job_count": len(jobs),
    }

    LOGGER.info("项目根目录: %s", project_root)
    LOGGER.info("Kaipan raw_dir: %s", provider.raw_dir)
    LOGGER.info("Kaipan snapshots_dir: %s", provider.snapshots_dir)
    LOGGER.info("交易日数量: %d", len(trading_dates))
    LOGGER.info("抓取任务数量: %d", len(jobs))
    LOGGER.info("运行目录: %s", run_dir)

    if dry_run:
        for job in jobs:
            LOGGER.info(
                "dry-run job=%s mode=%s paginated=%s max_pages=%d page_size=%d",
                job.name,
                job.run_mode,
                job.paginated,
                job.max_pages,
                job.page_size,
            )
        write_json(summary_path, summary)
        LOGGER.info("dry-run 完成，summary=%s", summary_path)
        return summary

    for current_index, current_date in enumerate(trading_dates):
        context = BatchContext(
            trading_dates=trading_dates,
            current_index=current_index,
            current_date=current_date,
            interval_window_days=interval_window_days,
            theme_id=theme_id,
            stock_id=stock_id,
        )
        LOGGER.info("处理交易日 %s (%d/%d)", current_date, current_index + 1, len(trading_dates))

        for job in jobs:
            if job.run_mode == "last" and current_index != len(trading_dates) - 1:
                LOGGER.debug("跳过只执行一次的任务 job=%s date=%s", job.name, current_date)
                continue

            page_index = 0
            while True:
                spec = job.builder(context, page_index, job.page_size)
                request_start = perf_counter()
                try:
                    payload = _execute_request(provider, context, spec)
                    duration = perf_counter() - request_start
                    item_count = _infer_item_count(payload)
                    record = {
                        "trade_date": current_date.isoformat(),
                        "job": job.name,
                        "page_index": page_index,
                        "page_size": job.page_size,
                        "slot": spec.slot,
                        "base_url_key": spec.base_url_key or _history_or_today_base_url(current_date),
                        "api_name": spec.api_name,
                        "controller": spec.controller,
                        "method": spec.method,
                        "status": "ok",
                        "duration_seconds": round(duration, 4),
                        "item_count": item_count,
                        "response_keys": _response_keys(payload),
                        "params": spec.params,
                    }
                    append_jsonl(records_path, record)
                    summary["success_count"] += 1
                    summary["request_count"] += 1
                    LOGGER.info(
                        "抓取成功 job=%s date=%s page=%d count=%s 耗时=%.2fs",
                        job.name,
                        current_date,
                        page_index,
                        item_count,
                        duration,
                    )

                    if not job.paginated:
                        break

                    if job.stop_on_short_page and item_count is not None and item_count < job.page_size:
                        LOGGER.info(
                            "分页结束 job=%s date=%s page=%d count=%s < page_size=%d",
                            job.name,
                            current_date,
                            page_index,
                            item_count,
                            job.page_size,
                        )
                        break

                    page_index += 1
                    if page_index >= job.max_pages:
                        LOGGER.info("达到最大分页数 job=%s date=%s max_pages=%d", job.name, current_date, job.max_pages)
                        break

                except Exception as exc:  # noqa: BLE001
                    duration = perf_counter() - request_start
                    summary["failure_count"] += 1
                    summary["request_count"] += 1
                    LOGGER.exception(
                        "抓取失败 job=%s date=%s page=%d 耗时=%.2fs: %s",
                        job.name,
                        current_date,
                        page_index,
                        duration,
                        exc,
                    )
                    append_jsonl(
                        records_path,
                        {
                            "trade_date": current_date.isoformat(),
                            "job": job.name,
                            "page_index": page_index,
                            "page_size": job.page_size,
                            "slot": spec.slot,
                            "base_url_key": spec.base_url_key or _history_or_today_base_url(current_date),
                            "api_name": spec.api_name,
                            "controller": spec.controller,
                            "method": spec.method,
                            "status": "error",
                            "duration_seconds": round(duration, 4),
                            "error": str(exc),
                            "params": spec.params,
                        },
                    )
                    break

    write_json(summary_path, summary)
    LOGGER.info("批量抓取完成，summary=%s，records=%s", summary_path, records_path)
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="批量抓取最近 N 个交易日的 Kaipan 接口数据")
    parser.add_argument("--config", type=Path, default=Path("config/app.yaml"), help="配置文件路径")
    parser.add_argument("--end-date", type=str, default=None, help="结束日期，默认今天，格式 YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=30, help="回溯交易日数量")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/kaipan/ntl-s0-011"),
        help="运行输出目录",
    )
    parser.add_argument("--log-level", type=str, default="INFO", help="日志级别")
    parser.add_argument("--theme-id", type=str, default="261", help="题材详情示例 ID")
    parser.add_argument("--stock-id", type=str, default="002726", help="股票所属板块 V2 示例股票代码")
    parser.add_argument(
        "--interval-window-days",
        type=int,
        default=20,
        help="区间统计-按股票的回看交易日窗口",
    )
    parser.add_argument(
        "--morning-pid-types",
        type=str,
        default="0",
        help="早盘竞价列表要抓取的 PidType，逗号分隔，例如 0,1,2,3,4",
    )
    parser.add_argument("--max-pages", type=int, default=2, help="分页接口最多抓取页数")
    parser.add_argument(
        "--include-auxiliary",
        action="store_true",
        help="同时抓取涨停原因、竞价总体信息、竞价数量统计、涨停信息、龙虎榜列表",
    )
    parser.add_argument("--dry-run", action="store_true", help="仅生成任务计划，不发起网络请求")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    end_date = _parse_date(args.end_date)
    morning_pid_types = _parse_int_csv(args.morning_pid_types)
    summary = run_batch_fetch(
        config_path=args.config,
        end_date=end_date,
        days=args.days,
        output_dir=args.output_dir,
        log_level=args.log_level,
        theme_id=args.theme_id,
        stock_id=args.stock_id,
        interval_window_days=args.interval_window_days,
        morning_pid_types=morning_pid_types,
        max_pages=args.max_pages,
        include_auxiliary=args.include_auxiliary,
        dry_run=args.dry_run,
    )
    LOGGER.info("最终汇总: %s", json.dumps(summary, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
