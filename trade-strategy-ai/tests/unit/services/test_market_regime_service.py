from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.market_regime_record import MarketRegimeRecord


@pytest.fixture()
async def market_regime_session_factory(tmp_path):
    """创建用于 Market Regime Service 测试的 sqlite session factory。"""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'market_regime_service.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(MarketRegimeRecord.__table__.create)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


class FakeSnapshotRepository:
    async def get_by_snapshot_id(self, session, snapshot_id: str):
        return SimpleNamespace(snapshot_id=snapshot_id, trade_date=date(2026, 5, 16), market="CN")


class FakeFeatureRepository:
    async def get_by_snapshot_and_version(self, session, snapshot_id: str, feature_version: str):
        return SimpleNamespace(
            snapshot_id=snapshot_id,
            trade_date=date(2026, 5, 16),
            market="CN",
            feature_version=feature_version,
            quality_status="ok",
            feature_payload_json={
                "trend": {"feature_key": "trend", "value": {"ret_20d": 0.11, "ret_5d": 0.04}, "source_section": "overview", "confidence": 0.9, "missing_reason": None},
                "breadth": {"feature_key": "breadth", "value": {"up_ratio": 0.68}, "source_section": "overview", "confidence": 0.88, "missing_reason": None},
                "volatility": {"feature_key": "volatility", "value": "mid", "source_section": "market_state", "confidence": 0.8, "missing_reason": None},
                "liquidity": {"feature_key": "liquidity", "value": "good", "source_section": "market_state", "confidence": 0.85, "missing_reason": None},
                "turnover_level": {"feature_key": "turnover_level", "value": "high", "source_section": "market_state", "confidence": 0.8, "missing_reason": None},
                "theme_strength": {"feature_key": "theme_strength", "value": {"topic_count": 5, "constituent_count": 12, "strong_symbol_count": 8}, "source_section": "hot_topics", "confidence": 0.7, "missing_reason": None},
            },
            summary_json={"source_sections": ["overview", "market_state", "hot_topics"]},
            storage_ref={"source": "db"},
            to_dict=lambda: {},
        )


@pytest.mark.asyncio()
async def test_build_market_regime_uses_feature_snapshot_and_persists_artifact(market_regime_session_factory, tmp_path):
    """Market Regime Service 应从 feature snapshot 构建并落盘 artifact。"""
    from src.services.market_regime_service import MarketRegimeService

    service = MarketRegimeService(
        session_factory=market_regime_session_factory,
        feature_repository=FakeFeatureRepository(),
        snapshot_repository=FakeSnapshotRepository(),
        artifact_root=tmp_path,
    )

    result = await service.build_market_regime(
        snapshot_id="snap-001",
        regime_version="market-regime-v1",
        feature_version="market-regime-features-v1",
    )

    assert result.status in {"ok", "partial"}
    assert result.payload["regime"]["snapshot_id"] == "snap-001"
    assert result.payload["regime"]["regime_version"] == "market-regime-v1"
    assert result.payload["artifact_ref"]["artifact_type"] == "market-regime-json"
    assert result.payload["artifact_path"].endswith("market-regime-v1.json")
