from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
from sqlalchemy import select

from src.common.utils import ensure_dir
from src.db.session import session_scope
from src.models.article_metadata import ArticleMetadata
from src.models.blog_article import BlogArticle


DUCKDB_DIR = Path("data/processed/duckdb")
DUCKDB_PATH = DUCKDB_DIR / "trade_strategy_ai.duckdb"

ARTICLES_COLUMNS = [
    "id", "source", "source_article_id", "source_url", "title",
    "author_name", "author_id", "published_at", "crawled_at",
    "content_text", "content_html", "summary", "tags",
    "view_count", "like_count", "bookmark_count", "comment_count",
    "comments_payload", "raw_payload", "content_hash",
]

METADATA_COLUMNS = [
    "id", "article_id", "schema_version", "processed_at",
    "extracted_concepts", "trading_symbols", "strategy_rules",
    "preconditions", "comment_insights", "raw_llm_output",
    "sentiment_score", "confidence_score",
]


@dataclass
class ExportStats:
    new_articles: int = 0
    new_metadata: int = 0
    skipped: int = 0
    duration_ms: int = 0
    watermark_before: datetime | None = None
    watermark_after: datetime | None = None


@dataclass
class ExportResult:
    stats: ExportStats
    duckdb_path: Path


def _duckdb_conn(path: Path) -> duckdb.DuckDBPyConnection:
    ensure_dir(path.parent)
    return duckdb.connect(str(path))


def _ensure_tables(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        "CREATE SEQUENCE IF NOT EXISTS articles_id_seq START 1;"
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS articles (
            id UUID PRIMARY KEY,
            source VARCHAR,
            source_article_id VARCHAR,
            source_url VARCHAR,
            title VARCHAR,
            author_name VARCHAR,
            author_id VARCHAR,
            published_at TIMESTAMP,
            crawled_at TIMESTAMP,
            content_text VARCHAR,
            content_html VARCHAR,
            summary VARCHAR,
            tags JSON,
            view_count BIGINT,
            like_count BIGINT,
            bookmark_count BIGINT,
            comment_count BIGINT,
            comments_payload JSON,
            raw_payload JSON,
            content_hash VARCHAR
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS metadata (
            id UUID PRIMARY KEY,
            article_id UUID,
            schema_version VARCHAR,
            processed_at TIMESTAMP,
            extracted_concepts JSON,
            trading_symbols JSON,
            strategy_rules JSON,
            preconditions JSON,
            comment_insights JSON,
            raw_llm_output JSON,
            sentiment_score DOUBLE,
            confidence_score DOUBLE
        )
        """
    )


def _ensure_export_state_table(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS export_state (
            key VARCHAR PRIMARY KEY,
            watermark TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )


def _serialize_value(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    return v


def _serialize_article(article: BlogArticle) -> tuple[Any, ...]:
    return (
        str(article.id),
        article.source,
        article.source_article_id,
        article.source_url,
        article.title,
        article.author_name,
        article.author_id,
        article.published_at,
        article.crawled_at,
        article.content_text,
        article.content_html,
        article.summary,
        _serialize_value(article.tags),
        article.view_count,
        article.like_count,
        article.bookmark_count,
        article.comment_count,
        _serialize_value(article.comments_payload),
        _serialize_value(article.raw_payload),
        article.content_hash,
    )


def _serialize_metadata(meta: ArticleMetadata) -> tuple[Any, ...]:
    return (
        str(meta.id),
        str(meta.article_id),
        meta.schema_version,
        meta.processed_at,
        _serialize_value(meta.extracted_concepts),
        _serialize_value(meta.trading_symbols),
        _serialize_value(meta.strategy_rules),
        _serialize_value(meta.preconditions),
        _serialize_value(meta.comment_insights),
        _serialize_value(meta.raw_llm_output),
        float(meta.sentiment_score) if meta.sentiment_score is not None else None,
        float(meta.confidence_score) if meta.confidence_score is not None else None,
    )


def _get_max_article_id(conn: duckdb.DuckDBPyConnection) -> str | None:
    result = conn.execute("SELECT MAX(id::VARCHAR) FROM articles").fetchone()
    if result and result[0]:
        return str(result[0])
    return None


async def run_export_task(
    *,
    duckdb_path: Path | None = None,
    force_full: bool = False,
) -> ExportResult:
    """Export articles + metadata from source DB to DuckDB.

    Incremental by default: only exports articles with id > max(articles.id) in DuckDB.
    Use force_full=True to re-export everything.
    """
    import time

    start = time.monotonic()
    stats = ExportStats()
    dest = Path(duckdb_path) if duckdb_path else DUCKDB_PATH

    with _duckdb_conn(dest) as conn:
        _ensure_tables(conn)

        if force_full:
            max_id: str | None = None
        else:
            max_id = _get_max_article_id(conn)

        async with session_scope() as session:
            if max_id is None:
                stmt = (
                    select(BlogArticle, ArticleMetadata)
                    .outerjoin(ArticleMetadata, ArticleMetadata.article_id == BlogArticle.id)
                    .order_by(BlogArticle.id)
                )
            else:
                max_uuid = uuid.UUID(max_id)
                stmt = (
                    select(BlogArticle, ArticleMetadata)
                    .outerjoin(ArticleMetadata, ArticleMetadata.article_id == BlogArticle.id)
                    .where(BlogArticle.id > max_uuid)
                    .order_by(BlogArticle.id)
                )

            rows = await session.execute(stmt)
            all_rows = rows.all()

            if not all_rows:
                stats.duration_ms = int((time.monotonic() - start) * 1000)
                return ExportResult(stats=stats, duckdb_path=dest)

            # Collect existing article_ids in DuckDB for dedup
            existing_ids: set[str] = set()
            if max_id is None:
                existing_ids = set(
                    str(r[0]) for r in conn.execute("SELECT id::VARCHAR FROM articles").fetchall()
                )

            article_placeholders = ", ".join(["?"] * len(ARTICLES_COLUMNS))
            article_sql = f"INSERT OR REPLACE INTO articles ({', '.join(ARTICLES_COLUMNS)}) VALUES ({article_placeholders})"

            metadata_placeholders = ", ".join(["?"] * len(METADATA_COLUMNS))
            metadata_sql = f"INSERT OR REPLACE INTO metadata ({', '.join(METADATA_COLUMNS)}) VALUES ({metadata_placeholders})"

            for article, meta in all_rows:
                article_id_str = str(article.id)

                if article_id_str in existing_ids:
                    stats.skipped += 1
                    continue

                conn.execute(article_sql, _serialize_article(article))
                stats.new_articles += 1

                if meta is not None:
                    conn.execute(metadata_sql, _serialize_metadata(meta))
                    stats.new_metadata += 1

    stats.duration_ms = int((time.monotonic() - start) * 1000)
    return ExportResult(stats=stats, duckdb_path=dest)
