"""题材成分解析器。

职责：
- 将 TopicConstituentsProvider 的标准化输出转换为 TopicConstituentsPayload
- 实例化 TopicConstituent dataclass
- 对 constituents 去重
"""
from __future__ import annotations

from datetime import datetime

from src.market_universe.schemas import TopicConstituent, TopicConstituentsPayload


class ConstituentsResolver:
    """将 provider 输出构建为 TopicConstituentsPayload。"""

    def build(self, provider_payload: dict) -> TopicConstituentsPayload:
        """从 provider 标准化输出构建 TopicConstituentsPayload。

        Args:
            provider_payload: TopicConstituentsProvider.normalize() 返回的 dict，
                包含 constituents list、trade_date、slot、sources。
                当 FallbackProvider 返回 partial=True 时，
                从 partial_payloads 中合并多个 constituents 列表。

        Returns:
            TopicConstituentsPayload dataclass 实例。
        """
        # NTL-S4-TD002: 处理 FallbackProvider 返回的 partial 结果
        if provider_payload.get("partial"):
            partial_payloads = provider_payload.get("partial_payloads", [])
            raw_constituents = []
            trade_date = ""
            slot = ""
            sources = []
            for p in partial_payloads:
                raw_constituents.extend(p.get("constituents", []))
                trade_date = trade_date or p.get("trade_date", "")
                slot = slot or p.get("slot", "")
                sources.extend(p.get("sources", []))
        else:
            raw_constituents = provider_payload.get("constituents", [])
            trade_date = provider_payload.get("trade_date", "")
            slot = provider_payload.get("slot", "")
            sources = provider_payload.get("sources", [])

        # 实例化 TopicConstituent，去重
        seen: set[tuple[str, str | None]] = set()
        constituents: list[TopicConstituent] = []

        for item in raw_constituents:
            # 不同 kind 有不同的唯一键：有些用 topic_id，有些用 symbol
            kind = item.get("kind", "")
            if kind in ("stock_sector_v2", "theme_detail", "limit_up_reason"):
                key = (kind, item.get("topic_id"))
            else:
                key = (kind, item.get("symbol"))

            if key in seen:
                continue
            seen.add(key)

            constituent = TopicConstituent(
                kind=kind,
                topic_id=item.get("topic_id"),
                topic_name=item.get("topic_name"),
                symbol=item.get("symbol"),
                name=item.get("name"),
                topic_change_pct=item.get("topic_change_pct"),
                leader_symbol=item.get("leader_symbol"),
                leader_name=item.get("leader_name"),
                leader_change_pct=item.get("leader_change_pct"),
                board_num=item.get("board_num"),
                net_buy=item.get("net_buy"),
                brief_intro=item.get("brief_intro"),
            )
            constituents.append(constituent)

        return TopicConstituentsPayload(
            trade_date=trade_date,
            slot=slot,
            constituents=constituents,
            sources=list(sources),
            fetched_at=datetime.now(),
        )