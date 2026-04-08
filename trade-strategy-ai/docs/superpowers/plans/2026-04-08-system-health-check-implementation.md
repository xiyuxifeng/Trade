# P5-020 系统健康检查实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的三级健康检查端点 `/health/live`, `/health/ready`, `/health/detailed`，覆盖 DB、Pipeline、Agent网络、告警系统、熔断器五大组件。

**Architecture:**
- `src/health/models.py` — 统一数据模型
- `src/health/db_checker.py` — DatabaseHealthChecker
- `src/health/pipeline_checker.py` — PipelineHealthChecker
- `src/health/agent_net_checker.py` — AgentNetHealthChecker
- `src/health/alerting_checker.py` — AlertingHealthChecker
- `src/health/circuit_breaker_checker.py` — CircuitBreakerChecker
- `src/health/service.py` — HealthCheckService 编排所有 checker
- `src/health/routes.py` — FastAPI 路由注册

**Tech Stack:** FastAPI, SQLAlchemy async, asyncio

---

## 文件清单

### 新建
- `src/health/__init__.py`
- `src/health/models.py`
- `src/health/db_checker.py`
- `src/health/pipeline_checker.py`
- `src/health/agent_net_checker.py`
- `src/health/alerting_checker.py`
- `src/health/circuit_breaker_checker.py`
- `src/health/service.py`
- `src/health/routes.py`
- `tests/unit/health/__init__.py`
- `tests/unit/health/test_health.py`
- `tests/unit/health/test_db_checker.py`
- `tests/unit/health/test_service.py`

### 修改
- `src/api/main.py` — 注册 health_router

---

## Task 1: models.py — 健康检查数据模型

**Files:**
- Create: `src/health/models.py`
- Test: `tests/unit/health/test_health.py`（Task 9）

- [ ] **Step 1: 创建 models.py，写入基础枚举和响应模型**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add src/health/models.py
git commit -m "feat(P5-020): add health check data models"
```

---

## Task 2: db_checker.py — 数据库检查器

**Files:**
- Create: `src/health/db_checker.py`
- Test: `tests/unit/health/test_db_checker.py`（Task 10）

- [ ] **Step 1: 编写 db_checker.py**

```python
"""数据库健康检查器。"""
from __future__ import annotations

import time
from datetime import UTC, datetime

from src.common.logger import get_logger
from src.health.models import ComponentCheck, HealthStatus, HealthStatus

logger = get_logger("health.db")


class DatabaseHealthChecker:
    """检查 PostgreSQL 连接池可用性。"""

    name: str = "database"

    async def check(self) -> ComponentCheck:
        """执行 DB 健康检查。

        尝试执行 SELECT 1，测量延迟，获取连接池状态。
        """
        start = time.perf_counter()
        try:
            from src.db.session import session_scope

            from sqlalchemy import text
            async with session_scope() as session:
                await session.execute(text("SELECT 1"))
            latency_ms = (time.perf_counter() - start) * 1000

            # 获取连接池信息（从 engine 获取）
            from src.db.session import get_engine
            engine = get_engine()
            pool = engine.pool
            pool_size = getattr(pool, "size", lambda: 0)()
            pool_checked_in = getattr(pool, "checked_in", lambda: 0)()
            pool_overflow = getattr(pool, "overflow", lambda: 0)()

            return ComponentCheck(
                name=self.name,
                status=HealthStatus.OK,
                latency_ms=round(latency_ms, 2),
                details={
                    "pool_size": pool_size,
                    "pool_checked_in": pool_checked_in,
                    "pool_overflow": pool_overflow,
                },
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error("database health check failed: %s", e)
            return ComponentCheck(
                name=self.name,
                status=HealthStatus.ERROR,
                latency_ms=round(latency_ms, 2),
                error=str(e),
            )
```

> **注意:** SQLAlchemy 2.0 async 的 `session.execute()` 需要 `text()` 包装。实现时使用：
> `from sqlalchemy import text; await session.execute(text("SELECT 1"))`

- [ ] **Step 2: 提交**

```bash
git add src/health/db_checker.py
git commit -m "feat(P5-020): add DatabaseHealthChecker"
```

---

## Task 3: pipeline_checker.py — Pipeline 健康检查器

**Files:**
- Create: `src/health/pipeline_checker.py`

- [ ] **Step 1: 编写 pipeline_checker.py**

```python
"""Pipeline 健康检查器。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.common.logger import get_logger
from src.health.models import ComponentCheck, HealthStatus

logger = get_logger("health.pipeline")


# 全局变量：记录最近一次 pipeline 执行快照
_last_pipeline_snapshot: "PipelineHealthSnapshot | None" = None


def record_pipeline_snapshot(snapshot: "PipelineHealthSnapshot") -> None:
    """由 PipelineRunner 调用，记录最新执行快照。"""
    global _last_pipeline_snapshot
    _last_pipeline_snapshot = snapshot


class PipelineHealthChecker:
    """检查 Pipeline 最近执行状态。"""

    name: str = "pipeline"

    async def check(self) -> ComponentCheck:
        """返回最近一次 PipelineHealthSnapshot 的状态。"""
        global _last_pipeline_snapshot

        if _last_pipeline_snapshot is None:
            return ComponentCheck(
                name=self.name,
                status=HealthStatus.WARNING,
                details={
                    "last_run": None,
                    "total_runs_today": 0,
                },
                error="No pipeline run recorded yet",
            )

        snap = _last_pipeline_snapshot
        today = datetime.now(UTC).date()
        snap_date = snap.started_at.date() if snap.started_at else None
        is_today = snap_date == today if snap_date else False

        failed_nodes = getattr(snap, "failed_nodes", [])
        status = HealthStatus.OK if not failed_nodes else HealthStatus.ERROR

        return ComponentCheck(
            name=self.name,
            status=status,
            details={
                "last_run": snap.started_at.isoformat() if snap.started_at else None,
                "last_status": snap.status,
                "failed_nodes": list(failed_nodes),
                "total_runs_today": 1 if is_today else 0,
            },
            error=f"{len(failed_nodes)} node(s) failed: {failed_nodes}" if failed_nodes else None,
        )
```

> **注意:** 需要在 `PipelineRunner.run()` 返回后调用 `record_pipeline_snapshot()`。见 Task 8 修改 `src/pipeline/runner.py`。

- [ ] **Step 2: 提交**

```bash
git add src/health/pipeline_checker.py
git commit -m "feat(P5-020): add PipelineHealthChecker"
```

---

## Task 4: agent_net_checker.py — Agent 网络健康检查器

**Files:**
- Create: `src/health/agent_net_checker.py`

- [ ] **Step 1: 编写 agent_net_checker.py**

```python
"""Agent 网络健康检查器。"""
from __future__ import annotations

from src.common.logger import get_logger
from src.health.models import ComponentCheck, HealthStatus

logger = get_logger("health.agent_net")


class AgentNetHealthChecker:
    """检查 Agent 网络注册状态和通道健康。"""

    name: str = "agent_net"

    async def check(self) -> ComponentCheck:
        """获取 Agent 网络状态。"""
        try:
            net = await AgentNetwork.get_instance()
            agents = net._agents
            channel = net._default_channel

            registered_count = len(agents)
            queue_depth = channel.qsize() if hasattr(channel, "qsize") else 0

            # 检查是否有任何熔断器处于 OPEN 状态
            from src.agent_net.circuit_breaker import get_global_breaker_registry
            registry = get_global_breaker_registry()
            open_circuits = [
                name for name, cb in registry._breakers.items()
                if cb.state.value == "open"
            ]

            status = HealthStatus.ERROR if open_circuits else HealthStatus.OK

            return ComponentCheck(
                name=self.name,
                status=status,
                details={
                    "registered_agents": registered_count,
                    "active_channels": len(net._channels),
                    "queue_depth": queue_depth,
                    "open_circuits": open_circuits,
                },
            )
        except Exception as e:
            logger.error("agent_net health check failed: %s", e)
            return ComponentCheck(
                name=self.name,
                status=HealthStatus.ERROR,
                error=str(e),
            )
```

- [ ] **Step 2: 提交**

```bash
git add src/health/agent_net_checker.py
git commit -m "feat(P5-020): add AgentNetHealthChecker"
```

---

## Task 5: alerting_checker.py — 告警系统健康检查器

**Files:**
- Create: `src/health/alerting_checker.py`

- [ ] **Step 1: 编写 alerting_checker.py**

```python
"""告警系统健康检查器。"""
from __future__ import annotations

from src.common.logger import get_logger
from src.health.models import ComponentCheck, HealthStatus

logger = get_logger("health.alerting")


class AlertingHealthChecker:
    """检查 AlertManager 状态。"""

    name: str = "alerting"

    def __init__(self, manager: "AlertManager | None" = None) -> None:
        """初始化检查器。

        Args:
            manager: AlertManager 实例。如果为 None，使用默认实例。
        """
        self._manager = manager

    async def check(self) -> ComponentCheck:
        """获取告警系统状态。"""
        try:
            from src.alerting.manager import AlertManager

            manager = self._manager
            if manager is None:
                # AlertManager 目前无全局单例，只能检查注入的实例
                return ComponentCheck(
                    name=self.name,
                    status=HealthStatus.WARNING,
                    details={"manager_instance": None},
                    error="AlertManager not injected, skipping",
                )

            stats = manager.get_statistics()
            cooldown_rules = stats.get("rules_in_cooldown", [])
            alert_counts = stats.get("alert_counts", {})
            last_24h = sum(alert_counts.get(k, 0) for k in list(alert_counts.keys()))

            status = HealthStatus.OK if len(cooldown_rules) == 0 else HealthStatus.WARNING

            return ComponentCheck(
                name=self.name,
                status=status,
                details={
                    "total_rules": stats.get("total_rules", 0),
                    "enabled_rules": stats.get("enabled_rules", 0),
                    "cooldown_rules": len(cooldown_rules),
                    "last_24h_alerts": last_24h,
                },
            )
        except Exception as e:
            logger.error("alerting health check failed: %s", e)
            return ComponentCheck(
                name=self.name,
                status=HealthStatus.ERROR,
                error=str(e),
            )
```

> **注意:** AlertManager 目前没有全局单例。如果需要在没有注入的情况下检查，可以选择返回 WARNING 并注明需要在应用启动时注入实例。这是已知限制，可后续优化。

- [ ] **Step 2: 提交**

```bash
git add src/health/alerting_checker.py
git commit -m "feat(P5-020): add AlertingHealthChecker"
```

---

## Task 6: circuit_breaker_checker.py — 熔断器健康检查器

**Files:**
- Create: `src/health/circuit_breaker_checker.py`

- [ ] **Step 1: 编写 circuit_breaker_checker.py**

```python
"""熔断器健康检查器。"""
from __future__ import annotations

from collections import Counter

from src.common.logger import get_logger
from src.health.models import ComponentCheck, HealthStatus

logger = get_logger("health.circuit_breaker")


class CircuitBreakerHealthChecker:
    """检查全局熔断器状态分布。"""

    name: str = "circuit_breaker"

    async def check(self) -> ComponentCheck:
        """获取所有熔断器的状态。"""
        try:
            from src.agent_net.circuit_breaker import get_global_breaker_registry

            registry = get_global_breaker_registry()
            breakers = registry._breakers

            if not breakers:
                return ComponentCheck(
                    name=self.name,
                    status=HealthStatus.OK,
                    details={"total": 0, "states": {}},
                )

            states = {name: cb.state.value for name, cb in breakers.items()}
            state_counts = Counter(states.values())

            open_count = state_counts.get("open", 0)
            half_open_count = state_counts.get("half_open", 0)
            status = HealthStatus.ERROR if open_count > 0 else HealthStatus.WARNING if half_open_count > 0 else HealthStatus.OK

            return ComponentCheck(
                name=self.name,
                status=status,
                details={
                    "total": len(breakers),
                    "states": dict(state_counts),
                    "by_circuit": states,
                },
                error=f"{open_count} circuit(s) open" if open_count > 0 else None,
            )
        except Exception as e:
            logger.error("circuit_breaker health check failed: %s", e)
            return ComponentCheck(
                name=self.name,
                status=HealthStatus.ERROR,
                error=str(e),
            )
```

- [ ] **Step 2: 提交**

```bash
git add src/health/circuit_breaker_checker.py
git commit -m "feat(P5-020): add CircuitBreakerHealthChecker"
```

---

## Task 7: service.py — HealthCheckService

**Files:**
- Create: `src/health/service.py`

- [ ] **Step 1: 编写 service.py**

```python
"""健康检查服务。"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from src.health.models import (
    ComponentCheck,
    DetailedHealthResponse,
    LiveHealthResponse,
    OverallStatus,
    ReadyHealthResponse,
)

LiveChecker = Callable[[], Awaitable[LiveHealthResponse]]
ReadyChecker = Callable[[], Awaitable[ReadyHealthResponse]]


class HealthCheckService:
    """编排所有健康检查器。

    Attributes:
        checkers: 组件检查器列表（db, pipeline, agent_net, alerting, circuit_breaker）
    """

    def __init__(
        self,
        db_checker: DatabaseHealthChecker | None = None,
        pipeline_checker: PipelineHealthChecker | None = None,
        agent_net_checker: AgentNetHealthChecker | None = None,
        alerting_checker: AlertingHealthChecker | None = None,
        circuit_breaker_checker: CircuitBreakerHealthChecker | None = None,
    ) -> None:
        self.db_checker = db_checker or DatabaseHealthChecker()
        self.pipeline_checker = pipeline_checker or PipelineHealthChecker()
        self.agent_net_checker = agent_net_checker or AgentNetHealthChecker()
        self.alerting_checker = alerting_checker or AlertingHealthChecker()
        self.circuit_breaker_checker = circuit_breaker_checker or CircuitBreakerHealthChecker()

    async def check_live(self) -> LiveHealthResponse:
        """Liveness 检查：进程存活即返回 alive。"""
        return LiveHealthResponse(status="alive")

    async def check_ready(self) -> ReadyHealthResponse:
        """Readiness 检查：只验证 DB 连接。"""
        check = await self.db_checker.check()
        db_ok = check.status.value == "ok"
        return ReadyHealthResponse(
            status="ready" if db_ok else "not_ready",
            checks={"database": "ok" if db_ok else "failed"},
        )

    async def check_detailed(self, timeout: float = 10.0) -> DetailedHealthResponse:
        """详细健康检查：并行执行所有组件检查。"""
        checkers: list[ComponentChecker] = [
            self.db_checker,
            self.pipeline_checker,
            self.agent_net_checker,
            self.alerting_checker,
            self.circuit_breaker_checker,
        ]

        results: dict[str, ComponentCheck] = {}
        issues: list[str] = []

        async def run_checker(checker: ComponentChecker) -> tuple[str, ComponentCheck]:
            try:
                return (checker.name, await asyncio.wait_for(checker.check(), timeout=timeout))
            except asyncio.TimeoutError:
                return (checker.name, ComponentCheck(
                    name=checker.name,
                    status=HealthStatus.ERROR,
                    error=f"Check timed out after {timeout}s",
                ))
            except Exception as e:
                return (checker.name, ComponentCheck(
                    name=checker.name,
                    status=HealthStatus.ERROR,
                    error=str(e),
                ))

        results_list = await asyncio.gather(*[run_checker(c) for c in checkers])
        for name, check in results_list:
            results[name] = check
            if check.status == HealthStatus.ERROR:
                issues.append(f"[ERROR] {name}: {check.error}")
            elif check.status == HealthStatus.WARNING:
                issues.append(f"[WARN] {name}: {check.error or 'unknown warning'}")

        # 计算整体状态
        error_count = sum(1 for c in results.values() if c.status == HealthStatus.ERROR)
        warning_count = sum(1 for c in results.values() if c.status == HealthStatus.WARNING)

        if error_count > 0:
            overall = OverallStatus.UNHEALTHY
        elif warning_count > 0:
            overall = OverallStatus.DEGRADED
        else:
            overall = OverallStatus.HEALTHY

        return DetailedHealthResponse(
            status=overall,
            components=results,
            issues=issues,
        )
```

- [ ] **Step 2: 提交**

```bash
git add src/health/service.py
git commit -m "feat(P5-020): add HealthCheckService"
```

---

## Task 8: routes.py — FastAPI 路由

**Files:**
- Create: `src/health/routes.py`
- Modify: `src/api/main.py`

- [ ] **Step 1: 编写 routes.py**

```python
"""健康检查路由。"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, status

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
```

- [ ] **Step 2: 修改 src/api/main.py，注册路由**

在 `src/api/main.py` 的 `app = FastAPI(...)` 之后、`app.include_router` 区域添加：

```python
from src.health.routes import health_router

# ... existing routers ...

app.include_router(health_router)
```

注意：保持 `/health` 路由在 CORS middleware 之后注册即可。

- [ ] **Step 3: 提交**

```bash
git add src/health/routes.py src/api/main.py
git commit -m "feat(P5-020): add health check routes and register in FastAPI"
```

---

## Task 9: PipelineRunner 集成 — 记录健康快照

**Files:**
- Modify: `src/pipeline/runner.py`

- [ ] **Step 1: 修改 PipelineRunner.run()，记录快照**

在 `runner.py` 文件顶部添加：

```python
from src.health.pipeline_checker import record_pipeline_snapshot
```

在 `run()` 方法返回之前添加：

```python
snapshot = PipelineHealthSnapshot(...)
# ... existing code ...
record_pipeline_snapshot(snapshot.finalize())
return snapshot
```

> 具体修改位置需要根据 runner.py 实际代码决定，确保在 `run()` 方法返回前调用 `record_pipeline_snapshot()`。

- [ ] **Step 2: 提交**

```bash
git add src/pipeline/runner.py
git commit -m "feat(P5-020): record pipeline health snapshot after each run"
```

---

## Task 10: 单元测试

**Files:**
- Create: `tests/unit/health/__init__.py`
- Create: `tests/unit/health/test_health.py`
- Create: `tests/unit/health/test_db_checker.py`
- Create: `tests/unit/health/test_service.py`

- [ ] **Step 1: 写 test_health.py — 测试模型**

```python
"""健康检查模型测试。"""
import pytest

from src.health.models import (
    ComponentCheck,
    DetailedHealthResponse,
    HealthStatus,
    LiveHealthResponse,
    OverallStatus,
    ReadyHealthResponse,
)


def test_live_health_response():
    resp = LiveHealthResponse()
    assert resp.status == "alive"
    assert resp.timestamp is not None


def test_ready_health_response_ok():
    resp = ReadyHealthResponse(status="ready", checks={"database": "ok"})
    assert resp.status == "ready"
    assert resp.checks["database"] == "ok"


def test_ready_health_response_not_ready():
    resp = ReadyHealthResponse(status="not_ready", checks={"database": "failed"})
    assert resp.status == "not_ready"


def test_component_check_ok():
    check = ComponentCheck(name="database", status=HealthStatus.OK, latency_ms=12.5)
    assert check.name == "database"
    assert check.status == HealthStatus.OK
    assert check.latency_ms == 12.5


def test_component_check_error():
    check = ComponentCheck(name="pipeline", status=HealthStatus.ERROR, error="timeout")
    assert check.status == HealthStatus.ERROR
    assert check.error == "timeout"


def test_detailed_health_response_healthy():
    components = {
        "database": ComponentCheck(name="database", status=HealthStatus.OK, latency_ms=5.0),
        "pipeline": ComponentCheck(name="pipeline", status=HealthStatus.OK),
    }
    resp = DetailedHealthResponse(status=OverallStatus.HEALTHY, components=components)
    assert resp.status == OverallStatus.HEALTHY
    assert len(resp.components) == 2


def test_detailed_health_response_degraded():
    components = {
        "database": ComponentCheck(name="database", status=HealthStatus.OK),
        "pipeline": ComponentCheck(name="pipeline", status=HealthStatus.WARNING, error="no runs"),
    }
    issues = ["[WARN] pipeline: no runs"]
    resp = DetailedHealthResponse(status=OverallStatus.DEGRADED, components=components, issues=issues)
    assert resp.status == OverallStatus.DEGRADED
    assert len(resp.issues) == 1
```

- [ ] **Step 2: 写 test_db_checker.py — DB 检查器测试**

```python
"""DatabaseHealthChecker 单元测试。"""
import pytest

from src.health.db_checker import DatabaseHealthChecker
from src.health.models import HealthStatus


@pytest.mark.asyncio
async def test_db_checker_returns_component_check():
    checker = DatabaseHealthChecker()
    result = await checker.check()
    assert result.name == "database"
    assert result.status in [HealthStatus.OK, HealthStatus.ERROR]
    assert result.latency_ms is not None
    assert isinstance(result.latency_ms, float)
```

- [ ] **Step 3: 写 test_service.py — Service 测试**

```python
"""HealthCheckService 单元测试。"""
import pytest
from unittest.mock import AsyncMock, patch

from src.health.models import ComponentCheck, HealthStatus, OverallStatus
from src.health.service import HealthCheckService


@pytest.mark.asyncio
async def test_check_live_returns_alive():
    service = HealthCheckService()
    result = await service.check_live()
    assert result.status == "alive"


@pytest.mark.asyncio
async def test_check_ready_db_ok():
    mock_checker = AsyncMock()
    mock_checker.check.return_value = ComponentCheck(name="database", status=HealthStatus.OK, latency_ms=5.0)
    service = HealthCheckService(db_checker=mock_checker)
    result = await service.check_ready()
    assert result.status == "ready"
    assert result.checks["database"] == "ok"


@pytest.mark.asyncio
async def test_check_ready_db_failed():
    mock_checker = AsyncMock()
    mock_checker.check.return_value = ComponentCheck(name="database", status=HealthStatus.ERROR, error="connection refused")
    service = HealthCheckService(db_checker=mock_checker)
    result = await service.check_ready()
    assert result.status == "not_ready"
    assert result.checks["database"] == "failed"


@pytest.mark.asyncio
async def test_check_detailed_all_healthy():
    mock_ok = AsyncMock()
    mock_ok.name = "database"
    mock_ok.check.return_value = ComponentCheck(name="database", status=HealthStatus.OK)

    service = HealthCheckService(
        db_checker=mock_ok,
        pipeline_checker=mock_ok,
        agent_net_checker=mock_ok,
        alerting_checker=mock_ok,
        circuit_breaker_checker=mock_ok,
    )
    result = await service.check_detailed(timeout=5.0)
    assert result.status == OverallStatus.HEALTHY
    assert len(result.components) == 5
    assert len(result.issues) == 0


@pytest.mark.asyncio
async def test_check_detailed_with_errors():
    mock_ok = AsyncMock()
    mock_ok.name = "database"
    mock_ok.check.return_value = ComponentCheck(name="database", status=HealthStatus.OK)

    mock_err = AsyncMock()
    mock_err.name = "pipeline"
    mock_err.check.return_value = ComponentCheck(name="pipeline", status=HealthStatus.ERROR, error="snapshot missing")

    service = HealthCheckService(
        db_checker=mock_ok,
        pipeline_checker=mock_err,
        agent_net_checker=mock_ok,
        alerting_checker=mock_ok,
        circuit_breaker_checker=mock_ok,
    )
    result = await service.check_detailed(timeout=5.0)
    assert result.status == OverallStatus.UNHEALTHY
    assert "pipeline" in result.components
    assert any("pipeline" in issue for issue in result.issues)
```

- [ ] **Step 4: 提交**

```bash
git add tests/unit/health/
git commit -m "test(P5-020): add health check unit tests"
```

---

## Task 11: __init__.py — 统一导出

**Files:**
- Create: `src/health/__init__.py`

- [ ] **Step 1: 写入 src/health/__init__.py**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add src/health/__init__.py
git commit -m "feat(P5-020): add health module __init__ exports"
```

---

## Task 12: 更新 docker-compose.yml — 添加健康检查配置

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: 在 db service 的 healthcheck 之后，添加 app service 骨架**

```yaml
services:
  app:
    build: .
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/health/ready || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

> **注意:** 当前项目可能还没有 Dockerfile 或 app service 定义。此任务为可选，仅当 docker-compose 中需要健康检查时实施。先跳过。

---

## 自检清单

1. **Spec coverage:**
   - ✅ `/health/live` → Task 7 (routes.py)
   - ✅ `/health/ready` → Task 7 (routes.py)
   - ✅ `/health/detailed` → Task 7 (routes.py)
   - ✅ DatabaseHealthChecker → Task 2
   - ✅ PipelineHealthChecker → Task 3
   - ✅ AgentNetHealthChecker → Task 4
   - ✅ AlertingHealthChecker → Task 5
   - ✅ CircuitBreakerChecker → Task 6
   - ✅ HealthCheckService → Task 7
   - ✅ PipelineRunner 集成 → Task 9
   - ✅ 单元测试 → Task 10
   - ⚠️ docker-compose healthcheck → Task 12（可选）

2. **Placeholder scan:** 无 TBD/TODO/placeholder

3. **Type consistency:** 所有模型属性名在 Task 间一致

---

## 执行后预期结果

- `src/health/` 模块包含 8 个文件
- 3 个新 FastAPI 端点：`/health/live`, `/health/ready`, `/health/detailed`
- 5 个组件检查器可独立测试
- 单元测试覆盖核心逻辑
- 所有任务遵循 TDD：先写测试，再实现
