from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

from src.domain.enums import AuthorProfileKind, FormalLifecycleState, QualityStatus
from src.models.market_data_snapshot import MarketSnapshot
from src.models.market_data_snapshot_section import MarketSnapshotSection
from src.models.market_regime_record import MarketRegimeRecord
from src.models.rule_applicability import RuleApplicabilityProfile
from src.models.stage2_canonical import (
    AuthorProfileVersion,
    Authors,
    DatasetLifecycleState,
    DatasetSnapshot,
    Rule,
    RuleVersion,
    Strategy,
    StrategyRuleMembership,
    StrategyVersion,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, compiler, **kw):
    return compiler.visit_JSON(None, **kw)


async def _build_session_factory(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'pre_market_readiness.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Authors.__table__.create)
        await conn.run_sync(Rule.__table__.create)
        await conn.run_sync(RuleVersion.__table__.create)
        await conn.run_sync(DatasetSnapshot.__table__.create)
        await conn.run_sync(MarketSnapshot.__table__.create)
        await conn.run_sync(MarketSnapshotSection.__table__.create)
        await conn.run_sync(MarketRegimeRecord.__table__.create)
        await conn.run_sync(AuthorProfileVersion.__table__.create)
        await conn.run_sync(Strategy.__table__.create)
        await conn.run_sync(StrategyVersion.__table__.create)
        await conn.run_sync(StrategyRuleMembership.__table__.create)
        await conn.run_sync(RuleApplicabilityProfile.__table__.create)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def _session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return _session_scope, session_factory, engine


async def _seed_ready_bundle(session_factory: async_sessionmaker[AsyncSession]) -> dict[str, UUID]:
    author_id = uuid4()
    rule_id = uuid4()
    rule_version_id = uuid4()
    validated_profile_id = uuid4()
    method_profile_id = uuid4()
    rule_profile_id = uuid4()
    dataset_snapshot_id = uuid4()
    market_snapshot_id = uuid4()
    market_state_id = uuid4()
    applicability_profile_id = uuid4()
    rule_applicability_row_id = uuid4()
    strategy_id = uuid4()
    strategy_version_id = uuid4()
    membership_id = uuid4()
    now = datetime(2026, 6, 21, 0, 30, tzinfo=UTC)

    async with session_factory() as session:
        session.add(Authors(author_id=author_id, source="seed", source_author_key="author-1", display_name="测试作者"))
        session.add(
            Rule(
                rule_id=rule_id,
                business_key="rule-breakout-001",
                current_published_version_id=rule_version_id,
                created_at=now,
                created_by="seed",
                updated_at=now,
                updated_by="seed",
            )
        )
        session.add(
            RuleVersion(
                rule_version_id=rule_version_id,
                rule_id=rule_id,
                version_no=1,
                canonical_fingerprint="rule-fingerprint-1",
                schema_version="rule-schema-v1",
                lifecycle_state=FormalLifecycleState.published,
                title="放量突破",
                description="成交量放大后的突破",
                rule_type="entry",
                instrument_scope={"market": "CN"},
                condition_json={"indicator": "volume_breakout"},
                action_json={"decision": "buy"},
                parameter_json={"lookback_days": 20},
                data_dependencies={"datasets": ["ohlcv_1d"]},
                evidence_json={"source": "formal"},
                quality_status=QualityStatus.verified,
                published_at=now,
                published_by="seed",
                created_by="seed",
                updated_by="seed",
            )
        )
        session.add(
            DatasetSnapshot(
                dataset_snapshot_id=dataset_snapshot_id,
                content_fingerprint="dataset-fingerprint-1",
                trade_date=date(2026, 6, 20),
                market="CN",
                dataset_type="ohlcv_1d",
                date_from=date(2026, 1, 1),
                date_to=date(2026, 6, 20),
                symbol_manifest={"count": 100},
                ohlcv_manifest={"coverage": "complete", "trade_date": "2026-06-20"},
                kaipan_manifest={"pre_market_trade_date": "2026-06-21"},
                benchmark_symbol="000300.SH",
                market_state_definition_version="market-state-v2",
                available_at=now,
                frozen_at=now,
                lifecycle_state=DatasetLifecycleState.ready,
                storage_ref={"logical_dataset_id": "ohlcv:CN:2026-06-20"},
            )
        )
        session.add(
            MarketSnapshot(
                id=market_snapshot_id,
                snapshot_id="market-snapshot-2026-06-21-am",
                trade_date=date(2026, 6, 21),
                market="CN",
                profile_id="profile-default",
                data_version="v2",
                slot="09-25",
                quality_status="ready",
                provider_sources=["kaipan"],
                section_count=6,
                available_section_count=6,
                partial_section_count=0,
                missing_section_count=0,
                storage_ref={"snapshot_id": "market-snapshot-2026-06-21-am"},
                data_quality={"state": "verified"},
                captured_at=now,
                available_at=now,
                effective_at=now,
                content_fingerprint="market-fingerprint-1",
                manifest_json={"slot": "09-25"},
            )
        )
        session.add(
            MarketRegimeRecord(
                market_state_id=market_state_id,
                regime_id="market-state-ready",
                market_snapshot_id=market_snapshot_id,
                snapshot_id="market-snapshot-2026-06-21-am",
                trade_date=date(2026, 6, 21),
                market="CN",
                regime_version="market-state-v2",
                source_feature_version="features-v2",
                primary_label="强势上行",
                labels=[],
                features=[],
                confidence=0.82,
                quality_status="ready",
                storage_ref={"market_state_id": "market-state-ready"},
                available_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        for profile_id, profile_kind in (
            (method_profile_id, AuthorProfileKind.method),
            (rule_profile_id, AuthorProfileKind.rule),
            (validated_profile_id, AuthorProfileKind.validated),
        ):
            session.add(
                AuthorProfileVersion(
                    author_profile_version_id=profile_id,
                    author_profile_id=uuid4(),
                    author_id=author_id,
                    profile_kind=profile_kind,
                    version_no=1,
                    schema_version="author-profile-v1",
                    lifecycle_state=FormalLifecycleState.published,
                    payload={"summary": f"{profile_kind.value}-summary"},
                    evidence_json={"source": "formal"},
                    source_article_ids={},
                    source_rule_version_ids={},
                    source_rule_family_ids={},
                    source_applicability_profile_ids={},
                    source_backtest_run_ids={},
                    source_backtest_result_ids={},
                    source_daily_review_ids={},
                    source_versions_json={"schema_version": "author-profile-v1"},
                    quality_status=QualityStatus.verified,
                    review_status="published",
                    published_at=now,
                    published_by="seed",
                    created_by="seed",
                    updated_by="seed",
                )
            )
        session.add(
            Strategy(
                strategy_id=strategy_id,
                owner_type="platform",
                owner_id=None,
                business_key="cn-swing-core",
                current_published_version_id=strategy_version_id,
                created_at=now,
                created_by="seed",
                updated_at=now,
                updated_by="seed",
            )
        )
        session.add(
            StrategyVersion(
                strategy_version_id=strategy_version_id,
                strategy_id=strategy_id,
                version_no=3,
                schema_version="strategy-schema-v1",
                lifecycle_state=FormalLifecycleState.published,
                title="A股趋势轮动策略",
                summary="正式策略",
                risk_policy_json={"position_limit": 0.2},
                selection_policy_json={"degraded_mode": "allow_partial_rule_applicability"},
                universe_json={"market": "CN"},
                author_method_profile_version_id=method_profile_id,
                author_rule_profile_version_id=rule_profile_id,
                author_validated_profile_version_id=validated_profile_id,
                evidence_json={
                    "validation_summary": {
                        "state": "passed",
                        "dataset_binding": {"state": "ready", "dataset_snapshot_id": str(dataset_snapshot_id)},
                        "market_snapshot_binding": {"state": "ready", "market_snapshot_ids": [str(market_snapshot_id)]},
                    }
                },
                quality_status=QualityStatus.verified,
                review_status="published",
                published_at=now,
                published_by="seed",
                created_by="seed",
                updated_by="seed",
            )
        )
        session.add(
            StrategyRuleMembership(
                membership_id=membership_id,
                strategy_version_id=strategy_version_id,
                rule_version_id=rule_version_id,
                base_weight=0.65,
                status="active",
                configuration_json={},
            )
        )
        session.add(
            RuleApplicabilityProfile(
                profile_id=rule_applicability_row_id,
                applicability_profile_id=applicability_profile_id,
                rule_version_id=rule_version_id,
                rule_version_fingerprint="rule-fingerprint-1",
                rule_version_no=1,
                dataset_snapshot_id=dataset_snapshot_id,
                dataset_fingerprint="dataset-fingerprint-1",
                lifecycle_state=FormalLifecycleState.published,
                result_status="ready",
                rule_id="rule-breakout-001",
                profile_version="rule-applicability-v1",
                source_backtest_id="backtest-run-1",
                source_rule_version="v1",
                market_regime_version="market-state-v2",
                source_feature_version="features-v2",
                source_backtest_run_ids=["backtest-run-1"],
                source_backtest_result_ids=["backtest-result-1"],
                source_result_fingerprints=["backtest-fingerprint-1"],
                market_snapshot_ids=[str(market_snapshot_id)],
                market_snapshot_fingerprints=["market-fingerprint-1"],
                sample_count=50,
                eligible_sample_count=50,
                evaluated_sample_count=50,
                coverage=1.0,
                return_metric=0.12,
                win_rate=0.58,
                maximum_drawdown=0.08,
                recommendation_status="available",
                quality_status="verified",
                insufficient_sample_status="sufficient",
                review_status="published",
                reviewed_by="seed",
                reviewed_at=now,
                created_by="seed",
            )
        )
        await session.commit()

    return {
        "strategy_version_id": strategy_version_id,
        "dataset_snapshot_id": dataset_snapshot_id,
        "market_snapshot_id": market_snapshot_id,
        "market_state_id": market_state_id,
        "applicability_profile_id": applicability_profile_id,
        "rule_applicability_row_id": rule_applicability_row_id,
        "validated_profile_id": validated_profile_id,
    }


@pytest.mark.asyncio()
async def test_pre_market_readiness_reports_ready_when_all_canonical_inputs_exist(tmp_path: Path) -> None:
    from src.services.pre_market_readiness_service import PreMarketReadinessService

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    try:
        seeded = await _seed_ready_bundle(session_factory)
        async with session_factory() as session:
            session.add(
                DatasetSnapshot(
                    dataset_snapshot_id=uuid4(),
                    content_fingerprint="dataset-fingerprint-non-ohlcv",
                    trade_date=date(2026, 6, 21),
                    market="CN",
                    dataset_type="market_regimes",
                    date_from=date(2026, 6, 21),
                    date_to=date(2026, 6, 21),
                    symbol_manifest={},
                    ohlcv_manifest={},
                    kaipan_manifest={},
                    benchmark_symbol="000300.SH",
                    market_state_definition_version="market-state-v2",
                    available_at=datetime(2026, 6, 21, 8, 45, tzinfo=UTC),
                    frozen_at=datetime(2026, 6, 21, 8, 45, tzinfo=UTC),
                    lifecycle_state=DatasetLifecycleState.ready,
                    storage_ref={"logical_dataset_id": "market-regime:CN:2026-06-21"},
                )
            )
            await session.commit()
        service = PreMarketReadinessService(session_scope_factory=session_scope)

        result = await service.get_readiness(
            trade_date="2026-06-21",
            actor_id="tester",
            actor_role="viewer",
        )

        assert result.readiness_status == "ready"
        assert result.state == "ready"
        assert result.trade_date == "2026-06-21"
        assert result.slot == "09-25"
        assert result.can_proceed is True
        assert result.can_proceed_in_degraded_mode is False
        assert result.traceability.strategy_version_id == str(seeded["strategy_version_id"])
        assert result.traceability.dataset_snapshot_id == str(seeded["dataset_snapshot_id"])
        assert result.traceability.market_snapshot_id == str(seeded["market_snapshot_id"])
        assert result.traceability.market_state_id == str(seeded["market_state_id"])
        assert result.traceability.rule_applicability_profile_ids == [str(seeded["applicability_profile_id"])]
        assert result.traceability.author_validated_profile_version_id == str(seeded["validated_profile_id"])
        assert {item.code for item in result.checks} == {
            "kaipan_pre_market",
            "latest_ohlcv",
            "current_market_state",
            "current_formal_strategy",
            "rule_applicability",
            "author_validated_profile",
            "data_quality",
        }
        assert all(item.status == "ready" for item in result.checks)
    finally:
        await engine.dispose()


@pytest.mark.asyncio()
async def test_pre_market_readiness_marks_partial_rule_applicability_as_degraded_without_generating_outputs(
    tmp_path: Path,
) -> None:
    from src.services.pre_market_readiness_service import PreMarketReadinessService

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    try:
        seeded = await _seed_ready_bundle(session_factory)
        async with session_factory() as session:
            profile = await session.get(RuleApplicabilityProfile, seeded["rule_applicability_row_id"])
            assert profile is not None
            profile.quality_status = "partial"
            profile.result_status = "partial"
            await session.commit()

        service = PreMarketReadinessService(session_scope_factory=session_scope)
        result = await service.get_readiness(
            trade_date="2026-06-21",
            actor_id="tester",
            actor_role="viewer",
        )

        assert result.readiness_status == "degraded"
        assert result.state == "partial"
        assert result.can_proceed is True
        assert result.can_proceed_in_degraded_mode is True
        applicability_check = next(item for item in result.checks if item.code == "rule_applicability")
        assert applicability_check.status == "degraded"
        assert applicability_check.traceability["applicability_profile_ids"] == [str(seeded["applicability_profile_id"])]
        assert result.traceability.rule_applicability_profile_ids == [str(seeded["applicability_profile_id"])]
    finally:
        await engine.dispose()


def test_rule_applicability_check_accepts_level_1_global_profile_without_market_snapshot_binding() -> None:
    from types import SimpleNamespace

    from src.services.pre_market_readiness_service import PreMarketReadinessService, PreMarketTraceabilityView

    service = PreMarketReadinessService()
    rule_version_id = uuid4()
    profile_id = uuid4()
    market_snapshot_id = uuid4()
    traceability = PreMarketTraceabilityView(trade_date="2024-05-31")

    check = service._build_rule_applicability_check(
        memberships=[SimpleNamespace(rule_version_id=rule_version_id)],
        market_snapshot=SimpleNamespace(id=market_snapshot_id),
        applicability_profiles=[
            SimpleNamespace(
                applicability_profile_id=profile_id,
                rule_version_id=rule_version_id,
                market_snapshot_ids=[],
                effective_level="level_1",
                quality_status="complete",
                result_status="ready",
                reviewed_at=None,
                created_at=None,
            )
        ],
        traceability=traceability,
    )

    assert check.status == "ready"
    assert traceability.rule_applicability_profile_ids == [str(profile_id)]


@pytest.mark.asyncio()
async def test_pre_market_readiness_blocks_when_pre_market_snapshot_or_market_state_missing(tmp_path: Path) -> None:
    from src.services.pre_market_readiness_service import PreMarketReadinessService

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    try:
        seeded = await _seed_ready_bundle(session_factory)
        async with session_factory() as session:
            snapshot = await session.get(MarketSnapshot, seeded["market_snapshot_id"])
            regime = await session.get(MarketRegimeRecord, seeded["market_state_id"])
            assert snapshot is not None
            assert regime is not None
            snapshot.slot = "17-30"
            await session.delete(regime)
            await session.commit()

        service = PreMarketReadinessService(session_scope_factory=session_scope)
        result = await service.get_readiness(
            trade_date="2026-06-21",
            actor_id="tester",
            actor_role="viewer",
        )

        assert result.readiness_status == "blocked"
        assert result.state == "unavailable"
        assert result.can_proceed is False
        kaipan_check = next(item for item in result.checks if item.code == "kaipan_pre_market")
        market_state_check = next(item for item in result.checks if item.code == "current_market_state")
        assert kaipan_check.status == "blocked"
        assert market_state_check.status == "blocked"
        assert result.traceability.market_snapshot_id is None
        assert result.traceability.market_state_id is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio()
async def test_pre_market_readiness_blocks_when_required_inputs_were_not_available_before_cutoff(tmp_path: Path) -> None:
    from src.services.pre_market_readiness_service import PreMarketReadinessService

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    try:
        seeded = await _seed_ready_bundle(session_factory)
        async with session_factory() as session:
            dataset = await session.get(DatasetSnapshot, seeded["dataset_snapshot_id"])
            snapshot = await session.get(MarketSnapshot, seeded["market_snapshot_id"])
            regime = await session.get(MarketRegimeRecord, seeded["market_state_id"])
            assert dataset is not None
            assert snapshot is not None
            assert regime is not None

            dataset.available_at = datetime(2026, 6, 21, 2, 5, tzinfo=UTC)
            snapshot.available_at = datetime(2026, 6, 21, 2, 10, tzinfo=UTC)
            regime.available_at = datetime(2026, 6, 21, 2, 15, tzinfo=UTC)
            await session.commit()

        service = PreMarketReadinessService(session_scope_factory=session_scope)
        result = await service.get_readiness(
            trade_date="2026-06-21",
            actor_id="tester",
            actor_role="viewer",
        )

        assert result.readiness_status == "blocked"
        assert result.state == "unavailable"
        latest_ohlcv = next(item for item in result.checks if item.code == "latest_ohlcv")
        kaipan_check = next(item for item in result.checks if item.code == "kaipan_pre_market")
        market_state_check = next(item for item in result.checks if item.code == "current_market_state")
        assert latest_ohlcv.status == "blocked"
        assert kaipan_check.status == "blocked"
        assert market_state_check.status == "blocked"
        assert "available_at" in latest_ohlcv.traceability
        assert "decision_cutoff_at" in latest_ohlcv.traceability
        assert "盘前决策时点" in latest_ohlcv.happened
        assert "不能把盘前之后才补齐的数据当作今天盘前可用输入" in latest_ohlcv.affected
    finally:
        await engine.dispose()
