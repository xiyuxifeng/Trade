from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends

from api.dependencies import verify_api_key
from src.common.config import load_app_config
from src.common.paths import resolve_project_path
from src.services.system_service import SystemService

router = APIRouter(prefix="/api/ui/v1/system", tags=["ui-system"])
legacy_router = APIRouter(prefix="/api/ui/system", tags=["ui-system-legacy"])


def get_system_service() -> SystemService:
    """构建系统服务。"""
    return SystemService()


def _config_path() -> Path:
    """返回当前 API 使用的配置文件路径。"""
    return resolve_project_path(os.environ.get("CONFIG_PATH", "config/app.yaml"))


def _profile_context() -> dict[str, str | None]:
    """返回当前进程显式绑定的 Profile 上下文。

    系统状态本身并不推断 Profile，只读取启动时显式注入的环境变量，避免把
    config_path 误当成 Profile 事实源。
    """
    profile_id = os.environ.get("PROFILE_ID") or os.environ.get("ACTIVE_PROFILE_ID")
    profile_snapshot_id = os.environ.get("PROFILE_SNAPSHOT_ID") or os.environ.get("ACTIVE_PROFILE_SNAPSHOT_ID")
    profile_id = profile_id.strip() if isinstance(profile_id, str) and profile_id.strip() else None
    profile_snapshot_id = profile_snapshot_id.strip() if isinstance(profile_snapshot_id, str) and profile_snapshot_id.strip() else None
    source = "env" if profile_id or profile_snapshot_id else "unset"
    return {
        "profile_id": profile_id,
        "profile_snapshot_id": profile_snapshot_id,
        "source": source,
    }


@router.get("/status")
async def get_system_status(_: str = Depends(verify_api_key)) -> dict[str, object]:
    """返回系统、数据库和关键目录状态。"""
    return await _build_system_status()


@router.get("/dashboard")
async def get_system_dashboard(
    service: SystemService = Depends(get_system_service),
    _: str = Depends(verify_api_key),
) -> dict[str, object]:
    """返回运维 Dashboard 摘要。"""
    result = await service.build_dashboard_summary(config_path=_config_path())
    return result.payload


@legacy_router.get("/status")
async def get_legacy_system_status(_: str = Depends(verify_api_key)) -> dict[str, object]:
    """兼容旧版系统状态入口。"""
    return await _build_system_status()


async def _build_system_status() -> dict[str, object]:
    """构建系统状态响应体。"""
    config_path = _config_path()
    loaded = load_app_config(config_path)
    service = SystemService()

    db_result = await service.check_database()
    dir_result = service.check_key_directories(config_path)

    return {
        "status": "ok",
        "config_path": str(config_path),
        "profile_context": _profile_context(),
        "project_root": str(config_path.parent.parent if config_path.parent.name == "config" else config_path.parent),
        "run_mode": loaded.config.run_mode,
        "database": db_result.payload["database"],
        "directories": dir_result.payload["directories"],
        "warnings": dir_result.warnings,
    }
