from __future__ import annotations

from datetime import date

from src.providers.base import ProviderStatus
from src.providers.topic_constituents_provider import TopicConstituentsProvider


class FakeKaipanBackend:
    def fetch_stock_sector_v2(self, *, trade_date: date, slot: str, stock_id: str | None = None):
        return {"info": [["T1", "题材A", 12.3, "000001", "龙头A", 9.8]]}

    def fetch_theme_detail(self, *, trade_date: date, slot: str, theme_id: str):
        return {"ID": theme_id, "Name": "题材A", "BriefIntro": "简介A"}

    def fetch_limit_up_reason(self, *, trade_date: date, slot: str):
        return {"list": [{"ZSCode": "T2", "ZSName": "涨停题材B"}]}

    def fetch_limit_up_info(self, *, trade_date: date, slot: str):
        return {"StockList": [["000002", "股票B", 2]]}

    def fetch_lhb_list(self, *, trade_date: date, slot: str):
        return {"list": [{"ID": "000003", "Name": "股票C", "BuyIn": 100.0}]}


def test_topic_constituents_provider_combines_multiple_sources() -> None:
    provider = TopicConstituentsProvider(backend=FakeKaipanBackend())

    result = provider.run("topic_constituents", request={"trade_date": "2026-04-22", "slot": "09-25"})

    assert result.status == ProviderStatus.ok
    assert result.payload["dataset"] == "topic_constituents"
    assert len(result.payload["constituents"]) == 5
    assert result.payload["constituents"][0]["kind"] == "stock_sector_v2"
    assert result.payload["constituents"][0]["topic_name"] == "题材A"
    assert result.payload["constituents"][1]["kind"] == "theme_detail"
    assert result.payload["constituents"][2]["kind"] == "limit_up_reason"
