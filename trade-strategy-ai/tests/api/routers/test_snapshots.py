"""快照 API 路由测试。

NTL-S7-005
"""
from httpx import AsyncClient, ASGITransport
import pytest

from api.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_snapshots_returns_paginated_response(client: AsyncClient):
    """列表端点返回分页结构"""
    response = await client.get("/snapshots/", params={"skip": 0, "limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "items" in data