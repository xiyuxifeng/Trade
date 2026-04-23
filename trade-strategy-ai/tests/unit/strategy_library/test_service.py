"""strategy_library service 测试。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.strategy_library.builder import StrategyVersionBuilder
from src.strategy_library.repository import StrategyLibraryRepository
from src.strategy_library.schemas import (
    StrategyRecommendation,
    StrategyVersion,
    StrategyVersionStatus,
)
from src.strategy_library.service import StrategyLibraryService
from src.trader_profile.schemas import TraderProfile


class TestStrategyLibraryService:
    """策略库 service 测试。"""

    @pytest.mark.asyncio
    async def test_get_current_released_version(self):
        """能读取某 trader 当日发布的最新版本。"""
        mock_session = AsyncMock()
        mock_version = StrategyVersion(
            version_id="trader-001_2026-04-23_released",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.released,
            recommendations=[
                StrategyRecommendation(symbol="000001.SZ", decision="buy", confidence=0.8),
            ],
        )

        repo = StrategyLibraryRepository()
        with patch.object(repo, "get_released_by_trader_and_date", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [mock_version]
            service = StrategyLibraryService()
            service._repo = repo
            result = await service.get_current_released_version(
                session=mock_session,
                trader_id="trader-001",
                strategy_date=date(2026, 4, 23),
            )
            assert result is not None
            assert result.version_id == "trader-001_2026-04-23_released"
            assert result.status == StrategyVersionStatus.released

    @pytest.mark.asyncio
    async def test_get_current_released_version_returns_none_when_empty(self):
        """无发布版本时返回 None。"""
        mock_session = AsyncMock()
        repo = StrategyLibraryRepository()
        with patch.object(repo, "get_released_by_trader_and_date", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            service = StrategyLibraryService()
            service._repo = repo
            result = await service.get_current_released_version(
                session=mock_session,
                trader_id="trader-001",
                strategy_date=date(2026, 4, 23),
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_save_version_persists_to_repository(self):
        """保存版本到 repository。"""
        mock_session = AsyncMock()
        version = StrategyVersion(
            version_id="trader-001_2026-04-23_draft",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.draft,
            recommendations=[],
        )
        repo = StrategyLibraryRepository()
        with patch.object(repo, "save", new_callable=AsyncMock) as mock_save:
            service = StrategyLibraryService()
            service._repo = repo
            await service.save_version(session=mock_session, version=version)
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_build_and_save_draft(self):
        """能构建草稿版本并保存。"""
        mock_session = AsyncMock()
        profile = TraderProfile(trader_id="trader-001", top_symbols=[], concept_tags=[])
        articles = []
        repo = StrategyLibraryRepository()
        builder = StrategyVersionBuilder()

        with patch.object(repo, "save", new_callable=AsyncMock) as mock_save:
            service = StrategyLibraryService()
            service._repo = repo
            service._builder = builder
            version = await service.build_and_save_draft(
                session=mock_session,
                trader_id="trader-001",
                strategy_date=date(2026, 4, 23),
                profile=profile,
                source_articles=articles,
            )
            assert version.status == StrategyVersionStatus.draft
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_version_updates_status(self):
        """能把 draft 版本升级为 released。"""
        mock_session = AsyncMock()
        draft_version = StrategyVersion(
            version_id="trader-001_2026-04-23_draft",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.draft,
            recommendations=[],
        )
        repo = StrategyLibraryRepository()
        builder = StrategyVersionBuilder()

        with patch.object(repo, "save", new_callable=AsyncMock) as mock_save:
            service = StrategyLibraryService()
            service._repo = repo
            service._builder = builder
            with patch.object(service, "get_current_released_version", return_value=None):
                released = await service.release_version(
                    session=mock_session,
                    draft_version=draft_version,
                )
                assert released.status == StrategyVersionStatus.released
                assert released.released_at is not None
                assert released.version_id == draft_version.version_id.replace("draft", "released")
                mock_save.assert_called_once()
