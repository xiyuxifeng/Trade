# JobService Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现数据库驱动的 JobService 与受控 Worker 协议，覆盖 Job 创建、查询、状态流转、幂等、日志路径、产物引用、心跳、重试和取消请求。

**Architecture:** JobService 只管理 Job 数据，不负责执行任务。`JobRunner` 负责按白名单领取和执行 Job，并通过心跳、锁和重试退避协议维持 Worker 语义。完整日志继续写文件系统，数据库保存状态、摘要、错误、产物引用和恢复元数据。实现会复用现有 `ServiceResult` 和 `session_scope` 模式，保证后续 Web API 与 CLI 能共享同一套服务层接口。

**Tech Stack:** Python, SQLAlchemy async, Pydantic, pytest, pytest-asyncio.

---

### Task 1: 建立 JobService 最小骨架

**Files:**
- Create: `src/services/job_service.py`
- Modify: `src/services/__init__.py`
- Test: `tests/unit/services/test_job_service.py`

- [ ] **Step 1: Write the failing test**

```python
from src.services.job_service import JobService

def test_job_service_is_exported_and_instantiable():
    service = JobService()
    assert service.service_name == "job"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest trade-strategy-ai/tests/unit/services/test_job_service.py::test_job_service_is_exported_and_instantiable -v`
Expected: FAIL because `JobService` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from src.services.base import BaseService


class JobService(BaseService):
    """Job Center 的数据库服务。"""

    service_name = "job"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest trade-strategy-ai/tests/unit/services/test_job_service.py::test_job_service_is_exported_and_instantiable -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add trade-strategy-ai/src/services/job_service.py trade-strategy-ai/src/services/__init__.py trade-strategy-ai/tests/unit/services/test_job_service.py
git commit -m "feat: add job service skeleton"
```

### Task 2: 实现 Job 创建、查询和列表

**Files:**
- Modify: `src/services/job_service.py`
- Test: `tests/unit/services/test_job_service.py`

- [ ] **Step 1: Write the failing test**

```python
import asyncio
from src.models.job import JobStatus
from src.services.job_service import JobService


def test_create_get_list_job():
    service = JobService(session_scope_factory=lambda: FakeSessionScope())
    created = asyncio.run(service.create_job(job_type="backtest-run", params={"trader_id": "t1"}, created_by="web"))
    assert created.status == "ok"
    job_id = created.payload["job"]["id"]
    loaded = asyncio.run(service.get_job(job_id))
    assert loaded.payload["job"]["job_type"] == "backtest-run"
    assert loaded.payload["job"]["created_by"] == "web"
    listed = asyncio.run(service.list_jobs())
    assert listed.payload["count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest trade-strategy-ai/tests/unit/services/test_job_service.py::test_create_get_list_job -v`
Expected: FAIL because create/query/list methods do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from uuid import uuid4
from src.models.job import Job, JobStatus


async def create_job(...):
    ...


async def get_job(...):
    ...


async def list_jobs(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest trade-strategy-ai/tests/unit/services/test_job_service.py::test_create_get_list_job -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add trade-strategy-ai/src/services/job_service.py trade-strategy-ai/tests/unit/services/test_job_service.py
git commit -m "feat: add job create query list"
```

### Task 3: 实现 Job 状态流转与恢复元数据

**Files:**
- Modify: `src/services/job_service.py`
- Test: `tests/unit/services/test_job_service.py`

- [ ] **Step 1: Write the failing test**

```python
import asyncio


def test_job_state_transitions():
    service = JobService(session_scope_factory=lambda: FakeSessionScope())
    created = asyncio.run(service.create_job(job_type="pipeline-run", params={}, created_by="web"))
    job_id = created.payload["job"]["id"]
    running = asyncio.run(service.start_job(job_id=job_id, worker_id="worker-1", lock_token="lock-1"))
    assert running.payload["job"]["status"] == "running"
    finished = asyncio.run(service.complete_job(job_id=job_id, result={"ok": True}))
    assert finished.payload["job"]["status"] == "success"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest trade-strategy-ai/tests/unit/services/test_job_service.py::test_job_state_transitions -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
async def start_job(...): ...
async def complete_job(...): ...
async def fail_job(...): ...
async def cancel_job(...): ...
async def mark_timed_out(...): ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest trade-strategy-ai/tests/unit/services/test_job_service.py::test_job_state_transitions -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add trade-strategy-ai/src/services/job_service.py trade-strategy-ai/tests/unit/services/test_job_service.py
git commit -m "feat: add job state transitions"
```

### Task 4: 实现 Job 日志与产物绑定

**Files:**
- Modify: `src/services/job_service.py`
- Test: `tests/unit/services/test_job_service.py`

- [ ] **Step 1: Write the failing test**

```python
import asyncio


def test_job_log_and_artifact_binding(tmp_path):
    service = JobService(session_scope_factory=lambda: FakeSessionScope(), job_base_dir=tmp_path)
    created = asyncio.run(service.create_job(job_type="run-pre-market", params={}, created_by="web"))
    job_id = created.payload["job"]["id"]
    logged = asyncio.run(service.append_log(job_id=job_id, line="hello"))
    bound = asyncio.run(service.bind_artifact(job_id=job_id, kind="html", path=str(tmp_path / "a.html")))
    assert "job.log" in logged.payload["log_path"]
    assert bound.payload["job"]["artifacts"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest trade-strategy-ai/tests/unit/services/test_job_service.py::test_job_log_and_artifact_binding -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
async def append_log(...): ...
async def bind_artifact(...): ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest trade-strategy-ai/tests/unit/services/test_job_service.py::test_job_log_and_artifact_binding -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add trade-strategy-ai/src/services/job_service.py trade-strategy-ai/tests/unit/services/test_job_service.py
git commit -m "feat: add job logs and artifacts"
```

### Task 5: 同步导出与任务清单

**Files:**
- Modify: `src/services/__init__.py`
- Modify: `docs/Web-TaskList.md`

- [ ] **Step 1: Update exports**

```python
from src.services.job_service import JobService
```

- [ ] **Step 2: Update task list**

Mark `WEB-S2-002` as done and write the completion note once all tests pass.

- [ ] **Step 3: Run the full service test suite**

Run: `python -m pytest trade-strategy-ai/tests/unit/services -q`
Expected: PASS

- [ ] **Step 4: Ensure created_by and cancel_requested_at are preserved**

```python
async def test_cancel_job_sets_cancel_requested_at():
    created = await service.create_job(job_type="backtest-run", params={}, created_by="web")
    job_id = created.payload["job"]["id"]
    cancelled = await service.cancel_job(job_id=job_id)
    assert cancelled.payload["job"]["cancel_requested_at"] is not None
    assert cancelled.payload["job"]["created_by"] == "web"
```

- [ ] **Step 5: Commit**

```bash
git add trade-strategy-ai/src/services/__init__.py trade-strategy-ai/docs/Web-TaskList.md
git commit -m "feat: complete job service"
```

### Task 6: Worker 协议补齐

**Files:**
- Modify: `src/services/job_service.py`
- Modify: `src/services/job_runner.py`
- Modify: `src/models/job.py`
- Modify: `src/db/migrations/versions/2026_05_08_0001_add_jobs_table.py`
- Test: `tests/unit/services/test_job_service.py`
- Test: `tests/unit/services/test_job_runner.py`

- [ ] **Step 1: Ensure claim/heartbeat/cancel/retry protocol exists**
- [ ] **Step 2: Ensure max retries and backoff are stored on Job**
- [ ] **Step 3: Ensure running jobs can be heartbeated and stale jobs can be recovered**
- [ ] **Step 4: Ensure cancel on running jobs is request-only and finalizes on completion**
- [ ] **Step 5: Run service test suite and commit**
