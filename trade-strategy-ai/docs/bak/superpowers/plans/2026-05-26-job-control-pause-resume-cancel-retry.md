# Job Control Pause/Resume/Cancel/Retry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real pause, resume, cancel, and error retry controls for the seven required long-running jobs, with persisted checkpoint recovery and Web buttons in Job List and Job Detail.

**Architecture:** Extend the existing Job record with a persisted runtime state JSON payload so checkpoint data stays in the same transaction boundary as status, progress, and audit. Add explicit job capability flags and a cooperative control context in the runner so workers can stop at safe boundaries, write checkpoints, and later resume without reprocessing completed work. The UI will only surface state-based controls and checkpoint summaries through the canonical Job APIs.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, Pydantic, React, TanStack Query, TypeScript, Vitest, pytest.

---

## File Map

- `src/models/job.py`: Job status, runtime state column, persisted control metadata.
- `src/services/job_registry.py`: job capability flags and job definition contract.
- `src/services/job_service.py`: state transitions, checkpoint persistence, audit events, retry semantics.
- `src/services/job_control.py` (new): shared control context and checkpoint helper types.
- `src/services/job_runner.py`: cooperative pause/resume/cancel/retry enforcement.
- `src/market_data/ohlcv_service.py`: `ohlcv-crawl` checkpoint and resume cursor handling.
- `src/services/kaipan_service.py`: `kaipan-fetch` / `kaipan-normalize` checkpoint and resume cursor handling.
- `src/services/snapshot_service.py`: `snapshot-build` checkpoint and resume cursor handling.
- `src/services/backtest_service.py`: `backtest-run` / `backtest-validate-rules` / `rule-pool-backtest` checkpoint and resume cursor handling.
- `src/backtest/engine.py` and `src/backtest/execution.py`: backtest engine-side checkpoint boundaries.
- `api/routers/ui/jobs.py`: pause/resume/cancel/retry endpoints.
- `web/src/lib/api/jobs.ts`: Job control API client.
- `web/src/types/jobs.ts`: Job record and runtime state types.
- `web/src/components/jobs/JobControls.tsx` (new): shared state-based action buttons.
- `web/src/components/jobs/JobTable.tsx`: list-row action entry point and paused badge.
- `web/src/pages/jobs/JobDetailPage.tsx`: detail-page action panel and checkpoint summary.

---

### Task 1: Add job contract, runtime state, and capability flags

**Files:**
- Modify: `trade-strategy-ai/src/models/job.py`
- Modify: `trade-strategy-ai/src/services/job_registry.py`
- Modify: `trade-strategy-ai/src/services/job_service.py`
- Modify: `trade-strategy-ai/web/src/types/jobs.ts`
- Test: `trade-strategy-ai/tests/unit/services/test_job_registry.py`
- Test: `trade-strategy-ai/tests/unit/services/test_job_service.py`
- Test: `trade-strategy-ai/tests/unit/models/test_job.py`

- [ ] **Step 1: Write the failing tests**

Add assertions for the new contract:

```python
def test_job_status_includes_paused() -> None:
    assert JobStatus.paused.value == "paused"


def test_runtime_state_is_serialized_on_job_detail() -> None:
    job = Job(
        job_type="ohlcv-crawl",
        status=JobStatus.paused.value,
        params={},
        runtime_state={"schema_version": 1, "checkpoint_type": "symbol"},
    )
    payload = service._serialize_job(job)
    assert payload["runtime_state"]["checkpoint_type"] == "symbol"


def test_rule_pool_backtest_can_retry() -> None:
    definition = get_job_definition("rule-pool-backtest")
    assert definition.can_retry is True
    assert definition.can_pause is True
    assert definition.can_resume is True
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python -m pytest trade-strategy-ai/tests/unit/services/test_job_registry.py trade-strategy-ai/tests/unit/services/test_job_service.py trade-strategy-ai/tests/unit/models/test_job.py -q
```

Expected: failures for missing `paused`, missing `runtime_state`, or missing capability flags.

- [ ] **Step 3: Implement the minimal contract changes**

Add the new state and persisted runtime field:

```python
class JobStatus(StrEnum):
    pending = "pending"
    running = "running"
    paused = "paused"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


class Job(TimestampMixin, Base):
    runtime_state: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant)
```

Extend `JobDefinition` with capability flags:

```python
class JobDefinition(BaseModel):
    can_pause: bool
    can_resume: bool
    can_cancel: bool
    can_retry: bool
```

Set these flags on the seven required jobs in `job_registry.py`, and flip `rule-pool-backtest` from `can_retry=False` to `can_retry=True`.

Add `runtime_state` to the serialized job payload and the Web type:

```ts
export type JobRecord = {
  runtime_state: Record<string, unknown> | null;
};
```

- [ ] **Step 4: Re-run the focused tests**

Run:

```bash
python -m pytest trade-strategy-ai/tests/unit/services/test_job_registry.py trade-strategy-ai/tests/unit/services/test_job_service.py trade-strategy-ai/tests/unit/models/test_job.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai add src/models/job.py src/services/job_registry.py src/services/job_service.py web/src/types/jobs.ts tests/unit/services/test_job_registry.py tests/unit/services/test_job_service.py tests/unit/models/test_job.py
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai commit -m "feat: add job runtime state contract"
```

---

### Task 2: Implement pause/resume/retry Job APIs and service transitions

**Files:**
- Modify: `trade-strategy-ai/api/routers/ui/jobs.py`
- Modify: `trade-strategy-ai/src/services/job_service.py`
- Modify: `trade-strategy-ai/src/services/job_control.py` (new)
- Modify: `trade-strategy-ai/web/src/lib/api/jobs.ts`
- Modify: `trade-strategy-ai/web/src/types/jobs.ts`
- Test: `trade-strategy-ai/tests/api/routers/test_jobs.py`
- Test: `trade-strategy-ai/tests/unit/services/test_job_service.py`

- [ ] **Step 1: Write the failing tests**

Describe the control endpoints and state transitions:

```python
async def test_pause_resume_retry_flow(job_service: JobService) -> None:
    created = await job_service.create_job(job_type="ohlcv-crawl", params={"profile_id": "demo"})
    job_id = created.payload["job"]["id"]
    paused = await job_service.pause_job(job_id=job_id, actor="web")
    assert paused.payload["job"]["status"] == "paused"
    resumed = await job_service.resume_job(job_id=job_id, actor="web")
    assert resumed.payload["job"]["status"] in {"pending", "running"}
    retry = await job_service.retry_job(job_id=job_id, actor="web")
    assert retry.payload["job"]["retry_count"] == 0
```

Add API contract checks:

```python
def test_job_control_routes_exist() -> None:
    assert any(route.path == "/api/ui/v1/jobs/{job_id}/pause" for route in router.routes)
    assert any(route.path == "/api/ui/v1/jobs/{job_id}/resume" for route in router.routes)
    assert any(route.path == "/api/ui/v1/jobs/{job_id}/retry" for route in router.routes)
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python -m pytest trade-strategy-ai/tests/unit/services/test_job_service.py trade-strategy-ai/tests/api/routers/test_jobs.py -q
```

Expected: failures because the control APIs and service methods do not exist yet.

- [ ] **Step 3: Implement the minimal control transitions**

Create a small shared control helper:

```python
@dataclass
class JobControlState:
    paused: bool = False
    cancel_requested: bool = False
    checkpoint: dict[str, Any] | None = None
```

Add service methods that mutate the Job row and write audit events:

```python
async def pause_job(self, *, job_id: str | UUID, actor: str) -> ServiceResult:
    return await self._transition_job_state(
        job_id=job_id,
        next_status=JobStatus.paused.value,
        actor=actor,
        operation="pause",
    )


async def resume_job(self, *, job_id: str | UUID, actor: str) -> ServiceResult:
    return await self._transition_job_state(
        job_id=job_id,
        next_status=JobStatus.pending.value,
        actor=actor,
        operation="resume",
    )


async def retry_job(self, *, job_id: str | UUID, actor: str) -> ServiceResult:
    return await self._transition_job_state(
        job_id=job_id,
        next_status=JobStatus.pending.value,
        actor=actor,
        operation="retry",
        preserve_runtime_state=True,
        reset_error=True,
    )
```

Expose router endpoints that call those methods and return the updated Job payload.

Update the Web client:

```ts
export function pauseJob(jobId: string) {
  return fetchJson(`/jobs/${jobId}/pause`, { method: 'POST' });
}

export function resumeJob(jobId: string) {
  return fetchJson(`/jobs/${jobId}/resume`, { method: 'POST' });
}

export function retryJob(jobId: string) {
  return fetchJson(`/jobs/${jobId}/retry`, { method: 'POST' });
}
```

- [ ] **Step 4: Re-run the focused tests**

Run:

```bash
python -m pytest trade-strategy-ai/tests/unit/services/test_job_service.py trade-strategy-ai/tests/api/routers/test_jobs.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai add api/routers/ui/jobs.py src/services/job_service.py src/services/job_control.py web/src/lib/api/jobs.ts web/src/types/jobs.ts tests/unit/services/test_job_service.py tests/api/routers/test_jobs.py
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai commit -m "feat: add job control apis"
```

---

### Task 3: Add cooperative checkpoint control to JobRunner

**Files:**
- Modify: `trade-strategy-ai/src/services/job_runner.py`
- Modify: `trade-strategy-ai/src/services/job_control.py`
- Modify: `trade-strategy-ai/src/services/job_service.py`
- Test: `trade-strategy-ai/tests/unit/services/test_job_runner.py`

- [ ] **Step 1: Write the failing tests**

Add a runner test that proves a handler can pause at a safe boundary and resume from checkpoint:

```python
async def test_runner_persists_checkpoint_and_pauses(monkeypatch) -> None:
    checkpoints = []

    async def handler(params, control):
        await control.save_checkpoint({"cursor": 2, "schema_version": 1})
        control.request_pause()
        return ServiceResult(status="ok", message="done", payload={})

    result = await runner.execute_job(job_id=job_id)
    assert checkpoints[-1]["cursor"] == 2
    assert result.payload["job"]["status"] == "paused"
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python -m pytest trade-strategy-ai/tests/unit/services/test_job_runner.py -q
```

Expected: failures because `JobRunner` does not yet accept or honor a control context.

- [ ] **Step 3: Implement the cooperative control loop**

Introduce a runner-side context object:

```python
@dataclass
class JobControlContext:
    job_id: UUID
    runtime_state: dict[str, Any]
    should_pause: Callable[[], bool]
    should_cancel: Callable[[], bool]
    save_checkpoint: Callable[[dict[str, Any]], Awaitable[None]]
    load_checkpoint: Callable[[], Awaitable[dict[str, Any] | None]]
```

Update `execute_job()` so handlers receive the control context and the runner:

```python
if control.should_cancel():
    await self._job_service.cancel_job(job_id=job_id, reason="cancel requested", actor=worker_id)
    return
if control.should_pause():
    await self._job_service.pause_job(job_id=job_id, actor=worker_id)
    return
```

Persist checkpoint updates through `JobService` so resume does not depend on process memory.

- [ ] **Step 4: Re-run the targeted tests**

Run:

```bash
python -m pytest trade-strategy-ai/tests/unit/services/test_job_runner.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai add src/services/job_runner.py src/services/job_control.py src/services/job_service.py tests/unit/services/test_job_runner.py
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai commit -m "feat: add cooperative job control"
```

---

### Task 4: Add checkpoint/resume to `ohlcv-crawl`, `kaipan-fetch`, `kaipan-normalize`, and `snapshot-build`

**Files:**
- Modify: `trade-strategy-ai/src/market_data/ohlcv_service.py`
- Modify: `trade-strategy-ai/src/services/market_service.py`
- Modify: `trade-strategy-ai/src/services/kaipan_service.py`
- Modify: `trade-strategy-ai/src/providers/kaipan_provider.py`
- Modify: `trade-strategy-ai/src/providers/kaipan_normalizer.py`
- Modify: `trade-strategy-ai/src/services/snapshot_service.py`
- Modify: `trade-strategy-ai/tests/unit/market_data/test_ohlcv_service.py`
- Modify: `trade-strategy-ai/tests/unit/services/test_kaipan_service.py`
- Modify: `trade-strategy-ai/tests/unit/services/test_snapshot_service.py`

- [ ] **Step 1: Write the failing tests**

Describe the resume cursor for each job:

```python
async def test_ohlcv_resume_skips_completed_symbols() -> None:
    state = {"checkpoint_type": "symbol", "cursor": 3}
    assert await service.resume_from_runtime_state(state) == 3


async def test_kaipan_fetch_resume_uses_trade_date_slot_fetcher() -> None:
    state = {"trade_date": "2026-05-26", "slot": "09-25", "cursor": 4}
    assert service._resume_cursor(state) == 4


async def test_snapshot_build_resume_skips_completed_combinations() -> None:
    state = {"trade_date": "2026-05-26", "snapshot_type": "all", "cursor": 2}
    assert service._next_cursor(state) == 2
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python -m pytest trade-strategy-ai/tests/unit/market_data/test_ohlcv_service.py trade-strategy-ai/tests/unit/services/test_kaipan_service.py trade-strategy-ai/tests/unit/services/test_snapshot_service.py -q
```

Expected: failures because the services do not yet load and advance checkpoint state.

- [ ] **Step 3: Implement per-job checkpoint handling**

For `ohlcv-crawl`, write checkpoint after each symbol:

```python
runtime_state = {
    "schema_version": 1,
    "checkpoint_type": "symbol",
    "cursor": symbol_index,
    "last_safe_point": {"symbol": symbol, "trade_date": trade_date.isoformat()},
}
```

For `kaipan-fetch`, checkpoint by `trade_date / slot / fetcher`:

```python
runtime_state = {
    "schema_version": 1,
    "checkpoint_type": "trade_date_slot_fetcher",
    "trade_date": trade_day.isoformat(),
    "slot": current_slot,
    "cursor": fetcher_index,
}
```

For `kaipan-normalize`, checkpoint by dataset:

```python
runtime_state = {
    "schema_version": 1,
    "checkpoint_type": "trade_date_slot_dataset",
    "trade_date": trade_day.isoformat(),
    "slot": current_slot,
    "cursor": dataset_index,
}
```

For `snapshot-build`, checkpoint by `trade_date x snapshot_type`:

```python
runtime_state = {
    "schema_version": 1,
    "checkpoint_type": "snapshot_combo",
    "trade_date": trade_day.isoformat(),
    "snapshot_type": snapshot_type,
    "cursor": combo_index,
}
```

Each service should read `job.runtime_state` at startup and continue from the stored cursor instead of recomputing from zero.

- [ ] **Step 4: Re-run the focused tests**

Run:

```bash
python -m pytest trade-strategy-ai/tests/unit/market_data/test_ohlcv_service.py trade-strategy-ai/tests/unit/services/test_kaipan_service.py trade-strategy-ai/tests/unit/services/test_snapshot_service.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai add src/market_data/ohlcv_service.py src/services/market_service.py src/services/kaipan_service.py src/providers/kaipan_provider.py src/providers/kaipan_normalizer.py src/services/snapshot_service.py tests/unit/market_data/test_ohlcv_service.py tests/unit/services/test_kaipan_service.py tests/unit/services/test_snapshot_service.py
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai commit -m "feat: add checkpoint resume for market jobs"
```

---

### Task 5: Add checkpoint/resume to `backtest-run`, `backtest-validate-rules`, and `rule-pool-backtest`

**Files:**
- Modify: `trade-strategy-ai/src/services/backtest_service.py`
- Modify: `trade-strategy-ai/src/backtest/engine.py`
- Modify: `trade-strategy-ai/src/backtest/execution.py`
- Modify: `trade-strategy-ai/src/services/job_registry.py`
- Modify: `trade-strategy-ai/tests/unit/services/test_backtest_service.py`
- Modify: `trade-strategy-ai/tests/unit/backtest/test_engine.py`

- [ ] **Step 1: Write the failing tests**

Capture resume behavior for the three backtest jobs:

```python
async def test_backtest_run_resumes_from_trade_day_checkpoint() -> None:
    state = {"checkpoint_type": "trade_day", "cursor": "2026-05-20"}
    assert service._resume_trade_day(state) == date(2026, 5, 20)


async def test_validate_rules_resumes_from_cursor() -> None:
    state = {"checkpoint_type": "trade_day", "cursor": "2026-05-21"}
    assert service._resume_trade_day(state) == date(2026, 5, 21)


async def test_rule_pool_backtest_can_retry() -> None:
    definition = get_job_definition("rule-pool-backtest")
    assert definition.can_retry is True
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python -m pytest trade-strategy-ai/tests/unit/services/test_backtest_service.py trade-strategy-ai/tests/unit/backtest/test_engine.py -q
```

Expected: failures because the engine and service do not yet persist checkpoint state.

- [ ] **Step 3: Implement backtest checkpoints and resume hooks**

Teach the backtest engine to accept a control context and a cursor:

```python
result = engine.run_sync(request, progress_callback=progress_callback, checkpoint_callback=save_checkpoint, resume_state=runtime_state)
```

Persist a trade-day cursor at each safe boundary:

```python
runtime_state = {
    "schema_version": 1,
    "checkpoint_type": "trade_day",
    "cursor": trade_date.isoformat(),
    "last_safe_point": {"trade_date": trade_date.isoformat()},
}
```

For `rule-pool-backtest`, keep the rule cursor alongside the trade-day cursor so resuming can skip finished rule/date combinations.

Set `rule-pool-backtest` to `can_retry=True` in `job_registry.py`.

- [ ] **Step 4: Re-run the targeted tests**

Run:

```bash
python -m pytest trade-strategy-ai/tests/unit/services/test_backtest_service.py trade-strategy-ai/tests/unit/backtest/test_engine.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai add src/services/backtest_service.py src/backtest/engine.py src/backtest/execution.py src/services/job_registry.py tests/unit/services/test_backtest_service.py tests/unit/backtest/test_engine.py
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai commit -m "feat: add checkpoint resume for backtest jobs"
```

---

### Task 6: Add Job List and Job Detail controls

**Files:**
- Create: `trade-strategy-ai/web/src/components/jobs/JobControls.tsx`
- Modify: `trade-strategy-ai/web/src/components/jobs/JobTable.tsx`
- Modify: `trade-strategy-ai/web/src/pages/jobs/JobDetailPage.tsx`
- Modify: `trade-strategy-ai/web/src/lib/api/jobs.ts`
- Modify: `trade-strategy-ai/web/src/types/jobs.ts`
- Test: `trade-strategy-ai/web/src/components/jobs/JobControls.test.tsx`
- Test: `trade-strategy-ai/web/src/pages/jobs/JobDetailPage.test.tsx`
- Test: `trade-strategy-ai/web/src/pages/jobs/index.test.tsx`

- [ ] **Step 1: Write the failing tests**

Add UI assertions for status-based actions:

```tsx
it('shows pause and cancel for running jobs', async () => {
  render(<JobControls job={runningJob} />);
  expect(screen.getByRole('button', { name: '暂停' })).toBeEnabled();
  expect(screen.getByRole('button', { name: '取消' })).toBeEnabled();
});

it('shows resume for paused jobs and retry for failed jobs', async () => {
  render(<JobControls job={pausedJob} />);
  expect(screen.getByRole('button', { name: '恢复' })).toBeEnabled();
  render(<JobControls job={failedJob} />);
  expect(screen.getByRole('button', { name: '重试' })).toBeEnabled();
});
```

Add detail-page checks for checkpoint summary:

```tsx
expect(screen.getByText('Checkpoint')).toBeInTheDocument();
expect(screen.getByText('paused')).toBeInTheDocument();
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
cd trade-strategy-ai/web && pnpm vitest run src/components/jobs/JobControls.test.tsx src/pages/jobs/JobDetailPage.test.tsx src/pages/jobs/index.test.tsx
```

Expected: failures because the controls component and endpoint wiring do not exist yet.

- [ ] **Step 3: Implement shared state-based controls**

Create a focused control component:

```tsx
export function JobControls({ job }: { job: JobRecord }) {
  if (job.status === 'running' || job.status === 'pending') {
    return <>
      <Button onClick={() => pauseJob(job.id)}>暂停</Button>
      <Button onClick={() => cancelJob(job.id)}>取消</Button>
    </>;
  }
  if (job.status === 'paused') {
    return <>
      <Button onClick={() => resumeJob(job.id)}>恢复</Button>
      <Button onClick={() => cancelJob(job.id)}>取消</Button>
    </>;
  }
  if (job.status === 'failed') {
    return <Button onClick={() => retryJob(job.id)}>重试</Button>;
  }
  return null;
}
```

Use the component in both Job List and Job Detail, and render `runtime_state` / checkpoint summary in the detail page with a small read-only panel.

- [ ] **Step 4: Re-run the focused tests**

Run:

```bash
cd trade-strategy-ai/web && pnpm vitest run src/components/jobs/JobControls.test.tsx src/pages/jobs/JobDetailPage.test.tsx src/pages/jobs/index.test.tsx
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai add web/src/components/jobs/JobControls.tsx web/src/components/jobs/JobTable.tsx web/src/pages/jobs/JobDetailPage.tsx web/src/lib/api/jobs.ts web/src/types/jobs.ts web/src/components/jobs/JobControls.test.tsx web/src/pages/jobs/JobDetailPage.test.tsx web/src/pages/jobs/index.test.tsx
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai commit -m "feat: add job control ui"
```

---

### Task 7: Regression, documentation, and end-to-end verification

**Files:**
- Modify: `trade-strategy-ai/tests/**`
- Modify: `trade-strategy-ai/docs/superpowers/specs/2026-05-26-job-control-pause-resume-cancel-retry-design.md` if any behavior decisions change
- Modify: `trade-strategy-ai/docs/New-Web-Linked-TaskLists/New-Web-TaskList.md` only if the team decides to register the new work item later

- [ ] **Step 1: Write the failing or missing integration checks**

Add an end-to-end style test matrix that covers the seven required jobs:

```python
def test_required_jobs_support_control_flags() -> None:
    job_types = [
        "ohlcv-crawl",
        "kaipan-fetch",
        "kaipan-normalize",
        "snapshot-build",
        "backtest-run",
        "backtest-validate-rules",
        "rule-pool-backtest",
    ]
    for job_type in job_types:
        definition = get_job_definition(job_type)
        assert definition.can_pause is True
        assert definition.can_resume is True
        assert definition.can_cancel is True
        assert definition.can_retry is True
```

- [ ] **Step 2: Run the full focused test set**

Run:

```bash
python -m pytest trade-strategy-ai/tests/unit/services/test_job_registry.py trade-strategy-ai/tests/unit/services/test_job_service.py trade-strategy-ai/tests/unit/services/test_job_runner.py trade-strategy-ai/tests/unit/services/test_backtest_service.py trade-strategy-ai/tests/unit/market_data/test_ohlcv_service.py trade-strategy-ai/tests/unit/services/test_kaipan_service.py trade-strategy-ai/tests/unit/services/test_snapshot_service.py trade-strategy-ai/tests/api/routers/test_jobs.py -q
cd trade-strategy-ai/web && pnpm vitest run src/components/jobs/JobControls.test.tsx src/pages/jobs/JobDetailPage.test.tsx src/pages/jobs/index.test.tsx
```

Expected: all pass.

- [ ] **Step 3: Validate the plan against the spec**

Confirm the implementation covers:

- `JC-001` to `JC-013`
- `paused` status
- persisted `runtime_state`
- pause/resume/cancel/retry APIs
- cooperative runner control
- checkpoint resume for all seven required jobs
- Job List and Job Detail buttons
- regression coverage for the seven required jobs

- [ ] **Step 4: Final documentation pass**

If any behavior changes were necessary during implementation, update this plan document and the spec document in the same commit so the implementation narrative matches the code.

- [ ] **Step 5: Commit**

```bash
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai add tests docs/superpowers/plans/2026-05-26-job-control-pause-resume-cancel-retry.md docs/superpowers/specs/2026-05-26-job-control-pause-resume-cancel-retry-design.md
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai commit -m "docs: add job control implementation plan"
```

---

## Coverage Check

- `JC-001` -> Task 1
- `JC-002` -> Task 1 and Task 2
- `JC-003` -> Task 2
- `JC-004` -> Task 3
- `JC-005` -> Task 4
- `JC-006` -> Task 4
- `JC-007` -> Task 4
- `JC-008` -> Task 5
- `JC-009` -> Task 5
- `JC-010` -> Task 5
- `JC-011` -> Task 6
- `JC-012` -> Task 6
- `JC-013` -> Task 7

This plan keeps the seven required jobs in scope and ensures the final implementation can reach the acceptance criteria in the spec.
