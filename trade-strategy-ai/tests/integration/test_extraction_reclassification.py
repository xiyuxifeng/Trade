from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import event, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.blog_article import BlogArticle
from src.models.extraction_taxonomy import (
    ExtractionItem,
    ExtractionReclassificationItem,
    ExtractionReclassificationRun,
)
from src.models.stage2_canonical import ArticleRevision, ArticleStructure, PromptRun, RuleCandidate
from src.services.extraction_reclassification_service import ExtractionReclassificationService
from tests.fixtures.taxonomy_samples import draft_for


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


def snapshot(candidate: RuleCandidate) -> str:
    return json.dumps(
        {
            "id": str(candidate.rule_candidate_id),
            "payload": candidate.canonical_payload,
            "evidence": candidate.evidence_json,
            "missing": candidate.missing_fields,
            "status": candidate.backtestability_status,
            "review": str(candidate.review_state),
            "quality": str(candidate.quality_status),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


@pytest.mark.asyncio
async def test_bounded_reclassification_is_append_only_repeatable_and_covers_all_types(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'reclass.db'}")
    @event.listens_for(engine.sync_engine, "connect")
    def _register_char_length(dbapi_connection, _connection_record):  # noqa: ANN001
        dbapi_connection.create_function("char_length", 1, lambda value: len(value) if value is not None else 0)
    async with engine.begin() as conn:
        for table in (
            BlogArticle.__table__, ArticleRevision.__table__, PromptRun.__table__, ArticleStructure.__table__,
            RuleCandidate.__table__, ExtractionReclassificationRun.__table__, ExtractionItem.__table__,
            ExtractionReclassificationItem.__table__,
        ):
            await conn.run_sync(lambda sync_conn, current=table: current.create(bind=sync_conn, checkfirst=True))
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    article_id, revision_id, source_run_id, structure_id = uuid4(), uuid4(), uuid4(), uuid4()
    candidate_ids = [uuid4() for _ in range(7)]
    async with factory() as session:
        session.add(BlogArticle(
            id=article_id, source="fixture", source_url="https://example.com/reclass", title="旧候选样本",
            author_name="test", author_id="test", published_at=datetime.now(UTC), crawled_at=datetime.now(UTC),
            content_text="fixture", summary=None, tags=[], content_hash="old-hash", view_count=0, like_count=0,
            bookmark_count=0, comment_count=0, raw_payload={},
        ))
        session.add(ArticleRevision(
            article_revision_id=revision_id, article_id=article_id, revision_no=1, content_hash="old-hash",
            content_text="fixture", content_html=None, source_payload={}, captured_at=datetime.now(UTC), quality_status="complete",
        ))
        session.add(PromptRun(
            prompt_run_id=source_run_id, run_id="old-run", article_id=article_id, prompt_name="article_analysis_v1",
            prompt_version="article_analysis_v1", schema_name="article_analysis_v1", schema_version="article_analysis_v1",
            provider="legacy", model="legacy", input_object_type="article_revision", input_object_id=str(article_id),
            input_version_id=str(revision_id), input_hash="old-input", request_json={}, raw_output={}, raw_output_text="{}",
            validation_state="valid", validation_errors={}, retry_count=0, token_usage={}, started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        ))
        session.add(ArticleStructure(
            article_structure_id=structure_id, article_id=article_id, article_revision_id=revision_id,
            prompt_run_id=source_run_id, schema_version="article_analysis_v1", payload={}, evidence_json={},
            missing_fields={}, inference_fields={}, lifecycle_state="draft", quality_status="partial",
            created_by="legacy", updated_by="legacy",
        ))
        for index, candidate_id in enumerate(candidate_ids):
            session.add(RuleCandidate(
                rule_candidate_id=candidate_id, article_structure_id=structure_id, source_article_id=article_id,
                candidate_index=index, candidate_fingerprint=f"{index:064d}", rule_type="entry",
                canonical_payload={"legacy": index}, evidence_json={"quote": "legacy"}, explicit_fields={},
                inferred_fields={}, missing_fields={}, data_dependencies={}, backtestability_status="partially_executable",
                review_state="extracted", quality_status="partial", created_by="legacy", updated_by="legacy",
            ))
        await session.commit()

    labels = [
        {"old_rule_candidate_id": candidate_id, "draft": draft_for(primary_type), "rationale": f"fixture {primary_type}"}
        for candidate_id, primary_type in zip(candidate_ids, (
            "executable_rule", "rule_candidate", "research_hypothesis", "semantic_experience",
            "risk_control_hint", "data_requirement_hint", "unusable_noise",
        ), strict=True)
    ]
    service = ExtractionReclassificationService()
    async with factory() as session:
        before = {row.rule_candidate_id: snapshot(row) for row in (await session.execute(select(RuleCandidate))).scalars()}
        run = await service.run_bounded_subset(session, labels=labels, classifier="deterministic-fixture-v1", created_by="test")
        await session.commit()
        first_run_id = run.reclassification_run_id
    async with factory() as session:
        repeat = await service.run_bounded_subset(session, labels=labels, classifier="deterministic-fixture-v1", created_by="test")
        after = {row.rule_candidate_id: snapshot(row) for row in (await session.execute(select(RuleCandidate))).scalars()}
        items = (await session.execute(select(ExtractionItem))).scalars().all()
        run_items = (await session.execute(select(ExtractionReclassificationItem))).scalars().all()
    assert repeat.reclassification_run_id == first_run_id
    assert before == after
    assert len(run_items) == len(items) == 7
    assert {str(item.primary_type) for item in items} == {
        "executable_rule", "rule_candidate", "research_hypothesis", "semantic_experience",
        "risk_control_hint", "data_requirement_hint", "unusable_noise",
    }
    assert all(item.provenance["origin"] == "old_candidate_reclassification" for item in items)
    assert all(len(item.provenance["lineage"]) == 1 for item in items)
    await engine.dispose()
