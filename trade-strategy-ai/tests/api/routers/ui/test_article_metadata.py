"""Article metadata selection UI BFF 路由测试。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import AsyncIterator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui import article_metadata as article_metadata_routes
from src.models.article_metadata import ArticleMetadata
from src.models.article_metadata_selection import ArticleMetadataSelection
from src.models.blog_article import BlogArticle

SEEDED_ARTICLE_ID: str | None = None
TEST_SESSION_FACTORY: async_sessionmaker[AsyncSession] | None = None


@pytest_asyncio.fixture
async def client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'article-metadata.db'}")

    @event.listens_for(engine.sync_engine, 'connect')
    def _register_char_length(dbapi_connection, _connection_record):  # noqa: ANN001
        dbapi_connection.create_function('char_length', 1, lambda value: len(value) if value is not None else 0)

    async with engine.begin() as conn:
        await conn.run_sync(BlogArticle.__table__.create)
        await conn.run_sync(ArticleMetadata.__table__.create)
        await conn.run_sync(ArticleMetadataSelection.__table__.create)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    global SEEDED_ARTICLE_ID
    global TEST_SESSION_FACTORY
    article_id = uuid4()
    SEEDED_ARTICLE_ID = str(article_id)
    TEST_SESSION_FACTORY = session_factory
    async with session_factory() as session:
        session.add(
            BlogArticle(
                id=article_id,
                source='tgb',
                source_url='https://example.com/article-1',
                title='Article One',
                author_id='author-1',
                author_name='Alice',
                published_at=datetime(2026, 5, 10, tzinfo=UTC),
                crawled_at=datetime(2026, 5, 10, 9, 0, tzinfo=UTC),
                content_text='hello',
                raw_payload={'trader_id': 'trader-a'},
            )
        )
        session.add(
            ArticleMetadata(
                article_id=article_id,
                version='v1',
                processed_at=datetime(2026, 5, 10, 10, 0, tzinfo=UTC),
                extracted_concepts=[{'name': 'macd'}],
                trading_symbols=['000001.SZ'],
                strategy_rules=[{'rule_id': 'rule-1'}],
                preconditions=[{'rule_id': 'pre-1'}],
                comment_insights=[{'insight': 'bullish'}],
                raw_llm_output={'a': 1, 'b': 2},
                sentiment_score=0.8,
                confidence_score=0.9,
                provider='openai',
                model='gpt-5',
                article_type='rule',
                extraction_version='v1',
            )
        )
        session.add(
            ArticleMetadata(
                article_id=article_id,
                version='v2',
                processed_at=datetime(2026, 5, 10, 10, 20, tzinfo=UTC),
                extracted_concepts=[{'name': 'macd'}, {'name': 'trend'}],
                trading_symbols=['000001.SZ', '000002.SZ'],
                strategy_rules=[{'rule_id': 'rule-2'}],
                preconditions=[],
                comment_insights=[],
                raw_llm_output={'a': 1},
                sentiment_score=0.6,
                confidence_score=0.7,
                provider='claude',
                model='sonnet',
                article_type='rule',
                extraction_version='v2',
            )
        )
        await session.commit()

    app.dependency_overrides.clear()
    app.dependency_overrides[verify_api_key] = lambda: 'test-key'
    original_session_factory = article_metadata_routes.async_session_factory
    article_metadata_routes.async_session_factory = lambda: session_factory
    app.state.article_metadata_test_session_factory = session_factory
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url='http://test') as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        article_metadata_routes.async_session_factory = original_session_factory
        if hasattr(app.state, 'article_metadata_test_session_factory'):
            delattr(app.state, 'article_metadata_test_session_factory')
        TEST_SESSION_FACTORY = None
        await engine.dispose()


@pytest.mark.asyncio
async def test_list_article_metadata_summary_returns_resolution_preview(client: AsyncClient) -> None:
    assert SEEDED_ARTICLE_ID is not None
    response = await client.get('/api/ui/v1/article-metadata/summary', params=[('article_ids', SEEDED_ARTICLE_ID)])
    assert response.status_code == 200
    payload = response.json()
    assert payload['items'][0]['recommended_schema_version'] == 'v2'
    assert payload['items'][0]['selected_schema_version'] == 'v2'

    assert TEST_SESSION_FACTORY is not None
    session_factory = TEST_SESSION_FACTORY
    async with session_factory() as session:
        selection_row = await session.scalar(
            select(ArticleMetadataSelection).where(ArticleMetadataSelection.article_id == UUID(SEEDED_ARTICLE_ID))
        )
        assert selection_row is not None
        assert selection_row.selected_schema_version == 'v2'


@pytest.mark.asyncio
async def test_get_and_select_article_metadata_version(client: AsyncClient) -> None:
    assert SEEDED_ARTICLE_ID is not None
    response = await client.get(f'/api/ui/v1/article-metadata/articles/{SEEDED_ARTICLE_ID}')
    assert response.status_code == 200
    payload = response.json()
    assert payload['effective_schema_version'] == 'v2'
    assert payload['candidates'][0]['schema_version'] == 'v2'

    select_response = await client.post(
        f'/api/ui/v1/article-metadata/articles/{SEEDED_ARTICLE_ID}/select',
        json={
            'selected_schema_version': 'v1',
            'selected_by': 'web',
            'selection_reason': 'manual selection',
        },
    )
    assert select_response.status_code == 200
    selected_payload = select_response.json()
    assert selected_payload['selected_schema_version'] == 'v1'
    assert selected_payload['effective_schema_version'] == 'v1'

    summary_after_select = await client.get('/api/ui/v1/article-metadata/summary', params=[('article_ids', SEEDED_ARTICLE_ID)])
    assert summary_after_select.status_code == 200
    assert summary_after_select.json()['items'][0]['selected_schema_version'] == 'v1'


@pytest.mark.asyncio
async def test_get_article_analysis_returns_truthful_partial_state(client: AsyncClient) -> None:
    assert SEEDED_ARTICLE_ID is not None

    class _FakeJourney:
        status = "partial"
        message = "该文章尚未完成结构化分析。"
        article = type(
            "Article",
            (),
            {
                "id": UUID(SEEDED_ARTICLE_ID),
                "title": "Article One",
                "source": "tgb",
                "source_url": "https://example.com/article-1",
                "author_name": "Alice",
                "author_id": "author-1",
                "published_at": datetime(2026, 5, 10, tzinfo=UTC),
                "crawled_at": datetime(2026, 5, 10, 9, 0, tzinfo=UTC),
                "content_text": "原始正文",
                "summary": "摘要",
                "tags": ["突破"],
            },
        )()
        revision = type("Revision", (), {"article_revision_id": uuid4(), "content_text": "清洗后正文", "content_hash": "hash-1"})()
        prompt_run = None
        structure = None
        candidates = []
        automatic_reviews = {}
        rule_versions = {}
        summary_provenance = type(
            "SummaryProvenance",
            (),
            {
                "summary": "摘要",
                "source": "blog_article_current",
                "article_revision_id": str(revision.article_revision_id),
                "content_hash": "hash-1",
                "available": True,
                "aligned": True,
                "reason": None,
            },
        )()
        article_structure_provenance = type(
            "StructureProvenance",
            (),
            {
                "article_structure_id": None,
                "article_revision_id": None,
                "prompt_run_id": None,
                "prompt_name": None,
                "prompt_version": None,
                "schema_name": None,
                "schema_version": None,
                "available": False,
            },
        )()

    class _FakeService:
        async def get_journey(self, *, article_id, article_revision_id=None):
            assert str(article_id) == SEEDED_ARTICLE_ID
            assert article_revision_id is None
            return _FakeJourney()

    app.dependency_overrides[article_metadata_routes.get_stage3_single_article_service] = lambda: _FakeService()
    try:
        response = await client.get(f"/api/ui/v1/article-metadata/articles/{SEEDED_ARTICLE_ID}/analysis")
    finally:
        app.dependency_overrides.pop(article_metadata_routes.get_stage3_single_article_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"
    assert payload["message"] == "该文章尚未完成结构化分析。"
    assert payload["article"]["original_text"] == "原始正文"
    assert payload["article"]["cleaned_content"] == "清洗后正文"
    assert payload["article"]["summary"] == "摘要"
    assert payload["article"]["content_hash"] == "hash-1"
    assert payload["summary_provenance"]["source"] == "blog_article_current"
    assert payload["summary_provenance"]["article_revision_id"] == payload["article"]["article_revision_id"]
    assert payload["candidates"] == []


@pytest.mark.asyncio
async def test_operator_can_review_article_candidate_and_viewer_cannot(client: AsyncClient) -> None:
    article_id = str(uuid4())
    candidate_id = str(uuid4())
    revision_id = str(uuid4())
    rule_version_id = str(uuid4())

    class _FakeJourney:
        status = "ready"
        message = None
        article = type(
            "Article",
            (),
            {
                "id": UUID(article_id),
                "title": "Article One",
                "source": "tgb",
                "source_url": "https://example.com/article-1",
                "author_name": "Alice",
                "author_id": "author-1",
                "published_at": datetime(2026, 5, 10, tzinfo=UTC),
                "crawled_at": datetime(2026, 5, 10, 9, 0, tzinfo=UTC),
                "content_text": "原始正文",
                "summary": "摘要",
                "tags": ["突破"],
            },
        )()
        revision = type("Revision", (), {"article_revision_id": UUID(revision_id), "content_text": "清洗后正文", "content_hash": "hash-1"})()
        prompt_run = type(
            "PromptRun",
            (),
            {
                "run_id": "run-1",
                "prompt_name": "article_analysis_v1",
                "prompt_version": "article_analysis_v1",
                "schema_name": "article_analysis_v1",
                "schema_version": "article_analysis_v1",
                "provider": "openai",
                "model": "gpt-5.4",
                "validation_state": "valid",
                "retry_count": 0,
                "token_usage": {"total_tokens": 12},
                "cost_amount": None,
                "cost_currency": None,
                "started_at": None,
                "completed_at": None,
            },
        )()
        structure = type(
            "Structure",
            (),
            {
                "payload": {"method_tags": ["突破"], "key_claims": [{"claim": "放量突破介入", "source": "explicit", "evidence": ["放量突破介入"]}]},
                "inference_fields": {},
                "missing_fields": {},
                "article_structure_id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                "article_revision_id": UUID(revision_id),
                "prompt_run_id": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            },
        )()
        candidate = type(
            "Candidate",
            (),
            {
                "rule_candidate_id": UUID(candidate_id),
                "candidate_index": 0,
                "rule_type": "entry",
                "canonical_payload": {"title": "放量突破介入", "market_state_applicability": {"status": "not_declared"}},
                "explicit_fields": {"holding_period": "intraday"},
                "inferred_fields": {"note": "可能需要配合量比"},
                "missing_fields": {"stop_loss": "unknown"},
                "evidence_json": {"items": [{"quote": "放量突破介入"}]},
                "data_dependencies": {"required": ["ohlcv_1d"]},
                "backtestability_status": "executable",
                "review_state": "approved",
            },
        )()
        candidates = [candidate]
        automatic_reviews = {UUID(candidate_id): type("Review", (), {"status": "pending_backtest", "reasons": ["证据完整"], "risk_level": "low"})()}
        rule_versions = {
            UUID(candidate_id): type("RuleVersion", (), {"rule_version_id": UUID(rule_version_id), "lifecycle_state": "draft"})()
        }
        summary_provenance = type(
            "SummaryProvenance",
            (),
            {
                "summary": "摘要",
                "source": "article_revision_source_payload",
                "article_revision_id": revision_id,
                "content_hash": "hash-1",
                "available": True,
                "aligned": True,
                "reason": None,
            },
        )()
        article_structure_provenance = type(
            "StructureProvenance",
            (),
            {
                "article_structure_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "article_revision_id": revision_id,
                "prompt_run_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "prompt_name": "article_analysis_v1",
                "prompt_version": "article_analysis_v1",
                "schema_name": "article_analysis_v1",
                "schema_version": "article_analysis_v1",
                "available": True,
            },
        )()

    class _FakeService:
        def __init__(self) -> None:
            self.calls = []

        async def review_candidate(self, **kwargs):
            self.calls.append(kwargs)
            return _FakeJourney()

    fake_service = _FakeService()
    app.dependency_overrides[article_metadata_routes.get_stage3_single_article_service] = lambda: fake_service
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="operator",
        api_key_label="operator-user",
        authenticated=True,
        source="api_key",
        api_key="operator-key",
    )
    try:
        response = await client.post(
            f"/api/ui/v1/article-metadata/articles/{article_id}/candidates/{candidate_id}/review",
            json={"decision": "approve", "reason": "证据充分。", "article_revision_id": revision_id},
        )
    finally:
        app.dependency_overrides.pop(article_metadata_routes.get_stage3_single_article_service, None)
        app.dependency_overrides.pop(get_current_principal, None)

    assert response.status_code == 200
    assert fake_service.calls[0]["actor_id"] == "operator-user"
    assert response.json()["candidates"][0]["human_review"]["formal_rule_created"] is True
    assert response.json()["candidates"][0]["human_review"]["formal_lifecycle_state"] == "draft"
    assert response.json()["candidates"][0]["human_review"]["stage3_status"] == "pending_backtest"
    assert response.json()["summary_provenance"]["article_revision_id"] == revision_id
    assert response.json()["article_structure_provenance"]["article_revision_id"] == revision_id
    assert response.json()["method_tags"] == ["突破"]

    app.dependency_overrides[article_metadata_routes.get_stage3_single_article_service] = lambda: fake_service
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="viewer",
        api_key_label="viewer-user",
        authenticated=True,
        source="api_key",
        api_key="viewer-key",
    )
    try:
        forbidden = await client.post(
            f"/api/ui/v1/article-metadata/articles/{article_id}/candidates/{candidate_id}/review",
            json={"decision": "approve", "reason": "证据充分。", "article_revision_id": revision_id},
        )
    finally:
        app.dependency_overrides.pop(article_metadata_routes.get_stage3_single_article_service, None)
        app.dependency_overrides.pop(get_current_principal, None)

    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "insufficient permissions"
