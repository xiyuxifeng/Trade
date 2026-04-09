# tests/unit/risk/test_portfolio_risk.py
import pytest
import numpy as np
from src.risk.portfolio_risk import assess_portfolio_risk, calculate_var, classify_risk_level, PortfolioRiskConfig
from src.risk.types import PortfolioRiskAssessment, AccountSnapshot, Position, RiskLevel
from datetime import datetime


def test_assess_portfolio_risk_pass():
    """测试组合风险在限制内"""
    positions = [
        Position(symbol="000001.SZ", quantity=1000, avg_cost=10.0, current_price=11.0,
                 market_value=11000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.10),
    ]
    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.now(),
        net_value=100000.0,
        cash=89000.0,
        total_position_value=11000.0,
        positions=positions,
        daily_pnl=1000.0,
        total_pnl=5000.0,
    )
    config = PortfolioRiskConfig(
        max_var_pct=0.20,
        max_volatility=0.30,
        max_leverage=1.0,
    )
    historical_returns = np.array([0.01, -0.02, 0.015, -0.01, 0.005])

    result = assess_portfolio_risk(positions, account, historical_returns, config)

    assert isinstance(result, PortfolioRiskAssessment)
    assert result.passed is True
    assert result.metrics.positions_count == 1


def test_assess_portfolio_risk_leverage_fail():
    """测试杠杆率超过限制"""
    positions = [
        Position(symbol="000001.SZ", quantity=5000, avg_cost=10.0, current_price=11.0,
                 market_value=55000.0, unrealized_pnl=5000.0, unrealized_pnl_pct=0.10),
    ]
    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.now(),
        net_value=50000.0,  # 低净值高持仓
        cash=-5000.0,
        total_position_value=55000.0,
        positions=positions,
        daily_pnl=5000.0,
        total_pnl=5000.0,
    )
    config = PortfolioRiskConfig(max_leverage=1.0)

    result = assess_portfolio_risk(positions, account, None, config)

    assert result.passed is False
    assert any("杠杆率" in v for v in result.violations)


def test_calculate_var():
    """测试 VaR 计算"""
    returns = np.array([0.01, -0.02, 0.015, -0.01, 0.005, -0.03, 0.02, 0.01, -0.015, 0.025])
    positions = [
        Position(symbol="000001.SZ", quantity=1000, avg_cost=10.0, current_price=11.0,
                 market_value=11000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.10),
    ]
    var = calculate_var(positions, returns, confidence=0.95, window=10)

    # VaR 应该是 95% 分位数（5% 分位数）的绝对值 * 总敞口
    expected_var_pct = abs(np.percentile(returns, 5))
    expected_var = expected_var_pct * 11000.0
    assert abs(var - expected_var) < 0.001


def test_risk_level_classification():
    """测试风险等级分类"""
    assert classify_risk_level(0.02, 0.05, 0.5) == RiskLevel.LOW  # all below thresholds
    assert classify_risk_level(0.05, 0.15, 0.7) == RiskLevel.MEDIUM  # var_pct >= 0.03
    assert classify_risk_level(0.12, 0.25, 0.9) == RiskLevel.HIGH  # var_pct >= 0.08
    assert classify_risk_level(0.20, 0.40, 1.5) == RiskLevel.CRITICAL  # var_pct >= 0.15