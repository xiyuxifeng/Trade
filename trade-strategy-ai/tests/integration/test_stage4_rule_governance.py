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
from src.services.stage3_regression_service import RegressionRunResult
from src.services.stage3_single_article_service import Stage3SingleArticleService


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


async def _seed_candidate(
    session: AsyncSession,
    *,
    article_id: UUID,
    revision_id: UUID,
    prompt_run_id: UUID,
    index: int,
    payload: dict,
    structure_id: UUID | None = None,
) -> RuleCandidate:
    structure_id = structure_id or uuid4()
    existing_structure = await session.get(ArticleStructure, structure_id)
    if existing_structure is None:
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
        candidate_index=index,
        candidate_fingerprint=f"legacy-{index}",
        rule_type="entry",
        canonical_payload=payload,
        evidence_json={"items": payload["evidence"]},
        explicit_fields={"title": payload["title"]},
        inferred_fields={},
        missing_fields={},
        data_dependencies={"required": payload["data_dependencies"]},
        backtestability_status="executable",
        review_state="manual_review",
        quality_status="complete",
        created_by="tester",
        updated_by="tester",
    )
    session.add(candidate)
    await session.flush()
    return candidate


@pytest.mark.asyncio
async def test_stage4_governance_reuses_existing_rule_version_for_exact_duplicate(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stage4-rule-governance.db'}")

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
        structure_id = uuid4()
        first_candidate = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            index=0,
            payload=_candidate_payload(),
            structure_id=structure_id,
        )
        duplicate_candidate = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            index=1,
            payload=_candidate_payload(title="同义文案"),
            structure_id=structure_id,
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

    service = Stage3SingleArticleService(
        session_scope_factory=_session_scope,
        regression_service=_PassingGate(),
    )

    first = await service.review_candidate(
        article_id=article_id,
        article_revision_id=revision_id,
        candidate_id=first_candidate.rule_candidate_id,
        decision="approve",
        actor_id="operator-user",
        reason="首次进入正式规则。",
    )
    duplicate = await service.review_candidate(
        article_id=article_id,
        article_revision_id=revision_id,
        candidate_id=duplicate_candidate.rule_candidate_id,
        decision="approve",
        actor_id="operator-user",
        reason="同义重复来源，链接到既有正式规则。",
    )

    first_version_id = first.rule_versions[first_candidate.rule_candidate_id].rule_version_id
    duplicate_version_id = duplicate.rule_versions[duplicate_candidate.rule_candidate_id].rule_version_id
    assert duplicate_version_id == first_version_id

    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Rule)) == 1
        assert await session.scalar(select(func.count()).select_from(RuleVersion)) == 1
        assert await session.scalar(select(func.count()).select_from(RuleFamily)) == 1
        assert await session.scalar(select(func.count()).select_from(RuleFamilyMembership)) == 1
        events = (await session.execute(select(LifecycleEvent).order_by(LifecycleEvent.occurred_at.asc()))).scalars().all()

    assert any(event.correlation_id == str(first_version_id) for event in events)
    await engine.dispose()


@pytest.mark.asyncio
async def test_stage4_governance_blocks_candidate_review_when_fixed_set_gate_fails(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stage4-gate-block.db'}")

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
        ):
            await conn.run_sync(lambda sync_conn, current_table=table: current_table.create(bind=sync_conn, checkfirst=True))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        article_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        revision_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        prompt_run_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
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
        structure_id = uuid4()
        candidate = await _seed_candidate(
            session,
            article_id=article_id,
            revision_id=revision_id,
            prompt_run_id=prompt_run_id,
            index=0,
            payload=_candidate_payload(),
            structure_id=structure_id,
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

    service = Stage3SingleArticleService(
        session_scope_factory=_session_scope,
        regression_service=_FailingGate(),
    )

    with pytest.raises(Exception):
        await service.review_candidate(
            article_id=article_id,
            article_revision_id=revision_id,
            candidate_id=candidate.rule_candidate_id,
            decision="approve",
            actor_id="operator-user",
            reason="gate should block",
        )

    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(RuleCandidate)) == 1

    await engine.dispose()
