from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.common.config import AppConfig, StorageConfig
from src.pipeline.completion import run_incremental_data_completion


@pytest.mark.asyncio
async def test_run_incremental_data_completion_raises_when_any_step_fails() -> None:
    config = AppConfig(storage=StorageConfig(output_dir="data/processed/test"))

    with (
        patch("src.pipeline.completion.handle_ohlcv_crawl", new=AsyncMock(side_effect=RuntimeError("ohlcv failed"))) as mocked_ohlcv,
        patch("src.pipeline.completion.handle_hot_topics_snapshot", new=AsyncMock(side_effect=RuntimeError("hot failed"))) as mocked_hot,
        patch("src.pipeline.completion.handle_topic_constituents_snapshot", new=AsyncMock(return_value=SimpleNamespace())) as mocked_constituents,
        patch("src.pipeline.completion.handle_strong_symbols_snapshot", new=AsyncMock(return_value=SimpleNamespace())) as mocked_strong,
    ):
        with pytest.raises(RuntimeError, match="盘后增量数据补全失败"):
            await run_incremental_data_completion(config=config, as_of_date=date(2026, 5, 23), force=False)

    mocked_ohlcv.assert_awaited_once()
    mocked_hot.assert_awaited_once()
    mocked_constituents.assert_awaited_once()
    mocked_strong.assert_awaited_once()
