"""Persona UI BFF 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui.persona import get_persona_service
from src.services.base import ServiceResult


@dataclass
class _FakePersonaService:
    sample_calls: list[dict[str, Any]] = field(default_factory=list)
    market_calls: list[dict[str, Any]] = field(default_factory=list)

    def build_sample_clusters(self, *, config_path: str) -> ServiceResult:
        self.sample_calls.append({"config_path": config_path})
        return ServiceResult(
            status="ok",
            message="sample clusters written",
            payload={
                "config_path": config_path,
                "base_dir": "/tmp/project",
                "clusters_path": "/tmp/project/data/processed/persona/clusters.sample.json",
                "trader_count": 3,
                "clusters_count": 6,
            },
        )

    def build_market_state(
        self,
        *,
        config_path: str,
        benchmark_symbol: str,
        as_of: str | None = None,
        from_akshare: bool = False,
        cache_csv: bool = True,
    ) -> ServiceResult:
        self.market_calls.append(
            {
                "config_path": config_path,
                "benchmark_symbol": benchmark_symbol,
                "as_of": as_of,
                "from_akshare": from_akshare,
                "cache_csv": cache_csv,
            }
        )
        return ServiceResult(
            status="ok",
            message="market state written",
            payload={
                "config_path": config_path,
                "base_dir": "/tmp/project",
                "market_state_path": "/tmp/project/data/processed/persona/market_state.json",
                "source": "akshare",
                "market_state": {"state": "bull"},
            },
        )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    fake_service = _FakePersonaService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_persona_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_build_sample_clusters_returns_path(client: AsyncClient) -> None:
    """样例聚类应返回生成文件路径。"""
    response = await client.post("/api/ui/v1/persona/sample", json={})
    assert response.status_code == 200
    payload = response.json()
    assert payload["clusters_path"].endswith(".json")


@pytest.mark.asyncio
async def test_build_market_state_returns_snapshot(client: AsyncClient) -> None:
    """MarketState 构建应返回快照路径别名。"""
    response = await client.post(
        "/api/ui/v1/persona/market-state/build",
        json={"benchmark_symbol": "000300.SH", "as_of": "2026-05-09", "from_akshare": False, "cache_csv": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "snapshot_path" in payload
    assert payload["snapshot_path"].endswith("market_state.json")
