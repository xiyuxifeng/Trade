import pytest
from unittest.mock import patch
from src.agents.risk_agent.agent import RiskAgent
from src.strategy.types import RawSignal, SignalSide, SynthesisMode, PositionSize, PositionSizeType
from src.risk.types import AccountSnapshot, StopLossLevel, StopLossMode
from datetime import datetime


@pytest.fixture
def risk_agent():
    return RiskAgent()


@pytest.mark.asyncio
async def test_check_pass(risk_agent):
    """测试风控检查通过的情况"""
    raw_signal = RawSignal(
        signal_id="test-id",
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=["rule1"],
        synthesis_mode=SynthesisMode.PRIORITY,
        entry_price=None,
        position_size=None,
        timestamp=datetime.utcnow(),
        metadata={}
    )

    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.utcnow(),
        net_value=100000.0,
        cash=50000.0,
        total_position_value=50000.0,
        positions=[],
        daily_pnl=0.0,
        total_pnl=0.0
    )

    # Mock skills
    async def mock_call_skill(name, **kwargs):
        if name == "drawdown_control":
            return {"passed": True, "reason": None}
        elif name == "stop_loss":
            return StopLossLevel(mode=StopLossMode.FIXED, level=95.0, trigger_condition="price <= 95")
        elif name == "position_sizing":
            return PositionSize(type=PositionSizeType.FIXED_RATIO, value=0.1, max_amount=100000.0)
        return None

    with patch.object(risk_agent, 'call_skill', side_effect=mock_call_skill):
        result = await risk_agent.check(raw_signal, account, {}, {})
        assert result.side == SignalSide.BUY
        assert result.signal_id == "test-id"
        assert result.stop_loss is not None
        assert result.position_size is not None


@pytest.mark.asyncio
async def test_check_reject_on_drawdown_failure(risk_agent):
    """测试回撤控制失败时信号被拒绝"""
    raw_signal = RawSignal(
        signal_id="test-id",
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=["rule1"],
        synthesis_mode=SynthesisMode.PRIORITY,
        entry_price=None,
        position_size=None,
        timestamp=datetime.utcnow(),
        metadata={}
    )

    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.utcnow(),
        net_value=100000.0,
        cash=50000.0,
        total_position_value=50000.0,
        positions=[],
        daily_pnl=0.0,
        total_pnl=0.0
    )

    async def mock_call_skill(name, **kwargs):
        if name == "drawdown_control":
            return {"passed": False, "reason": "drawdown exceeded"}
        return None

    with patch.object(risk_agent, 'call_skill', side_effect=mock_call_skill):
        result = await risk_agent.check(raw_signal, account, {}, {})
        assert result.side == SignalSide.HOLD
        assert result.metadata.get("rejected_reason") == "drawdown exceeded"


@pytest.mark.asyncio
async def test_check_exception_handling(risk_agent):
    """测试异常情况下的拒绝逻辑"""
    raw_signal = RawSignal(
        signal_id="test-id",
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=["rule1"],
        synthesis_mode=SynthesisMode.PRIORITY,
        entry_price=None,
        position_size=None,
        timestamp=datetime.utcnow(),
        metadata={}
    )

    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.utcnow(),
        net_value=100000.0,
        cash=50000.0,
        total_position_value=50000.0,
        positions=[],
        daily_pnl=0.0,
        total_pnl=0.0
    )

    # 模拟 drawdown_control 通过但调用其他 skill 时抛出异常
    async def mock_call_skill(name, **kwargs):
        if name == "drawdown_control":
            return {"passed": True, "reason": None}
        elif name == "stop_loss":
            raise Exception("stop loss error")
        return None

    with patch.object(risk_agent, 'call_skill', side_effect=mock_call_skill):
        result = await risk_agent.check(raw_signal, account, {}, {})
        assert result.side == SignalSide.HOLD
        assert result.metadata.get("rejected_reason") == "stop loss error"


def test_register_skills(risk_agent):
    """测试技能注册"""
    skills = risk_agent.list_skills()
    assert "drawdown_control" in skills
    assert "stop_loss" in skills
    assert "position_sizing" in skills
