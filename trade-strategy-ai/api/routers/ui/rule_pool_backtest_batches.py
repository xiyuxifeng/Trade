from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from src.db.session import get_session_factory as async_session_factory
from src.services.rule_pool_backtest_batch_service import RulePoolBacktestBatchService


router = APIRouter(prefix="/api/ui/v1/rules/backtests/batch-runs", tags=["ui-rule-pool-backtest-batches"])


class RulePoolBacktestBatchRunCreateRequest(BaseModel):
    rule_ids: list[str] = Field(min_length=1)
    batch_size: int = Field(default=30, ge=1, le=500)
    start_date: date
    end_date: date
    min_confidence: float = Field(default=0.7, ge=0, le=1)
    market_regime_version: str | None = "market-regime-v3"
    profile_id: str | None = None


def get_rule_pool_backtest_batch_service() -> RulePoolBacktestBatchService:
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

    return RulePoolBacktestBatchService(session_scope_factory=_session_scope)


def _actor_id(principal: CurrentPrincipal) -> str:
    return principal.api_key_label or principal.role or "anonymous"


def _handle_service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到规则池批量回测记录")
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"status": "blocked", "message": str(exc)})
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="规则池批量回测处理失败")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_rule_pool_batch_run(
    request: RulePoolBacktestBatchRunCreateRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: RulePoolBacktestBatchService = Depends(get_rule_pool_backtest_batch_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return await service.create_batch_run(
            rule_ids=request.rule_ids,
            batch_size=request.batch_size,
            start_date=request.start_date,
            end_date=request.end_date,
            min_confidence=request.min_confidence,
            market_regime_version=request.market_regime_version,
            profile_id=request.profile_id,
            created_by=_actor_id(principal),
        )
    except Exception as exc:
        raise _handle_service_error(exc) from exc


@router.get("")
async def list_rule_pool_batch_runs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: RulePoolBacktestBatchService = Depends(get_rule_pool_backtest_batch_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    return await service.list_batch_runs(skip=skip, limit=limit)


@router.get("/{batch_run_id}")
async def get_rule_pool_batch_run(
    batch_run_id: str,
    _principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: RulePoolBacktestBatchService = Depends(get_rule_pool_backtest_batch_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return await service.refresh_batch_status(batch_run_id)
    except Exception as exc:
        raise _handle_service_error(exc) from exc


@router.post("/{batch_run_id}/batches/{batch_index}/start")
async def start_rule_pool_batch(
    batch_run_id: str,
    batch_index: int,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: RulePoolBacktestBatchService = Depends(get_rule_pool_backtest_batch_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return await service.start_batch(batch_run_id, batch_index=batch_index, actor=_actor_id(principal))
    except Exception as exc:
        raise _handle_service_error(exc) from exc


@router.post("/{batch_run_id}/merge")
async def merge_rule_pool_batch_results(
    batch_run_id: str,
    _principal: CurrentPrincipal = Depends(require_role("operator")),
    service: RulePoolBacktestBatchService = Depends(get_rule_pool_backtest_batch_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return await service.merge_batch_results(batch_run_id)
    except Exception as exc:
        raise _handle_service_error(exc) from exc
