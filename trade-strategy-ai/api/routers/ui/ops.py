from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
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


def _raise_service_error(result: Any, *, default_message: str) -> None:
    """把服务层错误映射为 HTTP 错误。"""
    detail = result.message or default_message
    raise HTTPException(status_code=400, detail=detail)


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
    result = await service.create_backup(include_processed=request.include_processed, backup_dir=request.backup_dir)
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
    result = await service.restore_backup(
        backup_path=request.backup_path,
        include_processed=request.include_processed,
        confirmed=request.confirmed,
    )
    if result.status != "ok":
        _raise_service_error(result, default_message="restore failed")
    return result.payload


__all__ = ["get_ops_recovery_service", "router"]
