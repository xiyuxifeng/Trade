from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.base import Base
from src.models.blog_article import BlogArticle
from src.models.job import Job
from src.models.stage2_canonical import ArticleRevision, ArticleStructure, LifecycleEvent, PromptRun, Rule, RuleCandidate, RuleVersion
from src.services.stage3_batch_service import Stage3BatchService
from src.services.stage3_regression_fixtures import (
    RegressionArticleFixture,
    RegressionSemanticAssertions,
    RegressionSummaryExpectation,
)
from src.services.stage3_regression_service import (
    FixedFixtureGateway,
    RegressionRunResult,
    Stage3RegressionService,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


@pytest.fixture
async def session_factory(tmp_path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stage3-batch.db'}")

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
            Job.__table__,
        ):
            await conn.run_sync(lambda sync_conn, current_table=table: current_table.create(bind=sync_conn, checkfirst=True))

    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@asynccontextmanager
async def _session_scope(factory: async_sessionmaker[AsyncSession]):
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _seed_fixture_articles(
    session_factory: async_sessionmaker[AsyncSession],
    fixtures: list[RegressionArticleFixture],
) -> None:
    async with session_factory() as session:
        for index, fixture in enumerate(fixtures, start=1):
            session.add(
                BlogArticle(
                    id=fixture.article_id,
                    source="tgb",
                    source_url=f"https://example.com/articles/{index}",
                    title=fixture.title,
                    author_name="Author",
                    author_id="author-1",
                    published_at=datetime(2026, 6, index, 9, 30, tzinfo=UTC),
                    crawled_at=datetime(2026, 6, index, 9, 40, tzinfo=UTC),
                    content_text=fixture.article_content,
                    summary=fixture.summary_expectation.summary,
                    tags=list(fixture.semantic_assertions.method_tags),
                    content_hash=fixture.content_hash,
                    view_count=1,
                    like_count=0,
                    bookmark_count=0,
                    comment_count=0,
                    raw_payload={},
                )
            )
            source_payload = {}
            if fixture.summary_expectation.source == "article_revision_source_payload":
                source_payload["summary"] = fixture.summary_expectation.summary
            session.add(
                ArticleRevision(
                    article_revision_id=fixture.article_revision_id,
                    article_id=fixture.article_id,
                    revision_no=1,
                    content_hash=fixture.content_hash,
                    content_text=fixture.article_content,
                    content_html=None,
                    source_payload=source_payload,
                    captured_at=datetime(2026, 6, index, 9, 40, tzinfo=UTC),
                    quality_status="complete",
                )
            )
        await session.commit()


def _fixture(
    *,
    title: str,
    categories: set[str],
    candidate_title: str | None,
    backtestability_status: str = "executable",
    market_state_status: str = "not_declared",
    kaipan_dependency: bool = False,
    ambiguous_terms: list[str] | None = None,
    missing_fields: list[str] | None = None,
    exercise_repair: bool = False,
    provider_failures_before_success: int = 0,
    summary_available: bool = True,
) -> RegressionArticleFixture:
    return RegressionArticleFixture.for_test_case(
        article_id=uuid4(),
        article_revision_id=uuid4(),
        content_hash=f"hash-{uuid4()}",
        title=title,
        article_content=f"{title} 正文，包含 {candidate_title or '概念说明'}",
        covered_categories=categories,
        selection_reason="test fixture",
        expected_outcome_ambiguity="clear",
        summary_available=summary_available,
        summary_source="blog_article_current" if summary_available else "unavailable",
        summary_contains=title[:4] if summary_available else None,
        method_tags=["概念"] if candidate_title is None else ["规则"],
        explicit_facts_contains=[title[:4]],
        hypotheses_contains=ambiguous_terms or [],
        missing_fields_contains=missing_fields or [],
        candidate_title=candidate_title,
        data_dependencies_contains=[] if candidate_title is None else (["kaipan_tick"] if kaipan_dependency else ["ohlcv_1d"]),
        backtestability_statuses=[] if candidate_title is None else [backtestability_status],
        automatic_review_statuses=[] if candidate_title is None else [
            "pending_backtest"
            if backtestability_status == "executable" and not kaipan_dependency and not (ambiguous_terms or missing_fields)
            else "needs_human_review"
        ],
        market_state_status=market_state_status,
        kaipan_dependency=kaipan_dependency,
        ambiguous_terms=ambiguous_terms or [],
        missing_fields=missing_fields or [],
        exercise_repair=exercise_repair,
        provider_failures_before_success=provider_failures_before_success,
    )


@pytest.mark.asyncio
async def test_regression_service_detects_semantic_assertion_failure(session_factory) -> None:
    fixture = _fixture(
        title="规则文章",
        categories={"explicit_and_actionable_rules"},
        candidate_title="放量突破介入",
    )
    bad_fixture = fixture.with_semantic_assertions(
        RegressionSemanticAssertions(
            **{
                **fixture.semantic_assertions.model_dump(),
                "method_tags": ["不会出现的标签"],
            }
        )
    )
    await _seed_fixture_articles(session_factory, [bad_fixture])
    gateway = FixedFixtureGateway({fixture.article_revision_id: fixture})

    service = Stage3RegressionService(
        session_scope_factory=lambda: _session_scope(session_factory),
        manifest=[bad_fixture],
        gateway=gateway,
        model="fixture-model",
    )

    result = await service.run_fixed_set()

    assert result.status == "failed"
    assert result.semantic_failures


@pytest.mark.asyncio
async def test_regression_service_is_idempotent_on_repeated_runs(session_factory) -> None:
    fixture = _fixture(
        title="可执行规则",
        categories={"explicit_and_actionable_rules"},
        candidate_title="放量突破介入",
        exercise_repair=True,
        provider_failures_before_success=1,
        summary_available=False,
    )
    await _seed_fixture_articles(session_factory, [fixture])
    gateway = FixedFixtureGateway({fixture.article_revision_id: fixture})

    service = Stage3RegressionService(
        session_scope_factory=lambda: _session_scope(session_factory),
        manifest=[fixture],
        gateway=gateway,
        model="fixture-model",
    )

    first = await service.run_fixed_set()
    second = await service.run_fixed_set()

    assert first.status == "passed"
    assert second.status == "passed"
    assert first.repaired_count == 1
    assert first.cached_count == 0
    assert second.cached_count == 1

    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(PromptRun)) == 2
        assert await session.scalar(select(func.count()).select_from(ArticleStructure)) == 1
        assert await session.scalar(select(func.count()).select_from(RuleCandidate)) == 1

    assert [name for name, _ in gateway.calls].count("article_analysis_v1") == 2
    assert [name for name, _ in gateway.calls].count("article_analysis_repair_v1") == 1


@pytest.mark.asyncio
async def test_batch_service_blocks_dry_run_when_regression_gate_fails(session_factory) -> None:
    fixture = _fixture(
        title="门禁失败样本",
        categories={"explicit_and_actionable_rules"},
        candidate_title="失败规则",
    )
    await _seed_fixture_articles(session_factory, [fixture])

    class _FailedGate:
        async def run_fixed_set(self):
            return RegressionRunResult.failed(
                manifest=[fixture],
                gate_version="stage3-fixed-set-v1",
                semantic_failures=["fixture failed"],
            )

    service = Stage3BatchService(
        session_scope_factory=lambda: _session_scope(session_factory),
        regression_service=_FailedGate(),
        manifest=[fixture],
        model="fixture-model",
    )

    result = await service.run(dry_run=True, limit=15)

    assert result.status == "blocked"
    assert result.gate_result.status == "failed"


@pytest.mark.asyncio
async def test_batch_service_resume_incremental_concurrency_and_retry(session_factory) -> None:
    fixtures = [
        _fixture(
            title="样本一",
            categories={"explicit_and_actionable_rules"},
            candidate_title="规则一",
            provider_failures_before_success=1,
            summary_available=False,
        ),
        _fixture(
            title="样本二",
            categories={"mixed_concept_and_rule_content"},
            candidate_title="规则二",
            backtestability_status="partially_executable",
            ambiguous_terms=["强势"],
            summary_available=False,
        ),
        _fixture(
            title="样本三",
            categories={"kaipan_dependency"},
            candidate_title="竞价规则",
            kaipan_dependency=True,
            summary_available=False,
        ),
    ]
    await _seed_fixture_articles(session_factory, fixtures)
    gateway = FixedFixtureGateway({fixture.article_revision_id: fixture for fixture in fixtures})
    regression = Stage3RegressionService(
        session_scope_factory=lambda: _session_scope(session_factory),
        manifest=fixtures,
        gateway=gateway,
        model="fixture-model",
    )
    service = Stage3BatchService(
        session_scope_factory=lambda: _session_scope(session_factory),
        regression_service=regression,
        manifest=fixtures,
        gateway=gateway,
        model="fixture-model",
        concurrency_limit=2,
    )

    failed = await service.run(dry_run=False, limit=3, fail_after_items=2)
    resumed = await service.run(dry_run=False, limit=3)

    assert failed.status == "failed"
    assert resumed.status == "completed"
    assert resumed.processed_count == 1
    assert resumed.skipped_count >= 2
    assert resumed.retry_count == 0
    assert gateway.max_active_calls <= 2

    async with session_factory() as session:
        jobs = (await session.execute(select(Job).order_by(Job.created_at.asc()))).scalars().all()
        assert len(jobs) == 1
        checkpoint = jobs[0].runtime_state["checkpoint"]
        assert checkpoint["processed_count"] == 3
        assert checkpoint["processed_items"]
        assert checkpoint["processed_items"][0]["input_hash"]
        assert checkpoint["processed_items"][0]["prompt_run_id"]
        assert checkpoint["processed_items"][0]["validation_state"] in {"valid", "repaired", "PromptValidationState.valid", "PromptValidationState.repaired"}
        assert jobs[0].progress["resume_point"]
        assert jobs[0].result["rejected_or_conflicted_items"] == []

    changed_revision = ArticleRevision(
        article_revision_id=uuid4(),
        article_id=fixtures[0].article_id,
        revision_no=2,
        content_hash="new-hash",
        content_text="样本一 新版本正文",
        content_html=None,
        source_payload={},
        captured_at=datetime(2026, 7, 1, 9, 40, tzinfo=UTC),
        quality_status="complete",
    )
    updated_fixture = fixtures[0].clone_for_revision(
        article_revision_id=changed_revision.article_revision_id,
        content_hash="new-hash",
        article_content="样本一 新版本正文",
    )
    gateway.fixtures[updated_fixture.article_revision_id] = updated_fixture
    async with session_factory() as session:
        session.add(changed_revision)
        await session.commit()

    service = Stage3BatchService(
        session_scope_factory=lambda: _session_scope(session_factory),
        regression_service=Stage3RegressionService(
            session_scope_factory=lambda: _session_scope(session_factory),
            manifest=[updated_fixture, fixtures[1], fixtures[2]],
            gateway=gateway,
            model="fixture-model",
        ),
        manifest=[updated_fixture, fixtures[1], fixtures[2]],
        gateway=gateway,
        model="fixture-model",
        concurrency_limit=2,
    )
    incremental = await service.run(dry_run=False, limit=3)

    assert incremental.status == "completed"
    assert incremental.processed_count == 1
