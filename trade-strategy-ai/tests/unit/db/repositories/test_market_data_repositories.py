from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture()
async def market_data_session_factory(tmp_path):
    """创建用于 market data repository 测试的 sqlite session factory。"""
    from src.models.market_data_quality_report import MarketDataQualityReport
    from src.models.market_dataset import MarketDataset
    from src.models.market_data_snapshot import MarketSnapshot
    from src.models.market_data_snapshot_item import MarketSnapshotItem
    from src.models.market_data_snapshot_section import MarketSnapshotSection

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'market_data.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(MarketSnapshot.__table__.create)
        await conn.run_sync(MarketSnapshotSection.__table__.create)
        await conn.run_sync(MarketDataset.__table__.create)
        await conn.run_sync(MarketSnapshotItem.__table__.create)
        await conn.run_sync(MarketDataQualityReport.__table__.create)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio()
async def test_market_data_repositories_support_snapshot_section_item_and_quality_queries(market_data_session_factory) -> None:
    """Repository 层应支持 market data 的主查询路径。"""
    from src.db.repositories import (
        MarketDataQualityRepository,
        MarketDatasetRepository,
        MarketSnapshotItemRepository,
        MarketSnapshotRepository,
        MarketSnapshotSectionRepository,
    )
    from src.models.market_data_quality_report import MarketDataQualityReport
    from src.models.market_dataset import MarketDataset
    from src.models.market_data_snapshot import MarketSnapshot
    from src.models.market_data_snapshot_item import MarketSnapshotItem
    from src.models.market_data_snapshot_section import MarketSnapshotSection

    snapshot_repo = MarketSnapshotRepository()
    section_repo = MarketSnapshotSectionRepository()
    item_repo = MarketSnapshotItemRepository()
    dataset_repo = MarketDatasetRepository()
    quality_repo = MarketDataQualityRepository()

    async with market_data_session_factory() as session:
        snapshot = MarketSnapshot(
            snapshot_id="snapshot-2026-05-16",
            trade_date=date(2026, 5, 16),
            market="CN",
            profile_id="default",
            data_version="v1",
            slot="17-30",
            quality_status="ok",
            provider_sources=["kaipan"],
            section_count=2,
            available_section_count=2,
            partial_section_count=0,
            missing_section_count=0,
            storage_ref={"path": "market_snapshot/snapshot.json"},
            summary_artifact_ref={"artifact_id": "summary"},
            quality_artifact_ref={"artifact_id": "quality"},
            data_quality={"overall": "ok"},
        )
        await snapshot_repo.upsert_snapshot(session, snapshot)

        section = MarketSnapshotSection(
            snapshot_id="snapshot-2026-05-16",
            section_id="overview",
            provider="kaipan",
            source_time=datetime(2026, 5, 16, 8, 0, tzinfo=timezone.utc),
            record_count=1,
            missing_reason=None,
            quality_status="ok",
            section_version="v1",
            storage_ref={"path": "market_snapshot/overview.json"},
            payload_json={"sentiment": 55},
        )
        await section_repo.upsert_section(session, section)

        dataset = MarketDataset(
            dataset_id="dataset-2026-05-16-overview",
            dataset_type="market_snapshot",
            trade_date=date(2026, 5, 16),
            market="CN",
            source="snapshot-build",
            storage_ref={"path": "market_snapshot/dataset.json"},
            snapshot_id="snapshot-2026-05-16",
            profile_id="default",
            quality_status="ok",
        )
        await dataset_repo.upsert_dataset(session, dataset)

        item = MarketSnapshotItem(
            snapshot_id="snapshot-2026-05-16",
            section_id="overview",
            dataset_id="dataset-2026-05-16-overview",
            symbol="000001.SZ",
            item_key="overview-1",
            item_type="overview",
            source_time=datetime(2026, 5, 16, 8, 0, tzinfo=timezone.utc),
            quality_status="ok",
            payload_json={"symbol": "000001.SZ", "sentiment": 55},
        )
        await item_repo.upsert_item(session, item)

        report = MarketDataQualityReport(
            snapshot_id="snapshot-2026-05-16",
            overall_status="ok",
            warning_count=0,
            error_count=0,
            section_summary_json={"overview": {"quality_status": "ok"}},
            report_json={"summary": "ok"},
            storage_ref={"path": "market_snapshot/quality.json"},
        )
        await quality_repo.upsert_report(session, report)

        await session.commit()

    async with market_data_session_factory() as session:
        snapshot = await snapshot_repo.get_by_snapshot_id(session, "snapshot-2026-05-16")
        assert snapshot is not None
        assert snapshot.quality_status == "ok"

        snapshots = await snapshot_repo.list_by_trade_date(session, date(2026, 5, 16), market="CN")
        assert len(snapshots) == 1

        sections = await section_repo.list_by_snapshot_id(session, "snapshot-2026-05-16")
        assert len(sections) == 1
        assert sections[0].section_id == "overview"

        section = await section_repo.get_by_snapshot_and_section(session, "snapshot-2026-05-16", "overview")
        assert section is not None
        assert section.payload_json["sentiment"] == 55

        items = await item_repo.list_by_snapshot_id(session, "snapshot-2026-05-16")
        assert len(items) == 1

        symbol_items = await item_repo.list_by_symbol(session, "000001.SZ")
        assert len(symbol_items) == 1

        section_items = await item_repo.list_by_section(session, "snapshot-2026-05-16", "overview")
        assert len(section_items) == 1

        dataset_items = await item_repo.list_by_dataset_id(session, "dataset-2026-05-16-overview")
        assert len(dataset_items) == 1

        dataset = await dataset_repo.get_by_dataset_id(session, "dataset-2026-05-16-overview")
        assert dataset is not None
        assert dataset.snapshot_id == "snapshot-2026-05-16"

        datasets = await dataset_repo.list_by_trade_date(session, date(2026, 5, 16), market="CN")
        assert len(datasets) == 1

        report = await quality_repo.get_by_snapshot_id(session, "snapshot-2026-05-16")
        assert report is not None
        assert report.overall_status == "ok"


@pytest.mark.asyncio()
async def test_market_data_repositories_are_idempotent_on_business_keys(market_data_session_factory) -> None:
    """重复写入同一 business key 时不应创建重复记录。"""
    from src.db.repositories import MarketSnapshotItemRepository, MarketSnapshotRepository
    from src.models.market_data_snapshot import MarketSnapshot
    from src.models.market_data_snapshot_item import MarketSnapshotItem

    snapshot_repo = MarketSnapshotRepository()
    item_repo = MarketSnapshotItemRepository()

    async with market_data_session_factory() as session:
        snapshot = MarketSnapshot(
            snapshot_id="snapshot-2026-05-17",
            trade_date=date(2026, 5, 17),
            market="CN",
            profile_id="default",
            data_version="v1",
            slot="17-30",
            quality_status="ok",
            provider_sources=["kaipan"],
            section_count=1,
            available_section_count=1,
            partial_section_count=0,
            missing_section_count=0,
            storage_ref={},
            summary_artifact_ref=None,
            quality_artifact_ref=None,
            data_quality={"overall": "ok"},
        )
        await snapshot_repo.upsert_snapshot(session, snapshot)
        await snapshot_repo.upsert_snapshot(session, snapshot)

        item = MarketSnapshotItem(
            snapshot_id="snapshot-2026-05-17",
            section_id="overview",
            dataset_id=None,
            symbol="000002.SZ",
            item_key="overview-1",
            item_type="overview",
            source_time=None,
            quality_status="ok",
            payload_json={"symbol": "000002.SZ"},
        )
        await item_repo.upsert_item(session, item)
        await item_repo.upsert_item(session, item)
        await session.commit()

    async with market_data_session_factory() as session:
        snapshots = await snapshot_repo.list_by_trade_date(session, date(2026, 5, 17), market="CN")
        assert len(snapshots) == 1

        items = await item_repo.list_by_snapshot_id(session, "snapshot-2026-05-17")
        assert len(items) == 1
