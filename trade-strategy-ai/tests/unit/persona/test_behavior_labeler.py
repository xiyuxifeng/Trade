"""Tests for BehaviorLabeler (P2-009)."""

from __future__ import annotations

import sys
sys.path.insert(0, "src")

from decimal import Decimal
from datetime import datetime

from src.models.trade_log import TradeLog
from src.models.market_data import MarketData
from src.persona.behavior_labeler import ContextBuilder, RuleCondition, Rule, RuleBasedClassifier
from src.persona.behavior import BehaviorLabel


def test_compute_price_vs_ma():
    """价格 vs MA20 比率计算正确。"""
    bars = [
        MarketData(symbol="000001", market="SZ", timeframe="1d",
                   traded_at=datetime(2026, 4, 1),
                   open=Decimal("10"), high=Decimal("10.5"), low=Decimal("9.5"),
                   close=Decimal("10"), volume=Decimal("1000")),
        MarketData(symbol="000001", market="SZ", timeframe="1d",
                   traded_at=datetime(2026, 4, 3),
                   open=Decimal("10.2"), high=Decimal("10.8"), low=Decimal("10"),
                   close=Decimal("10.5"), volume=Decimal("1200")),
    ]
    trade = TradeLog(
        source="test", account_id="acc1", symbol="000001", market="SZ",
        side="buy", position_side="long", executed_at=datetime(2026, 4, 3, 14, 30),
        quantity=Decimal("100"), price=Decimal("10.5"), amount=Decimal("1050"),
        fee=Decimal("1"),
    )

    builder = ContextBuilder()
    ctx = builder.build(trade, bars)

    # price_vs_ma = trade_price / avg_close(10, 10.5) = 10.5 / 10.25 ≈ 1.024
    assert "price_vs_ma" in ctx["features"]
    assert abs(ctx["features"]["price_vs_ma"] - 1.024) < 0.01


def test_context_requires_minimum_bars():
    """K线数据不足时返回默认值。"""
    trade = TradeLog(
        source="test", account_id="acc1", symbol="000001", market="SZ",
        side="buy", position_side="long", executed_at=datetime(2026, 4, 3, 14, 30),
        quantity=Decimal("100"), price=Decimal("10.5"), amount=Decimal("1050"),
        fee=Decimal("1"),
    )

    builder = ContextBuilder()
    ctx = builder.build(trade, [])  # 无 K线数据

    assert ctx["features"]["price_vs_ma"] == 1.0  # 默认值


def test_rule_condition_gt():
    """gt 比较器工作正常。"""
    trade = None
    ctx = {"trade": trade, "bars": [], "features": {"price_vs_ma": 1.1}}

    # 规则：price_vs_ma > 1.02
    cond = RuleCondition(field="price_vs_ma", op="gt", value=1.02)
    assert cond.evaluate(ctx) is True

    cond2 = RuleCondition(field="price_vs_ma", op="gt", value=1.2)
    assert cond2.evaluate(ctx) is False


def test_rule_condition_lt():
    """lt 比较器工作正常。"""
    ctx = {"trade": None, "bars": [], "features": {"distance_from_high": 0.15}}

    cond = RuleCondition(field="distance_from_high", op="lt", value=0.1)
    assert cond.evaluate(ctx) is False

    cond2 = RuleCondition(field="distance_from_high", op="lt", value=0.2)
    assert cond2.evaluate(ctx) is True


def test_rule_all_conditions_must_match():
    """AND 逻辑：所有条件都匹配才算匹配。"""
    ctx = {"trade": None, "bars": [], "features": {"price_vs_ma": 1.1, "volume_ratio": 2.0}}

    rule = Rule(
        label=BehaviorLabel.CHASE_RALLY,
        conditions=[
            RuleCondition(field="price_vs_ma", op="gt", value=1.02),
            RuleCondition(field="volume_ratio", op="gt", value=1.5),
        ],
    )
    assert rule.matches(ctx) is True

    rule2 = Rule(
        label=BehaviorLabel.CHASE_RALLY,
        conditions=[
            RuleCondition(field="price_vs_ma", op="gt", value=1.02),
            RuleCondition(field="volume_ratio", op="gt", value=3.0),  # 不满足
        ],
    )
    assert rule2.matches(ctx) is False


def test_classifier_unknown_when_no_match():
    """无规则匹配时返回 UNKNOWN。"""
    classifier = RuleBasedClassifier("config/rules/behavior_rules.yaml")
    ctx = {"trade": None, "bars": [], "features": {"price_vs_ma": 1.0, "volume_ratio": 1.0}}

    result = classifier.classify(ctx)
    assert result.label == BehaviorLabel.UNKNOWN


def test_labeler_facade():
    """BehaviorLabeler 提供统一入口。"""
    from src.persona.behavior_labeler import BehaviorLabeler

    bars = [
        MarketData(symbol="000001", market="SZ", timeframe="1d",
                   traded_at=datetime(2026, 4, 1),
                   open=Decimal("10"), high=Decimal("10.5"), low=Decimal("9.5"),
                   close=Decimal("10"), volume=Decimal("1000")),
        MarketData(symbol="000001", market="SZ", timeframe="1d",
                   traded_at=datetime(2026, 4, 2),
                   open=Decimal("10.1"), high=Decimal("10.6"), low=Decimal("10"),
                   close=Decimal("10.4"), volume=Decimal("1100")),
        MarketData(symbol="000001", market="SZ", timeframe="1d",
                   traded_at=datetime(2026, 4, 3),
                   open=Decimal("10.3"), high=Decimal("10.8"), low=Decimal("10.2"),
                   close=Decimal("10.6"), volume=Decimal("1500")),
    ]

    trade = TradeLog(
        source="test", account_id="acc1", symbol="000001", market="SZ",
        side="buy", position_side="long",
        executed_at=datetime(2026, 4, 3, 14, 30),
        quantity=Decimal("100"), price=Decimal("10.6"), amount=Decimal("1060"),
        fee=Decimal("1"),
    )

    labeler = BehaviorLabeler(rules_path="config/rules/behavior_rules.yaml")
    pattern = labeler.label(trade, bars)

    assert isinstance(pattern.label, BehaviorLabel)
    assert isinstance(pattern.confidence, float)


def test_labeler_unknown():
    """无特征时返回 UNKNOWN。"""
    from src.persona.behavior_labeler import BehaviorLabeler

    trade = TradeLog(
        source="test", account_id="acc1", symbol="000001", market="SZ",
        side="buy", position_side="long",
        executed_at=datetime(2026, 4, 3, 14, 30),
        quantity=Decimal("100"), price=Decimal("10"), amount=Decimal("1000"),
        fee=Decimal("1"),
    )

    labeler = BehaviorLabeler(rules_path="config/rules/behavior_rules.yaml")
    pattern = labeler.label(trade, [])  # 无 K线

    assert pattern.label == BehaviorLabel.UNKNOWN