"""风控配置加载"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from src.common.config import load_app_config
from src.common.paths import resolve_project_path
from src.risk.types import (
    PositionSizeType,
    StopLossMode,
    TakeProfitMode,
    ScalingLevel,
    ConcentrationConfig,
    IndustryExposureConfig,
    PortfolioRiskConfig,
)


class PositionManagerConfig(BaseModel):
    """头寸管理器配置"""
    mode: str = "fixed_ratio"
    fixed_amount: float = 10_000.0
    fixed_ratio_pct: float = 0.05
    target_volatility: float = 0.15
    max_position_pct: float = 0.20
    max_single_position: float = 50_000.0


class StopLossConfigModel(BaseModel):
    """止损配置"""
    mode: str = "volatility"
    fixed_pct: float = 0.05
    atr_multiplier: float = 2.0
    atr_window: int = 14
    drawdown_pct: float = 0.10
    max_hold_days: int = 10


class TakeProfitConfigModel(BaseModel):
    """止盈配置"""
    mode: str = "scaling"
    fixed_pct: float = 0.15
    scaling_levels: list[ScalingLevel] = Field(default_factory=lambda: [
        ScalingLevel(target_pct=0.05, close_pct=0.50),
        ScalingLevel(target_pct=0.10, close_pct=0.30),
        ScalingLevel(target_pct=0.20, close_pct=0.20),
    ])
    trailing_pct: float = 0.05
    target_hold_days: int = 5


class SimulatedAccountConfig(BaseModel):
    """模拟账户配置"""
    enabled: bool = True
    initial_capital: float = 100_000.0
    persist_to_db: bool = True


class RiskConfig(BaseModel):
    """风控配置"""
    position_manager: PositionManagerConfig = PositionManagerConfig()
    stop_loss: StopLossConfigModel = StopLossConfigModel()
    take_profit: TakeProfitConfigModel = TakeProfitConfigModel()
    simulated_account: SimulatedAccountConfig = SimulatedAccountConfig()
    # P4-009~P4-012 新增
    concentration: ConcentrationConfig = ConcentrationConfig()
    industry: IndustryExposureConfig = IndustryExposureConfig()
    portfolio: PortfolioRiskConfig = PortfolioRiskConfig()


@lru_cache
def get_risk_config() -> RiskConfig:
    """获取风控配置（单例）

    优先从 config/app.yaml 读取 risk section；兼容独立 risk.yaml。
    """
    config_path = resolve_project_path("config/app.yaml")
    loaded = load_app_config(config_path)
    return RiskConfig.model_validate(loaded.config.risk or {})


def load_risk_config(config_path: str | Path) -> RiskConfig:
    """从指定路径加载风控配置"""
    path = resolve_project_path(config_path)
    if not path.exists():
        return RiskConfig()

    loaded = load_app_config(path)
    return RiskConfig.model_validate(loaded.config.risk or {})
