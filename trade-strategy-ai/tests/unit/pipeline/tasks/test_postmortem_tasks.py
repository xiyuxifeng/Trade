"""postmortem_analysis 任务处理器测试：NTL-S5-008"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.pipeline.tasks.postmortem_tasks import handle_postmortem_analysis


class TestHandlePostmortemAnalysis:
    """测试 handle_postmortem_analysis 各种场景。"""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.storage.output_dir = "data/agent"
        return config

    @pytest.fixture
    def valid_details(self):
        idea_id = str(uuid4())
        return {
            "idea_id": idea_id,
            "trade_date": "2026-04-25",
            "trader_id": "trader_001",
            "symbol": "000001",
        }

    @pytest.mark.asyncio
    async def test_idea_id_or_trade_date_missing_skips(self, mock_config):
        """idea_id 或 trade_date 缺失时跳过。"""
        details = {"trader_id": "trader_001", "symbol": "000001"}
        # 不应抛出异常
        await handle_postmortem_analysis(details, config=mock_config)

    @pytest.mark.asyncio
    async def test_daily_report_not_found_skips(self, mock_config, valid_details):
        """DailyReport 文件不存在时跳过。"""
        with patch("src.pipeline.tasks.postmortem_tasks._daily_report_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/daily_report_2026-04-25.json")
            # 不应抛出异常
            await handle_postmortem_analysis(valid_details, config=mock_config)

    @pytest.mark.asyncio
    async def test_trade_idea_not_in_report_skips(self, mock_config, valid_details):
        """TradeIdea 不在 DailyReport 中时跳过。"""
        from src.schemas.contracts import DailyReport
        mock_report = DailyReport(as_of_date=date(2026, 4, 25), ideas=[])

        with TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "daily_report_2026-04-25.json"

            with patch("src.pipeline.tasks.postmortem_tasks._daily_report_path") as mock_path:
                mock_path.return_value = report_path
                with patch("src.pipeline.tasks.postmortem_tasks.read_json", return_value=mock_report.model_dump()):
                    # 不应抛出异常
                    await handle_postmortem_analysis(valid_details, config=mock_config)

    @pytest.mark.asyncio
    async def test_writes_memory_on_success(self, mock_config, valid_details):
        """成功执行时写入 TraderMemory。"""
        from src.schemas.contracts import DailyReport, TradeIdea, TradeEntry

        idea_id = uuid4()
        # 确保 valid_details 和 mock_idea 使用相同的 idea_id
        valid_details["idea_id"] = str(idea_id)

        mock_idea = TradeIdea(
            idea_id=idea_id,
            trader_id="trader_001",
            as_of_date=date(2026, 4, 25),
            symbol="000001",
            side="buy",
            entry=TradeEntry(price=10.0),
            strategy_version_id="v1",
        )

        mock_report = DailyReport(as_of_date=date(2026, 4, 25), ideas=[mock_idea])
        mock_store = MagicMock()

        with TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "daily_report_2026-04-25.json"
            report_path.touch()  # 创建文件，使 .exists() 返回 True

            with patch("src.pipeline.tasks.postmortem_tasks._daily_report_path") as mock_path:
                mock_path.return_value = report_path
                with patch("src.pipeline.tasks.postmortem_tasks.read_json", return_value=mock_report.model_dump()):
                    with patch("src.pipeline.tasks.postmortem_tasks._fetch_last_prices", new_callable=AsyncMock, return_value={"000001": 9.5}):
                        with patch("src.pipeline.tasks.postmortem_tasks.TraderMemoryStore", return_value=mock_store):
                            await handle_postmortem_analysis(valid_details, config=mock_config)
                            mock_store.append.assert_called_once()
                            # 验证写入的 memory 类型
                            call_args = mock_store.append.call_args[0][0]
                            assert call_args.memory_type.value == "postmortem"
