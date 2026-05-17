from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture()
async def market_regime_feature_repo_session_factory(tmp_path):
    """创建用于 MarketRegimeFeatureRepository 的 sqlite session factory。"""
    from src.models.market_data_snapshot import MarketSnapshot as MarketDataSnapshotRecord
    from src.models.market_regime import MarketRegimeFeature

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'market_regime_feature_repo.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(MarketDataSnapshotRecord.__table__.create)
        await conn.run_sync(MarketRegimeFeature.__table__.create)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio()
async def test_market_regime_feature_repository_supports_upsert_and_lookup(market_regime_feature_repo_session_factory) -> None:
    """仓储层应支持按 snapshot + version 的幂等写入和查询。"""
    from src.db.repositories import MarketRegimeFeatureRepository
    from src.models.market_data_snapshot import MarketSnapshot as MarketDataSnapshotRecord
    from src.models.market_regime import MarketRegimeFeature

    repo = MarketRegimeFeatureRepository()

    async with market_regime_feature_repo_session_factory() as session:
        session.add(
            MarketDataSnapshotRecord(
                snapshot_id="snap-101",
                trade_date=date(2026, 5, 19),
                market="CN",
                profile_id="default",
                data_version="market-snapshot-v1",
                slot="17-30",
                quality_status="ok",
                provider_sources=["kaipan"],
                section_count=0,
                available_section_count=0,
                partial_section_count=0,
                missing_section_count=0,
                storage_ref={"snapshot_id": "snap-101"},
                summary_artifact_ref=None,
                quality_artifact_ref=None,
                data_quality={},
            )
        )
        await session.commit()

        feature = MarketRegimeFeature(
            snapshot_id="snap-101",
            trade_date=date(2026, 5, 19),
            market="CN",
            feature_version="market-regime-features-v1",
            quality_status="ok",
            available_feature_count=1,
            partial_feature_count=0,
            missing_feature_count=0,
            feature_payload_json={"trend": {"feature_key": "trend", "value": "trend_up"}},
            summary_json={"snapshot_id": "snap-101"},
            storage_ref={"relative_path": "2026-05-19/snap-101/market-regime-features-v1.json"},
        )
        saved = await repo.upsert_feature(session, feature)
        await session.commit()

    async with market_regime_feature_repo_session_factory() as session:
        loaded = await repo.get_by_snapshot_and_version(session, "snap-101", "market-regime-features-v1")
        assert loaded is not None
        assert loaded.snapshot_id == "snap-101"
        assert loaded.feature_version == "market-regime-features-v1"

        listed = await repo.list_features(session, trade_date=date(2026, 5, 19), market="CN", limit=10, offset=0)
        assert len(listed) == 1
        assert listed[0].snapshot_id == "snap-101"

        by_snapshot = await repo.list_by_snapshot_id(session, "snap-101")
        assert len(by_snapshot) == 1
        assert by_snapshot[0].feature_version == "market-regime-features-v1"
        assert saved.snapshot_id == "snap-101"
