"""回测结果 API 路由测试。

NTL-S7-005
"""
from httpx import AsyncClient, ASGITransport
import pytest

from api.main import app
from src.common.paths import project_root


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_backtest_results_returns_paginated_response(client: AsyncClient):
    response = await client.get("/backtest_results/", params={"skip": 0, "limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "items" in data


def test_backtest_result_dirs_are_project_root_relative() -> None:
    """回测结果目录应锚定到 trade-strategy-ai 项目根目录。"""
    from api.routers.backtest_results import _get_backtest_results_dirs

    dirs = _get_backtest_results_dirs()
    assert dirs == [
        project_root() / "data" / "backtest" / "results",
        project_root() / "data" / "processed" / "backtest",
    ]
