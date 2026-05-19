"""Job audit UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.job_audits import get_job_audit_query_service


@dataclass
class _FakeJobAuditQueryService:
    """Job Audit API 测试用的替身。"""

    list_calls: list[dict[str, Any]] = field(default_factory=list)
    detail_calls: list[str] = field(default_factory=list)

    async def list_job_audits(self, **kwargs: Any) -> Any:
        self.list_calls.append(kwargs)
        return _result(
            {
                "filters": kwargs,
                "summary": {
                    "total": 1,
                    "confirmed_count": 1,
                    "high_risk_count": 1,
                    "unique_jobs": 1,
                    "operation_counts": {"create": 1},
                },
                "page": {"total": 1, "skip": kwargs.get("skip", 0), "limit": kwargs.get("limit", 50), "count": 1},
                "items": [
                    {
                        "id": "audit-1",
                        "job_id": "job-1",
                        "job_type": "pipeline-run",
                        "job_status": "success",
                        "created_by": "web",
                        "operation": "create",
                        "actor": "web",
                        "source": "ui",
                        "confirmed": True,
                        "params_summary": {"config_path": "config/app.yaml"},
                        "payload": {"request_context": {"confirmed": True}},
                        "event_at": "2026-05-17T00:00:00+00:00",
                        "created_at": "2026-05-17T00:00:00+00:00",
                        "updated_at": "2026-05-17T00:00:00+00:00",
                    }
                ],
            }
        )

    async def get_job_audit_detail(self, job_id: str) -> Any:
        self.detail_calls.append(job_id)
        if job_id == "missing":
            return _result({"job_id": job_id}, status="partial", message="job not found")
        return _result(
            {
                "job": {
                    "id": job_id,
                    "job_type": "pipeline-run",
                    "status": "success",
                    "created_by": "web",
                    "retry_count": 0,
                    "max_retries": 3,
                    "retry_backoff_seconds": 0,
                    "timeout_seconds": None,
                    "cancel_requested": False,
                    "cancel_requested_at": None,
                    "worker_id": "worker-1",
                    "lock_acquired_at": None,
                    "heartbeat_at": None,
                    "scheduled_at": None,
                    "started_at": "2026-05-17T00:00:00+00:00",
                    "finished_at": "2026-05-17T00:02:00+00:00",
                    "created_at": "2026-05-17T00:00:00+00:00",
                    "updated_at": "2026-05-17T00:02:00+00:00",
                    "artifacts": [
                        {
                            "artifact_id": "artifact-1",
                            "job_id": job_id,
                            "workflow_id": None,
                            "step_id": None,
                            "kind": "report",
                            "title": "回测报告",
                            "summary": "report",
                            "safe_download_url": "/api/ui/v1/artifacts/artifact-1/download",
                            "download_token": None,
                            "size_bytes": 1024,
                            "created_at": "2026-05-17T00:02:00+00:00",
                            "visibility": "internal",
                            "metadata": {},
                            "storage_ref": None,
                        }
                    ],
                },
                "summary": {"event_count": 2, "confirmed_count": 1, "high_risk_count": 1, "has_artifacts": True},
                "request_context": {"channel": "ui", "path": "/api/ui/v1/jobs", "confirmed": True},
                "items": [
                    {
                        "id": "audit-1",
                        "job_id": job_id,
                        "job_type": "pipeline-run",
                        "job_status": "success",
                        "created_by": "web",
                        "operation": "create",
                        "actor": "web",
                        "source": "ui",
                        "confirmed": True,
                        "params_summary": {"config_path": "config/app.yaml"},
                        "payload": {"request_context": {"confirmed": True}},
                        "event_at": "2026-05-17T00:00:00+00:00",
                        "created_at": "2026-05-17T00:00:00+00:00",
                        "updated_at": "2026-05-17T00:00:00+00:00",
                    }
                ],
            }
        )


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(status=status, message=message, payload=payload)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建带认证覆盖的测试客户端。"""
    fake_service = _FakeJobAuditQueryService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="admin",
            api_key_label="Admin",
            authenticated=True,
            source="api_key",
            api_key="admin-key",
        )
        app.dependency_overrides[get_job_audit_query_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.fake_service = fake_service  # type: ignore[attr-defined]
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_and_get_job_audits(client: AsyncClient) -> None:
    """Job 审计 API 应支持列表和详情。"""
    listed = await client.get(
        "/api/ui/v1/job-audits",
        params={
            "actor": "web",
            "job_type": "pipeline-run",
            "operation": "create",
            "confirmed": "true",
            "start_date": "2026-05-17",
            "end_date": "2026-05-17",
        },
    )
    assert listed.status_code == 200
    assert listed.json()["items"][0]["job_id"] == "job-1"
    assert client.fake_service.list_calls[0]["confirmed"] is True  # type: ignore[attr-defined]

    detail = await client.get("/api/ui/v1/job-audits/job-1")
    assert detail.status_code == 200
    assert detail.json()["job"]["id"] == "job-1"


@pytest.mark.asyncio
async def test_viewer_cannot_access_job_audits(client: AsyncClient) -> None:
    """viewer 不能访问 Job 审计 UI API。"""
    previous = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="viewer",
        api_key_label="Viewer",
        authenticated=True,
        source="api_key",
        api_key="viewer-key",
    )
    try:
        response = await client.get("/api/ui/v1/job-audits")
        assert response.status_code == 403
        assert response.json()["detail"] == "insufficient permissions"
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous


@pytest.mark.asyncio
async def test_session_admin_can_access_job_audits_without_api_key_override(client: AsyncClient) -> None:
    """session admin 应可直接访问 Job 审计 UI API。"""
    previous_principal = app.dependency_overrides.get(get_current_principal)
    previous_verify = app.dependency_overrides.pop(verify_api_key, None)
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="admin",
        api_key_label="Local Admin",
        authenticated=True,
        source="session",
        api_key="session-token",
    )
    try:
        response = await client.get("/api/ui/v1/job-audits")
        assert response.status_code == 200
        assert response.json()["items"][0]["job_id"] == "job-1"
    finally:
        if previous_principal is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_principal
        if previous_verify is None:
            app.dependency_overrides.pop(verify_api_key, None)
        else:
            app.dependency_overrides[verify_api_key] = previous_verify
