from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from src.db.session import get_session_factory as async_session_factory
from src.services.rule_review_service import RuleReviewError, RuleReviewService
from src.services.stage3_regression_service import Stage3RegressionService


router = APIRouter(prefix="/api/ui/v1/rule-review", tags=["ui-rule-review"])


class RuleReviewActionRequest(BaseModel):
    action: str
    reason: str
    correlation_id: str
    edits: dict[str, Any] = Field(default_factory=dict)


class RuleReviewBatchRequest(BaseModel):
    action: str
    reason: str
    correlation_id: str
    candidate_ids: list[str] = Field(default_factory=list)


def _serialize(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def get_rule_review_service() -> RuleReviewService:
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

    return RuleReviewService(
        session_scope_factory=_session_scope,
        regression_service=Stage3RegressionService(session_scope_factory=_session_scope),
    )


@router.get("/candidates")
async def list_rule_review_candidates(
    require_human_review_only: bool = Query(False),
    automatic_review_status: str | None = Query(default=None),
    service: RuleReviewService = Depends(get_rule_review_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    items = await service.list_candidates(
        require_human_review_only=require_human_review_only,
        automatic_review_status=automatic_review_status,
    )
    return {
        "count": len(items),
        "total": len(items),
        "items": _serialize(items),
    }


@router.get("/candidates/{candidate_id}")
async def get_rule_review_candidate(
    candidate_id: str,
    service: RuleReviewService = Depends(get_rule_review_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return _serialize(await service.get_candidate_detail(candidate_id=candidate_id))
    except RuleReviewError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/candidates/{candidate_id}/actions")
async def apply_rule_review_action(
    candidate_id: str,
    request: RuleReviewActionRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    del candidate_id, request, principal
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "status": "retired_read_only",
            "message": "旧 rule_candidates 仅保留为审计证据；请从文章分类抽取结果处理新项目。",
        },
    )


@router.post("/candidates/batch-actions")
async def apply_rule_review_batch_action(
    request: RuleReviewBatchRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    del request, principal
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "status": "retired_read_only",
            "message": "旧 rule_candidates 批量写入路径已停用；历史记录保持只读。",
        },
    )
