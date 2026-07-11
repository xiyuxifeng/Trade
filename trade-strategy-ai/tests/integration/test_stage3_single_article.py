from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.repositories.stage3_prompt_runtime_repository import Stage3ArticleAnalysisRepository, Stage3PromptRunRepository
from src.db.repositories.stage3_single_article_repository import Stage3SingleArticleRepository
from src.llm.runtime import LLMInvocationTrace
from src.models.blog_article import BlogArticle
from src.models.extraction_taxonomy import ExtractionItem
from src.models.stage2_canonical import (
    ArticleRevision, ArticleStructure, LifecycleEvent, PromptRun, Rule, RuleCandidate, RuleVersion,
)
from src.services.stage3_prompt_runtime_service import Stage3PromptRuntimeService
from src.services.stage3_single_article_service import Stage3SingleArticleError, Stage3SingleArticleService
from tests.fixtures.taxonomy_samples import PAYLOADS, article_taxonomy_output


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


class _PassingGateway:
    async def invoke_json(self, *, prompt_name: str, system_prompt: str, user_prompt: str, model: str) -> LLMInvocationTrace:
        del system_prompt, user_prompt, model
        assert prompt_name == "article_taxonomy_v1"
        payload = article_taxonomy_output(["executable_rule", "semantic_experience", "rule_candidate"])
        return LLMInvocationTrace(
            provider="test-provider", model="test-model", data=payload, raw_output=payload,
            raw_output_text=str(payload), token_usage={"total_tokens": 60}, cost_amount=None, cost_currency=None,
        )


def _article(article_id: UUID) -> BlogArticle:
    return BlogArticle(
        id=article_id, source="tgb", source_url="https://example.com/article", title="示例文章",
        author_name="Alice", author_id="author-1", published_at=datetime(2026, 6, 15, 9, 30, tzinfo=UTC),
        crawled_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC), content_text="原始文章正文",
        summary="最新版本摘要", tags=["突破"], content_hash="hash-1", view_count=1, like_count=0,
        bookmark_count=0, comment_count=0, raw_payload={},
    )


async def _create_tables(engine, *, governance: bool) -> None:
    tables = [BlogArticle.__table__, ArticleRevision.__table__, PromptRun.__table__, ArticleStructure.__table__, RuleCandidate.__table__, ExtractionItem.__table__]
    if governance:
        tables += [Rule.__table__, RuleVersion.__table__, LifecycleEvent.__table__]
    async with engine.begin() as conn:
        for table in tables:
            await conn.run_sync(lambda sync_conn, current=table: current.create(bind=sync_conn, checkfirst=True))


@pytest.mark.asyncio
async def test_only_accepted_strict_executable_item_creates_rule_version(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'single.db'}")
    @event.listens_for(engine.sync_engine, "connect")
    def _register_char_length(dbapi_connection, _connection_record):  # noqa: ANN001
        dbapi_connection.create_function("char_length", 1, lambda value: len(value) if value is not None else 0)
    await _create_tables(engine, governance=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    article_id = UUID("11111111-1111-1111-1111-111111111111")
    revision_id = UUID("22222222-2222-2222-2222-222222222222")
    async with session_factory() as session:
        session.add(_article(article_id))
        session.add(ArticleRevision(
            article_revision_id=revision_id, article_id=article_id, revision_no=1, content_hash="hash-1",
            content_text="清洗后的文章正文", content_html=None, source_payload={},
            captured_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC), quality_status="complete",
        ))
        await session.commit()

    @asynccontextmanager
    async def scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    runtime = Stage3PromptRuntimeService(
        session_scope_factory=scope, gateway=_PassingGateway(), prompt_run_repository=Stage3PromptRunRepository(),
        article_analysis_repository=Stage3ArticleAnalysisRepository(), model="test-model",
    )
    service = Stage3SingleArticleService(session_scope_factory=scope, prompt_runtime_service=runtime, repository=Stage3SingleArticleRepository())
    analyzed = await service.run_analysis(article_id=article_id, article_revision_id=revision_id)
    assert [str(item.primary_type) for item in analyzed.extraction_items] == ["executable_rule", "semantic_experience", "rule_candidate"]
    executable, semantic, candidate = analyzed.extraction_items
    assert analyzed.eligibilities[executable.extraction_item_id].eligible is False

    with pytest.raises(Stage3SingleArticleError):
        await service.promote_executable_item(article_id=article_id, item_id=semantic.extraction_item_id, actor_id="operator")
    repaired_journey = await service.repair_rule_candidate(
        article_id=article_id,
        item_id=candidate.extraction_item_id,
        repaired_payload={"primary_type": "executable_rule", **PAYLOADS["executable_rule"]},
        source_quote="指数跌破共振日低点立即退出。",
        rationale="bounded human repair used only traceable source mechanics",
        actor_id="operator",
        article_revision_id=revision_id,
    )
    repaired = next(item for item in repaired_journey.extraction_items if item.provenance.get("origin") == "repair_output")
    assert str(repaired.primary_type) == "executable_rule"
    assert repaired.provenance["lineage"] == [str(candidate.extraction_item_id)]
    assert repaired_journey.eligibilities[repaired.extraction_item_id].eligible is False
    await service.review_extraction_item(
        article_id=article_id, item_id=executable.extraction_item_id, decision="accept", actor_id="operator",
        reason="strict validation accepted", article_revision_id=revision_id,
    )
    promoted = await service.promote_executable_item(
        article_id=article_id, item_id=executable.extraction_item_id, actor_id="operator", article_revision_id=revision_id,
    )
    version = promoted.rule_versions[executable.extraction_item_id]
    assert version.source_candidate_id is None
    assert version.source_extraction_item_id == executable.extraction_item_id
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(RuleVersion)) == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_single_article_journey_binds_summary_to_selected_revision(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'summary.db'}")
    @event.listens_for(engine.sync_engine, "connect")
    def _register_char_length(dbapi_connection, _connection_record):  # noqa: ANN001
        dbapi_connection.create_function("char_length", 1, lambda value: len(value) if value is not None else 0)
    await _create_tables(engine, governance=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    article_id = UUID("33333333-3333-3333-3333-333333333333")
    old_revision_id = UUID("44444444-4444-4444-4444-444444444444")
    new_revision_id = UUID("55555555-5555-5555-5555-555555555555")
    async with session_factory() as session:
        article = _article(article_id)
        article.content_hash = "hash-new"
        session.add(article)
        for revision_id, number, content_hash, source_payload in (
            (old_revision_id, 1, "hash-old", {"summary": "旧版本摘要"}),
            (new_revision_id, 2, "hash-new", {}),
        ):
            prompt_id = UUID(int=revision_id.int + 100)
            structure_id = UUID(int=revision_id.int + 200)
            session.add(ArticleRevision(
                article_revision_id=revision_id, article_id=article_id, revision_no=number, content_hash=content_hash,
                content_text=f"正文-{number}", content_html=None, source_payload=source_payload,
                captured_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC), quality_status="complete",
            ))
            session.add(PromptRun(
                prompt_run_id=prompt_id, run_id=f"run-{number}", article_id=article_id,
                prompt_name="article_taxonomy_v1", prompt_version="article_taxonomy_v1", schema_name="article_taxonomy_v1",
                schema_version="article_taxonomy_v1", provider="test", model="test", input_object_type="article_revision",
                input_object_id=str(article_id), input_version_id=str(revision_id), input_hash=f"input-{number}",
                request_json={}, raw_output={}, raw_output_text="{}", validation_state="valid", validation_errors={},
                retry_count=0, token_usage={}, started_at=datetime.now(UTC), completed_at=datetime.now(UTC),
            ))
            session.add(ArticleStructure(
                article_structure_id=structure_id, article_id=article_id, article_revision_id=revision_id,
                prompt_run_id=prompt_id, schema_version="article_taxonomy_v1",
                payload={"method_tags": [f"标签-{number}"], "key_claims": []}, evidence_json={}, missing_fields={},
                inference_fields={}, lifecycle_state="draft", quality_status="partial", created_by="test", updated_by="test",
            ))
        await session.commit()

    @asynccontextmanager
    async def scope():
        async with session_factory() as session:
            yield session

    service = Stage3SingleArticleService(session_scope_factory=scope, repository=Stage3SingleArticleRepository())
    latest = await service.get_journey(article_id=article_id, article_revision_id=new_revision_id)
    older = await service.get_journey(article_id=article_id, article_revision_id=old_revision_id)
    assert latest.summary_provenance.summary == "最新版本摘要"
    assert latest.summary_provenance.source == "blog_article_current"
    assert older.summary_provenance.summary == "旧版本摘要"
    assert older.summary_provenance.source == "article_revision_source_payload"
    await engine.dispose()
