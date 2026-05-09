from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends

from api.dependencies import verify_api_key
from src.common.paths import resolve_project_path
from src.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/ui/v1", tags=["ui-data-health"])


def _config_path() -> Path:
    """读取当前 UI BFF 使用的配置文件路径。"""
    return resolve_project_path(os.environ.get("CONFIG_PATH", "config/app.yaml"))


def get_dashboard_service() -> DashboardService:
    """构建 dashboard 服务。"""
    return DashboardService()


@router.get("/data-health/dashboard", dependencies=[Depends(verify_api_key)])
async def data_health_dashboard(service: DashboardService = Depends(get_dashboard_service)):
    """生成 dashboard HTML 并返回报告摘要。"""
    result = await service.build_report(config_path=_config_path(), mode="html")
    return result.payload

__all__ = ["get_dashboard_service", "router"]
