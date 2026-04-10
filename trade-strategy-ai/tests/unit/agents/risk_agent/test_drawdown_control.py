# tests/unit/agents/risk_agent/test_drawdown_control.py
import pytest
from src.agents.risk_agent.skills.drawdown_control import drawdown_control

@pytest.mark.asyncio
async def test_drawdown_control_success():
    from src.risk.types import AccountSnapshot
    from datetime import datetime, timezone

    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.now(timezone.utc),
        net_value=100000.0,
        cash=50000.0,
        total_position_value=50000.0,
        positions=[],
        daily_pnl=0.0,
        total_pnl=0.0
    )

    result = await drawdown_control(account, None)
    assert "passed" in result