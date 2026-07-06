from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select

from api.dependencies import get_current_principal, verify_api_key
from api.schemas import (
    ArticleMetadataListItemResponse,
    ArticleMetadataListResponse,
    ArticleMetadataResolutionListResponse,
    ArticleMetadataResolutionResponse,
    ArticleMetadataSelectRequest,
)
from src.db.session import get_session_factory as async_session_factory
from src.models.blog_article import BlogArticle
from src.models.article_metadata_selection import ArticleMetadataSelection
from src.services.article_metadata_selection_service import ArticleMetadataSelectionService


router = APIRouter(prefix="/api/ui/v1/article-metadata", tags=["ui-article-metadata"])


def _structured_error(code: str, message: str, status_value: str, fields: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "status": status_value,
        "fields": fields or {},
    }


def get_article_metadata_selection_service() -> ArticleMetadataSelectionService:
    """获取文章元数据版本选择服务。"""
    return ArticleMetadataSelectionService()


def _selection_status_condition(selection_status: str):
    """将列表筛选状态映射为 SQL 条件。"""
    if selection_status == "selected":
        return ArticleMetadataSelection.selection_mode == "manual"
    if selection_status == "unselected":
        return or_(
            ArticleMetadataSelection.selection_mode.is_(None),
            ArticleMetadataSelection.selection_mode != "manual",
        )
    return None


def _search_condition(search: str | None):
    """构建文章列表搜索条件。"""
    if not search or not search.strip():
        return None
    term = f"%{search.strip()}%"
    return or_(
        BlogArticle.title.ilike(term),
        BlogArticle.author_name.ilike(term),
        BlogArticle.author_id.ilike(term),
        BlogArticle.source.ilike(term),
        BlogArticle.source_url.ilike(term),
        BlogArticle.summary.ilike(term),
    )


@router.get("/summary", response_model=ArticleMetadataResolutionListResponse)
async def list_article_metadata_summary(
    article_ids: list[UUID] = Query(default_factory=list),
    service: ArticleMetadataSelectionService = Depends(get_article_metadata_selection_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """批量返回文章元数据版本选择摘要。"""
    if not article_ids:
        return {"items": []}

    session_factory = async_session_factory()
    async with session_factory() as session:
        resolutions = await service.resolve_resolutions(
            session,
            article_ids=article_ids,
            persist_missing=True,
            selected_by="system",
        )
        await session.commit()
    items = [ArticleMetadataResolutionResponse.model_validate(resolution.to_dict()).model_dump(mode="json") for resolution in resolutions.values()]
    return {"items": items}


@router.get("/articles", response_model=ArticleMetadataListResponse)
async def list_article_metadata_articles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    selection_status: str = Query(default="all", pattern="^(all|selected|unselected)$"),
    search: str | None = None,
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """返回文章元数据版本选择的分页列表。"""
    offset = (page - 1) * page_size
    selection_condition = _selection_status_condition(selection_status)
    search_filter = _search_condition(search)

    session_factory = async_session_factory()
    async with session_factory() as session:
        base_query = (
            select(
                BlogArticle.id.label("article_id"),
                BlogArticle.title,
                BlogArticle.author_name,
                BlogArticle.author_id,
                BlogArticle.source,
                BlogArticle.source_url,
                BlogArticle.published_at,
                BlogArticle.crawled_at,
                BlogArticle.summary,
                BlogArticle.tags,
                ArticleMetadataSelection.selected_schema_version,
                ArticleMetadataSelection.selected_by,
                ArticleMetadataSelection.selected_at,
                ArticleMetadataSelection.selection_mode,
                ArticleMetadataSelection.selection_reason,
                ArticleMetadataSelection.recommended_schema_version,
            )
            .select_from(BlogArticle)
            .outerjoin(ArticleMetadataSelection, ArticleMetadataSelection.article_id == BlogArticle.id)
        )
        count_query = select(func.count(BlogArticle.id)).select_from(BlogArticle).outerjoin(
            ArticleMetadataSelection,
            ArticleMetadataSelection.article_id == BlogArticle.id,
        )

        if search_filter is not None:
            base_query = base_query.where(search_filter)
            count_query = count_query.where(search_filter)
        if selection_condition is not None:
            base_query = base_query.where(selection_condition)
            count_query = count_query.where(selection_condition)

        total_result = await session.execute(count_query)
        total = int(total_result.scalar() or 0)
        rows = (
            await session.execute(
                base_query.order_by(BlogArticle.published_at.desc(), BlogArticle.crawled_at.desc()).offset(offset).limit(page_size)
            )
        ).mappings().all()

    items = [
        ArticleMetadataListItemResponse.model_validate(
            {
                "article_id": str(row["article_id"]),
                "title": row["title"],
                "author_name": row["author_name"],
                "author_id": row["author_id"],
                "source": row["source"],
                "source_url": row["source_url"],
                "published_at": row["published_at"],
                "crawled_at": row["crawled_at"],
                "summary": row["summary"],
                "tags": row["tags"] or [],
                "selection_status": "selected" if row["selection_mode"] == "manual" else "unselected",
                "selected_schema_version": row["selected_schema_version"],
                "selected_by": row["selected_by"],
                "selected_at": row["selected_at"],
                "selection_mode": row["selection_mode"],
                "selection_reason": row["selection_reason"],
                "recommended_schema_version": row["recommended_schema_version"],
                "effective_schema_version": row["selected_schema_version"],
            }
        ).model_dump(mode="json")
        for row in rows
    ]

    pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/articles/{article_id}", response_model=ArticleMetadataResolutionResponse)
async def get_article_metadata_summary(
    article_id: UUID,
    service: ArticleMetadataSelectionService = Depends(get_article_metadata_selection_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """返回单篇文章的元数据版本选择摘要。"""
    session_factory = async_session_factory()
    async with session_factory() as session:
        article = await session.get(BlogArticle, article_id)
        if article is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_structured_error("article_not_found", f"article not found: {article_id}", "error"),
            )
        resolution = await service.resolve_resolution(
            session,
            article_id=article_id,
            persist_missing=True,
            selected_by="system",
        )
        await session.commit()
    return ArticleMetadataResolutionResponse.model_validate(resolution.to_dict()).model_dump(mode="json")


@router.post("/articles/{article_id}/select", response_model=ArticleMetadataResolutionResponse)
async def select_article_metadata_version(
    article_id: UUID,
    request: ArticleMetadataSelectRequest,
    service: ArticleMetadataSelectionService = Depends(get_article_metadata_selection_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """手动设置文章元数据的当前生效版本。"""
    session_factory = async_session_factory()
    async with session_factory() as session:
        article = await session.get(BlogArticle, article_id)
        if article is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_structured_error("article_not_found", f"article not found: {article_id}", "error"),
            )
        try:
            resolution = await service.select_version(
                session,
                article_id=article_id,
                selected_schema_version=request.selected_schema_version,
                selected_by=request.selected_by,
                selection_reason=request.selection_reason,
            )
            await session.commit()
        except ValueError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_structured_error("article_metadata_selection_failed", str(exc), "error"),
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive guard
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_structured_error("article_metadata_selection_failed", str(exc), "error"),
            ) from exc

    return ArticleMetadataResolutionResponse.model_validate(resolution.to_dict()).model_dump(mode="json")
