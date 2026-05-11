# Web S9-003 Operational Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `trade-strategy-ai` 增加一个独立的运维 Dashboard 页面，用来展示最近失败任务、任务耗时、数据新鲜度、告警摘要和可追踪的 request/job 线索，同时保持 `Overview` 轻量。

**Architecture:** 复用现有 `/data-health` 路由作为独立 Dashboard 承载页，`Overview` 继续只展示入口级摘要。后端新增 `/api/ui/v1/system/dashboard`，由 `SystemService` 聚合 `HealthCheckService`、`JobService` 和现有 `DashboardService` 的结果，前端新增一个运维中心组件消费这组数据；现有 `Data Health` 报告接口保留，用作报告文件和 HTML 产物的辅助入口。

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, React, TanStack Query, TypeScript, Vite, shadcn/ui, pytest, Vitest.

---

### Task 1: 后端系统 Dashboard 聚合接口

**Files:**
- Modify: `src/services/system_service.py`
- Modify: `api/routers/ui/system.py`
- Create: `tests/unit/services/test_system_service_dashboard.py`
- Create: `tests/api/routers/ui/test_ui_system_dashboard.py`

- [ ] **Step 1: 写失败测试**

先写一个只验证聚合结果的单测。测试里把 `HealthCheckService`、`JobService` 和 `DashboardService` 都替换成假实现，确认 `SystemService.build_dashboard_summary()` 会把失败任务、运行中任务心跳、耗时统计、数据新鲜度和告警摘要拼成一个响应体。

```python
from dataclasses import dataclass
from src.health.models import ComponentCheck, DetailedHealthResponse, HealthStatus, OverallStatus
from src.services.base import ServiceResult


@dataclass
class FakeHealthService:
    async def check_detailed(self, timeout: float = 10.0) -> DetailedHealthResponse:
        return DetailedHealthResponse(
            status=OverallStatus.HEALTHY,
            components={
                "database": ComponentCheck(name="database", status=HealthStatus.OK, latency_ms=3.2),
            },
            issues=[],
        )


@dataclass
class FakeJobService:
    async def list_jobs(self, *, status=None, job_type=None, created_by=None, skip=0, limit=50) -> ServiceResult:
        if status == "failed":
            return ServiceResult(
                status="ok",
                message="jobs listed",
                payload={
                    "count": 1,
                    "total": 1,
                    "skip": 0,
                    "limit": limit,
                    "items": [{
                        "id": "job-failed-1",
                        "job_type": "run_after_close",
                        "status": "failed",
                        "started_at": "2026-05-11T09:00:00+00:00",
                        "finished_at": "2026-05-11T09:03:00+00:00",
                        "heartbeat_at": "2026-05-11T09:02:30+00:00",
                        "error": {"message": "boom"},
                        "audit_events": [{
                            "job_id": "job-failed-1",
                            "payload": {"request_context": {"path": "/api/ui/v1/jobs", "method": "POST"}},
                        }],
                    }],
                },
            )
        if status == "running":
            return ServiceResult(
                status="ok",
                message="jobs listed",
                payload={
                    "count": 1,
                    "total": 1,
                    "skip": 0,
                    "limit": limit,
                    "items": [{
                        "id": "job-running-1",
                        "job_type": "crawl",
                        "status": "running",
                        "started_at": "2026-05-11T09:05:00+00:00",
                        "finished_at": None,
                        "heartbeat_at": "2026-05-11T09:05:30+00:00",
                        "error": None,
                        "audit_events": [],
                    }],
                },
            )
        return ServiceResult(status="ok", message="jobs listed", payload={"count": 0, "total": 0, "skip": 0, "limit": limit, "items": []})


@dataclass
class FakeDashboardService:
    async def build_report(self, *, config_path, mode="cli", output=None) -> ServiceResult:
        return ServiceResult(
            status="ok",
            message="dashboard report built",
            payload={
                "config_path": str(config_path),
                "report": {
                    "source_freshness": [
                        {"source": "articles", "entity_type": "article", "freshness_hours": 1.5, "is_stale": False},
                        {"source": "market_data", "entity_type": "market", "freshness_hours": 24.0, "is_stale": True},
                    ],
                    "alerts": [
                        {"level": "critical", "title": "stale market data", "message": "market data is stale", "timestamp": "2026-05-11T09:00:00+00:00"},
                    ],
                },
                "html_path": None,
                "critical_alerts": 1,
                "exit_code": 1,
            },
        )
```

断言至少覆盖这些字段：

```python
result = await service.build_dashboard_summary()
assert result.status == "partial"
assert result.payload["health"]["database"]["status"] == "ok"
assert result.payload["worker"]["heartbeat_at"] == "2026-05-11T09:05:30+00:00"
assert result.payload["failed_jobs"][0]["id"] == "job-failed-1"
assert result.payload["duration_summary"]["average_seconds"] == 180.0
assert result.payload["freshness"]["sources"][1]["is_stale"] is True
assert result.payload["alerts"]["critical"] == 1
assert result.payload["traces"][0]["request_context"]["path"] == "/api/ui/v1/jobs"
```

- [ ] **Step 2: 先跑测试确认失败**

Run:

```bash
pytest -q tests/unit/services/test_system_service_dashboard.py tests/api/routers/ui/test_ui_system_dashboard.py
```

Expected: fail，因为 `build_dashboard_summary()` 和 `/api/ui/v1/system/dashboard` 还不存在。

- [ ] **Step 3: 实现最小后端聚合**

在 `src/services/system_service.py` 里给 `SystemService` 增加可注入依赖，并实现 `build_dashboard_summary()`。建议直接复用现成服务：

```python
class SystemService(BaseService):
    def __init__(
        self,
        db_checker: DatabaseHealthChecker | None = None,
        health_service: HealthCheckService | None = None,
        job_service: JobService | None = None,
        dashboard_service: DashboardService | None = None,
    ) -> None:
        self._db_checker = db_checker or DatabaseHealthChecker()
        self._health_service = health_service or HealthCheckService()
        self._job_service = job_service or JobService()
        self._dashboard_service = dashboard_service or DashboardService()

    async def build_dashboard_summary(self) -> ServiceResult:
        detailed = await self._health_service.check_detailed()
        failed_jobs = await self._job_service.list_jobs(status="failed", limit=10)
        running_jobs = await self._job_service.list_jobs(status="running", limit=20)
        success_jobs = await self._job_service.list_jobs(status="success", limit=20)
        dashboard_report = await self._dashboard_service.build_report(
            config_path="config/app.yaml",
            mode="cli",
        )
        return self._assemble_dashboard_summary(
            detailed=detailed,
            failed_jobs=failed_jobs.payload["items"],
            running_jobs=running_jobs.payload["items"],
            success_jobs=success_jobs.payload["items"],
            dashboard_report=dashboard_report.payload,
        )
```

聚合时的最小行为：

- `health` 使用 `HealthCheckService.check_detailed()`，保留数据库和系统健康状态
- `running` 和 `failed` Job 直接调用 `JobService.list_jobs()`
- `duration_summary` 由最近 `success` Job 的 `finished_at - started_at` 计算
- `freshness` 和 `alerts` 直接从 `DashboardService.build_report(mode="cli")` 的 `report` 里提取
- `traces` 从最近失败 Job 的 `audit_events` 中拿 `request_context`，至少暴露 `path`、`method`、`client_host` 和 `job_id`

在 `api/routers/ui/system.py` 中补一个依赖工厂：

```python
def get_system_service() -> SystemService:
    return SystemService()

@router.get("/dashboard")
async def get_system_dashboard(
    service: SystemService = Depends(get_system_service),
    _: str = Depends(verify_api_key),
) -> dict[str, object]:
    result = await service.build_dashboard_summary()
    return result.payload
```

`/status` 继续沿用现有逻辑，不要把 Dashboard 结果塞回基础健康检查。

- [ ] **Step 4: 跑后端测试确认通过**

Run:

```bash
pytest -q tests/unit/services/test_system_service_dashboard.py tests/api/routers/ui/test_ui_system_dashboard.py tests/api/routers/ui/test_data_health.py tests/api/routers/test_system_status.py
```

Expected: PASS。

- [ ] **Step 5: 提交后端改动**

```bash
git add src/services/system_service.py api/routers/ui/system.py tests/unit/services/test_system_service_dashboard.py tests/api/routers/ui/test_ui_system_dashboard.py
git commit -m "feat: add system dashboard aggregation"
```

---

### Task 2: 前端系统 Dashboard API 和组件

**Files:**
- Modify: `web/src/types/system.ts`
- Modify: `web/src/lib/api/system.ts`
- Create: `web/src/lib/api/system.test.ts`
- Create: `web/src/features/data-health/operational-dashboard-center.tsx`
- Modify: `web/src/features/data-health/index.ts`
- Create: `web/src/features/data-health/operational-dashboard-center.test.tsx`

- [ ] **Step 1: 写失败测试**

先写 API client 测试，确认前端会请求新的系统 Dashboard 接口。

```ts
import { describe, expect, it, vi } from 'vitest';
import { getSystemDashboard } from './system';
import { fetchJson } from './http';

vi.mock('./http', () => ({
  fetchJson: vi.fn(),
}));

it('calls the dashboard endpoint', async () => {
  vi.mocked(fetchJson).mockResolvedValueOnce({
    status: 'ok',
    generated_at: '2026-05-11T09:00:00Z',
    health: { database: { status: 'ok' } },
    failed_jobs: [],
    duration_summary: { average_seconds: null, p95_seconds: null, recent_jobs: [] },
    freshness: { sources: [] },
    alerts: { critical: 0, warning: 0, latest: [] },
    traces: [],
  });

  await getSystemDashboard();
  expect(fetchJson).toHaveBeenCalledWith('/system/dashboard');
});
```

再写组件测试，覆盖有数据、空态、错误态三个状态：

```tsx
mockedGetSystemDashboard.mockResolvedValue({
  status: 'ok',
  generated_at: '2026-05-11T09:00:00Z',
  health: { database: { status: 'ok', latency_ms: 3.2 }, worker: { status: 'ok' } },
  failed_jobs: [{ id: 'job-failed-1', job_type: 'run_after_close', status: 'failed', duration_seconds: 180 }],
  duration_summary: { average_seconds: 180.0, p95_seconds: 240.0, recent_jobs: [] },
  freshness: { sources: [{ source: 'market_data', entity_type: 'market', freshness_hours: 24, is_stale: true }] },
  alerts: { critical: 1, warning: 0, latest: [{ level: 'critical', title: 'stale market data', message: 'market data is stale' }] },
  traces: [{ job_id: 'job-failed-1', request_context: { path: '/api/ui/v1/jobs', method: 'POST' } }],
});
```

断言应至少覆盖：

- 标题 `Operational Dashboard`
- 最近失败任务卡
- `stale market data` 告警摘要
- `market_data` 新鲜度行
- `job-failed-1` 追踪行

- [ ] **Step 2: 先跑测试确认失败**

Run:

```bash
pytest -q tests/unit/services/test_system_service_dashboard.py tests/api/routers/ui/test_ui_system_dashboard.py
./node_modules/.bin/vitest run src/lib/api/system.test.ts src/features/data-health/operational-dashboard-center.test.tsx
```

Expected: fail，因为前端 Dashboard client 和组件还没实现。

- [ ] **Step 3: 实现最小前端类型和组件**

在 `web/src/types/system.ts` 里补 Dashboard 响应类型，保持和后端 payload 对齐：

```ts
export type SystemDashboardResponse = {
  status: 'ok' | 'partial' | 'error';
  generated_at: string;
  health: {
    database: DatabaseHealthStatus;
    worker?: {
      status: 'ok' | 'warning' | 'error';
      heartbeat_at?: string | null;
      heartbeat_age_minutes?: number | null;
    };
  };
  failed_jobs: Array<{
    id: string;
    job_type: string;
    status: string;
    started_at?: string | null;
    finished_at?: string | null;
    duration_seconds?: number | null;
    error_message?: string | null;
    request_context?: { path?: string; method?: string; client_host?: string | null } | null;
  }>;
  duration_summary: {
    average_seconds: number | null;
    p95_seconds: number | null;
    recent_jobs: Array<{ id: string; job_type: string; duration_seconds: number | null }>;
  };
  freshness: {
    sources: Array<{ source: string; entity_type: string; last_updated: string | null; freshness_hours: number | null; is_stale: boolean }>;
  };
  alerts: {
    critical: number;
    warning: number;
    latest: Array<{ level: string; title: string; message: string; timestamp?: string | null }>;
  };
  traces: Array<{ job_id: string; request_context: { path?: string; method?: string; client_host?: string | null } | null }>;
};
```

在 `web/src/lib/api/system.ts` 增加：

```ts
export function getSystemDashboard() {
  return fetchJson<SystemDashboardResponse>('/system/dashboard');
}
```

新增 `web/src/features/data-health/operational-dashboard-center.tsx`，让它只负责 Dashboard 运维摘要，不要和现有 `buildDashboardReport()` 混写成一个大组件。组件结构建议是：

- 顶部刷新按钮
- 4 个 KPI 卡
- 失败任务列表
- 耗时摘要
- 新鲜度列表
- 告警摘要

页面状态处理建议：

- `loading` 时显示骨架屏
- `error` 时显示局部错误卡片
- 空数据时显示 `暂无数据`
- `refresh` 使用 `query.refetch()`，不要引入额外状态管理

在 `web/src/features/data-health/index.ts` 把新组件导出，保留现有 report 组件不动，方便页面同时展示“运维摘要”和“Dashboard report”。

- [ ] **Step 4: 跑前端测试确认通过**

Run:

```bash
./node_modules/.bin/vitest run src/lib/api/system.test.ts src/features/data-health/operational-dashboard-center.test.tsx
```

Expected: PASS。

- [ ] **Step 5: 提交前端改动**

```bash
git add web/src/types/system.ts web/src/lib/api/system.ts web/src/lib/api/system.test.ts web/src/features/data-health/operational-dashboard-center.tsx web/src/features/data-health/operational-dashboard-center.test.tsx web/src/features/data-health/index.ts
git commit -m "feat: add operational dashboard ui"
```

---

### Task 3: 页面接线、导航文案和回归测试

**Files:**
- Modify: `web/src/pages/data-health/index.tsx`
- Modify: `web/src/pages/data-health/index.test.tsx`
- Modify: `web/src/app/navigation.ts`
- Modify: `docs/WebDeployment.md`
- Modify: `docs/Web-TaskList.md`

- [ ] **Step 1: 写失败测试**

先更新页面测试，让它同时覆盖新的运维 Dashboard 和原有 report 产物。测试里同时 mock 两个 API：

```tsx
vi.mock('@/lib/api/system', () => ({
  getSystemDashboard: vi.fn(),
}));

vi.mock('@/lib/api/dataHealth', () => ({
  buildDashboardReport: vi.fn(),
}));
```

页面断言至少覆盖：

- `Operational Dashboard` 标题
- `Recent failed jobs` 或对应中文文案
- `Dashboard report` 区块仍然存在
- `stale market data` 告警摘要
- `dashboard.html` 产物路径

再补一个简单回归断言，确保 `Overview` 仍然只显示入口级卡片，不把运维卡塞回首页。

- [ ] **Step 2: 先跑测试确认失败**

Run:

```bash
./node_modules/.bin/vitest run src/pages/data-health/index.test.tsx src/pages/overview/index.test.tsx
```

Expected: fail，因为页面还没接上新的 Dashboard 组件和文案。

- [ ] **Step 3: 接好页面和导航**

在 `web/src/pages/data-health/index.tsx` 里把页面标题调整成运维 Dashboard 语义，建议保持：

```tsx
<PageHeader
  kicker="Data Ops"
  title="Operational Dashboard"
  description="Live failures, runtime, freshness, and alert summaries."
/>
```

然后在页面主体同时渲染：

```tsx
<OperationalDashboardCenter />
<DataHealthCenter />
```

这样 `Operational Dashboard` 负责运维指标，`DataHealthCenter` 继续保留 HTML 报告产物和 JSON 预览，不会丢掉已有能力。

在 `web/src/app/navigation.ts` 里把 `Data Health` 的描述改成更准确的运维语义，例如：

```ts
{ label: 'Data Health', path: '/data-health', description: 'Operational dashboard and HTML report artifact' },
```

在 `docs/WebDeployment.md` 里补一小段“健康检查与 Dashboard”说明，明确：

- `/api/ui/v1/system/status` 适合机器探测
- `/api/ui/v1/system/dashboard` 适合人工运维查看
- `/data-health` 页面承载运维 Dashboard 和报告产物

- [ ] **Step 4: 跑页面和回归测试确认通过**

Run:

```bash
./node_modules/.bin/vitest run src/pages/data-health/index.test.tsx src/pages/overview/index.test.tsx
pytest -q tests/api/routers/ui/test_ui_system_dashboard.py tests/api/routers/ui/test_data_health.py tests/api/routers/test_system_status.py
```

Expected: PASS。

- [ ] **Step 5: 更新任务状态并提交**

把 `docs/Web-TaskList.md` 里的 `WEB-S9-003` 改成完成，并在 Stage 9 后续任务排序里保持和当前实现一致。

```bash
git add web/src/pages/data-health/index.tsx web/src/pages/data-health/index.test.tsx web/src/app/navigation.ts docs/WebDeployment.md docs/Web-TaskList.md
git commit -m "feat: wire operational dashboard page"
```

---

### Task 4: 全量验证和收口

**Files:**
- Modify: 无新增代码，主要是验证

- [ ] **Step 1: 跑后端相关测试**

Run:

```bash
pytest -q tests/unit/services/test_system_service_dashboard.py tests/api/routers/ui/test_ui_system_dashboard.py tests/api/routers/ui/test_data_health.py tests/api/routers/test_system_status.py
```

Expected: PASS。

- [ ] **Step 2: 跑前端相关测试**

Run:

```bash
./node_modules/.bin/vitest run src/lib/api/system.test.ts src/features/data-health/operational-dashboard-center.test.tsx src/pages/data-health/index.test.tsx src/pages/overview/index.test.tsx
```

Expected: PASS。

- [ ] **Step 3: 跑仓库级校验**

Run:

```bash
./node_modules/.bin/vitest run src/lib/api/system.test.ts src/features/data-health/operational-dashboard-center.test.tsx src/pages/data-health/index.test.tsx src/pages/overview/index.test.tsx
python -m pytest -q tests/unit/services/test_system_service_dashboard.py tests/api/routers/ui/test_ui_system_dashboard.py tests/api/routers/ui/test_data_health.py tests/api/routers/test_system_status.py
```

如果仓库已有既定命令，再补跑：

```bash
python -m pytest -q tests/unit/services
```

确保没有引入回归。

- [ ] **Step 4: 收口说明**

确认以下结论都成立后，才把任务标记为完成：

- `Overview` 没有被 Dashboard 指标污染
- `/api/ui/v1/system/status` 仍然是轻量健康检查
- `/api/ui/v1/system/dashboard` 能展示失败任务、耗时、新鲜度、告警和追踪线索
- `/data-health` 页面同时具备运维摘要和报告产物入口
- 文档和任务状态同步

- [ ] **Step 5: 最终提交**

```bash
git add -A
git commit -m "feat: finish web s9-003 operational dashboard"
```
