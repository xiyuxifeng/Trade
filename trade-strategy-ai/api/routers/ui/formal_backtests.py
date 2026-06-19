from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from src.db.session import get_session_factory as async_session_factory
from src.services.backtest_application_service import (
    BacktestApplicationService,
    BacktestResultView,
    BacktestRunCreateRequest,
    BacktestRunView,
    BacktestSelection,
)


router = APIRouter(prefix="/api/ui/v1/rules/backtests", tags=["ui-formal-backtests"])


class FormalBacktestCreateRequest(BaseModel):
    selection: BacktestSelection
    reason: str | None = None
    accept_downgrade: bool = False
    accepted_effective_level: str | None = None


class FormalApplicabilityDraftRequest(BaseModel):
    result_id: str | None = None
    reason: str | None = None


class FormalApplicabilityReviewRequest(BaseModel):
    review_status: str
    reason: str | None = None


def get_backtest_application_service() -> BacktestApplicationService:
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

    return BacktestApplicationService(session_scope_factory=_session_scope)


def _actor_id(principal: CurrentPrincipal) -> str:
    return principal.api_key_label or principal.role or "anonymous"


def _serialize(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


@router.post("/dependency-check")
async def check_formal_backtest_dependencies(
    selection: BacktestSelection,
    principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: BacktestApplicationService = Depends(get_backtest_application_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    result = await service.check_dependencies(
        selection,
        actor_id=_actor_id(principal),
        actor_role=principal.role,
    )
    return _serialize(result)


@router.post("/runs", status_code=status.HTTP_201_CREATED)
async def create_formal_backtest_run(
    request: FormalBacktestCreateRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: BacktestApplicationService = Depends(get_backtest_application_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result = await service.create_run(
            BacktestRunCreateRequest(
                selection=request.selection,
                actor_id=_actor_id(principal),
                actor_role=principal.role,
                reason=request.reason,
                source_surface="/rules/backtests",
                accept_downgrade=request.accept_downgrade,
                accepted_effective_level=request.accepted_effective_level,
            )
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"status": "blocked", "message": str(exc)}) from exc
    return _serialize(result)


@router.get("/runs/{run_id}")
async def get_formal_backtest_run(
    run_id: str,
    principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: BacktestApplicationService = Depends(get_backtest_application_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result: BacktestRunView = await service.get_run(
            run_id,
            actor_id=_actor_id(principal),
            actor_role=principal.role,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到正式回测记录") from exc
    return _serialize(result)


@router.post("/runs/{run_id}/execute")
async def execute_formal_backtest_run(
    run_id: str,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: BacktestApplicationService = Depends(get_backtest_application_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result: BacktestResultView = await service.execute_run(
            run_id,
            actor_id=_actor_id(principal),
            actor_role=principal.role,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到正式回测记录") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"status": "blocked", "message": str(exc)}) from exc
    return _serialize(result)


@router.get("/runs/{run_id}/result")
async def get_formal_backtest_result(
    run_id: str,
    principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: BacktestApplicationService = Depends(get_backtest_application_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result: BacktestResultView = await service.get_result(
            run_id,
            actor_id=_actor_id(principal),
            actor_role=principal.role,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到正式回测结果") from exc
    return _serialize(result)


@router.post("/runs/{run_id}/applicability-profiles", status_code=status.HTTP_201_CREATED)
async def generate_formal_applicability_profile_draft(
    run_id: str,
    request: FormalApplicabilityDraftRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: BacktestApplicationService = Depends(get_backtest_application_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result = await service.generate_applicability_draft(
            run_id,
            request.result_id,
            actor_id=_actor_id(principal),
            actor_role=principal.role,
            reason=request.reason,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到可生成画像的正式回测证据") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"status": "blocked", "message": str(exc)}) from exc
    return _serialize(result)


@router.post("/applicability-profiles/{profile_id}/review")
async def review_formal_applicability_profile(
    profile_id: str,
    request: FormalApplicabilityReviewRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: BacktestApplicationService = Depends(get_backtest_application_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result = await service.review_applicability_profile(
            profile_id,
            request.review_status,
            actor_id=_actor_id(principal),
            actor_role=principal.role,
            reason=request.reason,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到适用性画像") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"status": "blocked", "message": str(exc)}) from exc
    return _serialize(result)
