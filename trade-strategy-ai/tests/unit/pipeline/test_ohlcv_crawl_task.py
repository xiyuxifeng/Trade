# tests/unit/pipeline/test_ohlcv_crawl_task.py
import pytest
from unittest.mock import AsyncMock, patch
from src.pipeline.tasks.ohlcv_crawl_task import handle_ohlcv_crawl
from src.common.config import AppConfig


@pytest.fixture
def mock_config():
    return AppConfig()


@pytest.mark.asyncio
async def test_handle_ohlcv_crawl_incremental(mock_config):
    """测试增量抓取"""
    details = {
        "mode": "incremental",
        "symbols": ["000001.SZ"],
    }

    with patch("src.market_data.ohlcv_service.OHLCVService") as MockService, patch(
        "src.services.dataset_snapshot_service.DatasetSnapshotService.freeze_ohlcv_snapshot",
        new_callable=AsyncMock,
    ) as freeze_snapshot:
        mock_instance = AsyncMock()
        mock_instance.crawl_bars.return_value = {"000001.SZ": 1}
        MockService.return_value = mock_instance
        freeze_snapshot.return_value = AsyncMock(
            content_fingerprint="fp",
            to_dict=lambda: {"dataset_id": "ohlcv:CN:test"},
        )

        await handle_ohlcv_crawl(details, config=mock_config)

        mock_instance.crawl_bars.assert_called_once()
        freeze_snapshot.assert_called_once()
