# NW-V1-S2-002 Step Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于现有 Job audit events 归一化出结构化 Step Timeline，并让 Job Detail API 返回可直接展示的执行过程。

**Architecture:** 以 `job_audit_events` 作为唯一输入源，新增轻量的 Step Timeline contract 和归一化服务，把 Job 生命周期事件映射成稳定的 timeline item。`JobService` 负责加载 Job 与 audit events，`StepTimelineService` 负责归一化与补齐运行中/成功/失败/取消场景，`api/routers/ui/jobs.py` 只做 contract 转发，不写展示逻辑。

**Tech Stack:** Python, Pydantic, FastAPI, pytest, SQLAlchemy existing models

---

### Task 1: Add Step Timeline contract and normalizer

**Files:**
- Create: `src/models/step_timeline.py`
- Create: `src/services/step_timeline_service.py`
- Modify: `src/models/__init__.py`
- Test: `tests/unit/services/test_step_timeline_service.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import UTC, datetime

from src.services.step_timeline_service import StepTimelineService


def test_normalize_audit_events_into_step_timeline() -> None:
    service = StepTimelineService()
    timeline = service.build_job_timeline(
        job={
            "id": "job-1",
            "status": "running",
            "started_at": "2026-05-15T00:00:00+00:00",
            "finished_at": None,
            "audit_events": [
                {
                    "operation": "create",
                    "actor": "web",
                    "event_at": "2026-05-15T00:00:00+00:00",
                    "payload": {"details": {"job_type": "pipeline-run"}},
                },
                {
                    "operation": "start",
                    "actor": "worker-1",
                    "event_at": "2026-05-15T00:01:00+00:00",
                    "payload": {"details": {"worker_id": "worker-1"}},
                },
            ],
        }
    )

    assert timeline.count == 2
    assert timeline.items[0].title == "Job 创建"
    assert timeline.items[0].status == "success"
    assert timeline.items[1].title == "Job 启动"
    assert timeline.items[1].status == "running"
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `pytest tests/unit/services/test_step_timeline_service.py -v`
Expected: fail because `StepTimelineService` and timeline contract are missing.

- [ ] **Step 3: Implement the minimal contract and normalizer**

```python
class StepTimelineService:
    def build_job_timeline(self, job: dict[str, Any]) -> JobTimeline:
        ...
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `pytest tests/unit/services/test_step_timeline_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit the unit-level change**

```bash
git add src/models/step_timeline.py src/services/step_timeline_service.py src/models/__init__.py tests/unit/services/test_step_timeline_service.py
git commit -m "feat: add structured job step timeline"
```

### Task 2: Wire JobService and Job timeline API to the contract

**Files:**
- Modify: `src/services/job_service.py`
- Modify: `api/routers/ui/jobs.py`
- Modify: `src/services/__init__.py`
- Test: `tests/api/routers/test_jobs_api.py`

- [ ] **Step 1: Write the failing API test**

```python
@pytest.mark.asyncio
async def test_job_timeline_returns_structured_entries(client: AsyncClient) -> None:
    created = await client.post("/api/ui/v1/jobs", json={"job_type": "pipeline-run", "params": {}, "created_by": "web"})
    job_id = created.json()["job"]["id"]

    timeline = await client.get(f"/api/ui/v1/jobs/{job_id}/timeline")

    assert timeline.status_code == 200
    assert timeline.json()["count"] >= 1
    assert timeline.json()["items"][0]["title"]
    assert "step_id" in timeline.json()["items"][0]
```

- [ ] **Step 2: Run the API test and confirm it fails**

Run: `pytest tests/api/routers/test_jobs_api.py -v -k timeline`
Expected: fail because the router still returns raw audit events.

- [ ] **Step 3: Delegate timeline assembly to the new service**

```python
timeline = self._step_timeline_service.build_job_timeline(job=self._serialize_job(job))
```

- [ ] **Step 4: Run the API test and confirm it passes**

Run: `pytest tests/api/routers/test_jobs_api.py -v -k timeline`
Expected: PASS.

- [ ] **Step 5: Commit the API wiring change**

```bash
git add src/services/job_service.py api/routers/ui/jobs.py src/services/__init__.py tests/api/routers/test_jobs_api.py
git commit -m "feat: expose structured job timeline"
```

### Task 3: Verify the TaskList contract and record completion state

**Files:**
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- Modify: `daily-sessions/2026-05-15.md`
- Modify: `daily-report/2026-05-15.md`

- [ ] **Step 1: Confirm the acceptance criteria are met**

```text
Job Detail API 可返回 Step Timeline
成功、失败、取消场景都有 timeline
运行中任务可刷新 timeline
```

- [ ] **Step 2: Update the task state only if tests pass**

```text
NW-V1-S2-002 -> [x]
```

- [ ] **Step 3: Record the resume point**

```text
Current Task: NW-V1-S2-002
Next Task: NW-V1-S2-003
```
