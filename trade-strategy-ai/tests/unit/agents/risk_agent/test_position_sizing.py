import pytest
from datetime import datetime
from src.agents.risk_agent.skills.position_sizing import calculate_position_size
from src.strategy.types import PositionSizeType
from src.risk.types import AccountSnapshot

@pytest.mark.asyncio
async def test_calculate_position_size_success():
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

    result = await calculate_position_size(None, account, {"type": "fixed_ratio", "value": 0.1})
    assert result.type == PositionSizeType.FIXED_RATIO
    assert result.value == 0.1