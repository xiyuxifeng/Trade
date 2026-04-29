from __future__ import annotations

from pathlib import Path

from src.agents.data_agent.agent import DataAgent
from src.common.config import AppConfig, DataConfig, StorageConfig
from src.schemas.contracts import DataRequest, DataResponseStatus


async def test_data_agent_uses_mock_prices_for_last_price() -> None:
    """测试 last_price 从 mock_prices 优先获取（CSV→DB 迁移后行为）"""
    config = AppConfig(
        storage=StorageConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"000001.SZ": 12.3}, market_data_cache_dir="data/processed/market_data"),
    )
    agent = DataAgent(config=config)

    response = await agent.handle(
        DataRequest(
            trader_id="trader_a",
            symbols=["000001.SZ"],
            fields=["last_price"],
        )
    )

    assert response.status == DataResponseStatus.ok
    assert response.payload["last_price"]["000001.SZ"] == 12.3
