from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import verify_api_key
from src.api.schemas import ArticleResponse
from src.db.session import get_session_factory as async_session_factory
from src.models.blog_article import BlogArticle

router = APIRouter(prefix="/articles", tags=["articles"])


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
    _: str = Depends(verify_api_key),
):
    """Export articles to CSV/JSON/Parquet."""
    async with async_session_factory() as session:
        query = select(BlogArticle)
        count_query = select(func.count(BlogArticle.id))
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
