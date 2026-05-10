"""Workflow UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.workflows import get_workflow_service

_workflow_service_spy: _FakeWorkflowService | None = None


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
        return _result(
            {
                "workflow": {"workflow_id": kwargs["workflow_id"], "job_type": "run-pre-market"},
                "job": {"id": "job-1", "job_type": "run-pre-market"},
            }
        )


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(status=status, message=message, payload=payload)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建带认证覆盖的测试客户端。"""
    global _workflow_service_spy
    fake_service = _FakeWorkflowService(run_calls=[])
    _workflow_service_spy = fake_service
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
