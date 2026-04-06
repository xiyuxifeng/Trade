from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.blog_article import BlogArticle
from src.models.article_metadata import ArticleMetadata
from src.pipeline.tasks.export_task import (
    ExportStats,
    _ensure_export_state_table,
    _get_watermark,
    _set_watermark,
    run_export_task,
    WATERMARK_KEY,
)


class TestWatermarkFunctions:
    def test_ensure_export_state_table_creates_table(self, tmp_path: Path) -> None:
        import duckdb
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))
        try:
            _ensure_export_state_table(conn)
            result = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name = 'export_state'"
            ).fetchone()
            assert result is not None
        finally:
            conn.close()

    def test_get_watermark_returns_none_when_empty(self, tmp_path: Path) -> None:
        import duckdb
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))
        _ensure_export_state_table(conn)
        try:
            watermark = _get_watermark(conn)
            assert watermark is None
        finally:
            conn.close()

    def test_set_and_get_watermark(self, tmp_path: Path) -> None:
        import duckdb
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))
        _ensure_export_state_table(conn)
        try:
            ts = datetime(2026, 4, 6, 10, 0, 0, tzinfo=timezone.utc)
            _set_watermark(conn, ts)
            retrieved = _get_watermark(conn)
            assert retrieved is not None
            assert retrieved.year == 2026
            assert retrieved.month == 4
            assert retrieved.day == 6
        finally:
            conn.close()

    def test_watermark_key_is_correct(self) -> None:
        assert WATERMARK_KEY == "articles_crawled_at"


class TestExportStatsWatermarks:
    def test_export_stats_default_watermarks_none(self) -> None:
        stats = ExportStats()
        assert stats.watermark_before is None
        assert stats.watermark_after is None

    def test_export_stats_watermarks_settable(self) -> None:
        ts = datetime(2026, 4, 6, 10, 0, 0, tzinfo=timezone.utc)
        stats = ExportStats(watermark_before=ts, watermark_after=ts)
        assert stats.watermark_before == ts
        assert stats.watermark_after == ts


class TestRunExportTask:
    """Integration tests for run_export_task."""

    def _create_mock_article(
        self,
        article_id: str | None = None,
        crawled_at: datetime | None = None,
        source: str = "test_source",
        content_text: str = "Test content",
    ) -> MagicMock:
        """Create a mock BlogArticle object."""
        article = MagicMock(spec=BlogArticle)
        article.id = uuid4() if article_id is None else article_id
        article.source = source
        article.source_article_id = "test_article_id"
        article.source_url = "https://example.com/article"
        article.title = "Test Title"
        article.author_name = "Test Author"
        article.author_id = "author_123"
        article.published_at = datetime(2026, 4, 5, 10, 0, 0, tzinfo=timezone.utc)
        article.crawled_at = crawled_at or datetime(2026, 4, 6, 9, 0, 0, tzinfo=timezone.utc)
        article.content_text = content_text
        article.content_html = "<p>Test content</p>"
        article.summary = "Test summary"
        article.tags = ["tag1", "tag2"]
        article.view_count = 100
        article.like_count = 10
        article.bookmark_count = 5
        article.comment_count = 2
        article.comments_payload = []
        article.raw_payload = {}
        article.content_hash = "abc123def456"
        return article

    def _create_mock_metadata(self, article_id: uuid.UUID) -> MagicMock:
        """Create a mock ArticleMetadata object."""
        meta = MagicMock(spec=ArticleMetadata)
        meta.id = uuid4()
        meta.article_id = article_id
        meta.schema_version = "v1"
        meta.processed_at = datetime(2026, 4, 6, 10, 0, 0, tzinfo=timezone.utc)
        meta.extracted_concepts = []
        meta.trading_symbols = ["AAPL", "GOOGL"]
        meta.strategy_rules = []
        meta.preconditions = []
        meta.comment_insights = []
        meta.raw_llm_output = {}
        meta.sentiment_score = 0.75
        meta.confidence_score = 0.85
        return meta

    @pytest.mark.asyncio
    async def test_force_full_resets_watermark(self, tmp_path: Path) -> None:
        """Test that force_full=True resets watermark and exports all articles."""
        db_path = tmp_path / "test_export.duckdb"

        article = self._create_mock_article()
        mock_meta = self._create_mock_metadata(article.id)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [(article, mock_meta)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_scope = AsyncMock()
        mock_session_scope.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_scope.__aexit__ = AsyncMock(return_value=None)

        with patch("src.pipeline.tasks.export_task.session_scope", return_value=mock_session_scope):
            result = await run_export_task(duckdb_path=db_path, force_full=True)

        assert result.stats.watermark_before is None
        assert result.stats.watermark_after is not None
        assert result.stats.new_articles == 1
        assert result.stats.new_metadata == 1
        assert result.stats.skipped == 0

        import duckdb
        conn = duckdb.connect(str(db_path))
        try:
            count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            assert count == 1
            export_state_count = conn.execute("SELECT COUNT(*) FROM export_state").fetchone()[0]
            assert export_state_count == 1
        finally:
            conn.close()

    @pytest.mark.asyncio
    async def test_incremental_with_no_new_articles(self, tmp_path: Path) -> None:
        """Test that incremental export with no new articles preserves watermark."""
        db_path = tmp_path / "test_export_incremental.duckdb"

        article = self._create_mock_article()
        mock_meta = self._create_mock_metadata(article.id)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [(article, mock_meta)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_scope = AsyncMock()
        mock_session_scope.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_scope.__aexit__ = AsyncMock(return_value=None)

        with patch("src.pipeline.tasks.export_task.session_scope", return_value=mock_session_scope):
            result1 = await run_export_task(duckdb_path=db_path, force_full=True)

        assert result1.stats.watermark_before is None
        assert result1.stats.watermark_after is not None
        watermark_after_full = result1.stats.watermark_after

        mock_result_empty = MagicMock()
        mock_result_empty.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result_empty)

        with patch("src.pipeline.tasks.export_task.session_scope", return_value=mock_session_scope):
            result2 = await run_export_task(duckdb_path=db_path, force_full=False)

        # Watermark from DuckDB is naive datetime, so compare without timezone
        assert result2.stats.watermark_before.replace(tzinfo=None) == watermark_after_full.replace(tzinfo=None)
        assert result2.stats.watermark_after.replace(tzinfo=None) == watermark_after_full.replace(tzinfo=None)
        assert result2.stats.new_articles == 0

    @pytest.mark.asyncio
    async def test_skipped_articles_advance_watermark(self, tmp_path: Path) -> None:
        """Test that skipped articles still advance the watermark."""
        db_path = tmp_path / "test_export_skipped.duckdb"

        article_id = uuid4()
        article = self._create_mock_article(
            article_id=str(article_id),
            crawled_at=datetime(2026, 4, 6, 9, 0, 0, tzinfo=timezone.utc)
        )
        article.id = article_id
        mock_meta = self._create_mock_metadata(article_id)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [(article, mock_meta)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_scope = AsyncMock()
        mock_session_scope.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_scope.__aexit__ = AsyncMock(return_value=None)

        with patch("src.pipeline.tasks.export_task.session_scope", return_value=mock_session_scope):
            result1 = await run_export_task(duckdb_path=db_path, force_full=True)

        assert result1.stats.new_articles == 1
        first_watermark = result1.stats.watermark_after

        # Return same article with newer crawled_at (simulating re-crawl)
        newer_article = self._create_mock_article(
            article_id=str(article_id),
            crawled_at=datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc)
        )
        newer_article.id = article_id
        mock_result2 = MagicMock()
        mock_result2.all.return_value = [(newer_article, None)]
        mock_session.execute = AsyncMock(return_value=mock_result2)

        with patch("src.pipeline.tasks.export_task.session_scope", return_value=mock_session_scope):
            result2 = await run_export_task(duckdb_path=db_path, force_full=False)

        assert result2.stats.watermark_after.replace(tzinfo=None) > first_watermark.replace(tzinfo=None)
        assert result2.stats.skipped == 1
        assert result2.stats.new_articles == 0

    @pytest.mark.asyncio
    async def test_empty_result_preserves_watermark(self, tmp_path: Path) -> None:
        """Test that empty result preserves watermark unchanged."""
        db_path = tmp_path / "test_export_empty.duckdb"

        article = self._create_mock_article()
        mock_meta = self._create_mock_metadata(article.id)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [(article, mock_meta)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_scope = AsyncMock()
        mock_session_scope.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_scope.__aexit__ = AsyncMock(return_value=None)

        with patch("src.pipeline.tasks.export_task.session_scope", return_value=mock_session_scope):
            result1 = await run_export_task(duckdb_path=db_path, force_full=True)

        assert result1.stats.watermark_after is not None
        watermark_after_first = result1.stats.watermark_after

        mock_result_empty = MagicMock()
        mock_result_empty.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result_empty)

        with patch("src.pipeline.tasks.export_task.session_scope", return_value=mock_session_scope):
            result2 = await run_export_task(duckdb_path=db_path, force_full=False)

        assert result2.stats.watermark_before.replace(tzinfo=None) == watermark_after_first.replace(tzinfo=None)
        assert result2.stats.watermark_after.replace(tzinfo=None) == watermark_after_first.replace(tzinfo=None)
        assert result2.stats.new_articles == 0