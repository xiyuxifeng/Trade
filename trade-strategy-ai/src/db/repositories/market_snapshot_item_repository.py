from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.market_data_snapshot_item import MarketSnapshotItem


class MarketSnapshotItemRepository:
    """市场快照明细仓储。"""

    async def upsert_item(self, session: AsyncSession, item: MarketSnapshotItem) -> MarketSnapshotItem:
        """按 snapshot_id + section_id + item_key 写入或更新 item。"""
        existing = await session.scalar(
            select(MarketSnapshotItem).where(
                MarketSnapshotItem.snapshot_id == item.snapshot_id,
                MarketSnapshotItem.section_id == item.section_id,
                MarketSnapshotItem.item_key == item.item_key,
            )
        )
        if existing is None:
            session.add(item)
            await session.flush()
            return item

        for field in (
            "dataset_id",
            "symbol",
            "item_type",
            "source_time",
            "quality_status",
            "payload_json",
        ):
            setattr(existing, field, getattr(item, field))
        await session.flush()
        return existing

    async def list_by_snapshot_id(self, session: AsyncSession, snapshot_id: str) -> list[MarketSnapshotItem]:
        """按 snapshot_id 查询明细列表。"""
        result = await session.scalars(
            select(MarketSnapshotItem)
            .where(MarketSnapshotItem.snapshot_id == snapshot_id)
            .order_by(MarketSnapshotItem.section_id.asc(), MarketSnapshotItem.item_key.asc())
        )
        return list(result.all())

    async def list_by_symbol(
        self,
        session: AsyncSession,
        symbol: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[MarketSnapshotItem]:
        """按 symbol 查询明细列表。"""
        stmt = select(MarketSnapshotItem).where(MarketSnapshotItem.symbol == symbol).order_by(MarketSnapshotItem.source_time.desc().nullslast())
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())

    async def list_by_section(
        self,
        session: AsyncSession,
        snapshot_id: str,
        section_id: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[MarketSnapshotItem]:
        """按 snapshot_id + section_id 查询明细列表。"""
        stmt = select(MarketSnapshotItem).where(
            MarketSnapshotItem.snapshot_id == snapshot_id,
            MarketSnapshotItem.section_id == section_id,
        ).order_by(MarketSnapshotItem.item_key.asc())
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())

    async def list_by_dataset_id(
        self,
        session: AsyncSession,
        dataset_id: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[MarketSnapshotItem]:
        """按 dataset_id 查询明细列表。"""
        stmt = select(MarketSnapshotItem).where(MarketSnapshotItem.dataset_id == dataset_id).order_by(MarketSnapshotItem.section_id.asc(), MarketSnapshotItem.item_key.asc())
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())
