"""Signal 创建函数单元测试 - P4-026"""
import pytest
from datetime import datetime
from src.strategy.signal import create_signal, create_signal_from_params
from src.strategy.types import (
    RawSignal,
    Signal,
    SignalSide,
    PriceSpec,
    PositionSize,
    PositionSizeType,
)
from src.risk.types import StopLossLevel, TakeProfitLevel, StopLossMode


def test_create_signal_basic():
    """测试基本信号创建"""
    raw = RawSignal(
        signal_id="raw-001",
        symbol="TEST",
        side=SignalSide.BUY,
        confidence=0.8,
        triggered_rules=["rule1", "rule2"],
        synthesis_mode=None,
    )

    result = create_signal(raw, symbol="TEST")

    assert result.signal_id == "raw-001"
    assert result.symbol == "TEST"
    assert result.side == SignalSide.BUY
    assert result.confidence == 0.8
    assert result.triggered_rules == ["rule1", "rule2"]


def test_create_signal_with_stop_loss():
    """测试带止损的信号创建"""
    raw = RawSignal(
        signal_id="raw-002",
        symbol="TEST",
        side=SignalSide.BUY,
        confidence=0.7,
        triggered_rules=["rule1"],
        synthesis_mode=None,
    )

    stop_loss = StopLossLevel(
        mode=StopLossMode.FIXED,
        level=95.0,
        trigger_condition="fixed stop at 95",
    )

    result = create_signal(raw, stop_loss=stop_loss)

    assert result.stop_loss is not None
    assert result.stop_loss.level == 95.0


def test_create_signal_with_take_profit():
    """测试带止盈的信号创建"""
    raw = RawSignal(
        signal_id="raw-003",
        symbol="TEST",
        side=SignalSide.SELL,
        confidence=0.6,
        triggered_rules=["rule1"],
        synthesis_mode=None,
    )

    take_profit_levels = [
        TakeProfitLevel(
            mode=StopLossMode.FIXED,
            level=105.0,
            close_pct=0.5,
            trigger_condition="first target",
        ),
        TakeProfitLevel(
            mode=StopLossMode.FIXED,
            level=110.0,
            close_pct=0.5,
            trigger_condition="second target",
        ),
    ]

    result = create_signal(raw, take_profit=take_profit_levels)

    assert result.take_profit is not None
    assert len(result.take_profit) == 2


def test_create_signal_overrides_symbol():
    """测试 symbol 参数覆盖"""
    raw = RawSignal(
        signal_id="raw-004",
        symbol="ORIGINAL",
        side=SignalSide.BUY,
        confidence=0.5,
        triggered_rules=[],
        synthesis_mode=None,
    )

    result = create_signal(raw, symbol="OVERRIDE")

    assert result.symbol == "OVERRIDE"


def test_create_signal_from_params_basic():
    """测试直接参数创建信号"""
    result = create_signal_from_params(
        symbol="TEST",
        side=SignalSide.BUY,
        confidence=0.9,
        triggered_rules=["rule1", "rule2"],
    )

    assert result.symbol == "TEST"
    assert result.side == SignalSide.BUY
    assert result.confidence == 0.9
    assert result.triggered_rules == ["rule1", "rule2"]
    assert result.version == "v1"


def test_create_signal_from_params_with_price_and_size():
    """测试带价格和头寸规格的信号创建"""
    entry_price = PriceSpec(type="limit", value=100.0)
    position_size = PositionSize(type=PositionSizeType.FIXED_RATIO, value=0.1)

    result = create_signal_from_params(
        symbol="TEST",
        side=SignalSide.BUY,
        confidence=0.85,
        triggered_rules=["rule1"],
        entry_price=entry_price,
        position_size=position_size,
    )

    assert result.entry_price is not None
    assert result.entry_price.type == "limit"
    assert result.entry_price.value == 100.0
    assert result.position_size is not None
    assert result.position_size.type == PositionSizeType.FIXED_RATIO
    assert result.position_size.value == 0.1


def test_create_signal_from_params_with_metadata():
    """测试带元数据的信号创建"""
    metadata = {"source": "test", "batch_id": "123"}

    result = create_signal_from_params(
        symbol="TEST",
        side=SignalSide.SELL,
        confidence=0.75,
        triggered_rules=["rule1"],
        metadata=metadata,
    )

    assert result.metadata == metadata


def test_create_signal_from_params_hold():
    """测试 HOLD 信号创建"""
    result = create_signal_from_params(
        symbol="TEST",
        side=SignalSide.HOLD,
        confidence=0.0,
        triggered_rules=[],
    )

    assert result.side == SignalSide.HOLD
    assert result.confidence == 0.0