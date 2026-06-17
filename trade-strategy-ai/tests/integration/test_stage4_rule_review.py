from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

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
from src.services.stage3_regression_service import RegressionRunResult


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


class _PassingGate:
    async def run_fixed_set(self) -> RegressionRunResult:
        return RegressionRunResult(status="passed", gate_version="stage3-fixed-set-v1", manifest=[])


class _FailingGate:
    async def run_fixed_set(self) -> RegressionRunResult:
        return RegressionRunResult.failed(
            manifest=[],
            gate_version="stage3-fixed-set-v1",
            semantic_failures=["blocked"],
        )


def _payload(
    *,
    title: str,
    rule_type: str = "entry",
    action_type: str = "enter",
    backtestability_status: str = "executable",
    ambiguous_terms: list[str] | None = None,
    manual_review_required: bool = False,
    evidence: list[dict] | None = None,
    condition: dict | None = None,
    data_dependencies: list[str] | None = None,
    market_state_status: str = "not_declared",
    inferred_hypotheses: list[dict] | None = None,
) -> tuple[dict, str]:
    return (
        {
            "title": title,
            "rule_type": rule_type,
            "instrument_focus": ["stock"],
            "timeframe": "5m",
            "holding_period": "intraday",
            "condition": condition
            or {
                "logic": "single",
                "clauses": [{"field": "volume", "operator": "gt", "value": 1.5, "unit": "x", "lookback": 5}],
            },
            "action": {"type": action_type, "side": "buy", "price_reference": "market"},
            "risk_controls": [],
            "data_dependencies": data_dependencies or ["ohlcv_1d"],
            "market_state_applicability": {
                "status": market_state_status,
                "explicit_conditions": [],
                "inferred_hypotheses": inferred_hypotheses or [],
            },
            "quantification": {
                "status": "executable" if backtestability_status == "executable" else "partially_executable",
                "missing_fields": [] if backtestability_status == "executable" else ["threshold"],
                "ambiguous_terms": ambiguous_terms or [],
                "manual_review_required": manual_review_required,
            },
            "evidence": evidence if evidence is not None else [{"quote": title, "supports": "condition"}],
        },
        backtestability_status,
    )


async def _seed_candidate(
    session: AsyncSession,
    *,
    article_id: UUID,
    revision_id: UUID,
    prompt_run_id: UUID,
    structure_id: UUID,
    index: int,
    payload: dict,
    backtestability_status: str,
    review_state: str = "extracted",
    inferred_fields: dict | None = None,
    missing_fields: dict | None = None,
) -> RuleCandidate:
    candidate = RuleCandidate(
        rule_candidate_id=uuid4(),
        article_structure_id=structure_id,
        source_article_id=article_id,
        candidate_index=index,
        candidate_fingerprint=f"legacy-{index}",
        rule_type=str(payload.get("rule_type") or "entry"),
        canonical_payload=payload,
        evidence_json={"items": payload.get("evidence") or []},
        explicit_fields={"title": payload["title"]},
        inferred_fields=inferred_fields or {},
        missing_fields=missing_fields or {},
        data_dependencies={"required": payload.get("data_dependencies") or []},
        backtestability_status=backtestability_status,
        review_state=review_state,
        quality_status="complete",
        created_by="tester",
        updated_by="tester",
    )
    session.add(candidate)
    await session.flush()
    return candidate


@pytest.mark.asyncio
async def test_rule_review_classifies_all_five_statuses_and_routes_conflicts(tmp_path) -> None:
    from src.services.rule_review_service import RuleReviewService

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stage4-rule-review-statuses.db'}")

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

        auto_pass_payload, auto_pass_backtestability = _payload(title="非入场过滤规则", rule_type="filter", action_type="filter")
        recommend_pass_payload, recommend_pass_backtestability = _payload(title="低风险入场规则")
        manual_payload, manual_backtestability = _payload(
            title="存在模糊描述",
            ambiguous_terms=["放量"],
            condition={
                "logic": "single",
                "clauses": [{"field": "close", "operator": "gt", "value": 2.0, "unit": "x", "lookback": 5}],
            },
        )
        not_backtestable_payload, not_backtestable = _payload(title="样本不足", backtestability_status="partial")
        reject_payload, reject_backtestability = _payload(title="缺少证据", evidence=[])

        auto_pass_candidate = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=0,
            payload=auto_pass_payload,
            backtestability_status=auto_pass_backtestability,
        )
        recommend_pass_candidate = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=1,
            payload=recommend_pass_payload,
            backtestability_status=recommend_pass_backtestability,
        )
        manual_candidate = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=2,
            payload=manual_payload,
            backtestability_status=manual_backtestability,
        )
        not_backtestable_candidate = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=3,
            payload=not_backtestable_payload,
            backtestability_status=not_backtestable,
        )
        reject_candidate = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=4,
            payload=reject_payload,
            backtestability_status=reject_backtestability,
        )

        existing_rule = Rule(
            rule_id=uuid4(),
            business_key="rule:existing-conflict",
            current_published_version_id=None,
            created_at=datetime.now(UTC),
            created_by="tester",
            updated_at=datetime.now(UTC),
            updated_by="tester",
        )
        session.add(existing_rule)
        existing_rule_version = RuleVersion(
            rule_version_id=uuid4(),
            rule_id=existing_rule.rule_id,
            version_no=1,
            source_candidate_id=None,
            canonical_fingerprint="existing-conflict-fp",
            schema_version="rule_v1",
            lifecycle_state="draft",
            title="既有卖出冲突规则",
            description=None,
            rule_type="entry",
            instrument_scope={"instrument_focus": ["stock"]},
            condition_json=manual_payload["condition"],
            action_json={"type": "enter", "side": "sell", "price_reference": "market"},
            parameter_json={"timeframe": "5m", "holding_period": "intraday", "risk_controls": [], "market_state_applicability": {}},
            data_dependencies={"required": ["ohlcv_1d"]},
            evidence_json={},
            quality_status="complete",
            parent_version_id=None,
            published_at=None,
            published_by=None,
            superseded_at=None,
            created_by="tester",
            updated_by="tester",
        )
        session.add(existing_rule_version)
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

    service = RuleReviewService(
        session_scope_factory=_session_scope,
        regression_service=_PassingGate(),
    )

    items = await service.list_candidates()
    statuses = {item.candidate_id: item.automatic_review.status for item in items}
    labels = {item.candidate_id: item.automatic_review.label for item in items}
    assert statuses[str(auto_pass_candidate.rule_candidate_id)] == "auto_pass"
    assert statuses[str(recommend_pass_candidate.rule_candidate_id)] == "recommend_pass"
    assert statuses[str(manual_candidate.rule_candidate_id)] == "manual_review"
    assert statuses[str(not_backtestable_candidate.rule_candidate_id)] == "not_backtestable"
    assert statuses[str(reject_candidate.rule_candidate_id)] == "recommend_reject"
    assert labels[str(auto_pass_candidate.rule_candidate_id)] == "自动通过"
    assert labels[str(recommend_pass_candidate.rule_candidate_id)] == "建议通过"
    assert labels[str(manual_candidate.rule_candidate_id)] == "需要人工确认"
    assert labels[str(not_backtestable_candidate.rule_candidate_id)] == "不可回测"
    assert labels[str(reject_candidate.rule_candidate_id)] == "建议驳回"

    conflict_detail = await service.get_candidate_detail(candidate_id=manual_candidate.rule_candidate_id)
    assert conflict_detail["automatic_review"]["status"] == "manual_review"
    assert "action.side" in conflict_detail["governance"]["related_rules"][0]["conflict_reasons"]
    human_only = await service.list_candidates(require_human_review_only=True)
    assert {item.automatic_review.status for item in human_only} == {"manual_review"}


@pytest.mark.asyncio
async def test_rule_review_edit_approve_merge_hold_reject_and_gate(tmp_path) -> None:
    from src.services.rule_review_service import RuleReviewService, RuleReviewTransitionBlockedError

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stage4-rule-review-actions.db'}")

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
        article_id = UUID("aaaaaaaa-1111-1111-1111-111111111111")
        revision_id = UUID("bbbbbbbb-2222-2222-2222-222222222222")
        prompt_run_id = UUID("cccccccc-3333-3333-3333-333333333333")
        structure_id = UUID("dddddddd-4444-4444-4444-444444444444")
        session.add(
            BlogArticle(
                id=article_id,
                source="tgb",
                source_url="https://example.com/article",
                title="动作文章",
                author_name="Bob",
                author_id="author-2",
                published_at=datetime(2026, 6, 15, 9, 30, tzinfo=UTC),
                crawled_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC),
                content_text="原始文章正文",
                summary="文章摘要",
                tags=["突破"],
                content_hash="hash-2",
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
                content_hash="hash-2",
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
                input_hash="input-hash-2",
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
        edit_payload, edit_backtestability = _payload(
            title="需要编辑后批准",
            ambiguous_terms=["放量"],
            condition={
                "logic": "single",
                "clauses": [{"field": "close", "operator": "gt", "value": 3.0, "unit": "x", "lookback": 5}],
            },
        )
        duplicate_payload, duplicate_backtestability = _payload(title="完全重复的规则")
        hold_payload, hold_backtestability = _payload(title="待补资料规则", ambiguous_terms=["附近"])
        reject_payload, reject_backtestability = _payload(title="无证据规则", evidence=[])

        editable_candidate = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=0,
            payload=edit_payload,
            backtestability_status=edit_backtestability,
        )
        duplicate_source = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=1,
            payload=duplicate_payload,
            backtestability_status=duplicate_backtestability,
            review_state="manual_review",
        )
        hold_candidate = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=2,
            payload=hold_payload,
            backtestability_status=hold_backtestability,
            review_state="manual_review",
        )
        reject_candidate = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=3,
            payload=reject_payload,
            backtestability_status=reject_backtestability,
            review_state="manual_review",
        )

        existing_rule = Rule(
            rule_id=uuid4(),
            business_key="rule:existing-duplicate",
            current_published_version_id=None,
            created_at=datetime.now(UTC),
            created_by="tester",
            updated_at=datetime.now(UTC),
            updated_by="tester",
        )
        session.add(existing_rule)
        existing_rule_version = RuleVersion(
            rule_version_id=uuid4(),
            rule_id=existing_rule.rule_id,
            version_no=1,
            source_candidate_id=None,
            canonical_fingerprint="existing-duplicate-fp",
            schema_version="rule_v1",
            lifecycle_state="draft",
            title="既有重复规则",
            description=None,
            rule_type="entry",
            instrument_scope={"instrument_focus": ["stock"]},
            condition_json=duplicate_payload["condition"],
            action_json=duplicate_payload["action"],
            parameter_json={"timeframe": "5m", "holding_period": "intraday", "risk_controls": [], "market_state_applicability": {}},
            data_dependencies={"required": ["ohlcv_1d"]},
            evidence_json={},
            quality_status="complete",
            parent_version_id=None,
            published_at=None,
            published_by=None,
            superseded_at=None,
            created_by="tester",
            updated_by="tester",
        )
        session.add(existing_rule_version)
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

    service = RuleReviewService(
        session_scope_factory=_session_scope,
        regression_service=_PassingGate(),
    )

    held = await service.apply_action(
        candidate_id=hold_candidate.rule_candidate_id,
        action="hold",
        actor_type="human",
        actor_id="reviewer",
        reason="证据引用还需要人工补充。",
        correlation_id="corr-hold",
    )
    assert held.current_review_state == "待审核"
    assert held.last_action == "hold"

    rejected = await service.apply_action(
        candidate_id=reject_candidate.rule_candidate_id,
        action="reject",
        actor_type="human",
        actor_id="reviewer",
        reason="证据缺失，驳回。",
        correlation_id="corr-reject",
    )
    assert rejected.current_review_state == "已拒绝"

    approved_after_edit = await service.apply_action(
        candidate_id=editable_candidate.rule_candidate_id,
        action="approve_after_edit",
        actor_type="human",
        actor_id="reviewer",
        reason="补齐量化条件后批准。",
        correlation_id="corr-approve-after-edit",
        edits={
            "canonical_payload": {
                **edit_payload,
                "quantification": {
                    "status": "executable",
                    "missing_fields": [],
                    "ambiguous_terms": [],
                    "manual_review_required": False,
                },
            }
        },
    )
    assert approved_after_edit.current_lifecycle_state == "已批准"
    assert approved_after_edit.rule_version_id is not None

    merged = await service.apply_action(
        candidate_id=duplicate_source.rule_candidate_id,
        action="merge",
        actor_type="human",
        actor_id="reviewer",
        reason="确认与既有规则完全重复，复用正式规则轨道。",
        correlation_id="corr-merge",
    )
    assert merged.rule_version_id == str(existing_rule_version.rule_version_id)

    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(RuleVersion)) == 2
        events = list((await session.execute(select(LifecycleEvent).order_by(LifecycleEvent.occurred_at.asc()))).scalars().all())
        reason_codes = [event.reason_code for event in events]
        assert "human_hold" in reason_codes
        assert "human_rejected" in reason_codes
        assert "human_edited" in reason_codes
        assert "linked_exact_duplicate" in reason_codes
        merge_events = [event for event in events if event.correlation_id == "corr-approve-after-edit"]
        assert merge_events

    blocked_service = RuleReviewService(
        session_scope_factory=_session_scope,
        regression_service=_FailingGate(),
    )
    with pytest.raises(RuleReviewTransitionBlockedError):
        await blocked_service.apply_action(
            candidate_id=hold_candidate.rule_candidate_id,
            action="hold",
            actor_type="human",
            actor_id="reviewer",
            reason="gate fail",
            correlation_id="corr-gate-fail",
        )


@pytest.mark.asyncio
async def test_rule_review_batch_approval_and_rejection_validate_status_and_permissions(tmp_path) -> None:
    from src.services.rule_review_service import RuleReviewService, RuleReviewTransitionBlockedError

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stage4-rule-review-batch.db'}")

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
        article_id = UUID("eeeeeeee-1111-1111-1111-111111111111")
        revision_id = UUID("ffffffff-2222-2222-2222-222222222222")
        prompt_run_id = UUID("abababab-3333-3333-3333-333333333333")
        structure_id = UUID("cdcdcdcd-4444-4444-4444-444444444444")
        session.add(
            BlogArticle(
                id=article_id,
                source="tgb",
                source_url="https://example.com/article",
                title="批量文章",
                author_name="Carol",
                author_id="author-3",
                published_at=datetime(2026, 6, 15, 9, 30, tzinfo=UTC),
                crawled_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC),
                content_text="原始文章正文",
                summary="文章摘要",
                tags=["突破"],
                content_hash="hash-3",
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
                content_hash="hash-3",
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
                input_hash="input-hash-3",
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
        approve_payload, approve_backtestability = _payload(title="批量通过规则")
        reject_payload, reject_backtestability = _payload(title="批量拒绝规则", evidence=[])
        manual_payload, manual_backtestability = _payload(title="冲突规则", ambiguous_terms=["附近"])

        batch_approve = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=0,
            payload=approve_payload,
            backtestability_status=approve_backtestability,
        )
        batch_reject = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=1,
            payload=reject_payload,
            backtestability_status=reject_backtestability,
        )
        batch_manual = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=2,
            payload=manual_payload,
            backtestability_status=manual_backtestability,
        )
        batch_precheck_approve = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=3,
            payload={**approve_payload, "title": "预检批量通过规则"},
            backtestability_status=approve_backtestability,
        )
        batch_precheck_manual = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=4,
            payload={**manual_payload, "title": "预检冲突规则"},
            backtestability_status=manual_backtestability,
        )
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

    service = RuleReviewService(
        session_scope_factory=_session_scope,
        regression_service=_PassingGate(),
    )

    with pytest.raises(RuleReviewTransitionBlockedError):
        await service.apply_batch_action(
            action="approve_low_risk",
            actor_type="human",
            actor_id="reviewer",
            reason="错误地混合低风险和需要人工判断的规则。",
            correlation_id="corr-batch-precheck",
            candidate_ids=[batch_precheck_approve.rule_candidate_id, batch_precheck_manual.rule_candidate_id],
        )
    precheck_detail = await service.get_candidate_detail(candidate_id=batch_precheck_approve.rule_candidate_id)
    assert precheck_detail["current_review_state"] == "候选"
    assert precheck_detail["rule_version_id"] is None

    approved = await service.apply_batch_action(
        action="approve_low_risk",
        actor_type="human",
        actor_id="reviewer",
        reason="批量通过低风险候选规则。",
        correlation_id="corr-batch-approve",
        candidate_ids=[batch_approve.rule_candidate_id],
    )
    assert approved.processed_count == 1
    approved_detail = await service.get_candidate_detail(candidate_id=batch_approve.rule_candidate_id)
    assert approved_detail["current_lifecycle_state"] == "待回测"
    retried = await service.apply_batch_action(
        action="approve_low_risk",
        actor_type="human",
        actor_id="reviewer",
        reason="重试同一批量通过请求。",
        correlation_id="corr-batch-approve",
        candidate_ids=[batch_approve.rule_candidate_id],
    )
    assert retried.processed_count == 1
    async with session_factory() as session:
        queued_events = list(
            (
                await session.execute(
                    select(LifecycleEvent)
                    .where(LifecycleEvent.reason_code == "queued_for_backtest")
                    .where(LifecycleEvent.correlation_id == "corr-batch-approve:0:queue-backtest")
                )
            )
            .scalars()
            .all()
        )
        assert len(queued_events) == 1

    rejected = await service.apply_batch_action(
        action="reject_invalid",
        actor_type="human",
        actor_id="reviewer",
        reason="批量驳回明显无效候选规则。",
        correlation_id="corr-batch-reject",
        candidate_ids=[batch_reject.rule_candidate_id],
    )
    assert rejected.processed_count == 1

    with pytest.raises(RuleReviewTransitionBlockedError):
        await service.apply_batch_action(
            action="approve_low_risk",
            actor_type="human",
            actor_id="reviewer",
            reason="错误地批量通过需要人工判断的规则。",
            correlation_id="corr-batch-blocked",
            candidate_ids=[batch_manual.rule_candidate_id],
        )


@pytest.mark.asyncio
async def test_rule_review_batch_approval_rolls_back_all_mutations_on_mid_batch_failure(tmp_path) -> None:
    from src.services.rule_review_service import RuleReviewService

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stage4-rule-review-batch-rollback.db'}")

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
        article_id = UUID("11111111-aaaa-1111-aaaa-111111111111")
        revision_id = UUID("22222222-bbbb-2222-bbbb-222222222222")
        prompt_run_id = UUID("33333333-cccc-3333-cccc-333333333333")
        structure_id = UUID("44444444-dddd-4444-dddd-444444444444")
        session.add(
            BlogArticle(
                id=article_id,
                source="tgb",
                source_url="https://example.com/article",
                title="批量回滚文章",
                author_name="Dora",
                author_id="author-4",
                published_at=datetime(2026, 6, 15, 9, 30, tzinfo=UTC),
                crawled_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC),
                content_text="原始文章正文",
                summary="文章摘要",
                tags=["突破"],
                content_hash="hash-rollback",
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
                content_hash="hash-rollback",
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
                input_hash="input-hash-rollback",
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
        payload_one, backtestability_one = _payload(title="回滚批量通过规则一")
        payload_two, backtestability_two = _payload(
            title="回滚批量通过规则二",
            condition={
                "logic": "single",
                "clauses": [{"field": "close", "operator": "gt", "value": 2.5, "unit": "x", "lookback": 5}],
            },
        )
        candidate_one = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=0,
            payload=payload_one,
            backtestability_status=backtestability_one,
        )
        candidate_two = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            structure_id=structure_id,
            index=1,
            payload=payload_two,
            backtestability_status=backtestability_two,
        )
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

    class _InjectedBatchFailureRuleReviewService(RuleReviewService):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._batch_item_counter = 0

        async def _after_batch_item_processed(self, **_kwargs) -> None:
            self._batch_item_counter += 1
            if self._batch_item_counter == 2:
                raise RuntimeError("injected mid-batch failure")

    service = _InjectedBatchFailureRuleReviewService(
        session_scope_factory=_session_scope,
        regression_service=_PassingGate(),
    )

    with pytest.raises(RuntimeError, match="injected mid-batch failure"):
        await service.apply_batch_action(
            action="approve_low_risk",
            actor_type="human",
            actor_id="reviewer",
            reason="第二条处理中断，整批必须回滚。",
            correlation_id="corr-batch-rollback",
            candidate_ids=[candidate_one.rule_candidate_id, candidate_two.rule_candidate_id],
        )

    async with session_factory() as session:
        candidates = (
            await session.execute(
                select(RuleCandidate).order_by(RuleCandidate.candidate_index.asc())
            )
        ).scalars().all()
        assert [candidate.review_state for candidate in candidates] == ["extracted", "extracted"]
        assert await session.scalar(select(func.count()).select_from(Rule)) == 0
        assert await session.scalar(select(func.count()).select_from(RuleVersion)) == 0
        assert await session.scalar(select(func.count()).select_from(RuleFamily)) == 0
        assert await session.scalar(select(func.count()).select_from(RuleFamilyMembership)) == 0
        assert await session.scalar(select(func.count()).select_from(RuleVersionSourceLink)) == 0
        assert await session.scalar(select(func.count()).select_from(LifecycleEvent)) == 0
