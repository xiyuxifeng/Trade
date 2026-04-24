"""Strategy Agent 类型定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from src.persona.dsl import ActionSpec


class SignalSide(StrEnum):
    """信号方向"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SynthesisMode(StrEnum):
    """信号合成模式"""
    WEIGHTED_SCORE = "weighted_score"
    VOTING = "voting"
    PRIORITY = "priority"


class PositionSizeType(StrEnum):
    """头寸类型"""
    FIXED_AMOUNT = "fixed_amount"
    FIXED_RATIO = "fixed_ratio"
    VOLATILITY_ADJUSTED = "volatility_adjusted"


@dataclass
class PriceSpec:
    """价格规格"""
    type: str  # "market", "limit", "trigger"
    value: float | None = None
    offset_pct: float | None = None


@dataclass
class PositionSize:
    """头寸规格"""
    type: PositionSizeType
    value: float  # 金额或比例
    max_amount: float | None = None


@dataclass
class RuleMatch:
    """单条规则匹配结果"""
    rule_id: str
    rule_type: str  # entry/exit/filter/sizing/risk
    matched: bool
    confidence: float  # 0-1
    action: ActionSpec


@dataclass
class SynthesisContext:
    """信号合成上下文"""
    market_state: dict[str, Any]
    features: dict[str, Any]


@dataclass
class RawSignal:
    """合成后但未经过风控的信号"""
    signal_id: str
    symbol: str
    side: SignalSide
    confidence: float
    triggered_rules: list[str]
    synthesis_mode: SynthesisMode
    entry_price: PriceSpec | None = None
    position_size: PositionSize | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Signal:
    """最终交易信号（经过风控）"""
    signal_id: str
    symbol: str
    side: SignalSide
    confidence: float
    timestamp: datetime
    triggered_rules: list[str]
    synthesis_mode: SynthesisMode
    entry_price: PriceSpec | None = None
    position_size: PositionSize | None = None
    stop_loss: Any = None  # StopLossLevel from risk module
    take_profit: Any = None  # list[TakeProfitLevel] from risk module
    version: str = "v1"
    # 策略版本追溯（NTL-S4-004）
    strategy_version_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SignalContext:
    """信号生成上下文（用于版本控制，NTL-S4-004 扩展）。

    扩展字段：
    - strategy_version_id：生成该信号所使用的策略版本 ID
    - market_universe_snapshot：市场候选池快照摘要（hot_topics / strong_symbols）
    - topic_source_ids：该信号关联的主题 ID 列表
    """
    features_snapshot: dict[str, Any]
    market_state: dict[str, Any]
    rules_snapshot: list[dict[str, Any]]
    timestamp: datetime
    # 版本化追溯字段（NTL-S4-004）
    strategy_version_id: str | None = None  # 策略版本 ID
    market_universe_snapshot: dict[str, Any] | None = None  # 候选池快照摘要
    topic_source_ids: list[str] = field(default_factory=list)  # 关联的主题 ID 列表


@dataclass
class SignalWithContext:
    """信号及其完整上下文"""
    signal: Signal
    context: SignalContext
