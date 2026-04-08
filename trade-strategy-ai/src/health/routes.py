"""健康检查路由。"""
from __future__ import annotations

from fastapi import APIRouter

from src.health.models import DetailedHealthResponse, LiveHealthResponse, ReadyHealthResponse
from src.health.service import HealthCheckService


health_router = APIRouter(prefix="/health", tags=["health"])

# 全局 HealthCheckService 实例
_service: HealthCheckService | None = None


def get_service() -> HealthCheckService:
    """获取或创建 HealthCheckService 单例。"""
    global _service
    if _service is None:
        _service = HealthCheckService()
    return _service


@health_router.get("/live", response_model=LiveHealthResponse)
async def health_live() -> LiveHealthResponse:
    """Liveness probe — 进程存活即返回 alive。"""
    return await get_service().check_live()


@health_router.get("/ready", response_model=ReadyHealthResponse)
async def health_ready() -> ReadyHealthResponse:
    """Readiness probe — 检查 DB 连接是否就绪。"""
    return await get_service().check_ready()


@health_router.get("/detailed", response_model=DetailedHealthResponse)
async def health_detailed() -> DetailedHealthResponse:
    """详细健康检查 — 所有组件状态。"""
    return await get_service().check_detailed()
