"""Data audit UI 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.data_audits import get_data_audit_query_service


@dataclass
class _FakeDataAuditQueryService:
    calls: list[dict[str, Any]]

    def __init__(self) -> None:
        self.calls = []

    async def list_data_audits(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return type(
            "Result",
            (),
            {
                "status": "ok",
                "message": "data audits listed",
                "payload": {
                    "filters": kwargs,
                    "summary": {"total": 1, "event_type_counts": {"backup_project_state": 1}, "entity_type_counts": {"backup": 1}, "source_counts": {"ui": 1}},
                    "page": {"total": 1, "skip": kwargs.get("skip", 0), "limit": kwargs.get("limit", 50), "count": 1},
                    "items": [
                        {
                            "id": "audit-1",
                            "event_type": "backup_project_state",
                            "actor": "ui.ops",
                            "entity_type": "backup",
                            "entity_id": "backup-1",
                            "dataset_version": "backup-1",
                            "source": "ui",
                            "payload": {"tables": ["jobs"]},
                            "event_at": "2026-05-17T08:00:00Z",
                            "created_at": "2026-05-17T08:00:00Z",
                            "updated_at": "2026-05-17T08:00:00Z",
                        }
                    ],
                },
            },
        )()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    fake_service = _FakeDataAuditQueryService()
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
        app.dependency_overrides[get_data_audit_query_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_data_audits_api_lists_backup_history(client: AsyncClient) -> None:
    response = await client.get("/api/ui/v1/data-audits?entity_type=backup&limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 1
    assert payload["items"][0]["event_type"] == "backup_project_state"
