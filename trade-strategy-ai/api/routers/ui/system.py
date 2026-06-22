from __future__ import annotations

import os

from fastapi import APIRouter, Depends

from api.dependencies import verify_api_key
from api.dependencies import CurrentPrincipal, get_current_principal
from src.common.config import ConfigError
from src.services.config_profile_service import ConfigProfileService
from src.services.system_run_trace_service import SystemRunTraceService
from src.services.system_service import SystemService

router = APIRouter(prefix="/api/ui/v1/system", tags=["ui-system"])
legacy_router = APIRouter(prefix="/api/ui/system", tags=["ui-system-legacy"])


def get_system_service() -> SystemService:
    """构建系统服务。"""
    return SystemService()


def get_system_run_trace_service() -> SystemRunTraceService:
    """构建系统运行追踪服务。"""
    return SystemRunTraceService()


async def _resolve_profile_id() -> str | None:
    """解析当前 UI 应使用的 Profile ID。"""
    service = ConfigProfileService()
    return service.resolve_runtime_profile_id()


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
    runtime_profile_id = await _resolve_profile_id()
    result = await service.build_dashboard_summary(profile_id=runtime_profile_id)
    return result.payload


@router.get("/runs")
async def list_system_runs(
    limit: int = 20,
    service: SystemRunTraceService = Depends(get_system_run_trace_service),
    principal: CurrentPrincipal = Depends(get_current_principal),
    _: str = Depends(verify_api_key),
) -> dict[str, object]:
    """返回系统管理运行追踪视图。"""
    result = await service.list_run_traces(actor_role=principal.role, limit=limit)
    return result.payload


@legacy_router.get("/status")
async def get_legacy_system_status(_: str = Depends(verify_api_key)) -> dict[str, object]:
    """兼容旧版系统状态入口。"""
    return await _build_system_status()


async def _build_system_status() -> dict[str, object]:
    """构建系统状态响应体。"""
    profile_id = await _resolve_profile_id()
    try:
        runtime = await ConfigProfileService().load_profile_runtime_config(profile_id)
    except ConfigError:
        return {
            "status": "partial",
            "profile_context": _profile_context(),
            "profile_id": profile_id,
            "profile_snapshot_id": None,
            "project_root": None,
            "run_mode": None,
            "database": {
                "status": "unavailable",
                "message": "系统运行配置暂不可用，无法检查数据库状态。",
            },
            "directories": None,
            "warnings": ["系统运行配置暂不可用，无法确认数据库和目录状态。"],
        }
    service = SystemService()
    db_result = await service.check_database()
    dir_result = await service.check_key_directories(profile_id=profile_id)
    return {
        "status": "ok",
        "profile_context": _profile_context(),
        "profile_id": runtime.profile_id,
        "profile_snapshot_id": runtime.profile_snapshot_id,
        "project_root": str(runtime.base_dir),
        "run_mode": runtime.config.run_mode,
        "database": db_result.payload["database"],
        "directories": dir_result.payload["directories"],
        "warnings": dir_result.warnings,
    }
