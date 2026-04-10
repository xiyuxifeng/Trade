import pytest
from unittest.mock import patch, MagicMock
from src.agents.strategy_agent.agent import StrategyAgent
from src.strategy.types import SignalSide, SynthesisMode, RawSignal
from datetime import datetime


@pytest.fixture
def strategy_agent():
    return StrategyAgent()


@pytest.mark.asyncio
async def test_generate_raw_signal_success(strategy_agent):
    mock_signal = RawSignal(
        signal_id="test-signal-123",
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=[],
        synthesis_mode=SynthesisMode.PRIORITY,
        timestamp=datetime.now()
    )

    def mock_call_skill(name, **kw):
        skill_returns = {
            "compute_features": {"rsi": 30.0},
            "evaluate_rules": [],
            "combine_scores": {"side": SignalSide.BUY, "confidence": 0.75, "triggered_rules": []},
            "generate_signal": mock_signal
        }
        return skill_returns.get(name)

    with patch.object(strategy_agent, 'call_skill', side_effect=mock_call_skill):
        result = await strategy_agent.generate_raw_signal(
            symbol="000001",
            trade_idea=None,
            market_data={},
            features={},
            rules=[]
        )
        assert result.symbol == "000001"
        assert result.side == SignalSide.BUY
