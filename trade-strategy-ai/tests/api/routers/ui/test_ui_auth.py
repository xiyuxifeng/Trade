"""UI auth 路由测试。"""

from __future__ import annotations

from typing import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建测试客户端。"""
    app.dependency_overrides.clear()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_me_returns_role_for_structured_key(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """结构化 API Key 应返回对应角色信息。"""
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {
            "auth": {
                "enabled": True,
                "api_keys": [
                    {"key": "viewer-key", "role": "viewer", "label": "Viewer"},
                ],
            }
        },
    )

    response = await client.get("/api/ui/v1/auth/me", headers={"X-API-Key": "viewer-key"})
    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "role": "viewer",
        "api_key_label": "Viewer",
        "authenticated": True,
        "source": "api_key",
    }


@pytest.mark.asyncio
async def test_auth_me_returns_anonymous_when_auth_disabled(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """关闭鉴权时 /auth/me 应返回匿名身份。"""
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": False, "api_keys": []}},
    )

    response = await client.get("/api/ui/v1/auth/me")
    assert response.status_code == 200
    assert response.json() == {
        "role": "anonymous",
        "api_key_label": None,
        "authenticated": False,
        "source": "anonymous",
    }
