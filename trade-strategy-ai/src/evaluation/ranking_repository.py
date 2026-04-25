"""Ranking 数据访问层。

职责：
  - Upsert ranking entry（原子性，通过 ON CONFLICT DO UPDATE）
  - 查询最新 entry
  - 批量更新 rank
  - 按日期/trader/version 查询

NTL-S5-004
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ranking_entry import RankingEntryRecord


class RankingRepository:
    """ranking 条目数据访问层。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, entry) -> RankingEntryRecord:
        """Upsert 一条 ranking entry，保证 is_latest=True 的唯一性。

        实现：先 UPDATE 标记旧的为 False，再用新 ID INSERT 新行。
        注意：由于 unique constraint 在 INSERT 时仍会冲突（constraint 不含 is_latest），
        所以先 DELETE 旧的，再 INSERT 新行。

        Args:
            entry: RankingEntry dataclass

        Returns:
            新创建的 RankingEntryRecord
        """
        from sqlalchemy import delete

        # 先删除同一 (trade_date, strategy_version_id, symbol) 的现有 entry
        await self.session.execute(
            delete(RankingEntryRecord).where(
                RankingEntryRecord.trade_date == entry.trade_date,
                RankingEntryRecord.trader_id == entry.trader_id,
                RankingEntryRecord.strategy_version_id == entry.strategy_version_id,
                RankingEntryRecord.symbol == entry.symbol,
            )
        )

        # 插入新 entry（is_latest=True）
        record = RankingEntryRecord(
            entry_id=entry.entry_id,
            trade_date=entry.trade_date,
            trader_id=entry.trader_id,
            strategy_version_id=entry.strategy_version_id,
            symbol=entry.symbol,
            return_pct=entry.return_pct,
            mfe=entry.mfe,
            mae=entry.mae,
            composite_score=entry.composite_score,
            rank=entry.rank,
            is_latest=True,
            idea_id=entry.idea_id,
            attribution_source=entry.attribution_source,
            extra=entry.extra,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def find_latest(
        self,
        strategy_version_id: str,
        symbol: str,
        trade_date: str,
    ) -> RankingEntryRecord | None:
        """查找指定版本+标的的最新 entry。"""
        stmt = select(RankingEntryRecord).where(
            RankingEntryRecord.trade_date == trade_date,
            RankingEntryRecord.strategy_version_id == strategy_version_id,
            RankingEntryRecord.symbol == symbol,
            RankingEntryRecord.is_latest == True,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def query_by_date(
        self,
        trade_date: str,
        trader_id: str | None = None,
        strategy_version_id: str | None = None,
        is_latest_only: bool = True,
    ) -> list[RankingEntryRecord]:
        """按日期查询 entry。用于 generate_ranking。"""
        stmt = select(RankingEntryRecord).where(
            RankingEntryRecord.trade_date == trade_date,
        )
        if trader_id:
            stmt = stmt.where(RankingEntryRecord.trader_id == trader_id)
        if strategy_version_id:
            stmt = stmt.where(RankingEntryRecord.strategy_version_id == strategy_version_id)
        if is_latest_only:
            stmt = stmt.where(RankingEntryRecord.is_latest == True)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_rank(self, entry_ids: list[UUID], ranks: list[int]) -> None:
        """批量更新 rank。"""
        if not entry_ids:
            return
        for entry_id, rank in zip(entry_ids, ranks):
            await self.session.execute(
                update(RankingEntryRecord)
                .where(RankingEntryRecord.entry_id == entry_id)
                .values(rank=rank)
            )
        await self.session.flush()

    async def get_latest_by_version(self, version_id: str) -> list[RankingEntryRecord]:
        """获取指定策略版本的最新 ranking 条目（is_latest=True）。"""
        stmt = select(RankingEntryRecord).where(
            RankingEntryRecord.strategy_version_id == version_id,
            RankingEntryRecord.is_latest == True,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
