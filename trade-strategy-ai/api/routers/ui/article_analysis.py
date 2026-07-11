from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from api.schemas import (
    ArticleAnalysisDetailResponse,
    ArticleProcessingStatusResponse,
    PromoteExtractionItemRequest,
    RepairRuleCandidateRequest,
    ReviewExtractionItemRequest,
    RunArticleAnalysisRequest,
    UpdateArticleProcessingStatusRequest,
)
from src.db.session import get_session_factory as async_session_factory
from src.models.blog_article import BlogArticle
from src.services import article_processing_state_service as article_processing_state
from src.services.stage3_regression_service import Stage3RegressionService
from src.services.stage3_single_article_service import Stage3SingleArticleError, Stage3SingleArticleService

router = APIRouter(prefix="/api/ui/v1/article-analysis", tags=["ui-article-analysis"])


def _structured_error(code: str, message: str, status_value: str, fields: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "status": status_value,
        "fields": fields or {},
    }


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

    return Stage3SingleArticleService(
        session_scope_factory=_session_scope,
        regression_service=Stage3RegressionService(session_scope_factory=_session_scope),
    )


def _display_fields(item) -> tuple[str, str]:
    payload = item.taxonomy_payload or {}
    title = next(
        (
            str(payload[key])
            for key in ("title", "candidate_rule_summary", "hypothesis_statement", "term_or_phrase", "data_name")
            if payload.get(key)
        ),
        str(item.primary_type),
    )
    summary = next(
        (
            str(payload[key])
            for key in ("plain_language_interpretation", "risk_action", "data_description", "reason", "source_experience")
            if payload.get(key)
        ),
        title,
    )
    return title, summary


def _build_article_analysis_response(journey) -> dict[str, Any]:
    prompt_run = journey.prompt_run
    structure = journey.structure
    structure_payload = structure.payload if structure is not None else {}
    claims = structure_payload.get("key_claims") or []
    explicit_claims = [claim for claim in claims if claim.get("source") == "explicit"]
    inferred_claims = [claim for claim in claims if claim.get("source") != "explicit"]
    summary = {
        "total": len(journey.extraction_items),
        "by_primary_type": {},
        "by_destination": {},
        "by_quality_state": {},
        "by_review_state": {},
    }
    for item in journey.extraction_items:
        for key, value in (
            ("by_primary_type", str(item.primary_type)),
            ("by_destination", str(item.review_destination)),
            ("by_quality_state", str(item.quality_state)),
            ("by_review_state", str(item.review_state)),
        ):
            summary[key][value] = summary[key].get(value, 0) + 1

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
        taxonomy_version=(journey.extraction_items[0].taxonomy_version if journey.extraction_items else None),
        extraction_summary=summary,
        extraction_items=[
            {
                "item_id": str(item.extraction_item_id),
                "item_index": item.item_index,
                "article_id": str(item.article_id),
                "article_revision_id": str(item.article_revision_id) if item.article_revision_id else None,
                "article_structure_id": str(item.article_structure_id),
                "prompt_run_id": str(item.prompt_run_id),
                "primary_type": str(item.primary_type),
                "secondary_tags": item.secondary_tags or [],
                "display_title": _display_fields(item)[0],
                "display_summary": _display_fields(item)[1],
                "source_evidence": item.source_evidence or {},
                "taxonomy_payload": item.taxonomy_payload or {},
                "confidence": item.confidence or {},
                "quality_state": str(item.quality_state),
                "review_destination": str(item.review_destination),
                "review_state": str(item.review_state),
                "backtest_eligibility": journey.eligibilities[item.extraction_item_id].__dict__,
                "promotion_eligibility": journey.eligibilities[item.extraction_item_id].__dict__,
                "provenance": item.provenance or {},
                "rule_version_id": str(journey.rule_versions[item.extraction_item_id].rule_version_id)
                if item.extraction_item_id in journey.rule_versions else None,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in journey.extraction_items
        ],
    ).model_dump(mode="json")


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


@router.post(
    "/articles/{article_id}/extraction-items/{item_id}/repair",
    response_model=ArticleAnalysisDetailResponse,
)
async def repair_article_rule_candidate(
    article_id: UUID,
    item_id: UUID,
    request: RepairRuleCandidateRequest,
    service: Stage3SingleArticleService = Depends(get_stage3_single_article_service),
    principal: CurrentPrincipal = Depends(require_role("operator")),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        journey = await service.repair_rule_candidate(
            article_id=article_id,
            item_id=item_id,
            repaired_payload=request.repaired_payload,
            source_quote=request.source_quote,
            rationale=request.rationale,
            actor_id=str(principal.api_key_label or principal.role),
            article_revision_id=UUID(request.article_revision_id) if request.article_revision_id else None,
        )
    except Stage3SingleArticleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_structured_error("rule_candidate_repair_failed", str(exc), "error"),
        ) from exc
    return _build_article_analysis_response(journey)


@router.post(
    "/articles/{article_id}/extraction-items/{item_id}/promote",
    response_model=ArticleAnalysisDetailResponse,
)
async def promote_article_executable_item(
    article_id: UUID,
    item_id: UUID,
    request: PromoteExtractionItemRequest,
    service: Stage3SingleArticleService = Depends(get_stage3_single_article_service),
    principal: CurrentPrincipal = Depends(require_role("operator")),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        journey = await service.promote_executable_item(
            article_id=article_id,
            item_id=item_id,
            actor_id=str(principal.api_key_label or principal.role),
            article_revision_id=UUID(request.article_revision_id) if request.article_revision_id else None,
        )
    except Stage3SingleArticleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_structured_error("executable_item_promotion_failed", str(exc), "error"),
        ) from exc
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
        unavailable = "LLM is not configured" in detail
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE if unavailable else status.HTTP_400_BAD_REQUEST,
            detail=_structured_error(
                "article_analysis_unavailable" if unavailable else "article_analysis_failed",
                detail,
                "unavailable" if unavailable else "error",
            ),
        ) from exc
    article_processing_state.clear_article_processing_state(str(article_id), path=article_processing_state.PROCESSING_STATE_PATH)
    return _build_article_analysis_response(journey)


@router.post("/articles/{article_id}/processing-status", response_model=ArticleProcessingStatusResponse)
async def update_article_processing_status(
    article_id: UUID,
    request: UpdateArticleProcessingStatusRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    session_factory = async_session_factory()
    async with session_factory() as session:
        article = await session.get(BlogArticle, article_id)
        if article is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_structured_error("article_not_found", f"article not found: {article_id}", "error"),
            )

    record = article_processing_state.set_article_processing_state(
        str(article_id),
        processing_status=request.action,
        processing_updated_by=str(principal.api_key_label or principal.role),
        processing_note=request.note,
        path=article_processing_state.PROCESSING_STATE_PATH,
    )
    return ArticleProcessingStatusResponse.model_validate({"article_id": str(article_id), **record}).model_dump(mode="json")


@router.post("/articles/{article_id}/extraction-items/{item_id}/review", response_model=ArticleAnalysisDetailResponse)
async def review_article_extraction_item(
    article_id: UUID,
    item_id: UUID,
    request: ReviewExtractionItemRequest,
    service: Stage3SingleArticleService = Depends(get_stage3_single_article_service),
    principal: CurrentPrincipal = Depends(require_role("operator")),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        journey = await service.review_extraction_item(
            article_id=article_id,
            article_revision_id=UUID(request.article_revision_id) if request.article_revision_id else None,
            item_id=item_id,
            decision=request.decision,
            actor_id=str(principal.api_key_label or principal.role),
            reason=request.reason,
        )
    except Stage3SingleArticleError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=_structured_error("extraction_item_review_failed", detail, "error"),
        ) from exc
    return _build_article_analysis_response(journey)
