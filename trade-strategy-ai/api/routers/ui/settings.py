from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from src.common.paths import resolve_project_path
from src.services.config_edit_service import ConfigEditService, get_config_edit_service


router = APIRouter(prefix="/api/ui/v1/settings", tags=["ui-settings"])


class SettingsDraftRequest(BaseModel):
    """配置草稿校验请求。"""

    config_path: str | None = None
    draft: dict[str, Any] = Field(default_factory=dict)


class SettingsSaveRequest(BaseModel):
    """配置保存请求。"""

    config_path: str | None = None
    draft: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False


class SettingsRestoreRequest(BaseModel):
    """配置恢复请求。"""

    config_path: str | None = None
    backup_path: str
    confirmed: bool = False


def _config_path(value: str | None = None) -> Path:
    """解析 settings API 使用的配置路径。"""
    return resolve_project_path(value or os.environ.get("CONFIG_PATH", "config/app.yaml"))


def _project_root() -> Path:
    """返回项目根目录。"""
    return resolve_project_path(None)


def _backups_root() -> Path:
    """返回配置备份目录。"""
    return resolve_project_path("data/backups")


def _is_within(path: Path, root: Path) -> bool:
    """判断路径是否位于指定根目录下。"""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _ensure_managed_config_path(value: str | None) -> Path:
    """只允许管理项目根目录下的配置文件。"""
    resolved = _config_path(value)
    if not _is_within(resolved, _project_root()):
        raise HTTPException(status_code=400, detail="config path must stay within project root")
    return resolved


def _ensure_managed_backup_path(value: str) -> Path:
    """只允许恢复备份目录下的文件。"""
    resolved = _config_path(value)
    if not _is_within(resolved, _backups_root()):
        raise HTTPException(status_code=400, detail="backup path must stay within backup root")
    return resolved


def _raise_service_error(result: Any, *, default_message: str) -> None:
    """把服务层错误映射为 HTTP 错误。"""
    detail = result.message or default_message
    status_code = 409 if detail == "config edit locked" else 400
    raise HTTPException(status_code=status_code, detail=detail)


@router.get("/config", dependencies=[Depends(verify_api_key)])
async def get_config(
    config_path: str | None = Query(default=None),
    service: ConfigEditService = Depends(get_config_edit_service),
) -> dict[str, Any]:
    """返回脱敏后的当前配置。"""
    result = service.get_current_config(_ensure_managed_config_path(config_path))
    if result.status != "ok":
        _raise_service_error(result, default_message="config load failed")
    return result.payload


@router.get("/schema", dependencies=[Depends(verify_api_key)])
async def get_schema(
    config_path: str | None = Query(default=None),
    service: ConfigEditService = Depends(get_config_edit_service),
) -> dict[str, Any]:
    """返回配置编辑 schema。"""
    result = service.get_edit_schema(_ensure_managed_config_path(config_path))
    if result.status != "ok":
        _raise_service_error(result, default_message="schema load failed")
    return result.payload


@router.post("/validate", dependencies=[Depends(verify_api_key)])
async def validate(
    request: SettingsDraftRequest,
    service: ConfigEditService = Depends(get_config_edit_service),
) -> dict[str, Any]:
    """校验配置草稿并返回 diff。"""
    result = service.validate_draft(_ensure_managed_config_path(request.config_path), request.draft)
    if result.status != "ok":
        _raise_service_error(result, default_message="validation failed")
    return result.payload


@router.post("/save", dependencies=[Depends(verify_api_key)])
async def save(
    request: SettingsSaveRequest,
    service: ConfigEditService = Depends(get_config_edit_service),
    _role_principal: CurrentPrincipal = Depends(require_role("admin")),
) -> dict[str, Any]:
    """保存配置，保存前要求确认。"""
    result = service.save_config(_ensure_managed_config_path(request.config_path), request.draft, confirmed=request.confirmed)
    if result.status != "ok":
        _raise_service_error(result, default_message="save failed")
    return result.payload


@router.get("/backups", dependencies=[Depends(verify_api_key)])
async def list_backups(
    config_path: str | None = Query(default=None),
    service: ConfigEditService = Depends(get_config_edit_service),
) -> dict[str, Any]:
    """列出当前配置的备份。"""
    result = service.list_backups(_ensure_managed_config_path(config_path))
    if result.status != "ok":
        _raise_service_error(result, default_message="backup listing failed")
    return result.payload


@router.post("/restore", dependencies=[Depends(verify_api_key)])
async def restore(
    request: SettingsRestoreRequest,
    service: ConfigEditService = Depends(get_config_edit_service),
    _role_principal: CurrentPrincipal = Depends(require_role("admin")),
) -> dict[str, Any]:
    """恢复配置备份，恢复前要求确认。"""
    result = service.restore_backup(
        _ensure_managed_config_path(request.config_path),
        _ensure_managed_backup_path(request.backup_path),
        confirmed=request.confirmed,
    )
    if result.status != "ok":
        _raise_service_error(result, default_message="restore failed")
    return result.payload


__all__ = ["get_config_edit_service", "router"]
