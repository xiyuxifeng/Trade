from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture()
async def dataset_snapshot_session_factory(tmp_path):
    """创建用于 DatasetSnapshot repository 测试的 sqlite session factory。"""
    from src.models.stage2_canonical import DatasetSnapshot

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'dataset_snapshot.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(DatasetSnapshot.__table__.create)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


def _build_snapshot(*, dataset_snapshot_id: object, trade_date: date, fingerprint: str, ohlcv_manifest: dict[str, object]) -> object:
    from src.models.stage2_canonical import DatasetLifecycleState, DatasetSnapshot

    return DatasetSnapshot(
        dataset_snapshot_id=dataset_snapshot_id,
        content_fingerprint=fingerprint,
        trade_date=trade_date,
        market="CN",
        dataset_type="ohlcv_daily",
        date_from=trade_date,
        date_to=trade_date,
        symbol_manifest={"symbols": ["000001.SZ"]},
        ohlcv_manifest=ohlcv_manifest,
        kaipan_manifest={},
        benchmark_symbol="000300.SH",
        market_state_definition_version="market-state-v1",
        available_at=datetime(2026, 4, 1, 15, 1, tzinfo=timezone.utc),
        frozen_at=datetime(2026, 4, 1, 15, 2, tzinfo=timezone.utc),
        lifecycle_state=DatasetLifecycleState.ready,
        quality_report_id=None,
        storage_ref={"source": "ohlcv", "trade_date": trade_date.isoformat()},
    )


@pytest.mark.asyncio()
async def test_dataset_snapshot_repository_is_immutable_by_fingerprint(dataset_snapshot_session_factory) -> None:
    from src.db.repositories.dataset_snapshot_repository import DatasetSnapshotRepository

    repository = DatasetSnapshotRepository()

    first = _build_snapshot(
        dataset_snapshot_id=uuid4(),
        trade_date=date(2026, 4, 1),
        fingerprint="placeholder",
        ohlcv_manifest={"row_count": 2, "symbols": ["000001.SZ"]},
    )
    second = _build_snapshot(
        dataset_snapshot_id=uuid4(),
        trade_date=date(2026, 4, 1),
        fingerprint="placeholder-2",
        ohlcv_manifest={"row_count": 2, "symbols": ["000001.SZ"]},
    )
    third = _build_snapshot(
        dataset_snapshot_id=uuid4(),
        trade_date=date(2026, 4, 1),
        fingerprint="placeholder-3",
        ohlcv_manifest={"row_count": 3, "symbols": ["000001.SZ", "600000.SH"]},
    )

    async with dataset_snapshot_session_factory() as session:
        saved_first = await repository.save(session, first)
        saved_second = await repository.save(session, second)
        saved_third = await repository.save(session, third)
        await session.commit()

    async with dataset_snapshot_session_factory() as session:
        rows = await repository.list_snapshots(session, trade_date=date(2026, 4, 1), market="CN")
        count = await repository.count_snapshots(session, trade_date=date(2026, 4, 1), market="CN")
        loaded = await repository.get_by_fingerprint(session, content_fingerprint=saved_first.content_fingerprint)

    assert saved_first.dataset_snapshot_id == saved_second.dataset_snapshot_id
    assert saved_first.content_fingerprint == saved_second.content_fingerprint
    assert saved_third.content_fingerprint != saved_first.content_fingerprint
    assert len(rows) == 2
    assert count == 2
    assert loaded is not None
    assert loaded.dataset_snapshot_id == saved_first.dataset_snapshot_id
    assert loaded.storage_ref["source"] == "ohlcv"
