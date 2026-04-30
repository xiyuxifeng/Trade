"""S10-008 测试：规则与标的联合验证。"""

from unittest.mock import MagicMock
import pytest

from src.strategy_library.builder import validate_rule_symbol_association


class TestRuleSymbolAssociation:
    """验证规则与标的联合验证"""

    def test_rule_with_symbol_and_rules_is_valid(self):
        """同时有 trading_symbols 和 strategy_rules 的文章是有效证据"""
        article = MagicMock()
        article.article_id = "art_001"
        article.trading_symbols = ["AAPL"]
        article.strategy_rules = [{"rule_id": "R001", "rule_text": "RSI<30买入"}]
        article.preconditions = []

        is_valid = validate_rule_symbol_association(article)
        assert is_valid is True

    def test_rule_without_symbol_is_invalid(self):
        """有 strategy_rules 但无 trading_symbols 的文章是无效证据"""
        article = MagicMock()
        article.article_id = "art_002"
        article.trading_symbols = []  # 无标的
        article.strategy_rules = [{"rule_id": "R001", "rule_text": "市场普涨"}]
        article.preconditions = []

        is_valid = validate_rule_symbol_association(article)
        assert is_valid is False

    def test_symbols_with_only_preconditions_is_valid(self):
        """有 trading_symbols + preconditions（无 strategy_rules）的文章是有效证据"""
        article = MagicMock()
        article.article_id = "art_003"
        article.trading_symbols = ["AAPL"]
        article.strategy_rules = []
        article.preconditions = [{"condition": "market_bull"}]

        is_valid = validate_rule_symbol_association(article)
        assert is_valid is True

    def test_only_symbols_no_rules_valid_for_sentiment(self):
        """只有 trading_symbols 没有 rules 也有效（用于 sentiment 场景）"""
        article = MagicMock()
        article.article_id = "art_004"
        article.trading_symbols = ["AAPL"]
        article.strategy_rules = []
        article.preconditions = []

        is_valid = validate_rule_symbol_association(article)
        assert is_valid is True

    def test_no_symbols_no_rules_no_preconditions_invalid(self):
        """什么都没有的文章是无效证据"""
        article = MagicMock()
        article.article_id = "art_005"
        article.trading_symbols = []
        article.strategy_rules = []
        article.preconditions = []

        is_valid = validate_rule_symbol_association(article)
        assert is_valid is False

    def test_none_trading_symbols_invalid(self):
        """trading_symbols 为 None 时无效"""
        article = MagicMock()
        article.article_id = "art_006"
        article.trading_symbols = None
        article.strategy_rules = [{"rule_id": "R001", "rule_text": "some rule"}]
        article.preconditions = []

        is_valid = validate_rule_symbol_association(article)
        assert is_valid is False

    def test_none_rules_and_preconditions_valid_with_symbols(self):
        """trading_symbols 有值，rules 和 preconditions 都是 None 时有效"""
        article = MagicMock()
        article.article_id = "art_007"
        article.trading_symbols = ["AAPL"]
        article.strategy_rules = None
        article.preconditions = None

        is_valid = validate_rule_symbol_association(article)
        assert is_valid is True
