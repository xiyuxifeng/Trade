"""S10-001 测试：ArticleMetadata.strategy_rules 填充到 rules_snapshot。"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.strategy_library.builder import StrategyVersionBuilder
from src.strategy_library.schemas import (
    StrategyVersionStatus,
)
from src.trader_profile.schemas import (
    PositionBias,
    RiskStyle,
    StrategyPreference,
    StrategyTimeframe,
    ThemeStat,
    TraderProfile,
)


def _mock_article_with_rules(
    article_id: str,
    symbols: list[str],
    sentiment: float,
    rationale: str,
    strategy_rules: list[dict],
    confidence: float = 0.7,
    entry_price: float | None = None,
) -> MagicMock:
    """构造一个包含 strategy_rules 的模拟文章对象。"""
    article = MagicMock()
    article.article_id = article_id
    article.trading_symbols = symbols
    article.sentiment_score = sentiment
    article.confidence_score = confidence
    article.rationale = rationale
    article.entry_price = entry_price
    article.strategy_rules = strategy_rules
    return article


def _mock_article(
    article_id: str,
    symbols: list[str],
    sentiment: float,
    rationale: str,
    confidence: float = 0.7,
    entry_price: float | None = None,
) -> MagicMock:
    """构造一个模拟文章对象（无 strategy_rules）。"""
    article = MagicMock()
    article.article_id = article_id
    article.trading_symbols = symbols
    article.sentiment_score = sentiment
    article.confidence_score = confidence
    article.rationale = rationale
    article.entry_price = entry_price
    article.strategy_rules = []  # 默认空规则
    return article


class TestBuildRulesSnapshot:
    """验证 ArticleMetadata.strategy_rules 正确填充到 StrategyVersion.rules_snapshot"""

    @pytest.fixture
    def trader_profile(self):
        return TraderProfile(
            trader_id="test_trader",
            strategy_preference=StrategyPreference(
                timeframe=StrategyTimeframe.SWING,
                entry_type="breakout",
                max_positions=5,
            ),
            risk_style=RiskStyle.BALANCED,
            theme_preference=[ThemeStat(theme="AI", mentions=10)],
            position_bias=PositionBias(directional="long", max_position_pct=20.0),
            top_symbols=[],
            concept_tags=["AI"],
        )

    def test_rules_snapshot_populated_from_article_metadata(self, trader_profile):
        """同一 trader 同一日期的 rules_snapshot 包含该 trader 对应文章中 LLM 提取的规则"""
        articles = [
            _mock_article_with_rules(
                article_id="art-001",
                symbols=["AAPL"],
                sentiment=0.8,
                rationale="AI 主题上涨",
                strategy_rules=[
                    {
                        "rule_id": "R001",
                        "rule_text": "当RSI<30时买入",
                        "programmatic_indicators": ["rsi"],
                        "required_fields": ["rsi"],
                    },
                    {
                        "rule_id": "R002",
                        "rule_text": "MACD金叉买入",
                        "programmatic_indicators": ["macd"],
                        "required_fields": ["macd"],
                    },
                ],
            ),
        ]

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="test_trader",
            strategy_date=date(2026, 4, 29),
            profile=trader_profile,
            source_articles=articles,
        )

        assert len(version.rules_snapshot) == 2
        assert version.rules_snapshot[0]["rule_id"] == "R001"
        assert version.rules_snapshot[1]["rule_id"] == "R002"
        # 验证规则中包含来源文章信息
        assert version.rules_snapshot[0]["source_article_id"] == "art-001"
        assert version.rules_snapshot[0]["source_symbols"] == ["AAPL"]

    def test_rules_snapshot_empty_when_no_articles(self, trader_profile):
        """没有文章时 rules_snapshot 为空列表（而非 None）"""
        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="test_trader",
            strategy_date=date(2026, 4, 29),
            profile=trader_profile,
            source_articles=[],
        )

        assert version.rules_snapshot == []

    def test_rules_snapshot_empty_when_articles_have_no_rules(self, trader_profile):
        """文章没有 strategy_rules 时，rules_snapshot 为空列表"""
        articles = [
            _mock_article(
                article_id="art-001",
                symbols=["AAPL"],
                sentiment=0.8,
                rationale="AI 主题上涨",
            ),
        ]

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="test_trader",
            strategy_date=date(2026, 4, 29),
            profile=trader_profile,
            source_articles=articles,
        )

        assert version.rules_snapshot == []

    def test_rules_snapshot_contains_rule_id_and_text(self, trader_profile):
        """rules_snapshot 中的规则包含 rule_id 和 rule_text"""
        articles = [
            _mock_article_with_rules(
                article_id="art-001",
                symbols=["AAPL"],
                sentiment=0.8,
                rationale="AI 主题上涨",
                strategy_rules=[
                    {
                        "rule_id": "R003",
                        "rule_text": "PE<20时买入低估值股票",
                        "programmatic_indicators": ["pe"],
                        "required_fields": ["pe"],
                    },
                ],
            ),
        ]

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="test_trader",
            strategy_date=date(2026, 4, 29),
            profile=trader_profile,
            source_articles=articles,
        )

        assert len(version.rules_snapshot) == 1
        assert version.rules_snapshot[0]["rule_id"] == "R003"
        assert version.rules_snapshot[0]["rule_text"] == "PE<20时买入低估值股票"

    def test_multiple_articles_rules_merged(self, trader_profile):
        """多篇文章的规则应合并到 rules_snapshot"""
        articles = [
            _mock_article_with_rules(
                article_id="art-001",
                symbols=["AAPL"],
                sentiment=0.8,
                rationale="AI 主题",
                strategy_rules=[{"rule_id": "R001", "rule_text": "规则1", "programmatic_indicators": [], "required_fields": []}],
            ),
            _mock_article_with_rules(
                article_id="art-002",
                symbols=["GOOGL"],
                sentiment=0.7,
                rationale="云主题",
                strategy_rules=[
                    {"rule_id": "R002", "rule_text": "规则2", "programmatic_indicators": [], "required_fields": []},
                    {"rule_id": "R003", "rule_text": "规则3", "programmatic_indicators": [], "required_fields": []},
                ],
            ),
        ]

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="test_trader",
            strategy_date=date(2026, 4, 29),
            profile=trader_profile,
            source_articles=articles,
        )

        assert len(version.rules_snapshot) == 3
        rule_ids = {r["rule_id"] for r in version.rules_snapshot}
        assert rule_ids == {"R001", "R002", "R003"}
