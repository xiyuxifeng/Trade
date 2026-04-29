# tests/unit/models/test_indicator.py
import pytest
from datetime import date
from src.models.indicator import Indicator


def test_indicator_creation():
    """测试 Indicator 创建"""
    ind = Indicator(
        symbol="000001.SZ",
        trade_date=date(2026, 4, 28),
        rsi=65.5,
        macd_histogram=0.12,
        bb_width=0.05,
        cci=120.0,
        ma50=10.2,
        ma200=9.8,
    )
    assert ind.symbol == "000001.SZ"
    assert ind.rsi == 65.5
    assert ind.macd_histogram == 0.12
    assert ind.bb_width == 0.05


def test_indicator_all_fields():
    """测试 Indicator 所有字段"""
    from datetime import datetime
    ind = Indicator(
        symbol="600519.SH",
        trade_date=date(2026, 4, 28),
        rsi=70.0,
        macd_histogram=0.15,
        bb_width=0.04,
        cci=150.0,
        ma50=1800.0,
        ma200=1750.0,
        stoch_k=80.0,
        volume_ratio=1.5,
        price_vs_ma=1.02,
        atr_ratio=0.03,
        close_position=0.7,
        computed_at=datetime.now(),
    )
    assert ind.symbol == "600519.SH"
    assert ind.rsi == 70.0
    assert ind.stoch_k == 80.0
    assert ind.volume_ratio == 1.5
    assert ind.price_vs_ma == 1.02
