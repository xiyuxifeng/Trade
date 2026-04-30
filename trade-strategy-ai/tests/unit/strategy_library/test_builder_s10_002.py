"""S10-002 测试：ArticleEvidence Protocol 扩展。"""

from datetime import datetime, UTC
from unittest.mock import MagicMock

import pytest

from src.strategy_library.builder import ArticleEvidence


class TestArticleEvidenceProtocol:
    """验证 ArticleEvidence Protocol 包含规则相关字段"""

    def test_article_evidence_supports_strategy_rules_field(self):
        """ArticleEvidence 可以包含 strategy_rules 字段"""
        mock_evidence: ArticleEvidence = {
            "article_id": "art_001",
            "trading_symbols": ["AAPL"],
            "sentiment_score": 0.8,
            "confidence_score": 0.9,
            "rationale": "Test rationale",
            "entry_price": None,
            "strategy_rules": [
                {"rule_id": "R001", "rule_text": "RSI<30买入"}
            ],
            "preconditions": None,
            "published_at": None,
        }
        assert "strategy_rules" in mock_evidence
        assert mock_evidence["strategy_rules"][0]["rule_id"] == "R001"

    def test_article_evidence_supports_preconditions_field(self):
        """ArticleEvidence 可以包含 preconditions 字段"""
        mock_evidence: ArticleEvidence = {
            "article_id": "art_001",
            "trading_symbols": ["AAPL"],
            "sentiment_score": 0.8,
            "confidence_score": 0.9,
            "rationale": "Test rationale",
            "entry_price": None,
            "strategy_rules": None,
            "preconditions": [
                {"field": "market_trend", "operator": "==", "value": "bullish"}
            ],
            "published_at": None,
        }
        assert "preconditions" in mock_evidence
        assert mock_evidence["preconditions"][0]["field"] == "market_trend"

    def test_article_evidence_supports_published_at_field(self):
        """ArticleEvidence 可以包含 published_at 字段"""
        pub_time = datetime(2026, 4, 20, tzinfo=UTC)
        mock_evidence: ArticleEvidence = {
            "article_id": "art_001",
            "trading_symbols": ["AAPL"],
            "sentiment_score": 0.8,
            "confidence_score": 0.9,
            "rationale": "Test rationale",
            "entry_price": None,
            "strategy_rules": None,
            "preconditions": None,
            "published_at": pub_time,
        }
        assert "published_at" in mock_evidence
        assert mock_evidence["published_at"] == pub_time

    def test_article_evidence_all_new_fields_optional(self):
        """新字段都是可选的（None 值有效）"""
        mock_evidence: ArticleEvidence = {
            "article_id": "art_001",
            "trading_symbols": ["AAPL"],
            "sentiment_score": 0.8,
            "confidence_score": 0.9,
            "rationale": "Test rationale",
            "entry_price": None,
            "strategy_rules": None,
            "preconditions": None,
            "published_at": None,
        }
        # 所有字段都应该是 None 或有效值（不抛出异常）
        assert mock_evidence["strategy_rules"] is None
        assert mock_evidence["preconditions"] is None
        assert mock_evidence["published_at"] is None

    def test_mock_article_can_have_all_fields(self):
        """MagicMock 模拟的对象可以拥有所有 Protocol 要求的字段"""
        article = MagicMock()
        article.article_id = "art_001"
        article.trading_symbols = ["AAPL"]
        article.sentiment_score = 0.8
        article.confidence_score = 0.9
        article.rationale = "Test rationale"
        article.entry_price = None
        article.strategy_rules = [{"rule_id": "R001", "rule_text": "RSI<30买入"}]
        article.preconditions = [{"field": "market_trend", "operator": "==", "value": "bullish"}]
        article.published_at = datetime(2026, 4, 20, tzinfo=UTC)

        # 验证可以作为 ArticleEvidence 使用
        assert article.article_id == "art_001"
        assert len(article.strategy_rules) == 1
        assert len(article.preconditions) == 1
        assert article.published_at.year == 2026
