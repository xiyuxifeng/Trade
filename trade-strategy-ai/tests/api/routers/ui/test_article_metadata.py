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

from api.dependencies import verify_api_key
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
