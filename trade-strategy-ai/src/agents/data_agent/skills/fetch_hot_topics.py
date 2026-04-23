"""热点拉取 skill（NTL-S2-013）。

DataAgent skill，支持返回热点主题快照。
当 DataRequest.fields 包含 "hot_topics" 时触发。
"""
from __future__ import annotations

from datetime import date
from typing import Any

from src.market_universe.hot_topics_builder import HotTopicsBuilder


def supported_fields() -> list[str]:
    """该 skill 支持的字段列表。"""
    return ["hot_topics"]


def to_payload(
    *,
    dataset: str | None = None,
    snapshot_date: date | None = None,
    slot: str = "17-30",
    provider: Any = None,
) -> dict[str, Any]:
    """从 provider 获取热点快照并构建 payload。

    Args:
        dataset: 数据集标识，传入 "hot_topics" 时触发本 skill
        snapshot_date: 快照日期，若为 None 则使用当前日期
        slot: 时段标识，默认 "17-30"（收盘后）
        provider: KaipanProvider 实例，若为 None 则返回空 payload

    Returns:
        包含 hot_topics 的 DataAgent payload 片段
    """
    if dataset != "hot_topics" and "hot_topics" not in (dataset or ""):
        return {}

    if provider is None:
        return {"hot_topics": None}

    trade_date = snapshot_date or date.today()

    try:
        raw_payload = provider.fetch_hot_topics(
            trade_date=trade_date,
            slot=slot,
        )
    except Exception:  # noqa: BLE001
        return {"hot_topics": None}

    builder = HotTopicsBuilder()
    hot_topics_payload = builder.build(raw_payload)

    return {
        "hot_topics": {
            "trade_date": hot_topics_payload.trade_date,
            "slot": hot_topics_payload.slot,
            "topics": [
                {
                    "kind": t.kind,
                    "topic_id": t.topic_id,
                    "topic_name": t.topic_name,
                    "score": t.score,
                    "increase_pct": t.increase_pct,
                    "speed_pct": t.speed_pct,
                    "turnover": t.turnover,
                    "net_inflow": t.net_inflow,
                }
                for t in hot_topics_payload.topics
            ],
            "sources": hot_topics_payload.sources,
            "fetched_at": hot_topics_payload.fetched_at.isoformat() if hot_topics_payload.fetched_at else None,
        }
    }