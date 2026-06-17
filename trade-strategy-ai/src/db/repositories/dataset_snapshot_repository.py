from __future__ import annotations

from datetime import date
import hashlib
import json

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.stage2_canonical import DatasetSnapshot


class DatasetSnapshotRepository:
    """Canonical DatasetSnapshot repository over dataset_snapshots."""

    def _canonical_fingerprint(self, dataset_snapshot: DatasetSnapshot) -> str:
        payload = {
            "trade_date": dataset_snapshot.trade_date.isoformat() if dataset_snapshot.trade_date else None,
            "market": dataset_snapshot.market,
            "dataset_type": dataset_snapshot.dataset_type,
            "date_from": dataset_snapshot.date_from.isoformat() if dataset_snapshot.date_from else None,
            "date_to": dataset_snapshot.date_to.isoformat() if dataset_snapshot.date_to else None,
            "symbol_manifest": dataset_snapshot.symbol_manifest or {},
            "ohlcv_manifest": dataset_snapshot.ohlcv_manifest or {},
            "kaipan_manifest": dataset_snapshot.kaipan_manifest or {},
            "benchmark_symbol": dataset_snapshot.benchmark_symbol,
            "market_state_definition_version": dataset_snapshot.market_state_definition_version,
            "storage_ref": dataset_snapshot.storage_ref or {},
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        ).hexdigest()

    async def get_by_fingerprint(
        self,
        session: AsyncSession,
        *,
        content_fingerprint: str,
    ) -> DatasetSnapshot | None:
        return await session.scalar(
            select(DatasetSnapshot).where(DatasetSnapshot.content_fingerprint == content_fingerprint)
        )

    async def get_by_dataset_id(
        self,
        session: AsyncSession,
        dataset_id: str,
    ) -> DatasetSnapshot | None:
        stmt = select(DatasetSnapshot).where(
            or_(
                DatasetSnapshot.content_fingerprint == dataset_id,
                DatasetSnapshot.storage_ref["logical_dataset_id"].as_string() == dataset_id,
            )
        )
        return await session.scalar(stmt)

    async def save(
        self,
        session: AsyncSession,
        dataset_snapshot: DatasetSnapshot,
    ) -> DatasetSnapshot:
        dataset_snapshot.content_fingerprint = self._canonical_fingerprint(dataset_snapshot)
        existing = await self.get_by_fingerprint(
            session,
            content_fingerprint=dataset_snapshot.content_fingerprint,
        )
        if existing is not None:
            return existing

        session.add(dataset_snapshot)
        await session.flush()
        return dataset_snapshot

    async def list_snapshots(
        self,
        session: AsyncSession,
        *,
        trade_date: date | None = None,
        market: str | None = None,
        dataset_type: str | None = None,
        quality_status: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[DatasetSnapshot]:
        stmt = select(DatasetSnapshot)
        if trade_date is not None:
            stmt = stmt.where(DatasetSnapshot.trade_date == trade_date)
        if market:
            stmt = stmt.where(DatasetSnapshot.market == market)
        if dataset_type:
            stmt = stmt.where(DatasetSnapshot.dataset_type == dataset_type)
        if quality_status:
            stmt = stmt.where(DatasetSnapshot.lifecycle_state == quality_status)
        stmt = stmt.order_by(DatasetSnapshot.created_at.desc())
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())

    async def count_snapshots(
        self,
        session: AsyncSession,
        *,
        trade_date: date | None = None,
        market: str | None = None,
        dataset_type: str | None = None,
        quality_status: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(DatasetSnapshot)
        if trade_date is not None:
            stmt = stmt.where(DatasetSnapshot.trade_date == trade_date)
        if market:
            stmt = stmt.where(DatasetSnapshot.market == market)
        if dataset_type:
            stmt = stmt.where(DatasetSnapshot.dataset_type == dataset_type)
        if quality_status:
            stmt = stmt.where(DatasetSnapshot.lifecycle_state == quality_status)
        return int((await session.scalar(stmt)) or 0)
