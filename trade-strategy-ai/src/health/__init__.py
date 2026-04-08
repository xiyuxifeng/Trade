"""系统健康检查模块。

提供三级健康检查端点：
- /health/live — 进程存活探活
- /health/ready — DB 就绪检查
- /health/detailed — 全量组件状态

用法:
    from src.health.routes import health_router
    app.include_router(health_router)
"""
from src.health.models import (
    ComponentCheck,
    DetailedHealthResponse,
    HealthStatus,
    LiveHealthResponse,
    OverallStatus,
    ReadyHealthResponse,
)
from src.health.service import HealthCheckService
from src.health.db_checker import DatabaseHealthChecker
from src.health.pipeline_checker import PipelineHealthChecker
from src.health.agent_net_checker import AgentNetHealthChecker
from src.health.alerting_checker import AlertingHealthChecker
from src.health.circuit_breaker_checker import CircuitBreakerHealthChecker

__all__ = [
    "HealthCheckService",
    "DatabaseHealthChecker",
    "PipelineHealthChecker",
    "AgentNetHealthChecker",
    "AlertingHealthChecker",
    "CircuitBreakerHealthChecker",
    "ComponentCheck",
    "DetailedHealthResponse",
    "HealthStatus",
    "LiveHealthResponse",
    "OverallStatus",
    "ReadyHealthResponse",
]
