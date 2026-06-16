from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import get_current_principal, verify_api_key
from src.db.session import get_session_factory as async_session_factory
from src.services.rule_lifecycle_service import (
    LifecycleAction,
    LifecycleView,
    RuleLifecycleError,
    RuleLifecycleService,
    RuleLifecycleStaleWriteError,
    RuleLifecycleTransitionBlockedError,
)
from src.services.stage3_regression_service import Stage3RegressionService


router = APIRouter(prefix="/api/ui/v1/rule-lifecycle", tags=["ui-rule-lifecycle"])


class LifecycleActionResponse(BaseModel):
    key: str
    label: str
    requires_reason: bool
    requires_evidence: bool


class LifecycleViewResponse(BaseModel):
    object_type: str
    object_id: str
    canonical_state: str
    display_state: str | None = None
    display_label: str | None = None
    status: str
    status_message: str | None = None
    restriction_message: str | None = None
    correlation_id: str | None = None
    updated_at: datetime
    allowed_next_actions: list[LifecycleActionResponse] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LifecycleHistoryResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)


class RuleLifecycleTransitionRequest(BaseModel):
    target_state: str
    reason: str | None = None
    correlation_id: str
    expected_updated_at: datetime | None = None
    evidence_refs: list[str] = Field(default_factory=list)


def _serialize_action(action: LifecycleAction) -> dict[str, Any]:
    return {
        "key": action.key,
        "label": action.label,
        "requires_reason": action.requires_reason,
        "requires_evidence": action.requires_evidence,
    }


def _serialize_view(view: LifecycleView) -> dict[str, Any]:
    return LifecycleViewResponse(
        object_type=view.object_type,
        object_id=view.object_id,
        canonical_state=view.canonical_state,
        display_state=view.display_state,
        display_label=view.display_label,
        status=view.status,
        status_message=view.status_message,
        restriction_message=view.restriction_message,
        correlation_id=view.correlation_id,
        updated_at=view.updated_at,
        allowed_next_actions=[LifecycleActionResponse.model_validate(_serialize_action(action)) for action in view.allowed_next_actions],
        metadata=view.metadata,
    ).model_dump(mode="json")


def get_rule_lifecycle_service() -> RuleLifecycleService:
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

    return RuleLifecycleService(
        session_scope_factory=_session_scope,
        regression_service=Stage3RegressionService(session_scope_factory=_session_scope),
    )


@router.get("/rule-versions/{rule_version_id}", response_model=LifecycleViewResponse)
async def get_rule_version_lifecycle(
    rule_version_id: str,
    service: RuleLifecycleService = Depends(get_rule_lifecycle_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return _serialize_view(await service.get_rule_version_lifecycle(rule_version_id=rule_version_id))
    except RuleLifecycleError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/rule-versions/{rule_version_id}/history", response_model=LifecycleHistoryResponse)
async def list_rule_version_history(
    rule_version_id: str,
    service: RuleLifecycleService = Depends(get_rule_lifecycle_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    return {"items": await service.list_rule_version_history(rule_version_id=rule_version_id)}


@router.post("/rule-versions/{rule_version_id}/transition", response_model=LifecycleViewResponse)
async def transition_rule_version(
    rule_version_id: str,
    request: RuleLifecycleTransitionRequest,
    principal=Depends(get_current_principal),
    service: RuleLifecycleService = Depends(get_rule_lifecycle_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    actor_id = getattr(principal, "api_key_label", None) or getattr(principal, "role", "anonymous")
    try:
        view = await service.transition_rule_version(
            rule_version_id=rule_version_id,
            target_state=request.target_state,
            actor_type="human",
            actor_id=actor_id,
            reason=request.reason,
            correlation_id=request.correlation_id,
            expected_updated_at=request.expected_updated_at,
            evidence_refs=request.evidence_refs,
        )
    except RuleLifecycleStaleWriteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"status": "stale_write", "message": str(exc)},
        ) from exc
    except RuleLifecycleTransitionBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"status": "blocked", "message": str(exc)},
        ) from exc
    except RuleLifecycleError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _serialize_view(view)
