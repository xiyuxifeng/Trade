from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from src.market_data.service import MarketDataCache
from src.market_universe.constituents_resolver import ConstituentsResolver
from src.market_universe.hot_topics_builder import HotTopicsBuilder
from src.market_universe.strong_symbols_selector import StrongSymbolsSelector
from src.models.market_snapshot import MarketSnapshotBuildContext, MarketSnapshotSection
from src.providers.kaipan_provider import KaipanProvider
from src.services.market_service import MarketService
from src.services.market_snapshot_registry import MarketSnapshotRegistry
from src.services.persona_service import PersonaService

_MAJOR_INDEX_SYMBOLS = ("SH000001", "SZ399001", "SZ399006", "SH000688")
_DATA_VERSION = "market-snapshot-v1"


def _now_utc() -> datetime:
    """返回统一的 UTC 时间戳。"""
    return datetime.now(UTC)


def _as_date(value: str | date) -> date:
    """将日期字符串或 date 统一为 date。"""
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _history_or_today_base_url(trade_date: date) -> str:
    """根据交易日判断历史/今日接口域名。"""
    return "apphwhq" if trade_date == date.today() else "apphis"


def _count_records(value: Any) -> int:
    """估算 section 的记录数。"""
    if value is None:
        return 0
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in ("items", "list", "info", "StockList", "topics", "constituents", "symbols"):
            nested = value.get(key)
            if isinstance(nested, list):
                return len(nested)
            if isinstance(nested, dict):
                return len(nested)
        return len(value)
    return 1


def _to_plain(value: Any) -> Any:
    """把 dataclass / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if is_dataclass(value):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _load_json_payload(path: Path) -> dict[str, Any] | None:
    """读取 provider 落盘的 raw JSON wrapper。"""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if isinstance(data, dict):
        payload = data.get("data")
        if isinstance(payload, dict):
            return payload
        if payload is not None:
            return {"value": payload}
    return data if isinstance(data, dict) else None


def _custom_raw_path(
    *,
    provider: KaipanProvider,
    dataset: str,
    trade_date: date,
    slot: str,
    api_name: str,
    **params: Any,
) -> Path:
    """复刻 KaipanProvider 的 raw 文件命名规则。"""
    filename_parts = [dataset, api_name]
    if api_name == "RealRankingInfo":
        filename_parts.append(f"ZSType{params.get('ZSType', '')}")
    elif api_name == "GetInterviewsByDateStock":
        filename_parts.append(f"Type{params.get('Type', '')}")
    elif api_name == "MorningBiddingList":
        filename_parts.append(f"PidType{params.get('PidType', '')}")
    elif api_name == "GetPlateInfo_w38":
        filename_parts.append(f"Index{params.get('Index', '')}")
    elif api_name == "GetZhangTingTianTi":
        filename_parts.append(f"Index{params.get('Index', '')}")
    elif api_name == "GetFengKListBest":
        filename_parts.append(f"Time{params.get('Time', '')}")
    elif api_name == "GetFengKList":
        filename_parts.append(f"Time{params.get('Time', '')}")
    elif api_name == "GetInterviewsByDateZS":
        filename_parts.append(f"Type{params.get('Type', '')}")
    raw_filename = "_".join(filter(None, filename_parts))
    return provider.raw_dir / dataset / f"{trade_date.isoformat()}_{slot}" / f"{raw_filename}.json"


def _build_custom_payload(
    *,
    provider: KaipanProvider,
    offline: bool,
    dataset: str,
    trade_date: date,
    slot: str,
    api_name: str,
    controller: str,
    base_url_key: str = "apphis",
    method: str = "GET",
    **params: Any,
) -> dict[str, Any] | None:
    """按在线抓取或离线 raw 文件回放获取 payload。"""
    clean_params = {key: value for key, value in params.items() if value is not None}
    if offline:
        payload = _load_json_payload(
            _custom_raw_path(
                provider=provider,
                dataset=dataset,
                trade_date=trade_date,
                slot=slot,
                api_name=api_name,
                **clean_params,
            )
        )
        return payload
    return provider.fetch_custom(
        trade_date=trade_date,
        slot=slot,
        dataset=dataset,
        api_name=api_name,
        controller=controller,
        base_url_key=base_url_key,
        method=method,
        **clean_params,
    )


def _build_section(
    *,
    section_id: str,
    provider: str | None,
    payload: dict[str, Any],
    record_count: int,
    quality_status: str,
    missing_reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> MarketSnapshotSection:
    """统一构建 MarketSnapshotSection。"""
    return MarketSnapshotSection(
        section_id=section_id,
        provider=provider,
        source_time=_now_utc(),
        record_count=record_count,
        missing_reason=missing_reason,
        quality_status=quality_status,
        payload=payload,
        metadata=metadata or {},
    )


def _status_from_parts(parts: dict[str, Any], *, expected_keys: tuple[str, ...]) -> tuple[str, str | None]:
    """从各子部分的可用性推导 section 质量状态。"""
    available = [key for key in expected_keys if key in parts and parts[key] is not None]
    if not available:
        return "missing", f"missing sections: {', '.join(expected_keys)}"
    if len(available) == len(expected_keys):
        return "ok", None
    missing = [key for key in expected_keys if key not in available]
    return "partial", f"missing sections: {', '.join(missing)}"


def _section_summary_payload(parts: dict[str, Any]) -> dict[str, Any]:
    """把 section 的原始分片聚合成适合 UI 的 payload。"""
    return {key: value for key, value in parts.items() if value is not None}


def build_overview_section(
    context: MarketSnapshotBuildContext,
    *,
    provider: KaipanProvider,
) -> MarketSnapshotSection:
    """构建市场概览 section。"""
    trade_date = _as_date(context.trade_date)
    base_url_key = _history_or_today_base_url(trade_date)
    parts: dict[str, Any] = {}
    missing_reasons: list[str] = []

    fetch_plan = [
        (
            "sentiment",
            lambda: _build_custom_payload(
                provider=provider,
                offline=context.offline,
                dataset="market_context",
                trade_date=trade_date,
                slot=context.slot,
                api_name="ChangeStatistics",
                controller="HisHomeDingPan",
                base_url_key=base_url_key,
                method="GET",
                Date=trade_date.isoformat(),
                st=1000,
            ),
        ),
        (
            "capacity",
            lambda: _build_custom_payload(
                provider=provider,
                offline=context.offline,
                dataset="market_context",
                trade_date=trade_date,
                slot=context.slot,
                api_name="MarketCapacity",
                controller="HisHomeDingPan",
                base_url_key=base_url_key,
                method="GET",
                Date=trade_date.isoformat(),
                Type=0,
            ),
        ),
        (
            "indices",
            lambda: _build_custom_payload(
                provider=provider,
                offline=context.offline,
                dataset="market_context",
                trade_date=trade_date,
                slot=context.slot,
                api_name="GetZsReal" if base_url_key == "apphis" else "RefreshStockList",
                controller="StockL2History" if base_url_key == "apphis" else "UserSelectStock",
                base_url_key=base_url_key,
                method="POST",
                Day=trade_date.isoformat() if base_url_key == "apphis" else None,
                StockIDList=",".join(_MAJOR_INDEX_SYMBOLS) if base_url_key != "apphis" else None,
            ),
        ),
    ]

    for key, loader in fetch_plan:
        try:
            payload = loader()
        except Exception as exc:  # noqa: BLE001
            missing_reasons.append(f"{key}: {exc}")
            continue
        if payload is None:
            missing_reasons.append(f"{key}: raw data missing")
            continue
        parts[key] = payload

    status, missing_reason = _status_from_parts(parts, expected_keys=("sentiment", "capacity", "indices"))
    if missing_reasons:
        missing_reason = "; ".join(filter(None, [missing_reason, *missing_reasons])) if missing_reason else "; ".join(missing_reasons)

    payload = _section_summary_payload(parts)
    record_count = sum(_count_records(item) for item in payload.values())
    return _build_section(
        section_id="overview",
        provider="kaipan",
        payload=payload,
        record_count=record_count,
        quality_status=status,
        missing_reason=missing_reason,
        metadata={
            "sources": list(payload.keys()),
            "trade_date": trade_date.isoformat(),
            "slot": context.slot,
        },
    )


def build_limit_up_down_section(
    context: MarketSnapshotBuildContext,
    *,
    provider: KaipanProvider,
) -> MarketSnapshotSection:
    """构建涨停 / 跌停 section。"""
    trade_date = _as_date(context.trade_date)
    base_url_key = _history_or_today_base_url(trade_date)
    parts: dict[str, Any] = {}
    missing_reasons: list[str] = []

    fetchers: list[tuple[str, Callable[[], dict[str, Any] | None]]] = [
        (
            "limit_up_counts",
            lambda: _build_custom_payload(
                provider=provider,
                offline=context.offline,
                dataset="limit_up_down",
                trade_date=trade_date,
                slot=context.slot,
                api_name="MarketStockZDNum",
                controller="HisHomeDingPan",
                base_url_key=base_url_key,
                method="POST",
                Date=trade_date.isoformat(),
            ),
        ),
        (
            "limit_up_index",
            lambda: _build_custom_payload(
                provider=provider,
                offline=context.offline,
                dataset="limit_up_down",
                trade_date=trade_date,
                slot=context.slot,
                api_name="DailyLimitIndex",
                controller="HisHomeDingPan" if base_url_key == "apphis" else "HomeDingPan",
                base_url_key=base_url_key,
                method="GET",
                Day=trade_date.isoformat() if base_url_key == "apphis" else None,
            ),
        ),
        (
            "limit_up_expression",
            lambda: _build_custom_payload(
                provider=provider,
                offline=context.offline,
                dataset="limit_up_down",
                trade_date=trade_date,
                slot=context.slot,
                api_name="ZhangTingExpression",
                controller="HisHomeDingPan",
                base_url_key=base_url_key,
                method="GET",
                Day=trade_date.isoformat(),
            ),
        ),
        (
            "limit_up_info",
            lambda: (
                _load_json_payload(_custom_raw_path(provider=provider, dataset="topic_constituents", trade_date=trade_date, slot=context.slot, api_name="GetZhangTingTianTi", Index=0, st=20))
                if context.offline
                else provider.fetch_limit_up_info(trade_date=trade_date, slot=context.slot)
            ),
        ),
        (
            "limit_up_reason",
            lambda: (
                _load_json_payload(_custom_raw_path(provider=provider, dataset="topic_constituents", trade_date=trade_date, slot=context.slot, api_name="GetPlateInfo_w38", Index=0, st=20))
                if context.offline
                else provider.fetch_limit_up_reason(trade_date=trade_date, slot=context.slot)
            ),
        ),
        (
            "break_board",
            lambda: _build_custom_payload(
                provider=provider,
                offline=context.offline,
                dataset="limit_up_down",
                trade_date=trade_date,
                slot=context.slot,
                api_name="DailyLimitPerformance2",
                controller="HisHomeDingPan",
                base_url_key=base_url_key,
                method="GET",
                Day=trade_date.isoformat() if base_url_key == "apphis" else None,
                PidType=1,
                Type=5,
                Index=0,
                Order=1,
                st=1000,
            ),
        ),
        (
            "highlight",
            lambda: _build_custom_payload(
                provider=provider,
                offline=context.offline,
                dataset="limit_up_down",
                trade_date=trade_date,
                slot=context.slot,
                api_name="GetPMSL_PMLD",
                controller="FuPanLa",
                base_url_key=base_url_key,
                method="GET",
                Date=trade_date.isoformat(),
                Index=0,
                st=20,
            ),
        ),
        (
            "lhb_list",
            lambda: (
                _load_json_payload(_custom_raw_path(provider=provider, dataset="topic_constituents", trade_date=trade_date, slot=context.slot, api_name="GetStockList", Index=0, st=300))
                if context.offline
                else provider.fetch_lhb_list(trade_date=trade_date, slot=context.slot)
            ),
        ),
    ]

    for key, loader in fetchers:
        try:
            payload = loader()
        except Exception as exc:  # noqa: BLE001
            missing_reasons.append(f"{key}: {exc}")
            continue
        if payload is None:
            missing_reasons.append(f"{key}: raw data missing")
            continue
        parts[key] = payload

    status, missing_reason = _status_from_parts(
        parts,
        expected_keys=("limit_up_counts", "limit_up_index", "limit_up_expression", "limit_up_info", "limit_up_reason", "break_board", "highlight"),
    )
    if missing_reasons:
        missing_reason = "; ".join(filter(None, [missing_reason, *missing_reasons])) if missing_reason else "; ".join(missing_reasons)

    payload = _section_summary_payload(parts)
    record_count = sum(_count_records(item) for item in payload.values())
    return _build_section(
        section_id="limit_up_down",
        provider="kaipan",
        payload=payload,
        record_count=record_count,
        quality_status=status,
        missing_reason=missing_reason,
        metadata={
            "sources": list(payload.keys()),
            "trade_date": trade_date.isoformat(),
            "slot": context.slot,
        },
    )


def build_sector_activity_section(
    context: MarketSnapshotBuildContext,
    *,
    provider: KaipanProvider,
) -> MarketSnapshotSection:
    """构建板块 / 行业 / 地区 / 权重活动 section。"""
    trade_date = _as_date(context.trade_date)
    base_url_key = _history_or_today_base_url(trade_date)
    parts: dict[str, Any] = {}
    missing_reasons: list[str] = []

    fetchers: list[tuple[str, Callable[[], dict[str, Any] | None]]] = [
        (
            "board_strength",
            lambda: (
                _load_json_payload(_custom_raw_path(provider=provider, dataset="hot_topics", trade_date=trade_date, slot=context.slot, api_name="RealRankingInfo", ZSType=7))
                if context.offline
                else provider.fetch_board_strength(trade_date=trade_date, slot=context.slot, use_today_url=base_url_key == "apphwhq")
            ),
        ),
        (
            "industry_ranking",
            lambda: (
                _load_json_payload(_custom_raw_path(provider=provider, dataset="hot_topics", trade_date=trade_date, slot=context.slot, api_name="RealRankingInfo", ZSType=4))
                if context.offline
                else provider.fetch_industry_ranking(trade_date=trade_date, slot=context.slot, use_today_url=base_url_key == "apphwhq")
            ),
        ),
        (
            "region_ranking",
            lambda: _build_custom_payload(
                provider=provider,
                offline=context.offline,
                dataset="hot_topics",
                trade_date=trade_date,
                slot=context.slot,
                api_name="RealRankingInfo",
                controller="ZhiShuRanking",
                base_url_key=base_url_key,
                method="POST",
                Date=trade_date.isoformat(),
                Type=2,
                Order=1,
                ZSType=6,
                Index=0,
                st=20,
            ),
        ),
        (
            "weight_performance",
            lambda: _build_custom_payload(
                provider=provider,
                offline=context.offline,
                dataset="sector_activity",
                trade_date=trade_date,
                slot=context.slot,
                api_name="WeightPerformance",
                controller="HisHomeDingPan",
                base_url_key=base_url_key,
                method="GET",
                Day=trade_date.isoformat(),
            ),
        ),
        (
            "block_bid",
            lambda: _build_custom_payload(
                provider=provider,
                offline=context.offline,
                dataset="sector_activity",
                trade_date=trade_date,
                slot=context.slot,
                api_name="GetBKJJ_W36",
                controller="StockBidYiDong",
                base_url_key=base_url_key,
                method="POST",
                Day=trade_date.strftime("%Y%m%d"),
                Order=1,
                Type=0,
            ),
        ),
        (
            "block_bid_stocks",
            lambda: _build_custom_payload(
                provider=provider,
                offline=context.offline,
                dataset="sector_activity",
                trade_date=trade_date,
                slot=context.slot,
                api_name="GetBKJJBL",
                controller="StockBidYiDong",
                base_url_key=base_url_key,
                method="POST",
                Day=trade_date.strftime("%Y%m%d"),
                StockID="801660",
                Index=0,
                Order=1,
                Type=1,
                IsLB=0,
                IsZT=0,
                Isst=1,
                filter=3,
                st=20,
            ),
        ),
    ]

    for key, loader in fetchers:
        try:
            payload = loader()
        except Exception as exc:  # noqa: BLE001
            missing_reasons.append(f"{key}: {exc}")
            continue
        if payload is None:
            missing_reasons.append(f"{key}: raw data missing")
            continue
        parts[key] = payload

    status, missing_reason = _status_from_parts(
        parts,
        expected_keys=("board_strength", "industry_ranking", "region_ranking", "weight_performance", "block_bid", "block_bid_stocks"),
    )
    if missing_reasons:
        missing_reason = "; ".join(filter(None, [missing_reason, *missing_reasons])) if missing_reason else "; ".join(missing_reasons)

    payload = _section_summary_payload(parts)
    record_count = sum(_count_records(item) for item in payload.values())
    return _build_section(
        section_id="sector_activity",
        provider="kaipan",
        payload=payload,
        record_count=record_count,
        quality_status=status,
        missing_reason=missing_reason,
        metadata={
            "sources": list(payload.keys()),
            "trade_date": trade_date.isoformat(),
            "slot": context.slot,
        },
    )


def build_auction_section(
    context: MarketSnapshotBuildContext,
    *,
    provider: KaipanProvider,
) -> MarketSnapshotSection:
    """构建竞价 section。"""
    trade_date = _as_date(context.trade_date)
    base_url_key = _history_or_today_base_url(trade_date)
    parts: dict[str, Any] = {}
    missing_reasons: list[str] = []

    fetchers: list[tuple[str, Callable[[], dict[str, Any] | None]]] = [
        (
            "pre_market_bid",
            lambda: (
                _load_json_payload(_custom_raw_path(provider=provider, dataset="market_context", trade_date=trade_date, slot=context.slot, api_name="MorningBidding", Date=trade_date.isoformat()))
                if context.offline
                else provider.fetch_pre_market_bid(trade_date=trade_date, slot=context.slot)
            ),
        ),
        (
            "pre_market_stats",
            lambda: (
                _load_json_payload(_custom_raw_path(provider=provider, dataset="market_context", trade_date=trade_date, slot=context.slot, api_name="MorningBiddingNum", Date=trade_date.isoformat()))
                if context.offline
                else provider.fetch_pre_market_stats(trade_date=trade_date, slot=context.slot)
            ),
        ),
        (
            "bidding_list",
            lambda: _build_custom_payload(
                provider=provider,
                offline=context.offline,
                dataset="strong_symbols",
                trade_date=trade_date,
                slot=context.slot,
                api_name="MorningBiddingList",
                controller="HisHomeDingPan",
                base_url_key="apphis",
                method="GET",
                Date=trade_date.isoformat(),
                PidType=0,
                Type=4,
                Index=0,
                Order=1,
                st=20,
            ),
        ),
        (
            "tail_auction",
            lambda: _build_custom_payload(
                provider=provider,
                offline=context.offline,
                dataset="auction",
                trade_date=trade_date,
                slot=context.slot,
                api_name="GetWPQC",
                controller="StockBidYiDong",
                base_url_key=base_url_key,
                method="GET",
                Day=trade_date.strftime("%Y%m%d"),
                Type=1,
                Index=0,
                Order=1,
                st=20,
            ),
        ),
    ]

    for key, loader in fetchers:
        try:
            payload = loader()
        except Exception as exc:  # noqa: BLE001
            missing_reasons.append(f"{key}: {exc}")
            continue
        if payload is None:
            missing_reasons.append(f"{key}: raw data missing")
            continue
        parts[key] = payload

    status, missing_reason = _status_from_parts(parts, expected_keys=("pre_market_bid", "pre_market_stats", "bidding_list", "tail_auction"))
    if missing_reasons:
        missing_reason = "; ".join(filter(None, [missing_reason, *missing_reasons])) if missing_reason else "; ".join(missing_reasons)

    payload = _section_summary_payload(parts)
    record_count = sum(_count_records(item) for item in payload.values())
    return _build_section(
        section_id="auction",
        provider="kaipan",
        payload=payload,
        record_count=record_count,
        quality_status=status,
        missing_reason=missing_reason,
        metadata={
            "sources": list(payload.keys()),
            "trade_date": trade_date.isoformat(),
            "slot": context.slot,
        },
    )


def build_ohlcv_section(
    context: MarketSnapshotBuildContext,
    *,
    market_service: MarketService,
    base_dir: Path,
    benchmark_symbol: str,
) -> MarketSnapshotSection:
    """构建 OHLCV section。"""
    trade_date = _as_date(context.trade_date)
    symbol = benchmark_symbol
    end_date = trade_date
    start_date = trade_date - timedelta(days=19)
    missing_reasons: list[str] = []
    payload: dict[str, Any] = {}

    try:
        result = __query_ohlcv(market_service, symbol, start_date, end_date)
    except Exception as exc:  # noqa: BLE001
        missing_reasons.append(f"database query: {exc}")
        result = None

    if result is None or result.get("count", 0) == 0:
        cache_dir = base_dir / "data/processed/market_data"
        cache = MarketDataCache(cache_dir)
        cached_path = cache.path_for_symbol(symbol)
        if cached_path.exists():
            try:
                df = cache.load_daily_frame(symbol)
                recent = df.tail(20).to_dict(orient="records")
                payload = {
                    "symbol": symbol,
                    "source": "cache",
                    "start_date": str(df["date"].iloc[0].date()) if not df.empty else start_date.isoformat(),
                    "end_date": str(df["date"].iloc[-1].date()) if not df.empty else end_date.isoformat(),
                    "count": len(recent),
                    "items": recent,
                    "cache_path": str(cached_path),
                }
            except Exception as exc:  # noqa: BLE001
                missing_reasons.append(f"cache fallback: {exc}")
        else:
            missing_reasons.append(f"cache missing: {cached_path}")
    else:
        payload = dict(result)
        payload["source"] = "database"

    status = "ok" if payload else "missing"
    if payload and missing_reasons:
        status = "partial"
    missing_reason = "; ".join(missing_reasons) if missing_reasons else None
    record_count = int(payload.get("count", 0)) if payload else 0
    return _build_section(
        section_id="ohlcv",
        provider="market",
        payload=payload,
        record_count=record_count,
        quality_status=status,
        missing_reason=missing_reason,
        metadata={
            "symbol": symbol,
            "trade_date": trade_date.isoformat(),
            "range_start": start_date.isoformat(),
            "range_end": end_date.isoformat(),
        },
    )


def __query_ohlcv(market_service: MarketService, symbol: str, start_date: date, end_date: date) -> dict[str, Any] | None:
    """执行 OHLCV 查询并返回 payload。"""
    import asyncio

    result = asyncio.run(market_service.get_ohlcv(symbol, start_date, end_date))
    if result.status == "error":
        return None
    payload = result.payload if isinstance(result.payload, dict) else {}
    return payload if isinstance(payload, dict) else None


def build_hot_topics_section(
    context: MarketSnapshotBuildContext,
    *,
    provider: KaipanProvider,
) -> MarketSnapshotSection:
    """构建热点主题 section。"""
    trade_date = _as_date(context.trade_date)
    try:
        payload = provider.fetch_hot_topics(trade_date=trade_date, slot=context.slot, offline=context.offline)
        payload = _to_plain(HotTopicsBuilder().build(payload))
        record_count = len(payload.get("topics", []))
        return _build_section(
            section_id="hot_topics",
            provider="kaipan",
            payload=payload,
            record_count=record_count,
            quality_status="ok" if record_count else "partial",
            missing_reason=None if record_count else "no hot topics returned",
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot, "sources": payload.get("sources", [])},
        )
    except Exception as exc:  # noqa: BLE001
        return _build_section(
            section_id="hot_topics",
            provider="kaipan",
            payload={},
            record_count=0,
            quality_status="missing",
            missing_reason=str(exc),
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot},
        )


def build_topic_constituents_section(
    context: MarketSnapshotBuildContext,
    *,
    provider: KaipanProvider,
) -> MarketSnapshotSection:
    """构建题材成分 section。"""
    trade_date = _as_date(context.trade_date)
    try:
        payload = provider.fetch_topic_constituents(trade_date=trade_date, slot=context.slot, offline=context.offline)
        payload = _to_plain(ConstituentsResolver().build(payload))
        record_count = len(payload.get("constituents", []))
        return _build_section(
            section_id="topic_constituents",
            provider="kaipan",
            payload=payload,
            record_count=record_count,
            quality_status="ok" if record_count else "partial",
            missing_reason=None if record_count else "no constituents returned",
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot, "sources": payload.get("sources", [])},
        )
    except Exception as exc:  # noqa: BLE001
        return _build_section(
            section_id="topic_constituents",
            provider="kaipan",
            payload={},
            record_count=0,
            quality_status="missing",
            missing_reason=str(exc),
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot},
        )


def build_strong_symbols_section(
    context: MarketSnapshotBuildContext,
    *,
    provider: KaipanProvider,
) -> MarketSnapshotSection:
    """构建强势标的 section。"""
    trade_date = _as_date(context.trade_date)
    try:
        payload = provider.fetch_strong_symbols(trade_date=trade_date, slot=context.slot, offline=context.offline)
        payload = _to_plain(StrongSymbolsSelector().build(payload))
        record_count = len(payload.get("symbols", []))
        return _build_section(
            section_id="strong_symbols",
            provider="kaipan",
            payload=payload,
            record_count=record_count,
            quality_status="ok" if record_count else "partial",
            missing_reason=None if record_count else "no strong symbols returned",
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot, "sources": payload.get("sources", [])},
        )
    except Exception as exc:  # noqa: BLE001
        return _build_section(
            section_id="strong_symbols",
            provider="kaipan",
            payload={},
            record_count=0,
            quality_status="missing",
            missing_reason=str(exc),
        metadata={"trade_date": trade_date.isoformat(), "slot": context.slot},
    )


def build_market_stock_zd_num_section(
    context: MarketSnapshotBuildContext,
    *,
    provider: KaipanProvider,
) -> MarketSnapshotSection:
    """构建涨跌停统计 section。"""
    trade_date = _as_date(context.trade_date)
    try:
        payload = _to_plain(provider.fetch_market_stock_zd_num(trade_date=trade_date, slot=context.slot, offline=context.offline))
        record_count = 1 if payload else 0
        return _build_section(
            section_id="market_stock_zd_num",
            provider="kaipan",
            payload=payload,
            record_count=record_count,
            quality_status="ok" if record_count else "missing",
            missing_reason=None if record_count else "no market stock zd num returned",
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot},
        )
    except Exception as exc:  # noqa: BLE001
        return _build_section(
            section_id="market_stock_zd_num",
            provider="kaipan",
            payload={},
            record_count=0,
            quality_status="missing",
            missing_reason=str(exc),
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot},
        )


def build_zhang_ting_expression_section(
    context: MarketSnapshotBuildContext,
    *,
    provider: KaipanProvider,
) -> MarketSnapshotSection:
    """构建涨停表达式 section。"""
    trade_date = _as_date(context.trade_date)
    try:
        payload = _to_plain(provider.fetch_zhang_ting_expression(trade_date=trade_date, slot=context.slot, offline=context.offline))
        record_count = len(payload.get("items", [])) if isinstance(payload, dict) else 0
        return _build_section(
            section_id="zhang_ting_expression",
            provider="kaipan",
            payload=payload,
            record_count=record_count or (1 if payload else 0),
            quality_status="ok" if payload else "missing",
            missing_reason=None if payload else "no zhang ting expression returned",
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot},
        )
    except Exception as exc:  # noqa: BLE001
        return _build_section(
            section_id="zhang_ting_expression",
            provider="kaipan",
            payload={},
            record_count=0,
            quality_status="missing",
            missing_reason=str(exc),
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot},
        )


def build_daily_limit_index_section(
    context: MarketSnapshotBuildContext,
    *,
    provider: KaipanProvider,
) -> MarketSnapshotSection:
    """构建连板结构 section。"""
    trade_date = _as_date(context.trade_date)
    try:
        payload = _to_plain(provider.fetch_daily_limit_index(trade_date=trade_date, slot=context.slot, offline=context.offline))
        record_count = len(payload.get("items", [])) if isinstance(payload, dict) else 0
        return _build_section(
            section_id="daily_limit_index",
            provider="kaipan",
            payload=payload,
            record_count=record_count or (1 if payload else 0),
            quality_status="ok" if payload else "missing",
            missing_reason=None if payload else "no daily limit index returned",
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot},
        )
    except Exception as exc:  # noqa: BLE001
        return _build_section(
            section_id="daily_limit_index",
            provider="kaipan",
            payload={},
            record_count=0,
            quality_status="missing",
            missing_reason=str(exc),
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot},
        )


def build_weight_performance_section(
    context: MarketSnapshotBuildContext,
    *,
    provider: KaipanProvider,
) -> MarketSnapshotSection:
    """构建权重板块表现 section。"""
    trade_date = _as_date(context.trade_date)
    try:
        payload = _to_plain(provider.fetch_weight_performance(trade_date=trade_date, slot=context.slot, offline=context.offline))
        record_count = len(payload.get("items", [])) if isinstance(payload, dict) else 0
        return _build_section(
            section_id="weight_performance",
            provider="kaipan",
            payload=payload,
            record_count=record_count,
            quality_status="ok" if record_count else "partial",
            missing_reason=None if record_count else "no weight performance returned",
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot},
        )
    except Exception as exc:  # noqa: BLE001
        return _build_section(
            section_id="weight_performance",
            provider="kaipan",
            payload={},
            record_count=0,
            quality_status="missing",
            missing_reason=str(exc),
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot},
        )


def build_get_feng_k_list_section(
    context: MarketSnapshotBuildContext,
    *,
    provider: KaipanProvider,
) -> MarketSnapshotSection:
    """构建收盘强势标的 section。"""
    trade_date = _as_date(context.trade_date)
    try:
        payload = _to_plain(provider.fetch_get_feng_k_list(trade_date=trade_date, slot=context.slot, offline=context.offline))
        record_count = len(payload.get("items", [])) if isinstance(payload, dict) else 0
        return _build_section(
            section_id="get_feng_k_list",
            provider="kaipan",
            payload=payload,
            record_count=record_count,
            quality_status="ok" if record_count else "partial",
            missing_reason=None if record_count else "no get feng k list returned",
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot},
        )
    except Exception as exc:  # noqa: BLE001
        return _build_section(
            section_id="get_feng_k_list",
            provider="kaipan",
            payload={},
            record_count=0,
            quality_status="missing",
            missing_reason=str(exc),
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot},
        )


def build_market_state_section(
    context: MarketSnapshotBuildContext,
    *,
    persona_service: PersonaService,
    config_path: str | Path,
    output_dir: Path,
    benchmark_symbol: str,
) -> MarketSnapshotSection:
    """构建 MarketState section。"""
    trade_date = _as_date(context.trade_date)
    dest = output_dir / "market_state.json"
    try:
        result = persona_service.build_market_state(
            config_path=config_path,
            benchmark_symbol=benchmark_symbol,
            as_of=trade_date,
            dest=dest,
            from_akshare=False,
            cache_csv=True,
        )
    except Exception as exc:  # noqa: BLE001
        return _build_section(
            section_id="market_state",
            provider="persona",
            payload={},
            record_count=0,
            quality_status="missing",
            missing_reason=str(exc),
            metadata={"trade_date": trade_date.isoformat(), "slot": context.slot, "dest": str(dest)},
        )

    payload = result.payload if isinstance(result.payload, dict) else {}
    state = payload.get("market_state") if isinstance(payload, dict) else None
    record_count = 1 if state else 0
    quality_status = "ok" if state else "missing"
    missing_reason = None if state else result.message
    return _build_section(
        section_id="market_state",
        provider="persona",
        payload=_section_summary_payload({"market_state": state, "source": payload.get("source"), "market_state_path": payload.get("market_state_path")}),
        record_count=record_count,
        quality_status=quality_status,
        missing_reason=missing_reason,
        metadata={"trade_date": trade_date.isoformat(), "slot": context.slot, "source": payload.get("source")},
    )


@dataclass(frozen=True)
class OverviewSectionBuilder:
    """市场概览 section builder。"""

    provider: KaipanProvider
    section_id: str = "overview"

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection:
        return build_overview_section(context, provider=self.provider)


@dataclass(frozen=True)
class LimitUpDownSectionBuilder:
    """涨停 / 跌停 section builder。"""

    provider: KaipanProvider
    section_id: str = "limit_up_down"

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection:
        return build_limit_up_down_section(context, provider=self.provider)


@dataclass(frozen=True)
class SectorActivitySectionBuilder:
    """板块活动 section builder。"""

    provider: KaipanProvider
    section_id: str = "sector_activity"

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection:
        return build_sector_activity_section(context, provider=self.provider)


@dataclass(frozen=True)
class AuctionSectionBuilder:
    """竞价 section builder。"""

    provider: KaipanProvider
    section_id: str = "auction"

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection:
        return build_auction_section(context, provider=self.provider)


@dataclass(frozen=True)
class OhlcvSectionBuilder:
    """OHLCV section builder。"""

    market_service: MarketService
    base_dir: Path
    benchmark_symbol: str
    section_id: str = "ohlcv"

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection:
        return build_ohlcv_section(
            context,
            market_service=self.market_service,
            base_dir=self.base_dir,
            benchmark_symbol=self.benchmark_symbol,
        )


@dataclass(frozen=True)
class HotTopicsSectionBuilder:
    """热点主题 section builder。"""

    provider: KaipanProvider
    section_id: str = "hot_topics"

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection:
        return build_hot_topics_section(context, provider=self.provider)


@dataclass(frozen=True)
class TopicConstituentsSectionBuilder:
    """题材成分 section builder。"""

    provider: KaipanProvider
    section_id: str = "topic_constituents"

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection:
        return build_topic_constituents_section(context, provider=self.provider)


@dataclass(frozen=True)
class StrongSymbolsSectionBuilder:
    """强势标的 section builder。"""

    provider: KaipanProvider
    section_id: str = "strong_symbols"

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection:
        return build_strong_symbols_section(context, provider=self.provider)


@dataclass(frozen=True)
class MarketStockZDNumSectionBuilder:
    """涨跌停统计 section builder。"""

    provider: KaipanProvider
    section_id: str = "market_stock_zd_num"

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection:
        return build_market_stock_zd_num_section(context, provider=self.provider)


@dataclass(frozen=True)
class ZhangTingExpressionSectionBuilder:
    """涨停表达式 section builder。"""

    provider: KaipanProvider
    section_id: str = "zhang_ting_expression"

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection:
        return build_zhang_ting_expression_section(context, provider=self.provider)


@dataclass(frozen=True)
class DailyLimitIndexSectionBuilder:
    """连板结构 section builder。"""

    provider: KaipanProvider
    section_id: str = "daily_limit_index"

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection:
        return build_daily_limit_index_section(context, provider=self.provider)


@dataclass(frozen=True)
class WeightPerformanceSectionBuilder:
    """权重板块表现 section builder。"""

    provider: KaipanProvider
    section_id: str = "weight_performance"

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection:
        return build_weight_performance_section(context, provider=self.provider)


@dataclass(frozen=True)
class GetFengKListSectionBuilder:
    """收盘强势标的 section builder。"""

    provider: KaipanProvider
    section_id: str = "get_feng_k_list"

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection:
        return build_get_feng_k_list_section(context, provider=self.provider)


@dataclass(frozen=True)
class MarketStateSectionBuilder:
    """MarketState section builder。"""

    persona_service: PersonaService
    config_path: str | Path
    output_dir: Path
    benchmark_symbol: str
    section_id: str = "market_state"

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection:
        return build_market_state_section(
            context,
            persona_service=self.persona_service,
            config_path=self.config_path,
            output_dir=self.output_dir,
            benchmark_symbol=self.benchmark_symbol,
        )


def build_default_market_snapshot_registry(
    *,
    provider: KaipanProvider,
    market_service: MarketService,
    persona_service: PersonaService,
    base_dir: Path,
    benchmark_symbol: str,
    config_path: str | Path,
) -> MarketSnapshotRegistry:
    """创建默认的 MarketSnapshotRegistry。"""
    registry = MarketSnapshotRegistry()
    registry.register(OverviewSectionBuilder(provider=provider))
    registry.register(LimitUpDownSectionBuilder(provider=provider))
    registry.register(SectorActivitySectionBuilder(provider=provider))
    registry.register(AuctionSectionBuilder(provider=provider))
    registry.register(OhlcvSectionBuilder(market_service=market_service, base_dir=base_dir, benchmark_symbol=benchmark_symbol))
    registry.register(HotTopicsSectionBuilder(provider=provider))
    registry.register(TopicConstituentsSectionBuilder(provider=provider))
    registry.register(StrongSymbolsSectionBuilder(provider=provider))
    registry.register(MarketStockZDNumSectionBuilder(provider=provider))
    registry.register(ZhangTingExpressionSectionBuilder(provider=provider))
    registry.register(DailyLimitIndexSectionBuilder(provider=provider))
    registry.register(WeightPerformanceSectionBuilder(provider=provider))
    registry.register(GetFengKListSectionBuilder(provider=provider))
    registry.register(
        MarketStateSectionBuilder(
            persona_service=persona_service,
            config_path=config_path,
            output_dir=base_dir / "data/processed/market_snapshot",
            benchmark_symbol=benchmark_symbol,
        )
    )
    return registry
