from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.repositories import DatasetSnapshotRepository
from src.db.session import get_session_factory
from src.models.ohlcv_bar import OHLCVBar
from src.models.stage2_canonical import DatasetLifecycleState, DatasetSnapshot


class DatasetSnapshotService:
    """Build immutable canonical DatasetSnapshot records over OHLCV data."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        repository: DatasetSnapshotRepository | None = None,
    ) -> None:
        self._session_factory = session_factory or get_session_factory()
        self._repository = repository or DatasetSnapshotRepository()

    async def freeze_ohlcv_snapshot(
        self,
        *,
        trade_date: date,
        date_from: date,
        date_to: date,
        market: str = "CN",
    ) -> DatasetSnapshot:
        async with self._session_factory() as session:
            bars = await session.scalars(
                select(OHLCVBar)
                .where(OHLCVBar.trade_date >= date_from)
                .where(OHLCVBar.trade_date <= date_to)
                .order_by(OHLCVBar.trade_date.asc(), OHLCVBar.symbol.asc())
            )
            rows = list(bars.all())
            latest_available_at = max((row.available_at for row in rows if row.available_at is not None), default=None)
            now = datetime.now(UTC)
            snapshot = DatasetSnapshot(
                trade_date=trade_date,
                market=market,
                dataset_type="ohlcv_daily",
                date_from=date_from,
                date_to=date_to,
                symbol_manifest={"symbols": [row.symbol for row in rows]},
                ohlcv_manifest={
                    "row_count": len(rows),
                    "symbols": [row.symbol for row in rows],
                    "date_range": [date_from.isoformat(), date_to.isoformat()],
                    "adjustment_policies": sorted({row.adjustment_policy for row in rows}),
                    "sources": sorted({row.source for row in rows if row.source}),
                },
                kaipan_manifest={},
                benchmark_symbol="000300.SH",
                market_state_definition_version="stage5-ohlcv-only",
                available_at=latest_available_at,
                frozen_at=now,
                lifecycle_state=DatasetLifecycleState.ready if rows else DatasetLifecycleState.partial,
                quality_report_id=None,
                storage_ref={
                    "source": "ohlcv",
                    "snapshot_kind": "ohlcv_daily",
                    "logical_dataset_id": f"ohlcv:{market}:{date_from.isoformat()}:{date_to.isoformat()}",
                    "trade_date": trade_date.isoformat(),
                },
            )
            saved = await self._repository.save(session, snapshot)
            await session.commit()
            return saved
