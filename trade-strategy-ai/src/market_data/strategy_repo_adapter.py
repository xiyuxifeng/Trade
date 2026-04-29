"""StrategyRepoAdapter - 包装 StrategyLibraryRepository，自动管理 AsyncSession。

用于 SnapshotLoader.load_version_for_date() 的依赖注入。
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from src.strategy_library.schemas import StrategyVersion

if TYPE_CHECKING:
    from src.strategy_library.repository import StrategyLibraryRepository


class StrategyRepoAdapter:
    """strategy_repo 适配器。

    SnapshotLoader.load_version_for_date() 调用时，
    内部创建 session、调用 repository、返回结果。
    """

    def __init__(self, repo: StrategyLibraryRepository | None = None) -> None:
        from src.strategy_library.repository import StrategyLibraryRepository
        from config.database import get_session_factory

        self._factory = get_session_factory()
        self._repo = repo or StrategyLibraryRepository()

    async def get_released_by_trader_and_date(
        self, trader_id: str, strategy_date: date
    ) -> list[StrategyVersion]:
        """查询指定交易员和日期的已发布版本。"""
        async with self._factory() as session:
            return await self._repo.get_released_by_trader_and_date(
                session=session,
                trader_id=trader_id,
                strategy_date=strategy_date,
            )
