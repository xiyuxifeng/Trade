from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import JSON, func, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

from src.domain.enums import (
    AuthorProfileKind,
    DailyRuleSelectionState,
    FormalLifecycleState,
    QualityStatus,
    SignalState,
    TradingDayPlanState,
)
from src.models.market_data_snapshot import MarketSnapshot
from src.models.market_data_snapshot_item import MarketSnapshotItem
from src.models.market_data_snapshot_section import MarketSnapshotSection
from src.models.market_regime_record import MarketRegimeRecord, RegimeLabelRecord
from src.models.signal import Signal
from src.models.stage2_canonical import (
    AuthorProfileVersion,
    Authors,
    DailyRuleSelection,
    DailyRuleSelectionItem,
    DailyStrategyInstance,
    DatasetLifecycleState,
    DatasetSnapshot,
    LifecycleEvent,
    OptimizationProposal,
    PostMarketReview,
    Rule,
    RuleVersion,
    Strategy,
    StrategyRuleMembership,
    StrategyVersion,
    TradingDayPlan,
)
from src.services.daily_trading_plan_service import DailyTradingPlanService, TradingDayPlanReviewRequest
from src.services.post_close_actuals_service import (
    POST_CLOSE_ACTUALS_CONTRACT_VERSION,
    POST_CLOSE_ACTUALS_SECTION_ID,
    OptimizationProposalAcceptRequest,
    OptimizationProposalGenerationRequest,
    OptimizationProposalReviewRequest,
    PostMarketReviewService,
    SignalAttributionEvaluationRequest,
    SignalOutcomeEvaluationRequest,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, compiler, **kw):
    return compiler.visit_JSON(None, **kw)


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_type, compiler, **kw):
    return compiler.visit_JSON(None, **kw)


async def _build_session_factory(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'daily_trading_plan.db'}")
    Signal.__table__.c.rule_version_ids.type = JSON()
    async with engine.begin() as conn:
        await conn.run_sync(Authors.__table__.create)
        await conn.run_sync(Rule.__table__.create)
        await conn.run_sync(RuleVersion.__table__.create)
        await conn.run_sync(DatasetSnapshot.__table__.create)
        await conn.run_sync(MarketSnapshot.__table__.create)
        await conn.run_sync(MarketSnapshotSection.__table__.create)
        await conn.run_sync(MarketSnapshotItem.__table__.create)
        await conn.run_sync(MarketRegimeRecord.__table__.create)
        await conn.run_sync(AuthorProfileVersion.__table__.create)
        await conn.run_sync(Strategy.__table__.create)
        await conn.run_sync(StrategyVersion.__table__.create)
        await conn.run_sync(StrategyRuleMembership.__table__.create)
        await conn.run_sync(DailyRuleSelection.__table__.create)
        await conn.run_sync(DailyRuleSelectionItem.__table__.create)
        await conn.run_sync(DailyStrategyInstance.__table__.create)
        await conn.run_sync(TradingDayPlan.__table__.create)
        await conn.run_sync(Signal.__table__.create)
        await conn.run_sync(PostMarketReview.__table__.create)
        await conn.run_sync(OptimizationProposal.__table__.create)
        await conn.run_sync(LifecycleEvent.__table__.create)
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


def _selection_view(
    *,
    trade_date: str,
    strategy_version_id: str,
    daily_rule_selection_id: str,
    dataset_snapshot_id: str,
    market_snapshot_id: str,
    market_state_id: str,
    status: str = "degraded",
    generated: bool = True,
    degraded_inputs: list[str] | None = None,
    unresolved_inputs: list[str] | None = None,
):
    degraded_inputs = degraded_inputs or []
    unresolved_inputs = unresolved_inputs or []
    return SimpleNamespace(
        state="partial" if status == "degraded" else "ready",
        selection_status=status,
        generated=generated,
        trade_date=trade_date,
        happened="部分规则因为样本不足被降权。",
        affected="今日规则选择可继续，但需要关注降级输入。",
        repair_guidance="先补齐适用性证据，或按降级结果继续。",
        daily_rule_selection_id=daily_rule_selection_id,
        revision_no=1,
        strategy_version_id=strategy_version_id,
        quality_status="partial" if status == "degraded" else "verified",
        readiness_status="degraded" if degraded_inputs else "ready",
        enabled_rules=[
            SimpleNamespace(
                rule_version_id="11111111-1111-1111-1111-111111111111",
                strategy_rule_membership_id="membership-1",
                decision="selected",
                controlling_priority_tier="current_market_state",
                controlling_priority_label="当前市场状态",
                evidence_ids=["applicability-1", market_state_id],
                quality_states=["verified", "ready"],
                reason_tiers=["formal_rule_applicability", "current_market_state"],
                reason_list=["规则适用性已发布。", "当前市场状态与规则适配。"],
                degraded_inputs=[],
                unresolved_inputs=[],
                model_dump=lambda mode="json": {
                    "rule_version_id": "11111111-1111-1111-1111-111111111111",
                    "strategy_rule_membership_id": "membership-1",
                    "decision": "selected",
                    "controlling_priority_tier": "current_market_state",
                    "controlling_priority_label": "当前市场状态",
                    "evidence_ids": ["applicability-1", market_state_id],
                    "quality_states": ["verified", "ready"],
                    "reason_tiers": ["formal_rule_applicability", "current_market_state"],
                    "reason_list": ["规则适用性已发布。", "当前市场状态与规则适配。"],
                    "degraded_inputs": [],
                    "unresolved_inputs": [],
                },
            )
        ],
        reduced_rules=[
            SimpleNamespace(
                rule_version_id="22222222-2222-2222-2222-222222222222",
                strategy_rule_membership_id="membership-2",
                decision="reduced",
                controlling_priority_tier="formal_rule_applicability",
                controlling_priority_label="正式规则适用性",
                evidence_ids=["applicability-2"],
                quality_states=["partial"],
                reason_tiers=["formal_rule_applicability"],
                reason_list=["样本不足，今日降权处理。"],
                degraded_inputs=list(degraded_inputs),
                unresolved_inputs=[],
                model_dump=lambda mode="json": {
                    "rule_version_id": "22222222-2222-2222-2222-222222222222",
                    "strategy_rule_membership_id": "membership-2",
                    "decision": "reduced",
                    "controlling_priority_tier": "formal_rule_applicability",
                    "controlling_priority_label": "正式规则适用性",
                    "evidence_ids": ["applicability-2"],
                    "quality_states": ["partial"],
                    "reason_tiers": ["formal_rule_applicability"],
                    "reason_list": ["样本不足，今日降权处理。"],
                    "degraded_inputs": list(degraded_inputs),
                    "unresolved_inputs": [],
                },
            )
        ],
        suspended_rules=[],
        traceability=SimpleNamespace(
            trade_date=trade_date,
            strategy_version_id=strategy_version_id,
            dataset_snapshot_id=dataset_snapshot_id,
            market_snapshot_id=market_snapshot_id,
            market_state_id=market_state_id,
            rule_applicability_profile_ids=["applicability-1", "applicability-2"],
            author_method_profile_version_id="66666666-6666-6666-6666-666666666666",
            author_rule_profile_version_id="77777777-7777-7777-7777-777777777777",
            author_validated_profile_version_id="88888888-8888-8888-8888-888888888888",
            data_quality_state="degraded" if degraded_inputs else "ready",
            model_dump=lambda mode="json": {
                "trade_date": trade_date,
                "strategy_version_id": strategy_version_id,
                "dataset_snapshot_id": dataset_snapshot_id,
                "market_snapshot_id": market_snapshot_id,
                "market_state_id": market_state_id,
                "rule_applicability_profile_ids": ["applicability-1", "applicability-2"],
                "author_method_profile_version_id": "66666666-6666-6666-6666-666666666666",
                "author_rule_profile_version_id": "77777777-7777-7777-7777-777777777777",
                "author_validated_profile_version_id": "88888888-8888-8888-8888-888888888888",
                "data_quality_state": "degraded" if degraded_inputs else "ready",
            },
        ),
        degraded_inputs=list(degraded_inputs),
        unresolved_inputs=list(unresolved_inputs),
    )


class _FakeSelectionService:
    def __init__(self, selection):
        self.selection = selection

    async def get_rule_selection(self, trade_date: str, *, actor_id: str, actor_role: str):
        del trade_date, actor_id, actor_role
        return self.selection


async def _seed_runtime_bundle(session_factory: async_sessionmaker[AsyncSession]) -> dict[str, str]:
    now = datetime(2026, 6, 21, 8, 30, tzinfo=UTC)
    author_id = uuid4()
    strategy_id = uuid4()
    strategy_version_id = uuid4()
    dataset_snapshot_id = uuid4()
    market_snapshot_id = uuid4()
    market_state_id = uuid4()
    selection_id = uuid4()
    rule_id_1 = uuid4()
    rule_id_2 = uuid4()
    method_profile_id = UUID("66666666-6666-6666-6666-666666666666")
    rule_profile_id = UUID("77777777-7777-7777-7777-777777777777")
    validated_profile_id = UUID("88888888-8888-8888-8888-888888888888")

    async with session_factory() as session:
        session.add(Authors(author_id=author_id, source="seed", source_author_key="author-1", display_name="测试作者"))
        session.add(
            Rule(
                rule_id=rule_id_1,
                business_key="rule-1",
                current_published_version_id=UUID("11111111-1111-1111-1111-111111111111"),
                created_at=now,
                created_by="seed",
                updated_at=now,
                updated_by="seed",
            )
        )
        session.add(
            Rule(
                rule_id=rule_id_2,
                business_key="rule-2",
                current_published_version_id=UUID("22222222-2222-2222-2222-222222222222"),
                created_at=now,
                created_by="seed",
                updated_at=now,
                updated_by="seed",
            )
        )
        session.add(
            RuleVersion(
                rule_version_id=UUID("11111111-1111-1111-1111-111111111111"),
                rule_id=rule_id_1,
                version_no=1,
                canonical_fingerprint="rule-fingerprint-1",
                schema_version="rule-schema-v1",
                lifecycle_state=FormalLifecycleState.published,
                title="竞价强势跟随",
                description="盘前竞价强势跟随",
                rule_type="entry",
                instrument_scope={"market": "CN"},
                condition_json={"indicator": "竞价强度"},
                action_json={"decision": "BUY"},
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
            RuleVersion(
                rule_version_id=UUID("22222222-2222-2222-2222-222222222222"),
                rule_id=rule_id_2,
                version_no=1,
                canonical_fingerprint="rule-fingerprint-2",
                schema_version="rule-schema-v1",
                lifecycle_state=FormalLifecycleState.published,
                title="样本不足降权规则",
                description="样本不足降权规则",
                rule_type="entry",
                instrument_scope={"market": "CN"},
                condition_json={"summary": "样本不足时缩减执行"},
                action_json={"decision": "BUY"},
                parameter_json={"lookback_days": 10},
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
                ohlcv_manifest={"coverage": "complete"},
                kaipan_manifest={"pre_market_trade_date": "2026-06-21"},
                benchmark_symbol="000300.SH",
                market_state_definition_version="market-state-v2",
                available_at=now,
                frozen_at=now,
                lifecycle_state=DatasetLifecycleState.ready,
                storage_ref={"logical_dataset_id": "dataset-ready"},
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
                section_count=1,
                available_section_count=1,
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
            MarketSnapshotSection(
                snapshot_id="market-snapshot-2026-06-21-am",
                section_id="strong_symbols",
                trade_date=date(2026, 6, 21),
                slot="09-25",
                source_dataset="strong_symbols",
                provider="kaipan",
                source_time=now,
                captured_at=now,
                available_at=now,
                record_count=2,
                quality_status="ok",
                storage_ref={},
                payload_json={
                    "symbols": [
                        {"symbol": "000001.SZ", "name": "平安银行", "score": 0.91},
                        {"symbol": "600000.SH", "name": "浦发银行", "score": 0.82},
                    ]
                },
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
                labels=[RegimeLabelRecord(label="强势上行", label_type="primary", score=0.9, confidence=0.9, status="ready", reason="趋势向上")],
                features=[],
                confidence=0.78,
                quality_status="ready",
                storage_ref={"market_state_id": "market-state-ready"},
                available_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        for profile_id in (method_profile_id, rule_profile_id, validated_profile_id):
            session.add(
                AuthorProfileVersion(
                    author_profile_version_id=profile_id,
                    author_profile_id=uuid4(),
                    author_id=author_id,
                    profile_kind=(
                        AuthorProfileKind.method
                        if profile_id == method_profile_id
                        else (AuthorProfileKind.rule if profile_id == rule_profile_id else AuthorProfileKind.validated)
                    ),
                    version_no=1,
                    schema_version="author-profile-v1",
                    lifecycle_state=FormalLifecycleState.published,
                    payload={"summary": "seed"},
                    evidence_json={"source": "formal"},
                    source_article_ids={},
                    source_rule_version_ids={},
                    source_rule_family_ids={},
                    source_applicability_profile_ids={},
                    source_backtest_run_ids={},
                    source_backtest_result_ids={},
                    quality_status=QualityStatus.verified,
                    created_by="seed",
                    updated_by="seed",
                )
            )
        session.add(
            Strategy(
                strategy_id=strategy_id,
                business_key="strategy-main",
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
                version_no=1,
                schema_version="strategy-v1",
                lifecycle_state=FormalLifecycleState.published,
                title="正式策略",
                summary="测试正式策略",
                risk_policy_json={"stop_loss_pct": "5%", "take_profit_pct": "12%", "position_limit": 0.5},
                selection_policy_json={},
                universe_json={},
                author_method_profile_version_id=method_profile_id,
                author_rule_profile_version_id=rule_profile_id,
                author_validated_profile_version_id=validated_profile_id,
                evidence_json={
                    "validation_summary": {
                        "state": "passed",
                        "label": "验证通过",
                        "reviewer_decision": "approved",
                        "reviewer_decision_label": "已批准",
                        "dataset_binding": {"state": "ready", "dataset_snapshot_id": str(dataset_snapshot_id), "market_state_definition_version": "market-state-v2"},
                        "market_snapshot_binding": {"state": "ready", "market_snapshot_ids": [str(market_snapshot_id)]},
                        "backtest": {
                            "state": "unavailable",
                            "out_of_sample_state": "unavailable",
                            "backtest_run_ids": [],
                            "backtest_result_ids": [],
                            "requested_level": None,
                            "effective_level": None,
                            "annual_return": None,
                            "max_drawdown": None,
                            "win_rate": None,
                        },
                        "rule_applicability": {
                            "state": "unavailable",
                            "covered_rule_count": 0,
                            "total_rule_count": 0,
                            "coverage_ratio": 0.0,
                            "uncovered_rule_version_ids": [],
                        },
                        "sample_coverage": {"state": "unknown", "sample_count": None, "insufficient_sample": False},
                        "data_quality": {"state": "verified", "warnings": [], "limitations": []},
                    }
                },
                quality_status=QualityStatus.verified,
                review_status="approved",
                created_by="seed",
                updated_by="seed",
            )
        )
        session.add(
            StrategyRuleMembership(
                membership_id=UUID("aaaaaaaa-1111-1111-1111-111111111111"),
                strategy_version_id=strategy_version_id,
                rule_version_id=UUID("11111111-1111-1111-1111-111111111111"),
                base_weight=0.6,
                status="active",
                configuration_json={"source": "seed"},
            )
        )
        session.add(
            StrategyRuleMembership(
                membership_id=UUID("bbbbbbbb-2222-2222-2222-222222222222"),
                strategy_version_id=strategy_version_id,
                rule_version_id=UUID("22222222-2222-2222-2222-222222222222"),
                base_weight=0.4,
                status="active",
                configuration_json={"source": "seed"},
            )
        )
        session.add(
            DailyRuleSelection(
                daily_rule_selection_id=selection_id,
                strategy_version_id=strategy_version_id,
                market_state_id=market_state_id,
                trade_date=date(2026, 6, 21),
                revision_no=1,
                selected_rules_json={"selection_context": {"trade_date": "2026-06-21"}},
                reduced_rules_json={"selection_context": {"trade_date": "2026-06-21"}},
                blocked_rules_json={"selection_context": {"trade_date": "2026-06-21"}},
                quality_status=QualityStatus.partial,
                lifecycle_state=DailyRuleSelectionState.generated,
                created_by="seed",
                updated_by="seed",
            )
        )
        session.add(
            DailyRuleSelectionItem(
                daily_rule_selection_id=selection_id,
                rule_version_id=UUID("11111111-1111-1111-1111-111111111111"),
                decision="selected",
                payload_json={"source": "formal_daily_rule_selection"},
            )
        )
        session.add(
            DailyRuleSelectionItem(
                daily_rule_selection_id=selection_id,
                rule_version_id=UUID("22222222-2222-2222-2222-222222222222"),
                decision="reduced",
                payload_json={"source": "formal_daily_rule_selection"},
            )
        )
        await session.commit()

    return {
        "trade_date": "2026-06-21",
        "strategy_version_id": str(strategy_version_id),
        "daily_rule_selection_id": str(selection_id),
        "dataset_snapshot_id": str(dataset_snapshot_id),
        "market_snapshot_id": str(market_snapshot_id),
        "market_state_id": str(market_state_id),
        "strategy_id": str(strategy_id),
    }


@pytest.mark.asyncio()
async def test_daily_trading_plan_generates_runtime_objects_without_mutating_formal_strategy(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    selection_service = _FakeSelectionService(
        _selection_view(
            trade_date=ids["trade_date"],
            strategy_version_id=ids["strategy_version_id"],
            daily_rule_selection_id=ids["daily_rule_selection_id"],
            dataset_snapshot_id=ids["dataset_snapshot_id"],
            market_snapshot_id=ids["market_snapshot_id"],
            market_state_id=ids["market_state_id"],
            degraded_inputs=["insufficient_sample"],
        )
    )
    service = DailyTradingPlanService(
        session_scope_factory=session_scope,
        daily_rule_selection_service=selection_service,
    )

    result = await service.get_trading_day_plan(ids["trade_date"], actor_id="tester", actor_role="operator")

    assert result.generated is True
    assert result.plan_status == "degraded"
    assert result.daily_strategy_instance_id is not None
    assert result.trading_day_plan_id is not None
    assert result.traceability is not None
    assert result.traceability.daily_rule_selection_id == ids["daily_rule_selection_id"]
    assert result.traceability.market_snapshot_id == ids["market_snapshot_id"]
    assert result.market_judgment.summary.startswith("强势上行")
    assert result.candidate_symbols[0].symbol == "000001.SZ"
    assert result.signals
    assert result.signals[0].side == "BUY"
    assert "降级输入" in " ".join(result.risk_warnings.details)

    async with session_factory() as session:
        strategy = await session.get(Strategy, UUID(ids["strategy_id"]))
        assert str(strategy.current_published_version_id) == ids["strategy_version_id"]
        assert await session.scalar(select(func.count()).select_from(DailyStrategyInstance)) == 1
        assert await session.scalar(select(func.count()).select_from(TradingDayPlan)) == 1
        assert await session.scalar(select(func.count()).select_from(Signal)) == 2
        assert await session.scalar(select(func.count()).select_from(PostMarketReview)) == 0
        assert await session.scalar(select(func.count()).select_from(OptimizationProposal)) == 0

    await engine.dispose()


@pytest.mark.asyncio()
async def test_daily_trading_plan_does_not_generate_when_selection_is_blocked(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    blocked_selection = _selection_view(
        trade_date=ids["trade_date"],
        strategy_version_id=ids["strategy_version_id"],
        daily_rule_selection_id=ids["daily_rule_selection_id"],
        dataset_snapshot_id=ids["dataset_snapshot_id"],
        market_snapshot_id=ids["market_snapshot_id"],
        market_state_id=ids["market_state_id"],
        status="blocked",
        generated=False,
    )
    service = DailyTradingPlanService(
        session_scope_factory=session_scope,
        daily_rule_selection_service=_FakeSelectionService(blocked_selection),
    )

    result = await service.get_trading_day_plan(ids["trade_date"], actor_id="tester", actor_role="viewer")

    assert result.generated is False
    assert result.plan_status == "blocked"
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(DailyStrategyInstance)) == 0
        assert await session.scalar(select(func.count()).select_from(TradingDayPlan)) == 0
        assert await session.scalar(select(func.count()).select_from(Signal)) == 0

    await engine.dispose()


@pytest.mark.asyncio()
async def test_daily_trading_plan_review_updates_plan_and_signal_states(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    selection = _selection_view(
        trade_date=ids["trade_date"],
        strategy_version_id=ids["strategy_version_id"],
        daily_rule_selection_id=ids["daily_rule_selection_id"],
        dataset_snapshot_id=ids["dataset_snapshot_id"],
        market_snapshot_id=ids["market_snapshot_id"],
        market_state_id=ids["market_state_id"],
    )
    service = DailyTradingPlanService(
        session_scope_factory=session_scope,
        daily_rule_selection_service=_FakeSelectionService(selection),
    )

    await service.get_trading_day_plan(ids["trade_date"], actor_id="tester", actor_role="operator")
    approved = await service.review_trading_day_plan(
        ids["trade_date"],
        actor_id="reviewer",
        actor_role="operator",
        request=TradingDayPlanReviewRequest(action="approve"),
    )

    assert approved.approval_state == "approved"
    assert approved.plan_lifecycle_state == TradingDayPlanState.approved.value
    async with session_factory() as session:
        signal_states = [item.signal_state for item in (await session.scalars(select(Signal))).all()]
        assert signal_states
        assert all(getattr(item, "value", item) == "approved" for item in signal_states)

    await engine.dispose()


def _actual_payload(
    *,
    symbol: str,
    trade_date: str,
    dataset_snapshot_id: str,
    dataset_content_fingerprint: str,
    row_fingerprint: str,
    previous_close: str | None = "10",
) -> dict[str, object]:
    now = "2026-06-21T08:30:00+00:00"
    return {
        "symbol": symbol,
        "trade_date": trade_date,
        "open": "10.20",
        "high": "11.00",
        "low": "9.80",
        "close": "10.50",
        "previous_close": previous_close,
        "volume": "1000000",
        "turnover": "10500000",
        "exchange": symbol.split(".")[-1],
        "asset_type": "stock",
        "frequency": "1d",
        "adjustment_policy": "none",
        "source": "canonical_ohlcv_snapshot",
        "source_time": now,
        "captured_at": now,
        "ingested_at": now,
        "available_at": now,
        "frozen_at": now,
        "dataset_snapshot_id": dataset_snapshot_id,
        "dataset_content_fingerprint": dataset_content_fingerprint,
        "row_fingerprint": row_fingerprint,
        "quality_state": "ready",
        "availability_state": "ready",
        "evidence_window": "daily_bar",
        "intraday_approximation": True,
        "actuals_contract_version": POST_CLOSE_ACTUALS_CONTRACT_VERSION,
    }


async def _approve_plan(session_scope, ids: dict[str, str]) -> str:
    selection = _selection_view(
        trade_date=ids["trade_date"],
        strategy_version_id=ids["strategy_version_id"],
        daily_rule_selection_id=ids["daily_rule_selection_id"],
        dataset_snapshot_id=ids["dataset_snapshot_id"],
        market_snapshot_id=ids["market_snapshot_id"],
        market_state_id=ids["market_state_id"],
    )
    service = DailyTradingPlanService(
        session_scope_factory=session_scope,
        daily_rule_selection_service=_FakeSelectionService(selection),
    )
    await service.get_trading_day_plan(ids["trade_date"], actor_id="tester", actor_role="operator")
    approved = await service.review_trading_day_plan(
        ids["trade_date"],
        actor_id="reviewer",
        actor_role="operator",
        request=TradingDayPlanReviewRequest(action="approve"),
    )
    assert approved.trading_day_plan_id is not None
    return approved.trading_day_plan_id


async def _set_signal_baseline(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    entry_price: dict[str, object],
    symbol: str | None = None,
) -> None:
    async with session_factory() as session:
        stmt = select(Signal)
        if symbol is not None:
            stmt = stmt.where(Signal.symbol == symbol)
        signals = list((await session.scalars(stmt)).all())
        for signal in signals:
            signal.entry_price = dict(entry_price)
        await session.commit()


async def _seed_post_close_actuals(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    missing_symbols: list[str] | None = None,
    conflict_symbols: list[str] | None = None,
    previous_close: str | None = "10",
) -> str:
    now = datetime(2026, 6, 21, 17, 30, tzinfo=UTC)
    dataset_snapshot_id = uuid4()
    dataset_content_fingerprint = "post-close-dataset-fingerprint-1"
    snapshot_id = uuid4()
    snapshot_key = "market-snapshot-2026-06-21-post-close"
    missing_symbols = missing_symbols or []
    conflict_symbols = conflict_symbols or []
    payloads = [
        _actual_payload(
            symbol=symbol,
            trade_date="2026-06-21",
            dataset_snapshot_id=str(dataset_snapshot_id),
            dataset_content_fingerprint=dataset_content_fingerprint,
            row_fingerprint=f"row-{symbol}",
            previous_close=previous_close,
        )
        for symbol in ("000001.SZ", "600000.SH")
        if symbol not in missing_symbols
    ]
    async with session_factory() as session:
        session.add(
            DatasetSnapshot(
                dataset_snapshot_id=dataset_snapshot_id,
                content_fingerprint=dataset_content_fingerprint,
                trade_date=date(2026, 6, 21),
                market="CN",
                dataset_type="ohlcv_daily",
                date_from=date(2026, 6, 21),
                date_to=date(2026, 6, 21),
                symbol_manifest={"symbols": ["000001.SZ", "600000.SH"]},
                ohlcv_manifest={"row_count": len(payloads), "row_fingerprints": [item["row_fingerprint"] for item in payloads]},
                kaipan_manifest={},
                benchmark_symbol="000300.SH",
                market_state_definition_version="market-state-v2",
                available_at=now,
                frozen_at=now,
                lifecycle_state=DatasetLifecycleState.ready,
                storage_ref={"logical_dataset_id": "post-close-ohlcv"},
            )
        )
        section_payload = {
            "actuals_contract_version": POST_CLOSE_ACTUALS_CONTRACT_VERSION,
            "dataset_snapshot_id": str(dataset_snapshot_id),
            "dataset_content_fingerprint": dataset_content_fingerprint,
            "row_count": len(payloads),
            "missing_symbols": missing_symbols,
            "conflict_symbols": conflict_symbols,
            "quality_summary": {"ready": len(payloads), "missing": len(missing_symbols), "conflict": len(conflict_symbols)},
            "row_fingerprints": {item["symbol"]: item["row_fingerprint"] for item in payloads},
        }
        section_fingerprint = f"section-{len(payloads)}-{len(missing_symbols)}"
        session.add(
            MarketSnapshot(
                id=snapshot_id,
                snapshot_id=snapshot_key,
                trade_date=date(2026, 6, 21),
                market="CN",
                profile_id="profile-default",
                data_version="post-close-actuals-v1",
                slot="17-30",
                quality_status="ready" if not missing_symbols else "partial",
                provider_sources=["canonical_ohlcv_snapshot"],
                section_count=1,
                available_section_count=1,
                partial_section_count=0 if not missing_symbols else 1,
                missing_section_count=0,
                storage_ref={"snapshot_id": snapshot_key, "contract": POST_CLOSE_ACTUALS_CONTRACT_VERSION},
                data_quality={"state": "ready" if not missing_symbols else "partial"},
                captured_at=now,
                ingested_at=now,
                available_at=now,
                effective_at=now,
                frozen_at=now,
                content_fingerprint=f"snapshot-content-{section_fingerprint}",
                manifest_json={"sections": {POST_CLOSE_ACTUALS_SECTION_ID: section_payload}},
            )
        )
        session.add(
            MarketSnapshotSection(
                snapshot_id=snapshot_key,
                section_id=POST_CLOSE_ACTUALS_SECTION_ID,
                trade_date=date(2026, 6, 21),
                slot="17-30",
                source_dataset="ohlcv_daily",
                provider="canonical_ohlcv_snapshot",
                source_time=now,
                captured_at=now,
                ingested_at=now,
                available_at=now,
                record_count=len(payloads),
                quality_status="ready" if not missing_symbols else "partial",
                section_version="v1",
                raw_payload_fingerprint=section_fingerprint,
                normalization_version=POST_CLOSE_ACTUALS_CONTRACT_VERSION,
                storage_ref={"snapshot_id": snapshot_key, "section_id": POST_CLOSE_ACTUALS_SECTION_ID},
                payload_json=section_payload,
            )
        )
        for payload in payloads:
            session.add(
                MarketSnapshotItem(
                    snapshot_id=snapshot_key,
                    section_id=POST_CLOSE_ACTUALS_SECTION_ID,
                    dataset_id=str(dataset_snapshot_id),
                    symbol=str(payload["symbol"]),
                    item_key=f"{POST_CLOSE_ACTUALS_SECTION_ID}:{payload['symbol']}:2026-06-21",
                    item_type="ohlcv_actual",
                    source_time=now,
                    quality_status="ready",
                    payload_json={**payload, "section_raw_payload_fingerprint": section_fingerprint},
                )
            )
        await session.commit()
    return str(snapshot_id)


@pytest.mark.asyncio()
async def test_post_close_actuals_reads_one_row_for_every_approved_signal(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.get_actuals_for_signals(
        trading_day_plan_id=plan_id,
        post_close_market_snapshot_id=post_close_snapshot_id,
        actor_id="viewer",
        actor_role="viewer",
    )

    assert result.coverage_state == "ready"
    assert len(result.signals) == 2
    assert {item.symbol for item in result.signals} == {"000001.SZ", "600000.SH"}
    assert all(item.row_fingerprint for item in result.signals)
    assert result.dataset_content_fingerprint == "post-close-dataset-fingerprint-1"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_post_close_actuals_marks_missing_signal_symbol_as_partial_not_success(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory, missing_symbols=["600000.SH"])
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.get_actuals_for_signals(
        trading_day_plan_id=plan_id,
        post_close_market_snapshot_id=post_close_snapshot_id,
        actor_id="viewer",
        actor_role="viewer",
    )

    assert result.coverage_state == "partial"
    missing = [item for item in result.signals if item.symbol == "600000.SH"][0]
    assert missing.state == "insufficient_coverage"
    assert missing.row is None
    assert "post_close_actual_row_missing" in missing.reasons

    await engine.dispose()


@pytest.mark.asyncio()
async def test_post_close_actuals_marks_conflict_symbol_without_computing_success(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory, conflict_symbols=["000001.SZ"])
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.get_actuals_for_signals(
        trading_day_plan_id=plan_id,
        post_close_market_snapshot_id=post_close_snapshot_id,
        actor_id="viewer",
        actor_role="viewer",
    )

    assert result.coverage_state == "conflict"
    conflict = [item for item in result.signals if item.symbol == "000001.SZ"][0]
    assert conflict.state == "conflict"
    assert conflict.row is None
    assert "post_close_actual_row_conflict" in conflict.reasons

    await engine.dispose()


@pytest.mark.asyncio()
async def test_post_close_actuals_rejects_free_form_actual_row_drift(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    async with session_factory() as session:
        item = await session.scalar(
            select(MarketSnapshotItem).where(
                MarketSnapshotItem.section_id == POST_CLOSE_ACTUALS_SECTION_ID,
                MarketSnapshotItem.symbol == "000001.SZ",
            )
        )
        item.payload_json = {**item.payload_json, "unexpected_metric": "must_not_be_accepted"}
        await session.commit()
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.get_actuals_for_signals(
        trading_day_plan_id=plan_id,
        post_close_market_snapshot_id=post_close_snapshot_id,
        actor_id="viewer",
        actor_role="viewer",
    )

    drifted = [item for item in result.signals if item.symbol == "000001.SZ"][0]
    assert result.coverage_state == "invalid"
    assert drifted.state == "invalid"
    assert any(reason.startswith("actual_payload_invalid") for reason in drifted.reasons)

    await engine.dispose()


@pytest.mark.asyncio()
async def test_post_close_actuals_rejects_invalid_actual_row_value_domains(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    async with session_factory() as session:
        item = await session.scalar(
            select(MarketSnapshotItem).where(
                MarketSnapshotItem.section_id == POST_CLOSE_ACTUALS_SECTION_ID,
                MarketSnapshotItem.symbol == "000001.SZ",
            )
        )
        item.payload_json = {**item.payload_json, "evidence_window": "free_form_window"}
        await session.commit()
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.get_actuals_for_signals(
        trading_day_plan_id=plan_id,
        post_close_market_snapshot_id=post_close_snapshot_id,
        actor_id="viewer",
        actor_role="viewer",
    )

    invalid = [item for item in result.signals if item.symbol == "000001.SZ"][0]
    assert result.coverage_state == "invalid"
    assert invalid.state == "invalid"
    assert any(reason.startswith("actual_payload_invalid") for reason in invalid.reasons)

    await engine.dispose()


@pytest.mark.asyncio()
async def test_post_close_actuals_rejects_row_dataset_binding_mismatch(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    async with session_factory() as session:
        item = await session.scalar(
            select(MarketSnapshotItem).where(
                MarketSnapshotItem.section_id == POST_CLOSE_ACTUALS_SECTION_ID,
                MarketSnapshotItem.symbol == "000001.SZ",
            )
        )
        item.payload_json = {**item.payload_json, "dataset_content_fingerprint": "wrong-fingerprint"}
        await session.commit()
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.get_actuals_for_signals(
        trading_day_plan_id=plan_id,
        post_close_market_snapshot_id=post_close_snapshot_id,
        actor_id="viewer",
        actor_role="viewer",
    )

    mismatched = [item for item in result.signals if item.symbol == "000001.SZ"][0]
    assert result.coverage_state == "invalid"
    assert mismatched.state == "invalid"
    assert "row_dataset_content_fingerprint_mismatch" in mismatched.reasons

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_outcome_evaluation_persists_review_without_attribution_or_proposals(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=ids["market_state_id"],
        ),
        actor_id="operator",
        actor_role="operator",
    )

    assert result.state == "ready"
    assert result.post_market_review_id is not None
    assert len(result.signal_results) == 2
    first = result.signal_results[0]
    assert first["triggered"]["value"] is True
    assert first["executed"]["state"] == "unavailable"
    assert first["actual_result"]["state"] == "ready"
    assert first["mfe"]["value"] == pytest.approx(0.1)
    assert first["mae"]["value"] == pytest.approx(-0.02)
    assert first["return"]["value"] == pytest.approx(0.05)
    assert first["market_state_change"]["value"] == "unchanged"
    assert first["evidence"]["intraday_approximation"] is True

    async with session_factory() as session:
        reviews = list((await session.scalars(select(PostMarketReview))).all())
        assert len(reviews) == 1
        review = reviews[0]
        assert review.signal_results_json["policy_version"] == "stage10-signal-outcome-v1"
        assert review.attribution_json["policy_version"] == "stage10-structured-attribution-v1"
        assert review.attribution_json["state"] == "ready"
        assert review.attribution_json["signals"][0]["category"] == "unattributable"
        assert review.evidence_json["actuals"]["row_fingerprints"]
        assert await session.scalar(select(func.count()).select_from(OptimizationProposal)) == 0

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_outcome_uses_valid_entry_price_before_previous_close(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(session_factory, entry_price={"type": "limit", "value": "10.25"}, symbol="000001.SZ")
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
        symbol="600000.SH",
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
        ),
        actor_id="operator",
        actor_role="operator",
    )

    first = [item for item in result.signal_results if item["symbol"] == "000001.SZ"][0]
    assert first["return"]["state"] == "ready"
    assert first["return"]["baseline_policy"] == "signal_entry_price"
    assert first["return"]["baseline"] == pytest.approx(10.25)
    assert first["return"]["value"] == pytest.approx((10.5 - 10.25) / 10.25)

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_outcome_matches_triggered_rules_when_rule_version_ids_do_not_intersect(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    async with session_factory() as session:
        signal = await session.scalar(select(Signal).where(Signal.symbol == "000001.SZ"))
        signal.rule_version_ids = ["99999999-9999-9999-9999-999999999999"]
        signal.triggered_rules = ["11111111-1111-1111-1111-111111111111"]
        await session.commit()
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
        ),
        actor_id="operator",
        actor_role="operator",
    )

    first = [item for item in result.signal_results if item["symbol"] == "000001.SZ"][0]
    assert first["matched_rule"]["state"] == "ready"
    assert first["matched_rule"]["rule_version_ids"] == ["11111111-1111-1111-1111-111111111111"]
    assert first["matched_rule"]["signal_rule_version_ids"] == ["99999999-9999-9999-9999-999999999999"]
    assert first["matched_rule"]["triggered_rules"] == ["11111111-1111-1111-1111-111111111111"]

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_outcome_missing_baseline_policy_keeps_metrics_unavailable(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
        ),
        actor_id="operator",
        actor_role="operator",
    )

    first = result.signal_results[0]
    assert first["return"]["state"] == "unavailable"
    assert first["return"]["value"] is None
    assert first["return"]["reason"] == "signal_entry_price_missing"
    assert first["actual_result"]["state"] == "unavailable"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_outcome_missing_previous_close_keeps_return_unavailable_not_zero(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory, previous_close=None)
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
        ),
        actor_id="operator",
        actor_role="operator",
    )

    first = result.signal_results[0]
    assert first["return"]["state"] == "unavailable"
    assert first["return"]["value"] is None
    assert first["return"]["reason"] == "baseline_previous_close_missing_or_invalid"
    assert first["market_state_change"]["state"] == "unavailable"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_outcome_hold_signal_is_not_triggered_and_execution_stays_unavailable(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    async with session_factory() as session:
        signal = await session.scalar(select(Signal).where(Signal.symbol == "000001.SZ"))
        signal.side = "HOLD"
        signal.updated_at = datetime(2026, 6, 21, 9, 0)
        await session.commit()
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
        ),
        actor_id="operator",
        actor_role="operator",
    )

    hold_result = [item for item in result.signal_results if item["symbol"] == "000001.SZ"][0]
    assert hold_result["triggered"]["state"] == "ready"
    assert hold_result["triggered"]["value"] is False
    assert hold_result["executed"]["state"] == "unavailable"
    assert hold_result["executed"]["value"] is None

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_outcome_persists_data_issue_attribution_for_missing_actual_rows(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory, missing_symbols=["600000.SH"])
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=ids["market_state_id"],
        ),
        actor_id="operator",
        actor_role="operator",
    )

    assert result.state == "partial"
    async with session_factory() as session:
        review = await session.scalar(select(PostMarketReview))
        assert review is not None
        assert review.attribution_json["state"] == "partial"
        missing_signal = [item for item in review.attribution_json["signals"] if item["symbol"] == "600000.SH"][0]
        assert missing_signal["category"] == "data issue"
        assert review.prompt_run_id is None
        assert await session.scalar(select(func.count()).select_from(OptimizationProposal)) == 0

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_outcome_persists_market_state_identification_issue_for_changed_market_state(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    changed_market_state_id = uuid4()
    async with session_factory() as session:
        item = await session.scalar(select(MarketSnapshotItem).where(MarketSnapshotItem.symbol == "000001.SZ"))
        item.payload_json = {**item.payload_json, "close": "9.50", "low": "9.40", "high": "10.60"}
        await session.commit()
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=str(changed_market_state_id),
        ),
        actor_id="operator",
        actor_role="operator",
    )

    assert result.signal_results[0]["market_state_change"]["state"] == "ready"
    assert result.signal_results[0]["market_state_change"]["value"] == "changed"
    async with session_factory() as session:
        review = await session.scalar(select(PostMarketReview))
        assert review is not None
        assert review.attribution_json["state"] == "ready"
        assert review.attribution_json["signals"][0]["category"] == "market-state identification issue"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_outcome_persists_rule_issue_attribution_for_negative_selected_rule_outcome(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    async with session_factory() as session:
        item = await session.scalar(select(MarketSnapshotItem).where(MarketSnapshotItem.symbol == "000001.SZ"))
        item.payload_json = {**item.payload_json, "close": "9.50", "low": "9.40", "high": "10.60"}
        await session.commit()
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=ids["market_state_id"],
        ),
        actor_id="operator",
        actor_role="operator",
    )

    assert result.signal_results[0]["matched_rule"]["state"] == "ready"
    async with session_factory() as session:
        review = await session.scalar(select(PostMarketReview))
        assert review is not None
        assert review.attribution_json["state"] == "ready"
        assert review.attribution_json["signals"][0]["category"] == "rule issue"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_outcome_persists_strategy_composition_issue_for_conflicting_selection_items(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    async with session_factory() as session:
        signal = await session.scalar(select(Signal).where(Signal.symbol == "000001.SZ"))
        signal.rule_version_ids = [
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        ]
        await session.commit()
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    async with session_factory() as session:
        item = await session.scalar(select(MarketSnapshotItem).where(MarketSnapshotItem.symbol == "000001.SZ"))
        item.payload_json = {**item.payload_json, "close": "9.50", "low": "9.40", "high": "10.60"}
        await session.commit()
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=ids["market_state_id"],
        ),
        actor_id="operator",
        actor_role="operator",
    )

    assert result.signal_results[0]["matched_rule"]["state"] == "ready"
    async with session_factory() as session:
        review = await session.scalar(select(PostMarketReview))
        assert review is not None
        assert review.attribution_json["state"] == "ready"
        assert review.attribution_json["signals"][0]["category"] == "strategy-composition issue"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_outcome_missing_execution_supplement_does_not_become_execution_issue(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    async with session_factory() as session:
        signal = await session.scalar(select(Signal).where(Signal.symbol == "000001.SZ"))
        signal.signal_state = SignalState.executed
        await session.commit()
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=ids["market_state_id"],
        ),
        actor_id="operator",
        actor_role="operator",
    )

    assert result.signal_results[0]["executed"]["state"] == "unavailable"
    assert result.signal_results[0]["executed"]["reason"] == "approved_execution_supplement_missing"
    async with session_factory() as session:
        review = await session.scalar(select(PostMarketReview))
        assert review is not None
        assert review.attribution_json["state"] == "ready"
        assert review.attribution_json["signals"][0]["category"] != "execution issue"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_outcome_persists_unattributable_state_for_clean_ready_signal(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=ids["market_state_id"],
        ),
        actor_id="operator",
        actor_role="operator",
    )

    assert result.state == "ready"
    assert result.signal_results[0]["return"]["state"] == "ready"
    async with session_factory() as session:
        review = await session.scalar(select(PostMarketReview))
        assert review is not None
        assert review.attribution_json["state"] == "ready"
        assert review.attribution_json["signals"][0]["category"] == "unattributable"
        assert review.signal_results_json["policy_version"] == "stage10-signal-outcome-v1"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_outcome_preserves_degraded_attribution_state_for_degraded_rows(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    async with session_factory() as session:
        item = await session.scalar(
            select(MarketSnapshotItem).where(
                MarketSnapshotItem.section_id == POST_CLOSE_ACTUALS_SECTION_ID,
                MarketSnapshotItem.symbol == "000001.SZ",
            )
        )
        item.quality_status = "degraded"
        item.payload_json = {**item.payload_json, "quality_state": "degraded"}
        await session.commit()
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=ids["market_state_id"],
        ),
        actor_id="operator",
        actor_role="operator",
    )

    assert result.state == "degraded"
    assert result.signal_results[0]["state"] == "degraded"
    async with session_factory() as session:
        review = await session.scalar(select(PostMarketReview))
        assert review is not None
        assert review.attribution_json["state"] == "degraded"
        assert review.attribution_json["signals"][0]["category"] == "data issue"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_attribution_supports_execution_issue_when_explicit_execution_evidence_exists(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    service = PostMarketReviewService(session_scope_factory=session_scope)

    await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=ids["market_state_id"],
        ),
        actor_id="operator",
        actor_role="operator",
    )
    async with session_factory() as session:
        review = await session.scalar(select(PostMarketReview))
        signal_results_json = dict(review.signal_results_json)
        signals = list(signal_results_json["signals"])
        signals[0] = {
            **signals[0],
            "executed": {
                "state": "ready",
                "value": False,
                "reason": "approved_execution_record_shows_not_filled",
            },
        }
        signal_results_json["signals"] = signals
        review.signal_results_json = signal_results_json
        await session.commit()

    result = await service.evaluate_signal_attribution(
        SignalAttributionEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
        ),
        actor_id="operator",
        actor_role="operator",
    )

    assert result.attribution["signals"][0]["category"] == "execution issue"
    assert result.attribution["signals"][0]["llm_validation"]["requested"] is False

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_attribution_marks_low_confidence_gate_without_replacing_program_facts(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    changed_market_state_id = uuid4()
    async with session_factory() as session:
        signal = await session.scalar(select(Signal).where(Signal.symbol == "000001.SZ"))
        signal.rule_version_ids = [
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        ]
        await session.commit()
    service = PostMarketReviewService(session_scope_factory=session_scope)
    await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=str(changed_market_state_id),
        ),
        actor_id="operator",
        actor_role="operator",
    )
    async with session_factory() as session:
        review = await session.scalar(select(PostMarketReview))
        signal_results_json = dict(review.signal_results_json)
        signals = list(signal_results_json["signals"])
        signals[0] = {
            **signals[0],
            "return": {"state": "ready", "value": -0.05, "baseline_policy": "previous_close_daily_market_signal", "baseline": 10.0},
            "actual_result": {"state": "ready", "value": "down", "baseline_policy": "previous_close_daily_market_signal", "baseline": 10.0, "close": 9.5},
            "market_state_change": {
                "state": "ready",
                "value": "changed",
                "pre_market_state_id": ids["market_state_id"],
                "post_close_market_state_id": str(changed_market_state_id),
            },
        }
        signal_results_json["signals"] = signals
        review.signal_results_json = signal_results_json
        await session.commit()

    result = await service.evaluate_signal_attribution(
        SignalAttributionEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
        ),
        actor_id="operator",
        actor_role="operator",
    )

    first = result.attribution["signals"][0]
    assert "low_confidence_multiple_candidate_categories" in first["llm_validation"]["reasons"]
    assert "important_signal" in first["llm_validation"]["reasons"]
    assert first["llm_validation"]["requested"] is False
    assert first["program_facts"]["return"]["value"] == -0.05
    assert first["program_facts"]["actual_result"]["value"] == "down"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_signal_attribution_marks_conflict_gate_without_llm_call(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory, conflict_symbols=["000001.SZ"])
    service = PostMarketReviewService(session_scope_factory=session_scope)

    result = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=ids["market_state_id"],
        ),
        actor_id="operator",
        actor_role="operator",
    )

    conflict_signal = [item for item in result.signal_results if item["symbol"] == "000001.SZ"][0]
    assert conflict_signal["state"] == "conflict"
    async with session_factory() as session:
        review = await session.scalar(select(PostMarketReview))
        first = [item for item in review.attribution_json["signals"] if item["symbol"] == "000001.SZ"][0]
        assert first["category"] == "data issue"
        assert "evidence_conflict" in first["llm_validation"]["reasons"]
        assert first["llm_validation"]["requested"] is False
        assert review.prompt_run_id is None

    await engine.dispose()


@pytest.mark.asyncio()
async def test_optimization_proposals_generate_three_separated_lanes_with_evidence_binding(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    service = PostMarketReviewService(session_scope_factory=session_scope)

    evaluation = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=ids["market_state_id"],
        ),
        actor_id="operator",
        actor_role="operator",
    )
    generated = await service.generate_optimization_proposals(
        OptimizationProposalGenerationRequest(post_market_review_id=evaluation.post_market_review_id),
        actor_id="operator",
        actor_role="operator",
    )

    assert generated.count >= 3
    proposal_types = {item.proposal_type for item in generated.items}
    assert "rule_optimization" in proposal_types
    assert {"author_profile_revision", "strategy_revision"}.issubset(proposal_types)
    strategy_proposal = [item for item in generated.items if item.proposal_type == "strategy_revision"][0]
    assert strategy_proposal.review_binding["post_market_review_id"] == evaluation.post_market_review_id
    assert strategy_proposal.review_binding["trading_day_plan_id"] == plan_id
    assert strategy_proposal.evidence["policy_version"] == "stage10-optimization-proposal-v1"
    assert strategy_proposal.accepted_draft_version_id is None

    async with session_factory() as session:
        proposals = list((await session.scalars(select(OptimizationProposal))).all())
        assert len(proposals) == generated.count
        assert "rule_optimization" in {item.proposal_type.value for item in proposals}
        assert all(item.evidence_json["post_market_review_id"] == evaluation.post_market_review_id for item in proposals)
        review = await session.get(PostMarketReview, UUID(evaluation.post_market_review_id))
        assert review is not None
        assert review.signal_results_json["policy_version"] == "stage10-signal-outcome-v1"
        assert review.attribution_json["policy_version"] == "stage10-structured-attribution-v1"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_optimization_proposals_generation_is_idempotent_and_does_not_duplicate_rows(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    service = PostMarketReviewService(session_scope_factory=session_scope)
    evaluation = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=ids["market_state_id"],
        ),
        actor_id="operator",
        actor_role="operator",
    )

    first = await service.generate_optimization_proposals(
        OptimizationProposalGenerationRequest(post_market_review_id=evaluation.post_market_review_id),
        actor_id="operator",
        actor_role="operator",
    )
    second = await service.generate_optimization_proposals(
        OptimizationProposalGenerationRequest(post_market_review_id=evaluation.post_market_review_id),
        actor_id="operator",
        actor_role="operator",
    )

    assert first.count >= 3
    assert second.count == first.count
    assert {item.proposal_id for item in first.items} == {item.proposal_id for item in second.items}
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(OptimizationProposal)) == first.count

    await engine.dispose()


@pytest.mark.asyncio()
async def test_optimization_proposal_review_actions_do_not_mutate_formal_objects(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    service = PostMarketReviewService(session_scope_factory=session_scope)
    evaluation = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=ids["market_state_id"],
        ),
        actor_id="operator",
        actor_role="operator",
    )
    generated = await service.generate_optimization_proposals(
        OptimizationProposalGenerationRequest(post_market_review_id=evaluation.post_market_review_id),
        actor_id="operator",
        actor_role="operator",
    )
    rule_proposal = [item for item in generated.items if item.proposal_type == "rule_optimization"][0]
    author_proposal = [item for item in generated.items if item.proposal_type == "author_profile_revision"][0]

    in_review = await service.review_optimization_proposal(
        rule_proposal.proposal_id,
        OptimizationProposalReviewRequest(action="start_review", reason="进入复核"),
        actor_id="reviewer",
        actor_role="operator",
    )
    assert in_review.lifecycle_state == "in_review"
    observing = await service.review_optimization_proposal(
        rule_proposal.proposal_id,
        OptimizationProposalReviewRequest(action="continue_observing", reason="单日证据先继续观察"),
        actor_id="reviewer",
        actor_role="operator",
    )
    rejected = await service.review_optimization_proposal(
        author_proposal.proposal_id,
        OptimizationProposalReviewRequest(action="reject", reason="不进入画像变更"),
        actor_id="reviewer",
        actor_role="operator",
    )

    assert observing.lifecycle_state == "draft"
    assert rejected.lifecycle_state == "rejected"
    async with session_factory() as session:
        strategy = await session.get(Strategy, UUID(ids["strategy_id"]))
        assert strategy is not None
        assert str(strategy.current_published_version_id) == ids["strategy_version_id"]
        rule_version = await session.get(RuleVersion, UUID("11111111-1111-1111-1111-111111111111"))
        author_profile = await session.get(AuthorProfileVersion, UUID("88888888-8888-8888-8888-888888888888"))
        assert rule_version is not None and rule_version.lifecycle_state == FormalLifecycleState.published
        assert author_profile is not None and author_profile.lifecycle_state == FormalLifecycleState.published

    await engine.dispose()


@pytest.mark.asyncio()
async def test_strategy_optimization_accept_to_draft_keeps_current_pointer_unchanged(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory)
    service = PostMarketReviewService(session_scope_factory=session_scope)
    evaluation = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=ids["market_state_id"],
        ),
        actor_id="operator",
        actor_role="operator",
    )
    async with session_factory() as session:
        review = await session.get(PostMarketReview, UUID(evaluation.post_market_review_id))
        signal_results_json = dict(review.signal_results_json)
        signals = list(signal_results_json["signals"])
        for index, signal in enumerate(signals):
            signal["return"] = {"state": "ready", "value": -0.08 if index == 0 else -0.06}
            signal["actual_result"] = {"state": "ready", "value": "down"}
            signal["matched_rule"] = {
                "state": "ready",
                "rule_version_ids": ["11111111-1111-1111-1111-111111111111"],
                "selection_decisions": {"11111111-1111-1111-1111-111111111111": "selected"},
            }
        review.signal_results_json = signal_results_json
        review.attribution_json = {
            **review.attribution_json,
            "signals": [
                {
                    **item,
                    "state": "ready",
                    "category": "strategy-composition issue",
                }
                for item in review.attribution_json["signals"]
            ],
            "state": "ready",
        }
        await session.commit()

    generated = await service.generate_optimization_proposals(
        OptimizationProposalGenerationRequest(post_market_review_id=evaluation.post_market_review_id),
        actor_id="operator",
        actor_role="operator",
    )
    strategy_proposal = [item for item in generated.items if item.proposal_type == "strategy_revision"][0]
    reviewed = await service.review_optimization_proposal(
        strategy_proposal.proposal_id,
        OptimizationProposalReviewRequest(action="start_review", reason="开始策略复核"),
        actor_id="reviewer",
        actor_role="operator",
    )
    assert reviewed.lifecycle_state == "in_review"
    linked_draft_version_id = uuid4()
    async with session_factory() as session:
        session.add(
            StrategyVersion(
                strategy_version_id=linked_draft_version_id,
                strategy_id=UUID(ids["strategy_id"]),
                version_no=2,
                schema_version="strategy-v1",
                lifecycle_state=FormalLifecycleState.draft,
                title="正式策略草稿",
                summary="供建议挂接的既有草稿",
                risk_policy_json={"stop_loss_pct": "5%", "take_profit_pct": "12%", "position_limit": 0.5},
                selection_policy_json={},
                universe_json={},
                    author_method_profile_version_id=UUID("66666666-6666-6666-6666-666666666666"),
                    author_rule_profile_version_id=UUID("77777777-7777-7777-7777-777777777777"),
                    author_validated_profile_version_id=UUID("88888888-8888-8888-8888-888888888888"),
                    evidence_json={
                        "validation_summary": {
                            "state": "passed",
                            "label": "验证通过",
                            "reviewer_decision": "approved",
                            "reviewer_decision_label": "已批准",
                            "dataset_binding": {"state": "ready", "dataset_snapshot_id": ids["dataset_snapshot_id"], "market_state_definition_version": "market-state-v2"},
                            "market_snapshot_binding": {"state": "ready", "market_snapshot_ids": [ids["market_snapshot_id"]]},
                            "backtest": {
                                "state": "unavailable",
                                "out_of_sample_state": "unavailable",
                                "backtest_run_ids": [],
                                "backtest_result_ids": [],
                                "requested_level": None,
                                "effective_level": None,
                                "annual_return": None,
                                "max_drawdown": None,
                                "win_rate": None,
                            },
                            "rule_applicability": {
                                "state": "unavailable",
                                "covered_rule_count": 0,
                                "total_rule_count": 0,
                                "coverage_ratio": 0.0,
                                "uncovered_rule_version_ids": [],
                            },
                            "sample_coverage": {"state": "unknown", "sample_count": None, "insufficient_sample": False},
                            "data_quality": {"state": "verified", "warnings": [], "limitations": []},
                        }
                    },
                quality_status=QualityStatus.verified,
                review_status="draft",
                created_by="seed",
                updated_by="seed",
            )
        )
        await session.commit()
    accepted = await service.accept_optimization_proposal_to_draft(
        strategy_proposal.proposal_id,
        OptimizationProposalAcceptRequest(
            reason="生成策略草稿",
            linked_draft_version_id=linked_draft_version_id,
        ),
        actor_id="reviewer",
        actor_role="operator",
    )

    assert accepted.lifecycle_state == "accepted"
    assert accepted.accepted_draft_version_id is not None
    async with session_factory() as session:
        strategy = await session.get(Strategy, UUID(ids["strategy_id"]))
        assert strategy is not None
        assert str(strategy.current_published_version_id) == ids["strategy_version_id"]
        proposal = await session.get(OptimizationProposal, UUID(strategy_proposal.proposal_id))
        assert proposal is not None
        assert proposal.accepted_draft_version_id is not None

    await engine.dispose()


@pytest.mark.asyncio()
async def test_partial_review_evidence_generates_continue_observing_without_execution_default(tmp_path: Path) -> None:
    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    ids = await _seed_runtime_bundle(session_factory)
    plan_id = await _approve_plan(session_scope, ids)
    await _set_signal_baseline(
        session_factory,
        entry_price={"type": "market", "baseline_policy": "previous_close_daily_market_signal"},
    )
    post_close_snapshot_id = await _seed_post_close_actuals(session_factory, missing_symbols=["600000.SH"])
    service = PostMarketReviewService(session_scope_factory=session_scope)
    evaluation = await service.evaluate_signal_outcomes(
        SignalOutcomeEvaluationRequest(
            trading_day_plan_id=plan_id,
            post_close_market_snapshot_id=post_close_snapshot_id,
            post_close_market_state_id=ids["market_state_id"],
        ),
        actor_id="operator",
        actor_role="operator",
    )

    generated = await service.generate_optimization_proposals(
        OptimizationProposalGenerationRequest(post_market_review_id=evaluation.post_market_review_id),
        actor_id="operator",
        actor_role="operator",
    )

    assert generated.state == "partial"
    assert all(item.recommendation_state == "continue_observing" for item in generated.items)
    assert all(item.evidence_state in {"partial", "insufficient_coverage", "unavailable"} for item in generated.items)
    strategy_proposal = [item for item in generated.items if item.proposal_type == "strategy_revision"][0]
    assert "approved_execution_supplement_missing" not in strategy_proposal.evidence["deterministic_reason_list"]

    await engine.dispose()
