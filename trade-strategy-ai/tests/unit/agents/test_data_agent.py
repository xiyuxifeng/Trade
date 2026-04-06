from __future__ import annotations

from pathlib import Path

from src.agents.data_agent.agent import DataAgent
from src.common.config import AppConfig, DataConfig, StorageConfig
from src.schemas.contracts import DataRequest, DataResponseStatus


async def test_data_agent_uses_market_data_cache_for_last_price(tmp_path: Path) -> None:
    cache_dir = tmp_path / "market"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "000001_SZ_daily.csv").write_text(
        "date,close\n2026-04-05,10.2\n2026-04-06,12.3\n",
        encoding="utf-8",
    )
    config = AppConfig(
        storage=StorageConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={}, market_data_cache_dir=str(cache_dir)),
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
