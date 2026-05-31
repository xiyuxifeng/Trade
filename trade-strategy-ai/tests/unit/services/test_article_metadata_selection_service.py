from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.article_metadata import ArticleMetadata
from src.models.article_metadata_selection import ArticleMetadataSelection
from src.models.blog_article import BlogArticle
from src.services.article_metadata_selection_service import ArticleMetadataSelectionService


@pytest_asyncio.fixture
async def session_factory(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'article-metadata.db'}")

    @event.listens_for(engine.sync_engine, 'connect')
    def _register_char_length(dbapi_connection, _connection_record):  # noqa: ANN001
        dbapi_connection.create_function('char_length', 1, lambda value: len(value) if value is not None else 0)

    async with engine.begin() as conn:
        await conn.run_sync(BlogArticle.__table__.create)
        await conn.run_sync(ArticleMetadata.__table__.create)
        await conn.run_sync(ArticleMetadataSelection.__table__.create)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@asynccontextmanager
async def _session_scope(factory: async_sessionmaker[AsyncSession]):
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.mark.asyncio
async def test_article_metadata_selection_service_auto_selects_best_version(session_factory: async_sessionmaker[AsyncSession]) -> None:
    article_id = uuid4()
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
                extracted_concepts=[{'name': 'macd'}],
                trading_symbols=['000001.SZ'],
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

    service = ArticleMetadataSelectionService()
    async with _session_scope(session_factory) as session:
        resolution = await service.resolve_resolution(session, article_id=article_id)

    assert resolution.selected_schema_version == 'v1'
    assert resolution.recommended_schema_version == 'v1'
    assert resolution.effective_schema_version == 'v1'
    assert resolution.selection_mode == 'auto'
    assert resolution.selected_at is not None
    candidates_by_version = {candidate.schema_version: candidate for candidate in resolution.candidates}
    assert candidates_by_version['v1'].score > candidates_by_version['v2'].score

    async with session_factory() as session:
        selection_row = await session.scalar(select(ArticleMetadataSelection).where(ArticleMetadataSelection.article_id == article_id))
        assert selection_row is not None
        assert selection_row.selected_schema_version == 'v1'
        assert selection_row.selection_mode == 'auto'


@pytest.mark.asyncio
async def test_article_metadata_selection_service_manual_override_and_effective_map(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    article_id = uuid4()
    async with session_factory() as session:
        session.add(
            BlogArticle(
                id=article_id,
                source='tgb',
                source_url='https://example.com/article-2',
                title='Article Two',
                author_id='author-2',
                author_name='Bob',
                published_at=datetime(2026, 5, 11, tzinfo=UTC),
                crawled_at=datetime(2026, 5, 11, 9, 0, tzinfo=UTC),
                content_text='hello',
                raw_payload={'trader_id': 'trader-b'},
            )
        )
        session.add(
            ArticleMetadata(
                article_id=article_id,
                version='v1',
                processed_at=datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
                extracted_concepts=[{'name': 'trend'}],
                trading_symbols=['000002.SZ'],
                strategy_rules=[{'rule_id': 'rule-1'}],
                preconditions=[{'rule_id': 'pre-1'}],
                comment_insights=[{'insight': 'neutral'}],
                raw_llm_output={'a': 1, 'b': 2},
                sentiment_score=0.5,
                confidence_score=0.8,
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
                processed_at=datetime(2026, 5, 11, 10, 20, tzinfo=UTC),
                extracted_concepts=[{'name': 'trend'}, {'name': 'breakout'}],
                trading_symbols=['000002.SZ', '000003.SZ'],
                strategy_rules=[{'rule_id': 'rule-2'}, {'rule_id': 'rule-3'}],
                preconditions=[{'rule_id': 'pre-2'}],
                comment_insights=[{'insight': 'strong'}],
                raw_llm_output={'a': 1, 'b': 2, 'c': 3},
                sentiment_score=0.7,
                confidence_score=0.95,
                provider='claude',
                model='sonnet',
                article_type='rule',
                extraction_version='v2',
            )
        )
        await session.commit()

    service = ArticleMetadataSelectionService()
    async with _session_scope(session_factory) as session:
        resolution = await service.select_version(
            session,
            article_id=article_id,
            selected_schema_version='v1',
            selected_by='web',
            selection_reason='manual selection',
        )
        effective_map = await service.load_effective_metadata_map(session, article_ids=[article_id])

    assert resolution.selected_schema_version == 'v1'
    assert resolution.selection_mode == 'manual'
    assert resolution.effective_schema_version == 'v1'
    assert resolution.effective_reason == 'manual selection'
    assert effective_map[article_id].version == 'v1'
