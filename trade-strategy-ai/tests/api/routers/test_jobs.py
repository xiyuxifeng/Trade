"""Job UI API 路由测试。"""

from __future__ import annotations

from typing import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from src.api.dependencies import verify_api_key


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建带认证覆盖的测试客户端。"""
    app.dependency_overrides[verify_api_key] = lambda: "test-key"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_job_definitions_returns_registry(client: AsyncClient) -> None:
    """定义列表接口应返回 job 注册表内容。"""
    response = await client.get("/api/ui/v1/jobs/definitions")
    assert response.status_code == 200
    data = response.json()
    assert any(item["job_type"] == "pipeline-run" for item in data)


@pytest.mark.asyncio
async def test_get_job_definition_returns_single_item(client: AsyncClient) -> None:
    """单条定义接口应返回指定 job type 的元数据。"""
    response = await client.get("/api/ui/v1/jobs/definitions/run-pre-market")
    assert response.status_code == 200
    data = response.json()
    assert data["job_type"] == "run-pre-market"
    assert data["runnable"] is True


@pytest.mark.asyncio
async def test_validate_job_submission_enforces_whitelist(client: AsyncClient) -> None:
    """提交校验接口应拒绝未接入的 job type。"""
    response = await client.post(
        "/api/ui/v1/jobs/validate",
        json={"job_type": "seed-data", "params": {"config_path": "config/app.yaml"}},
    )
    assert response.status_code == 400
    assert "not runnable" in response.json()["detail"]

