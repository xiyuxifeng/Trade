"""Job UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator
from types import SimpleNamespace

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.jobs import get_job_service

_job_service_spy: _FakeJobService | None = None


@dataclass
class _FakeJobService:
    """用于 UI 路由测试的轻量 JobService 替身。"""

    jobs: dict[str, dict[str, Any]] = field(default_factory=dict)
    create_calls: list[dict[str, Any]] = field(default_factory=list)
    cancel_calls: list[dict[str, Any]] = field(default_factory=list)

    async def create_job(self, **kwargs: Any) -> Any:
        job_id = f"job-{len(self.jobs) + 1}"
        job = {
            "id": job_id,
            "job_type": kwargs["job_type"],
            "status": "pending",
            "params": kwargs.get("params", {}),
            "result": None,
            "error": None,
            "progress": None,
            "artifacts": [],
            "created_by": kwargs.get("created_by") or "system",
            "idempotency_key": kwargs.get("idempotency_key"),
            "retry_count": 0,
            "max_retries": kwargs.get("max_retries", 3),
            "retry_backoff_seconds": kwargs.get("retry_backoff_seconds", 0),
            "timeout_seconds": kwargs.get("timeout_seconds"),
            "cancel_requested": False,
            "cancel_requested_at": None,
            "worker_id": None,
            "lock_token": None,
            "lock_acquired_at": None,
            "heartbeat_at": None,
            "scheduled_at": None,
            "started_at": None,
            "finished_at": None,
            "created_at": "2026-05-09T00:00:00",
            "updated_at": "2026-05-09T00:00:00",
            "audit_events": [
                {
                    "operation": "create",
                    "actor": kwargs.get("created_by") or "system",
                    "event_at": "2026-05-09T00:00:00",
                    "payload": {"job_type": kwargs["job_type"]},
                }
            ],
        }
        self.jobs[job_id] = job
        self.create_calls.append(kwargs)
        return _service_result(
            {
                "created": True,
                "job": job,
                "job_dir": str(Path("/tmp") / job_id),
                "log_path": str(Path("/tmp") / job_id / "job.log"),
                "params_path": str(Path("/tmp") / job_id / "params.json"),
                "result_path": str(Path("/tmp") / job_id / "result.json"),
                "artifacts_path": str(Path("/tmp") / job_id / "artifacts.json"),
            }
        )

    async def list_jobs(self, **kwargs: Any) -> Any:
        items = list(self.jobs.values())
        return _service_result({"count": len(items), "total": len(items), "skip": 0, "limit": 50, "items": items})

    async def get_job(self, job_id: str) -> Any:
        job = self.jobs.get(job_id)
        if job is None:
            return _service_result({"job_id": job_id}, status="partial", message="job not found")
        return _service_result(
            {
                "job": job,
                "job_dir": str(Path("/tmp") / job_id),
                "log_path": str(Path("/tmp") / job_id / "job.log"),
                "params_path": str(Path("/tmp") / job_id / "params.json"),
                "result_path": str(Path("/tmp") / job_id / "result.json"),
                "artifacts_path": str(Path("/tmp") / job_id / "artifacts.json"),
            }
        )

    async def get_job_timeline(self, job_id: str) -> Any:
        job = self.jobs.get(job_id)
        if job is None:
            return _service_result({"job_id": job_id}, status="partial", message="job not found")

        items: list[dict[str, Any]] = []
        for index, event in enumerate(job.get("audit_events") or [], start=1):
            operation = event.get("operation") or "unknown"
            status = "success"
            if operation in {"start", "heartbeat"} and job.get("status") == "running":
                status = "running"
            elif operation == "fail":
                status = "failed"
            elif operation == "cancel" or job.get("status") == "cancelled":
                status = "cancelled"
            items.append(
                {
                    "step_id": "job.heartbeat.%s" % index if operation == "heartbeat" else f"job.{operation}",
                    "step_name": operation,
                    "title": {
                        "create": "Job 创建",
                        "start": "Job 启动",
                        "heartbeat": "Job 心跳",
                        "complete": "Job 完成",
                        "fail": "Job 失败",
                        "cancel": "Job 取消",
                        "bind_artifact": "产物绑定",
                    }.get(operation, f"Job {operation}"),
                    "status": status,
                    "started_at": event.get("event_at"),
                    "finished_at": None if status == "running" else event.get("event_at"),
                    "duration_ms": None if status == "running" else 0,
                    "error": None,
                    "artifact_refs": [],
                    "order": index,
                    "operation": operation,
                    "actor": event.get("actor"),
                    "source": event.get("source", "system"),
                    "metadata": {},
                }
            )

        return _service_result(
            {
                "job_id": job_id,
                "job_status": job.get("status"),
                "count": len(items),
                "items": items,
                "metadata": {},
            }
        )

    async def cancel_job(self, **kwargs: Any) -> Any:
        self.cancel_calls.append(kwargs)
        job_id = kwargs["job_id"]
        job = self.jobs.get(job_id)
        if job is not None:
            job["status"] = "cancelled"
            job["cancel_requested"] = True
            job["cancel_requested_at"] = "2026-05-09T00:00:00"
        return _service_result(
            {
                "job": job,
                "job_dir": str(Path("/tmp") / job_id),
                "log_path": str(Path("/tmp") / job_id / "job.log"),
                "params_path": str(Path("/tmp") / job_id / "params.json"),
                "result_path": str(Path("/tmp") / job_id / "result.json"),
                "artifacts_path": str(Path("/tmp") / job_id / "artifacts.json"),
            }
        )


def _service_result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    """构造测试用的 ServiceResult 替身。"""
    return SimpleNamespace(status=status, message=message, payload=payload)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建带认证覆盖的测试客户端。"""
    global _job_service_spy
    fake_service = _FakeJobService()
    _job_service_spy = fake_service
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="operator",
            api_key_label="Operator",
            authenticated=True,
            source="api_key",
            api_key="operator-key",
        )
        app.dependency_overrides[get_job_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_list_detail_logs_and_cancel_jobs(client: AsyncClient) -> None:
    """Job UI API 应支持创建、列表、详情、日志和取消。"""
    created = await client.post(
        "/api/ui/v1/jobs",
        json={
            "job_type": "pipeline-run",
            "params": {"config_path": "config/app.yaml"},
            "created_by": "web",
        },
    )
    assert created.status_code == 200
    job_id = created.json()["job"]["id"]
    assert _job_service_spy is not None
    assert _job_service_spy.create_calls[0]["confirmed"] is False
    assert _job_service_spy.create_calls[0]["audit_source"]["channel"] == "ui"
    assert _job_service_spy.create_calls[0]["audit_source"]["path"] == "/api/ui/v1/jobs"
    assert created.json()["job"]["progress"] is None

    listed = await client.get("/api/ui/v1/jobs")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == job_id
    assert listed.json()["items"][0]["progress"] is None

    detail = await client.get(f"/api/ui/v1/jobs/{job_id}")
    assert detail.status_code == 200
    assert detail.json()["job"]["id"] == job_id
    assert detail.json()["job"]["progress"] is None

    logs = await client.get(f"/api/ui/v1/jobs/{job_id}/logs")
    assert logs.status_code == 200
    assert logs.json()["items"] == []

    timeline = await client.get(f"/api/ui/v1/jobs/{job_id}/timeline")
    assert timeline.status_code == 200
    assert timeline.json()["items"][0]["operation"] == "create"

    artifacts = await client.get(f"/api/ui/v1/jobs/{job_id}/artifacts")
    assert artifacts.status_code == 200
    assert artifacts.json() == {"job_id": job_id, "count": 0, "items": []}

    cancelled = await client.post(f"/api/ui/v1/jobs/{job_id}/cancel", json={"reason": "stop now"})
    assert cancelled.status_code == 200
    assert cancelled.json()["job"]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_job_timeline_returns_structured_contract(client: AsyncClient) -> None:
    """Job Timeline 应返回结构化执行过程，而不是 raw audit event。"""
    created = await client.post(
        "/api/ui/v1/jobs",
        json={
            "job_type": "pipeline-run",
            "params": {"config_path": "config/app.yaml"},
            "created_by": "web",
        },
    )
    assert created.status_code == 200
    job_id = created.json()["job"]["id"]

    timeline = await client.get(f"/api/ui/v1/jobs/{job_id}/timeline")
    assert timeline.status_code == 200
    payload = timeline.json()
    assert payload["count"] >= 1
    assert payload["items"][0]["title"] == "Job 创建"
    assert payload["items"][0]["status"] == "success"
    assert payload["items"][0]["step_name"] == "create"
    assert payload["items"][0]["step_id"] == "job.create"


@pytest.mark.asyncio
async def test_high_risk_job_requires_confirmation(client: AsyncClient) -> None:
    """高风险 Job 未确认时不应创建，确认后才可创建。"""
    rejected = await client.post(
        "/api/ui/v1/jobs",
        json={
            "job_type": "init-project",
            "params": {"config_path": "config/app.yaml"},
            "created_by": "web",
        },
    )
    assert rejected.status_code == 400
    assert "confirmation required" in rejected.json()["detail"]

    approved = await client.post(
        "/api/ui/v1/jobs",
        json={
            "job_type": "init-project",
            "params": {"config_path": "config/app.yaml"},
            "created_by": "web",
            "confirmed": True,
        },
    )
    assert approved.status_code == 200
    assert approved.json()["job"]["job_type"] == "init-project"
    assert _job_service_spy is not None
    assert _job_service_spy.create_calls[-1]["confirmed"] is True


@pytest.mark.asyncio
async def test_viewer_cannot_create_jobs(client: AsyncClient) -> None:
    """viewer 不能创建 Job。"""
    previous = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="viewer",
        api_key_label="Viewer",
        authenticated=True,
        source="api_key",
        api_key="viewer-key",
    )
    try:
        response = await client.post(
            "/api/ui/v1/jobs",
            json={
                "job_type": "pipeline-run",
                "params": {"config_path": "config/app.yaml"},
                "created_by": "web",
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "insufficient permissions"
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous
