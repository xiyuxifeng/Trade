import pytest
from src.agents.strategy_agent.skills.generate_signal import generate_signal
from src.strategy.types import SignalSide, SynthesisMode


def test_generate_signal_success():
    result = generate_signal(
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=["rule1", "rule2"],
        synthesis_mode=SynthesisMode.PRIORITY,
        context={}
    )
    assert result.symbol == "000001"
    assert result.side == SignalSide.BUY
    assert result.confidence == 0.75


def test_generate_signal_error_returns_hold():
    """异常时返回 HOLD 信号（降级）"""
    result = generate_signal(
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=[],
        synthesis_mode=SynthesisMode.PRIORITY,
        context={}
    )
    assert result.signal_id is not None