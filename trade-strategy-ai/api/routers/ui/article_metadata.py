from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select

from api.dependencies import CurrentPrincipal, get_current_principal, require_role, verify_api_key
from api.schemas import (
    ArticleAnalysisDetailResponse,
    ArticleMetadataListItemResponse,
    ArticleMetadataListResponse,
    ArticleMetadataResolutionListResponse,
    ArticleMetadataResolutionResponse,
    ArticleMetadataSelectRequest,
    ReviewCandidateRequest,
    RunArticleAnalysisRequest,
)
from src.db.session import get_session_factory as async_session_factory
from src.models.blog_article import BlogArticle
from src.models.article_metadata_selection import ArticleMetadataSelection
from src.services.article_metadata_selection_service import ArticleMetadataSelectionService
from src.services.stage3_single_article_service import Stage3SingleArticleError, Stage3SingleArticleService


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


def get_stage3_single_article_service() -> Stage3SingleArticleService:
    session_factory = async_session_factory()

    @asynccontextmanager
    async def _session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return Stage3SingleArticleService(session_scope_factory=_session_scope)


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


def _bool_contains_kaipan(payload: Any) -> bool:
    if isinstance(payload, str):
        return "kaipan" in payload.lower()
    if isinstance(payload, list):
        return any(_bool_contains_kaipan(item) for item in payload)
    if isinstance(payload, dict):
        return any(_bool_contains_kaipan(item) for item in payload.values())
    return False


def _build_article_analysis_response(journey) -> dict[str, Any]:
    prompt_run = journey.prompt_run
    structure = journey.structure
    structure_payload = structure.payload if structure is not None else {}
    claims = structure_payload.get("key_claims") or []
    explicit_claims = [claim for claim in claims if claim.get("source") == "explicit"]
    inferred_claims = [claim for claim in claims if claim.get("source") != "explicit"]

    return ArticleAnalysisDetailResponse(
        status=journey.status,
        message=journey.message,
        article={
            "article_id": str(journey.article.id),
            "article_revision_id": str(journey.revision.article_revision_id),
            "content_hash": journey.revision.content_hash,
            "title": journey.article.title,
            "source": journey.article.source,
            "source_url": journey.article.source_url,
            "author_name": journey.article.author_name,
            "author_id": journey.article.author_id,
            "published_at": journey.article.published_at,
            "crawled_at": journey.article.crawled_at,
            "original_text": journey.article.content_text,
            "cleaned_content": journey.revision.content_text,
            "summary": journey.summary_provenance.summary,
            "tags": journey.article.tags,
        },
        summary_provenance={
            "source": journey.summary_provenance.source,
            "article_revision_id": journey.summary_provenance.article_revision_id,
            "content_hash": journey.summary_provenance.content_hash,
            "available": journey.summary_provenance.available,
            "aligned": journey.summary_provenance.aligned,
            "reason": journey.summary_provenance.reason,
        },
        article_structure_provenance={
            "article_structure_id": journey.article_structure_provenance.article_structure_id,
            "article_revision_id": journey.article_structure_provenance.article_revision_id,
            "prompt_run_id": journey.article_structure_provenance.prompt_run_id,
            "prompt_name": journey.article_structure_provenance.prompt_name,
            "prompt_version": journey.article_structure_provenance.prompt_version,
            "schema_name": journey.article_structure_provenance.schema_name,
            "schema_version": journey.article_structure_provenance.schema_version,
            "available": journey.article_structure_provenance.available,
        },
        method_tags=(structure_payload.get("method_tags") or []) if structure is not None else [],
        explicit_facts=explicit_claims,
        hypotheses=inferred_claims + list(structure.inference_fields.get("items") or []) if structure is not None else [],
        missing_fields=structure.missing_fields if structure is not None else {},
        prompt_trace={
            "run_id": prompt_run.run_id if prompt_run is not None else None,
            "prompt_name": prompt_run.prompt_name if prompt_run is not None else None,
            "prompt_version": prompt_run.prompt_version if prompt_run is not None else None,
            "schema_name": prompt_run.schema_name if prompt_run is not None else None,
            "schema_version": prompt_run.schema_version if prompt_run is not None else None,
            "provider": prompt_run.provider if prompt_run is not None else None,
            "model": prompt_run.model if prompt_run is not None else None,
            "validation_state": str(prompt_run.validation_state) if prompt_run is not None else None,
            "retry_count": prompt_run.retry_count if prompt_run is not None else 0,
            "token_usage": prompt_run.token_usage if prompt_run is not None else {},
            "cost_amount": float(prompt_run.cost_amount) if prompt_run is not None and prompt_run.cost_amount is not None else None,
            "cost_currency": prompt_run.cost_currency if prompt_run is not None else None,
            "started_at": prompt_run.started_at if prompt_run is not None else None,
            "completed_at": prompt_run.completed_at if prompt_run is not None else None,
        },
        candidates=[
            {
                "candidate_id": str(candidate.rule_candidate_id),
                "candidate_index": candidate.candidate_index,
                "title": str((candidate.canonical_payload or {}).get("title") or f"candidate-{candidate.candidate_index}"),
                "rule_type": candidate.rule_type,
                "explicit_facts": candidate.explicit_fields or {},
                "hypotheses": candidate.inferred_fields or {},
                "missing_fields": candidate.missing_fields or {},
                "evidence": candidate.evidence_json or {},
                "data_dependencies": candidate.data_dependencies or {},
                "backtestability_status": candidate.backtestability_status,
                "kaipan_dependency": _bool_contains_kaipan(candidate.data_dependencies or {}),
                "market_state_declaration_status": str(
                    ((candidate.canonical_payload or {}).get("market_state_applicability") or {}).get("status") or "not_declared"
                ),
                "automatic_review": {
                    "status": journey.automatic_reviews[candidate.rule_candidate_id].status,
                    "reasons": journey.automatic_reviews[candidate.rule_candidate_id].reasons,
                    "risk_level": journey.automatic_reviews[candidate.rule_candidate_id].risk_level,
                },
                "human_review": {
                    "review_state": str(candidate.review_state),
                    "formal_rule_created": candidate.rule_candidate_id in journey.rule_versions,
                    "rule_version_id": str(journey.rule_versions[candidate.rule_candidate_id].rule_version_id)
                    if candidate.rule_candidate_id in journey.rule_versions
                    else None,
                    "formal_lifecycle_state": str(journey.rule_versions[candidate.rule_candidate_id].lifecycle_state)
                    if candidate.rule_candidate_id in journey.rule_versions
                    else None,
                    "stage3_status": "pending_backtest" if candidate.rule_candidate_id in journey.rule_versions else None,
                },
            }
            for candidate in journey.candidates
        ],
    ).model_dump(mode="json")


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


@router.get("/articles/{article_id}/analysis", response_model=ArticleAnalysisDetailResponse)
async def get_article_analysis(
    article_id: UUID,
    article_revision_id: UUID | None = Query(default=None),
    service: Stage3SingleArticleService = Depends(get_stage3_single_article_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        journey = await service.get_journey(article_id=article_id, article_revision_id=article_revision_id)
    except Stage3SingleArticleError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=_structured_error("article_analysis_unavailable", detail, "error")) from exc
    return _build_article_analysis_response(journey)


@router.post("/articles/{article_id}/analysis", response_model=ArticleAnalysisDetailResponse)
async def run_article_analysis(
    article_id: UUID,
    request: RunArticleAnalysisRequest,
    service: Stage3SingleArticleService = Depends(get_stage3_single_article_service),
    principal: CurrentPrincipal = Depends(require_role("operator")),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    del principal
    try:
        journey = await service.run_analysis(
            article_id=article_id,
            article_revision_id=UUID(request.article_revision_id) if request.article_revision_id else None,
        )
    except Stage3SingleArticleError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_structured_error("article_analysis_failed", detail, "error"),
        ) from exc
    return _build_article_analysis_response(journey)


@router.post("/articles/{article_id}/candidates/{candidate_id}/review", response_model=ArticleAnalysisDetailResponse)
async def review_article_candidate(
    article_id: UUID,
    candidate_id: UUID,
    request: ReviewCandidateRequest,
    service: Stage3SingleArticleService = Depends(get_stage3_single_article_service),
    principal: CurrentPrincipal = Depends(require_role("operator")),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        journey = await service.review_candidate(
            article_id=article_id,
            article_revision_id=UUID(request.article_revision_id) if request.article_revision_id else None,
            candidate_id=candidate_id,
            decision=request.decision,
            actor_id=str(principal.api_key_label or principal.role),
            reason=request.reason,
        )
    except Stage3SingleArticleError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=_structured_error("article_candidate_review_failed", detail, "error"),
        ) from exc
    return _build_article_analysis_response(journey)


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
