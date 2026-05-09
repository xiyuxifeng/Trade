"""Job UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui.jobs import get_job_service


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


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建带认证覆盖的测试客户端。"""
    fake_service = _FakeJobService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
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

    listed = await client.get("/api/ui/v1/jobs")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == job_id

    detail = await client.get(f"/api/ui/v1/jobs/{job_id}")
    assert detail.status_code == 200
    assert detail.json()["job"]["id"] == job_id

    logs = await client.get(f"/api/ui/v1/jobs/{job_id}/logs")
    assert logs.status_code == 200
    assert logs.json()["items"] == []

    cancelled = await client.post(f"/api/ui/v1/jobs/{job_id}/cancel", json={"reason": "stop now"})
    assert cancelled.status_code == 200
    assert cancelled.json()["job"]["status"] == "cancelled"
