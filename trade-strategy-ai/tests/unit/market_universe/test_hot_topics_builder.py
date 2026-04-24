"""hot_topics_builder 测试。"""

from datetime import datetime
from src.market_universe.schemas import HotTopicsPayload, HotTopic


class TestHotTopicsBuilder:
    """Builder 将 provider 原始输出转换为 HotTopicsPayload。"""

    def test_build_from_provider_result(self):
        """标准 provider 输出应转换为 HotTopicsPayload。"""
        from src.market_universe.hot_topics_builder import HotTopicsBuilder

        provider_payload = {
            "dataset": "hot_topics",
            "trade_date": "2026-04-23",
            "slot": "17-30",
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

        builder = HotTopicsBuilder()
        result = builder.build(provider_payload)

        assert isinstance(result, HotTopicsPayload)
        assert result.trade_date == "2026-04-23"
        assert result.slot == "17-30"
        assert len(result.topics) == 2
        assert result.sources == ["board_strength", "industry", "concept_fengkou"]

        # 验证 HotTopic dataclass 实例
        first_topic = result.topics[0]
        assert isinstance(first_topic, HotTopic)
        assert first_topic.kind == "concept"
        assert first_topic.topic_id == "BK0001"
        assert first_topic.topic_name == "人工智能"
        assert first_topic.score == 85.5
        assert first_topic.increase_pct == 3.2

        second_topic = result.topics[1]
        assert second_topic.kind == "industry"
        assert second_topic.topic_name == "电子"

    def test_build_with_empty_topics(self):
        """空 topics 列表应正常返回空 payload。"""
        from src.market_universe.hot_topics_builder import HotTopicsBuilder

        provider_payload = {
            "dataset": "hot_topics",
            "trade_date": "2026-04-23",
            "slot": "09-25",
            "topics": [],
            "sources": ["board_strength"],
        }

        builder = HotTopicsBuilder()
        result = builder.build(provider_payload)

        assert isinstance(result, HotTopicsPayload)
        assert result.trade_date == "2026-04-23"
        assert result.slot == "09-25"
        assert len(result.topics) == 0

    def test_build_with_missing_optional_fields(self):
        """provider 输出缺少可选字段时应正常处理。"""
        from src.market_universe.hot_topics_builder import HotTopicsBuilder

        provider_payload = {
            "dataset": "hot_topics",
            "trade_date": "2026-04-23",
            "slot": "15-00",
            "topics": [
                {
                    "kind": "concept",
                    "topic_id": "BK0002",
                    "topic_name": "芯片",
                },
            ],
            "sources": ["concept_fengkou"],
        }

        builder = HotTopicsBuilder()
        result = builder.build(provider_payload)

        assert len(result.topics) == 1
        topic = result.topics[0]
        assert topic.topic_name == "芯片"
        assert topic.score is None
        assert topic.increase_pct is None
        assert topic.speed_pct is None

    def test_build_includes_fetched_at_timestamp(self):
        """build 应自动填充 fetched_at 时间戳。"""
        from src.market_universe.hot_topics_builder import HotTopicsBuilder

        provider_payload = {
            "dataset": "hot_topics",
            "trade_date": "2026-04-23",
            "slot": "17-30",
            "topics": [],
            "sources": [],
        }

        builder = HotTopicsBuilder()
        before = datetime.now()
        result = builder.build(provider_payload)
        after = datetime.now()

        assert result.fetched_at is not None
        assert before <= result.fetched_at <= after

    def test_build_preserves_multiple_sources(self):
        """多个数据源应全部保留在 sources 中。"""
        from src.market_universe.hot_topics_builder import HotTopicsBuilder

        provider_payload = {
            "dataset": "hot_topics",
            "trade_date": "2026-04-23",
            "slot": "17-30",
            "topics": [
                {"kind": "concept_fengkou", "topic_id": "fk001", "topic_name": "风口1"},
            ],
            "sources": ["board_strength", "industry", "concept_fengkou"],
        }

        builder = HotTopicsBuilder()
        result = builder.build(provider_payload)

        assert len(result.sources) == 3
        assert "board_strength" in result.sources
        assert "concept_fengkou" in result.sources

    def test_build_deduplicates_by_topic_id_and_kind(self):
        """相同 kind + topic_id 的重复热点应去重。"""
        from src.market_universe.hot_topics_builder import HotTopicsBuilder

        provider_payload = {
            "dataset": "hot_topics",
            "trade_date": "2026-04-23",
            "slot": "17-30",
            "topics": [
                {"kind": "concept", "topic_id": "BK0001", "topic_name": "AI"},
                {"kind": "concept", "topic_id": "BK0001", "topic_name": "AI"},  # 重复
                {"kind": "industry", "topic_id": "BK0001", "topic_name": "AI"},  # 不同 kind，保留
            ],
            "sources": [],
        }

        builder = HotTopicsBuilder()
        result = builder.build(provider_payload)

        # 3个输入，2个去重（concept/BK0001 去重保留1个，industry/BK0001 保留）
        assert len(result.topics) == 2

    def test_build_sorts_by_score_descending(self):
        """热点应按 score 降序排列。"""
        from src.market_universe.hot_topics_builder import HotTopicsBuilder

        provider_payload = {
            "dataset": "hot_topics",
            "trade_date": "2026-04-23",
            "slot": "17-30",
            "topics": [
                {"kind": "concept", "topic_id": "t3", "topic_name": "低分", "score": 60.0},
                {"kind": "concept", "topic_id": "t1", "topic_name": "高分", "score": 95.0},
                {"kind": "concept", "topic_id": "t2", "topic_name": "中分", "score": 75.0},
            ],
            "sources": [],
        }

        builder = HotTopicsBuilder()
        result = builder.build(provider_payload)

        assert result.topics[0].topic_name == "高分"
        assert result.topics[1].topic_name == "中分"
        assert result.topics[2].topic_name == "低分"

    def test_build_preserves_topics_without_score(self):
        """没有 score 的热点应保留且排在最后。"""
        from src.market_universe.hot_topics_builder import HotTopicsBuilder

        provider_payload = {
            "dataset": "hot_topics",
            "trade_date": "2026-04-23",
            "slot": "17-30",
            "topics": [
                {"kind": "concept", "topic_id": "t1", "topic_name": "无分", "score": None},
                {"kind": "concept", "topic_id": "t2", "topic_name": "有分", "score": 80.0},
            ],
            "sources": [],
        }

        builder = HotTopicsBuilder()
        result = builder.build(provider_payload)

        # 有 score 的排在前面
        assert result.topics[0].topic_name == "有分"
        assert result.topics[1].topic_name == "无分"

    def test_build_merges_partial_payloads(self):
        """NTL-S4-TD002: FallbackProvider 返回 partial=True 时，合并多个 partial_payloads。"""
        from src.market_universe.hot_topics_builder import HotTopicsBuilder

        # FallbackProvider partial 返回格式
        provider_payload = {
            "partial": True,
            "errors": ["provider2 timeout"],
            "partial_payloads": [
                {
                    "trade_date": "2026-04-23",
                    "slot": "17-30",
                    "topics": [
                        {"kind": "concept", "topic_id": "BK001", "topic_name": "AI", "score": 85.0},
                    ],
                    "sources": ["provider1"],
                },
                {
                    "trade_date": "2026-04-23",
                    "slot": "17-30",
                    "topics": [
                        {"kind": "industry", "topic_id": "HY001", "topic_name": "芯片", "score": 80.0},
                        {"kind": "concept", "topic_id": "BK002", "topic_name": "新能源", "score": 75.0},
                    ],
                    "sources": ["provider2"],
                },
            ],
        }

        builder = HotTopicsBuilder()
        result = builder.build(provider_payload)

        # 合并后应有 3 个 topics（AI、芯片、新能源）
        assert len(result.topics) == 3
        assert result.trade_date == "2026-04-23"
        assert result.slot == "17-30"
        # sources 合并
        assert "provider1" in result.sources
        assert "provider2" in result.sources