# NW-V2-S3-002 Strategy Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the V2 strategy workflow as a Web-first, production-bound execution and result-explanation loop for strategy-build, run-pre-market, and run-after-close.

**Architecture:** Keep execution inside the existing Job/Workflow/StrategyService stack and keep presentation inside the existing Strategy Workspace, Job Detail, and Artifact Center. Do not introduce any CLI surface or file-browser behavior. The flow is: Web submits a strategy action, Job/Runner executes it, Strategy and Artifact services persist the result, and the UI explains the result through shared recovery and artifact panels.

**Tech Stack:** Python, SQLAlchemy, FastAPI routers, pytest, TypeScript, React, TanStack Query, Vitest, React Router.

---

### Task 1: Strategy execution contract

**Files:**
- Modify: `src/services/strategy_service.py`
- Modify: `src/services/job_runner.py`
- Modify: `src/services/job_registry.py`
- Modify: `src/services/workflow_service.py`
- Test: `tests/unit/services/test_strategy_service.py`
- Test: `tests/unit/services/test_job_runner.py`
- Test: `tests/unit/services/test_job_registry.py`
- Test: `tests/api/routers/test_jobs.py`

- [ ] **Step 1: Write the failing tests**

```python
from src.services.job_registry import get_job_definition, get_runnable_job_types


def test_strategy_build_is_runnable():
    definition = get_job_definition("strategy-build")
    assert definition is not None
    assert definition.runnable is True
    assert "strategy-build" in get_runnable_job_types()

async def test_strategy_build_runs_through_strategy_service(monkeypatch):
    called = {}

    async def fake_build(details, *, config):
        called["details"] = details
        called["config"] = config

    service = StrategyService(build_handler=fake_build)
    result = await service.build_strategy_version(
        config_path="config/app.yaml",
        trader_id="trader_a",
        strategy_date="2026-05-16",
        force=False,
    )
    assert result.status == "ok"
    assert called["details"]["trader_id"] == "trader_a"
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
python -m pytest tests/unit/services/test_strategy_service.py tests/unit/services/test_job_runner.py tests/unit/services/test_job_registry.py tests/api/routers/test_jobs.py -q
```

Expected: fail on the missing runnable/handler contract or on mismatched strategy execution behavior.

- [ ] **Step 3: Implement the minimal contract**

```python
async def _strategy_build(params):
    service = StrategyService()
    return await service.build_strategy_version(
        config_path=params["config_path"],
        trader_id=params["trader_id"],
        strategy_date=params["strategy_date"],
        force=params.get("force", False),
    )

register_job_definition(
    job_type="strategy-build",
    runnable=True,
    handler_name="build_strategy_version",
)
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
python -m pytest tests/unit/services/test_strategy_service.py tests/unit/services/test_job_runner.py tests/unit/services/test_job_registry.py tests/api/routers/test_jobs.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/services/strategy_service.py src/services/job_runner.py src/services/job_registry.py src/services/workflow_service.py tests/unit/services/test_strategy_service.py tests/unit/services/test_job_runner.py tests/unit/services/test_job_registry.py tests/api/routers/test_jobs.py
git commit -m "feat(strategy): wire strategy workflow execution"
```

### Task 2: Job Detail strategy result explanation

**Files:**
- Modify: `web/src/pages/jobs/JobDetailPage.tsx`
- Modify: `web/src/pages/jobs/JobDetailPage.test.tsx`
- Modify: `web/src/lib/error-recovery.ts`
- Modify: `web/src/lib/error-recovery.test.ts`

- [ ] **Step 1: Write the failing tests**

```tsx
it('renders strategy report and evidence links through shared error state', async () => {
  mockedGetJob.mockResolvedValue({
    job: {
      id: 'job-9',
      job_type: 'strategy-build',
      status: 'failed',
      error: { type: 'runner_error', message: 'handler failed' },
      artifacts: [],
      params: { config_path: 'config/app.yaml' },
      result: null,
      created_by: 'web',
      idempotency_key: null,
      retry_count: 0,
      max_retries: 3,
      retry_backoff_seconds: 0,
      timeout_seconds: null,
      cancel_requested: false,
      cancel_requested_at: null,
      worker_id: 'worker-1',
      lock_token: null,
      lock_acquired_at: null,
      heartbeat_at: null,
      scheduled_at: null,
      started_at: '2026-05-16T08:00:00Z',
      finished_at: '2026-05-16T08:05:00Z',
      audit_events: [],
      created_at: '2026-05-16T08:00:00Z',
      updated_at: '2026-05-16T08:05:00Z',
      config_snapshot_path: null,
      config_snapshot: null,
    },
    job_dir: '/tmp/job-9',
    log_path: '/tmp/job-9/job.log',
    params_path: '/tmp/job-9/params.json',
    result_path: '/tmp/job-9/result.json',
    artifacts_path: '/tmp/job-9/artifacts.json',
  } as never);
  mockedGetJobLogs.mockResolvedValue({ job_id: 'job-9', log_path: '/tmp/job-9/job.log', count: 0, items: [] } as never);

  renderWithRouter([{ path: '/jobs/:jobId', element: <JobDetailPage /> }], ['/jobs/job-9']);

  expect(await screen.findByText('任务执行失败')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '重新运行' })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/pages/jobs/JobDetailPage.test.tsx src/lib/error-recovery.test.ts
```

Expected: fail because the Job Detail error block still needs to be unified or the new assertion does not match.

- [ ] **Step 3: Implement the minimal UI update**

```tsx
{errorObject ? (
  <ErrorState
    {...buildErrorRecoveryState(errorObject, 'job-detail')}
    onRetry={canOperateJobs ? () => rerunMutation.mutate() : undefined}
    retryLabel="重新运行"
  />
) : (
  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">暂无错误。</div>
)}
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/pages/jobs/JobDetailPage.test.tsx src/lib/error-recovery.test.ts
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/jobs/JobDetailPage.tsx web/src/pages/jobs/JobDetailPage.test.tsx web/src/lib/error-recovery.ts web/src/lib/error-recovery.test.ts
git commit -m "fix(strategy): unify job detail error explanation"
```

### Task 3: Strategy artifact retrieval and surfacing

**Files:**
- Modify: `src/services/artifact_service.py`
- Modify: `api/routers/ui/artifacts.py`
- Modify: `tests/unit/services/test_artifact_service.py`
- Modify: `tests/api/routers/test_artifacts.py`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-artifacts.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx`
- Modify: `web/src/pages/artifacts/index.tsx`
- Modify: `web/src/pages/artifacts/index.test.tsx`

- [ ] **Step 1: Write the failing tests**

```python
async def test_list_artifacts_filters_strategy_outputs():
    service = ArtifactService(job_lookup=_fake_job_lookup)
    result = await service.list_artifacts(job_type="strategy-build", date="2026-05-16")
    assert result.payload["items"][0]["job_type"] == "strategy-build"
    assert result.payload["items"][0]["job_id"] == "job-123"
```

```tsx
it('shows strategy artifacts and jumps back to the source job', async () => {
  mockedListArtifacts.mockResolvedValueOnce({
    count: 1,
    total: 1,
    skip: 0,
    limit: 24,
    items: [strategyArtifact],
  } as never);

  renderWithRouter([{ path: '/artifacts', element: <ArtifactsPage /> }], ['/artifacts']);

  expect(await screen.findByText('strategy-build')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: '查看来源 Job' })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
python -m pytest tests/unit/services/test_artifact_service.py tests/api/routers/test_artifacts.py -q
cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/pages/artifacts/index.test.tsx src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx
```

Expected: fail on missing strategy-oriented surfacing or filtering.

- [ ] **Step 3: Implement the minimal retrieval path**

```python
async def list_artifacts(
    *,
    kind: str | None = None,
    source: str | None = None,
    job_type: str | None = None,
    date: str | None = None,
    job_id: str | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> ServiceResult:
    records = self._scan_files()
    self._apply_job_metadata(
        records,
        await self._job_metadata_by_id({record.job_id for record in records if record.job_id}),
    )
    if job_type is not None:
        records = [item for item in records if item.job_type == job_type]
    if date is not None:
        records = [item for item in records if item.modified_at and item.modified_at.startswith(date.strip())]
    total = len(records)
    items = [record.to_payload() for record in records[skip : skip + limit]]
    return ServiceResult(
        status="ok",
        message="artifacts listed",
        payload={"count": len(items), "total": total, "skip": skip, "limit": limit, "items": items},
    )
```

```tsx
<ArtifactPanel
  artifacts={artifacts}
  onViewJob={(jobId) => navigate(`/jobs/${encodeURIComponent(jobId)}`)}
/>
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
python -m pytest tests/unit/services/test_artifact_service.py tests/api/routers/test_artifacts.py -q
cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/pages/artifacts/index.test.tsx src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/services/artifact_service.py api/routers/ui/artifacts.py tests/unit/services/test_artifact_service.py tests/api/routers/test_artifacts.py web/src/features/strategy-workspace/strategy-workspace-artifacts.tsx web/src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx web/src/pages/artifacts/index.tsx web/src/pages/artifacts/index.test.tsx
git commit -m "feat(strategy): surface strategy artifacts in artifact center"
```

### Task 4: Strategy workflow verification and task closure

**Files:**
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- Modify: `daily-sessions/2026-05-17.md`
- Modify: `daily-report/2026-05-17.md`
- Test: run the combined backend and frontend regression suite

- [ ] **Step 1: Write the failing closure checks**

```python
from src.services.job_registry import get_job_definition, get_runnable_job_types


def test_strategy_workflow_contract_is_closed():
    assert get_job_definition("strategy-build") is not None
    assert "strategy-build" in get_runnable_job_types()
```

```tsx
expect(await screen.findByText('策略工作台')).toBeInTheDocument();
expect(await screen.findByText('任务执行失败')).toBeInTheDocument();
```

- [ ] **Step 2: Run the full targeted regression**

Run:

```bash
python -m pytest tests/unit/services/test_strategy_service.py tests/unit/services/test_job_runner.py tests/unit/services/test_job_registry.py tests/unit/services/test_artifact_service.py tests/api/routers/test_jobs.py tests/api/routers/test_artifacts.py tests/api/routers/test_workflows.py -q
cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/pages/jobs/JobDetailPage.test.tsx src/pages/artifacts/index.test.tsx src/features/strategy-workspace/strategy-workspace-actions.test.tsx src/features/strategy-workspace/strategy-workspace-history.test.tsx src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx
```

Expected: pass.

- [ ] **Step 3: Update task list and daily records**

```md
### [x] NW-V2-S3-002 P0 实现 Strategy Workflow

完成情况：

- 已打通 strategy-build、run-pre-market、run-after-close 的 Web/API 执行闭环。
- 已让 Job Detail 可展示策略任务的错误、报告、证据包和产物跳转。
- 已让 Artifact Center 可检索策略产物并回溯来源 Job。
- 已通过相关后端和前端回归测试。
```

```md
## 今日成果
- 完成 NW-V2-S3-002。
- 打通 strategy workflow、Job Detail 结果解释和 Artifact Center 检索闭环。
```

- [ ] **Step 4: Commit**

```bash
git add docs/New-Web-Linked-TaskLists/New-Web-TaskList.md daily-sessions/2026-05-17.md daily-report/2026-05-17.md
git commit -m "feat(strategy): close strategy workflow v2"
```

## Self-Review Checklist

- `NW-V2-S3-002` 的四个验收点都被单独映射到了任务。
- 没有把 `UI-V2-009` 提前混入主链路。
- 没有 CLI 强化或 Demo-only 旁路。
- 任务里的类名、文件名、路由名都来自当前代码库已有实体。
- 每个修改步骤都附带了明确的测试命令。
