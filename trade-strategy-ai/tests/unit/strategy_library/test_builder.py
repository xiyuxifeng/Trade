"""strategy_library builder 测试。"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.strategy_library.builder import StrategyVersionBuilder
from src.strategy_library.schemas import (
    StrategyRecommendation,
    StrategyVersion,
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


class TestStrategyVersionBuilder:
    """策略版本构建器测试。"""

    def test_build_draft_version(self):
        """能构建 draft 状态的策略版本。"""
        profile = TraderProfile(
            trader_id="trader-001",
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
        # 模拟文章证据
        articles = [
            _mock_article("art-1", ["000001.SZ"], 0.8, "突破关键阻力位"),
            _mock_article("art-2", ["600519.SH"], 0.7, "业绩超预期"),
        ]

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            profile=profile,
            source_articles=articles,
        )

        assert version.trader_id == "trader-001"
        assert version.strategy_date == date(2026, 4, 23)
        assert version.status == StrategyVersionStatus.draft
        assert len(version.recommendations) == 2
        assert version.source_article_ids == ["art-1", "art-2"]

    def test_build_released_version(self):
        """能构建 released 状态的策略版本，并设置 released_at。"""
        profile = TraderProfile(
            trader_id="trader-001",
            strategy_preference=StrategyPreference(timeframe=StrategyTimeframe.INTRADAY),
            risk_style=RiskStyle.CONSERVATIVE,
            position_bias=PositionBias(directional="neutral"),
            top_symbols=[],
            concept_tags=[],
        )
        articles = [_mock_article("art-1", ["000001.SZ"], 0.9, "日内反弹")]

        builder = StrategyVersionBuilder()
        version = builder.build_released(
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            profile=profile,
            source_articles=articles,
        )

        assert version.status == StrategyVersionStatus.released
        assert version.released_at is not None

    def test_recommendations_from_articles(self):
        """每篇文章生成一条 StrategyRecommendation。"""
        profile = TraderProfile(
            trader_id="trader-001",
            strategy_preference=StrategyPreference(timeframe=StrategyTimeframe.SWING),
            risk_style=RiskStyle.BALANCED,
            position_bias=PositionBias(directional="long"),
            top_symbols=[],
            concept_tags=[],
        )
        articles = [
            _mock_article("art-1", ["000001.SZ"], 0.8, "突破"),
            _mock_article("art-2", ["000002.SZ"], 0.6, "回调"),
            _mock_article("art-3", ["600519.SH"], 0.9, "业绩"),
        ]

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            profile=profile,
            source_articles=articles,
        )

        assert len(version.recommendations) == 3
        symbols = {r.symbol for r in version.recommendations}
        assert symbols == {"000001.SZ", "000002.SZ", "600519.SH"}

    def test_recommendation_decision_based_on_sentiment(self):
        """decision (buy/sell/hold) 基于情绪分决定。"""
        profile = TraderProfile(
            trader_id="trader-001",
            strategy_preference=StrategyPreference(timeframe=StrategyTimeframe.SWING),
            risk_style=RiskStyle.BALANCED,
            position_bias=PositionBias(directional="long"),
            top_symbols=[],
            concept_tags=[],
        )
        # 正面文章 → buy
        pos_article = _mock_article("art-pos", ["000001.SZ"], 0.8, "看好")
        # 负面文章 → sell
        neg_article = _mock_article("art-neg", ["000002.SZ"], -0.7, "看空")
        # 中性文章 → hold
        neutral_article = _mock_article("art-neu", ["000003.SZ"], 0.05, "观望")

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            profile=profile,
            source_articles=[pos_article, neg_article, neutral_article],
        )

        rec_by_symbol = {r.symbol: r.decision for r in version.recommendations}
        assert rec_by_symbol["000001.SZ"] == "buy"
        assert rec_by_symbol["000002.SZ"] == "sell"
        assert rec_by_symbol["000003.SZ"] == "hold"

    def test_confidence_from_article_confidence_score(self):
        """recommendation 的 confidence 反映文章质量分。"""
        profile = TraderProfile(
            trader_id="trader-001",
            strategy_preference=StrategyPreference(timeframe=StrategyTimeframe.SWING),
            risk_style=RiskStyle.BALANCED,
            position_bias=PositionBias(directional="long"),
            top_symbols=[],
            concept_tags=[],
        )
        # confidence_score = 0.9 → 高置信度
        article = _mock_article("art-1", ["000001.SZ"], 0.8, "突破", confidence=0.9)

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            profile=profile,
            source_articles=[article],
        )

        assert version.recommendations[0].confidence == 0.9

    def test_evidence_refs_from_articles(self):
        """evidence_refs 收集所有来源引用。"""
        profile = TraderProfile(
            trader_id="trader-001",
            strategy_preference=StrategyPreference(timeframe=StrategyTimeframe.SWING),
            risk_style=RiskStyle.BALANCED,
            position_bias=PositionBias(directional="long"),
            top_symbols=[],
            concept_tags=[],
        )
        articles = [
            _mock_article("art-1", ["000001.SZ"], 0.8, "理由1"),
            _mock_article("art-2", ["000002.SZ"], 0.7, "理由2"),
        ]

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            profile=profile,
            source_articles=articles,
        )

        assert set(version.evidence_refs) == {"art-1:理由1", "art-2:理由2"}

    def test_empty_articles_returns_empty_recommendations(self):
        """无文章时返回空推荐列表。"""
        profile = TraderProfile(
            trader_id="trader-001",
            strategy_preference=StrategyPreference(timeframe=StrategyTimeframe.SWING),
            risk_style=RiskStyle.BALANCED,
            position_bias=PositionBias(directional="long"),
            top_symbols=[],
            concept_tags=[],
        )

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            profile=profile,
            source_articles=[],
        )

        assert version.recommendations == []
        assert version.source_article_ids == []

    def test_position_bias_short_overrides_buy_to_sell(self):
        """position_bias=short 时，正面情绪文章降为 sell。"""
        profile = TraderProfile(
            trader_id="trader-001",
            strategy_preference=StrategyPreference(timeframe=StrategyTimeframe.SWING),
            risk_style=RiskStyle.BALANCED,
            position_bias=PositionBias(directional="short"),
            top_symbols=[],
            concept_tags=[],
        )
        # 正面文章本应 buy
        article = _mock_article("art-1", ["000001.SZ"], 0.8, "看好突破")

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            profile=profile,
            source_articles=[article],
        )

        # short bias 将 buy 翻转为 sell
        assert version.recommendations[0].decision == "sell"

    def test_position_bias_neutral_blocks_directional_conflict(self):
        """position_bias=neutral 时，任何方向性信号都降为 hold。"""
        profile = TraderProfile(
            trader_id="trader-001",
            strategy_preference=StrategyPreference(timeframe=StrategyTimeframe.SWING),
            risk_style=RiskStyle.BALANCED,
            position_bias=PositionBias(directional="neutral"),
            top_symbols=[],
            concept_tags=[],
        )
        pos_article = _mock_article("art-1", ["000001.SZ"], 0.8, "看好")
        neg_article = _mock_article("art-2", ["000002.SZ"], -0.7, "看空")

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            profile=profile,
            source_articles=[pos_article, neg_article],
        )

        # neutral bias 将所有决策降为 hold
        for rec in version.recommendations:
            assert rec.decision == "hold"

    def test_risk_style_aggressive_no_stop_loss(self):
        """aggressive 风格不设置止损（高风险容忍）。"""
        profile = TraderProfile(
            trader_id="trader-001",
            strategy_preference=StrategyPreference(timeframe=StrategyTimeframe.SWING),
            risk_style=RiskStyle.AGGRESSIVE,
            position_bias=PositionBias(directional="long"),
            top_symbols=[],
            concept_tags=[],
        )
        article = _mock_article("art-1", ["000001.SZ"], 0.8, "激进追涨")

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            profile=profile,
            source_articles=[article],
        )

        # aggressive 不设置止损
        assert version.recommendations[0].stop_loss_price is None

    def test_risk_style_conservative_sets_stop_loss(self):
        """conservative 风格根据仓位占比设置止损。"""
        profile = TraderProfile(
            trader_id="trader-001",
            strategy_preference=StrategyPreference(timeframe=StrategyTimeframe.SWING),
            risk_style=RiskStyle.CONSERVATIVE,
            position_bias=PositionBias(directional="long", max_position_pct=20.0),
            top_symbols=[],
            concept_tags=[],
        )
        # 入场价 10.0，conservative 止损 3%（保守）
        article = _mock_article("art-1", ["000001.SZ"], 0.8, "稳健低吸", entry_price=10.0)

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            profile=profile,
            source_articles=[article],
        )

        # conservative 应设置止损
        assert version.recommendations[0].stop_loss_price is not None

    def test_strategy_preference_max_positions_limits_recommendations(self):
        """strategy_preference.max_positions 限制推荐数量。"""
        profile = TraderProfile(
            trader_id="trader-001",
            strategy_preference=StrategyPreference(
                timeframe=StrategyTimeframe.SWING,
                max_positions=2,  # 最多2个持仓
            ),
            risk_style=RiskStyle.BALANCED,
            position_bias=PositionBias(directional="long"),
            top_symbols=[],
            concept_tags=[],
        )
        articles = [
            _mock_article("art-1", ["000001.SZ"], 0.8, "标的1"),
            _mock_article("art-2", ["000002.SZ"], 0.7, "标的2"),
            _mock_article("art-3", ["600519.SH"], 0.6, "标的3"),
        ]

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            profile=profile,
            source_articles=articles,
        )

        # 限制为 max_positions=2
        assert len(version.recommendations) <= 2

    def test_theme_preference_filters_articles(self):
        """theme_preference 优先推荐匹配主题的文章。"""
        profile = TraderProfile(
            trader_id="trader-001",
            strategy_preference=StrategyPreference(timeframe=StrategyTimeframe.SWING),
            risk_style=RiskStyle.BALANCED,
            position_bias=PositionBias(directional="long"),
            top_symbols=[],
            concept_tags=[],
            theme_preference=[
                ThemeStat(theme="AI", mentions=10),
                ThemeStat(theme="新能源", mentions=3),
            ],
        )
        # AI 主题文章
        ai_article = _mock_article("art-ai", ["000001.SZ"], 0.5, "AI算力爆发")
        # 非偏好主题文章
        other_article = _mock_article("art-other", ["000002.SZ"], 0.9, "猪肉涨价")

        builder = StrategyVersionBuilder()
        version = builder.build_draft(
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            profile=profile,
            source_articles=[ai_article, other_article],
        )

        # AI 主题文章应在推荐中（高优先级）
        symbols = {r.symbol for r in version.recommendations}
        assert "000001.SZ" in symbols


def _mock_article(
    article_id: str,
    symbols: list[str],
    sentiment: float,
    rationale: str,
    confidence: float = 0.7,
    entry_price: float | None = None,
) -> MagicMock:
    """构造一个模拟文章对象。"""
    article = MagicMock()
    article.article_id = article_id
    article.trading_symbols = symbols
    article.sentiment_score = sentiment
    article.confidence_score = confidence
    article.rationale = rationale
    article.entry_price = entry_price
    return article