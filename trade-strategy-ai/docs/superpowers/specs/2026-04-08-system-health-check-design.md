# P5-020 系统健康检查设计

## 1. 背景与目标

为 Trade Strategy AI 系统实现完整的健康检查体系，满足 k8s/docker-compose 健康检查语义，并为运维和 Prometheus 监控提供详细状态接口。

**目标：**
1. 提供 k8s liveness / readiness / detailed 三级健康检查端点
2. 检查 DB 连接池、Pipeline 执行状态、Agent 网络状态、告警系统状态、熔断器状态
3. 所有检查操作有明确超时，不阻塞容器启动
4. 输出格式统一，可供 Prometheus 抓取

## 2. 端点设计

| 端点 | 用途 | 认证 | 超时 |
|------|------|------|------|
| `GET /health/live` | k8s livenessProbe | 无 | < 100ms |
| `GET /health/ready` | k8s readinessProbe | 无 | < 3s |
| `GET /health/detailed` | 运维详情 / Prometheus | 无 | < 10s |

### 2.1 /health/live

仅探活，返回即表示进程存活。

```json
{
  "status": "alive",
  "timestamp": "2026-04-08T10:30:00Z"
}
```

### 2.2 /health/ready

检查服务是否可接受流量。核心依赖不可用时返回 `not_ready`。

```json
{
  "status": "ready",
  "timestamp": "2026-04-08T10:30:00Z",
  "checks": {
    "database": "ok"
  }
}
```

- `status` = `"ready"` 或 `"not_ready"`
- 目前只检查 DB，未来可扩展

### 2.3 /health/detailed

运维详情，包含所有组件状态。

```json
{
  "status": "healthy",
  "timestamp": "2026-04-08T10:30:00Z",
  "components": {
    "database": {
      "status": "ok",
      "latency_ms": 12.5,
      "pool_size": 5,
      "checked_at": "2026-04-08T10:30:00Z"
    },
    "pipeline": {
      "status": "ok",
      "last_run": "2026-04-08T08:00:00Z",
      "last_status": "success",
      "failed_nodes": [],
      "total_runs_today": 3
    },
    "agent_net": {
      "status": "ok",
      "registered_agents": 4,
      "active_channels": 2,
      "circuit_breakers": {
        "data_agent": "closed",
        "knowledge_agent": "closed"
      }
    },
    "alerting": {
      "status": "ok",
      "total_rules": 10,
      "enabled_rules": 8,
      "cooldown_rules": 1,
      "last_24h_alerts": 3
    }
  },
  "issues": []
}
```

- `status` = `"healthy"`（所有组件 ok）、`"degraded"`（部分组件异常但核心可用）、`"unhealthy"`（核心组件不可用）
- `issues` 列表包含所有非 ok 组件的问题描述

## 3. 组件检查器设计

每个检查器实现统一的 `ComponentChecker` 接口：

```python
class ComponentChecker(Protocol):
    name: str

    async def check(self) -> ComponentCheck: ...


@dataclass(slots=True)
class ComponentCheck:
    name: str
    status: HealthStatus  # "ok" | "warning" | "error"
    latency_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
```

### 3.1 DatabaseHealthChecker

- 执行 `SELECT 1` 验证 DB 可达
- 记录查询延迟
- 记录连接池状态（从 `get_engine().pool.size()` 获取）

### 3.2 PipelineHealthChecker

- 读取最近一次 `PipelineHealthSnapshot`（从文件或内存）
- 检查 `failed_nodes` 是否为空
- 统计今日运行次数

> 注：当前 `PipelineHealthSnapshot` 存储在内存中，未来可扩展为持久化存储。

### 3.3 AgentNetHealthChecker

- 从 `AgentNetwork.get_instance()` 获取注册 agent 数
- 获取各 `CircuitBreaker` 的状态（通过 `CircuitBreakerRegistry`）
- 获取 channel 队列深度（`InMemoryChannel.qsize()`）

### 3.4 AlertingHealthChecker

- 获取 `AlertManager.get_statistics()`
- 统计启用规则数、冷却中规则数、最近 24h 告警数

### 3.5 CircuitBreakerChecker

- 从 `get_global_breaker_registry()` 获取所有熔断器
- 汇总各熔断器的状态分布

## 4. HealthCheckService

编排所有 checker，统一超时控制：

```python
class HealthCheckService:
    def __init__(self, checkers: list[ComponentChecker] | None = None):
        self._checkers = {c.name: c for c in (checkers or self._default_checkers())}

    async def check_live(self) -> LiveHealthResponse: ...

    async def check_ready(self) -> ReadyHealthResponse: ...

    async def check_detailed(self, timeout: float = 10.0) -> DetailedHealthResponse: ...
```

## 5. 文件结构

```
src/health/
    __init__.py                  # 统一导出
    models.py                    # HealthStatus, ComponentCheck, 各响应模型
    db_checker.py                # DatabaseHealthChecker
    pipeline_checker.py           # PipelineHealthChecker
    agent_net_checker.py          # AgentNetHealthChecker
    alerting_checker.py           # AlertingHealthChecker
    circuit_breaker_checker.py    # CircuitBreakerChecker
    service.py                   # HealthCheckService
    routes.py                    # FastAPI 路由注册

tests/unit/health/
    __init__.py
    test_health.py              # 路由测试
    test_db_checker.py          # DB 检查器测试
    test_service.py             # Service 集成测试
```

## 6. 注册路由

在 `src/api/main.py` 中注册：

```python
from src.health.routes import health_router

app.include_router(health_router)
```

## 7. 健康检查状态流转

```
/health/live        → always returns {"status": "alive"}
/health/ready       → DB check
                      ├─ ok     → status=ready
                      └─ error  → status=not_ready
/health/detailed    → all checks in parallel (with timeout)
                      ├─ all ok     → status=healthy
                      ├─ any error  → status=degraded or unhealthy
                      └─ all error  → status=unhealthy
```

## 8. 超时策略

| 端点 | 超时 | 降级行为 |
|------|------|----------|
| /health/live | 100ms | 超时也返回 alive（进程在跑） |
| /health/ready | 3s | 超时视为 DB 不可用，返回 not_ready |
| /health/detailed | 10s | 超时的组件标记为 error，单个组件超时不影响其他 |

## 9. 验证方式

1. `/health/live` 任意时刻返回 200
2. DB 断开时 `/health/ready` 返回 503
3. `/health/detailed` 包含所有 4 个组件的检查结果
4. 各检查器可独立单元测试
5. 所有端点 < 约定超时时间
