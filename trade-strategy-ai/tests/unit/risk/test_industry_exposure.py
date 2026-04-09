# tests/unit/risk/test_industry_exposure.py
import pytest
from src.risk.industry_exposure import check_industry_exposure, IndustryExposureConfig
from src.risk.types import IndustryExposureResult, Position


def test_industry_exposure_pass():
    """测试行业敞口在限制内"""
    positions = [
        Position(symbol="000001.SZ", quantity=1000, avg_cost=10.0, current_price=11.0,
                 market_value=11000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.10),
        Position(symbol="000002.SZ", quantity=1000, avg_cost=20.0, current_price=21.0,
                 market_value=21000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.05),
    ]
    # 申万一级行业：银行
    industry_map = {
        "000001.SZ": ("801780", "银行"),
        "000002.SZ": ("801780", "银行"),
    }
    config = IndustryExposureConfig(max_sector_pct=0.40)
    result = check_industry_exposure(positions, industry_map, net_value=100000.0, config=config)

    assert isinstance(result, IndustryExposureResult)
    # 32000/100000 = 32% < 40%, 应该通过
    assert result.checks[0].passed is True


def test_industry_exposure_fail():
    """测试行业敞口超过限制"""
    positions = [
        Position(symbol="000001.SZ", quantity=5000, avg_cost=10.0, current_price=11.0,
                 market_value=55000.0, unrealized_pnl=5000.0, unrealized_pnl_pct=0.10),
    ]
    industry_map = {
        "000001.SZ": ("801780", "银行"),
    }
    config = IndustryExposureConfig(max_sector_pct=0.40)
    result = check_industry_exposure(positions, industry_map, net_value=100000.0, config=config)

    # 55000/100000 = 55% > 40%, 应该失败
    assert result.checks[0].passed is False
    assert result.checks[0].exposure_pct == 0.55


def test_multiple_industries():
    """测试多个行业"""
    positions = [
        Position(symbol="000001.SZ", quantity=1000, avg_cost=10.0, current_price=11.0,
                 market_value=11000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.10),
        Position(symbol="600000.SH", quantity=1000, avg_cost=20.0, current_price=21.0,
                 market_value=21000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.05),
    ]
    industry_map = {
        "000001.SZ": ("801780", "银行"),
        "600000.SH": ("801780", "银行"),
    }
    config = IndustryExposureConfig(max_sector_pct=0.40)
    result = check_industry_exposure(positions, industry_map, net_value=100000.0, config=config)

    assert len(result.checks) == 1  # 只有一个行业
    assert result.checks[0].passed is True  # 32% < 40%