"""Workflow UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.workflows import get_workflow_run_service, get_workflow_service

_workflow_service_spy: _FakeWorkflowService | None = None
_workflow_run_service_spy: _FakeWorkflowRunService | None = None


@dataclass
class _FakeWorkflowService:
    """Workflow API 单测用的替身。"""

    run_calls: list[dict[str, Any]]

    async def list_workflows(self) -> Any:
        return _result({"count": 1, "items": [{"workflow_id": "pre-market", "job_type": "run-pre-market"}]})

    async def get_workflow(self, workflow_id: str) -> Any:
        if workflow_id != "pre-market":
            return _result({"workflow_id": workflow_id}, status="partial", message="workflow not found")
        return _result({"workflow": {"workflow_id": "pre-market", "job_type": "run-pre-market"}})

    async def run_workflow(self, **kwargs: Any) -> Any:
        self.run_calls.append(kwargs)
        if kwargs["workflow_id"] == "init-project" and not kwargs.get("confirmed"):
            return _result(
                {
                    "workflow_id": kwargs["workflow_id"],
                    "workflow": {
                        "workflow_id": "init-project",
                        "job_type": "init-project",
                    },
                    "requires_confirmation": True,
                },
                status="error",
                message="confirmation required for high-risk workflow",
            )
        return _result(
            {
                "workflow": {"workflow_id": kwargs["workflow_id"], "job_type": "run-pre-market"},
                "job": {"id": "job-1", "job_type": "run-pre-market"},
            }
        )


@dataclass
class _FakeWorkflowRunService:
    """Workflow run API 单测用的替身。"""

    list_calls: list[dict[str, Any]]
    detail_calls: list[str]
    step_calls: list[dict[str, Any]]

    async def list_workflow_runs(self, **kwargs: Any) -> Any:
        self.list_calls.append(kwargs)
        return _result(
            {
                "filters": {
                    "workflow_id": kwargs.get("workflow_id"),
                    "status": kwargs.get("status"),
                    "created_by": kwargs.get("created_by"),
                },
                "page": {"total": 1, "limit": kwargs.get("limit", 50), "offset": kwargs.get("offset", 0), "count": 1},
                "items": [
                    {
                        "id": "run-1",
                        "workflow_id": "pre-market",
                        "workflow_title": "盘前工作台",
                        "workflow_version": "kaipan-run",
                        "status": "success",
                        "trigger_source": "ui",
                        "created_by": "web",
                        "confirmed": True,
                        "idempotency_key": "run-1",
                        "started_at": "2026-05-16T09:30:00+00:00",
                        "finished_at": "2026-05-16T09:32:00+00:00",
                        "duration_ms": 120000,
                        "input_params_json": {"config_path": "config/app.yaml"},
                        "output_summary_json": {"step_count": 1},
                        "error_json": None,
                        "metadata_json": {"workflow_summary": {"workflow_id": "pre-market"}},
                        "created_at": "2026-05-16T09:30:00+00:00",
                        "updated_at": "2026-05-16T09:32:00+00:00",
                    }
                ],
            }
        )

    async def get_workflow_run(self, workflow_run_id: str) -> Any:
        self.detail_calls.append(workflow_run_id)
        if workflow_run_id == "not-a-uuid":
            return _result(
                {
                    "error": {
                        "type": "invalid_query",
                        "message": "invalid workflow run id",
                        "detail": "bad uuid",
                        "metadata": {"workflow_run_id": workflow_run_id},
                    }
                },
                status="error",
                message="invalid workflow run id",
            )
        if workflow_run_id == "run-missing":
            return _result({"error": {"type": "workflow_run_not_found", "message": "workflow run not found", "detail": workflow_run_id, "metadata": {"workflow_run_id": workflow_run_id}}}, status="partial", message="workflow run not found")
        return _result(
            {
                "workflow_run": {
                    "id": workflow_run_id,
                    "workflow_id": "pre-market",
                    "workflow_title": "盘前工作台",
                    "workflow_version": "kaipan-run",
                    "status": "success",
                    "trigger_source": "ui",
                    "created_by": "web",
                    "confirmed": True,
                    "idempotency_key": "run-1",
                    "started_at": "2026-05-16T09:30:00+00:00",
                    "finished_at": "2026-05-16T09:32:00+00:00",
                    "duration_ms": 120000,
                    "input_params_json": {"config_path": "config/app.yaml"},
                    "output_summary_json": {"step_count": 1},
                    "error_json": None,
                    "metadata_json": {"workflow_summary": {"workflow_id": "pre-market"}},
                    "created_at": "2026-05-16T09:30:00+00:00",
                    "updated_at": "2026-05-16T09:32:00+00:00",
                },
                "steps": [
                    {
                        "id": "step-1",
                        "workflow_run_id": workflow_run_id,
                        "step_id": "run-pre-market",
                        "step_name": "盘前报表",
                        "step_order": 1,
                        "job_id": "job-1",
                        "job_type": "run-pre-market",
                        "status": "success",
                        "started_at": "2026-05-16T09:30:00+00:00",
                        "finished_at": "2026-05-16T09:31:00+00:00",
                        "duration_ms": 60000,
                        "input_json": {"workflow_id": "pre-market"},
                        "output_json": {"job_type": "run-pre-market"},
                        "error_json": None,
                        "artifact_refs_json": [],
                        "metadata_json": {"workflow_step_id": "run-pre-market"},
                        "created_at": "2026-05-16T09:30:00+00:00",
                        "updated_at": "2026-05-16T09:31:00+00:00",
                    }
                ],
                "page": {"total": 1, "limit": 1, "offset": 0, "count": 1},
            }
        )

    async def list_workflow_run_steps(self, workflow_run_id: str, **kwargs: Any) -> Any:
        self.step_calls.append({"workflow_run_id": workflow_run_id, **kwargs})
        if workflow_run_id == "not-a-uuid":
            return _result(
                {
                    "error": {
                        "type": "invalid_query",
                        "message": "invalid workflow run id",
                        "detail": "bad uuid",
                        "metadata": {"workflow_run_id": workflow_run_id},
                    }
                },
                status="error",
                message="invalid workflow run id",
            )
        return _result(
            {
                "workflow_run_id": workflow_run_id,
                "page": {"total": 1, "limit": kwargs.get("limit", 200), "offset": kwargs.get("offset", 0), "count": 1},
                "items": [
                    {
                        "id": "step-1",
                        "workflow_run_id": workflow_run_id,
                        "step_id": "run-pre-market",
                        "step_name": "盘前报表",
                        "step_order": 1,
                        "job_id": "job-1",
                        "job_type": "run-pre-market",
                        "status": "success",
                        "started_at": "2026-05-16T09:30:00+00:00",
                        "finished_at": "2026-05-16T09:31:00+00:00",
                        "duration_ms": 60000,
                        "input_json": {"workflow_id": "pre-market"},
                        "output_json": {"job_type": "run-pre-market"},
                        "error_json": None,
                        "artifact_refs_json": [],
                        "metadata_json": {"workflow_step_id": "run-pre-market"},
                        "created_at": "2026-05-16T09:30:00+00:00",
                        "updated_at": "2026-05-16T09:31:00+00:00",
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
    global _workflow_service_spy
    global _workflow_run_service_spy
    fake_service = _FakeWorkflowService(run_calls=[])
    fake_run_service = _FakeWorkflowRunService(list_calls=[], detail_calls=[], step_calls=[])
    _workflow_service_spy = fake_service
    _workflow_run_service_spy = fake_run_service
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
        app.dependency_overrides[get_workflow_service] = lambda: fake_service
        app.dependency_overrides[get_workflow_run_service] = lambda: fake_run_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_get_and_run_workflows(client: AsyncClient) -> None:
    """Workflow UI API 应支持列表、详情和运行。"""
    listed = await client.get("/api/ui/v1/workflows")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["workflow_id"] == "pre-market"

    detail = await client.get("/api/ui/v1/workflows/pre-market")
    assert detail.status_code == 200
    assert detail.json()["workflow"]["workflow_id"] == "pre-market"

    run = await client.post(
        "/api/ui/v1/workflows/pre-market/run",
        json={"params": {"config_path": "config/app.yaml"}, "created_by": "web", "confirmed": True},
    )
    assert run.status_code == 200
    assert run.json()["job"]["job_type"] == "run-pre-market"
    assert _workflow_service_spy is not None
    assert _workflow_service_spy.run_calls[0]["confirmed"] is True
    assert _workflow_service_spy.run_calls[0]["audit_source"]["channel"] == "ui"
    assert _workflow_service_spy.run_calls[0]["audit_source"]["path"] == "/api/ui/v1/workflows/pre-market/run"


@pytest.mark.asyncio
async def test_viewer_cannot_run_workflow(client: AsyncClient) -> None:
    """viewer 不能运行 Workflow。"""
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
            "/api/ui/v1/workflows/pre-market/run",
            json={"params": {"config_path": "config/app.yaml"}, "created_by": "web", "confirmed": True},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "insufficient permissions"
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous


@pytest.mark.asyncio
async def test_high_risk_workflow_requires_confirmation(client: AsyncClient) -> None:
    """高风险 Workflow 未确认时应被拒绝，确认后才可运行。"""
    rejected = await client.post(
        "/api/ui/v1/workflows/init-project/run",
        json={"params": {"config_path": "config/app.yaml"}, "created_by": "web", "confirmed": False},
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "confirmation required for high-risk workflow"

    approved = await client.post(
        "/api/ui/v1/workflows/init-project/run",
        json={"params": {"config_path": "config/app.yaml"}, "created_by": "web", "confirmed": True},
    )
    assert approved.status_code == 200
    assert approved.json()["workflow"]["workflow_id"] == "init-project"


@pytest.mark.asyncio
async def test_list_and_get_workflow_runs(client: AsyncClient) -> None:
    """Workflow run 查询 API 应支持列表、详情和 step 明细。"""
    listed = await client.get("/api/ui/v1/workflows/runs?workflow_id=pre-market&status=success&created_by=web")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["workflow_id"] == "pre-market"
    assert _workflow_run_service_spy is not None
    assert _workflow_run_service_spy.list_calls[0]["workflow_id"] == "pre-market"

    detail = await client.get("/api/ui/v1/workflows/runs/run-1")
    assert detail.status_code == 200
    assert detail.json()["workflow_run"]["id"] == "run-1"

    steps = await client.get("/api/ui/v1/workflows/runs/run-1/steps")
    assert steps.status_code == 200
    assert steps.json()["items"][0]["step_id"] == "run-pre-market"


@pytest.mark.asyncio
async def test_missing_workflow_run_returns_404(client: AsyncClient) -> None:
    """不存在的 workflow run 应返回结构化 404。"""
    response = await client.get("/api/ui/v1/workflows/runs/run-missing")
    assert response.status_code == 404
    assert response.json()["detail"]["type"] == "workflow_run_not_found"


@pytest.mark.asyncio
async def test_invalid_workflow_run_id_returns_422(client: AsyncClient) -> None:
    """非法 workflow run id 应返回结构化 422。"""
    response = await client.get("/api/ui/v1/workflows/runs/not-a-uuid")
    assert response.status_code == 422
    assert response.json()["detail"]["type"] == "invalid_query"
