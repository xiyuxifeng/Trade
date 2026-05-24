"""UI API 鉴权基线回归测试。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.routers.ui.imports import get_setup_service
from api.routers.ui.signals import get_signal_service
from src.services.base import ServiceResult


@dataclass
class _FakeSignalService:
    """用于鉴权回归测试的信号服务。"""

    calls: list[dict[str, Any]]

    def __init__(self) -> None:
        self.calls = []

    def list_signals(
        self,
        *,
        config_path: str,
        symbol: str | None = None,
        since: str | None = None,
        limit: int = 100,
    ) -> ServiceResult:
        self.calls.append(
            {
                "config_path": config_path,
                "symbol": symbol,
                "since": since,
                "limit": limit,
            }
        )
        return ServiceResult(
            status="ok",
            message="signals listed",
            payload={
                "config_path": config_path,
                "base_dir": "/tmp/project",
                "count": 1,
                "signals": [
                    {
                        "signal_id": "signal-1",
                        "symbol": "000001.SZ",
                        "side": "buy",
                        "confidence": 0.93,
                        "timestamp": "2026-05-09T09:25:00Z",
                        "trader_id": "trader_a",
                        "strategy_version_id": "version-1",
                        "context": {"trend": "up", "score": 0.93},
                    }
                ],
            },
        )


@dataclass
class _FakeSetupService:
    """用于鉴权回归测试的导入服务。"""

    migrate_calls: list[dict[str, Any]]

    def __init__(self) -> None:
        self.migrate_calls = []

    async def migrate_crawl_state(self, *, config_path: str) -> ServiceResult:
        self.migrate_calls.append({"config_path": config_path})
        return ServiceResult(
            status="ok",
            message="crawl state migrated",
            payload={
                "config_path": config_path,
                "base_dir": "/tmp/project",
                "migrated": 2,
                "skipped": 0,
                "results": [{"source": "tgb", "author_id": "10461311", "status": "migrated"}],
            },
        )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建带有 fake service 的测试客户端。"""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_signal_service] = lambda: _FakeSignalService()
    app.dependency_overrides[get_setup_service] = lambda: _FakeSetupService()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ui_route_rejects_missing_key(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """鉴权开启但未提供 key 时应拒绝 UI 请求。"""
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": True, "api_keys": []}},
    )

    response = await client.get("/api/ui/v1/signals?limit=1")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ui_route_allows_when_auth_disabled(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """关闭鉴权时应允许匿名访问 UI 请求。"""
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": False, "api_keys": []}},
    )

    response = await client.get("/api/ui/v1/signals?limit=1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1


@pytest.mark.asyncio
async def test_ui_write_route_allows_valid_key(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """鉴权开启且 key 命中时应允许写入类 UI 请求。"""
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": True, "api_keys": ["demo-key"]}},
    )

    response = await client.post(
        "/api/ui/v1/imports/crawl-state/migrate",
        headers={"X-API-Key": "demo-key"},
        json={},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["migrated"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/api/ui/v1/system/status", "get"),
        ("/api/ui/v1/workflows", "get"),
        ("/api/ui/v1/jobs/definitions", "get"),
        ("/api/ui/v1/profiles", "get"),
        ("/api/ui/v1/artifacts", "get"),
        ("/api/ui/v1/market/symbols", "get"),
        ("/api/ui/v1/market/snapshots", "get"),
        ("/api/ui/v1/market/snapshots/snap-001", "get"),
        ("/api/ui/v1/market/snapshots/snap-001/sections", "get"),
        ("/api/ui/v1/market/snapshots/snap-001/sections/overview", "get"),
        ("/api/ui/v1/market/datasets", "get"),
        ("/api/ui/v1/market/datasets/snap-001:dataset", "get"),
        ("/api/ui/v1/market/snapshots/snap-001/quality", "get"),
        ("/api/ui/v1/data-audits", "get"),
        ("/api/ui/v1/ops/recover-stale", "post"),
    ],
)
async def test_ui_routes_reject_missing_api_key_for_core_endpoints(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    method: str,
) -> None:
    """核心 UI API 在鉴权开启且未提供 key 时应统一拒绝访问。"""
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": True, "api_keys": []}},
    )

    response = await getattr(client, method)(path)
    assert response.status_code == 403
