"""Kaipan 调度器 CLI。

提供 fetch / normalize / status / run 四个命令。
"""

from __future__ import annotations

import argparse
import sys
import yaml
import logging
from datetime import date
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# 确保项目根目录在 sys.path 中
_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.providers.kaipan_provider import KaipanAuth, KaipanProvider
from src.providers.kaipan_normalizer import KaipanNormalizer


def load_kaipan_config() -> dict:
    """从 config/app.yaml 加载 kaipan 配置。"""
    config_path = _root / "config" / "app.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("kaipan", {})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.providers.kaipan_scheduler",
        description="Kaipan 开盘啦数据抓取与快照调度器",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # fetch 命令
    fetch_parser = sub.add_parser("fetch", help="抓取指定日期和时间槽的数据")
    fetch_parser.add_argument("--date", default=None, help="交易日期 YYYY-MM-DD，默认当天")
    fetch_parser.add_argument("--slot", default="all", help="时间槽：09-25、17-30、all（默认 all）")

    # normalize 命令
    norm_parser = sub.add_parser("normalize", help="转换指定日期和时间槽的 raw → snapshot")
    norm_parser.add_argument("--date", default=None, help="交易日期 YYYY-MM-DD，默认当天")
    norm_parser.add_argument("--slot", default="all", help="时间槽：09-25、17-30、all（默认 all）")

    # status 命令
    sub.add_parser("status", help="查看最近一次抓取状态")

    # run 命令
    run_parser = sub.add_parser("run", help="启动自动调度（APScheduler）")
    return parser


def is_trading_day(trade_date: date) -> bool:
    """通过 akshare 判断是否为 A 股交易日。"""
    try:
        import akshare as ak
        cal = ak.trade_cal(symbol="A股")
        trading_days = cal[cal["is_open"] == 1]["cal_date"].tolist()
        return trade_date.isoformat() in trading_days
    except Exception:
        return False  # 网络异常时跳过，不阻塞调度


def run_fetch(slot: str):
    """由 APScheduler 调用的 fetch 包装函数。"""
    from datetime import date as date_cls

    trade_date = date_cls.today()
    cfg = load_kaipan_config()
    data_root = _root / cfg.get("data_dir", "data/kaipan")
    raw_dir = data_root / "raw"
    snapshots_dir = data_root / "snapshots"
    schema_dir = _root / cfg.get("schema_dir", "src/providers/kaipan_schema")
    auth = KaipanAuth()
    provider = KaipanProvider(
        auth=auth,
        raw_dir=raw_dir,
        normalized_dir=snapshots_dir,
        snapshots_dir=snapshots_dir,
        kaipan_config=cfg,
    )
    normalizer = KaipanNormalizer(
        schema_dir=schema_dir,
        snapshots_dir=snapshots_dir,
    )

    if slot == "09-25":
        datasets = [
            (provider.fetch_board_strength, {}),
            (provider.fetch_industry_ranking, {}),
            (provider.fetch_concept_fengkou, {}),
            (provider.fetch_theme_detail, {}),
            (provider.fetch_stock_sector_v2, {}),
            (provider.fetch_strong_fengkou, {}),
            (provider.fetch_interval_stats_stock, {}),
            (provider.fetch_morning_bidding_list, {}),
            (provider.fetch_limit_up_reason, {}),
            (provider.fetch_pre_market_bid, {}),
            (provider.fetch_pre_market_stats, {}),
            (provider.fetch_limit_up_info, {}),
        ]
    else:
        datasets = [
            (provider.fetch_board_strength, {}),
            (provider.fetch_industry_ranking, {}),
            (provider.fetch_concept_fengkou, {}),
            (provider.fetch_theme_detail, {}),
            (provider.fetch_stock_sector_v2, {}),
            (provider.fetch_strong_fengkou, {}),
            (provider.fetch_interval_stats_stock, {}),
            (provider.fetch_limit_up_reason, {}),
            (provider.fetch_limit_up_info, {}),
            (provider.fetch_lhb_list, {}),
        ]

    for fetch_fn, kwargs in datasets:
        try:
            fetch_fn(trade_date=trade_date, slot=slot, **kwargs)
        except Exception as e:
            logging.warning(f"{fetch_fn.__name__} failed: {e}")

    normalizer.normalize_date(trade_date.isoformat(), slots=(slot,))
    logging.info(f"scheduled fetch + normalize completed for {trade_date} {slot}")


def main():
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:])

    if args.command == "fetch":
        trade_date = date.today() if args.date is None else date.fromisoformat(args.date)
        slot = args.slot
        cfg = load_kaipan_config()
        data_root = _root / cfg.get("data_dir", "data/kaipan")
        raw_dir = data_root / "raw"
        snapshots_dir = data_root / "snapshots"
        schema_dir = _root / cfg.get("schema_dir", "src/providers/kaipan_schema")

        # 解析时间槽对应的接口集合
        if slot == "all":
            slots_to_fetch = ["09-25", "17-30"]
        else:
            slots_to_fetch = [slot]

        # 实例化 provider（使用工作区根目录路径）
        auth = KaipanAuth()
        provider = KaipanProvider(
            auth=auth,
            raw_dir=raw_dir,
            normalized_dir=snapshots_dir,
            snapshots_dir=snapshots_dir,
            kaipan_config=cfg,
        )

        # 9:25 有 12 个接口（含竞价数据，无龙虎榜）
        fetchors_0925 = [
            provider.fetch_board_strength,
            provider.fetch_industry_ranking,
            provider.fetch_concept_fengkou,
            provider.fetch_theme_detail,
            provider.fetch_stock_sector_v2,
            provider.fetch_strong_fengkou,
            provider.fetch_interval_stats_stock,
            provider.fetch_morning_bidding_list,
            provider.fetch_limit_up_reason,
            provider.fetch_pre_market_bid,
            provider.fetch_pre_market_stats,
            provider.fetch_limit_up_info,
        ]
        # 17:30 有 10 个接口（含龙虎榜，无竞价数据）
        fetchors_1730 = [
            provider.fetch_board_strength,
            provider.fetch_industry_ranking,
            provider.fetch_concept_fengkou,
            provider.fetch_theme_detail,
            provider.fetch_stock_sector_v2,
            provider.fetch_strong_fengkou,
            provider.fetch_interval_stats_stock,
            provider.fetch_limit_up_reason,
            provider.fetch_limit_up_info,
            provider.fetch_lhb_list,
        ]

        for s in slots_to_fetch:
            if s == "09-25":
                fetchors = fetchors_0925
            elif s == "17-30":
                fetchors = fetchors_1730
            else:
                print(f"[WARN] 未知时间槽 {s}，跳过")
                continue

            print(f"[fetch] 开始抓取 {trade_date} {s}，共 {len(fetchors)} 个接口")
            for i, fetcher in enumerate(fetchors, 1):
                try:
                    fetcher(trade_date=trade_date, slot=s)
                    print(f"[fetch] [{i}/{len(fetchors)}] {fetcher.__name__} 成功")
                except Exception as e:
                    print(f"[WARN] [{i}/{len(fetchors)}] {fetcher.__name__} 失败: {e}，继续其余接口")

        # 抓取完成后调用 normalize_date 转换
        normalizer = KaipanNormalizer(
            schema_dir=schema_dir,
            snapshots_dir=snapshots_dir,
        )
        slots_tuple = tuple(slots_to_fetch)
        norm_results = normalizer.normalize_date(trade_date.isoformat(), slots_tuple)
        print(f"[fetch] normalize 完成，结果: {norm_results}")
    elif args.command == "normalize":
        trade_date = date.today() if args.date is None else date.fromisoformat(args.date)
        slots = ("09-25", "17-30") if args.slot == "all" else (args.slot,)

        cfg = load_kaipan_config()
        data_root = _root / cfg.get("data_dir", "data/kaipan")
        snapshots_dir = data_root / "snapshots"
        normalizer = KaipanNormalizer(
            schema_dir=_root / cfg.get("schema_dir", "src/providers/kaipan_schema"),
            snapshots_dir=snapshots_dir,
        )

        results = normalizer.normalize_date(trade_date.isoformat(), slots=slots)
        for slot, datasets in results.items():
            ok = sum(1 for v in datasets.values() if v is not None and "_error" not in v)
            err = sum(1 for v in datasets.values() if v is None or "_error" in v)
            print(f"normalize {trade_date} {slot}: {ok} ok, {err} failed")
    elif args.command == "status":
        from pathlib import Path
        import json

        cfg = load_kaipan_config()
        raw_base = _root / cfg.get("data_dir", "data/kaipan") / "raw"
        if not raw_base.exists():
            print("status: no data yet")
            return

        # 查找最近一次抓取
        latest = None
        for p in sorted(raw_base.rglob("*.json"), reverse=True):
            if p.parent.name.startswith("20"):
                latest = p.parent.name
                break

        if latest:
            print(f"status: latest slot {latest}")
        else:
            print("status: no data yet")
    elif args.command == "run":
        import signal

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )

        if not is_trading_day(date.today()):
            print("today is not a trading day, skipping")
            return

        scheduler = BackgroundScheduler()

        cfg = load_kaipan_config()
        pre_market = cfg.get("fetch_schedule", {}).get("pre_market", "9:25")
        post_close = cfg.get("fetch_schedule", {}).get("post_close", "17:30")

        # 解析时间
        pre_hour, pre_min = map(int, pre_market.split(":"))
        post_hour, post_min = map(int, post_close.split(":"))

        scheduler.add_job(
            run_fetch,
            CronTrigger(hour=pre_hour, minute=pre_min, second=0),
            args=["09-25"],
            id="pre_market",
            replace_existing=True,
        )
        scheduler.add_job(
            run_fetch,
            CronTrigger(hour=post_hour, minute=post_min, second=0),
            args=["17-30"],
            id="post_close",
            replace_existing=True,
        )

        scheduler.start()
        print(f"scheduler started (pre_market {pre_market}, post_close {post_close})")

        signal.signal(signal.SIGINT, lambda *_: scheduler.shutdown())
        signal.signal(signal.SIGTERM, lambda *_: scheduler.shutdown())
        scheduler._thread.join()


if __name__ == "__main__":
    main()
