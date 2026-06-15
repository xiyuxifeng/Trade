from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.base import Base
from src.models.blog_article import BlogArticle
from src.models.stage2_canonical import ArticleRevision, ArticleStructure, PromptRun, RuleCandidate
from src.services.stage3_prompt_runtime_service import ArticlePromptInput, Stage3PromptRuntimeService
from src.llm.runtime import LLMInvocationTrace


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


class _FakeGateway:
    async def invoke_json(self, *, prompt_name: str, system_prompt: str, user_prompt: str, model: str) -> LLMInvocationTrace:
        del system_prompt, user_prompt, model
        if prompt_name != "article_analysis_v1":
            raise AssertionError(prompt_name)
        payload = {
            "prompt_version": "article_analysis_v1",
            "schema_version": "article_analysis_v1",
            "classification": {"article_type": "rule", "confidence": 0.9, "evidence": ["原文证据"]},
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
                "holding_period": {"value": "intraday", "source": "explicit", "confidence": 0.8, "evidence": ["当日"]},
                "entry_patterns": ["放量突破"],
                "exit_patterns": [],
                "risk_concepts": [],
                "data_dependencies": ["ohlcv_1d"],
                "market_state": {"status": "not_declared", "explicit_conditions": [], "inferred_hypotheses": []},
                "key_claims": [{"claim": "放量突破介入", "claim_type": "entry", "source": "explicit", "confidence": 0.8, "evidence": ["放量突破介入"]}],
                "article_quality": {"information_density": "medium", "quantifiability": "medium", "duplicate_risk": "low", "needs_manual_review": False, "warnings": []},
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
                    "condition": {"logic": "single", "clauses": [{"field": "volume", "operator": "gt", "value": 1, "unit": None, "lookback": None, "raw_expression": "放量"}]},
                    "action": {"type": "enter", "side": "buy", "price_reference": "market"},
                    "risk_controls": [],
                    "data_dependencies": ["ohlcv_1d"],
                    "market_state_applicability": {"status": "not_declared", "explicit_conditions": [], "inferred_hypotheses": []},
                    "quantification": {"status": "partially_executable", "missing_fields": ["threshold"], "ambiguous_terms": ["放量"], "manual_review_required": True},
                    "confidence": 0.8,
                    "evidence": [{"quote": "放量突破", "supports": "condition"}],
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
            token_usage={"prompt_tokens": 20, "completion_tokens": 30, "total_tokens": 50},
            cost_amount=None,
            cost_currency=None,
        )


@pytest.mark.asyncio
async def test_stage3_runtime_persists_prompt_run_structure_and_candidates(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stage3-runtime.db'}")

    @event.listens_for(engine.sync_engine, "connect")
    def _register_char_length(dbapi_connection, _connection_record):  # noqa: ANN001
        dbapi_connection.create_function("char_length", 1, lambda value: len(value) if value is not None else 0)

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: BlogArticle.__table__.create(bind=sync_conn, checkfirst=True))
        await conn.run_sync(lambda sync_conn: ArticleRevision.__table__.create(bind=sync_conn, checkfirst=True))
        await conn.run_sync(lambda sync_conn: PromptRun.__table__.create(bind=sync_conn, checkfirst=True))
        await conn.run_sync(lambda sync_conn: ArticleStructure.__table__.create(bind=sync_conn, checkfirst=True))
        await conn.run_sync(lambda sync_conn: RuleCandidate.__table__.create(bind=sync_conn, checkfirst=True))

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
                content_text="放量突破介入",
                summary="summary",
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
                content_text="放量突破介入",
                content_html=None,
                source_payload={},
                captured_at=datetime(2026, 6, 15, 9, 40, tzinfo=UTC),
                quality_status="complete",
            )
        )
        await session.commit()

    from src.db.repositories.stage3_prompt_runtime_repository import (
        Stage3ArticleAnalysisRepository,
        Stage3PromptRunRepository,
    )

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
        session_scope_factory=_session_scope,
        gateway=_FakeGateway(),
        prompt_run_repository=Stage3PromptRunRepository(),
        article_analysis_repository=Stage3ArticleAnalysisRepository(),
        model="test-model",
    )

    await service.analyze_article(
        ArticlePromptInput(
            article_id=article_id,
            article_revision_id=revision_id,
            article_title="示例文章",
            article_content="放量突破介入",
            source_url="https://example.com/article",
            published_at=datetime(2026, 6, 15, 9, 30, tzinfo=UTC),
        )
    )

    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(PromptRun)) == 1
        prompt_runs = (await session.execute(select(PromptRun))).scalars().all()
        structures = (await session.execute(select(ArticleStructure))).scalars().all()
        candidates = (await session.execute(select(RuleCandidate))).scalars().all()

    assert len(prompt_runs) == 1
    assert len(structures) == 1
    assert len(candidates) == 1
    assert prompt_runs[0].prompt_name == "article_analysis_v1"
    assert prompt_runs[0].prompt_version == "article_analysis_v1"
    assert prompt_runs[0].schema_name == "article_analysis_v1"
    assert prompt_runs[0].schema_version == "article_analysis_v1"
    assert prompt_runs[0].provider == "test-provider"
    assert prompt_runs[0].model == "test-model"
    assert prompt_runs[0].input_object_type == "article_revision"
    assert prompt_runs[0].input_version_id == str(revision_id)
    assert prompt_runs[0].input_hash
    assert prompt_runs[0].request_json["article_revision_id"] == str(revision_id)
    assert prompt_runs[0].raw_output_text
    assert prompt_runs[0].validation_state in {"valid", "repaired"}
    assert prompt_runs[0].retry_count == 0
    assert prompt_runs[0].token_usage["total_tokens"] == 50
    assert structures[0].article_revision_id == revision_id
    assert candidates[0].backtestability_status == "partially_executable"

    await engine.dispose()
