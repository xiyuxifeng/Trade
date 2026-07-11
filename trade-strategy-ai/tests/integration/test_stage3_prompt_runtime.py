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
from src.llm.runtime import LLMInvocationTrace
from src.models.blog_article import BlogArticle
from src.models.extraction_taxonomy import ExtractionItem
from src.models.stage2_canonical import ArticleRevision, ArticleStructure, PromptRun, RuleCandidate
from src.services.stage3_prompt_runtime_service import ArticlePromptInput, Stage3PromptRuntimeService
from tests.fixtures.taxonomy_samples import article_taxonomy_output


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


class _FakeGateway:
    async def invoke_json(self, *, prompt_name: str, system_prompt: str, user_prompt: str, model: str) -> LLMInvocationTrace:
        del system_prompt, user_prompt, model
        assert prompt_name == "article_taxonomy_v1"
        payload = article_taxonomy_output(["rule_candidate", "semantic_experience"])
        return LLMInvocationTrace(
            provider="test-provider", model="test-model", data=payload, raw_output=payload,
            raw_output_text=str(payload), token_usage={"total_tokens": 50}, cost_amount=None, cost_currency=None,
        )


@pytest.mark.asyncio
async def test_stage3_runtime_persists_taxonomy_items_without_creating_rule_candidates(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stage3-runtime.db'}")

    @event.listens_for(engine.sync_engine, "connect")
    def _register_char_length(dbapi_connection, _connection_record):  # noqa: ANN001
        dbapi_connection.create_function("char_length", 1, lambda value: len(value) if value is not None else 0)

    async with engine.begin() as conn:
        for table in (
            BlogArticle.__table__, ArticleRevision.__table__, PromptRun.__table__, ArticleStructure.__table__,
            RuleCandidate.__table__, ExtractionItem.__table__,
        ):
            await conn.run_sync(lambda sync_conn, current=table: current.create(bind=sync_conn, checkfirst=True))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    article_id = UUID("11111111-1111-1111-1111-111111111111")
    revision_id = UUID("22222222-2222-2222-2222-222222222222")
    async with session_factory() as session:
        session.add(BlogArticle(
            id=article_id, source="tgb", source_url="https://example.com/article", title="示例文章",
            author_name="Alice", author_id="author-1", published_at=datetime(2026, 6, 15, 9, 30, tzinfo=UTC),
            crawled_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC), content_text="突破必须放量确认",
            summary="summary", tags=["突破"], content_hash="hash-1", view_count=1, like_count=0,
            bookmark_count=0, comment_count=0, raw_payload={},
        ))
        session.add(ArticleRevision(
            article_revision_id=revision_id, article_id=article_id, revision_no=1, content_hash="hash-1",
            content_text="突破必须放量确认", content_html=None, source_payload={},
            captured_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC), quality_status="complete",
        ))
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

    service = Stage3PromptRuntimeService(
        session_scope_factory=_session_scope, gateway=_FakeGateway(),
        prompt_run_repository=Stage3PromptRunRepository(),
        article_analysis_repository=Stage3ArticleAnalysisRepository(), model="test-model",
    )
    result = await service.analyze_article(ArticlePromptInput(
        article_id=article_id, article_revision_id=revision_id, article_title="示例文章",
        article_content="突破必须放量确认", source_url="https://example.com/article",
        published_at=datetime(2026, 6, 15, 9, 30, tzinfo=UTC),
    ))

    async with session_factory() as session:
        prompt_run = (await session.execute(select(PromptRun))).scalars().one()
        items = (await session.execute(select(ExtractionItem).order_by(ExtractionItem.item_index))).scalars().all()
        old_count = await session.scalar(select(func.count()).select_from(RuleCandidate))

    assert result.extraction_item_ids == [item.extraction_item_id for item in items]
    assert prompt_run.prompt_name == "article_taxonomy_v1"
    assert [str(item.primary_type) for item in items] == ["rule_candidate", "semantic_experience"]
    assert all(item.source_evidence["article_revision_id"] == str(revision_id) for item in items)
    assert all(item.provenance["taxonomy_version"] == "extraction_taxonomy_v1" for item in items)
    assert old_count == 0
    await engine.dispose()
