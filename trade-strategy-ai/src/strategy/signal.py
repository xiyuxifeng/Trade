"""信号输出 - P4-004"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from src.strategy.types import (
    RawSignal,
    Signal,
    SignalSide,
    PriceSpec,
    PositionSize,
)
from src.risk.types import StopLossLevel, TakeProfitLevel


def create_signal(
    raw: RawSignal,
    stop_loss: StopLossLevel | None = None,
    take_profit: list[TakeProfitLevel] | None = None,
    symbol: str | None = None,
) -> Signal:
    """从 RawSignal 创建最终 Signal

    Args:
        raw: 原始信号
        stop_loss: 止损级别
        take_profit: 止盈级别列表
        symbol: 标的代码

    Returns:
        Signal 最终信号
    """
    return Signal(
        signal_id=raw.signal_id,
        symbol=symbol or raw.symbol,
        side=raw.side,
        confidence=raw.confidence,
        timestamp=raw.timestamp or datetime.now(),
        triggered_rules=raw.triggered_rules,
        synthesis_mode=raw.synthesis_mode,
        entry_price=raw.entry_price,
        position_size=raw.position_size,
        stop_loss=stop_loss,
        take_profit=take_profit,
        version="v1",
        metadata=raw.metadata,
    )


def create_signal_from_params(
    symbol: str,
    side: SignalSide,
    confidence: float,
    triggered_rules: list[str],
    entry_price: PriceSpec | None = None,
    position_size: PositionSize | None = None,
    stop_loss: StopLossLevel | None = None,
    take_profit: list[TakeProfitLevel] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Signal:
    """直接创建信号（不经过 RawSignal）

    Args:
        symbol: 标的代码
        side: 信号方向
        confidence: 置信度
        triggered_rules: 触发的规则 ID 列表
        entry_price: 入场价格规格
        position_size: 头寸规格
        stop_loss: 止损级别
        take_profit: 止盈级别列表
        metadata: 元数据

    Returns:
        Signal 最终信号
    """
    return Signal(
        signal_id=str(uuid.uuid4()),
        symbol=symbol,
        side=side,
        confidence=confidence,
        timestamp=datetime.now(),
        triggered_rules=triggered_rules,
        synthesis_mode=None,  # 直接创建时无合成模式
        entry_price=entry_price,
        position_size=position_size,
        stop_loss=stop_loss,
        take_profit=take_profit,
        version="v1",
        metadata=metadata or {},
    )
