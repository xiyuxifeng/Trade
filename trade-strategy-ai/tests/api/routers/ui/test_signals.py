"""Signals UI BFF 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui.signals import get_signal_service
from src.services.base import ServiceResult


@dataclass
class _FakeSignalService:
    calls: list[dict[str, Any]] = field(default_factory=list)

    def list_signals(
        self,
        *,
        profile_id: str | None = None,
        config_path: str | None = None,
        symbol: str | None = None,
        since: str | None = None,
        limit: int = 100,
    ) -> ServiceResult:
        self.calls.append(
            {
                "profile_id": profile_id,
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
                "profile_id": profile_id,
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


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    fake_service = _FakeSignalService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_signal_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_signals_returns_summary(client: AsyncClient) -> None:
    """信号列表应返回上下文摘要。"""
    response = await client.get("/api/ui/v1/signals?limit=2")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] <= 2
    assert "signals" in payload
    assert "context_summary" in payload["signals"][0]
