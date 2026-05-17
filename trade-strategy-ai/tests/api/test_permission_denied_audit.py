from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

import api.app as api_app


@dataclass
class _FakeAuditService:
    """记录 403 审计写入调用的替身。"""

    calls: list[dict[str, Any]] = field(default_factory=list)

    async def record(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return kwargs


@pytest.mark.asyncio
async def test_forbidden_requests_are_recorded_as_permission_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_service = _FakeAuditService()
    monkeypatch.setattr(api_app, "get_audit_service", lambda: fake_service)

    transport = ASGITransport(app=api_app.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/ui/v1/security/permission-denied")

    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient permissions"
    assert fake_service.calls, "permission denied request should be recorded"
    recorded = fake_service.calls[0]
    assert recorded["event_type"] == "permission_denied"
    assert recorded["entity_type"] == "http_request"
    assert recorded["entity_id"] == "GET /api/ui/v1/security/permission-denied"
    assert recorded["payload"]["response"]["status_code"] == 403
    assert recorded["payload"]["principal"]["role"] == "anonymous"
