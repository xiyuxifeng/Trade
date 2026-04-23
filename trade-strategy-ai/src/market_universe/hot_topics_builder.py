"""热点快照构建器。

职责：
- 将 HotTopicsProvider 的标准化输出转换为 HotTopicsPayload
- 实例化 HotTopic dataclass
- 对 topics 去重、排序
"""
from __future__ import annotations

from dataclasses import fields
from datetime import datetime

from src.market_universe.schemas import HotTopic, HotTopicsPayload


class HotTopicsBuilder:
    """将 provider 输出构建为 HotTopicsPayload。"""

    def build(self, provider_payload: dict) -> HotTopicsPayload:
        """从 provider 标准化输出构建 HotTopicsPayload。

        Args:
            provider_payload: HotTopicsProvider.normalize() 返回的 dict，
                包含 topics list、trade_date、slot、sources。

        Returns:
            HotTopicsPayload dataclass 实例。
        """
        raw_topics = provider_payload.get("topics", [])
        trade_date = provider_payload.get("trade_date", "")
        slot = provider_payload.get("slot", "")
        sources = provider_payload.get("sources", [])

        # 实例化 HotTopic，去重
        seen: set[tuple[str, str]] = set()
        hot_topics: list[HotTopic] = []

        for item in raw_topics:
            key = (item.get("kind", ""), item.get("topic_id", ""))
            if key in seen:
                continue
            seen.add(key)

            hot_topic = HotTopic(
                kind=item.get("kind", ""),
                topic_id=item.get("topic_id", ""),
                topic_name=item.get("topic_name", ""),
                score=item.get("score"),
                increase_pct=item.get("increase_pct"),
                speed_pct=item.get("speed_pct"),
                turnover=item.get("turnover"),
                net_inflow=item.get("net_inflow"),
            )
            hot_topics.append(hot_topic)

        # 按 score 降序排列，None 排在最后
        hot_topics.sort(key=lambda t: (t.score is None, -(t.score or 0)))

        return HotTopicsPayload(
            trade_date=trade_date,
            slot=slot,
            topics=hot_topics,
            sources=list(sources),
            fetched_at=datetime.now(),
        )