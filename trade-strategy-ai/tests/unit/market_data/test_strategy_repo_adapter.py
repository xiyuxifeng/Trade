# tests/unit/market_data/test_strategy_repo_adapter.py
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from src.strategy_library.schemas import StrategyVersion, StrategyVersionStatus


class MockRepo:
    """Mock StrategyLibraryRepository"""
    async def get_released_by_trader_and_date(self, session, trader_id, strategy_date):
        return [
            StrategyVersion(
                version_id="test_v1",
                trader_id=trader_id,
                strategy_date=strategy_date,
                status=StrategyVersionStatus.released,
                recommendations=[],
                source_article_ids=[],
                evidence_refs=[],
            )
        ]


class MockFactory:
    """Mock AsyncSession factory"""
    def __init__(self):
        self.session = AsyncMock()

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *args):
        pass

    def __call__(self):
        return MockFactory()


@pytest.mark.asyncio
async def test_get_released_by_trader_and_date():
    """测试 StrategyRepoAdapter 能正确调用 repository"""
    from src.market_data.strategy_repo_adapter import StrategyRepoAdapter

    mock_factory = MockFactory()
    mock_repo = MockRepo()

    adapter = StrategyRepoAdapter(repo=mock_repo)
    # 替换 factory 为 mock
    adapter._factory = mock_factory

    versions = await adapter.get_released_by_trader_and_date(
        trader_id="trader_a",
        strategy_date=date(2026, 4, 23),
    )

    assert len(versions) == 1
    assert versions[0].version_id == "test_v1"
    assert versions[0].trader_id == "trader_a"
