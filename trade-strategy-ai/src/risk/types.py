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


# ===== P4-009 单股集中度 =====

@dataclass
class ConcentrationCheck:
    """单股集中度检查结果"""
    symbol: str
    market_value: float
    net_value: float
    concentration_pct: float  # 占净值比例
    passed: bool
    limit: float  # 阈值
    trigger_condition: str  # 触发条件描述


@dataclass
class ConcentrationConfig:
    """集中度配置"""
    max_single_position_pct: float = 0.20
    max_single_position_amount: float = 50_000.0


# ===== P4-010 行业敞口 =====

@dataclass
class IndustryExposure:
    """行业敞口"""
    industry_code: str    # 申万行业代码
    industry_name: str    # 申万行业名称
    market_value: float   # 该行业持仓市值
    exposure_pct: float   # 占净值比例
    positions: list[str]  # 该行业包含的股票


@dataclass
class IndustryExposureCheck:
    """行业敞口检查结果"""
    sector_code: str
    sector_name: str
    exposure_pct: float
    passed: bool
    limit: float


@dataclass
class IndustryExposureResult:
    """行业敞口检查汇总"""
    total_exposure: float  # 已用敞口
    checks: list[IndustryExposureCheck]
    industry_map: dict[str, tuple[str, str]]  # symbol -> (一级代码, 一级名称)


@dataclass
class IndustryExposureConfig:
    """行业敞口配置"""
    max_industry_pct: float = 0.30       # 申万二级行业最大占比
    max_sector_pct: float = 0.40         # 申万一级行业最大占比
    cache_ttl_hours: int = 24             # 行业数据缓存时间


# ===== P4-011 组合风险 =====

class RiskLevel(StrEnum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PortfolioRiskMetrics:
    """组合风险指标"""
    var: float                           # Value at Risk（金额）
    var_pct: float                      # VaR 占净值比例
    volatility: float                   # 组合波动率
    leverage: float                     # 杠杆率 = 总敞口 / 净值
    net_value: float                    # 账户净值
    total_exposure: float               # 总敞口
    positions_count: int                # 持仓数量
    risk_level: RiskLevel              # 风险等级


@dataclass
class PortfolioRiskAssessment:
    """组合风险评估结果"""
    metrics: PortfolioRiskMetrics
    var_limit: float                   # VaR 限制
    volatility_limit: float             # 波动率限制
    leverage_limit: float               # 杠杆率限制
    passed: bool                        # 是否通过所有检查
    violations: list[str]               # 违规项列表


@dataclass
class PortfolioRiskConfig:
    """组合风险配置"""
    var_confidence: float = 0.95          # VaR 置信度 95%
    var_window: int = 20                   # VaR 计算窗口
    max_var_pct: float = 0.10             # 最大 VaR 占比
    max_volatility: float = 0.30          # 最大波动率 30%
    max_leverage: float = 1.0             # 最大杠杆率 100%
