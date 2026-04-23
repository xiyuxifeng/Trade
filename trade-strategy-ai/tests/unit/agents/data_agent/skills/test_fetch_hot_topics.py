"""fetch_hot_topics skill 测试。"""

from datetime import date
from src.agents.data_agent.skills.fetch_hot_topics import supported_fields, to_payload


class TestFetchHotTopicsSkill:
    """测试热点拉取 skill。"""

    def test_supported_fields_returns_hot_topics(self):
        """supported_fields 应返回包含 hot_topics 的列表。"""
        fields = supported_fields()
        assert "hot_topics" in fields

    def test_to_payload_returns_empty_when_no_dataset(self):
        """dataset 不是 hot_topics 时返回空 dict。"""
        result = to_payload(dataset=None)
        assert result == {}

        result = to_payload(dataset="last_price")
        assert result == {}

    def test_to_payload_returns_empty_when_no_provider(self):
        """没有 provider 时返回 None 的 hot_topics。"""
        result = to_payload(dataset="hot_topics", provider=None)
        assert result == {"hot_topics": None}

    def test_to_payload_with_mock_provider(self):
        """有 provider 时返回构建后的热点数据。"""
        from src.agents.data_agent.skills.fetch_hot_topics import to_payload

        # 构造一个 mock provider
        mock_provider = _MockHotTopicsProvider()

        result = to_payload(
            dataset="hot_topics",
            snapshot_date=date(2026, 4, 23),
            slot="17-30",
            provider=mock_provider,
        )

        assert "hot_topics" in result
        assert result["hot_topics"] is not None
        hot = result["hot_topics"]
        assert hot["trade_date"] == "2026-04-23"
        assert hot["slot"] == "17-30"
        assert len(hot["topics"]) == 2
        assert hot["topics"][0]["topic_name"] == "人工智能"
        assert hot["sources"] == ["board_strength", "industry", "concept_fengkou"]

    def test_to_payload_handles_provider_exception(self):
        """provider 抛出异常时返回 None。"""
        bad_provider = _BadProvider()

        result = to_payload(
            dataset="hot_topics",
            snapshot_date=date(2026, 4, 23),
            provider=bad_provider,
        )

        assert result == {"hot_topics": None}


class _MockHotTopicsProvider:
    """模拟 HotTopicsProvider，用于测试。"""

    def fetch_hot_topics(self, *, trade_date, slot, **kwargs):
        return {
            "dataset": "hot_topics",
            "trade_date": trade_date.isoformat(),
            "slot": slot,
            "topics": [
                {
                    "kind": "concept",
                    "topic_id": "BK0001",
                    "topic_name": "人工智能",
                    "score": 85.5,
                    "increase_pct": 3.2,
                    "speed_pct": 1.1,
                    "turnover": 5000.0,
                    "net_inflow": 2000.0,
                },
                {
                    "kind": "industry",
                    "topic_id": "HY001",
                    "topic_name": "电子",
                    "score": 80.0,
                    "increase_pct": 2.1,
                    "speed_pct": 0.5,
                    "turnover": 3000.0,
                    "net_inflow": 1500.0,
                },
            ],
            "sources": ["board_strength", "industry", "concept_fengkou"],
        }


class _BadProvider:
    """模拟抛出异常的 provider。"""

    def fetch_hot_topics(self, **kwargs):
        raise RuntimeError("provider error")