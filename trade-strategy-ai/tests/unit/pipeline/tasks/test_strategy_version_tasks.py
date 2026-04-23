"""strategy_version_tasks 测试。"""

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.tasks.strategy_version_tasks import handle_build_trader_strategy_version
from src.strategy_library.schemas import StrategyVersion, StrategyVersionStatus
from src.trader_profile.schemas import TraderProfile


class TestHandleBuildTraderStrategyVersion:
    """build_trader_strategy_version 任务处理器测试。"""

    @pytest.mark.asyncio
    async def test_skips_when_trader_id_missing(self):
        """trader_id 缺失时跳过。"""
        config = MagicMock()
        details = {"strategy_date": "2026-04-23"}
        # 不应抛出异常
        await handle_build_trader_strategy_version(details, config=config)

    @pytest.mark.asyncio
    async def test_skips_when_strategy_date_missing(self):
        """strategy_date 缺失时跳过。"""
        config = MagicMock()
        details = {"trader_id": "trader-001"}
        await handle_build_trader_strategy_version(details, config=config)

    @pytest.mark.asyncio
    async def test_skips_when_profiles_file_not_found(self):
        """profiles 文件不存在时跳过。"""
        config = MagicMock()
        details = {"trader_id": "trader-001", "strategy_date": "2026-04-23"}
        with patch("src.pipeline.tasks.strategy_version_tasks.default_profiles_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/profiles.json")
            # 不应抛出异常
            await handle_build_trader_strategy_version(details, config=config)

    @pytest.mark.asyncio
    async def test_skips_when_trader_profile_not_found(self):
        """trader 不在 profiles 中时跳过。"""
        config = MagicMock()
        details = {"trader_id": "trader-999", "strategy_date": "2026-04-23"}

        mock_profiles_file = MagicMock()
        mock_profiles_file.profiles_by_trader = {"trader-001": MagicMock()}

        with patch("src.pipeline.tasks.strategy_version_tasks.default_profiles_path") as mock_path:
            mock_path.return_value = Path("/tmp/profiles.json")
            with patch("src.pipeline.tasks.strategy_version_tasks.load_trader_profiles_file") as mock_load:
                mock_load.return_value = mock_profiles_file
                await handle_build_trader_strategy_version(details, config=config)

    @pytest.mark.asyncio
    async def test_skips_when_released_version_exists(self):
        """非 force 模式下，已有发布版本时跳过。"""
        from src.strategy_library.schemas import StrategyVersionStatus
        from src.trader_profile.schemas import TraderProfile

        config = MagicMock()
        details = {"trader_id": "trader-001", "strategy_date": "2026-04-23", "force": False}

        mock_profile = TraderProfile(trader_id="trader-001", top_symbols=[], concept_tags=[])

        mock_profiles_file = MagicMock()
        mock_profiles_file.profiles_by_trader = {"trader-001": mock_profile}

        mock_session = AsyncMock()
        mock_existing = StrategyVersion(
            version_id="trader-001_2026-04-23_released",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.released,
            recommendations=[],
        )

        with patch("src.pipeline.tasks.strategy_version_tasks.default_profiles_path") as mock_path:
            mock_path.return_value = Path("/tmp/profiles.json")
            with patch("src.pipeline.tasks.strategy_version_tasks.load_trader_profiles_file") as mock_load:
                mock_load.return_value = mock_profiles_file
                with patch("src.pipeline.tasks.strategy_version_tasks.session_scope") as mock_scope:
                    mock_scope.return_value.__aenter__.return_value = mock_session
                    service = MagicMock()
                    service.get_current_released_version = AsyncMock(return_value=mock_existing)
                    with patch("src.pipeline.tasks.strategy_version_tasks.StrategyLibraryService", return_value=service):
                        await handle_build_trader_strategy_version(details, config=config)
                        # 不应调用 build_and_save_draft
                        service.build_and_save_draft.assert_not_called()

    @pytest.mark.asyncio
    async def test_builds_draft_when_no_released_version(self):
        """无发布版本时，构建并保存 draft。"""
        config = MagicMock()
        details = {"trader_id": "trader-001", "strategy_date": "2026-04-23", "force": False}

        mock_profile = TraderProfile(trader_id="trader-001", top_symbols=[], concept_tags=[])

        mock_profiles_file = MagicMock()
        mock_profiles_file.profiles_by_trader = {"trader-001": mock_profile}

        mock_draft = StrategyVersion(
            version_id="trader-001_2026-04-23_draft",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.draft,
            recommendations=[],
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        mock_profiles_path = MagicMock()
        mock_profiles_path.exists.return_value = True

        with patch("src.pipeline.tasks.strategy_version_tasks.default_profiles_path", return_value=mock_profiles_path):
            with patch("src.pipeline.tasks.strategy_version_tasks.load_trader_profiles_file") as mock_load:
                mock_load.return_value = mock_profiles_file
                with patch("src.pipeline.tasks.strategy_version_tasks.session_scope") as mock_scope:
                    mock_scope.return_value.__aenter__.return_value = mock_session
                    service = MagicMock()
                    service.get_current_released_version = AsyncMock(return_value=None)
                    service.build_and_save_draft = AsyncMock(return_value=mock_draft)
                    with patch("src.pipeline.tasks.strategy_version_tasks.StrategyLibraryService", return_value=service):
                        await handle_build_trader_strategy_version(details, config=config)
                        service.build_and_save_draft.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_rebuilds_even_with_existing(self):
        """force=True 时，即使已有发布版本也重建。"""
        config = MagicMock()
        details = {"trader_id": "trader-001", "strategy_date": "2026-04-23", "force": True}

        mock_profile = TraderProfile(trader_id="trader-001", top_symbols=[], concept_tags=[])

        mock_profiles_file = MagicMock()
        mock_profiles_file.profiles_by_trader = {"trader-001": mock_profile}

        mock_draft = StrategyVersion(
            version_id="trader-001_2026-04-23_draft",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.draft,
            recommendations=[],
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        mock_profiles_path = MagicMock()
        mock_profiles_path.exists.return_value = True

        with patch("src.pipeline.tasks.strategy_version_tasks.default_profiles_path", return_value=mock_profiles_path):
            with patch("src.pipeline.tasks.strategy_version_tasks.load_trader_profiles_file") as mock_load:
                mock_load.return_value = mock_profiles_file
                with patch("src.pipeline.tasks.strategy_version_tasks.session_scope") as mock_scope:
                    mock_scope.return_value.__aenter__.return_value = mock_session
                    service = MagicMock()
                    service.get_current_released_version = AsyncMock(return_value=None)
                    service.build_and_save_draft = AsyncMock(return_value=mock_draft)
                    with patch("src.pipeline.tasks.strategy_version_tasks.StrategyLibraryService", return_value=service):
                        await handle_build_trader_strategy_version(details, config=config)
                        service.build_and_save_draft.assert_called_once()
