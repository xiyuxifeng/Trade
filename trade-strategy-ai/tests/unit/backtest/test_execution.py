"""NTL-S6-002: 回测执行器单元测试"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from src.strategy_library.schemas import (
    StrategyRecommendation,
    StrategyVersion,
    StrategyVersionStatus,
)


class TestStrategyReplayer:
    """策略版本回放器测试"""

    def test_replay_candidates_from_strategy_version(self):
        """从 released 版本重放出 recommendations"""
        version = StrategyVersion(
            version_id="v1",
            trader_id="trader_a",
            strategy_date=date(2026, 4, 1),
            status=StrategyVersionStatus.released,
            recommendations=[
                StrategyRecommendation(
                    symbol="000001.SZ",
                    decision="buy",
                    confidence=0.8,
                    entry_price=10.0,
                    target_price=11.0,
                    stop_loss_price=9.5,
                ),
                StrategyRecommendation(
                    symbol="000002.SZ",
                    decision="sell",
                    confidence=0.6,
                ),
            ],
        )
        market_context: dict[str, Any] = {
            "trade_date": "2026-04-01",
            "bars_by_symbol": {},
            "indicators_by_symbol": {},
            "market_universe": None,
            "topic_snapshot": None,
            "source_refs": [],
        }
        from src.backtest.execution import replay_candidates

        result = replay_candidates(version, market_context)
        assert len(result) == 2
        assert result[0]["symbol"] == "000001.SZ"
        assert result[0]["decision"] == "buy"
        assert result[0]["entry_price"] == 10.0
        assert result[1]["symbol"] == "000002.SZ"
        assert result[1]["decision"] == "sell"

    def test_replay_candidates_empty_when_no_recommendations(self):
        """无 recommendations 时返回空列表"""
        version = StrategyVersion(
            version_id="v1",
            trader_id="trader_a",
            strategy_date=date(2026, 4, 1),
            status=StrategyVersionStatus.released,
            recommendations=[],
        )
        market_context: dict[str, Any] = {
            "trade_date": "2026-04-01",
            "bars_by_symbol": {},
            "indicators_by_symbol": {},
            "market_universe": None,
            "topic_snapshot": None,
            "source_refs": [],
        }
        from src.backtest.execution import replay_candidates

        result = replay_candidates(version, market_context)
        assert result == []

    def test_detect_missing_rules_snapshot_as_compatibility_gap(self):
        """rules_snapshot 为空时标记为 missing_or_legacy_gap"""
        version = StrategyVersion(
            version_id="v1",
            trader_id="trader_a",
            strategy_date=date(2026, 4, 1),
            status=StrategyVersionStatus.released,
            recommendations=[],
            rules_snapshot=[],  # 空列表
        )
        from src.backtest.execution import classify_rules_snapshot_gap

        result = classify_rules_snapshot_gap(version)
        assert result == "missing_or_legacy_gap"

    def test_detect_rules_snapshot_present(self):
        """rules_snapshot 非空时标记为 None（无 gap）"""
        version = StrategyVersion(
            version_id="v1",
            trader_id="trader_a",
            strategy_date=date(2026, 4, 1),
            status=StrategyVersionStatus.released,
            recommendations=[],
            rules_snapshot=[{"rule_id": "r1", "condition": "ma5_cross"}],
        )
        from src.backtest.execution import classify_rules_snapshot_gap

        result = classify_rules_snapshot_gap(version)
        assert result is None

    def test_rules_snapshot_none_by_default(self):
        """未设置 rules_snapshot 默认为 None（历史数据）"""
        version = StrategyVersion(
            version_id="v1",
            trader_id="trader_a",
            strategy_date=date(2026, 4, 1),
            status=StrategyVersionStatus.released,
            recommendations=[],
            rules_snapshot=None,  # 默认 None
        )
        from src.backtest.execution import classify_rules_snapshot_gap

        result = classify_rules_snapshot_gap(version)
        assert result == "missing_or_legacy_gap"


class TestExecutionConstraints:
    """交易执行约束测试"""

    def test_classify_rules_snapshot_gap_returns_string_or_none(self):
        """gap 分类结果只可能是字符串或 None"""
        for rules_snapshot in [[], [{"rule_id": "r1"}], None]:
            version = StrategyVersion(
                version_id="v1",
                trader_id="trader_a",
                strategy_date=date(2026, 4, 1),
                status=StrategyVersionStatus.released,
                recommendations=[],
                rules_snapshot=rules_snapshot,
            )
            from src.backtest.execution import classify_rules_snapshot_gap

            result = classify_rules_snapshot_gap(version)
            assert result is None or isinstance(result, str)
