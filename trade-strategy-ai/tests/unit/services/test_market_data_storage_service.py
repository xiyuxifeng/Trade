from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture()
async def market_data_session_factory(tmp_path):
    """创建用于 market data storage service 测试的 sqlite session factory。"""
    from src.models.market_data_quality_report import MarketDataQualityReport
    from src.models.market_dataset import MarketDataset
    from src.models.market_data_snapshot import MarketSnapshot
    from src.models.market_data_snapshot_item import MarketSnapshotItem
    from src.models.market_data_snapshot_section import MarketSnapshotSection

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'market_data_service.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(MarketSnapshot.__table__.create)
        await conn.run_sync(MarketSnapshotSection.__table__.create)
        await conn.run_sync(MarketDataset.__table__.create)
        await conn.run_sync(MarketSnapshotItem.__table__.create)
        await conn.run_sync(MarketDataQualityReport.__table__.create)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio()
async def test_market_data_storage_service_saves_and_loads_snapshot(market_data_session_factory) -> None:
    """MarketDataStorageService 应写入并回读结构化 snapshot。"""
    from src.models.market_snapshot import MarketSnapshot, MarketSnapshotSection
    from src.services.market_data_storage_service import MarketDataStorageService

    snapshot = MarketSnapshot(
        snapshot_id="snapshot-2026-05-16",
        trade_date="2026-05-16",
        market="CN",
        data_version="market-snapshot-v1",
        provider_sources=["kaipan", "market"],
        created_at=datetime(2026, 5, 16, 8, 0, tzinfo=timezone.utc),
        data_quality={"overall_status": "ok"},
        sections={
            "overview": MarketSnapshotSection(
                section_id="overview",
                provider="kaipan",
                source_time=datetime(2026, 5, 16, 8, 0, tzinfo=timezone.utc),
                record_count=1,
                missing_reason=None,
                quality_status="ok",
                payload={"sentiment": 55, "indices": [{"symbol": "000001.SZ"}]},
                metadata={"section_version": "v1"},
            ),
            "strong_symbols": MarketSnapshotSection(
                section_id="strong_symbols",
                provider="kaipan",
                source_time=datetime(2026, 5, 16, 8, 5, tzinfo=timezone.utc),
                record_count=2,
                missing_reason=None,
                quality_status="ok",
                payload={"symbols": [{"symbol": "000001.SZ"}, {"symbol": "600000.SH"}]},
                metadata={"section_version": "v1"},
            ),
        },
        metadata={"profile_id": "default", "slot": "17-30"},
    )

    service = MarketDataStorageService(session_factory=market_data_session_factory)
    saved = await service.save_snapshot(snapshot, summary_payload={"section_count": 2, "available_section_count": 2, "partial_section_count": 0, "missing_section_count": 0}, quality_payload={"overall_status": "ok"})
    loaded = await service.load_snapshot("snapshot-2026-05-16")

    assert saved.status == "ok"
    assert saved.payload["snapshot_id"] == "snapshot-2026-05-16"
    assert saved.payload["dataset_id"] == "snapshot-2026-05-16:dataset"
    assert saved.payload["section_count"] == 2
    assert saved.payload["item_count"] >= 3
    assert loaded.status == "ok"
    assert loaded.payload["snapshot"]["snapshot_id"] == "snapshot-2026-05-16"
    assert len(loaded.payload["sections"]) == 2
    assert len(loaded.payload["items"]) >= 3
    assert loaded.payload["quality_report"]["snapshot_id"] == "snapshot-2026-05-16"
    assert loaded.payload["dataset"]["dataset_id"] == "snapshot-2026-05-16:dataset"


@pytest.mark.asyncio()
async def test_market_data_storage_service_is_idempotent_on_snapshot_id(market_data_session_factory) -> None:
    """重复保存同一 snapshot_id 不应产生重复主记录。"""
    from src.models.market_snapshot import MarketSnapshot, MarketSnapshotSection
    from src.services.market_data_storage_service import MarketDataStorageService

    snapshot = MarketSnapshot(
        snapshot_id="snapshot-2026-05-17",
        trade_date="2026-05-17",
        market="CN",
        data_version="market-snapshot-v1",
        provider_sources=["kaipan"],
        created_at=datetime(2026, 5, 17, 8, 0, tzinfo=timezone.utc),
        data_quality={"overall_status": "ok"},
        sections={
            "overview": MarketSnapshotSection(
                section_id="overview",
                provider="kaipan",
                source_time=datetime(2026, 5, 17, 8, 0, tzinfo=timezone.utc),
                record_count=1,
                missing_reason=None,
                quality_status="ok",
                payload={"sentiment": 60},
                metadata={"section_version": "v1"},
            )
        },
        metadata={"profile_id": "default", "slot": "17-30"},
    )

    service = MarketDataStorageService(session_factory=market_data_session_factory)
    await service.save_snapshot(snapshot)
    await service.save_snapshot(snapshot)

    loaded = await service.load_snapshot("snapshot-2026-05-17")
    assert loaded.status == "ok"
    assert loaded.payload["snapshot"]["snapshot_id"] == "snapshot-2026-05-17"
    assert len(loaded.payload["sections"]) == 1

