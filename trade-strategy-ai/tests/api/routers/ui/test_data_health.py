"""Data Health UI BFF 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui.data_health import get_dashboard_service
from src.services.base import ServiceResult


@dataclass
class _FakeDashboardService:
    calls: list[dict[str, Any]]

    def __init__(self) -> None:
        self.calls = []

    async def build_report(self, *, config_path: str, mode: str = "cli", output: str | None = None) -> ServiceResult:
        self.calls.append({"config_path": config_path, "mode": mode, "output": output})
        return ServiceResult(
            status="ok",
            message="dashboard report built",
            payload={
                "config_path": config_path,
                "report": {"title": "Daily Health", "alerts": []},
                "html_path": "/tmp/project/data/processed/dashboard/dashboard.html",
                "critical_alerts": 0,
                "exit_code": 0,
            },
        )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    fake_service = _FakeDashboardService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_dashboard_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_returns_report(client: AsyncClient) -> None:
    """dashboard 接口应返回报告摘要。"""
    response = await client.get("/api/ui/v1/data-health/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert "report" in payload
