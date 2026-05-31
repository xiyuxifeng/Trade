from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import verify_api_key
from api.schemas import (
    ArticleMetadataResolutionListResponse,
    ArticleMetadataResolutionResponse,
    ArticleMetadataSelectRequest,
)
from src.db.session import get_session_factory as async_session_factory
from src.models.blog_article import BlogArticle
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
