"""fetch_topic_constituents skill 测试。"""

from datetime import date
from src.agents.data_agent.skills.fetch_topic_constituents import supported_fields, to_payload


class TestFetchTopicConstituentsSkill:
    """测试题材成分拉取 skill。"""

    def test_supported_fields_returns_topic_constituents(self):
        """supported_fields 应返回包含 topic_constituents 的列表。"""
        fields = supported_fields()
        assert "topic_constituents" in fields

    def test_to_payload_returns_empty_when_no_dataset(self):
        """dataset 不是 topic_constituents 时返回空 dict。"""
        result = to_payload(dataset=None)
        assert result == {}

        result = to_payload(dataset="last_price")
        assert result == {}

    def test_to_payload_returns_empty_when_no_provider(self):
        """没有 provider 时返回 None 的 topic_constituents。"""
        result = to_payload(dataset="topic_constituents", provider=None)
        assert result == {"topic_constituents": None}

    def test_to_payload_with_mock_provider(self):
        """有 provider 时返回构建后的题材成分数据。"""
        from src.agents.data_agent.skills.fetch_topic_constituents import to_payload

        mock_provider = _MockTopicConstituentsProvider()

        result = to_payload(
            dataset="topic_constituents",
            snapshot_date=date(2026, 4, 23),
            slot="17-30",
            provider=mock_provider,
        )

        assert "topic_constituents" in result
        assert result["topic_constituents"] is not None
        tc = result["topic_constituents"]
        assert tc["trade_date"] == "2026-04-23"
        assert tc["slot"] == "17-30"
        assert len(tc["constituents"]) == 2
        assert tc["constituents"][0]["topic_name"] == "人工智能"
        assert tc["constituents"][0]["kind"] == "stock_sector_v2"
        assert "stock_sector_v2" in tc["sources"]

    def test_to_payload_handles_provider_exception(self):
        """provider 抛出异常时返回 None。"""
        bad_provider = _BadProvider()

        result = to_payload(
            dataset="topic_constituents",
            snapshot_date=date(2026, 4, 23),
            provider=bad_provider,
        )

        assert result == {"topic_constituents": None}


class _MockTopicConstituentsProvider:
    """模拟 TopicConstituentsProvider，用于测试。"""

    def fetch_topic_constituents(self, *, trade_date, slot, **kwargs):
        return {
            "dataset": "topic_constituents",
            "trade_date": trade_date.isoformat(),
            "slot": slot,
            "constituents": [
                {
                    "kind": "stock_sector_v2",
                    "topic_id": "ZS001",
                    "topic_name": "人工智能",
                    "topic_change_pct": 2.5,
                    "leader_symbol": "000001",
                    "leader_name": "平安银行",
                    "leader_change_pct": 3.1,
                },
                {
                    "kind": "limit_up_reason",
                    "topic_id": "ZS002",
                    "topic_name": "芯片",
                },
            ],
            "sources": ["stock_sector_v2", "limit_up_reason", "limit_up_info", "lhb_list", "theme_detail"],
        }


class _BadProvider:
    """模拟抛出异常的 provider。"""

    def fetch_topic_constituents(self, **kwargs):
        raise RuntimeError("provider error")