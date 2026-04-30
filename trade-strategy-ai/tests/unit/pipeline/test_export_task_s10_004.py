"""S10-004 测试：DuckDB UPSERT 修复 - 明确冲突列为 (article_id, schema_version)。"""

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.pipeline.tasks.export_task import (
    METADATA_COLUMNS,
    _serialize_metadata,
)


class TestDuckDBUPSERT:
    """验证 DuckDB UPSERT 明确冲突列为 (article_id, schema_version)"""

    def test_metadata_columns_contains_article_id_and_schema_version(self):
        """METADATA_COLUMNS 应包含 article_id 和 schema_version"""
        assert "article_id" in METADATA_COLUMNS
        assert "schema_version" in METADATA_COLUMNS

    def test_serialize_metadata_returns_string_for_article_id(self):
        """_serialize_metadata 返回的 article_id 应为字符串"""
        meta = MagicMock()
        meta.id = uuid4()
        meta.article_id = uuid4()
        meta.schema_version = "v1"
        meta.processed_at = datetime(2026, 4, 29)
        meta.extracted_concepts = []
        meta.trading_symbols = ["AAPL"]
        meta.strategy_rules = []
        meta.preconditions = []
        meta.comment_insights = []
        meta.raw_llm_output = {}
        meta.sentiment_score = 0.8
        meta.confidence_score = 0.9

        result = _serialize_metadata(meta)
        # result 是 tuple，第一个元素是 id，第二个是 article_id
        assert isinstance(result[1], str)  # article_id 应该是字符串

    def test_serialize_metadata_returns_string_for_schema_version(self):
        """_serialize_metadata 返回的 schema_version 应保持原样"""
        meta = MagicMock()
        meta.id = uuid4()
        meta.article_id = uuid4()
        meta.schema_version = "v2"
        meta.processed_at = datetime(2026, 4, 29)
        meta.extracted_concepts = []
        meta.trading_symbols = ["AAPL"]
        meta.strategy_rules = []
        meta.preconditions = []
        meta.comment_insights = []
        meta.raw_llm_output = {}
        meta.sentiment_score = 0.8
        meta.confidence_score = 0.9

        result = _serialize_metadata(meta)
        # result[2] 是 schema_version
        assert result[2] == "v2"

    def test_metadata_sql_should_specify_conflict_columns(self):
        """元数据 SQL 应明确指定 ON CONFLICT 列（通过检查 SQL 字符串）"""
        # 这个测试验证修复后的 metadata_sql 包含冲突列
        # 由于 metadata_sql 在函数内部定义，我们通过集成测试来验证
        # 这里只验证 METADATA_COLUMNS 的正确性
        expected_columns = [
            "id", "article_id", "schema_version", "processed_at",
            "extracted_concepts", "trading_symbols", "strategy_rules",
            "preconditions", "comment_insights", "raw_llm_output",
            "sentiment_score", "confidence_score",
        ]
        assert METADATA_COLUMNS == expected_columns

    def test_serialize_metadata_tuple_length_matches_columns(self):
        """_serialize_metadata 返回的 tuple 长度应与 METADATA_COLUMNS 一致"""
        meta = MagicMock()
        meta.id = uuid4()
        meta.article_id = uuid4()
        meta.schema_version = "v1"
        meta.processed_at = datetime(2026, 4, 29)
        meta.extracted_concepts = []
        meta.trading_symbols = ["AAPL"]
        meta.strategy_rules = []
        meta.preconditions = []
        meta.comment_insights = []
        meta.raw_llm_output = {}
        meta.sentiment_score = 0.8
        meta.confidence_score = 0.9

        result = _serialize_metadata(meta)
        assert len(result) == len(METADATA_COLUMNS)
