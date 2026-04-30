"""S10-010 测试：source_topic_ids 统一生成。"""

from src.market_universe.snapshot_service import generate_canonical_topic_tags


class TestCanonicalTopicTags:
    """验证统一 source_topic_ids tag 生成逻辑"""

    def test_generate_tags_from_hot_topics_and_constituents(self):
        """tag 应来自 hot_topics 和 topic_constituents 双重校验"""
        hot_topics = [
            {"topic_id": "T1", "topic_name": "AI"},
            {"topic_id": "T2", "topic_name": "新能源"},
        ]
        topic_constituents = {
            "T1": ["AAPL", "GOOGL", "MSFT"],
            "T3": ["TSLA"],  # T3 不在 hot_topics 中，应被过滤
        }

        tags = generate_canonical_topic_tags(
            hot_topics=hot_topics,
            topic_constituents=topic_constituents,
            target_symbols=["AAPL", "TSLA"],
        )

        # T1 符合：存在于 hot_topics 且 AAPL 在其 constituents 中
        assert "T1" in tags
        # T3 不符合：不在 hot_topics 中，即使 TSLA 在其 constituents 中
        assert "T3" not in tags

    def test_empty_hot_topics_returns_empty_tags(self):
        """hot_topics 为空时返回空列表"""
        tags = generate_canonical_topic_tags(
            hot_topics=[],
            topic_constituents={"T1": ["AAPL"]},
            target_symbols=["AAPL"],
        )
        assert tags == []

    def test_empty_topic_constituents_returns_empty_tags(self):
        """topic_constituents 为空时返回空列表"""
        tags = generate_canonical_topic_tags(
            hot_topics=[{"topic_id": "T1", "topic_name": "AI"}],
            topic_constituents={},
            target_symbols=["AAPL"],
        )
        assert tags == []

    def test_no_target_symbols_returns_all_matching_topics(self):
        """没有指定 target_symbols 时，返回所有在 hot_topics 和 constituents 中都存在的 topic"""
        hot_topics = [
            {"topic_id": "T1", "topic_name": "AI"},
            {"topic_id": "T2", "topic_name": "新能源"},
        ]
        topic_constituents = {
            "T1": ["AAPL", "GOOGL"],
            "T2": ["TSLA"],
            "T3": ["FB"],  # T3 不在 hot_topics 中
        }

        tags = generate_canonical_topic_tags(
            hot_topics=hot_topics,
            topic_constituents=topic_constituents,
            target_symbols=None,  # 不指定 target
        )

        # T1 和 T2 都在 hot_topics 中，且在 constituents 中有值
        assert set(tags) == {"T1", "T2"}

    def test_topic_without_symbol_match_is_filtered(self):
        """topic 在 hot_topics 中存在，但 constituents 与 target_symbols 无交集时过滤"""
        hot_topics = [
            {"topic_id": "T1", "topic_name": "AI"},
        ]
        topic_constituents = {
            "T1": ["GOOGL", "MSFT"],  # 不包含 AAPL
        }

        tags = generate_canonical_topic_tags(
            hot_topics=hot_topics,
            topic_constituents=topic_constituents,
            target_symbols=["AAPL"],  # 只关心 AAPL
        )

        # T1 不在结果中，因为它的 constituents 不包含 AAPL
        assert tags == []

    def test_generate_canonical_topic_tags_is_standalone_function(self):
        """generate_canonical_topic_tags 应是独立函数，可在保存快照时调用"""
        assert callable(generate_canonical_topic_tags)
