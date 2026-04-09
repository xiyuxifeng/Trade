"""Agent 集成测试"""
import pytest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from src.agents.manager_agent.agent import ManagerAgent
from src.agents.strategy_agent.agent import StrategyAgent
from src.agents.risk_agent.agent import RiskAgent
from src.strategy.types import (
    Signal,
    SignalSide,
    SynthesisMode,
    RawSignal,
    PriceSpec,
    PositionSize,
    PositionSizeType,
)
from src.risk.types import AccountSnapshot, StopLossLevel, StopLossMode
from src.schemas.contracts import TradeIdea, TradeEntry
from src.common.config import AppConfig


@pytest.fixture
def mock_config():
    """创建测试用配置"""
    return AppConfig()


@pytest.fixture
def mock_base_dir(tmp_path):
    """创建临时目录作为 base_dir"""
    return tmp_path


@pytest.fixture
def mock_setup(mock_config, mock_base_dir):
    """Mock 所有外部依赖"""
    with patch('src.agents.manager_agent.agent.DataAgent') as mock_data, \
         patch('src.agents.manager_agent.agent.TraderAgent') as mock_trader, \
         patch('src.agents.manager_agent.agent.SignalVersioning') as mock_versioning:

        manager = ManagerAgent(config=mock_config, base_dir=mock_base_dir)
        yield {
            "manager": manager,
            "data_agent": mock_data,
            "trader_agent": mock_trader,
            "versioning": mock_versioning,
            "config": mock_config,
            "base_dir": mock_base_dir,
        }


@pytest.mark.asyncio
async def test_full_pipeline_success(mock_setup):
    """完整流程：TradeIdea → RawSignal → 最终 Signal"""
    manager = mock_setup["manager"]

    trade_idea = TradeIdea(
        idea_id=uuid4(),
        trader_id="trader1",
        as_of_date=date(2026, 4, 9),
        symbol="000001",
        side="buy",
        entry=TradeEntry(type="limit", price=10.0),
        target_price=12.0,
        stop_loss_price=9.0,
    )

    # Mock RawSignal
    raw_signal = RawSignal(
        signal_id="signal-uuid",
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=["rule1"],
        synthesis_mode=SynthesisMode.PRIORITY,
        entry_price=None,
        position_size=None,
        timestamp=datetime.now(timezone.utc),
        metadata={},
    )

    # Mock 最终 Signal（通过风控）
    final_signal = Signal(
        signal_id="signal-uuid",
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        timestamp=datetime.now(timezone.utc),
        triggered_rules=["rule1"],
        synthesis_mode=SynthesisMode.PRIORITY,
        entry_price=PriceSpec(type="limit", value=10.0),
        position_size=PositionSize(
            type=PositionSizeType.FIXED_RATIO,
            value=0.1,
            max_amount=100000.0,
        ),
        stop_loss=StopLossLevel(
            mode=StopLossMode.FIXED,
            level=9.5,
            trigger_condition="price <= 9.5",
        ),
        take_profit=None,
        metadata={},
    )

    with patch.object(
        StrategyAgent, 'generate_raw_signal', new_callable=AsyncMock, return_value=raw_signal
    ):
        with patch.object(
            RiskAgent, 'check', new_callable=AsyncMock, return_value=final_signal
        ):
            result = await manager.evaluate_signal(trade_idea, {"last_price": 10.0})
            assert result is not None
            assert result.side == SignalSide.BUY
            assert result.symbol == "000001"
            assert result.confidence == 0.75


@pytest.mark.asyncio
async def test_risk_agent_rejection(mock_setup):
    """风控拒绝场景"""
    manager = mock_setup["manager"]

    trade_idea = TradeIdea(
        idea_id=uuid4(),
        trader_id="trader1",
        as_of_date=date(2026, 4, 9),
        symbol="000001",
        side="buy",
        entry=TradeEntry(type="limit", price=10.0),
        target_price=12.0,
        stop_loss_price=9.0,
    )

    # Mock RawSignal
    raw_signal = RawSignal(
        signal_id="signal-uuid",
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=["rule1"],
        synthesis_mode=SynthesisMode.PRIORITY,
        entry_price=None,
        position_size=None,
        timestamp=datetime.now(timezone.utc),
        metadata={},
    )

    # Mock 风控拒绝的 Signal
    rejected_signal = Signal(
        signal_id="signal-uuid",
        symbol="000001",
        side=SignalSide.HOLD,  # 拒绝后变为 HOLD
        confidence=0.0,
        timestamp=datetime.now(timezone.utc),
        triggered_rules=["rule1"],
        synthesis_mode=SynthesisMode.PRIORITY,
        entry_price=None,
        position_size=None,
        stop_loss=None,
        take_profit=None,
        metadata={"rejected_reason": "drawdown exceeded"},
    )

    with patch.object(
        StrategyAgent, 'generate_raw_signal', new_callable=AsyncMock, return_value=raw_signal
    ):
        with patch.object(
            RiskAgent, 'check', new_callable=AsyncMock, return_value=rejected_signal
        ):
            result = await manager.evaluate_signal(trade_idea, {"last_price": 10.0})
            assert result is not None
            # 风控拒绝后，side 变为 HOLD
            assert result.side == SignalSide.HOLD
            assert "rejected_reason" in result.metadata
