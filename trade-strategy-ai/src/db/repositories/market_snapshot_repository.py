from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.market_data_snapshot import MarketSnapshot
from src.common.stage2_writer_routing import require_canonical_write


class MarketSnapshotRepository:
    """市场快照主表仓储。"""

    async def get_by_content_fingerprint(self, session: AsyncSession, content_fingerprint: str) -> MarketSnapshot | None:
        """按 canonical content_fingerprint 查询快照。"""
        return await session.scalar(
            select(MarketSnapshot).where(MarketSnapshot.content_fingerprint == content_fingerprint)
        )

    async def upsert_snapshot(self, session: AsyncSession, snapshot: MarketSnapshot) -> MarketSnapshot:
        """按 canonical 内容写入或复用 frozen snapshot。"""
        require_canonical_write("market_snapshot", "MarketSnapshotRepository.upsert_snapshot")
        existing_by_fingerprint = await self.get_by_content_fingerprint(session, snapshot.content_fingerprint)
        if existing_by_fingerprint is not None:
            return existing_by_fingerprint

        existing = await session.scalar(select(MarketSnapshot).where(MarketSnapshot.snapshot_id == snapshot.snapshot_id))
        if existing is None:
            session.add(snapshot)
            await session.flush()
            return snapshot

        if existing.content_fingerprint != snapshot.content_fingerprint:
            raise ValueError(
                f"frozen snapshot {snapshot.snapshot_id} already exists with a different content fingerprint"
            )
        return existing

    async def get_by_snapshot_id(self, session: AsyncSession, snapshot_id: str) -> MarketSnapshot | None:
        """按 snapshot_id 查询快照。"""
        return await session.scalar(select(MarketSnapshot).where(MarketSnapshot.snapshot_id == snapshot_id))

    async def list_snapshots(
        self,
        session: AsyncSession,
        *,
        trade_date: date | None = None,
        market: str | None = None,
        quality_status: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[MarketSnapshot]:
        """按条件查询快照列表。"""
        stmt = select(MarketSnapshot)
        if trade_date is not None:
            stmt = stmt.where(MarketSnapshot.trade_date == trade_date)
        if market:
            stmt = stmt.where(MarketSnapshot.market == market)
        if quality_status:
            stmt = stmt.where(MarketSnapshot.quality_status == quality_status)
        stmt = stmt.order_by(MarketSnapshot.created_at.desc())
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())

    async def list_by_trade_date(
        self,
        session: AsyncSession,
        trade_date: date,
        *,
        market: str | None = None,
    ) -> list[MarketSnapshot]:
        """Compatibility query routed to the canonical snapshot repository."""
        return await self.list_snapshots(session, trade_date=trade_date, market=market)

    async def count_snapshots(
        self,
        session: AsyncSession,
        *,
        trade_date: date | None = None,
        market: str | None = None,
        quality_status: str | None = None,
    ) -> int:
        """统计符合条件的快照数量。"""
        stmt = select(func.count()).select_from(MarketSnapshot)
        if trade_date is not None:
            stmt = stmt.where(MarketSnapshot.trade_date == trade_date)
        if market:
            stmt = stmt.where(MarketSnapshot.market == market)
        if quality_status:
            stmt = stmt.where(MarketSnapshot.quality_status == quality_status)
        return int((await session.scalar(stmt)) or 0)
