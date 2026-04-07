"""Tests for BehaviorLabeler (P2-009)."""

from __future__ import annotations

import sys
sys.path.insert(0, "src")

from decimal import Decimal
from datetime import datetime

from src.models.trade_log import TradeLog
from src.models.market_data import MarketData
from src.persona.behavior_labeler import ContextBuilder


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