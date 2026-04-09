"""TakeProfitCalculator 单元测试"""
import pytest
from src.risk.take_profit import TakeProfitCalculator
from src.risk.types import TakeProfitMode, ScalingLevel, TakeProfitConfig
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


def test_fixed_take_profit():
    """测试固定止盈"""
    config = TakeProfitConfig(mode=TakeProfitMode.FIXED, fixed_pct=0.15)
    calculator = TakeProfitCalculator(config)

    signal = _create_signal(entry_price=100.0)
    market_data = {"close": 100.0}

    result = calculator.calculate(100.0, signal, market_data)
    assert len(result) == 1
    assert result[0].level == 115.0  # 100 * (1 + 0.15)
    assert result[0].mode == TakeProfitMode.FIXED


def test_scaling_take_profit():
    """测试分批止盈"""
    config = TakeProfitConfig(
        mode=TakeProfitMode.SCALING,
        scaling_levels=[
            ScalingLevel(target_pct=0.05, close_pct=0.50),
            ScalingLevel(target_pct=0.10, close_pct=0.30),
            ScalingLevel(target_pct=0.20, close_pct=0.20),
        ],
    )
    calculator = TakeProfitCalculator(config)

    signal = _create_signal(entry_price=100.0)
    market_data = {"close": 100.0}

    result = calculator.calculate(100.0, signal, market_data)
    assert len(result) == 3
    assert result[0].level == 105.0
    assert result[0].close_pct == 0.50
    assert result[1].level == 110.0
    assert result[1].close_pct == 0.30
    assert result[2].level == 120.0
    assert result[2].close_pct == 0.20


def test_trailing_take_profit():
    """测试移动止损止盈"""
    config = TakeProfitConfig(
        mode=TakeProfitMode.TRAILING,
        trailing_pct=0.05,
    )
    calculator = TakeProfitCalculator(config)

    signal = _create_signal(entry_price=100.0)
    market_data = {"close": 110.0, "high": 115.0}

    result = calculator.calculate(100.0, signal, market_data)
    assert len(result) == 1
    assert result[0].mode == TakeProfitMode.TRAILING
    # 高点 115 * (1 - 0.05) = 109.25
    assert result[0].level == 109.25


def test_time_take_profit():
    """测试时间止盈"""
    config = TakeProfitConfig(
        mode=TakeProfitMode.TIME,
        target_hold_days=5,
    )
    calculator = TakeProfitCalculator(config)

    signal = _create_signal(entry_price=100.0)
    market_data = {"close": 100.0}

    result = calculator.calculate(100.0, signal, market_data)
    assert len(result) == 1
    assert result[0].mode == TakeProfitMode.TIME
    assert "5 天" in result[0].trigger_condition