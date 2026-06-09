# Article Pipeline Step Builder and Schedule Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the article workbench create step-specific jobs with incremental/Force semantics, and add a start/stop schedule for daily `pipeline-run` execution.

**Architecture:** Keep `article_pipeline` as the canonical workflow definition, but expose its steps as first-class UI choices. The backend will map a selected step to the existing runnable job types (`crawl` and `pipeline-run`) and will keep schedule state in a dedicated in-memory scheduler service, consistent with other UI-managed schedulers in the repo. The frontend will use the existing article page as the single entry point and render step-specific forms plus a separate schedule panel.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLAlchemy async, APScheduler, React, TanStack Query, TypeScript, Vitest.

---

### Task 1: Extend article pipeline contract and job schemas

**Files:**
- Modify: `trade-strategy-ai/src/pipelines/article_pipeline_spec.py`
- Modify: `trade-strategy-ai/src/services/job_registry.py`
- Modify: `trade-strategy-ai/src/services/pipeline_service.py`
- Modify: `trade-strategy-ai/src/services/job_runner.py`
- Test: `trade-strategy-ai/tests/pipelines/test_article_pipeline_spec.py`
- Test: `trade-strategy-ai/tests/unit/services/test_job_registry.py`
- Test: `trade-strategy-ai/tests/unit/services/test_pipeline_service.py`
- Test: `trade-strategy-ai/tests/unit/services/test_job_runner.py`

- [ ] **Step 1: Write the failing tests**

Add assertions that:

```python
def test_article_pipeline_exposes_step_list():
    summary = ARTICLE_PIPELINE_SPEC.summary()
    assert [step["step_id"] for step in summary["steps"]] == ["crawl", "pipeline-run"]
    assert summary["steps"][0]["job_type"] == "crawl"
    assert summary["steps"][1]["job_type"] == "pipeline-run"

def test_crawl_job_accepts_force():
    definition = get_job_definition("crawl")
    assert "force" in definition.param_schema.fields

def test_pipeline_service_run_pipeline_step_forwards_force():
    result = asyncio.run(service.run_pipeline_step(step="crawl", config_path=config_path, force=True))
    assert calls["pipeline"]["force"] is True
    assert calls["pipeline"]["from_step"] == "crawl"
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python -m pytest trade-strategy-ai/tests/pipelines/test_article_pipeline_spec.py trade-strategy-ai/tests/unit/services/test_job_registry.py trade-strategy-ai/tests/unit/services/test_pipeline_service.py trade-strategy-ai/tests/unit/services/test_job_runner.py -q
```

Expected: failures for missing `force` on `crawl` and any new step-specific contract assertions.

- [ ] **Step 3: Implement the minimal contract changes**

Update the `crawl` job definition to include `force`:

```python
_def(
    job_type="crawl",
    ...
    param_schema=_schema(
        "抓取参数",
        {
            "config_path": _path_field("配置文件路径", required=True),
            "max_articles": _integer("最多抓取文章数"),
            "force": _boolean("是否强制执行", default=False),
        },
    ),
)
```

Ensure `PipelineService.run_pipeline_step()` forwards `force` and preserves `from_step`.

Ensure the article pipeline spec continues to expose `steps` with stable `step_id` / `job_type` values so the UI can render a step selector from the canonical workflow summary.

- [ ] **Step 4: Re-run the focused tests**

Run:

```bash
python -m pytest trade-strategy-ai/tests/pipelines/test_article_pipeline_spec.py trade-strategy-ai/tests/unit/services/test_job_registry.py trade-strategy-ai/tests/unit/services/test_pipeline_service.py trade-strategy-ai/tests/unit/services/test_job_runner.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai add src/pipelines/article_pipeline_spec.py src/services/job_registry.py src/services/pipeline_service.py src/services/job_runner.py tests/pipelines/test_article_pipeline_spec.py tests/unit/services/test_job_registry.py tests/unit/services/test_pipeline_service.py tests/unit/services/test_job_runner.py
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai commit -m "feat: expose article pipeline steps"
```

---

### Task 2: Add article pipeline scheduler service and API

**Files:**
- Create: `trade-strategy-ai/src/services/article_pipeline_schedule_service.py`
- Modify: `trade-strategy-ai/src/services/pipeline_application_service.py`
- Modify: `trade-strategy-ai/api/routers/ui/pipelines.py`
- Modify: `trade-strategy-ai/api/app.py`
- Test: `trade-strategy-ai/tests/unit/services/test_article_pipeline_schedule_service.py`
- Test: `trade-strategy-ai/tests/api/routers/test_pipelines.py`

- [ ] **Step 1: Write the failing tests**

Add tests that describe the scheduler contract:

```python
def test_schedule_service_start_stop_status(monkeypatch):
    service = ArticlePipelineScheduleService(...)
    start = asyncio.run(service.start(schedule_time="09:30", config_path="config/app.yaml", force=False))
    assert start.payload["scheduler_started"] is True
    status = asyncio.run(service.status(config_path="config/app.yaml"))
    assert status.payload["scheduler_started"] is True
    stop = asyncio.run(service.stop(config_path="config/app.yaml"))
    assert stop.payload["scheduler_started"] is False

def test_schedule_service_skips_today_when_already_complete():
    assert result.status == "ok"
    assert result.payload["message"] == "already completed"
```

Add API tests for:

```python
POST /api/ui/v1/pipelines/article_pipeline/schedule/start
POST /api/ui/v1/pipelines/article_pipeline/schedule/stop
GET  /api/ui/v1/pipelines/article_pipeline/schedule/status
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python -m pytest trade-strategy-ai/tests/unit/services/test_article_pipeline_schedule_service.py trade-strategy-ai/tests/api/routers/test_pipelines.py -q
```

Expected: route/service failures until the scheduler exists.

- [ ] **Step 3: Implement the scheduler service**

Create a dedicated in-memory scheduler service modeled after the existing `market_service` and `kaipan_service` patterns:

```python
class ArticlePipelineScheduleService(BaseService):
    service_name = "article-pipeline-schedule"

    async def start(self, *, config_path: str | Path, schedule_time: str, force: bool = False) -> ServiceResult: ...
    async def stop(self, *, config_path: str | Path) -> ServiceResult: ...
    async def status(self, *, config_path: str | Path) -> ServiceResult: ...
```

The scheduled job should:

```python
await pipeline_application_service.run_pipeline(
    pipeline_id="article_pipeline",
    params={"config_path": config_path, "force": force, "from_step": "pipeline-run"},
    created_by="article-schedule",
    confirmed=False,
)
```

The daily completion guard should:

```python
today = date.today().isoformat()
jobs = await job_service.list_jobs(job_type="pipeline-run", created_by="article-schedule", status="success", skip=0, limit=50)
if any(job["created_at"].startswith(today) for job in jobs.payload["items"]) and not force:
    return ServiceResult(status="ok", message="already completed", payload={...})
```

Keep the scheduler state in memory and expose `scheduler_started`, `schedule_time`, `force`, and `config_path` in the status payload.

- [ ] **Step 4: Wire API routes**

Add article pipeline schedule endpoints under `api/routers/ui/pipelines.py` so the UI can control the scheduler without touching generic job APIs.

- [ ] **Step 5: Re-run the focused tests**

Run:

```bash
python -m pytest trade-strategy-ai/tests/unit/services/test_article_pipeline_schedule_service.py trade-strategy-ai/tests/api/routers/test_pipelines.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai add src/services/article_pipeline_schedule_service.py src/services/pipeline_application_service.py api/routers/ui/pipelines.py api/app.py tests/unit/services/test_article_pipeline_schedule_service.py tests/api/routers/test_pipelines.py
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai commit -m "feat: add article pipeline scheduler"
```

---

### Task 3: Build the step selector and dynamic article pipeline form

**Files:**
- Modify: `trade-strategy-ai/web/src/pages/articles/ArticlePipelinePage.tsx`
- Modify: `trade-strategy-ai/web/src/lib/api/pipelines.ts`
- Modify: `trade-strategy-ai/web/src/types/pipeline.ts`
- Modify: `trade-strategy-ai/web/src/pages/articles/index.tsx`
- Test: `trade-strategy-ai/web/src/pages/articles/ArticlePipelinePage.test.tsx`
- Test: `trade-strategy-ai/web/src/pages/articles/index.test.tsx`
- Test: `trade-strategy-ai/web/src/lib/api/contract.test.ts`

- [ ] **Step 1: Write the failing tests**

Add UI tests that describe:

```tsx
it('renders step options and swaps the schema when step changes', async () => {
  expect(screen.getByLabelText('步骤')).toHaveValue('crawl');
  await user.selectOptions(screen.getByLabelText('步骤'), 'pipeline-run');
  expect(screen.getByLabelText('Force')).toBeInTheDocument();
});

it('submits the selected step with the right job type', async () => {
  expect(mockedRunArticlePipeline).toHaveBeenCalledWith(
    expect.objectContaining({
      params: expect.objectContaining({ step: 'crawl', force: true }),
    }),
  );
});
```

- [ ] **Step 2: Run the focused UI tests to verify failure**

Run:

```bash
cd /Users/wanghui/Documents/Claude/trade-strategy-ai/web && pnpm vitest run src/pages/articles/ArticlePipelinePage.test.tsx src/pages/articles/index.test.tsx src/lib/api/contract.test.ts
```

Expected: failures because the page still assumes a single `pipeline-run` form.

- [ ] **Step 3: Implement the dynamic step form**

Refactor the page so it:

```tsx
const steps = articlePipeline.workflow.steps;
const [selectedStepId, setSelectedStepId] = useState(steps[0]?.step_id ?? 'pipeline-run');
const selectedStep = steps.find((step) => step.step_id === selectedStepId);
```

The rendered form should:

```tsx
<Select aria-label="步骤" value={selectedStepId} onChange={(e) => setSelectedStepId(e.target.value)}>
  {steps.map((step) => <option key={step.step_id} value={step.step_id}>{step.title}</option>)}
</Select>
```

Render the step-specific params from the selected step schema, and always show a `Force` checkbox. Keep the existing `Profile` input as the shared execution context.

When submitting, send the selected step in the request body and preserve the current `Profile`/`config_path` mapping used by the backend.

- [ ] **Step 4: Re-run the focused UI tests**

Run:

```bash
cd /Users/wanghui/Documents/Claude/trade-strategy-ai/web && pnpm vitest run src/pages/articles/ArticlePipelinePage.test.tsx src/pages/articles/index.test.tsx src/lib/api/contract.test.ts
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai add web/src/pages/articles/ArticlePipelinePage.tsx web/src/lib/api/pipelines.ts web/src/types/pipeline.ts web/src/pages/articles/index.tsx web/src/pages/articles/ArticlePipelinePage.test.tsx web/src/pages/articles/index.test.tsx web/src/lib/api/contract.test.ts
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai commit -m "feat: add article pipeline step builder"
```

---

### Task 4: Add the schedule panel to the article page

**Files:**
- Modify: `trade-strategy-ai/web/src/pages/articles/ArticlePipelinePage.tsx`
- Modify: `trade-strategy-ai/web/src/lib/api/pipelines.ts`
- Modify: `trade-strategy-ai/web/src/types/pipeline.ts`
- Modify: `trade-strategy-ai/web/src/components/articles/*`
- Test: `trade-strategy-ai/web/src/pages/articles/ArticlePipelinePage.test.tsx`

- [ ] **Step 1: Write the failing tests**

Cover these UI states:

```tsx
it('shows scheduler running and stopped states', async () => { ... });
it('shows already completed when today already ran and force is off', async () => { ... });
it('allows force rerun when the force checkbox is checked', async () => { ... });
```

- [ ] **Step 2: Run the focused tests to verify failure**

Run:

```bash
cd /Users/wanghui/Documents/Claude/trade-strategy-ai/web && pnpm vitest run src/pages/articles/ArticlePipelinePage.test.tsx
```

Expected: failures until the panel exists.

- [ ] **Step 3: Implement the scheduler panel**

Add a dedicated section that contains:

```tsx
<Input type="time" value={scheduleTime} onChange={...} />
<CheckboxField label="Force" ... />
<Button onClick={startSchedule}>启动</Button>
<Button variant="secondary" onClick={stopSchedule}>停止</Button>
```

The panel should read scheduler status on load, render loading/error/empty states, and show the current runtime summary with the selected `config_path`/`Profile`.

- [ ] **Step 4: Re-run the focused tests**

Run:

```bash
cd /Users/wanghui/Documents/Claude/trade-strategy-ai/web && pnpm vitest run src/pages/articles/ArticlePipelinePage.test.tsx
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai add web/src/pages/articles/ArticlePipelinePage.tsx web/src/lib/api/pipelines.ts web/src/types/pipeline.ts web/src/components/articles
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai commit -m "feat: add article pipeline scheduler panel"
```

---

### Task 5: End-to-end verification and TaskList sync

**Files:**
- Modify: `trade-strategy-ai/docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- Modify: `trade-strategy-ai/docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `trade-strategy-ai/daily-sessions/2026-05-26.md` if a session note is needed
- Test: `trade-strategy-ai/tests/api/test_ui_openapi_contract.py`
- Test: `trade-strategy-ai/web/src/e2e/web-acceptance.test.tsx` if the page path changes

- [ ] **Step 1: Run the contract and integration checks**

Run:

```bash
python -m pytest trade-strategy-ai/tests/api/test_ui_openapi_contract.py trade-strategy-ai/tests/api/routers/test_pipelines.py -q
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai diff --check
```

- [ ] **Step 2: Run the targeted article pipeline and web tests**

Run:

```bash
python -m pytest trade-strategy-ai/tests/pipelines/test_article_pipeline_spec.py trade-strategy-ai/tests/unit/services/test_job_registry.py trade-strategy-ai/tests/unit/services/test_pipeline_service.py trade-strategy-ai/tests/unit/services/test_job_runner.py trade-strategy-ai/tests/unit/services/test_article_pipeline_schedule_service.py trade-strategy-ai/tests/api/routers/test_pipelines.py -q
cd /Users/wanghui/Documents/Claude/trade-strategy-ai/web && pnpm vitest run src/pages/articles/ArticlePipelinePage.test.tsx src/pages/articles/index.test.tsx src/lib/api/contract.test.ts
```

- [ ] **Step 3: Verify the article page manually if needed**

Open the article workbench and confirm:

```text
/articles
/articles/run
```

The page should show step selection, step-specific params, Force, schedule controls, and job history.

- [ ] **Step 4: Mark the tasks complete only if DoD is met**

Before changing TaskList states to `[x]`, confirm:

```text
- functionality is implemented
- relevant tests pass
- UI/API contract matches
- docs and task lists are synchronized
- no temporary mock or TODO remains
```

- [ ] **Step 5: Commit the final verification updates**

```bash
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai add docs/New-Web-Linked-TaskLists/New-Web-TaskList.md docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md docs/superpowers/plans/2026-05-26-article-pipeline-step-schedule.md
git -C /Users/wanghui/Documents/Claude/trade-strategy-ai commit -m "docs: plan article pipeline step schedule"
```

