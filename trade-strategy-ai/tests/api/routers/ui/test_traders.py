from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.app import app
from api.dependencies import verify_api_key
from api.routers.ui.traders import get_trader_option_service
from src.services.base import ServiceResult


@dataclass
class _FakeTraderOptionService:
    """用于 trader options 路由测试的替身服务。"""

    calls: list[str]

    def __init__(self) -> None:
        self.calls = []

    async def list_trader_options(self, *, source: str = 'all') -> ServiceResult:
        self.calls.append(source)
        payloads = {
            'strategy': {'count': 2, 'items': ['trader_a', 'trader_b']},
            'backtest': {'count': 1, 'items': ['trader_c']},
            'all': {'count': 3, 'items': ['trader_a', 'trader_b', 'trader_c']},
        }
        return ServiceResult(status='ok', message='ok', payload=payloads[source])


@pytest.fixture()
async def client() -> AsyncIterator[AsyncClient]:
    app.dependency_overrides.clear()
    app.dependency_overrides[verify_api_key] = lambda: 'demo-key'
    fake_service = _FakeTraderOptionService()
    app.dependency_overrides[get_trader_option_service] = lambda: fake_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_trader_options_returns_expected_items(client: AsyncClient) -> None:
    response = await client.get('/api/ui/v1/traders?source=strategy')

    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'success'
    assert payload['count'] == 2
    assert payload['items'] == ['trader_a', 'trader_b']
