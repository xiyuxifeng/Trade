from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.base import Base
from src.models.blog_article import BlogArticle
from src.models.stage2_canonical import (
    ArticleRevision,
    ArticleStructure,
    LifecycleEvent,
    PromptRun,
    Rule,
    RuleCandidate,
    RuleFamily,
    RuleFamilyMembership,
    RuleVersion,
    RuleVersionSourceLink,
)
from src.services.rule_lifecycle_service import (
    RuleLifecycleConflictError,
    RuleLifecycleService,
    RuleLifecycleStaleWriteError,
    RuleLifecycleTransitionBlockedError,
)
from src.services.stage3_regression_service import RegressionRunResult


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


class _PassingGate:
    async def run_fixed_set(self) -> RegressionRunResult:
        return RegressionRunResult(status="passed", gate_version="stage3-fixed-set-v1", manifest=[])


def _candidate_payload(*, threshold: float = 1.5, title: str = "放量突破介入") -> dict:
    return {
        "title": title,
        "rule_type": "entry",
        "instrument_focus": ["stock"],
        "timeframe": "5m",
        "holding_period": "intraday",
        "condition": {
            "logic": "single",
            "clauses": [{"field": "volume", "operator": "gt", "value": threshold, "unit": "x", "lookback": 5}],
        },
        "action": {"type": "enter", "side": "buy", "price_reference": "market"},
        "risk_controls": [],
        "data_dependencies": ["ohlcv_1d"],
        "market_state_applicability": {"status": "not_declared", "explicit_conditions": [], "inferred_hypotheses": []},
        "quantification": {"status": "executable", "missing_fields": [], "ambiguous_terms": [], "manual_review_required": False},
        "evidence": [{"quote": "放量突破介入", "supports": "condition"}],
    }


async def _seed_candidate_bundle(session: AsyncSession) -> tuple[UUID, UUID, UUID, UUID, RuleCandidate]:
    article_id = UUID("11111111-1111-1111-1111-111111111111")
    revision_id = UUID("22222222-2222-2222-2222-222222222222")
    prompt_run_id = UUID("33333333-3333-3333-3333-333333333333")
    structure_id = UUID("44444444-4444-4444-4444-444444444444")
    session.add(
        BlogArticle(
            id=article_id,
            source="tgb",
            source_url="https://example.com/article",
            title="示例文章",
            author_name="Alice",
            author_id="author-1",
            published_at=datetime(2026, 6, 15, 9, 30, tzinfo=UTC),
            crawled_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC),
            content_text="原始文章正文",
            summary="文章摘要",
            tags=["突破"],
            content_hash="hash-1",
            view_count=1,
            like_count=0,
            bookmark_count=0,
            comment_count=0,
            raw_payload={},
        )
    )
    session.add(
        ArticleRevision(
            article_revision_id=revision_id,
            article_id=article_id,
            revision_no=1,
            content_hash="hash-1",
            content_text="清洗后的文章正文",
            content_html=None,
            source_payload={"summary": "冻结摘要"},
            captured_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC),
            quality_status="complete",
        )
    )
    session.add(
        PromptRun(
            prompt_run_id=prompt_run_id,
            run_id=str(prompt_run_id),
            article_id=article_id,
            prompt_name="article_analysis_v1",
            prompt_version="article_analysis_v1",
            schema_name="article_analysis_v1",
            schema_version="article_analysis_v1",
            provider="test-provider",
            model="test-model",
            input_object_type="article_revision",
            input_object_id=str(article_id),
            input_version_id=str(revision_id),
            input_hash="input-hash-1",
            request_json={},
            raw_output={},
            validation_errors={},
            validation_state="valid",
            retry_count=0,
            token_usage={},
            cost_amount=None,
            cost_currency=None,
            raw_output_text="{}",
            started_at=datetime(2026, 6, 15, 9, 41, tzinfo=UTC),
            completed_at=datetime(2026, 6, 15, 9, 41, tzinfo=UTC),
        )
    )
    session.add(
        ArticleStructure(
            article_structure_id=structure_id,
            article_id=article_id,
            article_revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            schema_version="article_structure_v1",
            payload={"method_tags": ["突破"], "key_claims": []},
            evidence_json={},
            missing_fields={},
            inference_fields={},
            lifecycle_state="approved",
            quality_status="complete",
            approved_by="tester",
            approved_at=datetime(2026, 6, 16, 9, 0, tzinfo=UTC),
            supersedes_id=None,
            created_by="tester",
            updated_by="tester",
        )
    )
    candidate = RuleCandidate(
        rule_candidate_id=uuid4(),
        article_structure_id=structure_id,
        source_article_id=article_id,
        candidate_index=0,
        candidate_fingerprint="legacy-0",
        rule_type="entry",
        canonical_payload=_candidate_payload(),
        evidence_json={"items": _candidate_payload()["evidence"]},
        explicit_fields={"title": "放量突破介入"},
        inferred_fields={},
        missing_fields={},
        data_dependencies={"required": ["ohlcv_1d"]},
        backtestability_status="executable",
        review_state="extracted",
        quality_status="complete",
        created_by="tester",
        updated_by="tester",
    )
    session.add(candidate)
    await session.flush()
    return article_id, revision_id, prompt_run_id, structure_id, candidate


@pytest.mark.asyncio
async def test_rule_lifecycle_requires_review_before_approval_and_tracks_pending_backtest_idempotently(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stage4-rule-lifecycle.db'}")

    @event.listens_for(engine.sync_engine, "connect")
    def _register_char_length(dbapi_connection, _connection_record):  # noqa: ANN001
        dbapi_connection.create_function("char_length", 1, lambda value: len(value) if value is not None else 0)

    async with engine.begin() as conn:
        for table in (
            BlogArticle.__table__,
            ArticleRevision.__table__,
            PromptRun.__table__,
            ArticleStructure.__table__,
            RuleCandidate.__table__,
            Rule.__table__,
            RuleVersion.__table__,
            RuleFamily.__table__,
            RuleFamilyMembership.__table__,
            RuleVersionSourceLink.__table__,
            LifecycleEvent.__table__,
        ):
            await conn.run_sync(lambda sync_conn, current_table=table: current_table.create(bind=sync_conn, checkfirst=True))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        _, _, _, _, candidate = await _seed_candidate_bundle(session)
        await session.commit()

    @asynccontextmanager
    async def _session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    service = RuleLifecycleService(
        session_scope_factory=_session_scope,
        regression_service=_PassingGate(),
    )

    with pytest.raises(RuleLifecycleTransitionBlockedError):
        await service.approve_candidate(
            candidate_id=candidate.rule_candidate_id,
            actor_id="operator-user",
            reason="跳过待审核直接批准。",
            correlation_id="corr-approve-skip",
        )

    review_state = await service.transition_candidate(
        candidate_id=candidate.rule_candidate_id,
        target_state="待审核",
        actor_type="human",
        actor_id="operator-user",
        reason="提交人工审核。",
        correlation_id="corr-candidate-review",
    )
    assert review_state.display_state == "待审核"
    assert review_state.canonical_state == "manual_review"

    approved = await service.approve_candidate(
        candidate_id=candidate.rule_candidate_id,
        actor_id="operator-user",
        reason="人工确认后进入正式待回测链路。",
        correlation_id="corr-approve",
    )
    assert approved.display_state == "已批准"
    assert approved.canonical_state == "draft"

    queued = await service.transition_rule_version(
        rule_version_id=UUID(approved.object_id),
        target_state="待回测",
        actor_type="human",
        actor_id="operator-user",
        reason="加入待回测队列。",
        correlation_id="corr-backtest-queue",
        expected_updated_at=approved.updated_at,
    )
    assert queued.display_state == "待回测"
    assert queued.canonical_state == "draft"

    retried = await service.transition_rule_version(
        rule_version_id=UUID(approved.object_id),
        target_state="待回测",
        actor_type="human",
        actor_id="operator-user",
        reason="重试同一请求。",
        correlation_id="corr-backtest-queue",
        expected_updated_at=queued.updated_at,
    )
    assert retried.display_state == "待回测"

    async with session_factory() as session:
        events = (
            await session.execute(
                select(LifecycleEvent)
                .where(LifecycleEvent.object_id == UUID(approved.object_id))
                .order_by(LifecycleEvent.occurred_at.asc())
            )
        ).scalars().all()
        assert [event.reason_code for event in events] == [
            "created_from_article_review",
            "queued_for_backtest",
        ]
        assert await session.scalar(select(func.count()).select_from(RuleVersion)) == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_rule_lifecycle_rejects_stale_write_and_blocks_publish_without_backtest_evidence(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stage4-rule-lifecycle-stale.db'}")

    @event.listens_for(engine.sync_engine, "connect")
    def _register_char_length(dbapi_connection, _connection_record):  # noqa: ANN001
        dbapi_connection.create_function("char_length", 1, lambda value: len(value) if value is not None else 0)

    async with engine.begin() as conn:
        for table in (
            BlogArticle.__table__,
            ArticleRevision.__table__,
            PromptRun.__table__,
            ArticleStructure.__table__,
            RuleCandidate.__table__,
            Rule.__table__,
            RuleVersion.__table__,
            RuleFamily.__table__,
            RuleFamilyMembership.__table__,
            RuleVersionSourceLink.__table__,
            LifecycleEvent.__table__,
        ):
            await conn.run_sync(lambda sync_conn, current_table=table: current_table.create(bind=sync_conn, checkfirst=True))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        _, _, _, _, candidate = await _seed_candidate_bundle(session)
        await session.commit()

    @asynccontextmanager
    async def _session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    service = RuleLifecycleService(
        session_scope_factory=_session_scope,
        regression_service=_PassingGate(),
    )

    await service.transition_candidate(
        candidate_id=candidate.rule_candidate_id,
        target_state="待审核",
        actor_type="human",
        actor_id="operator-user",
        reason="进入审核。",
        correlation_id="corr-review",
    )
    approved = await service.approve_candidate(
        candidate_id=candidate.rule_candidate_id,
        actor_id="operator-user",
        reason="人工批准。",
        correlation_id="corr-approve",
    )
    queued = await service.transition_rule_version(
        rule_version_id=UUID(approved.object_id),
        target_state="待回测",
        actor_type="human",
        actor_id="operator-user",
        reason="加入待回测队列。",
        correlation_id="corr-queue",
        expected_updated_at=approved.updated_at,
    )
    validating = await service.transition_rule_version(
        rule_version_id=UUID(approved.object_id),
        target_state="验证中",
        actor_type="human",
        actor_id="operator-user",
        reason="开始验证。",
        correlation_id="corr-validating",
        expected_updated_at=queued.updated_at,
    )
    assert validating.display_state == "验证中"
    assert validating.canonical_state == "in_review"

    with pytest.raises(RuleLifecycleStaleWriteError):
        await service.transition_rule_version(
            rule_version_id=UUID(approved.object_id),
            target_state="验证中",
            actor_type="human",
            actor_id="operator-user",
            reason="使用旧时间戳重复提交。",
            correlation_id="corr-stale",
            expected_updated_at=queued.updated_at,
        )

    with pytest.raises(RuleLifecycleTransitionBlockedError):
        await service.transition_rule_version(
            rule_version_id=UUID(approved.object_id),
            target_state="可用",
            actor_type="human",
            actor_id="operator-user",
            reason="缺少回测证据。",
            correlation_id="corr-publish-blocked",
            expected_updated_at=validating.updated_at,
        )

    available = await service.transition_rule_version(
        rule_version_id=UUID(approved.object_id),
        target_state="可用",
        actor_type="human",
        actor_id="operator-user",
        reason="验证完成后允许正常使用。",
        correlation_id="corr-publish",
        expected_updated_at=validating.updated_at,
        evidence_refs=["backtest-run:bt-001", "dataset-snapshot:ds-001"],
    )
    assert available.display_state == "可用"
    assert available.canonical_state == "published"
    assert available.allowed_next_actions[0].label == "限定使用"

    limited = await service.transition_rule_version(
        rule_version_id=UUID(approved.object_id),
        target_state="限定使用",
        actor_type="human",
        actor_id="operator-user",
        reason="样本覆盖不足，仅限特定情形使用。",
        correlation_id="corr-limited",
        expected_updated_at=available.updated_at,
        evidence_refs=["backtest-run:bt-001"],
    )
    assert limited.display_state == "限定使用"
    assert limited.canonical_state == "published"

    retired = await service.transition_rule_version(
        rule_version_id=UUID(approved.object_id),
        target_state="已停用",
        actor_type="human",
        actor_id="operator-user",
        reason="人工停用该规则。",
        correlation_id="corr-retired",
        expected_updated_at=limited.updated_at,
    )
    assert retired.display_state == "已停用"
    assert retired.canonical_state == "archived"

    await engine.dispose()

