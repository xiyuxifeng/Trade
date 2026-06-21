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
    TradingDayPlanState,
)
from src.models.market_data_snapshot import MarketSnapshot
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
    OptimizationProposal,
    PostMarketReview,
    Rule,
    RuleVersion,
    Strategy,
    StrategyVersion,
    TradingDayPlan,
)
from src.services.daily_trading_plan_service import DailyTradingPlanService, TradingDayPlanReviewRequest


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
        await conn.run_sync(MarketRegimeRecord.__table__.create)
        await conn.run_sync(AuthorProfileVersion.__table__.create)
        await conn.run_sync(Strategy.__table__.create)
        await conn.run_sync(StrategyVersion.__table__.create)
        await conn.run_sync(DailyRuleSelection.__table__.create)
        await conn.run_sync(DailyRuleSelectionItem.__table__.create)
        await conn.run_sync(DailyStrategyInstance.__table__.create)
        await conn.run_sync(TradingDayPlan.__table__.create)
        await conn.run_sync(Signal.__table__.create)
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
                evidence_json={"validation_summary": {"state": "passed"}},
                quality_status=QualityStatus.verified,
                review_status="approved",
                created_by="seed",
                updated_by="seed",
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
