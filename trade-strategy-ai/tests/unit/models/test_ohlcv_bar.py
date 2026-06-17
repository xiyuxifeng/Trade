# tests/unit/models/test_ohlcv_bar.py
import pytest
from datetime import date
from sqlalchemy import UniqueConstraint
from src.models.ohlcv_bar import OHLCVBar


def test_ohlcv_bar_creation():
    """测试 OHLCVBar 创建"""
    bar = OHLCVBar(
        symbol="000001.SZ",
        trade_date=date(2026, 4, 28),
        open=10.0,
        high=10.5,
        low=9.8,
        close=10.2,
        volume=1000000,
    )
    assert bar.symbol == "000001.SZ"
    assert bar.trade_date == date(2026, 4, 28)
    assert bar.close == 10.2


def test_ohlcv_bar_all_fields():
    """测试 OHLCVBar 所有字段"""
    bar = OHLCVBar(
        symbol="600519.SH",
        trade_date=date(2026, 4, 28),
        open=1800.0,
        high=1850.0,
        low=1790.0,
        close=1830.0,
        volume=5000000,
        turnover=9150000000.0,
    )
    assert bar.symbol == "600519.SH"
    assert bar.open == 1800.0
    assert bar.high == 1850.0
    assert bar.low == 1790.0
    assert bar.close == 1830.0
    assert bar.volume == 5000000.0
    assert bar.turnover == 9150000000.0


def test_ohlcv_identity_constraint_includes_asset_and_adjustment_dimensions():
    constraints = [
        constraint
        for constraint in OHLCVBar.__table__.constraints
        if isinstance(constraint, UniqueConstraint) and constraint.name == "uq_ohlcv_identity_trade_date"
    ]
    assert len(constraints) == 1
    columns = {column.name for column in constraints[0].columns}
    assert columns == {"symbol", "exchange", "asset_type", "frequency", "adjustment_policy", "trade_date"}
