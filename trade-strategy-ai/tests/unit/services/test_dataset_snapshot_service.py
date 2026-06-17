from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.ohlcv_bar import OHLCVBar
from src.models.stage2_canonical import DatasetSnapshot


@pytest.fixture()
async def dataset_snapshot_service_session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'dataset_snapshot_service.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(OHLCVBar.__table__.create)
        await conn.run_sync(DatasetSnapshot.__table__.create)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio()
async def test_freeze_ohlcv_snapshot_is_idempotent(dataset_snapshot_service_session_factory) -> None:
    from src.services.dataset_snapshot_service import DatasetSnapshotService

    async with dataset_snapshot_service_session_factory() as session:
        session.add(
            OHLCVBar(
                symbol="000001.SZ",
                source_symbol="000001.SZ",
                exchange="SZ",
                asset_type="stock",
                frequency="1d",
                adjustment_policy="unadjusted",
                source="akshare",
                trade_date=date(2026, 4, 1),
                open=10.0,
                high=10.5,
                low=9.8,
                close=10.2,
                volume=1000000,
                turnover=10200000,
                event_time=datetime(2026, 4, 1, 7, 0, tzinfo=UTC),
                source_time=None,
                source_time_reason="provider_time_unavailable",
                captured_at=datetime(2026, 4, 1, 8, 0, tzinfo=UTC),
                ingested_at=datetime(2026, 4, 1, 8, 1, tzinfo=UTC),
                available_at=datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
                source_payload_fingerprint="row-1",
            )
        )
        await session.commit()

    service = DatasetSnapshotService(session_factory=dataset_snapshot_service_session_factory)
    first = await service.freeze_ohlcv_snapshot(
        trade_date=date(2026, 4, 1),
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 1),
        market="CN",
    )
    second = await service.freeze_ohlcv_snapshot(
        trade_date=date(2026, 4, 1),
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 1),
        market="CN",
    )

    assert first.content_fingerprint == second.content_fingerprint
    assert first.dataset_snapshot_id == second.dataset_snapshot_id
    assert first.frozen_at is not None
    assert first.storage_ref["logical_dataset_id"] == "ohlcv:CN:2026-04-01:2026-04-01"


@pytest.mark.asyncio()
async def test_freeze_ohlcv_snapshot_creates_new_version_when_content_changes(
    dataset_snapshot_service_session_factory,
) -> None:
    from src.services.dataset_snapshot_service import DatasetSnapshotService

    async with dataset_snapshot_service_session_factory() as session:
        session.add(
            OHLCVBar(
                symbol="000001.SZ",
                source_symbol="000001.SZ",
                exchange="SZ",
                asset_type="stock",
                frequency="1d",
                adjustment_policy="unadjusted",
                source="akshare",
                trade_date=date(2026, 4, 1),
                open=10.0,
                high=10.5,
                low=9.8,
                close=10.2,
                volume=1000000,
                turnover=10200000,
                event_time=datetime(2026, 4, 1, 7, 0, tzinfo=UTC),
                source_time=None,
                source_time_reason="provider_time_unavailable",
                captured_at=datetime(2026, 4, 1, 8, 0, tzinfo=UTC),
                ingested_at=datetime(2026, 4, 1, 8, 1, tzinfo=UTC),
                available_at=datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
                source_payload_fingerprint="row-1",
            )
        )
        await session.commit()

    service = DatasetSnapshotService(session_factory=dataset_snapshot_service_session_factory)
    first = await service.freeze_ohlcv_snapshot(
        trade_date=date(2026, 4, 1),
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 1),
        market="CN",
    )

    async with dataset_snapshot_service_session_factory() as session:
        session.add(
            OHLCVBar(
                symbol="600000.SH",
                source_symbol="600000.SH",
                exchange="SH",
                asset_type="stock",
                frequency="1d",
                adjustment_policy="unadjusted",
                source="akshare",
                trade_date=date(2026, 4, 1),
                open=11.0,
                high=11.5,
                low=10.8,
                close=11.2,
                volume=1200000,
                turnover=13200000,
                event_time=datetime(2026, 4, 1, 7, 0, tzinfo=UTC),
                source_time=None,
                source_time_reason="provider_time_unavailable",
                captured_at=datetime(2026, 4, 1, 8, 5, tzinfo=UTC),
                ingested_at=datetime(2026, 4, 1, 8, 6, tzinfo=UTC),
                available_at=datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
                source_payload_fingerprint="row-2",
            )
        )
        await session.commit()

    second = await service.freeze_ohlcv_snapshot(
        trade_date=date(2026, 4, 1),
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 1),
        market="CN",
    )

    assert first.content_fingerprint != second.content_fingerprint
    assert first.dataset_snapshot_id != second.dataset_snapshot_id
    assert second.ohlcv_manifest["row_count"] == 2
