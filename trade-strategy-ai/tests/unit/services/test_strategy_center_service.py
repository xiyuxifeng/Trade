from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import select

from src.domain.enums import AuthorProfileKind, FormalLifecycleState, QualityStatus
from src.models.market_regime_record import MarketRegimeRecord
from src.models.market_data_snapshot import MarketSnapshot
from src.models.market_data_snapshot_section import MarketSnapshotSection
from src.models.rule_applicability import RuleApplicabilityProfile
from src.models.stage2_canonical import (
    AuthorProfileVersion,
    Authors,
    BacktestResult,
    BacktestRun,
    DatasetLifecycleState,
    DatasetSnapshot,
    DailyRuleSelection,
    DailyStrategyInstance,
    LifecycleEvent,
    OptimizationProposal,
    PostMarketReview,
    Rule,
    RuleVersion,
    Strategy,
    StrategyRuleMembership,
    TradingDayPlan,
    StrategyVersion,
    StrategyVersionAudit,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, compiler, **kw):
    return compiler.visit_JSON(None, **kw)


async def _build_session_factory(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'strategy_center.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Authors.__table__.create)
        await conn.run_sync(Rule.__table__.create)
        await conn.run_sync(RuleVersion.__table__.create)
        await conn.run_sync(DatasetSnapshot.__table__.create)
        await conn.run_sync(MarketSnapshot.__table__.create)
        await conn.run_sync(MarketSnapshotSection.__table__.create)
        await conn.run_sync(AuthorProfileVersion.__table__.create)
        await conn.run_sync(Strategy.__table__.create)
        await conn.run_sync(StrategyVersion.__table__.create)
        await conn.run_sync(StrategyRuleMembership.__table__.create)
        await conn.run_sync(StrategyVersionAudit.__table__.create)
        await conn.run_sync(LifecycleEvent.__table__.create)
        await conn.run_sync(BacktestRun.__table__.create)
        await conn.run_sync(BacktestResult.__table__.create)
        await conn.run_sync(RuleApplicabilityProfile.__table__.create)
        await conn.run_sync(MarketRegimeRecord.__table__.create)
        await conn.run_sync(DailyRuleSelection.__table__.create)
        await conn.run_sync(DailyStrategyInstance.__table__.create)
        await conn.run_sync(TradingDayPlan.__table__.create)
        await conn.run_sync(PostMarketReview.__table__.create)
        await conn.run_sync(OptimizationProposal.__table__.create)
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


async def _seed_dependencies(session_factory: async_sessionmaker[AsyncSession]) -> dict[str, UUID]:
    author_id = uuid4()
    rule_id = uuid4()
    rule_version_id = uuid4()
    method_profile_id = uuid4()
    rule_profile_id = uuid4()
    validated_profile_id = uuid4()
    dataset_snapshot_id = uuid4()
    market_snapshot_id = uuid4()
    applicability_profile_id = uuid4()
    backtest_run_id = uuid4()
    backtest_result_id = uuid4()
    market_state_id = uuid4()
    daily_rule_selection_id = uuid4()
    daily_strategy_instance_id = uuid4()
    trading_day_plan_id = uuid4()
    post_market_review_id = uuid4()
    now = datetime.now(UTC)

    async with session_factory() as session:
        session.add(Authors(author_id=author_id, source="test", source_author_key=f"author-{author_id}", display_name="测试作者"))
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
                description="成交量放大后的突破介入规则",
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
                trade_date=date(2026, 6, 19),
                market="CN",
                dataset_type="ohlcv_1d",
                date_from=date(2026, 1, 1),
                date_to=date(2026, 6, 19),
                symbol_manifest={"count": 100},
                ohlcv_manifest={"coverage": "complete"},
                kaipan_manifest={},
                benchmark_symbol="000300.SH",
                market_state_definition_version="market-state-v2",
                available_at=now,
                frozen_at=now,
                lifecycle_state=DatasetLifecycleState.ready,
                storage_ref={"logical_dataset_id": "dataset-2026-06-19"},
            )
        )
        session.add(
            MarketSnapshot(
                id=market_snapshot_id,
                snapshot_id="market-snapshot-2026-06-19-pm",
                trade_date=date(2026, 6, 19),
                market="CN",
                profile_id="profile-default",
                data_version="v2",
                slot="17-30",
                quality_status="ready",
                provider_sources=["kaipan"],
                section_count=6,
                available_section_count=6,
                partial_section_count=0,
                missing_section_count=0,
                storage_ref={"snapshot_id": "market-snapshot-2026-06-19-pm"},
                data_quality={"state": "ready"},
                captured_at=now,
                available_at=now,
                effective_at=now,
                content_fingerprint="market-fingerprint-1",
                manifest_json={"slot": "17-30"},
            )
        )
        session.add(
            MarketRegimeRecord(
                market_state_id=market_state_id,
                regime_id="market-state-ready",
                market_snapshot_id=market_snapshot_id,
                snapshot_id="market-snapshot-2026-06-19-pm",
                trade_date=date(2026, 6, 19),
                market="CN",
                regime_version="market-state-v2",
                source_feature_version="features-v2",
                primary_label="强势上行",
                labels=[],
                features=[],
                confidence=0.8,
                quality_status="ready",
                storage_ref={"market_state_id": "market-state-ready"},
                available_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        for profile_version_id, profile_kind, version_no in (
            (method_profile_id, AuthorProfileKind.method, 1),
            (rule_profile_id, AuthorProfileKind.rule, 1),
            (validated_profile_id, AuthorProfileKind.validated, 1),
        ):
            session.add(
                AuthorProfileVersion(
                    author_profile_version_id=profile_version_id,
                    author_profile_id=uuid4(),
                    author_id=author_id,
                    profile_kind=profile_kind,
                    version_no=version_no,
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
            RuleApplicabilityProfile(
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
        session.add(
            BacktestRun(
                run_id=backtest_run_id,
                rule_version_id=rule_version_id,
                rule_version_fingerprint="rule-fingerprint-1",
                rule_version_no=1,
                frozen_rule_version_ids=[str(rule_version_id)],
                frozen_rule_version_fingerprints=["rule-fingerprint-1"],
                date_from=date(2026, 1, 1),
                date_to=date(2026, 6, 19),
                universe_json={"market": "CN"},
                benchmark_symbol="000300.SH",
                mode="backtest",
                requested_level="L2",
                effective_level="L2",
                dataset_snapshot_id=dataset_snapshot_id,
                dataset_fingerprint="dataset-fingerprint-1",
                market_snapshot_ids=[str(market_snapshot_id)],
                market_snapshot_fingerprints=["market-fingerprint-1"],
                market_state_model_version="market-state-v2",
                indicator_version="indicators-v1",
                engine_version="engine-v1",
                execution_policy_version="execution-v1",
                decision_time_policy="next_open",
                request_fingerprint="request-fingerprint-1",
                reproducibility_fingerprint="reproducibility-fingerprint-1",
                snapshot_only=True,
                status="completed_valid",
                coverage_state="ready",
                quality_state="verified",
                repair_guidance=[],
                unavailable_reasons=[],
                limitations=[],
                progress_json={"step": "completed"},
                audit_json={"out_of_sample_state": "available"},
                actor_id="seed",
                actor_role="system",
                source_surface="/tests",
            )
        )
        session.add(
            BacktestResult(
                result_id=backtest_result_id,
                run_id=backtest_run_id,
                input_fingerprint="input-fingerprint-1",
                result_fingerprint="result-fingerprint-1",
                reproducibility_fingerprint="result-reproducibility-1",
                status="completed_valid",
                requested_level="L2",
                effective_level="L2",
                market_state_model_version="market-state-v2",
                market_state_source_version="market-state-source-v2",
                market_state_result_version="market-state-result-v2",
                decision_time_policy="next_open",
                overall_metrics={"annual_return": 0.18, "max_drawdown": 0.09, "win_rate": 0.56},
                per_market_state_metrics=[{"market_state": "强势上行", "annual_return": 0.24}],
                per_rule_metrics=[{"rule_version_id": str(rule_version_id), "annual_return": 0.18}],
                sample_state_counts={"total": 48, "insufficient_sample": 0},
                coverage_json={"out_of_sample_state": "available", "sample_count": 48},
                warnings=[],
                limitations=[],
                provenance_json={"dataset_snapshot_id": str(dataset_snapshot_id)},
                audit_json={"quality_state": "verified"},
            )
        )
        session.add(
            DailyRuleSelection(
                daily_rule_selection_id=daily_rule_selection_id,
                strategy_version_id=uuid4(),
                market_state_id=market_state_id,
                trade_date=date(2026, 6, 19),
                revision_no=1,
                selected_rules_json={},
                reduced_rules_json={},
                blocked_rules_json={},
                quality_status=QualityStatus.verified,
                lifecycle_state="approved",
                created_by="seed",
                updated_by="seed",
            )
        )
        session.add(
            DailyStrategyInstance(
                daily_strategy_instance_id=daily_strategy_instance_id,
                strategy_version_id=uuid4(),
                daily_rule_selection_id=daily_rule_selection_id,
                market_snapshot_id=market_snapshot_id,
                trade_date=date(2026, 6, 19),
                revision_no=1,
                risk_multiplier=1.0,
                position_limit=0.8,
                payload={},
                lifecycle_state="approved",
                created_by="seed",
                updated_by="seed",
            )
        )
        session.add(
            TradingDayPlan(
                trading_day_plan_id=trading_day_plan_id,
                daily_strategy_instance_id=daily_strategy_instance_id,
                trade_date=date(2026, 6, 19),
                revision_no=1,
                lifecycle_state="approved",
                payload={},
                created_by="seed",
                updated_by="seed",
            )
        )
        session.add(
            PostMarketReview(
                post_market_review_id=post_market_review_id,
                trading_day_plan_id=trading_day_plan_id,
                revision_no=1,
                market_snapshot_id=market_snapshot_id,
                market_state_id=market_state_id,
                signal_results_json={},
                attribution_json={},
                evidence_json={"source": "formal"},
                lifecycle_state="approved",
                quality_status=QualityStatus.verified,
                created_by="seed",
                updated_by="seed",
            )
        )
        await session.commit()

    return {
        "author_id": author_id,
        "rule_version_id": rule_version_id,
        "method_profile_version_id": method_profile_id,
        "rule_profile_version_id": rule_profile_id,
        "validated_profile_version_id": validated_profile_id,
        "dataset_snapshot_id": dataset_snapshot_id,
        "market_snapshot_id": market_snapshot_id,
        "applicability_profile_id": applicability_profile_id,
        "backtest_run_id": backtest_run_id,
        "backtest_result_id": backtest_result_id,
        "post_market_review_id": post_market_review_id,
    }


def _draft_request(deps: dict[str, UUID], *, business_key: str = "cn-swing-core", strategy_id: UUID | None = None):
    from src.services.strategy_center_service import StrategyDraftRequest

    return StrategyDraftRequest(
        strategy_id=strategy_id,
        business_key=business_key,
        schema_version="strategy-schema-v1",
        title="A股趋势轮动策略",
        summary="聚合规则池、作者画像和风险约束的正式策略草稿。",
        rule_memberships=[
            {
                "rule_version_id": str(deps["rule_version_id"]),
                "base_weight": 0.65,
                "status": "active",
                "configuration_json": {"position_role": "core"},
            }
        ],
        author_method_profile_version_id=str(deps["method_profile_version_id"]),
        author_rule_profile_version_id=str(deps["rule_profile_version_id"]),
        author_validated_profile_version_id=str(deps["validated_profile_version_id"]),
        risk_policy_json={
            "max_drawdown_limit": 0.08,
            "position_constraints": {"single_position_pct": 0.2, "total_position_pct": 0.8},
        },
        selection_policy_json={
            "market_state_selection_policy": {"preferred_states": ["强势上行"]},
            "degradation_policy": {"missing_canonical_data": "unavailable"},
        },
        universe_json={"market": "CN", "boards": ["主板", "创业板"]},
        evidence_json={
            "dataset_snapshot_id": str(deps["dataset_snapshot_id"]),
            "market_snapshot_ids": [str(deps["market_snapshot_id"])],
            "rule_applicability_profile_ids": [str(deps["applicability_profile_id"])],
            "backtest_run_ids": [str(deps["backtest_run_id"])],
            "backtest_result_ids": [str(deps["backtest_result_id"])],
        },
        reason="由正式规则和画像生成策略草稿",
    )


@pytest.mark.asyncio()
async def test_strategy_center_create_submit_publish_and_preserve_history(tmp_path: Path) -> None:
    from src.services.strategy_center_service import StrategyCenterService, StrategyTransitionRequest

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    deps = await _seed_dependencies(session_factory)
    service = StrategyCenterService(session_scope_factory=session_scope)

    draft = await service.create_draft(_draft_request(deps), actor_id="operator-a", actor_role="operator")
    assert draft.lifecycle_state == "draft"
    assert draft.version_no == 1
    assert draft.current_status.is_current is False
    assert draft.rule_pool[0]["rule_version_id"] == str(deps["rule_version_id"])
    assert draft.evidence.dataset_snapshot_id == str(deps["dataset_snapshot_id"])

    pending = await service.submit_for_review(
        draft.strategy_version_id,
        StrategyTransitionRequest(reason="提交审核"),
        actor_id="operator-a",
        actor_role="operator",
    )
    assert pending.lifecycle_state == "pending_review"

    published = await service.publish(
        pending.strategy_version_id,
        StrategyTransitionRequest(reason="审核通过后发布"),
        actor_id="reviewer-a",
        actor_role="operator",
    )
    assert published.lifecycle_state == "published"
    assert published.current_status.is_current is True

    revision = await service.create_draft(
        _draft_request(deps, strategy_id=UUID(draft.strategy_id)),
        actor_id="operator-a",
        actor_role="operator",
    )
    assert revision.version_no == 2
    assert revision.current_status.current_version_id == published.strategy_version_id

    revision = await service.submit_for_review(
        revision.strategy_version_id,
        StrategyTransitionRequest(reason="提交修订审核"),
        actor_id="operator-a",
        actor_role="operator",
    )
    revision = await service.publish(
        revision.strategy_version_id,
        StrategyTransitionRequest(reason="发布新正式版本"),
        actor_id="reviewer-a",
        actor_role="operator",
    )
    assert revision.current_status.is_current is True
    assert revision.current_status.current_version_id == revision.strategy_version_id
    assert revision.current_status.previous_current_version_id == published.strategy_version_id

    first_after = await service.get_version(published.strategy_version_id, actor_id="viewer-a", actor_role="viewer")
    assert first_after.lifecycle_state == "published"
    assert first_after.current_status.is_current is False

    listing = await service.list_versions(actor_id="viewer-a", actor_role="viewer")
    assert listing["state"] == "ready"
    assert listing["current_strategy"]["current_version_id"] == revision.strategy_version_id
    assert listing["count"] == 2

    await engine.dispose()


@pytest.mark.asyncio()
async def test_strategy_center_exposes_only_canonical_draft_inputs(tmp_path: Path) -> None:
    from src.services.strategy_center_service import StrategyCenterService

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    deps = await _seed_dependencies(session_factory)
    service = StrategyCenterService(session_scope_factory=session_scope)

    options = await service.get_draft_options(actor_id="viewer-a", actor_role="viewer")

    assert options["rule_options"][0]["rule_version_id"] == str(deps["rule_version_id"])
    assert options["author_profile_options"]["method"][0]["author_profile_version_id"] == str(deps["method_profile_version_id"])
    assert options["dataset_options"][0]["dataset_snapshot_id"] == str(deps["dataset_snapshot_id"])
    assert options["market_snapshot_options"][0]["market_snapshot_id"] == str(deps["market_snapshot_id"])
    assert options["rule_applicability_options"][0]["applicability_profile_id"] == str(deps["applicability_profile_id"])
    assert "trader_strategy_version_id" not in str(options)

    await engine.dispose()


@pytest.mark.asyncio()
async def test_strategy_center_validates_compares_diffs_and_rolls_back_with_audit(tmp_path: Path) -> None:
    from src.services.strategy_center_service import (
        StrategyCenterService,
        StrategyRollbackRequest,
        StrategyRuleMembershipInput,
        StrategyTransitionRequest,
        StrategyValidationRequest,
    )

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    deps = await _seed_dependencies(session_factory)
    service = StrategyCenterService(session_scope_factory=session_scope)

    first = await service.create_draft(_draft_request(deps), actor_id="operator-a", actor_role="operator")
    first = await service.submit_for_review(first.strategy_version_id, StrategyTransitionRequest(reason="提交审核"), actor_id="operator-a", actor_role="operator")
    first = await service.publish(first.strategy_version_id, StrategyTransitionRequest(reason="首次发布"), actor_id="reviewer-a", actor_role="operator")

    revision_request = _draft_request(deps, strategy_id=UUID(first.strategy_id))
    revision_request.title = "A股趋势轮动策略 v2"
    revision_request.summary = "加入趋势确认规则后的修订版本。"
    revision_request.rule_memberships = [
        StrategyRuleMembershipInput(
            rule_version_id=deps["rule_version_id"],
            base_weight=0.8,
            status="active",
            configuration_json={"position_role": "core", "confirm_trend": True},
        )
    ]
    revision = await service.create_draft(revision_request, actor_id="operator-a", actor_role="operator")

    validated = await service.validate_version(
        revision.strategy_version_id,
        StrategyValidationRequest(reason="校验候选策略"),
        actor_id="reviewer-b",
        actor_role="operator",
    )
    assert validated.validation.state == "passed"
    assert validated.validation.backtest.out_of_sample_state == "available"
    assert validated.validation.rule_applicability.coverage_ratio == 1.0
    assert validated.validation.sample_coverage.state == "sufficient"
    assert validated.validation.reviewer_decision == "approved"

    comparison = await service.compare_with_current(revision.strategy_version_id, actor_id="viewer-a", actor_role="viewer")
    assert comparison["state"] == "ready"
    assert comparison["current_version"]["strategy_version_id"] == first.strategy_version_id
    assert comparison["candidate_version"]["strategy_version_id"] == revision.strategy_version_id
    assert comparison["delta"]["rule_weight_changes"] == 1

    diff = await service.diff_versions(revision.strategy_version_id, actor_id="viewer-a", actor_role="viewer")
    assert diff["base_version"]["strategy_version_id"] == first.strategy_version_id
    assert any(change["field"] == "title" for change in diff["changes"])
    assert any(change["field"] == "rule_pool" for change in diff["changes"])

    revision = await service.submit_for_review(revision.strategy_version_id, StrategyTransitionRequest(reason="提交修订审核"), actor_id="operator-a", actor_role="operator")
    revision = await service.publish(revision.strategy_version_id, StrategyTransitionRequest(reason="发布修订版本"), actor_id="reviewer-b", actor_role="operator")
    assert revision.current_status.is_current is True

    rolled_back = await service.rollback_to_version(
        first.strategy_version_id,
        StrategyRollbackRequest(reason="新版本样本覆盖不足，回退到上一正式版本"),
        actor_id="reviewer-c",
        actor_role="operator",
    )
    assert rolled_back.strategy_version_id == first.strategy_version_id
    assert rolled_back.current_status.is_current is True
    assert rolled_back.current_status.previous_current_version_id == revision.strategy_version_id

    revision_after = await service.get_version(revision.strategy_version_id, actor_id="viewer-a", actor_role="viewer")
    assert revision_after.current_status.is_current is False

    async with session_factory() as session:
        versions = list((await session.execute(select(StrategyVersion))).scalars().all())
        assert len(versions) == 2
        audits = list((await session.execute(select(StrategyVersionAudit).order_by(StrategyVersionAudit.created_at.asc()))).scalars().all())
        assert any(audit.transition == "validated" for audit in audits)
        rollback_audit = next(audit for audit in audits if audit.transition == "rollback_to_current")
        assert rollback_audit.reason == "新版本样本覆盖不足，回退到上一正式版本"
        assert rollback_audit.before_state_json["current_version_id"] == revision.strategy_version_id
        assert rollback_audit.after_state_json["current_version_id"] == first.strategy_version_id

    await engine.dispose()


@pytest.mark.asyncio()
async def test_strategy_center_proposal_lifecycle_accepts_to_new_draft_without_publishing(tmp_path: Path) -> None:
    from src.services.strategy_center_service import (
        StrategyCenterService,
        StrategyProposalAcceptRequest,
        StrategyProposalCreateRequest,
        StrategyProposalReviewRequest,
        StrategyTransitionRequest,
    )

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    deps = await _seed_dependencies(session_factory)
    service = StrategyCenterService(session_scope_factory=session_scope)

    published = await service.create_draft(_draft_request(deps), actor_id="operator-a", actor_role="operator")
    published = await service.submit_for_review(
        published.strategy_version_id,
        StrategyTransitionRequest(reason="提交审核"),
        actor_id="operator-a",
        actor_role="operator",
    )
    published = await service.publish(
        published.strategy_version_id,
        StrategyTransitionRequest(reason="审核通过后发布"),
        actor_id="reviewer-a",
        actor_role="operator",
    )
    current_before = published.current_status.current_version_id

    proposal = await service.create_proposal(
        StrategyProposalCreateRequest(
            post_market_review_id=deps["post_market_review_id"],
            affected_strategy_version_id=UUID(published.strategy_version_id),
            rationale="近期样本回撤扩大，建议降低核心规则权重。",
            trigger_type="manual_review",
            confidence=0.82,
            proposed_changes={
                "title": "A股趋势轮动策略 v2 草稿",
                "summary": "降低核心规则仓位并保留当前正式版本不变。",
                "proposed_weight_changes": [
                    {"rule_version_id": str(deps["rule_version_id"]), "base_weight": 0.5}
                ],
            },
            evidence_json={"evidence_state": "partial", "limitations": ["样本外验证待补齐"]},
        ),
        actor_id="operator-a",
        actor_role="operator",
    )
    assert proposal.lifecycle_state == "draft"
    assert proposal.accepted_draft_version_id is None
    assert proposal.evidence_state == "partial"

    in_review = await service.review_proposal(
        proposal.proposal_id,
        StrategyProposalReviewRequest(action="start_review", reason="开始复核"),
        actor_id="reviewer-a",
        actor_role="operator",
    )
    assert in_review.lifecycle_state == "in_review"

    accepted = await service.accept_proposal_to_draft(
        proposal.proposal_id,
        StrategyProposalAcceptRequest(reason="生成草稿继续复核"),
        actor_id="reviewer-a",
        actor_role="operator",
    )
    assert accepted.lifecycle_state == "accepted"
    assert accepted.accepted_draft_version_id is not None
    assert accepted.affected_strategy_version.strategy_version_id == published.strategy_version_id

    listing = await service.list_versions(actor_id="viewer-a", actor_role="viewer")
    assert listing["current_strategy"]["current_version_id"] == current_before
    assert len(listing["items"]) == 2
    linked_draft = next(item for item in listing["items"] if item["strategy_version_id"] == accepted.accepted_draft_version_id)
    assert linked_draft["lifecycle_state"] == "draft"
    assert linked_draft["current_status"]["is_current"] is False

    published_after = await service.get_version(published.strategy_version_id, actor_id="viewer-a", actor_role="viewer")
    assert published_after.current_status.current_version_id == current_before
    assert published_after.current_status.is_current is True

    async with session_factory() as session:
        proposal_row = await session.get(OptimizationProposal, UUID(proposal.proposal_id))
        assert proposal_row is not None
        assert proposal_row.accepted_draft_version_id == UUID(accepted.accepted_draft_version_id)
        events = list((await session.execute(select(LifecycleEvent).order_by(LifecycleEvent.occurred_at.asc()))).scalars().all())
        assert any(event.to_state == "accepted" for event in events)

    await engine.dispose()


@pytest.mark.asyncio()
async def test_strategy_center_proposal_can_link_existing_draft_without_mutating_current(tmp_path: Path) -> None:
    from src.services.strategy_center_service import (
        StrategyCenterService,
        StrategyProposalAcceptRequest,
        StrategyProposalCreateRequest,
        StrategyProposalReviewRequest,
        StrategyTransitionRequest,
    )

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    deps = await _seed_dependencies(session_factory)
    service = StrategyCenterService(session_scope_factory=session_scope)

    published = await service.create_draft(_draft_request(deps), actor_id="operator-a", actor_role="operator")
    published = await service.submit_for_review(published.strategy_version_id, StrategyTransitionRequest(reason="提交审核"), actor_id="operator-a", actor_role="operator")
    published = await service.publish(published.strategy_version_id, StrategyTransitionRequest(reason="审核通过后发布"), actor_id="reviewer-a", actor_role="operator")

    existing_draft = await service.create_draft(
        _draft_request(deps, strategy_id=UUID(published.strategy_id)),
        actor_id="operator-a",
        actor_role="operator",
    )

    proposal = await service.create_proposal(
        StrategyProposalCreateRequest(
            post_market_review_id=deps["post_market_review_id"],
            affected_strategy_version_id=UUID(published.strategy_version_id),
            rationale="已有人工草稿，建议把本次修订挂接到现有草稿继续处理。",
            trigger_type="manual_review",
            confidence=0.7,
            proposed_changes={"summary": "沿用现有草稿继续完善。"},
            evidence_json={"evidence_state": "ready"},
        ),
        actor_id="operator-a",
        actor_role="operator",
    )
    proposal = await service.review_proposal(
        proposal.proposal_id,
        StrategyProposalReviewRequest(action="start_review", reason="开始复核"),
        actor_id="reviewer-a",
        actor_role="operator",
    )
    accepted = await service.accept_proposal_to_draft(
        proposal.proposal_id,
        StrategyProposalAcceptRequest(
            reason="关联现有草稿",
            linked_draft_version_id=UUID(existing_draft.strategy_version_id),
        ),
        actor_id="reviewer-a",
        actor_role="operator",
    )
    assert accepted.accepted_draft_version_id == existing_draft.strategy_version_id

    published_after = await service.get_version(published.strategy_version_id, actor_id="viewer-a", actor_role="viewer")
    assert published_after.current_status.is_current is True
    assert published_after.current_status.current_version_id == published.strategy_version_id

    await engine.dispose()


@pytest.mark.asyncio()
async def test_strategy_center_validation_marks_missing_canonical_coverage_as_insufficient(tmp_path: Path) -> None:
    from src.services.strategy_center_service import StrategyCenterService, StrategyValidationRequest

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    deps = await _seed_dependencies(session_factory)
    service = StrategyCenterService(session_scope_factory=session_scope)

    request = _draft_request(deps)
    request.evidence_json = {
        "dataset_snapshot_id": str(deps["dataset_snapshot_id"]),
        "market_snapshot_ids": [],
        "rule_applicability_profile_ids": [],
        "backtest_run_ids": [str(deps["backtest_run_id"])],
        "backtest_result_ids": [str(deps["backtest_result_id"])],
    }
    draft = await service.create_draft(request, actor_id="operator-a", actor_role="operator")

    validated = await service.validate_version(
        draft.strategy_version_id,
        StrategyValidationRequest(reason="缺少正式适用性覆盖"),
        actor_id="reviewer-a",
        actor_role="operator",
    )

    assert validated.validation.state == "insufficient_coverage"
    assert validated.validation.reviewer_decision == "review_required"
    assert validated.validation.rule_applicability.coverage_ratio == 0.0
    assert validated.validation.sample_coverage.state == "sufficient"

    await engine.dispose()
