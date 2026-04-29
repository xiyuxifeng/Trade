"""策略版本 API 路由测试。

NTL-S7-005
"""
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport
import pytest

from api.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_db_session():
    """模拟数据库 session，返回空结果。"""
    mock = MagicMock()

    def execute_side_effect(stmt):
        # 返回一个 mock result，可以调用 scalar() 或 scalars().all()
        result = MagicMock()
        # count 查询：scalar() 返回 0
        result.scalar.return_value = 0
        # 分页查询：scalars().all() 返回空列表
        result.scalars.return_value.all.return_value = []
        return result

    mock.execute = AsyncMock(side_effect=execute_side_effect)
    return mock


@pytest.fixture
def mock_session_scope(mock_db_session):
    """模拟 session_scope context manager。"""
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


@pytest.mark.asyncio
async def test_list_strategy_versions_returns_paginated_response(client: AsyncClient, mock_session_scope):
    """列表端点返回分页结构（空结果）。"""
    with patch("src.db.session.session_scope", return_value=mock_session_scope):
        response = await client.get("/strategy_versions/", params={"skip": 0, "limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "items" in data
    assert "total" in data
    assert data["total"] == 0
    assert data["count"] == 0
    assert data["skip"] == 0
    assert data["limit"] == 10