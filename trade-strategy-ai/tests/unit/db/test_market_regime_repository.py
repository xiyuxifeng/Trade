from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.market_regime_record import MarketRegimeRecord


@pytest.fixture()
async def market_regime_session_factory(tmp_path):
    """创建用于 Market Regime 仓储测试的 sqlite session factory。"""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'market_regime.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(MarketRegimeRecord.__table__.create)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio()
async def test_upsert_and_get_market_regime(market_regime_session_factory) -> None:
    """MarketRegimeRepository 应按 snapshot+version 写入和读取。"""
    from src.db.repositories.market_regime_repository import MarketRegimeRepository

    repo = MarketRegimeRepository()
    async with market_regime_session_factory() as session:
        record = MarketRegimeRecord(
            regime_id="regime-001",
            trade_date=date(2026, 5, 16),
            snapshot_id="snap-001",
            market="CN",
            regime_version="market-regime-v1",
            source_feature_version="market-regime-features-v1",
            primary_label="weak_bull",
            labels=[],
            features=[],
            confidence=0.81,
            quality_status="ok",
            missing_reason=None,
        )
        saved = await repo.upsert_regime(session, record)
        await session.commit()

        fetched = await repo.get_by_snapshot_and_version(session, "snap-001", "market-regime-v1")

    assert saved.regime_id == "regime-001"
    assert fetched is not None
    assert fetched.snapshot_id == "snap-001"
