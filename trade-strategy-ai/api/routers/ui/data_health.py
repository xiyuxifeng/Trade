from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends

from api.dependencies import verify_api_key
from src.services.config_profile_service import ConfigProfileService
from src.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/ui/v1", tags=["ui-data-health"])


def _profile_id() -> str:
    """读取当前 UI BFF 使用的 Profile。"""
    return ConfigProfileService().resolve_runtime_profile_id()


def get_dashboard_service() -> DashboardService:
    """构建 dashboard 服务。"""
    return DashboardService()


@router.get("/data-health/dashboard", dependencies=[Depends(verify_api_key)])
async def data_health_dashboard(service: DashboardService = Depends(get_dashboard_service)):
    """生成 dashboard HTML 并返回报告摘要。"""
    result = await service.build_report(profile_id=_profile_id(), mode="html")
    return result.payload

__all__ = ["get_dashboard_service", "router"]
