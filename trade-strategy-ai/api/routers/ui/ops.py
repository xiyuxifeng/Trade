from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from pydantic import BaseModel, Field

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from src.services.ops_service import OpsRecoveryService, get_ops_recovery_service


router = APIRouter(prefix="/api/ui/v1/ops", tags=["ui-ops"])


class OpsBackupRequest(BaseModel):
    """项目级备份请求。"""

    backup_dir: str | None = None
    include_processed: bool = True


class OpsRestoreRequest(BaseModel):
    """项目级恢复请求。"""

    backup_path: str
    include_processed: bool = True
    confirmed: bool = False


class OpsRecoverStaleRequest(BaseModel):
    """stale Job 回收请求。"""

    stale_before_minutes: int = Field(default=10, ge=1, le=1440)


def _raise_service_error(result: Any, *, default_message: str) -> None:
    """把服务层错误映射为 HTTP 错误。"""
    detail = result.message or default_message
    raise HTTPException(status_code=400, detail=detail)


def _handle_value_error(exc: ValueError) -> None:
    """把路径越界等参数错误映射为 400。"""
    raise HTTPException(status_code=400, detail=str(exc))


@router.get("/backups", dependencies=[Depends(verify_api_key)])
async def list_backups(service: OpsRecoveryService = Depends(get_ops_recovery_service)) -> dict[str, Any]:
    """列出项目级备份包。"""
    result = service.list_backups()
    if result.status != "ok":
        _raise_service_error(result, default_message="backup listing failed")
    return result.payload


@router.post("/backup", dependencies=[Depends(verify_api_key)])
async def create_backup(
    request: OpsBackupRequest,
    service: OpsRecoveryService = Depends(get_ops_recovery_service),
    _role_principal: CurrentPrincipal = Depends(require_role("admin")),
) -> dict[str, Any]:
    """创建项目级备份。"""
    try:
        result = await service.create_backup(include_processed=request.include_processed, backup_dir=request.backup_dir)
    except ValueError as exc:
        _handle_value_error(exc)
    if result.status != "ok":
        _raise_service_error(result, default_message="backup creation failed")
    return result.payload


@router.post("/restore", dependencies=[Depends(verify_api_key)])
async def restore_backup(
    request: OpsRestoreRequest,
    service: OpsRecoveryService = Depends(get_ops_recovery_service),
    _role_principal: CurrentPrincipal = Depends(require_role("admin")),
) -> dict[str, Any]:
    """恢复项目级备份。"""
    try:
        result = await service.restore_backup(
            backup_path=request.backup_path,
            include_processed=request.include_processed,
            confirmed=request.confirmed,
        )
    except ValueError as exc:
        _handle_value_error(exc)
    if result.status != "ok":
        _raise_service_error(result, default_message="restore failed")
    return result.payload


@router.post("/recover-stale", dependencies=[Depends(verify_api_key)])
async def recover_stale_jobs(
    request: OpsRecoverStaleRequest,
    service: OpsRecoveryService = Depends(get_ops_recovery_service),
    principal: CurrentPrincipal = Depends(require_role("admin")),
) -> dict[str, Any]:
    """回收 stale 的 running Job。"""
    result = await service.recover_stale_jobs(
        stale_before_minutes=request.stale_before_minutes,
        actor=principal.api_key_label or principal.role,
        audit_source={
            "channel": "ui",
            "path": "/api/ui/v1/ops/recover-stale",
            "method": "POST",
            "actor": principal.api_key_label or principal.role,
            "principal": principal.to_public_dict(),
        },
    )
    if result.status != "ok":
        _raise_service_error(result, default_message="stale recovery failed")
    return result.payload


__all__ = ["get_ops_recovery_service", "router"]
