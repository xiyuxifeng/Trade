from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.enums import FormalLifecycleState, QualityStatus
from src.llm.runtime import LLMInvocationTrace
from src.models.blog_article import BlogArticle
from src.models.stage2_canonical import (
    ArticleRevision,
    ArticleStructure,
    Authors,
    AuthorProfileVersion,
    AuthorProfileVersionAudit,
    PromptRun,
    PromptValidationState,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


class _FakeGateway:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    async def invoke_json(self, *, prompt_name: str, system_prompt: str, user_prompt: str, model: str) -> LLMInvocationTrace:
        self.calls.append(
            {
                "prompt_name": prompt_name,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "model": model,
            }
        )
        return LLMInvocationTrace(
            provider="test-provider",
            model=model,
            data=self.payload,
            raw_output=self.payload,
            raw_output_text="{}",
            token_usage={"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33},
            cost_amount=0.12,
            cost_currency="USD",
        )


async def _build_session_factory(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'author_method_profiles.db'}")

    @event.listens_for(engine.sync_engine, "connect")
    def _register_char_length(dbapi_connection, _connection_record):  # noqa: ANN001
        dbapi_connection.create_function("char_length", 1, lambda value: len(value) if value is not None else 0)

    async with engine.begin() as conn:
        await conn.run_sync(BlogArticle.__table__.create)
        await conn.run_sync(Authors.__table__.create)
        await conn.run_sync(ArticleRevision.__table__.create)
        await conn.run_sync(PromptRun.__table__.create)
        await conn.run_sync(ArticleStructure.__table__.create)
        await conn.run_sync(AuthorProfileVersion.__table__.create)
        await conn.run_sync(AuthorProfileVersionAudit.__table__.create)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def _session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return _session_scope, session_factory, engine


async def _seed_structured_articles(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    author_id: UUID,
    author_source_key: str = "author-001",
    article_count: int = 10,
    aligned: bool = True,
) -> list[UUID]:
    structure_ids: list[UUID] = []
    async with session_factory() as session:
        session.add(
            Authors(
                author_id=author_id,
                source="tgb",
                source_author_key=author_source_key,
                display_name="测试作者",
            )
        )
        for index in range(article_count):
            article_id = uuid4()
            revision_id = uuid4()
            prompt_run_id = uuid4()
            structure_id = uuid4()
            structure_ids.append(structure_id)
            published_at = datetime(2026, 1, 1 + index, 9, 30, tzinfo=UTC)
            session.add(
                BlogArticle(
                    id=article_id,
                    source="tgb",
                    source_article_id=f"source-{index}",
                    source_url=f"https://example.com/articles/{index}",
                    title=f"文章 {index}",
                    author_name="测试作者",
                    author_id=author_source_key if aligned else "other-author",
                    published_at=published_at,
                    crawled_at=published_at,
                    content_text=f"正文 {index}",
                    summary=f"摘要 {index}",
                    tags=["趋势", "复盘"],
                    content_hash=f"hash-{index}",
                    view_count=0,
                    like_count=0,
                    bookmark_count=0,
                    comment_count=0,
                    comments_payload=[],
                    raw_payload={},
                )
            )
            session.add(
                ArticleRevision(
                    article_revision_id=revision_id,
                    article_id=article_id,
                    revision_no=1,
                    content_hash=f"hash-{index}",
                    content_text=f"正文 {index}",
                    content_html=None,
                    source_payload={},
                    captured_at=published_at,
                    quality_status=QualityStatus.complete,
                )
            )
            session.add(
                PromptRun(
                    prompt_run_id=prompt_run_id,
                    run_id=f"stage3-run-{index}",
                    article_id=article_id,
                    prompt_name="article_analysis_v1",
                    prompt_version="article_analysis_v1",
                    schema_name="article_analysis_v1",
                    schema_version="article_analysis_v1",
                    provider="test-provider",
                    model="gpt-5.4",
                    input_object_type="article_revision",
                    input_object_id=str(article_id),
                    input_version_id=str(revision_id) if aligned else str(uuid4()),
                    input_hash=f"input-hash-{index}",
                    request_json={"article_id": str(article_id)},
                    raw_output={"article_structure": {"method_tags": ["趋势突破"]}},
                    raw_output_text="{}",
                    validation_state=PromptValidationState.valid,
                    validation_errors={},
                    retry_count=0,
                    token_usage={"total_tokens": 10},
                    cost_amount=0.01,
                    cost_currency="USD",
                    started_at=published_at,
                    completed_at=published_at,
                )
            )
            session.add(
                ArticleStructure(
                    article_structure_id=structure_id,
                    article_id=article_id,
                    article_revision_id=revision_id,
                    prompt_run_id=prompt_run_id,
                    schema_version="article_structure_v1",
                    payload={
                        "article_id": str(article_id),
                        "author_id": author_source_key if aligned else "other-author",
                        "published_at": published_at.isoformat(),
                        "method_tags": ["趋势突破", "仓位管理"],
                        "analysis_dimensions": ["量价", "题材"],
                        "instrument_focus": ["强势股"],
                        "holding_period": {
                            "value": "2-5天",
                            "source": "explicit",
                            "confidence": 0.8,
                            "evidence": [f"持股周期 {index}"],
                        },
                        "entry_patterns": ["放量突破"],
                        "exit_patterns": ["跌破均线减仓"],
                        "risk_concepts": ["控制回撤"],
                        "data_dependencies": ["ohlcv_1d", "volume"],
                        "market_state": {
                            "status": "not_declared",
                            "explicit_conditions": [],
                            "inferred_hypotheses": [
                                {
                                    "market_state": "情绪回暖",
                                    "source": "inferred_hypothesis",
                                    "confidence": 0.65,
                                    "evidence": [f"情绪判断 {index}"],
                                    "validation_status": "unverified",
                                }
                            ],
                        },
                        "key_claims": [
                            {
                                "claim": "优先做强势股突破",
                                "claim_type": "method",
                                "source": "explicit",
                                "confidence": 0.9,
                                "evidence": [f"原文证据 {index}"],
                            }
                        ],
                        "article_quality": {
                            "information_density": "high",
                            "quantifiability": "medium",
                            "duplicate_risk": "low",
                            "needs_manual_review": False,
                            "warnings": [],
                        },
                    },
                    evidence_json={"key_claims": [f"原文证据 {index}"]},
                    missing_fields={},
                    inference_fields={},
                    lifecycle_state=FormalLifecycleState.approved,
                    quality_status=QualityStatus.complete,
                    approved_by="reviewer",
                    approved_at=published_at,
                    supersedes_id=None,
                    created_by="stage3",
                    updated_by="stage3",
                )
            )
        await session.commit()
    return structure_ids


def _llm_output() -> dict[str, Any]:
    return {
        "prompt_version": "author_method_profile_batch_v1",
        "author_id": "placeholder",
        "batch_id": "batch-1",
        "date_range": {"start": "2026-01-01", "end": "2026-01-10"},
        "article_count": 10,
        "dominant_methods": [
            {
                "name": "趋势突破",
                "weight": 0.8,
                "confidence": 0.84,
                "article_ids": ["article-a", "article-b"],
                "evidence": ["证据 A", "证据 B"],
            }
        ],
        "analysis_framework": [{"name": "量价共振", "confidence": 0.77, "article_ids": ["article-a"], "evidence": ["量价观察"]}],
        "instrument_preferences": [{"name": "强势股", "confidence": 0.8, "article_ids": ["article-a"], "evidence": ["强势股"]}],
        "entry_preferences": [{"name": "放量突破", "confidence": 0.8, "article_ids": ["article-a"], "evidence": ["放量突破"]}],
        "exit_preferences": [{"name": "跌破均线减仓", "confidence": 0.7, "article_ids": ["article-b"], "evidence": ["跌破均线"]}],
        "risk_expressions": [{"name": "控制回撤", "confidence": 0.82, "article_ids": ["article-b"], "evidence": ["控制回撤"]}],
        "holding_period_preferences": [{"name": "2-5天", "confidence": 0.75, "article_ids": ["article-a"], "evidence": ["2-5天"]}],
        "data_dependency_preferences": [{"name": "ohlcv_1d", "confidence": 0.8, "article_ids": ["article-a"], "evidence": ["日线"]}],
        "market_state_hypotheses": [
            {
                "market_state": "情绪回暖",
                "source": "inferred_hypothesis",
                "confidence": 0.66,
                "article_ids": ["article-a"],
                "evidence": ["情绪回暖"],
                "validation_status": "unverified",
            }
        ],
        "stable_traits": [{"name": "重视趋势", "confidence": 0.79, "article_ids": ["article-a"], "evidence": ["重视趋势"]}],
        "stage_specific_traits": [],
        "conflicts": [],
        "representative_articles": [{"article_id": "article-a", "reason": "表达完整"}],
        "quality": {
            "coverage": "high",
            "consistency": "medium",
            "confidence": 0.78,
            "warnings": [],
        },
    }


@pytest.mark.asyncio()
async def test_generate_method_profile_draft_from_structured_articles_binds_prompt_and_evidence(tmp_path: Path) -> None:
    from src.services.author_method_profile_service import (
        AuthorMethodProfileGenerationRequest,
        AuthorMethodProfileService,
    )

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    author_id = uuid4()
    structure_ids = await _seed_structured_articles(session_factory, author_id=author_id, article_count=10, aligned=True)
    gateway = _FakeGateway(_llm_output())
    service = AuthorMethodProfileService(
        session_scope_factory=session_scope,
        gateway=gateway,
        model="gpt-5.4",
    )

    version = await service.generate_draft(
        AuthorMethodProfileGenerationRequest(
            author_id=author_id,
            article_structure_ids=structure_ids,
            evidence_from=date(2026, 1, 1),
            evidence_to=date(2026, 1, 10),
            effective_from=date(2026, 1, 11),
            effective_to=date(2026, 3, 31),
            reason="根据结构化文章生成作者方法画像草稿",
        ),
        actor_id="operator-a",
        actor_role="operator",
    )

    assert len(gateway.calls) == 1
    assert version.profile_kind == "method"
    assert version.prompt_version == "author_method_profile_batch_v1"
    assert version.status_state == "draft"
    assert version.source_bindings["rule_version_ids"] == {}
    assert version.source_bindings["backtest_run_ids"] == {}
    assert version.source_bindings["article_revision_ids"]["article_structure_ids"] == [str(item) for item in structure_ids]
    assert version.source_versions["method_profile_prompt_schema_version"] == "author_method_profile_batch_v1"
    assert version.source_versions["prompt_run_id"]
    assert version.payload["method_profile"]["trading_style"][0]["name"] == "趋势突破"
    assert version.payload["limitations"][0].startswith("画像来自结构化文章表达")
    assert version.payload["conclusions"]
    assert version.payload["conclusions"][0]["version_binding"]["prompt_version"] == "author_method_profile_batch_v1"
    assert version.payload["conclusions"][0]["provenance"]["lane"] == "article_expression"
    assert version.payload["conclusions"][0]["evidence"][0]["article_structure_id"]
    await engine.dispose()


@pytest.mark.asyncio()
async def test_generate_method_profile_draft_marks_unaligned_evidence_as_partial_without_llm_call(tmp_path: Path) -> None:
    from src.services.author_method_profile_service import (
        AuthorMethodProfileGenerationRequest,
        AuthorMethodProfileService,
    )

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    author_id = uuid4()
    structure_ids = await _seed_structured_articles(session_factory, author_id=author_id, article_count=3, aligned=False)
    gateway = _FakeGateway(_llm_output())
    service = AuthorMethodProfileService(
        session_scope_factory=session_scope,
        gateway=gateway,
        model="gpt-5.4",
    )

    version = await service.generate_draft(
        AuthorMethodProfileGenerationRequest(
            author_id=author_id,
            article_structure_ids=structure_ids,
            evidence_from=date(2026, 1, 1),
            evidence_to=date(2026, 1, 3),
            effective_from=date(2026, 1, 4),
            reason="来源版本不对齐时只能生成部分草稿",
        ),
        actor_id="operator-a",
        actor_role="operator",
    )

    assert gateway.calls == []
    assert version.profile_kind == "method"
    assert version.status_state == "partial"
    assert version.quality_status == "unresolved"
    assert any("证据来源未对齐" in reason for reason in version.partial_reasons)
    assert version.payload["quality"]["status"] == "insufficient_evidence"
    assert version.payload["conclusions"] == []
    await engine.dispose()
