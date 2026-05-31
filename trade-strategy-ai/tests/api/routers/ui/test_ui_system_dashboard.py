from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui.system import get_system_service


@dataclass
class _FakeSystemService:
    calls: list[str]

    def __init__(self) -> None:
        self.calls = []

    async def build_dashboard_summary(
        self,
        *,
        profile_id: str | None = None,
        config_path: str | None = None,
    ) -> Any:
        self.calls.append("build_dashboard_summary")
        return type(
            "Result",
            (),
            {
                "payload": {
                    "status": "partial",
                    "generated_at": "2026-05-11T09:10:00Z",
                    "health": {"database": {"status": "ok", "latency_ms": 3.2}},
                    "worker": {"status": "ok", "heartbeat_at": "2026-05-11T09:05:30Z"},
                    "failed_jobs": [{"id": "job-failed-1"}],
                    "duration_summary": {"average_seconds": 240.0, "p95_seconds": 300.0, "recent_jobs": []},
                    "freshness": {"sources": [{"source": "market_data", "entity_type": "market", "is_stale": True}]},
                    "alerts": {"critical": 1, "warning": 0, "latest": [{"level": "critical", "title": "stale market data"}]},
                    "traces": [{"job_id": "job-failed-1", "request_context": {"path": "/api/ui/v1/jobs", "method": "POST"}}],
                }
            },
        )()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    fake_service = _FakeSystemService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_system_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_system_dashboard_returns_operational_summary(client: AsyncClient) -> None:
    """系统 Dashboard 路由应返回运维摘要。"""
    response = await client.get("/api/ui/v1/system/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["failed_jobs"][0]["id"] == "job-failed-1"
    assert payload["alerts"]["critical"] == 1
