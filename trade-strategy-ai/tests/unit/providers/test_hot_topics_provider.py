from __future__ import annotations

from datetime import date

from src.providers.hot_topics_provider import HotTopicsProvider
from src.providers.base import ProviderStatus


class FakeKaipanBackend:
    def fetch_board_strength(self, *, trade_date: date, slot: str, use_today_url=None):
        return {"list": [["001", "概念A", 12.3, 1.1, 0.5, 100.0, 200.0]]}

    def fetch_industry_ranking(self, *, trade_date: date, slot: str, use_today_url=None):
        return {"list": [["002", "行业B", 3.4, 2.2, 1.1, 150.0, 250.0]]}

    def fetch_concept_fengkou(self, *, trade_date: date, slot: str):
        return {"List": [["风口C", 7.8]]}


def test_hot_topics_provider_combines_multiple_sources() -> None:
    provider = HotTopicsProvider(backend=FakeKaipanBackend())

    result = provider.run("hot_topics", request={"trade_date": "2026-04-22", "slot": "09-25"})

    assert result.status == ProviderStatus.ok
    assert result.capability == "hot_topics"
    assert result.payload["dataset"] == "hot_topics"
    assert len(result.payload["topics"]) == 3
    assert result.payload["topics"][0]["kind"] == "concept"
    assert result.payload["topics"][1]["kind"] == "industry"
    assert result.payload["topics"][2]["kind"] == "concept_fengkou"
    assert result.payload["topics"][0]["topic_name"] == "概念A"
