from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
from sqlalchemy import select

from src.common.utils import ensure_dir
from src.common.paths import resolve_project_path
from src.db.session import session_scope
from src.models.article_metadata import ArticleMetadata
from src.models.blog_article import BlogArticle
from src.models.stage2_canonical import ArticleStructure, RuleCandidate


DUCKDB_DIR = resolve_project_path("data/processed/duckdb")
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

ARTICLE_STRUCTURE_COLUMNS = [
    "article_structure_id", "article_id", "article_revision_id", "prompt_run_id",
    "schema_version", "payload", "evidence_json", "missing_fields",
    "inference_fields", "lifecycle_state", "quality_status", "processed_at",
]

RULE_CANDIDATE_COLUMNS = [
    "rule_candidate_id", "article_structure_id", "source_article_id",
    "candidate_index", "candidate_fingerprint", "rule_type", "canonical_payload",
    "evidence_json", "explicit_fields", "inferred_fields", "missing_fields",
    "data_dependencies", "backtestability_status", "review_state", "quality_status",
]


@dataclass
class ExportStats:
    new_articles: int = 0
    new_metadata: int = 0
    new_article_structures: int = 0
    new_rule_candidates: int = 0
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
    # 添加唯一约束，保证同一文章的同一版本只有一条记录
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_metadata_article_version ON metadata(article_id, schema_version)"
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS article_structures (
            article_structure_id UUID PRIMARY KEY,
            article_id UUID,
            article_revision_id UUID,
            prompt_run_id UUID,
            schema_version VARCHAR,
            payload JSON,
            evidence_json JSON,
            missing_fields JSON,
            inference_fields JSON,
            lifecycle_state VARCHAR,
            quality_status VARCHAR,
            processed_at TIMESTAMP
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS rule_candidates (
            rule_candidate_id UUID PRIMARY KEY,
            article_structure_id UUID,
            source_article_id UUID,
            candidate_index INTEGER,
            candidate_fingerprint VARCHAR,
            rule_type VARCHAR,
            canonical_payload JSON,
            evidence_json JSON,
            explicit_fields JSON,
            inferred_fields JSON,
            missing_fields JSON,
            data_dependencies JSON,
            backtestability_status VARCHAR,
            review_state VARCHAR,
            quality_status VARCHAR
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


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _serialize_article_structure(structure: ArticleStructure) -> tuple[Any, ...]:
    return (
        str(structure.article_structure_id),
        str(structure.article_id),
        str(structure.article_revision_id) if structure.article_revision_id is not None else None,
        str(structure.prompt_run_id),
        structure.schema_version,
        _serialize_value(structure.payload),
        _serialize_value(structure.evidence_json),
        _serialize_value(structure.missing_fields),
        _serialize_value(structure.inference_fields),
        _enum_value(structure.lifecycle_state),
        _enum_value(structure.quality_status),
        structure.updated_at,
    )


def _serialize_rule_candidate(candidate: RuleCandidate) -> tuple[Any, ...]:
    return (
        str(candidate.rule_candidate_id),
        str(candidate.article_structure_id),
        str(candidate.source_article_id),
        candidate.candidate_index,
        candidate.candidate_fingerprint,
        candidate.rule_type,
        _serialize_value(candidate.canonical_payload),
        _serialize_value(candidate.evidence_json),
        _serialize_value(candidate.explicit_fields),
        _serialize_value(candidate.inferred_fields),
        _serialize_value(candidate.missing_fields),
        _serialize_value(candidate.data_dependencies),
        candidate.backtestability_status,
        _enum_value(candidate.review_state),
        _enum_value(candidate.quality_status),
    )


WATERMARK_KEY = "articles_crawled_at"


def _get_watermark(conn: duckdb.DuckDBPyConnection) -> datetime | None:
    """Read the last exported crawled_at watermark from export_state."""
    result = conn.execute(
        "SELECT watermark FROM export_state WHERE key = ?",
        (WATERMARK_KEY,),
    ).fetchone()
    if result and result[0]:
        return datetime.fromisoformat(str(result[0]))
    return None


def _set_watermark(conn: duckdb.DuckDBPyConnection, watermark: datetime) -> None:
    """Update the export watermark in export_state (upsert)."""
    conn.execute(
        "INSERT OR REPLACE INTO export_state (key, watermark, updated_at) VALUES (?, ?, ?)",
        (WATERMARK_KEY, watermark.isoformat(), datetime.now().isoformat()),
    )


async def run_export_task(
    *,
    duckdb_path: Path | None = None,
    force_full: bool = False,
) -> ExportResult:
    """Export articles + metadata from source DB to DuckDB.

    Incremental by default: exports articles with crawled_at > last_watermark.
    Use force_full=True to re-export everything (watermark reset).
    """
    import time

    start = time.monotonic()
    stats = ExportStats()
    dest = resolve_project_path(duckdb_path) if duckdb_path else DUCKDB_PATH

    with _duckdb_conn(dest) as conn:
        _ensure_tables(conn)
        _ensure_export_state_table(conn)

        if force_full:
            watermark: datetime | None = None
        else:
            watermark = _get_watermark(conn)

        stats.watermark_before = watermark

        async with session_scope() as session:
            if watermark is None:
                stmt = (
                    select(BlogArticle, ArticleMetadata)
                    .outerjoin(ArticleMetadata, ArticleMetadata.article_id == BlogArticle.id)
                    .order_by(BlogArticle.crawled_at)
                )
            else:
                stmt = (
                    select(BlogArticle, ArticleMetadata)
                    .outerjoin(ArticleMetadata, ArticleMetadata.article_id == BlogArticle.id)
                    .where(BlogArticle.crawled_at > watermark)
                    .order_by(BlogArticle.crawled_at)
                )

            rows = await session.execute(stmt)
            all_rows = rows.all()

            if not all_rows:
                stats.watermark_after = watermark
                stats.duration_ms = int((time.monotonic() - start) * 1000)
                return ExportResult(stats=stats, duckdb_path=dest)

            # Collect existing article_ids in DuckDB for dedup
            existing_ids: set[str] = set(
                str(r[0]) for r in conn.execute("SELECT id::VARCHAR FROM articles").fetchall()
            )

            article_placeholders = ", ".join(["?"] * len(ARTICLES_COLUMNS))
            article_sql = f"INSERT OR REPLACE INTO articles ({', '.join(ARTICLES_COLUMNS)}) VALUES ({article_placeholders})"

            metadata_placeholders = ", ".join(["?"] * len(METADATA_COLUMNS))
            # S10-004 修复：明确冲突目标列为 (article_id, schema_version)
            # 使用 INSERT ... ON CONFLICT DO UPDATE SET 代替 INSERT OR REPLACE
            # INSERT OR REPLACE 是完整行替换，可能导致非冲突列被意外覆盖
            metadata_sql = (
                f"INSERT INTO metadata ({', '.join(METADATA_COLUMNS)}) "
                f"VALUES ({metadata_placeholders}) "
                f"ON CONFLICT (article_id, schema_version) DO UPDATE SET "
                + ", ".join([
                    f"{col} = EXCLUDED.{col}"
                    for col in METADATA_COLUMNS
                    if col not in ("article_id", "schema_version")
                ])
            )
            structure_placeholders = ", ".join(["?"] * len(ARTICLE_STRUCTURE_COLUMNS))
            structure_sql = (
                f"INSERT OR REPLACE INTO article_structures ({', '.join(ARTICLE_STRUCTURE_COLUMNS)}) "
                f"VALUES ({structure_placeholders})"
            )
            candidate_placeholders = ", ".join(["?"] * len(RULE_CANDIDATE_COLUMNS))
            candidate_sql = (
                f"INSERT OR REPLACE INTO rule_candidates ({', '.join(RULE_CANDIDATE_COLUMNS)}) "
                f"VALUES ({candidate_placeholders})"
            )

            max_crawled_at: datetime | None = None
            article_ids: set[Any] = set()

            for article, meta in all_rows:
                # Track max crawled_at for ALL articles (including skipped) to advance watermark
                if max_crawled_at is None or article.crawled_at > max_crawled_at:
                    max_crawled_at = article.crawled_at

                article_id_str = str(article.id)
                article_ids.add(article.id)

                if article_id_str in existing_ids:
                    stats.skipped += 1
                else:
                    conn.execute(article_sql, _serialize_article(article))
                    stats.new_articles += 1

                if meta is not None:
                    conn.execute(metadata_sql, _serialize_metadata(meta))
                    stats.new_metadata += 1

            if article_ids:
                structure_rows = await session.execute(
                    select(ArticleStructure).where(ArticleStructure.article_id.in_(list(article_ids)))
                )
                structures = structure_rows.scalars().all()
                structure_ids = [structure.article_structure_id for structure in structures]
                for structure in structures:
                    conn.execute(structure_sql, _serialize_article_structure(structure))
                    stats.new_article_structures += 1

                if structure_ids:
                    candidate_rows = await session.execute(
                        select(RuleCandidate).where(RuleCandidate.article_structure_id.in_(structure_ids))
                    )
                    for candidate in candidate_rows.scalars().all():
                        conn.execute(candidate_sql, _serialize_rule_candidate(candidate))
                        stats.new_rule_candidates += 1

        # Update watermark after successful export
        if max_crawled_at is not None:
            _set_watermark(conn, max_crawled_at)
            stats.watermark_after = max_crawled_at

    stats.duration_ms = int((time.monotonic() - start) * 1000)
    return ExportResult(stats=stats, duckdb_path=dest)
