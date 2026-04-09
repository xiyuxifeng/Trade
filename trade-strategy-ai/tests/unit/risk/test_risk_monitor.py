# tests/unit/risk/test_risk_monitor.py
import pytest
import numpy as np
from unittest.mock import MagicMock
from src.risk.risk_monitor import RiskMonitor
from src.risk.types import (
    ConcentrationConfig,
    IndustryExposureConfig,
    PortfolioRiskConfig,
    AccountSnapshot,
    Position,
)
from src.alerting.models import AlertEvent, AlertLevel
from datetime import datetime


# 提供正常的历史收益率，避免波动率触发告警
NORMAL_RETURNS = np.array([0.01, -0.01, 0.005, -0.005, 0.008, -0.003, 0.012, -0.007, 0.004, -0.002])


def test_risk_monitor_no_alerts():
    """测试无告警场景"""
    mock_alert_manager = MagicMock()

    monitor = RiskMonitor(
        alert_manager=mock_alert_manager,
        concentration_config=ConcentrationConfig(),
        industry_config=IndustryExposureConfig(),
        portfolio_config=PortfolioRiskConfig(),
    )

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
    industry_map = {}

    alerts = monitor.check_and_alert(account, positions, industry_map, NORMAL_RETURNS)

    # 无违规，不应返回任何告警
    assert len(alerts) == 0


def test_risk_monitor_concentration_alert():
    """测试单股集中度超限告警"""
    mock_alert_manager = MagicMock()

    monitor = RiskMonitor(
        alert_manager=mock_alert_manager,
        concentration_config=ConcentrationConfig(max_single_position_pct=0.10),
        industry_config=IndustryExposureConfig(),
        portfolio_config=PortfolioRiskConfig(),
    )

    positions = [
        Position(symbol="000001.SZ", quantity=2000, avg_cost=10.0, current_price=11.0,
                 market_value=22000.0, unrealized_pnl=2000.0, unrealized_pnl_pct=0.10),
    ]
    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.now(),
        net_value=100000.0,
        cash=78000.0,
        total_position_value=22000.0,
        positions=positions,
        daily_pnl=2000.0,
        total_pnl=5000.0,
    )

    alerts = monitor.check_and_alert(account, positions, {}, NORMAL_RETURNS)

    assert len(alerts) == 1
    assert "集中度超限" in alerts[0].title
    assert alerts[0].level == AlertLevel.WARNING


def test_risk_monitor_industry_alert():
    """测试行业敞口超限告警"""
    mock_alert_manager = MagicMock()

    # concentration 检查：max_single_position_pct=0.40 避免触发，max_single_position_amount=100000 避免触发
    monitor = RiskMonitor(
        alert_manager=mock_alert_manager,
        concentration_config=ConcentrationConfig(max_single_position_pct=0.40, max_single_position_amount=100000.0),
        industry_config=IndustryExposureConfig(max_sector_pct=0.30),
        portfolio_config=PortfolioRiskConfig(),
    )

    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.now(),
        net_value=100000.0,
        cash=56000.0,
        total_position_value=44000.0,
        positions=[],
        daily_pnl=4000.0,
        total_pnl=5000.0,
    )
    industry_map = {"000001.SZ": ("801780", "银行")}

    # 市值 35000/100000 = 35% > 30% 行业敞口限制，< 40% 集中度限制
    positions_for_industry = [
        Position(symbol="000001.SZ", quantity=3182, avg_cost=10.0, current_price=11.0,
                 market_value=35000.0, unrealized_pnl=3182.0, unrealized_pnl_pct=0.10),
    ]
    alerts = monitor.check_and_alert(account, positions_for_industry, industry_map, NORMAL_RETURNS)

    assert len(alerts) == 1
    assert "行业敞口超限" in alerts[0].title
    assert alerts[0].level == AlertLevel.WARNING


def test_risk_monitor_portfolio_alert():
    """测试组合风险超限告警"""
    mock_alert_manager = MagicMock()

    # 设置高 concentration 阈值避免触发，专注杠杆率
    monitor = RiskMonitor(
        alert_manager=mock_alert_manager,
        concentration_config=ConcentrationConfig(max_single_position_pct=0.70, max_single_position_amount=100000.0),
        industry_config=IndustryExposureConfig(),
        portfolio_config=PortfolioRiskConfig(max_leverage=0.5, max_volatility=0.30),
    )

    # 市值 66000/100000 = 66% > 50% 杠杆率限制
    positions = [
        Position(symbol="000001.SZ", quantity=6000, avg_cost=10.0, current_price=11.0,
                 market_value=66000.0, unrealized_pnl=6000.0, unrealized_pnl_pct=0.10),
    ]
    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.now(),
        net_value=100000.0,
        cash=34000.0,
        total_position_value=66000.0,
        positions=positions,
        daily_pnl=6000.0,
        total_pnl=5000.0,
    )

    alerts = monitor.check_and_alert(account, positions, {}, NORMAL_RETURNS)

    # 只有一个杠杆率超限的告警
    assert len(alerts) == 1
    assert "组合风险超限" in alerts[0].title
    assert alerts[0].level == AlertLevel.CRITICAL
    assert "杠杆率" in alerts[0].message