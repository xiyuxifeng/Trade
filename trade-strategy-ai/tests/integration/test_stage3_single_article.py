from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.repositories.stage3_prompt_runtime_repository import (
    Stage3ArticleAnalysisRepository,
    Stage3PromptRunRepository,
)
from src.db.repositories.stage3_single_article_repository import Stage3SingleArticleRepository
from src.llm.runtime import LLMInvocationTrace
from src.models.base import Base
from src.models.blog_article import BlogArticle
from src.models.stage2_canonical import (
    ArticleRevision,
    ArticleStructure,
    LifecycleEvent,
    PromptRun,
    Rule,
    RuleCandidate,
    RuleVersion,
)
from src.services.stage3_prompt_runtime_service import ArticlePromptInput, Stage3PromptRuntimeService
from src.services.stage3_single_article_service import Stage3SingleArticleService


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


class _PassingGateway:
    async def invoke_json(self, *, prompt_name: str, system_prompt: str, user_prompt: str, model: str) -> LLMInvocationTrace:
        del system_prompt, user_prompt, model
        if prompt_name != "article_analysis_v1":
            raise AssertionError(prompt_name)
        payload = {
            "prompt_version": "article_analysis_v1",
            "schema_version": "article_analysis_v1",
            "classification": {"article_type": "rule", "confidence": 0.92, "evidence": ["放量突破"]},
            "concept_extraction": {
                "prompt_version": "concept_extraction_v1",
                "schema_version": "concept_v1",
                "concepts": [],
                "trading_symbols": [],
                "indicators": [],
                "chart_patterns": [],
                "market_themes": [],
                "risk_concepts": [],
                "data_dependencies": ["ohlcv_1d"],
                "sentiment": {"score": 0.0, "confidence": 0.0},
                "warnings": [],
            },
            "article_structure": {
                "prompt_version": "article_structure_extraction_v1",
                "schema_version": "article_structure_v1",
                "article_id": "11111111-1111-1111-1111-111111111111",
                "author_id": "author-1",
                "published_at": "2026-06-15T09:30:00Z",
                "article_type": "rule",
                "method_tags": ["突破"],
                "analysis_dimensions": ["price"],
                "instrument_focus": ["stock"],
                "holding_period": {"value": "intraday", "source": "explicit", "confidence": 0.9, "evidence": ["当日"]},
                "entry_patterns": ["放量突破"],
                "exit_patterns": [],
                "risk_concepts": [],
                "data_dependencies": ["ohlcv_1d"],
                "market_state": {"status": "not_declared", "explicit_conditions": [], "inferred_hypotheses": []},
                "key_claims": [{"claim": "放量突破介入", "claim_type": "entry", "source": "explicit", "confidence": 0.9, "evidence": ["放量突破介入"]}],
                "article_quality": {"information_density": "high", "quantifiability": "high", "duplicate_risk": "low", "needs_manual_review": False, "warnings": []},
            },
            "rule_extraction": {
                "prompt_version": "rule_extraction_v1",
                "schema_version": "rule_v1",
                "strategy_rules": [{
                    "rule_key": "rule-1",
                    "title": "放量突破介入",
                    "rule_type": "entry",
                    "instrument_focus": ["stock"],
                    "timeframe": "5m",
                    "holding_period": "intraday",
                    "condition": {"logic": "single", "clauses": [{"field": "volume", "operator": "gt", "value": 1.5, "unit": "x", "lookback": 5, "raw_expression": "放量"}]},
                    "action": {"type": "enter", "side": "buy", "price_reference": "market"},
                    "risk_controls": [],
                    "data_dependencies": ["ohlcv_1d"],
                    "market_state_applicability": {"status": "not_declared", "explicit_conditions": [], "inferred_hypotheses": []},
                    "quantification": {"status": "executable", "missing_fields": [], "ambiguous_terms": [], "manual_review_required": False},
                    "confidence": 0.88,
                    "evidence": [{"quote": "放量突破介入", "supports": "condition"}],
                    "source_article_id": "11111111-1111-1111-1111-111111111111",
                }],
            },
            "explicit_preconditions": {
                "prompt_version": "explicit_precondition_extraction_v1",
                "schema_version": "explicit_precondition_v1",
                "status": "not_declared",
                "preconditions": [],
                "warnings": [],
            },
            "quality": {"needs_repair": False, "repair_reasons": [], "warnings": []},
        }
        return LLMInvocationTrace(
            provider="test-provider",
            model="test-model",
            data=payload,
            raw_output=payload,
            raw_output_text=str(payload),
            token_usage={"prompt_tokens": 20, "completion_tokens": 40, "total_tokens": 60},
            cost_amount=None,
            cost_currency=None,
        )


@pytest.mark.asyncio
async def test_single_article_journey_creates_rule_version_only_after_human_approval(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stage3-single-article.db'}")

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
            LifecycleEvent.__table__,
        ):
            await conn.run_sync(lambda sync_conn, current_table=table: current_table.create(bind=sync_conn, checkfirst=True))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        article_id = UUID("11111111-1111-1111-1111-111111111111")
        revision_id = UUID("22222222-2222-2222-2222-222222222222")
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
                source_payload={},
                captured_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC),
                quality_status="complete",
            )
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

    runtime_service = Stage3PromptRuntimeService(
        session_scope_factory=_session_scope,
        gateway=_PassingGateway(),
        prompt_run_repository=Stage3PromptRunRepository(),
        article_analysis_repository=Stage3ArticleAnalysisRepository(),
        model="test-model",
    )
    single_article_service = Stage3SingleArticleService(
        session_scope_factory=_session_scope,
        prompt_runtime_service=runtime_service,
        repository=Stage3SingleArticleRepository(),
    )

    analyzed = await single_article_service.run_analysis(
        article_id=article_id,
        article_revision_id=revision_id,
    )
    assert analyzed.status == "ready"
    assert len(analyzed.candidates) == 1
    candidate = analyzed.candidates[0]
    assert analyzed.automatic_reviews[candidate.rule_candidate_id].status == "pending_backtest"

    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(RuleVersion)) == 0

    reviewed = await single_article_service.review_candidate(
        article_id=article_id,
        article_revision_id=revision_id,
        candidate_id=candidate.rule_candidate_id,
        decision="approve",
        actor_id="operator-user",
        reason="证据充分，进入待回测。",
    )
    assert reviewed.rule_versions[candidate.rule_candidate_id].lifecycle_state == "draft"

    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(RuleVersion)) == 1
        version = (await session.execute(select(RuleVersion))).scalars().one()
        events = (await session.execute(select(LifecycleEvent).order_by(LifecycleEvent.occurred_at.asc()))).scalars().all()

    assert version.source_candidate_id == candidate.rule_candidate_id
    assert version.lifecycle_state == "draft"
    assert version.published_at is None
    assert len(events) == 2
    assert events[0].actor_id == "operator-user"
    assert events[0].reason_text == "证据充分，进入待回测。"

    await engine.dispose()


@pytest.mark.asyncio
async def test_single_article_journey_binds_summary_to_selected_revision(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stage3-single-article-summary.db'}")

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
    article_id = UUID("33333333-3333-3333-3333-333333333333")
    old_revision_id = UUID("44444444-4444-4444-4444-444444444444")
    latest_revision_id = UUID("55555555-5555-5555-5555-555555555555")
    old_prompt_run_id = UUID("66666666-6666-6666-6666-666666666666")
    latest_prompt_run_id = UUID("77777777-7777-7777-7777-777777777777")
    old_structure_id = UUID("88888888-8888-8888-8888-888888888888")
    latest_structure_id = UUID("99999999-9999-9999-9999-999999999999")

    async with session_factory() as session:
        session.add(
            BlogArticle(
                id=article_id,
                source="tgb",
                source_url="https://example.com/article-summary",
                title="双版本文章",
                author_name="Alice",
                author_id="author-1",
                published_at=datetime(2026, 6, 15, 9, 30, tzinfo=UTC),
                crawled_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC),
                content_text="最新原文",
                summary="最新版本摘要",
                tags=["突破"],
                content_hash="hash-new",
                view_count=1,
                like_count=0,
                bookmark_count=0,
                comment_count=0,
                raw_payload={},
            )
        )
        session.add_all(
            [
                ArticleRevision(
                    article_revision_id=old_revision_id,
                    article_id=article_id,
                    revision_no=1,
                    content_hash="hash-old",
                    content_text="旧版清洗正文",
                    content_html=None,
                    source_payload={"summary": "旧版本摘要"},
                    captured_at=datetime(2026, 6, 14, 9, 40, tzinfo=UTC),
                    quality_status="complete",
                ),
                ArticleRevision(
                    article_revision_id=latest_revision_id,
                    article_id=article_id,
                    revision_no=2,
                    content_hash="hash-new",
                    content_text="新版清洗正文",
                    content_html=None,
                    source_payload={},
                    captured_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC),
                    quality_status="complete",
                ),
                PromptRun(
                    prompt_run_id=old_prompt_run_id,
                    run_id="run-old",
                    article_id=article_id,
                    prompt_name="article_analysis_v1",
                    prompt_version="article_analysis_v1",
                    schema_name="article_analysis_v1",
                    schema_version="article_analysis_v1",
                    provider="test-provider",
                    model="test-model",
                    input_object_type="article_revision",
                    input_object_id=str(article_id),
                    input_version_id=str(old_revision_id),
                    input_hash="hash-old-run",
                    request_json={},
                    raw_output={},
                    raw_output_text="{}",
                    validation_state="valid",
                    validation_errors={},
                    retry_count=0,
                    token_usage={},
                    cost_amount=None,
                    cost_currency=None,
                    started_at=datetime(2026, 6, 14, 9, 41, tzinfo=UTC),
                    completed_at=datetime(2026, 6, 14, 9, 42, tzinfo=UTC),
                ),
                PromptRun(
                    prompt_run_id=latest_prompt_run_id,
                    run_id="run-latest",
                    article_id=article_id,
                    prompt_name="article_analysis_v1",
                    prompt_version="article_analysis_v1",
                    schema_name="article_analysis_v1",
                    schema_version="article_analysis_v1",
                    provider="test-provider",
                    model="test-model",
                    input_object_type="article_revision",
                    input_object_id=str(article_id),
                    input_version_id=str(latest_revision_id),
                    input_hash="hash-latest-run",
                    request_json={},
                    raw_output={},
                    raw_output_text="{}",
                    validation_state="valid",
                    validation_errors={},
                    retry_count=0,
                    token_usage={},
                    cost_amount=None,
                    cost_currency=None,
                    started_at=datetime(2026, 6, 15, 9, 41, tzinfo=UTC),
                    completed_at=datetime(2026, 6, 15, 9, 42, tzinfo=UTC),
                ),
                ArticleStructure(
                    article_structure_id=old_structure_id,
                    article_id=article_id,
                    article_revision_id=old_revision_id,
                    prompt_run_id=old_prompt_run_id,
                    schema_version="article_analysis_v1",
                    payload={"method_tags": ["旧标签"], "key_claims": []},
                    evidence_json={},
                    missing_fields={},
                    inference_fields={},
                    lifecycle_state="draft",
                    quality_status="partial",
                    created_by="test",
                    updated_by="test",
                ),
                ArticleStructure(
                    article_structure_id=latest_structure_id,
                    article_id=article_id,
                    article_revision_id=latest_revision_id,
                    prompt_run_id=latest_prompt_run_id,
                    schema_version="article_analysis_v1",
                    payload={"method_tags": ["新标签"], "key_claims": []},
                    evidence_json={},
                    missing_fields={},
                    inference_fields={},
                    lifecycle_state="draft",
                    quality_status="partial",
                    created_by="test",
                    updated_by="test",
                ),
            ]
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
        repository=Stage3SingleArticleRepository(),
    )

    latest = await service.get_journey(article_id=article_id, article_revision_id=latest_revision_id)
    older = await service.get_journey(article_id=article_id, article_revision_id=old_revision_id)

    assert latest.summary_provenance.summary == "最新版本摘要"
    assert latest.summary_provenance.source == "blog_article_current"
    assert latest.summary_provenance.available is True
    assert latest.summary_provenance.article_revision_id == str(latest_revision_id)
    assert latest.summary_provenance.content_hash == "hash-new"
    assert latest.article_structure_provenance.article_revision_id == str(latest_revision_id)
    assert latest.structure.payload["method_tags"] == ["新标签"]

    assert older.summary_provenance.summary == "旧版本摘要"
    assert older.summary_provenance.source == "article_revision_source_payload"
    assert older.summary_provenance.available is True
    assert older.summary_provenance.article_revision_id == str(old_revision_id)
    assert older.summary_provenance.content_hash == "hash-old"
    assert older.summary_provenance.summary != latest.summary_provenance.summary
    assert older.article_structure_provenance.article_revision_id == str(old_revision_id)
    assert older.structure.payload["method_tags"] == ["旧标签"]

    await engine.dispose()
