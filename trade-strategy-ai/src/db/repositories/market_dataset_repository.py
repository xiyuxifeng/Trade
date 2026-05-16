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

    async def list_by_trade_date(self, session: AsyncSession, trade_date: date, market: str | None = None) -> list[MarketDataset]:
        """按 trade_date 查询数据集列表。"""
        stmt = select(MarketDataset).where(MarketDataset.trade_date == trade_date)
        if market:
            stmt = stmt.where(MarketDataset.market == market)
        stmt = stmt.order_by(MarketDataset.created_at.desc())
        result = await session.scalars(stmt)
        return list(result.all())

