"""风控配置加载"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.risk.types import (
    PositionSizeType,
    StopLossMode,
    TakeProfitMode,
    ScalingLevel,
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


@lru_cache
def get_risk_config() -> RiskConfig:
    """获取风控配置（单例）

    从 config/risk.yaml 加载配置
    """
    config_path = Path("config/risk.yaml")
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return RiskConfig(**data)
    return RiskConfig()


def load_risk_config(config_path: str | Path) -> RiskConfig:
    """从指定路径加载风控配置"""
    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return RiskConfig(**data)
    return RiskConfig()