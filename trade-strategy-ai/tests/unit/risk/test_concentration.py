# tests/unit/risk/test_concentration.py
import pytest
from src.risk.concentration import check_position_concentration, ConcentrationConfig
from src.risk.types import Position


def test_concentration_pass():
    """测试集中度在限制内的情况"""
    positions = [
        Position(symbol="000001.SZ", quantity=1000, avg_cost=10.0, current_price=11.0,
                 market_value=11000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.10),
    ]
    config = ConcentrationConfig(max_single_position_pct=0.20, max_single_position_amount=50000.0)
    results = check_position_concentration(positions, net_value=100000.0, config=config)

    assert len(results) == 1
    assert results[0].passed is True
    assert results[0].symbol == "000001.SZ"
    assert results[0].concentration_pct == 0.11


def test_concentration_fail_pct():
    """测试集中度超过百分比限制"""
    positions = [
        Position(symbol="000001.SZ", quantity=5000, avg_cost=10.0, current_price=11.0,
                 market_value=55000.0, unrealized_pnl=5000.0, unrealized_pnl_pct=0.10),
    ]
    config = ConcentrationConfig(max_single_position_pct=0.20, max_single_position_amount=50000.0)
    results = check_position_concentration(positions, net_value=100000.0, config=config)

    assert len(results) == 1
    assert results[0].passed is False
    assert "超过限制" in results[0].trigger_condition


def test_concentration_fail_amount():
    """测试集中度超过金额限制"""
    positions = [
        Position(symbol="000001.SZ", quantity=6000, avg_cost=10.0, current_price=11.0,
                 market_value=66000.0, unrealized_pnl=6000.0, unrealized_pnl_pct=0.10),
    ]
    config = ConcentrationConfig(max_single_position_pct=0.20, max_single_position_amount=50000.0)
    results = check_position_concentration(positions, net_value=1000000.0, config=config)

    assert len(results) == 1
    assert results[0].passed is False


def test_multiple_positions():
    """测试多个持仓"""
    positions = [
        Position(symbol="000001.SZ", quantity=1000, avg_cost=10.0, current_price=11.0,
                 market_value=11000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.10),
        Position(symbol="000002.SZ", quantity=2000, avg_cost=20.0, current_price=21.0,
                 market_value=42000.0, unrealized_pnl=2000.0, unrealized_pnl_pct=0.05),
    ]
    config = ConcentrationConfig(max_single_position_pct=0.20, max_single_position_amount=50000.0)
    results = check_position_concentration(positions, net_value=100000.0, config=config)

    assert len(results) == 2
    assert results[0].passed is True   # 11% < 20%
    assert results[1].passed is False  # 42% > 20%