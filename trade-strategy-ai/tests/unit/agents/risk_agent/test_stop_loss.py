import pytest
from src.agents.risk_agent.skills.stop_loss import calculate_stop_loss

@pytest.mark.asyncio
async def test_calculate_stop_loss_success():
    signal = {"entry_price": {"value": 100}}
    market_data = {"last_price": 100}
    config = {"mode": "fixed", "level_pct": 0.05}

    result = await calculate_stop_loss(signal, market_data, config)
    assert result.level == 95.0  # 5% below 100

@pytest.mark.asyncio
async def test_calculate_stop_loss_error():
    result = await calculate_stop_loss({}, {}, {})
    assert result.level == 0.0  # 降级