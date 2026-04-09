"""StopLossCalculator 单元测试"""
import pytest
from src.risk.stop_loss import StopLossCalculator, StopLossConfig
from src.risk.types import StopLossMode, StopLossLevel
from src.strategy.types import Signal, SignalSide, PriceSpec, PositionSize, PositionSizeType
from datetime import date


def _create_signal(entry_price: float = 100.0) -> Signal:
    """创建样本信号"""
    return Signal(
        signal_id="test-001",
        symbol="TEST",
        side=SignalSide.BUY,
        confidence=0.8,
        timestamp=date(2026, 4, 9),
        triggered_rules=[],
        synthesis_mode=None,
        entry_price=PriceSpec(type="market", value=entry_price),
        position_size=PositionSize(
            type=PositionSizeType.FIXED_RATIO,
            value=100.0,
        ),
    )


def test_fixed_stop_loss():
    """测试固定止损"""
    config = StopLossConfig(mode=StopLossMode.FIXED, fixed_pct=0.05)
    calculator = StopLossCalculator(config)

    signal = _create_signal(entry_price=100.0)
    market_data = {"close": 100.0}

    result = calculator.calculate(100.0, signal, market_data)
    assert result is not None
    assert result.level == 95.0  # 100 * (1 - 0.05)
    assert result.mode == StopLossMode.FIXED


def test_volatility_stop_loss():
    """测试波动率止损"""
    config = StopLossConfig(
        mode=StopLossMode.VOLATILITY,
        atr_multiplier=2.0,
        atr_window=14,
    )
    calculator = StopLossCalculator(config)

    signal = _create_signal(entry_price=100.0)
    market_data = {"close": 100.0, "atr": 2.0}

    result = calculator.calculate(100.0, signal, market_data)
    assert result is not None
    assert result.level == 96.0  # 100 - 2 * 2.0
    assert result.mode == StopLossMode.VOLATILITY


def test_time_stop_loss():
    """测试时间止损"""
    config = StopLossConfig(mode=StopLossMode.TIME, max_hold_days=10)
    calculator = StopLossCalculator(config)

    signal = _create_signal(entry_price=100.0)
    market_data = {"close": 100.0}

    result = calculator.calculate(100.0, signal, market_data)
    assert result is not None
    assert result.mode == StopLossMode.TIME