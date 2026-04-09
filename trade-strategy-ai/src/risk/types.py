"""Risk Agent 类型定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class PositionSizeType(StrEnum):
    """头寸类型"""
    FIXED_AMOUNT = "fixed_amount"
    FIXED_RATIO = "fixed_ratio"
    VOLATILITY_ADJUSTED = "volatility_adjusted"


class StopLossMode(StrEnum):
    """止损模式"""
    FIXED = "fixed"
    VOLATILITY = "volatility"
    TRAILING = "trailing"
    TIME = "time"


class TakeProfitMode(StrEnum):
    """止盈模式"""
    FIXED = "fixed"
    SCALING = "scaling"
    TRAILING = "trailing"
    TIME = "time"


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


@dataclass
class AccountSnapshot:
    """账户快照"""
    account_id: str
    timestamp: datetime
    net_value: float
    cash: float
    total_position_value: float
    positions: list[Position]
    daily_pnl: float
    total_pnl: float


@dataclass
class ScalingLevel:
    """分批止盈级别"""
    target_pct: float  # 目标涨幅
    close_pct: float   # 卖出比例（0-1）


@dataclass
class StopLossLevel:
    """止损级别"""
    mode: StopLossMode
    level: float  # 止损价格
    trigger_condition: str  # 触发条件描述


@dataclass
class TakeProfitLevel:
    """止盈级别"""
    mode: TakeProfitMode
    level: float  # 目标价格
    close_pct: float  # 卖出比例（分批止盈用）
    trigger_condition: str  # 触发条件描述


@dataclass
class StopLossConfig:
    """止损配置"""
    default_mode: StopLossMode = StopLossMode.FIXED
    default_level: float = 0.05  # 默认止损幅度 5%
    trailing_distance: float = 0.03  # 追踪止损距离 3%
    time_based_minutes: int = 60  # 时间止损（分钟）
    levels: list[StopLossLevel] = field(default_factory=list)  # 分级止损


@dataclass
class TakeProfitConfig:
    """止盈配置"""
    mode: TakeProfitMode = TakeProfitMode.SCALING
    # 固定止盈
    fixed_pct: float = 0.15  # 15%
    # 分批止盈
    scaling_levels: list[ScalingLevel] = field(default_factory=lambda: [
        ScalingLevel(target_pct=0.05, close_pct=0.50),
        ScalingLevel(target_pct=0.10, close_pct=0.30),
        ScalingLevel(target_pct=0.20, close_pct=0.20),
    ])
    # 移动止损
    trailing_pct: float = 0.05
    # 时间止盈
    target_hold_days: int = 5
