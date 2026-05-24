"""Ranking API 路由测试。

NTL-S7-005
"""
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport
import pytest
import pytest_asyncio

from api.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_db_session():
    """模拟数据库 session，返回空结果。"""
    mock = MagicMock()

    def execute_side_effect(stmt):
        result = MagicMock()
        result.scalar.return_value = 0
        result.scalars.return_value.all.return_value = []
        return result

    mock.execute = AsyncMock(side_effect=execute_side_effect)
    return mock


@pytest.fixture
def mock_session_scope(mock_db_session):
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


@pytest.mark.asyncio
async def test_list_rankings_returns_paginated_response(client: AsyncClient, mock_session_scope):
    """列表端点返回分页结构（空结果）。"""
    with patch("src.db.session.session_scope", return_value=mock_session_scope):
        response = await client.get("/rankings/", params={"skip": 0, "limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "items" in data
    assert data["total"] == 0
    assert data["count"] == 0
