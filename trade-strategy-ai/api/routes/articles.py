from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO
from collections.abc import Iterable
from pathlib import Path

from sqlalchemy import exists, func, or_, select
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import verify_api_key
from api.schemas import ArticleFilterOptionsResponse, ArticleQualitySummaryResponse, ArticleResponse
from src.common.config import load_app_config
from src.common.paths import resolve_project_path
from src.db.session import get_session_factory as async_session_factory
from src.models.blog_article import BlogArticle
from src.models.stage2_canonical import ArticleStructure
from src.services.config_profile_service import ConfigProfileService

router = APIRouter(prefix="/articles", tags=["articles"])


def _resolve_local_web_index() -> Path | None:
    """解析本机调试时的 Web 静态入口。"""
    raw = os.getenv("WEB_STATIC_DIR")
    if not raw:
        return None
    candidate = resolve_project_path(raw)
    index_path = candidate / "index.html"
    return index_path if index_path.exists() else None


def _should_serve_web_index(request: Request) -> bool:
    """判断当前请求是否更像浏览器的页面导航而不是 API 请求。"""
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return False
    return "text/html" in accept or "*/*" in accept or not accept.strip()


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


def _collect_profile_trader_ids(config: Any) -> list[str]:
    """提取当前 Profile 作用范围内的 trader_id。"""
    trader_ids: list[str] = []

    traders = getattr(config, "traders", None) or []
    for trader in traders:
        if getattr(trader, "enabled", True) and getattr(trader, "trader_id", None):
            trader_ids.append(str(getattr(trader, "trader_id")))

    sources = getattr(getattr(config, "crawl", None), "sources", None) or []
    for source in sources:
        if not getattr(source, "enabled", True):
            continue
        if getattr(source, "trader_id", None):
            trader_ids.append(str(getattr(source, "trader_id")))

    return _normalize_strings(trader_ids)


def _collect_profile_author_ids(config: Any) -> list[str]:
    """提取当前 Profile 作用范围内的 author_id。"""
    author_ids: list[str] = []

    sources = getattr(getattr(config, "crawl", None), "sources", None) or []
    for source in sources:
        if getattr(source, "enabled", True) and getattr(source, "author_id", None):
            author_ids.append(str(getattr(source, "author_id")))

    return _normalize_strings(author_ids)


def _build_profile_article_scope_condition(config: Any):
    """构建当前 Profile 对应的文章筛选条件。"""
    trader_ids = _collect_profile_trader_ids(config)
    author_ids = _collect_profile_author_ids(config)
    conditions = []

    for trader_id in trader_ids:
        condition = _build_trader_id_condition(trader_id, config)
        if condition is not None:
            conditions.append(condition)

    if author_ids:
        conditions.append(BlogArticle.author_id.in_(author_ids))

    if not conditions:
        return None

    return or_(*conditions)


def _summarize_quality_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """把文章明细压缩成质量摘要。"""
    total = len(rows)
    with_summary = 0
    with_tags = 0
    with_hash = 0
    with_author = 0
    latest_crawled_at = None

    for row in rows:
        summary = row.get("summary")
        tags = row.get("tags")
        content_hash = row.get("content_hash")
        author_id = row.get("author_id")
        author_name = row.get("author_name")
        crawled_at = row.get("crawled_at")

        if isinstance(summary, str) and summary.strip():
            with_summary += 1
        if isinstance(tags, list) and len(tags) > 0:
            with_tags += 1
        if isinstance(content_hash, str) and content_hash.strip():
            with_hash += 1
        if bool(author_name) or bool(author_id):
            with_author += 1
        if isinstance(crawled_at, datetime):
            if latest_crawled_at is None or crawled_at > latest_crawled_at:
                latest_crawled_at = crawled_at

    return {
        "total": total,
        "with_summary": with_summary,
        "with_tags": with_tags,
        "with_hash": with_hash,
        "with_author": with_author,
        "latest_crawled_at": latest_crawled_at,
    }


def _apply_article_filters(
    query,
    count_query=None,
    *,
    author_id: str | None = None,
    source: str | None = None,
    trader_id: str | None = None,
    published_after: datetime | None = None,
    published_before: datetime | None = None,
    processing_status: str | None = None,
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

    if processing_status and "processing_status" not in excluded:
        processed_exists = exists(select(1).where(ArticleStructure.article_id == BlogArticle.id))
        if processing_status == "processed":
            condition = processed_exists
        elif processing_status == "unprocessed":
            condition = ~processed_exists
        else:
            condition = None

        if condition is not None:
            query = query.where(condition)
            if count_query is not None:
                count_query = count_query.where(condition)

    if count_query is None:
        return query
    return query, count_query


@router.get("", response_model=dict[str, Any])
async def list_articles(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    author_id: str | None = None,
    source: str | None = None,
    trader_id: str | None = None,
    published_after: datetime | None = None,
    published_before: datetime | None = None,
    processing_status: str = Query(default="all", pattern="^(all|processed|unprocessed)$"),
    _: str = Depends(verify_api_key),
):
    """List articles with pagination and filters."""
    if _should_serve_web_index(request):
        web_index = _resolve_local_web_index()
        if web_index is not None:
            return FileResponse(web_index)

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
            processing_status=processing_status,
        )

        query = query.order_by(
            BlogArticle.published_at.desc().nullslast(),
            BlogArticle.crawled_at.desc(),
            BlogArticle.id.desc(),
        ).offset(offset).limit(page_size)

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


@router.get("/quality", response_model=ArticleQualitySummaryResponse)
async def get_article_quality_summary(
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """返回当前 Profile 范围内的文章质量全量摘要。"""
    service = ConfigProfileService()
    profile_id = service.resolve_runtime_profile_id()
    runtime = await service.load_profile_runtime_config(profile_id)
    trader_ids = _collect_profile_trader_ids(runtime.config)
    author_ids = _collect_profile_author_ids(runtime.config)
    scope_condition = _build_profile_article_scope_condition(runtime.config)

    session_factory = async_session_factory()
    async with session_factory() as session:
        query = select(
            BlogArticle.author_id,
            BlogArticle.author_name,
            BlogArticle.summary,
            BlogArticle.tags,
            BlogArticle.content_hash,
            BlogArticle.crawled_at,
        )
        if scope_condition is None:
            rows = []
        else:
            result = await session.execute(query.where(scope_condition).order_by(BlogArticle.crawled_at.desc()))
            rows = result.mappings().all()

    summary = _summarize_quality_rows([dict(row) for row in rows])
    return {
        "profile_id": runtime.profile_id,
        "profile_snapshot_id": runtime.profile_snapshot_id,
        "trader_ids": trader_ids,
        "author_ids": author_ids,
        **summary,
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
