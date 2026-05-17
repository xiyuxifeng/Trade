from __future__ import annotations

from datetime import date

import pytest


@pytest.fixture()
async def market_regime_feature_session_factory(tmp_path):
    """创建用于 MarketRegimeFeatureService 的 sqlite session factory。"""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from src.models.market_data_quality_report import MarketDataQualityReport
    from src.models.market_dataset import MarketDataset
    from src.models.market_data_snapshot import MarketSnapshot as MarketDataSnapshotRecord
    from src.models.market_data_snapshot_item import MarketSnapshotItem
    from src.models.market_data_snapshot_section import MarketSnapshotSection
    from src.models.market_regime import MarketRegimeFeature

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'market_regime_feature.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(MarketDataSnapshotRecord.__table__.create)
        await conn.run_sync(MarketSnapshotSection.__table__.create)
        await conn.run_sync(MarketDataset.__table__.create)
        await conn.run_sync(MarketSnapshotItem.__table__.create)
        await conn.run_sync(MarketDataQualityReport.__table__.create)
        await conn.run_sync(MarketRegimeFeature.__table__.create)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield session_factory
    await engine.dispose()


async def _seed_snapshot(
    session_factory,
    *,
    snapshot_id: str,
    trade_date: date,
    market: str,
    sections: list[dict[str, object]],
) -> None:
    """写入一份用于 feature build 的 Market Snapshot。"""
    from datetime import UTC, datetime

    from src.models.market_data_quality_report import MarketDataQualityReport
    from src.models.market_dataset import MarketDataset
    from src.models.market_data_snapshot import MarketSnapshot as MarketDataSnapshotRecord
    from src.models.market_data_snapshot_item import MarketSnapshotItem
    from src.models.market_data_snapshot_section import MarketSnapshotSection

    async with session_factory() as session:
        snapshot = MarketDataSnapshotRecord(
            snapshot_id=snapshot_id,
            trade_date=trade_date,
            market=market,
            profile_id="default",
            data_version="market-snapshot-v1",
            slot="17-30",
            quality_status="ok" if all(section["quality_status"] == "ok" for section in sections) else "partial",
            provider_sources=["kaipan", "persona"],
            section_count=len(sections),
            available_section_count=sum(1 for section in sections if section["quality_status"] == "ok"),
            partial_section_count=sum(1 for section in sections if section["quality_status"] == "partial"),
            missing_section_count=sum(1 for section in sections if section["quality_status"] == "missing"),
            storage_ref={"snapshot_id": snapshot_id},
            summary_artifact_ref={"snapshot_id": snapshot_id, "artifact_type": "snapshot-summary-json"},
            quality_artifact_ref={"snapshot_id": snapshot_id, "artifact_type": "snapshot-quality-json"},
            data_quality={"overall_status": "ok"},
        )
        dataset = MarketDataset(
            dataset_id=f"{snapshot_id}:dataset",
            dataset_type="market_snapshot",
            trade_date=trade_date,
            market=market,
            source="snapshot-build",
            storage_ref={"snapshot_id": snapshot_id, "dataset_id": f"{snapshot_id}:dataset"},
            snapshot_id=snapshot_id,
            profile_id="default",
            quality_status="ok",
        )
        quality = MarketDataQualityReport(
            snapshot_id=snapshot_id,
            overall_status="ok",
            warning_count=0,
            error_count=0,
            section_summary_json={section["section_id"]: {"quality_status": section["quality_status"]} for section in sections},
            report_json={"overall_status": "ok"},
            storage_ref={"snapshot_id": snapshot_id, "dataset_id": f"{snapshot_id}:dataset", "kind": "quality_report"},
        )

        section_records = [
            MarketSnapshotSection(
                snapshot_id=snapshot_id,
                section_id=str(section["section_id"]),
                provider=str(section.get("provider") or "kaipan"),
                source_time=datetime(2026, 5, 16, 9, 30, tzinfo=UTC),
                record_count=int(section.get("record_count") or 0),
                missing_reason=section.get("missing_reason"),
                quality_status=str(section["quality_status"]),
                section_version="v1",
                storage_ref={"snapshot_id": snapshot_id, "section_id": str(section["section_id"])},
                payload_json=dict(section.get("payload_json") or {}),
            )
            for section in sections
        ]
        items = []
        for section in sections:
            payload = dict(section.get("payload_json") or {})
            for item_index, item_payload in enumerate(payload.get("items", [])):
                if not isinstance(item_payload, dict):
                    item_payload = {"value": item_payload}
                items.append(
                    MarketSnapshotItem(
                        snapshot_id=snapshot_id,
                        section_id=str(section["section_id"]),
                        dataset_id=f"{snapshot_id}:dataset",
                        symbol=item_payload.get("symbol"),
                        item_key=f"{section['section_id']}:items:{item_index}",
                        item_type="items",
                        source_time=datetime(2026, 5, 16, 9, 30, tzinfo=UTC),
                        quality_status=str(section["quality_status"]),
                        payload_json=item_payload,
                    )
                )

        async with session.begin():
            session.add(snapshot)
            session.add(dataset)
            session.add(quality)
            session.add_all(section_records)
            session.add_all(items)


@pytest.mark.asyncio()
async def test_build_market_regime_features_persists_feature_and_artifact(market_regime_feature_session_factory, tmp_path) -> None:
    """feature build 应输出完整结果、落库并写入 artifact。"""
    from src.services.market_regime_feature_service import MarketRegimeFeatureService

    await _seed_snapshot(
        market_regime_feature_session_factory,
        snapshot_id="snap-001",
        trade_date=date(2026, 5, 16),
        market="CN",
        sections=[
            {
                "section_id": "overview",
                "quality_status": "ok",
                "record_count": 3,
                "payload_json": {
                    "sentiment": {"label": "bullish", "score": 0.82},
                    "capacity": {"last": 23417, "turnover_level": "high"},
                    "indices": {"trend": "trend_up"},
                },
            },
            {
                "section_id": "limit_up_down",
                "quality_status": "ok",
                "record_count": 3,
                "payload_json": {
                    "limit_up_counts": {"info": {"SJZT": "79", "SJDT": "1"}},
                    "limit_up_reason": {"nums": {"ZT": 79, "DT": 1}},
                    "limit_up_info": {"info": [{"symbol": "000001.SZ"}, {"symbol": "000002.SZ"}]},
                },
            },
            {
                "section_id": "sector_activity",
                "quality_status": "ok",
                "record_count": 2,
                "payload_json": {
                    "board_strength": {"list": [["881007", "板块强度", 398]]},
                    "industry_ranking": {"list": [["881267", "行业涨幅", 398]]},
                    "weight_performance": {"info": {"SZ": [["881162", "通信服务", 3.8]]}},
                },
            },
            {
                "section_id": "hot_topics",
                "quality_status": "ok",
                "record_count": 2,
                "payload_json": {"topics": [{"topic_id": "1"}, {"topic_id": "2"}], "sources": ["board_strength"]},
            },
            {
                "section_id": "topic_constituents",
                "quality_status": "ok",
                "record_count": 2,
                "payload_json": {"constituents": [{"topic_id": "1"}, {"topic_id": "2"}], "sources": ["topic_constituents"]},
            },
            {
                "section_id": "strong_symbols",
                "quality_status": "ok",
                "record_count": 1,
                "payload_json": {"symbols": [{"symbol": "000001.SZ"}], "sources": ["strong_symbols"]},
            },
            {
                "section_id": "market_state",
                "quality_status": "ok",
                "record_count": 1,
                "payload_json": {
                    "market_state": {
                        "regime": "trend_up",
                        "volatility": "high",
                        "liquidity": "good",
                        "breadth": "strong",
                        "event_risk": False,
                        "features": {"vol20": 0.031},
                    },
                    "source": "cache",
                    "market_state_path": "data/processed/persona/market_state.json",
                },
            },
        ],
    )

    service = MarketRegimeFeatureService(
        session_factory=market_regime_feature_session_factory,
        artifact_root=tmp_path / "processed" / "market_regime_features",
    )

    result = await service.build_market_regime_features(snapshot_id="snap-001")

    assert result.status == "ok"
    assert result.payload["feature"]["snapshot_id"] == "snap-001"
    assert result.payload["feature"]["feature_version"] == "market-regime-features-v1"
    assert result.payload["feature"]["quality_status"] == "ok"
    assert result.payload["summary"]["available_feature_count"] == 9
    assert result.payload["summary"]["missing_feature_count"] == 0
    assert result.payload["feature_payload_json"]["trend"]["source_section"] == "market_state"
    assert result.payload["feature_payload_json"]["limit_up_count"]["value"] == 79
    assert result.payload["feature_payload_json"]["turnover_level"]["value"] == "high"
    assert result.payload["warnings"] == []
    assert (tmp_path / "processed" / "market_regime_features" / "2026-05-16" / "snap-001" / "market-regime-features-v1.json").exists()


@pytest.mark.asyncio()
async def test_build_market_regime_features_returns_partial_when_inputs_are_missing(market_regime_feature_session_factory, tmp_path) -> None:
    """缺失 section 时应返回 partial feature。"""
    from src.services.market_regime_feature_service import MarketRegimeFeatureService

    await _seed_snapshot(
        market_regime_feature_session_factory,
        snapshot_id="snap-002",
        trade_date=date(2026, 5, 17),
        market="CN",
        sections=[
            {
                "section_id": "overview",
                "quality_status": "ok",
                "record_count": 2,
                "payload_json": {
                    "sentiment": {"label": "neutral", "score": 0.51},
                    "capacity": {"last": 12000},
                },
            },
            {
                "section_id": "limit_up_down",
                "quality_status": "ok",
                "record_count": 2,
                "payload_json": {
                    "limit_up_counts": {"info": {"SJZT": "12", "SJDT": "3"}},
                    "limit_up_reason": {"nums": {"ZT": 12, "DT": 3}},
                },
            },
        ],
    )

    service = MarketRegimeFeatureService(
        session_factory=market_regime_feature_session_factory,
        artifact_root=tmp_path / "processed" / "market_regime_features",
    )

    result = await service.build_market_regime_features(snapshot_id="snap-002")

    assert result.status == "partial"
    assert result.payload["feature"]["quality_status"] == "partial"
    assert result.payload["summary"]["missing_feature_count"] >= 1
    assert result.payload["feature_payload_json"]["trend"]["value"] is None
    assert result.payload["feature_payload_json"]["theme_strength"]["value"] is None
    assert any("trend" in warning or "theme_strength" in warning for warning in result.warnings)


@pytest.mark.asyncio()
async def test_list_and_detail_market_regime_features(market_regime_feature_session_factory, tmp_path) -> None:
    """feature 列表和详情查询应可复用同一份落库结果。"""
    from src.services.market_regime_feature_service import MarketRegimeFeatureService

    await _seed_snapshot(
        market_regime_feature_session_factory,
        snapshot_id="snap-003",
        trade_date=date(2026, 5, 18),
        market="HK",
        sections=[
            {
                "section_id": "overview",
                "quality_status": "ok",
                "record_count": 1,
                "payload_json": {
                    "sentiment": {"label": "bullish", "score": 0.91},
                    "capacity": {"last": 54321, "turnover_level": "high"},
                },
            },
            {
                "section_id": "limit_up_down",
                "quality_status": "ok",
                "record_count": 2,
                "payload_json": {
                    "limit_up_counts": {"info": {"SJZT": "8", "SJDT": "2"}},
                    "limit_up_reason": {"nums": {"ZT": 8, "DT": 2}},
                },
            },
            {
                "section_id": "market_state",
                "quality_status": "ok",
                "record_count": 1,
                "payload_json": {
                    "market_state": {
                        "regime": "range",
                        "volatility": "mid",
                        "liquidity": "good",
                        "breadth": "weak",
                        "event_risk": False,
                        "features": {},
                    }
                },
            },
        ],
    )

    service = MarketRegimeFeatureService(
        session_factory=market_regime_feature_session_factory,
        artifact_root=tmp_path / "processed" / "market_regime_features",
    )

    build_result = await service.build_market_regime_features(snapshot_id="snap-003")
    assert build_result.status == "partial"

    list_result = await service.list_features(trade_date="2026-05-18", market="HK", limit=10, offset=0)
    assert list_result.status == "ok"
    assert list_result.payload["page"]["total"] == 1
    assert list_result.payload["items"][0]["snapshot_id"] == "snap-003"

    detail_result = await service.get_feature_detail("snap-003")
    assert detail_result.status == "partial"
    assert detail_result.payload["feature"]["snapshot_id"] == "snap-003"
    assert detail_result.payload["feature"]["market"] == "HK"
    assert detail_result.payload["feature_payload_json"]["liquidity"]["value"] == "good"


@pytest.mark.asyncio()
async def test_build_market_regime_features_returns_partial_when_db_write_fails(market_regime_feature_session_factory, tmp_path) -> None:
    """数据库写入失败时，只要 artifact 成功落盘就应返回 partial。"""
    from src.services.market_regime_feature_service import MarketRegimeFeatureService

    class _FailingFeatureRepository:
        async def upsert_feature(self, session, feature):  # noqa: ANN001
            raise RuntimeError("db unavailable")

    await _seed_snapshot(
        market_regime_feature_session_factory,
        snapshot_id="snap-004",
        trade_date=date(2026, 5, 19),
        market="CN",
        sections=[
            {
                "section_id": "overview",
                "quality_status": "ok",
                "record_count": 1,
                "payload_json": {
                    "sentiment": {"label": "bullish", "score": 0.88},
                    "capacity": {"last": 21456, "turnover_level": "high"},
                },
            },
            {
                "section_id": "limit_up_down",
                "quality_status": "ok",
                "record_count": 2,
                "payload_json": {
                    "limit_up_counts": {"info": {"SJZT": "6", "SJDT": "1"}},
                    "limit_up_reason": {"nums": {"ZT": 6, "DT": 1}},
                },
            },
        ],
    )

    service = MarketRegimeFeatureService(
        session_factory=market_regime_feature_session_factory,
        feature_repository=_FailingFeatureRepository(),
        artifact_root=tmp_path / "processed" / "market_regime_features",
    )

    result = await service.build_market_regime_features(snapshot_id="snap-004")

    assert result.status == "partial"
    assert any("database persistence failed" in warning for warning in result.warnings)
    assert (tmp_path / "processed" / "market_regime_features" / "2026-05-19" / "snap-004" / "market-regime-features-v1.json").exists()


@pytest.mark.asyncio()
async def test_list_market_regime_features_reports_total_before_pagination(market_regime_feature_session_factory, tmp_path) -> None:
    """列表分页的 total 应反映全部匹配结果，而不是当前页数量。"""
    from src.services.market_regime_feature_service import MarketRegimeFeatureService

    await _seed_snapshot(
        market_regime_feature_session_factory,
        snapshot_id="snap-005",
        trade_date=date(2026, 5, 20),
        market="CN",
        sections=[
            {
                "section_id": "overview",
                "quality_status": "ok",
                "record_count": 1,
                "payload_json": {
                    "sentiment": {"label": "bullish", "score": 0.88},
                    "capacity": {"last": 21456, "turnover_level": "high"},
                },
            },
            {
                "section_id": "limit_up_down",
                "quality_status": "ok",
                "record_count": 2,
                "payload_json": {
                    "limit_up_counts": {"info": {"SJZT": "6", "SJDT": "1"}},
                    "limit_up_reason": {"nums": {"ZT": 6, "DT": 1}},
                },
            },
        ],
    )
    await _seed_snapshot(
        market_regime_feature_session_factory,
        snapshot_id="snap-006",
        trade_date=date(2026, 5, 20),
        market="CN",
        sections=[
            {
                "section_id": "overview",
                "quality_status": "ok",
                "record_count": 1,
                "payload_json": {
                    "sentiment": {"label": "neutral", "score": 0.52},
                    "capacity": {"last": 18000},
                },
            },
            {
                "section_id": "limit_up_down",
                "quality_status": "ok",
                "record_count": 2,
                "payload_json": {
                    "limit_up_counts": {"info": {"SJZT": "3", "SJDT": "1"}},
                    "limit_up_reason": {"nums": {"ZT": 3, "DT": 1}},
                },
            },
        ],
    )

    service = MarketRegimeFeatureService(
        session_factory=market_regime_feature_session_factory,
        artifact_root=tmp_path / "processed" / "market_regime_features",
    )

    await service.build_market_regime_features(snapshot_id="snap-005")
    await service.build_market_regime_features(snapshot_id="snap-006")

    result = await service.list_features(trade_date="2026-05-20", market="CN", limit=1, offset=0)

    assert result.status == "ok"
    assert result.payload["page"]["total"] == 2
    assert result.payload["page"]["count"] == 1
