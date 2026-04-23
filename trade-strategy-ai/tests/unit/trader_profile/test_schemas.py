"""trader_profile schema 测试。"""

from datetime import UTC, datetime

import pytest

from src.trader_profile.schemas import (
    PositionBias,
    RiskStyle,
    StrategyPreference,
    StrategyTimeframe,
    ThemeStat,
    TraderProfile,
)


class TestStrategyPreference:
    """策略偏好字段测试。"""

    def test_strategy_preference_fields(self):
        """StrategyPreference 包含所有必要字段。"""
        pref = StrategyPreference(
            timeframe=StrategyTimeframe.INTRADAY,
            entry_type="breakout",
            position_style="momentum",
            max_positions=5,
            avg_holding_period=0.5,
        )
        assert pref.timeframe == StrategyTimeframe.INTRADAY
        assert pref.entry_type == "breakout"
        assert pref.position_style == "momentum"
        assert pref.max_positions == 5
        assert pref.avg_holding_period == 0.5

    def test_strategy_preference_defaults(self):
        """可选字段有默认值。"""
        pref = StrategyPreference(timeframe=StrategyTimeframe.SWING)
        assert pref.entry_type is None
        assert pref.position_style is None
        assert pref.max_positions is None
        assert pref.avg_holding_period is None


class TestRiskStyle:
    """风险风格枚举测试。"""

    def test_risk_style_values(self):
        """三种风险风格值正确。"""
        assert RiskStyle.CONSERVATIVE.value == "conservative"
        assert RiskStyle.BALANCED.value == "balanced"
        assert RiskStyle.AGGRESSIVE.value == "aggressive"


class TestPositionBias:
    """仓位倾向字段测试。"""

    def test_position_bias_directional(self):
        """directional 取值正确。"""
        for bias in ("long", "short", "neutral"):
            pb = PositionBias(directional=bias)
            assert pb.directional == bias

    def test_position_bias_defaults(self):
        """可选字段有默认值。"""
        pb = PositionBias(directional="neutral")
        assert pb.max_position_pct is None
        assert pb.avg_position_pct is None


class TestThemeStat:
    """主题偏好统计测试。"""

    def test_theme_stat_fields(self):
        """ThemeStat 包含必要字段。"""
        stat = ThemeStat(theme="AI", mentions=10)
        assert stat.theme == "AI"
        assert stat.mentions == 10


class TestTraderProfile:
    """TraderProfile 聚合测试。"""

    def test_trader_profile_extended_fields(self):
        """TraderProfile 包含扩展字段。"""
        profile = TraderProfile(
            trader_id="trader-001",
            strategy_preference=StrategyPreference(
                timeframe=StrategyTimeframe.SWING,
                entry_type="mean_reversion",
            ),
            risk_style=RiskStyle.BALANCED,
            theme_preference=[
                ThemeStat(theme="AI", mentions=5),
                ThemeStat(theme="新能源", mentions=3),
            ],
            position_bias=PositionBias(directional="long"),
            evidence={"articles_scanned": 20},
        )
        assert profile.trader_id == "trader-001"
        assert profile.strategy_preference.timeframe == StrategyTimeframe.SWING
        assert profile.risk_style == RiskStyle.BALANCED
        assert len(profile.theme_preference) == 2
        assert profile.position_bias.directional == "long"

    def test_trader_profile_legacy_fields_still_work(self):
        """原有字段仍然可用。"""
        from src.trader_profile.schemas import SymbolStat

        profile = TraderProfile(
            trader_id="trader-001",
            top_symbols=[SymbolStat(symbol="000001.SZ", mentions=10)],
            concept_tags=["AI", "科技"],
        )
        assert len(profile.top_symbols) == 1
        assert profile.top_symbols[0].symbol == "000001.SZ"
        assert "AI" in profile.concept_tags