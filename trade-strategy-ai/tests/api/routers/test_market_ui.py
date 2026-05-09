"""Market UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui.market import get_market_service


@dataclass
class _FakeMarketService:
    """Market API 单测用的替身。"""

    async def list_symbols(self, **_: Any) -> Any:
        return _result({"count": 2, "items": ["000001.SZ", "600000.SH"]})

    async def get_ohlcv(self, **_: Any) -> Any:
        return _result(
            {
                "symbol": "000001.SZ",
                "start_date": "2026-04-01",
                "end_date": "2026-04-30",
                "count": 1,
                "items": [
                    {
                        "time": "2026-04-01",
                        "open": 1.0,
                        "high": 1.1,
                        "low": 0.9,
                        "close": 1.05,
                        "volume": 1000,
                    }
                ],
            }
        )


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(status=status, message=message, payload=payload)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建带认证覆盖的测试客户端。"""
    fake_service = _FakeMarketService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_market_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_symbols_and_ohlcv(client: AsyncClient) -> None:
    """Market UI API 应支持标的列表和 K 线查询。"""
    symbols = await client.get("/api/ui/v1/market/symbols")
    assert symbols.status_code == 200
    assert symbols.json()["items"] == ["000001.SZ", "600000.SH"]

    ohlcv = await client.get(
        "/api/ui/v1/market/ohlcv",
        params={"symbol": "000001.SZ", "start_date": "2026-04-01", "end_date": "2026-04-30"},
    )
    assert ohlcv.status_code == 200
    assert ohlcv.json()["items"][0]["close"] == 1.05

