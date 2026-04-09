"""Risk Agent"""
from src.risk.types import (
    Position,
    PositionSizeType,
    AccountSnapshot,
    StopLossMode,
    StopLossLevel,
    StopLossConfig,
    TakeProfitMode,
    TakeProfitLevel,
    TakeProfitConfig,
    ScalingLevel,
    # P4-009~P4-012 新增
    ConcentrationCheck,
    ConcentrationConfig,
    IndustryExposure,
    IndustryExposureCheck,
    IndustryExposureResult,
    IndustryExposureConfig,
    PortfolioRiskMetrics,
    PortfolioRiskAssessment,
    PortfolioRiskConfig,
    RiskLevel,
)
from src.risk.position_manager import PositionManager, PositionSizeMode, PositionConfig
from src.risk.stop_loss import StopLossCalculator
from src.risk.take_profit import TakeProfitCalculator
from src.risk.concentration import check_position_concentration
from src.risk.industry_exposure import check_industry_exposure, get_sw_industry
from src.risk.portfolio_risk import assess_portfolio_risk, calculate_var, classify_risk_level
from src.risk.risk_monitor import RiskMonitor

__all__ = [
    # types
    "Position",
    "PositionSizeType",
    "AccountSnapshot",
    "StopLossMode",
    "StopLossLevel",
    "StopLossConfig",
    "TakeProfitMode",
    "TakeProfitLevel",
    "TakeProfitConfig",
    "ScalingLevel",
    # P4-009~P4-012
    "ConcentrationCheck",
    "ConcentrationConfig",
    "IndustryExposure",
    "IndustryExposureCheck",
    "IndustryExposureResult",
    "IndustryExposureConfig",
    "PortfolioRiskMetrics",
    "PortfolioRiskAssessment",
    "PortfolioRiskConfig",
    "RiskLevel",
    # modules
    "PositionManager",
    "PositionSizeMode",
    "PositionConfig",
    "StopLossCalculator",
    "TakeProfitCalculator",
    "check_position_concentration",
    "check_industry_exposure",
    "get_sw_industry",
    "assess_portfolio_risk",
    "calculate_var",
    "classify_risk_level",
    "RiskMonitor",
]
