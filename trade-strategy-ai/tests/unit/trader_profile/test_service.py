"""trader_profile service 测试（扩展版）。"""

from collections.abc import AsyncGenerator
from datetime import date
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.trader_profile.service import _aggregate_profile
from src.trader_profile.service import build_trader_profiles
from src.common.config import AppConfig, CrawlConfig, StorageConfig, TradeLogSourceConfig, TraderConfig
from src.trader_profile.schemas import (
    PositionBias,
    RiskStyle,
    StrategyPreference,
    StrategyTimeframe,
    SymbolStat,
    ThemeStat,
    TraderProfile,
)


class TestAggregateProfile:
    """扩展后的 _aggregate_profile 测试。"""

    def test_aggregates_strategy_preference(self):
        """能从策略规则中聚合策略偏好。"""
        # 模拟文章中抽出的策略规则，包含 timeframe / entry_type 信息
        rules_by_article = [
            [
                {"claim_key": "entry", "rule_type": "breakout", "timeframe": "swing"},
                {"claim_key": "entry", "rule_type": "momentum", "timeframe": "swing"},
            ],
            [
                {"claim_key": "exit", "rule_type": "stop_loss", "timeframe": "intraday"},
            ],
        ]
        profile = _aggregate_profile(
            trader_id="trader-001",
            symbols_by_article=[["000001.SZ"]],
            concepts_by_article=[[]],
            rules_by_article=rules_by_article,
            clusters_file=None,
        )
        assert profile.strategy_preference is not None
        # swing 出现最多（2次），应为主要的 timeframe
        assert profile.strategy_preference.timeframe == StrategyTimeframe.SWING

    def test_aggregates_risk_style(self):
        """能从策略规则中推断风险风格。"""
        # 大量日内 + 轻仓规则 → conservative
        rules_by_article = [
            [{"timeframe": "intraday", "position_size_pct": 5}],
            [{"timeframe": "intraday", "position_size_pct": 3}],
        ]
        profile = _aggregate_profile(
            trader_id="trader-001",
            symbols_by_article=[["000001.SZ"]],
            concepts_by_article=[[]],
            rules_by_article=rules_by_article,
            clusters_file=None,
        )
        assert profile.risk_style == RiskStyle.CONSERVATIVE

    def test_aggregates_theme_preference(self):
        """能从概念标签中聚合主题偏好。"""
        concepts_by_article = [
            [{"name": "AI", "type": "theme"}, {"name": "科技", "type": "theme"}, {"name": "AI", "type": "theme"}],
            [{"name": "新能源", "type": "theme"}, {"name": "AI", "type": "theme"}],
        ]
        profile = _aggregate_profile(
            trader_id="trader-001",
            symbols_by_article=[[]],
            concepts_by_article=concepts_by_article,
            rules_by_article=[],
            clusters_file=None,
        )
        assert len(profile.theme_preference) >= 1
        # AI 出现3次，应排第一
        ai_stat = next((t for t in profile.theme_preference if t.theme == "AI"), None)
        assert ai_stat is not None
        assert ai_stat.mentions == 3

    def test_aggregates_position_bias(self):
        """能从策略方向中聚合仓位倾向。"""
        rules_by_article = [
            [{"direction": "long", "position_size_pct": 20}],
            [{"direction": "long", "position_size_pct": 15}],
            [{"direction": "short", "position_size_pct": 5}],
        ]
        profile = _aggregate_profile(
            trader_id="trader-001",
            symbols_by_article=[["000001.SZ"]],
            concepts_by_article=[[]],
            rules_by_article=rules_by_article,
            clusters_file=None,
        )
        assert profile.position_bias is not None
        assert profile.position_bias.directional == "long"

    def test_legacy_fields_still_aggregated(self):
        """原有字段仍然正常聚合。"""
        symbols_by_article = [
            ["000001.SZ", "000001.SZ", "600519.SH"],
            ["000001.SZ"],
        ]
        concepts_by_article = [
            [{"name": "AI", "type": "concept"}],
            [{"name": "科技", "type": "concept"}],
        ]
        profile = _aggregate_profile(
            trader_id="trader-001",
            symbols_by_article=symbols_by_article,
            concepts_by_article=concepts_by_article,
            rules_by_article=[],
            clusters_file=None,
        )
        assert len(profile.top_symbols) >= 1
        assert profile.top_symbols[0].symbol == "000001.SZ"
        assert len(profile.concept_tags) >= 1

    def test_no_data_returns_defaults(self):
        """无数据时返回合理的默认值。"""
        profile = _aggregate_profile(
            trader_id="trader-001",
            symbols_by_article=[],
            concepts_by_article=[],
            rules_by_article=[],
            clusters_file=None,
        )
        assert profile.trader_id == "trader-001"
        assert profile.top_symbols == []
        assert profile.concept_tags == []


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, article_rows, trade_rows):
        self._results = [_FakeResult(article_rows), _FakeResult(trade_rows)]
        self._idx = 0

    async def execute(self, stmt):
        del stmt
        result = self._results[min(self._idx, len(self._results) - 1)]
        self._idx += 1
        return result


@pytest.mark.asyncio
async def test_build_trader_profiles_includes_trade_logs(tmp_path, monkeypatch):
    """build_trader_profiles 应该把 trade_logs 纳入画像主链路。"""
    article_rows = [
        ("author-1", {"trader_id": "trader-001"}, ["000001.SZ"], [], []),
    ]
    trade_rows = [
        ("acct-1", "600519.SH"),
        ("acct-1", "600519.SH"),
    ]
    session = _FakeSession(article_rows, trade_rows)

    @asynccontextmanager
    async def _fake_session_scope():
        yield session

    monkeypatch.setattr("src.trader_profile.service.session_scope", _fake_session_scope)

    config = AppConfig(
        storage=StorageConfig(output_dir="data/processed/phase0"),
        crawl=CrawlConfig(),
        traders=[
            TraderConfig(
                trader_id="trader-001",
                display_name="Trader 001",
                trade_log_sources=TradeLogSourceConfig(account_ids=["acct-1"]),
            )
        ],
    )

    profiles_file = await build_trader_profiles(config=config, base_dir=tmp_path, max_articles_per_trader=10)
    profile = profiles_file.profiles_by_trader["trader-001"]

    assert profile.top_symbols[0].symbol == "600519.SH"
    assert profile.top_symbols[0].mentions == 2
    assert profile.evidence["articles_scanned"] == 1
    assert profile.evidence["trade_logs_scanned"] == 2
