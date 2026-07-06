"""Article API 路由测试。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import AsyncIterator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.dependencies import verify_api_key
from api.main import app
from api.routes import articles as article_routes
from api.routers.ui import article_metadata as article_metadata_routes
from src.models.article_metadata import ArticleMetadata
from src.models.blog_article import BlogArticle
from src.models.article_metadata_selection import ArticleMetadataSelection
from src.models.stage2_canonical import (
    ArticleRevision,
    ArticleStructure,
    FormalLifecycleState,
    PromptRun,
    PromptValidationState,
    QualityStatus,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


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
        await conn.run_sync(lambda sync_conn: ArticleRevision.__table__.create(bind=sync_conn, checkfirst=True))
        await conn.run_sync(lambda sync_conn: PromptRun.__table__.create(bind=sync_conn, checkfirst=True))
        await conn.run_sync(lambda sync_conn: ArticleStructure.__table__.create(bind=sync_conn, checkfirst=True))
        await conn.run_sync(lambda sync_conn: ArticleMetadata.__table__.create(bind=sync_conn, checkfirst=True))
        await conn.run_sync(lambda sync_conn: ArticleMetadataSelection.__table__.create(bind=sync_conn, checkfirst=True))

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
                    id=UUID("11111111-1111-1111-1111-111111111111"),
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
                raw_payload={"trader_id": "trader_a"},
                ),
                BlogArticle(
                    id=UUID("22222222-2222-2222-2222-222222222222"),
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
                raw_payload={"trader_id": "trader_c"},
                ),
            ]
        )
        revision_id = UUID("44444444-4444-4444-4444-444444444444")
        prompt_run_id = UUID("55555555-5555-5555-5555-555555555555")
        structure_id = UUID("66666666-6666-6666-6666-666666666666")
        session.add(
            ArticleRevision(
                article_revision_id=revision_id,
                article_id=UUID("22222222-2222-2222-2222-222222222222"),
                revision_no=1,
                content_hash="hash-2-revision",
                content_text="another article content",
                source_payload={},
                captured_at=datetime(2026, 5, 11, 9, 0, tzinfo=UTC),
                quality_status=QualityStatus.complete,
            )
        )
        session.add(
            PromptRun(
                prompt_run_id=prompt_run_id,
                article_id=UUID("22222222-2222-2222-2222-222222222222"),
                prompt_name="article_analysis_v1",
                prompt_version="article_analysis_v1",
                schema_name="article_analysis_v1",
                schema_version="article_analysis_v1",
                provider="qwen",
                model="qwen-plus",
                input_object_type="ArticleRevision",
                input_object_id=str(UUID("22222222-2222-2222-2222-222222222222")),
                input_version_id=str(revision_id),
                input_hash="prompt-hash-2",
                request_json={},
                raw_output={},
                validation_state=PromptValidationState.valid,
                validation_errors={},
                retry_count=0,
                token_usage={},
                completed_at=datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
            )
        )
        session.add(
            ArticleStructure(
                article_structure_id=structure_id,
                article_id=UUID("22222222-2222-2222-2222-222222222222"),
                article_revision_id=revision_id,
                prompt_run_id=prompt_run_id,
                schema_version="article_analysis_v1",
                payload={},
                evidence_json={},
                missing_fields={},
                inference_fields={},
                lifecycle_state=FormalLifecycleState.draft,
                quality_status=QualityStatus.partial,
            )
        )
        session.add(
            ArticleMetadataSelection(
                selection_id="selection-article-1",
                article_id=UUID("11111111-1111-1111-1111-111111111111"),
                selected_schema_version="v1",
                recommended_schema_version="v1",
                selection_mode="manual",
                selection_score=4.5,
                recommended_score=4.5,
                selection_reason="用户手动确认",
                recommended_reason="自动推荐：当前候选即最优候选",
                selected_by="web",
                selected_at=datetime(2026, 5, 10, 10, 0, tzinfo=UTC),
                candidate_versions_json=[],
            )
        )
        session.add(
            ArticleMetadata(
                article_id=UUID("11111111-1111-1111-1111-111111111111"),
                version="v1",
                processed_at=datetime(2026, 5, 10, 10, 30, tzinfo=UTC),
                extracted_concepts=[],
                trading_symbols=[],
                strategy_rules=[],
                preconditions=[],
                comment_insights=[],
                raw_llm_output={},
            )
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
        "trader_ids": ["trader_a", "trader_c"],
    }


@pytest.mark.asyncio
async def test_article_list_still_returns_json_for_api_clients(
    client: AsyncClient,
    article_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API 客户端请求 /articles 时仍应返回 JSON，而不是 SPA HTML。"""
    await _seed_articles(article_session_factory)

    monkeypatch.setattr(article_routes, "async_session_factory", lambda: article_session_factory)
    monkeypatch.setenv("WEB_STATIC_DIR", str(Path("/tmp/nonexistent-web-static")))

    response = await client.get("/articles", headers={"Accept": "application/json"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["items"][0]["title"] == "Article Two"


@pytest.mark.asyncio
async def test_article_list_uses_stable_sorting_and_processing_filters(
    client: AsyncClient,
    article_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """文章列表应保持稳定分页，并支持按处理状态过滤。"""
    await _seed_articles(article_session_factory)

    monkeypatch.setattr(article_routes, "async_session_factory", lambda: article_session_factory)

    first_page = await client.get("/articles?page=1&page_size=1", headers={"Accept": "application/json"})
    second_page = await client.get("/articles?page=2&page_size=1", headers={"Accept": "application/json"})
    third_page = await client.get("/articles?page=3&page_size=1", headers={"Accept": "application/json"})

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert third_page.status_code == 200
    assert first_page.json()["items"][0]["id"] == "22222222-2222-2222-2222-222222222222"
    assert second_page.json()["items"][0]["id"] == "11111111-1111-1111-1111-111111111111"
    assert third_page.json()["items"] == []

    processed_response = await client.get("/articles?processing_status=processed", headers={"Accept": "application/json"})
    unprocessed_response = await client.get("/articles?processing_status=unprocessed", headers={"Accept": "application/json"})

    assert processed_response.status_code == 200
    assert unprocessed_response.status_code == 200
    assert [item["id"] for item in processed_response.json()["items"]] == [
        "22222222-2222-2222-2222-222222222222",
    ]
    assert [item["id"] for item in unprocessed_response.json()["items"]] == [
        "11111111-1111-1111-1111-111111111111",
    ]


@pytest.mark.asyncio
async def test_article_quality_summary_filters_by_current_profile(
    client: AsyncClient,
    article_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """文章质量摘要应只统计当前 Profile 范围内的数据。"""
    await _seed_articles(article_session_factory)

    async with article_session_factory() as session:
        session.add(
            BlogArticle(
                source="tgb",
                source_url="https://example.com/article-3",
                title="Article Three",
                author_name="Carol",
                author_id="author-3",
                published_at=datetime(2026, 5, 12, 8, 0, tzinfo=UTC),
                crawled_at=datetime(2026, 5, 12, 9, 0, tzinfo=UTC),
                content_text="third article content",
                summary=None,
                tags=[],
                content_hash="hash-3",
                view_count=1,
                like_count=0,
                bookmark_count=0,
                comment_count=0,
                raw_payload={"trader_id": "trader_a"},
            )
        )
        await session.commit()

    monkeypatch.setattr(article_routes, "async_session_factory", lambda: article_session_factory)
    monkeypatch.setattr(article_routes.ConfigProfileService, "resolve_runtime_profile_id", lambda self, preferred=None: "profile-1")

    async def _load_runtime_config(self, profile_id: str):  # noqa: ANN001
        assert profile_id == "profile-1"
        return SimpleNamespace(
            profile_id="profile-1",
            profile_snapshot_id="snapshot-1",
            config=SimpleNamespace(
                traders=[
                    SimpleNamespace(trader_id="trader_a", enabled=True),
                ],
                crawl=SimpleNamespace(
                    sources=[
                        SimpleNamespace(author_id="author-4", trader_id="trader_b", enabled=True),
                    ]
                ),
            ),
        )

    monkeypatch.setattr(article_routes.ConfigProfileService, "load_profile_runtime_config", _load_runtime_config)

    response = await client.get("/articles/quality")
    assert response.status_code == 200
    assert response.json() == {
        "profile_id": "profile-1",
        "profile_snapshot_id": "snapshot-1",
        "trader_ids": ["trader_a", "trader_b"],
        "author_ids": ["author-4"],
        "total": 2,
        "with_summary": 1,
        "with_tags": 1,
        "with_hash": 2,
        "with_author": 2,
        "latest_crawled_at": "2026-05-12T09:00:00",
    }


@pytest.mark.asyncio
async def test_article_metadata_list_filters_by_selection_status_search_and_page(
    client: AsyncClient,
    article_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """文章元数据列表应支持按选择状态、搜索和分页筛选。"""
    await _seed_articles(article_session_factory)

    async with article_session_factory() as session:
        session.add(
            BlogArticle(
                id=UUID("33333333-3333-3333-3333-333333333333"),
                source="tgb",
                source_url="https://example.com/article-3",
                title="Article Three",
                author_name="Carol",
                author_id="author-3",
                published_at=datetime(2026, 5, 12, 8, 0, tzinfo=UTC),
                crawled_at=datetime(2026, 5, 12, 9, 0, tzinfo=UTC),
                content_text="third article content",
                summary="summary three",
                tags=["macro"],
                content_hash="hash-3",
                view_count=1,
                like_count=0,
                bookmark_count=0,
                comment_count=0,
                raw_payload={"trader_id": "trader_b"},
            )
        )
        await session.commit()

    monkeypatch.setattr(article_metadata_routes, "async_session_factory", lambda: article_session_factory)

    response = await client.get("/api/ui/v1/article-metadata/articles?selection_status=unselected&page=1&page_size=1&search=Two")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["pages"] == 1
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert body["items"][0]["article_id"] == "22222222-2222-2222-2222-222222222222"
    assert body["items"][0]["selection_status"] == "unselected"
    assert body["items"][0]["title"] == "Article Two"

    selected_response = await client.get("/api/ui/v1/article-metadata/articles?selection_status=selected")
    assert selected_response.status_code == 200
    assert selected_response.json()["items"][0]["article_id"] == "11111111-1111-1111-1111-111111111111"
