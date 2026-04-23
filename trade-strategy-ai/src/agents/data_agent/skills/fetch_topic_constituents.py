"""题材成分拉取 skill（NTL-S2-014）。

DataAgent skill，支持返回题材成分快照。
当 DataRequest.fields 包含 "topic_constituents" 时触发。
"""
from __future__ import annotations

from datetime import date
from typing import Any

from src.market_universe.constituents_resolver import ConstituentsResolver


def supported_fields() -> list[str]:
    """该 skill 支持的字段列表。"""
    return ["topic_constituents"]


def to_payload(
    *,
    dataset: str | None = None,
    snapshot_date: date | None = None,
    slot: str = "17-30",
    provider: Any = None,
) -> dict[str, Any]:
    """从 provider 获取题材成分快照并构建 payload。

    Args:
        dataset: 数据集标识，传入 "topic_constituents" 时触发本 skill
        snapshot_date: 快照日期，若为 None 则使用当前日期
        slot: 时段标识，默认 "17-30"（收盘后）
        provider: KaipanProvider 实例，若为 None 则返回空 payload

    Returns:
        包含 topic_constituents 的 DataAgent payload 片段
    """
    if dataset != "topic_constituents" and "topic_constituents" not in (dataset or ""):
        return {}

    if provider is None:
        return {"topic_constituents": None}

    trade_date = snapshot_date or date.today()

    try:
        raw_payload = provider.fetch_topic_constituents(
            trade_date=trade_date,
            slot=slot,
        )
    except Exception:  # noqa: BLE001
        return {"topic_constituents": None}

    resolver = ConstituentsResolver()
    constituents_payload = resolver.build(raw_payload)

    return {
        "topic_constituents": {
            "trade_date": constituents_payload.trade_date,
            "slot": constituents_payload.slot,
            "constituents": [
                {
                    "kind": c.kind,
                    "topic_id": c.topic_id,
                    "topic_name": c.topic_name,
                    "symbol": c.symbol,
                    "name": c.name,
                    "topic_change_pct": c.topic_change_pct,
                    "leader_symbol": c.leader_symbol,
                    "leader_name": c.leader_name,
                    "leader_change_pct": c.leader_change_pct,
                    "board_num": c.board_num,
                    "net_buy": c.net_buy,
                    "brief_intro": c.brief_intro,
                }
                for c in constituents_payload.constituents
            ],
            "sources": constituents_payload.sources,
            "fetched_at": constituents_payload.fetched_at.isoformat() if constituents_payload.fetched_at else None,
        }
    }