"""健康检查数据模型。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class HealthStatus(str, Enum):
    """组件健康状态。"""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class OverallStatus(str, Enum):
    """整体健康状态。"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ComponentCheck:
    """单个组件的检查结果。"""
    name: str
    status: HealthStatus
    latency_ms: float | None = None
    details: dict[str, object] = field(default_factory=dict)
    error: str | None = None


@dataclass(slots=True)
class LiveHealthResponse:
    """GET /health/live 响应。"""
    status: str = "alive"  # always "alive"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class ReadyHealthResponse:
    """GET /health/ready 响应。"""
    status: str  # "ready" | "not_ready"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    checks: dict[str, str] = field(default_factory=dict)  # component_name -> "ok" | "failed"


@dataclass(slots=True)
class DetailedHealthResponse:
    """GET /health/detailed 响应。"""
    status: OverallStatus
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    components: dict[str, ComponentCheck] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
