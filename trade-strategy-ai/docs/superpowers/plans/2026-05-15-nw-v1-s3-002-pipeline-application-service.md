# NW-V1-S3-002 Pipeline Application Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `article_pipeline` the canonical Web/API entry for the article processing demo while keeping `pipeline` as an explicit legacy compatibility path.

**Architecture:** Introduce a thin `PipelineApplicationService` that owns article pipeline catalog lookup, canonical `article_pipeline` detail assembly, and request orchestration. It will build a workflow-shaped execution object from `article_pipeline_spec`, delegate execution to the existing `WorkflowRunner`, and rely on `JobRunner` and `PipelineService` for the actual crawl / pipeline-run / pipeline-step work. The existing generic `WorkflowService` remains in place for other workflows, but the article pipeline route stops depending on it directly.

**Tech Stack:** Python, FastAPI, pytest, existing service layer, existing job/timeline/artifact contracts.

---

### Task 1: Define the application service contract

**Files:**
- Create: `src/services/pipeline_application_service.py`
- Modify: `tests/unit/services/test_pipeline_application_service.py`

- [ ] **Step 1: Write the failing test**

```python
from dataclasses import dataclass


@dataclass
class _FakeWorkflowRunner:
    calls: list[dict]

    async def run_workflow(self, **kwargs):
        self.calls.append(kwargs)
        return type("Result", (), {"status": "ok", "message": "workflow completed", "payload": {"job": {"id": "job-1"}}})()


def test_pipeline_service_lists_only_article_pipeline():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/services/test_pipeline_application_service.py -v`

Expected: fail because the service file and methods do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class PipelineApplicationService(BaseService):
    async def list_pipelines(self) -> ServiceResult: ...
    async def get_pipeline(self, pipeline_id: str) -> ServiceResult: ...
    async def run_pipeline(self, *, pipeline_id: str, params: dict[str, Any] | None = None, created_by: str | None = None, idempotency_key: str | None = None, confirmed: bool = False, audit_source: dict[str, Any] | None = None) -> ServiceResult: ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/services/test_pipeline_application_service.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/pipeline_application_service.py tests/unit/services/test_pipeline_application_service.py
git commit -m "test: add pipeline application service contract"
```

### Task 2: Implement canonical article_pipeline orchestration

**Files:**
- Modify: `src/services/pipeline_application_service.py`
- Modify: `src/services/__init__.py`
- Modify: `tests/unit/services/test_pipeline_application_service.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_pipeline_service_runs_article_pipeline_through_workflow_runner():
    ...
    assert fake_runner.calls[0]["workflow"].workflow_id == "article_pipeline"
    assert fake_runner.calls[0]["workflow"].steps[0].required_job_type == "crawl"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/services/test_pipeline_application_service.py -v`

Expected: FAIL because orchestration and canonical workflow assembly are not implemented yet.

- [ ] **Step 3: Write minimal implementation**

```python
from src.pipelines.article_pipeline_spec import ARTICLE_PIPELINE_SPEC
from src.services.workflow_service import WorkflowDefinition, WorkflowStep


def _build_article_workflow() -> WorkflowDefinition:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/services/test_pipeline_application_service.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/pipeline_application_service.py src/services/__init__.py tests/unit/services/test_pipeline_application_service.py
git commit -m "feat: add article pipeline application service"
```

### Task 3: Switch the UI pipeline router to the new service

**Files:**
- Modify: `api/routers/ui/pipelines.py`
- Modify: `tests/api/routers/test_pipelines.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_article_pipeline_routes_use_application_service():
    ...
    assert client.fake_service.run_calls[0]["pipeline_id"] == "article_pipeline"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/api/routers/test_pipelines.py -v`

Expected: FAIL because the router still depends on WorkflowService.

- [ ] **Step 3: Write minimal implementation**

```python
router = APIRouter(prefix="/api/ui/v1/pipelines", tags=["ui-pipelines"])

def get_pipeline_application_service(job_service: JobService = Depends(get_job_service)) -> PipelineApplicationService:
    return make_pipeline_application_service(job_service=job_service)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/api/routers/test_pipelines.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/routers/ui/pipelines.py tests/api/routers/test_pipelines.py
git commit -m "feat: route article pipeline through application service"
```

### Task 4: Sync task list and validate the boundary

**Files:**
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- Modify: `daily-sessions/2026-05-15.md`
- Modify: `daily-report/2026-05-15.md`

- [ ] **Step 1: Update the task notes**

Record that `article_pipeline` is canonical, `pipeline` is compat, and the UI router no longer depends on `WorkflowService` for article pipeline execution.

- [ ] **Step 2: Run regression tests**

Run:
`pytest tests/unit/services/test_pipeline_application_service.py -v`
`pytest tests/api/routers/test_pipelines.py -v`
`pytest tests/api/test_ui_openapi_contract.py -v`

- [ ] **Step 3: Commit the documentation sync**

```bash
git add docs/New-Web-Linked-TaskLists/New-Web-TaskList.md daily-sessions/2026-05-15.md daily-report/2026-05-15.md
git commit -m "docs: sync nw-v1-s3-002 boundary"
```

---

## Self-Review

- Spec coverage: the plan covers the article pipeline application service, route wiring, and task/doc sync.
- Placeholder scan: no TBD/TODO placeholders remain in the actual implementation tasks.
- Type consistency: the service uses `PipelineApplicationService`, `WorkflowRunner`, `WorkflowDefinition`, and `WorkflowStep` consistently across tests and implementation tasks.
