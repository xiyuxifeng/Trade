"""Article API 路由测试。"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.dependencies import verify_api_key
from api.main import app
from api.routes import articles as article_routes
from src.models.blog_article import BlogArticle


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建测试客户端。"""
    app.dependency_overrides[verify_api_key] = lambda: "test-key"
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def article_session_factory(tmp_path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """创建文章路由测试用的临时数据库。"""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'articles.db'}")

    @event.listens_for(engine.sync_engine, "connect")
    def _register_char_length(dbapi_connection, _connection_record):  # noqa: ANN001
        dbapi_connection.create_function("char_length", 1, lambda value: len(value) if value is not None else 0)

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: BlogArticle.__table__.create(bind=sync_conn, checkfirst=True))

    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


async def _seed_articles(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        session.add_all(
            [
                BlogArticle(
                    source="tgb",
                    source_url="https://example.com/article-1",
                    title="Article One",
                    author_name="Alice",
                    author_id="author-1",
                    published_at=datetime(2026, 5, 10, 8, 0, tzinfo=UTC),
                    crawled_at=datetime(2026, 5, 10, 9, 0, tzinfo=UTC),
                    content_text="hello article content",
                    summary="summary one",
                    tags=["trend", "alpha"],
                    content_hash="hash-1",
                    view_count=10,
                    like_count=2,
                    bookmark_count=1,
                    comment_count=3,
                    raw_payload={},
                ),
                BlogArticle(
                    source="xhs",
                    source_url="https://example.com/article-2",
                    title="Article Two",
                    author_name="Bob",
                    author_id="author-2",
                    published_at=datetime(2026, 5, 11, 8, 0, tzinfo=UTC),
                    crawled_at=datetime(2026, 5, 11, 9, 0, tzinfo=UTC),
                    content_text="another article content",
                    summary="summary two",
                    tags=["momentum"],
                    content_hash="hash-2",
                    view_count=6,
                    like_count=1,
                    bookmark_count=0,
                    comment_count=0,
                    raw_payload={"trader_id": "trader_b"},
                ),
            ]
        )
        await session.commit()


@pytest.mark.asyncio
async def test_article_filter_options_are_linked_and_db_driven(
    client: AsyncClient,
    article_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """筛选选项应按当前条件联动收敛。"""
    await _seed_articles(article_session_factory)

    monkeypatch.setattr(article_routes, "async_session_factory", lambda: article_session_factory)
    monkeypatch.setattr(
        article_routes,
        "load_app_config",
        lambda _: SimpleNamespace(
            config=SimpleNamespace(
                crawl=SimpleNamespace(
                    sources=[
                        SimpleNamespace(author_id="author-1", trader_id="trader_a"),
                    ]
                )
            )
        ),
    )

    response = await client.get("/articles/filter-options?source=tgb")
    assert response.status_code == 200
    assert response.json() == {
        "author_ids": ["author-1"],
        "sources": ["tgb", "xhs"],
        "trader_ids": ["trader_a"],
    }


@pytest.mark.asyncio
async def test_article_filter_options_survive_config_load_failure(
    client: AsyncClient,
    article_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """配置加载失败时，筛选选项仍应返回数据库中的作者和来源。"""
    await _seed_articles(article_session_factory)

    monkeypatch.setattr(article_routes, "async_session_factory", lambda: article_session_factory)
    monkeypatch.setattr(article_routes, "load_app_config", lambda _: (_ for _ in ()).throw(RuntimeError("missing config")))

    response = await client.get("/articles/filter-options")
    assert response.status_code == 200
    assert response.json() == {
        "author_ids": ["author-1", "author-2"],
        "sources": ["tgb", "xhs"],
        "trader_ids": ["trader_b"],
    }
