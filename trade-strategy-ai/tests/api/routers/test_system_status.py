"""系统状态 UI API 测试。"""

from __future__ import annotations

from typing import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.dependencies import verify_api_key


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建带认证覆盖的测试客户端。"""
    app.dependency_overrides[verify_api_key] = lambda: "test-key"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_system_status_route_exists(client: AsyncClient) -> None:
    """系统状态路由应可返回统一状态结构。"""
    response = await client.get("/api/ui/system/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "config_path" in payload
    assert "database" in payload
    assert "directories" in payload
