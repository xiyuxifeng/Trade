from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.market_data_snapshot import MarketSnapshot


class MarketSnapshotRepository:
    """市场快照主表仓储。"""

    async def upsert_snapshot(self, session: AsyncSession, snapshot: MarketSnapshot) -> MarketSnapshot:
        """按 snapshot_id 写入或更新快照主记录。"""
        existing = await session.scalar(select(MarketSnapshot).where(MarketSnapshot.snapshot_id == snapshot.snapshot_id))
        if existing is None:
            session.add(snapshot)
            await session.flush()
            return snapshot

        for field in (
            "trade_date",
            "market",
            "profile_id",
            "data_version",
            "slot",
            "quality_status",
            "provider_sources",
            "section_count",
            "available_section_count",
            "partial_section_count",
            "missing_section_count",
            "storage_ref",
            "summary_artifact_ref",
            "quality_artifact_ref",
            "data_quality",
        ):
            setattr(existing, field, getattr(snapshot, field))
        await session.flush()
        return existing

    async def get_by_snapshot_id(self, session: AsyncSession, snapshot_id: str) -> MarketSnapshot | None:
        """按 snapshot_id 查询快照。"""
        return await session.scalar(select(MarketSnapshot).where(MarketSnapshot.snapshot_id == snapshot_id))

    async def list_by_trade_date(self, session: AsyncSession, trade_date: date, market: str | None = None) -> list[MarketSnapshot]:
        """按 trade_date 查询快照列表。"""
        stmt = select(MarketSnapshot).where(MarketSnapshot.trade_date == trade_date)
        if market:
            stmt = stmt.where(MarketSnapshot.market == market)
        stmt = stmt.order_by(MarketSnapshot.created_at.desc())
        result = await session.scalars(stmt)
        return list(result.all())

