from __future__ import annotations

from datetime import datetime
from io import BytesIO
from collections.abc import Iterable

from sqlalchemy import or_
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import verify_api_key
from api.schemas import ArticleFilterOptionsResponse, ArticleResponse
from src.common.config import load_app_config
from src.db.session import get_session_factory as async_session_factory
from src.models.blog_article import BlogArticle

router = APIRouter(prefix="/articles", tags=["articles"])


def _build_trader_id_condition(trader_id: str | None, config: Any):
    """Build SQLAlchemy filter condition for trader_id.

    Logic:
    - If trader_id is None, return None (no filter)
    - First try raw_payload['trader_id'] match
    - Then fall back to author_id mapping via crawl.sources config
    """
    if not trader_id:
        return None

    # 安全获取 sources 列表
    sources = getattr(getattr(config, 'crawl', None), 'sources', None) or []

    # Build trader_id → author_ids mapping from crawl sources
    author_ids = [
        src.author_id
        for src in sources
        if getattr(src, 'author_id', None) and getattr(src, 'trader_id', None) == trader_id
    ]

    if author_ids:
        return or_(
            BlogArticle.raw_payload["trader_id"].as_string() == trader_id,
            BlogArticle.author_id.in_(author_ids),
        )
    return BlogArticle.raw_payload["trader_id"].as_string() == trader_id


def _normalize_strings(values: Iterable[str | None]) -> list[str]:
    """去重并稳定排序字符串值。"""
    normalized = {value.strip() for value in values if isinstance(value, str) and value.strip()}
    return sorted(normalized)


def _load_article_config() -> Any | None:
    """安全加载文章筛选所需配置。"""
    try:
        return load_app_config("config/app.yaml").config
    except Exception:
        return None


def _collect_trader_ids(rows, config: Any | None) -> list[str]:
    """从文章行中提取 trader_id，并补充 author_id 映射。"""
    trader_values: list[str] = []
    for row in rows:
        raw_payload = row.get("raw_payload")
        if isinstance(raw_payload, dict):
            raw_trader_id = raw_payload.get("trader_id")
            if isinstance(raw_trader_id, str):
                trader_values.append(raw_trader_id)

        mapped_trader_id = _author_to_trader_id(config, str(row.get("author_id") or ""))
        if mapped_trader_id:
            trader_values.append(mapped_trader_id)

    return _normalize_strings(trader_values)


def _apply_article_filters(
    query,
    count_query=None,
    *,
    author_id: str | None = None,
    source: str | None = None,
    trader_id: str | None = None,
    published_after: datetime | None = None,
    published_before: datetime | None = None,
    config: Any | None = None,
    exclude_fields: set[str] | frozenset[str] = frozenset(),
):
    """给文章查询套用过滤条件。"""
    excluded = set(exclude_fields)

    if trader_id and "trader_id" not in excluded:
        cfg = config or load_app_config("config/app.yaml").config
        condition = _build_trader_id_condition(trader_id, cfg)
        if condition is not None:
            query = query.where(condition)
            if count_query is not None:
                count_query = count_query.where(condition)

    if author_id and "author_id" not in excluded:
        query = query.where(BlogArticle.author_id == author_id)
        if count_query is not None:
            count_query = count_query.where(BlogArticle.author_id == author_id)
    if source and "source" not in excluded:
        query = query.where(BlogArticle.source == source)
        if count_query is not None:
            count_query = count_query.where(BlogArticle.source == source)
    if published_after and "published_after" not in excluded:
        query = query.where(BlogArticle.published_at >= published_after)
        if count_query is not None:
            count_query = count_query.where(BlogArticle.published_at >= published_after)
    if published_before and "published_before" not in excluded:
        query = query.where(BlogArticle.published_at <= published_before)
        if count_query is not None:
            count_query = count_query.where(BlogArticle.published_at <= published_before)

    if count_query is None:
        return query
    return query, count_query


@router.get("", response_model=dict[str, Any])
async def list_articles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    author_id: str | None = None,
    source: str | None = None,
    trader_id: str | None = None,
    published_after: datetime | None = None,
    published_before: datetime | None = None,
    _: str = Depends(verify_api_key),
):
    """List articles with pagination and filters."""
    offset = (page - 1) * page_size

    session_factory = async_session_factory()
    async with session_factory() as session:
        query = select(BlogArticle)
        count_query = select(func.count(BlogArticle.id))
        query, count_query = _apply_article_filters(
            query,
            count_query,
            author_id=author_id,
            source=source,
            trader_id=trader_id,
            published_after=published_after,
            published_before=published_before,
        )

        query = query.order_by(BlogArticle.published_at.desc()).offset(offset).limit(page_size)

        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        result = await session.execute(query)
        articles = result.scalars().all()

        items = [
            ArticleResponse.model_validate(a).model_dump(mode="json")
            for a in articles
        ]

        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }


def _articles_query_filters(query, count_query, author_id, source, published_after, published_before):
    """Apply filters to article query."""
    return _apply_article_filters(
        query,
        count_query,
        author_id=author_id,
        source=source,
        published_after=published_after,
        published_before=published_before,
    )


@router.get("/filter-options", response_model=ArticleFilterOptionsResponse)
async def list_article_filter_options(
    author_id: str | None = None,
    source: str | None = None,
    trader_id: str | None = None,
    published_after: datetime | None = None,
    published_before: datetime | None = None,
    _: str = Depends(verify_api_key),
):
    """Return linked filter options for the article list page."""
    session_factory = async_session_factory()
    async with session_factory() as session:
        author_query = select(BlogArticle.author_id).distinct()
        author_query = _apply_article_filters(
            author_query,
            author_id=author_id,
            source=source,
            trader_id=trader_id,
            published_after=published_after,
            published_before=published_before,
            exclude_fields={"author_id"},
        ).order_by(BlogArticle.author_id.asc())
        author_result = await session.execute(author_query)
        author_ids = _normalize_strings(author_result.scalars().all())

        source_query = select(BlogArticle.source).distinct()
        source_query = _apply_article_filters(
            source_query,
            author_id=author_id,
            source=source,
            trader_id=trader_id,
            published_after=published_after,
            published_before=published_before,
            exclude_fields={"source"},
        ).order_by(BlogArticle.source.asc())
        source_result = await session.execute(source_query)
        sources = _normalize_strings(source_result.scalars().all())

        cfg = _load_article_config()
        trader_query = select(
            BlogArticle.author_id.label("author_id"),
            BlogArticle.raw_payload.label("raw_payload"),
        )
        trader_query = _apply_article_filters(
            trader_query,
            author_id=author_id,
            source=source,
            trader_id=trader_id,
            published_after=published_after,
            published_before=published_before,
            config=cfg,
            exclude_fields={"trader_id"},
        )
        trader_result = await session.execute(trader_query)
        trader_ids = _collect_trader_ids(trader_result.mappings().all(), cfg)

        return {
            "author_ids": author_ids,
            "sources": sources,
            "trader_ids": trader_ids,
        }


def _author_to_trader_id(config: Any, author_id: str) -> str | None:
    """根据 crawl.sources 配置把 author_id 解析成 trader_id。"""
    if not author_id:
        return None

    sources = getattr(getattr(config, "crawl", None), "sources", None) or []
    for source in sources:
        if getattr(source, "author_id", None) == author_id and getattr(source, "trader_id", None):
            return str(getattr(source, "trader_id"))
    return None


@router.get("/export")
async def export_articles(
    format: str = Query(default="csv", pattern="^(csv|json|parquet)$"),
    author_id: str | None = None,
    source: str | None = None,
    published_after: datetime | None = None,
    published_before: datetime | None = None,
    trader_id: str | None = None,
    _: str = Depends(verify_api_key),
):
    """Export articles to CSV/JSON/Parquet."""
    session_factory = async_session_factory()
    async with session_factory() as session:
        query = select(BlogArticle)
        count_query = select(func.count(BlogArticle.id))

        # Apply trader_id filter
        if trader_id:
            cfg = load_app_config("config/app.yaml").config
            condition = _build_trader_id_condition(trader_id, cfg)
            if condition is not None:
                query = query.where(condition)
                count_query = count_query.where(condition)

        query, count_query = _articles_query_filters(query, count_query, author_id, source, published_after, published_before)
        query = query.order_by(BlogArticle.published_at.desc())

        result = await session.execute(query)
        articles = result.scalars().all()

        items = [
            ArticleResponse.model_validate(a).model_dump(mode="json")
            for a in articles
        ]

        df = pd.DataFrame(items)

        buffer = BytesIO()
        filename = f"articles_export.{format}"

        if format == "csv":
            df.to_csv(buffer, index=False)
            media_type = "text/csv"
        elif format == "json":
            df.to_json(buffer, orient="records", force_ascii=False, indent=2)
            media_type = "application/json"
        else:  # parquet
            df.to_parquet(buffer, index=False)
            media_type = "application/octet-stream"

        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
