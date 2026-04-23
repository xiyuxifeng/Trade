"""强势池拉取 skill（NTL-S2-015）。

DataAgent skill，支持返回强势标的快照。
当 DataRequest.fields 包含 "strong_symbols" 时触发。
"""
from __future__ import annotations

from datetime import date
from typing import Any

from src.market_universe.strong_symbols_selector import StrongSymbolsSelector


def supported_fields() -> list[str]:
    """该 skill 支持的字段列表。"""
    return ["strong_symbols"]


def to_payload(
    *,
    dataset: str | None = None,
    snapshot_date: date | None = None,
    slot: str = "17-30",
    provider: Any = None,
) -> dict[str, Any]:
    """从 provider 获取强势标的快照并构建 payload。

    Args:
        dataset: 数据集标识，传入 "strong_symbols" 时触发本 skill
        snapshot_date: 快照日期，若为 None 则使用当前日期
        slot: 时段标识，默认 "17-30"（收盘后）
        provider: KaipanProvider 实例，若为 None 则返回空 payload

    Returns:
        包含 strong_symbols 的 DataAgent payload 片段
    """
    if dataset != "strong_symbols" and "strong_symbols" not in (dataset or ""):
        return {}

    if provider is None:
        return {"strong_symbols": None}

    trade_date = snapshot_date or date.today()

    try:
        raw_payload = provider.fetch_strong_symbols(
            trade_date=trade_date,
            slot=slot,
        )
    except Exception:  # noqa: BLE001
        return {"strong_symbols": None}

    selector = StrongSymbolsSelector()
    strong_symbols_payload = selector.build(raw_payload)

    return {
        "strong_symbols": {
            "trade_date": strong_symbols_payload.trade_date,
            "slot": strong_symbols_payload.slot,
            "symbols": [
                {
                    "kind": s.kind,
                    "symbol": s.symbol,
                    "name": s.name,
                    "strength_score": s.strength_score,
                    "change_pct": s.change_pct,
                    "turnover": s.turnover,
                    "turnover_ratio": s.turnover_ratio,
                    "return_pct": s.return_pct,
                    "net_inflow": s.net_inflow,
                    "main_force_buy": s.main_force_buy,
                    "main_force_sell": s.main_force_sell,
                    "rt_change_pct": s.rt_change_pct,
                    "bid_net": s.bid_net,
                    "bid_turnover": s.bid_turnover,
                    "topic_tags": s.topic_tags,
                }
                for s in strong_symbols_payload.symbols
            ],
            "sources": strong_symbols_payload.sources,
            "fetched_at": strong_symbols_payload.fetched_at.isoformat() if strong_symbols_payload.fetched_at else None,
        }
    }