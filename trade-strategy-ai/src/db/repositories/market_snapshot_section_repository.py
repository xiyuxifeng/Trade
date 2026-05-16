from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.market_data_snapshot_section import MarketSnapshotSection


class MarketSnapshotSectionRepository:
    """市场快照 section 仓储。"""

    async def upsert_section(self, session: AsyncSession, section: MarketSnapshotSection) -> MarketSnapshotSection:
        """按 snapshot_id + section_id 写入或更新 section。"""
        existing = await session.scalar(
            select(MarketSnapshotSection).where(
                MarketSnapshotSection.snapshot_id == section.snapshot_id,
                MarketSnapshotSection.section_id == section.section_id,
            )
        )
        if existing is None:
            session.add(section)
            await session.flush()
            return section

        for field in (
            "provider",
            "source_time",
            "record_count",
            "missing_reason",
            "quality_status",
            "section_version",
            "storage_ref",
            "payload_json",
        ):
            setattr(existing, field, getattr(section, field))
        await session.flush()
        return existing

    async def list_by_snapshot_id(self, session: AsyncSession, snapshot_id: str) -> list[MarketSnapshotSection]:
        """按 snapshot_id 查询 section 列表。"""
        result = await session.scalars(
            select(MarketSnapshotSection)
            .where(MarketSnapshotSection.snapshot_id == snapshot_id)
            .order_by(MarketSnapshotSection.section_id.asc())
        )
        return list(result.all())

    async def get_by_snapshot_and_section(self, session: AsyncSession, snapshot_id: str, section_id: str) -> MarketSnapshotSection | None:
        """按 snapshot_id + section_id 查询 section。"""
        return await session.scalar(
            select(MarketSnapshotSection).where(
                MarketSnapshotSection.snapshot_id == snapshot_id,
                MarketSnapshotSection.section_id == section_id,
            )
        )

