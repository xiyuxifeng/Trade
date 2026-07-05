from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import event, inspect, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from src.domain.enums import FormalLifecycleState, QualityStatus
from src.models.blog_article import BlogArticle
from src.models.stage2_canonical import (
    ArticleRevision,
    ArticleStructure,
    CandidateReviewState,
    PromptRun,
    PromptValidationState,
    RuleCandidate,
)
from src.services.article_analysis_selection_service import ArticleAnalysisSelectionService


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


@pytest_asyncio.fixture
async def session_factory(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'article-analysis.db'}")

    @event.listens_for(engine.sync_engine, "connect")
    def _register_char_length(dbapi_connection, _connection_record):  # noqa: ANN001
        dbapi_connection.create_function("char_length", 1, lambda value: len(value) if value is not None else 0)

    async with engine.begin() as conn:
        await conn.run_sync(BlogArticle.__table__.create)
        await conn.run_sync(ArticleRevision.__table__.create)
        await conn.run_sync(PromptRun.__table__.create)
        await conn.run_sync(ArticleStructure.__table__.create)
        await conn.run_sync(RuleCandidate.__table__.create)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_load_effective_analysis_map_projects_stage3_outputs(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    article_id = uuid4()
    revision_id = uuid4()
    prompt_run_id = uuid4()
    structure_id = uuid4()
    now = datetime(2026, 7, 5, 10, 0, tzinfo=UTC)

    async with session_factory() as session:
        session.add(
            BlogArticle(
                id=article_id,
                source="tgb",
                source_url="https://example.com/a",
                title="A",
                author_id="author-1",
                author_name="Author",
                published_at=now,
                crawled_at=now,
                content_text="content",
                raw_payload={"trader_id": "trader-1"},
            )
        )
        session.add(
            ArticleRevision(
                article_revision_id=revision_id,
                article_id=article_id,
                revision_no=1,
                content_hash="hash-1",
                content_text="content",
                source_payload={},
                captured_at=now,
                quality_status=QualityStatus.complete,
            )
        )
        session.add(
            PromptRun(
                prompt_run_id=prompt_run_id,
                article_id=article_id,
                prompt_name="article_analysis_v1",
                prompt_version="article_analysis_v1",
                schema_name="article_analysis_v1",
                schema_version="article_analysis_v1",
                provider="qwen",
                model="qwen3",
                input_object_type="ArticleRevision",
                input_object_id=str(article_id),
                input_version_id=str(revision_id),
                input_hash="hash",
                request_json={},
                raw_output={
                    "classification": {"article_type": "rule", "confidence": 0.91},
                    "concept_extraction": {
                        "concepts": [{"name": "AI", "normalized_name": "AI", "type": "theme", "confidence": 0.8}],
                        "trading_symbols": [{"raw_name": "平安银行", "symbol": "000001.SZ", "asset_type": "stock", "confidence": 0.9}],
                        "sentiment": {"score": 0.6, "confidence": 0.7},
                    },
                    "explicit_preconditions": {
                        "status": "explicit",
                        "preconditions": [
                            {
                                "condition_type": "market",
                                "condition": {"field": "market_state", "operator": "=", "value": "trend_up", "raw_expression": "市场走强"},
                                "confidence": 0.75,
                                "evidence": ["市场走强"],
                            }
                        ],
                    },
                },
                validation_state=PromptValidationState.valid,
                validation_errors={},
                retry_count=0,
                token_usage={},
                completed_at=now,
            )
        )
        session.add(
            ArticleStructure(
                article_structure_id=structure_id,
                article_id=article_id,
                article_revision_id=revision_id,
                prompt_run_id=prompt_run_id,
                schema_version="article_analysis_v1",
                payload={"article_type": "rule", "instrument_focus": ["stock"]},
                evidence_json={},
                missing_fields={},
                inference_fields={},
                lifecycle_state=FormalLifecycleState.draft,
                quality_status=QualityStatus.partial,
            )
        )
        session.add(
            RuleCandidate(
                article_structure_id=structure_id,
                source_article_id=article_id,
                candidate_index=0,
                candidate_fingerprint="fingerprint",
                rule_type="entry",
                canonical_payload={
                    "rule_key": "entry_breakout",
                    "rule_type": "entry",
                    "instrument_focus": ["stock"],
                    "condition": {"logic": "all", "clauses": [{"field": "price", "operator": "breaks_above", "value": "high", "raw_expression": "突破新高"}]},
                    "action": {"type": "enter", "side": "buy", "price_reference": "close"},
                    "confidence": 0.82,
                    "timeframe": "swing",
                    "evidence": [{"quote": "突破新高", "supports": "condition"}],
                },
                evidence_json={},
                explicit_fields={},
                inferred_fields={},
                missing_fields={},
                data_dependencies={},
                backtestability_status="partially_executable",
                review_state=CandidateReviewState.extracted,
                quality_status=QualityStatus.partial,
            )
        )
        await session.commit()

    service = ArticleAnalysisSelectionService()
    async with session_factory() as session:
        result = await service.load_effective_analysis_map(session, article_ids=[article_id])

    analysis = result[article_id]
    assert analysis.processed_at is not None
    assert analysis.processed_at.replace(tzinfo=UTC) == now
    assert analysis.trading_symbols == ["000001.SZ"]
    assert analysis.extracted_concepts[0]["name"] == "AI"
    assert analysis.sentiment_score == 0.6
    assert analysis.confidence_score == 0.91
    assert analysis.strategy_rules[0]["claim_key"] == "entry.trigger"
    assert analysis.strategy_rules[0]["source_rule_key"] == "entry_breakout"
    assert analysis.strategy_rules[0]["instrument_focus"] == "stock"
    assert analysis.preconditions[0]["condition"]["field"] == "market_state"

    async with session_factory() as session:
        table_names = await session.run_sync(lambda sync_session: set(inspect(sync_session.get_bind()).get_table_names()))
        assert "article_metadata" not in table_names
