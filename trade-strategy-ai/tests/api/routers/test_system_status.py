"""系统状态 UI API 测试。"""

from __future__ import annotations

from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.dependencies import verify_api_key


@pytest_asyncio.fixture
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
    response = await client.get("/api/ui/v1/system/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "config_path" in payload
    assert "profile_context" in payload
    assert "database" in payload
    assert "directories" in payload
    assert payload["profile_context"]["profile_id"] is None
    assert payload["profile_context"]["profile_snapshot_id"] is None
    assert payload["profile_context"]["source"] == "unset"


@pytest.mark.asyncio
async def test_system_status_includes_env_profile_context(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """系统状态应显式透出环境变量注入的 Profile 上下文。"""
    monkeypatch.setenv("PROFILE_ID", "profile-001")
    monkeypatch.setenv("PROFILE_SNAPSHOT_ID", "snapshot-001")

    response = await client.get("/api/ui/v1/system/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["profile_context"] == {
        "profile_id": "profile-001",
        "profile_snapshot_id": "snapshot-001",
        "source": "env",
    }


@pytest.mark.asyncio
async def test_legacy_system_status_route_still_works(client: AsyncClient) -> None:
    """旧系统状态路由应继续兼容。"""
    response = await client.get("/api/ui/system/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
