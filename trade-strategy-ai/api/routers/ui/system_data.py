from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from api.dependencies import CurrentPrincipal, get_current_principal, require_role, verify_api_key
from src.services.data_scheduling_service import DataSchedulingService


router = APIRouter(prefix="/api/ui/v1/system/data", tags=["ui-system-data"])


class SystemDataOperationRequest(BaseModel):
    action: str
    profile_id: str | None = None
    target_trade_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    schedule_key: str | None = None


class OperationControlRequest(BaseModel):
    reason: str | None = None


def get_data_scheduling_service() -> DataSchedulingService:
    return DataSchedulingService()


def _audit_source(request: Request) -> dict[str, Any]:
    client_host = request.client.host if request.client is not None else None
    return {
        "channel": "ui",
        "path": request.url.path,
        "method": request.method,
        "client_host": client_host,
        "user_agent": request.headers.get("user-agent"),
    }


def _payload(result: Any) -> dict[str, Any]:
    if hasattr(result, "payload"):
        return result.payload
    return result


@router.get("/readiness")
async def get_system_data_readiness(
    service: DataSchedulingService = Depends(get_data_scheduling_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    return _payload(await service.get_readiness())


@router.get("/schedule")
async def get_system_data_schedule(
    service: DataSchedulingService = Depends(get_data_scheduling_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    return _payload(await service.build_schedule_summary())


@router.get("/operations")
async def list_system_data_operations(
    limit: int = 20,
    offset: int = 0,
    service: DataSchedulingService = Depends(get_data_scheduling_service),
    principal: CurrentPrincipal = Depends(get_current_principal),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    return _payload(await service.list_operations(limit=limit, offset=offset, actor_role=principal.role))


@router.post("/operations")
async def create_system_data_operation(
    payload: SystemDataOperationRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: DataSchedulingService = Depends(get_data_scheduling_service),
) -> dict[str, Any]:
    result = await service.submit_operation(
        action=payload.action,
        principal=principal,
        profile_id=payload.profile_id,
        target_trade_date=payload.target_trade_date,
        start_date=payload.start_date,
        end_date=payload.end_date,
        schedule_key=payload.schedule_key,
        audit_source=_audit_source(request),
    )
    return result.payload


@router.post("/operations/{operation_id}/cancel")
async def cancel_system_data_operation(
    operation_id: str,
    payload: OperationControlRequest,
    request: Request,
    _: CurrentPrincipal = Depends(require_role("operator")),
    service: DataSchedulingService = Depends(get_data_scheduling_service),
) -> dict[str, Any]:
    result = await service.cancel_operation(operation_id=operation_id, reason=payload.reason, audit_source=_audit_source(request))
    return result.payload


@router.post("/operations/{operation_id}/retry")
async def retry_system_data_operation(
    operation_id: str,
    payload: OperationControlRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: DataSchedulingService = Depends(get_data_scheduling_service),
) -> dict[str, Any]:
    del payload
    result = await service.retry_operation(
        operation_id=operation_id,
        actor=principal.api_key_label or principal.role,
        audit_source=_audit_source(request),
    )
    return result.payload


@router.post("/operations/{operation_id}/resume")
async def resume_system_data_operation(
    operation_id: str,
    request: Request,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: DataSchedulingService = Depends(get_data_scheduling_service),
) -> dict[str, Any]:
    result = await service.resume_operation(
        operation_id=operation_id,
        actor=principal.api_key_label or principal.role,
        audit_source=_audit_source(request),
    )
    return result.payload
