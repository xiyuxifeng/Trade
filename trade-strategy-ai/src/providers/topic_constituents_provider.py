from __future__ import annotations

from datetime import date
from typing import Any

from src.providers.base import ProviderBase, ProviderError


class TopicConstituentsProvider(ProviderBase):
    """题材成分 provider。

    作用：
    - 汇总题材相关来源
    - 统一输出题材、龙头、涨停原因、龙虎榜等成分信息
    """

    def __init__(self, *, backend: Any, provider_name: str = "topic_constituents") -> None:
        super().__init__(provider_name=provider_name)
        self.backend = backend

    def request(self, *, capability: str, **kwargs: Any) -> dict[str, Any]:
        """拉取题材成分原始数据。"""

        if capability != "topic_constituents":
            self.unsupported(capability)

        trade_date = kwargs.get("trade_date")
        slot = kwargs.get("slot", "09-25")
        if isinstance(trade_date, str):
            trade_date = date.fromisoformat(trade_date)
        if not isinstance(trade_date, date):
            raise ProviderError("trade_date is required and must be a date or ISO string")

        stock_sector_v2 = self.backend.fetch_stock_sector_v2(trade_date=trade_date, slot=slot)
        theme_detail = self.backend.fetch_theme_detail(trade_date=trade_date, slot=slot, theme_id=kwargs.get("theme_id", ""))
        limit_up_reason = self.backend.fetch_limit_up_reason(trade_date=trade_date, slot=slot)
        limit_up_info = self.backend.fetch_limit_up_info(trade_date=trade_date, slot=slot)
        lhb_list = self.backend.fetch_lhb_list(trade_date=trade_date, slot=slot)

        return {
            "trade_date": trade_date.isoformat(),
            "slot": slot,
            "stock_sector_v2": stock_sector_v2,
            "theme_detail": theme_detail,
            "limit_up_reason": limit_up_reason,
            "limit_up_info": limit_up_info,
            "lhb_list": lhb_list,
        }

    def normalize(
        self,
        *,
        capability: str,
        raw: dict[str, Any],
        request: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """把多来源题材成分结果归一成统一 constituents 列表。"""

        if capability != "topic_constituents":
            self.unsupported(capability)

        trade_date = raw.get("trade_date") or (request or {}).get("trade_date")
        slot = raw.get("slot") or (request or {}).get("slot")

        constituents: list[dict[str, Any]] = []
        constituents.extend(self._parse_stock_sector_v2(raw.get("stock_sector_v2", {})))
        constituents.extend(self._parse_theme_detail(raw.get("theme_detail", {})))
        constituents.extend(self._parse_limit_up_reason(raw.get("limit_up_reason", {})))
        constituents.extend(self._parse_limit_up_info(raw.get("limit_up_info", {})))
        constituents.extend(self._parse_lhb_list(raw.get("lhb_list", {})))

        return {
            "dataset": "topic_constituents",
            "trade_date": trade_date,
            "slot": slot,
            "constituents": constituents,
            "sources": ["stock_sector_v2", "theme_detail", "limit_up_reason", "limit_up_info", "lhb_list"],
        }

    def _parse_stock_sector_v2(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        items = raw.get("info")
        if not isinstance(items, list):
            return []
        results = []
        for row in items:
            if not isinstance(row, list) or len(row) < 2:
                continue
            results.append(
                {
                    "kind": "stock_sector_v2",
                    "topic_id": row[0],
                    "topic_name": row[1],
                    "topic_change_pct": row[2] if len(row) > 2 else None,
                    "leader_symbol": row[3] if len(row) > 3 else None,
                    "leader_name": row[4] if len(row) > 4 else None,
                    "leader_change_pct": row[5] if len(row) > 5 else None,
                }
            )
        return results

    def _parse_theme_detail(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        if not raw:
            return []
        return [
            {
                "kind": "theme_detail",
                "topic_id": raw.get("ID"),
                "topic_name": raw.get("Name"),
                "brief_intro": raw.get("BriefIntro"),
            }
        ]

    def _parse_limit_up_reason(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        items = raw.get("list")
        if not isinstance(items, list):
            return []
        results = []
        for row in items:
            if not isinstance(row, dict):
                continue
            results.append(
                {
                    "kind": "limit_up_reason",
                    "topic_id": row.get("ZSCode"),
                    "topic_name": row.get("ZSName"),
                }
            )
        return results

    def _parse_limit_up_info(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        items = raw.get("StockList")
        if not isinstance(items, list):
            return []
        results = []
        for row in items:
            if not isinstance(row, list) or len(row) < 2:
                continue
            results.append(
                {
                    "kind": "limit_up_info",
                    "symbol": row[0],
                    "name": row[1],
                    "board_num": row[2] if len(row) > 2 else None,
                }
            )
        return results

    def _parse_lhb_list(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        items = raw.get("list")
        if not isinstance(items, list):
            return []
        results = []
        for row in items:
            if not isinstance(row, dict):
                continue
            results.append(
                {
                    "kind": "lhb_list",
                    "symbol": row.get("ID"),
                    "name": row.get("Name"),
                    "net_buy": row.get("BuyIn"),
                }
            )
        return results
