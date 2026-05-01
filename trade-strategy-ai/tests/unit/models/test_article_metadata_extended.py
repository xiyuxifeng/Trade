"""测试 article_metadata 模型扩展字段"""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.models.article_metadata import ArticleMetadata


class TestArticleMetadataExtendedFields:
    """测试 ArticleMetadata 模型的扩展字段"""

    def test_article_type_field_exists(self) -> None:
        """验证 article_type 字段存在"""
        assert hasattr(ArticleMetadata, "article_type")
        column = ArticleMetadata.__table__.c["article_type"]
        assert column.type.__class__.__name__ == "String"

    def test_extraction_version_field_exists(self) -> None:
        """验证 extraction_version 字段存在"""
        assert hasattr(ArticleMetadata, "extraction_version")
        column = ArticleMetadata.__table__.c["extraction_version"]
        assert column.type.__class__.__name__ == "String"

    def test_standalone_rule_ids_field_exists(self) -> None:
        """验证 standalone_rule_ids 字段存在（JSON 类型）"""
        assert hasattr(ArticleMetadata, "standalone_rule_ids")
        column = ArticleMetadata.__table__.c["standalone_rule_ids"]
        # JSON 类型在不同的数据库后端可能返回不同的类名
        assert "JSON" in column.type.__class__.__name__ or hasattr(column.type, "astypes")

    def test_derived_rule_ids_field_exists(self) -> None:
        """验证 derived_rule_ids 字段存在（JSON 类型）"""
        assert hasattr(ArticleMetadata, "derived_rule_ids")
        column = ArticleMetadata.__table__.c["derived_rule_ids"]
        assert "JSON" in column.type.__class__.__name__ or hasattr(column.type, "astypes")

    def test_trade_sample_ids_field_exists(self) -> None:
        """验证 trade_sample_ids 字段存在（JSON 类型）"""
        assert hasattr(ArticleMetadata, "trade_sample_ids")
        column = ArticleMetadata.__table__.c["trade_sample_ids"]
        assert "JSON" in column.type.__class__.__name__ or hasattr(column.type, "astypes")

    def test_all_extended_fields_nullable(self) -> None:
        """验证所有扩展字段都是可空的"""
        article_type = ArticleMetadata.__table__.c["article_type"]
        extraction_version = ArticleMetadata.__table__.c["extraction_version"]
        standalone_rule_ids = ArticleMetadata.__table__.c["standalone_rule_ids"]
        derived_rule_ids = ArticleMetadata.__table__.c["derived_rule_ids"]
        trade_sample_ids = ArticleMetadata.__table__.c["trade_sample_ids"]

        assert article_type.nullable is True
        assert extraction_version.nullable is True
        assert standalone_rule_ids.nullable is True
        assert derived_rule_ids.nullable is True
        assert trade_sample_ids.nullable is True

    def test_article_type_max_length(self) -> None:
        """验证 article_type 字段的最大长度为 32"""
        column = ArticleMetadata.__table__.c["article_type"]
        assert column.type.length == 32

    def test_extraction_version_max_length(self) -> None:
        """验证 extraction_version 字段的最大长度为 20"""
        column = ArticleMetadata.__table__.c["extraction_version"]
        assert column.type.length == 20
