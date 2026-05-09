from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends

from api.dependencies import verify_api_key
from src.common.config import load_app_config
from src.common.paths import resolve_project_path
from src.services.system_service import SystemService

router = APIRouter(prefix="/api/ui/system", tags=["ui-system"])


def _config_path() -> Path:
    """返回当前 API 使用的配置文件路径。"""
    return resolve_project_path(os.environ.get("CONFIG_PATH", "config/app.yaml"))


@router.get("/status")
async def get_system_status(_: str = Depends(verify_api_key)) -> dict[str, object]:
    """返回系统、数据库和关键目录状态。"""
    config_path = _config_path()
    loaded = load_app_config(config_path)
    service = SystemService()

    db_result = await service.check_database()
    dir_result = service.check_key_directories(config_path)

    return {
        "status": "ok",
        "config_path": str(config_path),
        "project_root": str(config_path.parent.parent if config_path.parent.name == "config" else config_path.parent),
        "run_mode": loaded.config.run_mode,
        "database": db_result.payload["database"],
        "directories": dir_result.payload["directories"],
        "warnings": dir_result.warnings,
    }
