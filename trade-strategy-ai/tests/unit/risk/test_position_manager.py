"""PositionManager 单元测试"""
import pytest
from datetime import date
from src.risk.position_manager import PositionManager, PositionConfig
from src.risk.types import AccountSnapshot, Position, PositionSizeType
from src.strategy.types import Signal, SignalSide, PositionSize, PriceSpec


def _create_account_snapshot(net_value: float = 100_000.0) -> AccountSnapshot:
    """创建样本账户快照"""
    return AccountSnapshot(
        account_id="test-account",
        timestamp=date(2026, 4, 9),
        net_value=net_value,
        cash=net_value,
        total_position_value=0.0,
        positions=[],
        daily_pnl=0.0,
        total_pnl=0.0,
    )


def _create_signal(side: SignalSide = SignalSide.BUY) -> Signal:
    """创建样本信号"""
    return Signal(
        signal_id="test-001",
        symbol="TEST",
        side=side,
        confidence=0.8,
        timestamp=date(2026, 4, 9),
        triggered_rules=[],
        synthesis_mode=None,
        entry_price=PriceSpec(type="market", value=100.0),
        position_size=PositionSize(
            type=PositionSizeType.FIXED_RATIO,
            value=0.05,
        ),
    )


def test_fixed_ratio_mode():
    """测试固定比例模式"""
    config = PositionConfig(fixed_ratio_pct=0.10)  # 10%
    manager = PositionManager(mode=PositionSizeType.FIXED_RATIO, config=config)

    account = _create_account_snapshot(net_value=100_000.0)
    signal = _create_signal()
    market_data = {"close": 100.0}

    result = manager.calculate_size(signal, account, market_data)
    # 100000 * 0.10 / 100 = 100 股
    assert result.value == 100.0


def test_fixed_amount_mode():
    """测试固定金额模式"""
    config = PositionConfig(fixed_amount=20_000.0)
    manager = PositionManager(mode=PositionSizeType.FIXED_AMOUNT, config=config)

    account = _create_account_snapshot(net_value=100_000.0)
    signal = _create_signal()
    market_data = {"close": 100.0}

    result = manager.calculate_size(signal, account, market_data)
    # 20000 / 100 = 200 股
    assert result.value == 200.0


def test_max_position_limit():
    """测试最大头寸限制"""
    config = PositionConfig(
        fixed_ratio_pct=1.0,  # 100%
        max_single_position=10_000.0,  # 但最大单标的不超过 10000
    )
    manager = PositionManager(mode=PositionSizeType.FIXED_RATIO, config=config)

    account = _create_account_snapshot(net_value=100_000.0)
    signal = _create_signal()
    market_data = {"close": 10.0}  # 价格低，头寸会超过限制

    result = manager.calculate_size(signal, account, market_data)
    # 10000 / 10 = 1000 股
    assert result.value == 1000.0


def test_hold_signal_returns_zero():
    """测试 HOLD 信号返回零头寸"""
    config = PositionConfig()
    manager = PositionManager(mode=PositionSizeType.FIXED_RATIO, config=config)

    account = _create_account_snapshot()
    signal = _create_signal(SignalSide.HOLD)
    market_data = {"close": 100.0}

    result = manager.calculate_size(signal, account, market_data)
    assert result.value == 0.0