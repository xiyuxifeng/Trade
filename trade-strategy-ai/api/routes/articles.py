from __future__ import annotations

from datetime import datetime
from io import BytesIO

from sqlalchemy import or_
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import verify_api_key
from api.schemas import ArticleResponse
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
            BlogArticle.raw_payload["trader_id"].astext == trader_id,
            BlogArticle.author_id.in_(author_ids),
        )
    return BlogArticle.raw_payload["trader_id"].astext == trader_id


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

    async with async_session_factory() as session:
        query = select(BlogArticle)
        count_query = select(func.count(BlogArticle.id))

        # Apply trader_id filter
        if trader_id:
            cfg = load_app_config("config/app.yaml").config
            condition = _build_trader_id_condition(trader_id, cfg)
            if condition is not None:
                query = query.where(condition)
                count_query = count_query.where(condition)

        if author_id:
            query = query.where(BlogArticle.author_id == author_id)
            count_query = count_query.where(BlogArticle.author_id == author_id)
        if source:
            query = query.where(BlogArticle.source == source)
            count_query = count_query.where(BlogArticle.source == source)
        if published_after:
            query = query.where(BlogArticle.published_at >= published_after)
            count_query = count_query.where(BlogArticle.published_at >= published_after)
        if published_before:
            query = query.where(BlogArticle.published_at <= published_before)
            count_query = count_query.where(BlogArticle.published_at <= published_before)

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
    if author_id:
        query = query.where(BlogArticle.author_id == author_id)
        count_query = count_query.where(BlogArticle.author_id == author_id)
    if source:
        query = query.where(BlogArticle.source == source)
        count_query = count_query.where(BlogArticle.source == source)
    if published_after:
        query = query.where(BlogArticle.published_at >= published_after)
        count_query = count_query.where(BlogArticle.published_at >= published_after)
    if published_before:
        query = query.where(BlogArticle.published_at <= published_before)
        count_query = count_query.where(BlogArticle.published_at <= published_before)
    return query, count_query


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
    async with async_session_factory() as session:
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
