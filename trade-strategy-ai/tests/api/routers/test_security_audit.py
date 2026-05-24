"""Security audit UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.security_audit import get_security_audit_query_service


@dataclass
class _FakeSecurityAuditQueryService:
    """Security audit API 测试用替身。"""

    list_calls: list[dict[str, Any]] = field(default_factory=list)
    detail_calls: list[str] = field(default_factory=list)

    async def list_permission_denied_logs(self, **kwargs: Any) -> Any:
        self.list_calls.append(kwargs)
        return _result(
            {
                "filters": kwargs,
                "summary": {
                    "total": 1,
                    "unique_actors": 1,
                    "unique_paths": 1,
                    "source_counts": {"ui": 1},
                },
                "page": {"total": 1, "skip": kwargs.get("skip", 0), "limit": kwargs.get("limit", 50), "count": 1},
                "items": [
                    {
                        "id": "audit-403",
                        "event_type": "permission_denied",
                        "actor": "anonymous",
                        "entity_type": "http_request",
                        "entity_id": "GET /api/ui/v1/jobs",
                        "dataset_version": None,
                        "source": "ui",
                        "request_context": {
                            "request": {"method": "GET", "path": "/api/ui/v1/jobs"},
                            "response": {"status_code": 403, "detail": "insufficient permissions"},
                            "principal": {
                                "role": "anonymous",
                                "api_key_label": None,
                                "authenticated": False,
                                "source": "anonymous",
                            },
                        },
                        "payload": {
                            "request": {"method": "GET", "path": "/api/ui/v1/jobs"},
                            "response": {"status_code": 403, "detail": "insufficient permissions"},
                        },
                        "event_at": "2026-05-17T00:00:00+00:00",
                        "created_at": "2026-05-17T00:00:00+00:00",
                        "updated_at": "2026-05-17T00:00:00+00:00",
                    }
                ],
            }
        )

    async def get_permission_denied_log(self, event_id: str) -> Any:
        self.detail_calls.append(event_id)
        if event_id == "missing":
            return _result({"event_id": event_id}, status="partial", message="permission denied log not found")
        return _result(
            {
                "item": {
                    "id": event_id,
                    "event_type": "permission_denied",
                    "actor": "anonymous",
                    "entity_type": "http_request",
                    "entity_id": "GET /api/ui/v1/jobs",
                    "dataset_version": None,
                    "source": "ui",
                    "request_context": {
                        "request": {"method": "GET", "path": "/api/ui/v1/jobs"},
                        "response": {"status_code": 403, "detail": "insufficient permissions"},
                        "principal": {
                            "role": "anonymous",
                            "api_key_label": None,
                            "authenticated": False,
                            "source": "anonymous",
                        },
                    },
                    "payload": {
                        "request": {"method": "GET", "path": "/api/ui/v1/jobs"},
                        "response": {"status_code": 403, "detail": "insufficient permissions"},
                    },
                    "event_at": "2026-05-17T00:00:00+00:00",
                    "created_at": "2026-05-17T00:00:00+00:00",
                    "updated_at": "2026-05-17T00:00:00+00:00",
                }
            }
        )


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(status=status, message=message, payload=payload)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建带认证覆盖的测试客户端。"""
    fake_service = _FakeSecurityAuditQueryService()
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
        app.dependency_overrides[get_security_audit_query_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.fake_service = fake_service  # type: ignore[attr-defined]
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_and_get_permission_denied_logs(client: AsyncClient) -> None:
    """权限拒绝日志 API 应支持列表和详情。"""
    listed = await client.get(
        "/api/ui/v1/security/permission-denied",
        params={
            "path": "/api/ui/v1/jobs",
            "source": "ui",
        },
    )
    assert listed.status_code == 200
    assert listed.json()["items"][0]["entity_id"] == "GET /api/ui/v1/jobs"
    assert client.fake_service.list_calls[0]["path"] == "/api/ui/v1/jobs"  # type: ignore[attr-defined]

    detail = await client.get("/api/ui/v1/security/permission-denied/audit-403")
    assert detail.status_code == 200
    assert detail.json()["item"]["id"] == "audit-403"


@pytest.mark.asyncio
async def test_viewer_cannot_access_permission_denied_logs(client: AsyncClient) -> None:
    """viewer 不能访问权限拒绝日志 UI API。"""
    previous = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="viewer",
        api_key_label="Viewer",
        authenticated=True,
        source="api_key",
        api_key="viewer-key",
    )
    try:
        response = await client.get("/api/ui/v1/security/permission-denied")
        assert response.status_code == 403
        assert response.json()["detail"] == "insufficient permissions"
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous
