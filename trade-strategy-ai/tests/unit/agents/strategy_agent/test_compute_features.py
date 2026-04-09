import pytest
from src.agents.strategy_agent.skills.compute_features import compute_features

@pytest.mark.asyncio
async def test_compute_features_success():
    market_data = {
        "symbol": "000001",
        "open": 9.5, "high": 10.5, "low": 9.0, "close": 10.0,
        "volume": 1000000
    }
    result = await compute_features("000001", market_data, {})
    assert isinstance(result, dict)

@pytest.mark.asyncio
async def test_compute_features_error_returns_empty():
    """异常时返回空字典（降级）"""
    result = await compute_features("INVALID", {}, {})
    assert result == {}
