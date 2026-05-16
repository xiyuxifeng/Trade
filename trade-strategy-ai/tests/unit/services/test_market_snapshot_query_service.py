from __future__ import annotations

from datetime import UTC, date, datetime

import pytest


@pytest.fixture()
async def market_snapshot_query_session_factory(tmp_path):
    """创建用于 MarketSnapshotQueryService 的 sqlite session factory。"""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from src.models.market_data_quality_report import MarketDataQualityReport
    from src.models.market_dataset import MarketDataset
    from src.models.market_data_snapshot import MarketSnapshot as MarketDataSnapshotRecord
    from src.models.market_data_snapshot_item import MarketSnapshotItem
    from src.models.market_data_snapshot_section import MarketSnapshotSection

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'market_snapshot_query.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(MarketDataSnapshotRecord.__table__.create)
        await conn.run_sync(MarketSnapshotSection.__table__.create)
        await conn.run_sync(MarketDataset.__table__.create)
        await conn.run_sync(MarketSnapshotItem.__table__.create)
        await conn.run_sync(MarketDataQualityReport.__table__.create)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        snapshot_1 = MarketDataSnapshotRecord(
            snapshot_id="snap-001",
            trade_date=date(2026, 5, 16),
            market="CN",
            profile_id="default",
            data_version="v1",
            slot="17-30",
            quality_status="ok",
            provider_sources=["kaipan", "market-state"],
            section_count=2,
            available_section_count=2,
            partial_section_count=0,
            missing_section_count=0,
            storage_ref={"snapshot_id": "snap-001"},
            summary_artifact_ref={"snapshot_id": "snap-001", "artifact_type": "snapshot-summary-json"},
            quality_artifact_ref={"snapshot_id": "snap-001", "artifact_type": "snapshot-quality-json"},
            data_quality={"overall_status": "ok"},
        )
        snapshot_2 = MarketDataSnapshotRecord(
            snapshot_id="snap-002",
            trade_date=date(2026, 5, 17),
            market="HK",
            profile_id="default",
            data_version="v1",
            slot="17-30",
            quality_status="partial",
            provider_sources=["kaipan"],
            section_count=1,
            available_section_count=1,
            partial_section_count=0,
            missing_section_count=0,
            storage_ref={"snapshot_id": "snap-002"},
            summary_artifact_ref={"snapshot_id": "snap-002", "artifact_type": "snapshot-summary-json"},
            quality_artifact_ref={"snapshot_id": "snap-002", "artifact_type": "snapshot-quality-json"},
            data_quality={"overall_status": "partial"},
        )
        section_1 = MarketSnapshotSection(
            snapshot_id="snap-001",
            section_id="overview",
            provider="kaipan",
            source_time=datetime(2026, 5, 16, 9, 30, tzinfo=UTC),
            record_count=1,
            missing_reason=None,
            quality_status="ok",
            section_version="v1",
            storage_ref={"snapshot_id": "snap-001", "section_id": "overview"},
            payload_json={"sentiment": "bull", "topics": [{"topic_id": "1", "topic_name": "热点"}]},
        )
        section_2 = MarketSnapshotSection(
            snapshot_id="snap-001",
            section_id="limit_up_down",
            provider="kaipan",
            source_time=datetime(2026, 5, 16, 9, 30, tzinfo=UTC),
            record_count=2,
            missing_reason=None,
            quality_status="ok",
            section_version="v1",
            storage_ref={"snapshot_id": "snap-001", "section_id": "limit_up_down"},
            payload_json={
                "items": [
                    {"symbol": "000001.SZ", "name": "示例A", "limit_type": "ZT"},
                    {"symbol": "000002.SZ", "name": "示例B", "limit_type": "ZT"},
                ]
            },
        )
        section_3 = MarketSnapshotSection(
            snapshot_id="snap-002",
            section_id="overview",
            provider="kaipan",
            source_time=datetime(2026, 5, 17, 9, 30, tzinfo=UTC),
            record_count=1,
            missing_reason=None,
            quality_status="partial",
            section_version="v1",
            storage_ref={"snapshot_id": "snap-002", "section_id": "overview"},
            payload_json={"sentiment": "neutral"},
        )
        dataset_1 = MarketDataset(
            dataset_id="snap-001:dataset",
            dataset_type="market_snapshot",
            trade_date=date(2026, 5, 16),
            market="CN",
            source="snapshot-build",
            storage_ref={"snapshot_id": "snap-001", "dataset_id": "snap-001:dataset"},
            snapshot_id="snap-001",
            profile_id="default",
            quality_status="ok",
        )
        dataset_2 = MarketDataset(
            dataset_id="snap-002:dataset",
            dataset_type="market_snapshot",
            trade_date=date(2026, 5, 17),
            market="HK",
            source="snapshot-build",
            storage_ref={"snapshot_id": "snap-002", "dataset_id": "snap-002:dataset"},
            snapshot_id="snap-002",
            profile_id="default",
            quality_status="partial",
        )
        item_1 = MarketSnapshotItem(
            snapshot_id="snap-001",
            section_id="overview",
            dataset_id="snap-001:dataset",
            symbol=None,
            item_key="overview:summary",
            item_type="overview",
            source_time=datetime(2026, 5, 16, 9, 30, tzinfo=UTC),
            quality_status="ok",
            payload_json={"sentiment": "bull", "topic_name": "热点"},
        )
        item_2 = MarketSnapshotItem(
            snapshot_id="snap-001",
            section_id="limit_up_down",
            dataset_id="snap-001:dataset",
            symbol="000001.SZ",
            item_key="limit_up_down:items:0",
            item_type="items",
            source_time=datetime(2026, 5, 16, 9, 30, tzinfo=UTC),
            quality_status="ok",
            payload_json={"symbol": "000001.SZ", "topic_name": "热点", "name": "示例A"},
        )
        item_3 = MarketSnapshotItem(
            snapshot_id="snap-001",
            section_id="limit_up_down",
            dataset_id="snap-001:dataset",
            symbol="000002.SZ",
            item_key="limit_up_down:items:1",
            item_type="items",
            source_time=datetime(2026, 5, 16, 9, 30, tzinfo=UTC),
            quality_status="ok",
            payload_json={"symbol": "000002.SZ", "topic_name": "热点", "name": "示例B"},
        )
        quality_1 = MarketDataQualityReport(
            snapshot_id="snap-001",
            overall_status="ok",
            warning_count=0,
            error_count=0,
            section_summary_json={"overview": {"quality_status": "ok"}},
            report_json={"overall_status": "ok"},
            storage_ref={"snapshot_id": "snap-001", "dataset_id": "snap-001:dataset", "kind": "quality_report"},
        )

        session.add_all([snapshot_1, snapshot_2, section_1, section_2, section_3, dataset_1, dataset_2, item_1, item_2, item_3, quality_1])
        await session.commit()

    yield session_factory
    await engine.dispose()


@pytest.mark.asyncio()
async def test_list_snapshots_filters_and_paginates(market_snapshot_query_session_factory) -> None:
    from src.services.market_snapshot_query_service import MarketSnapshotQueryService

    service = MarketSnapshotQueryService(session_factory=market_snapshot_query_session_factory)

    result = await service.list_snapshots(trade_date="2026-05-16", market="CN", topic="热点", limit=10, offset=0)

    assert result.status == "ok"
    assert result.payload["page"]["total"] == 1
    assert result.payload["items"][0]["snapshot_id"] == "snap-001"
    assert result.payload["items"][0]["quality_status"] == "ok"


@pytest.mark.asyncio()
async def test_list_snapshots_returns_empty_data_for_no_match(market_snapshot_query_session_factory) -> None:
    from src.services.market_snapshot_query_service import MarketSnapshotQueryService

    service = MarketSnapshotQueryService(session_factory=market_snapshot_query_session_factory)

    result = await service.list_snapshots(trade_date="2026-05-18", market="CN", limit=10, offset=0)

    assert result.status == "error"
    assert result.payload["error"]["type"] == "empty_data"


@pytest.mark.asyncio()
async def test_get_snapshot_detail_returns_sections_quality_and_dataset(market_snapshot_query_session_factory) -> None:
    from src.services.market_snapshot_query_service import MarketSnapshotQueryService

    service = MarketSnapshotQueryService(session_factory=market_snapshot_query_session_factory)

    result = await service.get_snapshot_detail("snap-001")

    assert result.status == "ok"
    assert result.payload["snapshot"]["snapshot_id"] == "snap-001"
    assert len(result.payload["sections"]) == 2
    assert result.payload["quality_report"]["overall_status"] == "ok"
    assert result.payload["dataset"]["dataset_id"] == "snap-001:dataset"


@pytest.mark.asyncio()
async def test_get_snapshot_detail_returns_partial_for_missing_related_data(market_snapshot_query_session_factory) -> None:
    from src.services.market_snapshot_query_service import MarketSnapshotQueryService

    service = MarketSnapshotQueryService(session_factory=market_snapshot_query_session_factory)

    result = await service.get_snapshot_detail("snap-002")

    assert result.status == "partial"
    assert result.payload["error"]["type"] == "partial_data"


@pytest.mark.asyncio()
async def test_get_snapshot_section_filters_items_and_paginates(market_snapshot_query_session_factory) -> None:
    from src.services.market_snapshot_query_service import MarketSnapshotQueryService

    service = MarketSnapshotQueryService(session_factory=market_snapshot_query_session_factory)

    result = await service.get_snapshot_section("snap-001", "limit_up_down", topic="热点", limit=1, offset=0)

    assert result.status == "ok"
    assert result.payload["section"]["section_id"] == "limit_up_down"
    assert result.payload["page"]["total"] == 2
    assert result.payload["page"]["count"] == 1
    assert result.payload["items"][0]["symbol"] == "000001.SZ"


@pytest.mark.asyncio()
async def test_get_dataset_detail_returns_items(market_snapshot_query_session_factory) -> None:
    from src.services.market_snapshot_query_service import MarketSnapshotQueryService

    service = MarketSnapshotQueryService(session_factory=market_snapshot_query_session_factory)

    result = await service.get_dataset_detail("snap-001:dataset", limit=1, offset=0)

    assert result.status == "ok"
    assert result.payload["dataset"]["dataset_id"] == "snap-001:dataset"
    assert result.payload["snapshot"]["snapshot_id"] == "snap-001"
    assert result.payload["page"]["total"] == 3
    assert result.payload["page"]["count"] == 1


@pytest.mark.asyncio()
async def test_get_quality_report_returns_partial_when_report_missing(market_snapshot_query_session_factory) -> None:
    from src.services.market_snapshot_query_service import MarketSnapshotQueryService

    service = MarketSnapshotQueryService(session_factory=market_snapshot_query_session_factory)

    result = await service.get_quality_report("snap-002")

    assert result.status == "partial"
    assert result.payload["error"]["type"] == "partial_data"


@pytest.mark.asyncio()
async def test_get_quality_report_reports_missing_snapshot(market_snapshot_query_session_factory) -> None:
    from src.services.market_snapshot_query_service import MarketSnapshotQueryService

    service = MarketSnapshotQueryService(session_factory=market_snapshot_query_session_factory)

    result = await service.get_quality_report("snap-missing")

    assert result.status == "partial"
    assert result.payload["error"]["type"] == "snapshot_not_found"
