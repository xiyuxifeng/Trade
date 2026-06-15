from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.base import Base
from src.models.blog_article import BlogArticle
from src.models.job import Job
from src.models.stage2_canonical import ArticleRevision, ArticleStructure, LifecycleEvent, PromptRun, Rule, RuleCandidate, RuleVersion
from src.services.stage3_batch_service import Stage3BatchService
from src.services.stage3_regression_fixtures import RegressionArticleFixture
from src.services.stage3_regression_service import (
    FixedFixtureGateway,
    Stage3RegressionService,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


@pytest.mark.asyncio
async def test_stage3_batch_dry_run_creates_single_checkpointed_job(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stage3-batch-integration.db'}")

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

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    fixture = RegressionArticleFixture.for_test_case(
        article_id=uuid4(),
        article_revision_id=uuid4(),
        content_hash="hash-integration",
        title="批处理集成样本",
        article_content="批处理集成样本文本，包含竞价和规则说明。",
        covered_categories={"explicit_and_actionable_rules", "human_review_required", "kaipan_dependency"},
        selection_reason="integration",
        expected_outcome_ambiguity="clear",
        summary_available=False,
        method_tags=["竞价"],
        explicit_facts_contains=["竞价"],
        candidate_title="竞价强转弱不接力",
        data_dependencies_contains=["kaipan_tick"],
        backtestability_statuses=["partially_executable"],
        automatic_review_statuses=["needs_human_review"],
        market_state_status="not_declared",
        kaipan_dependency=True,
        ambiguous_terms=["强转弱"],
    )

    async with session_factory() as session:
        session.add(
            BlogArticle(
                id=fixture.article_id,
                source="tgb",
                source_url="https://example.com/batch",
                title=fixture.title,
                author_name="Author",
                author_id="author-1",
                published_at=datetime(2026, 6, 15, 9, 30, tzinfo=UTC),
                crawled_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC),
                content_text=fixture.article_content,
                summary=None,
                tags=["竞价"],
                content_hash=fixture.content_hash,
                view_count=1,
                like_count=0,
                bookmark_count=0,
                comment_count=0,
                raw_payload={},
            )
        )
        session.add(
            ArticleRevision(
                article_revision_id=fixture.article_revision_id,
                article_id=fixture.article_id,
                revision_no=1,
                content_hash=fixture.content_hash,
                content_text=fixture.article_content,
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

    gateway = FixedFixtureGateway({fixture.article_revision_id: fixture})
    regression = Stage3RegressionService(
        session_scope_factory=lambda: _session_scope(),
        manifest=[fixture],
        gateway=gateway,
        model="fixture-model",
    )
    batch = Stage3BatchService(
        session_scope_factory=lambda: _session_scope(),
        regression_service=regression,
        manifest=[fixture],
        gateway=gateway,
        model="fixture-model",
        concurrency_limit=1,
    )

    result = await batch.run(dry_run=True, limit=1)

    assert result.status == "completed"
    assert result.gate_result.status == "passed"
    assert result.processed_count == 1

    async with session_factory() as session:
        jobs = (await session.execute(Job.__table__.select())).all()
        assert len(jobs) == 1

    await engine.dispose()
