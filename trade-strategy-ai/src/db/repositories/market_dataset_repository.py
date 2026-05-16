from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.market_dataset import MarketDataset


class MarketDatasetRepository:
    """市场数据集仓储。"""

    async def upsert_dataset(self, session: AsyncSession, dataset: MarketDataset) -> MarketDataset:
        """按 dataset_id 写入或更新数据集。"""
        existing = await session.scalar(select(MarketDataset).where(MarketDataset.dataset_id == dataset.dataset_id))
        if existing is None:
            session.add(dataset)
            await session.flush()
            return dataset

        for field in (
            "dataset_type",
            "trade_date",
            "market",
            "source",
            "storage_ref",
            "snapshot_id",
            "profile_id",
            "quality_status",
        ):
            setattr(existing, field, getattr(dataset, field))
        await session.flush()
        return existing

    async def get_by_dataset_id(self, session: AsyncSession, dataset_id: str) -> MarketDataset | None:
        """按 dataset_id 查询数据集。"""
        return await session.scalar(select(MarketDataset).where(MarketDataset.dataset_id == dataset_id))

    async def list_datasets(
        self,
        session: AsyncSession,
        *,
        trade_date: date | None = None,
        market: str | None = None,
        dataset_type: str | None = None,
        quality_status: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[MarketDataset]:
        """按条件查询数据集列表。"""
        stmt = select(MarketDataset)
        if trade_date is not None:
            stmt = stmt.where(MarketDataset.trade_date == trade_date)
        if market:
            stmt = stmt.where(MarketDataset.market == market)
        if dataset_type:
            stmt = stmt.where(MarketDataset.dataset_type == dataset_type)
        if quality_status:
            stmt = stmt.where(MarketDataset.quality_status == quality_status)
        stmt = stmt.order_by(MarketDataset.created_at.desc())
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())
