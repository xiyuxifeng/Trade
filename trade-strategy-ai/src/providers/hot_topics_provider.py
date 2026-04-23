from __future__ import annotations

from datetime import date
from typing import Any

from src.providers.base import ProviderBase, ProviderError


class HotTopicsProvider(ProviderBase):
    """热点主题 provider。

    作用：
    - 复用已有 Kaipan 接口结果
    - 汇总板块强度、行业排名、概念风口，输出统一热点结构
    - 为后续 market_universe / DataAgent 提供单一入口
    """

    def __init__(self, *, backend: Any, provider_name: str = "hot_topics") -> None:
        super().__init__(provider_name=provider_name)
        self.backend = backend

    def request(self, *, capability: str, **kwargs: Any) -> dict[str, Any]:
        """拉取热点原始数据。"""

        if capability != "hot_topics":
            self.unsupported(capability)

        trade_date = kwargs.get("trade_date")
        slot = kwargs.get("slot", "09-25")
        use_today_url = kwargs.get("use_today_url")

        if isinstance(trade_date, str):
            trade_date = date.fromisoformat(trade_date)
        if not isinstance(trade_date, date):
            raise ProviderError("trade_date is required and must be a date or ISO string")

        board_strength = self.backend.fetch_board_strength(
            trade_date=trade_date,
            slot=slot,
            use_today_url=use_today_url,
        )
        industry = self.backend.fetch_industry_ranking(
            trade_date=trade_date,
            slot=slot,
            use_today_url=use_today_url,
        )
        concept_fengkou = self.backend.fetch_concept_fengkou(
            trade_date=trade_date,
            slot=slot,
        )

        return {
            "trade_date": trade_date.isoformat(),
            "slot": slot,
            "board_strength": board_strength,
            "industry": industry,
            "concept_fengkou": concept_fengkou,
        }

    def normalize(
        self,
        *,
        capability: str,
        raw: dict[str, Any],
        request: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """把多来源热点结果归一成统一 topics 列表。"""

        if capability != "hot_topics":
            self.unsupported(capability)

        trade_date = raw.get("trade_date") or (request or {}).get("trade_date")
        slot = raw.get("slot") or (request or {}).get("slot")

        topics: list[dict[str, Any]] = []
        topics.extend(self._parse_ranked_topics(raw.get("board_strength", {}), kind="concept"))
        topics.extend(self._parse_ranked_topics(raw.get("industry", {}), kind="industry"))
        topics.extend(self._parse_fengkou_topics(raw.get("concept_fengkou", {}), kind="concept_fengkou"))

        return {
            "dataset": "hot_topics",
            "trade_date": trade_date,
            "slot": slot,
            "topics": topics,
            "sources": ["board_strength", "industry", "concept_fengkou"],
        }

    def _parse_ranked_topics(self, raw: dict[str, Any], *, kind: str) -> list[dict[str, Any]]:
        """解析 RealRankingInfo 的 list 数组。"""

        items = raw.get("list")
        if not isinstance(items, list):
            return []

        topics: list[dict[str, Any]] = []
        for row in items:
            if not isinstance(row, list) or len(row) < 2:
                continue
            topics.append(
                {
                    "kind": kind,
                    "topic_id": row[0],
                    "topic_name": row[1],
                    "score": row[2] if len(row) > 2 else None,
                    "increase_pct": row[3] if len(row) > 3 else None,
                    "speed_pct": row[4] if len(row) > 4 else None,
                    "turnover": row[5] if len(row) > 5 else None,
                    "net_inflow": row[6] if len(row) > 6 else None,
                }
            )
        return topics

    def _parse_fengkou_topics(self, raw: dict[str, Any], *, kind: str) -> list[dict[str, Any]]:
        """解析 GetFengKYDPlate 的 List 数组。"""

        items = raw.get("List") or raw.get("list")
        if not isinstance(items, list):
            return []

        topics: list[dict[str, Any]] = []
        for idx, row in enumerate(items):
            if not isinstance(row, list) or not row:
                continue
            topics.append(
                {
                    "kind": kind,
                    "topic_id": f"fengkou_{idx}",
                    "topic_name": row[0],
                    "score": row[1] if len(row) > 1 else None,
                }
            )
        return topics
