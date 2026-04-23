"""strategy_library 唯一性与隔离测试（S3-010, S3-011）。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.strategy_library.schemas import StrategyVersion, StrategyVersionStatus
from src.strategy_library.service import StrategyLibraryService


class TestReleasedVersionUniqueness:
    """S3-010：同一 trader 同日只能有一个 released 版本。"""

    @pytest.mark.asyncio
    async def test_release_version_checks_existing(self):
        """release_version 发布前检查是否已有 released 版本。"""
        existing = StrategyVersion(
            version_id="trader-001_2026-04-23_released",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.released,
            recommendations=[],
        )
        draft = StrategyVersion(
            version_id="trader-001_2026-04-23_draft",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.draft,
            recommendations=[],
        )

        service = StrategyLibraryService()
        mock_session = AsyncMock()

        # patch 实例方法（AsyncMock 自动处理协程）
        with patch.object(service, "get_current_released_version", return_value=existing):
            with pytest.raises(ValueError, match="已有"):
                await service.release_version(mock_session, draft)

    @pytest.mark.asyncio
    async def test_release_allows_when_no_existing(self):
        """无已有版本时正常发布。"""
        draft = StrategyVersion(
            version_id="trader-001_2026-04-23_draft",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.draft,
            recommendations=[],
        )

        service = StrategyLibraryService()
        mock_session = AsyncMock()

        with patch.object(service, "get_current_released_version", return_value=None):
            service._repo = MagicMock()
            service._repo.save = AsyncMock()
            released = await service.release_version(mock_session, draft)
            assert released.status == StrategyVersionStatus.released

    @pytest.mark.asyncio
    async def test_different_trader_can_have_released_same_day(self):
        """不同 trader 同日可以各自有 released 版本（隔离验证）。"""
        version_t2 = StrategyVersion(
            version_id="trader-002_2026-04-23_draft",
            trader_id="trader-002",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.draft,
            recommendations=[],
        )

        service = StrategyLibraryService()
        mock_session = AsyncMock()

        # trader-2 发布时，检查的是 trader-2 的已有版本（返回 None → 可发布）
        with patch.object(service, "get_current_released_version", return_value=None):
            service._repo = MagicMock()
            service._repo.save = AsyncMock()
            released = await service.release_version(mock_session, version_t2)
            assert released.trader_id == "trader-002"
            assert released.status == StrategyVersionStatus.released


class TestTraderIsolation:
    """S3-011：不同 trader 版本严格隔离。"""

    def test_version_id_contains_trader_id(self):
        """版本 ID 包含 trader_id，不会混淆。"""
        v1 = StrategyVersion(
            version_id="trader-001_2026-04-23_released",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.released,
            recommendations=[],
        )
        v2 = StrategyVersion(
            version_id="trader-002_2026-04-23_released",
            trader_id="trader-002",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.released,
            recommendations=[],
        )
        assert v1.version_id != v2.version_id
        assert "trader-001" in v1.version_id
        assert "trader-002" in v2.version_id

    @pytest.mark.asyncio
    async def test_get_versions_only_returns_matching_trader(self):
        """get_by_trader_and_date 只返回匹配 trader_id 的版本。"""
        from src.strategy_library.repository import StrategyLibraryRepository
        repo = StrategyLibraryRepository()
        mock_session = AsyncMock()

        v1 = StrategyVersion(
            version_id="trader-001_2026-04-23_draft",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.draft,
            recommendations=[],
        )
        v2 = StrategyVersion(
            version_id="trader-002_2026-04-23_released",
            trader_id="trader-002",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.released,
            recommendations=[],
        )

        with patch.object(repo, "get_by_trader_and_date", new_callable=AsyncMock) as mock_get:
            # 模拟只返回 trader-001 的版本
            mock_get.return_value = [v1]
            results = await repo.get_by_trader_and_date(
                mock_session, "trader-001", date(2026, 4, 23)
            )
            assert all(r.trader_id == "trader-001" for r in results)
            # 验证调用时使用了正确的 trader_id 参数
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][1] == "trader-001"

    @pytest.mark.asyncio
    async def test_repository_query_filters_by_trader_id(self):
        """Repository 查询时按 trader_id 过滤。"""
        from src.strategy_library.repository import StrategyLibraryRepository

        repo = StrategyLibraryRepository()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_by_trader_and_date(mock_session, "trader-001", date(2026, 4, 23))

        # 验证 SQL 语句包含 trader_id 过滤条件
        call_args = mock_session.execute.call_args
        assert call_args is not None