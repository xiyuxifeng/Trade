"""Snapshot UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui.snapshots import get_snapshot_service
from src.market_universe.schemas import (
    HotTopic,
    HotTopicsPayload,
    MarketUniverse,
    StrongSymbol,
    StrongSymbolsPayload,
    TopicConstituent,
    TopicConstituentsPayload,
)


@dataclass
class _FakeSnapshotService:
    """Snapshot API 单测用的替身。"""

    def list_snapshots(self, trade_date_start: str, trade_date_end: str) -> list[MarketUniverse]:
        self.last_range = (trade_date_start, trade_date_end)
        return [_build_snapshot("2026-05-09")]

    def load_snapshot(self, trade_date: str, slot: str) -> MarketUniverse | None:
        if trade_date == "2026-05-09" and slot == "17-30":
            return _build_snapshot(trade_date, slot=slot)
        return None


def _build_snapshot(trade_date: str, *, slot: str = "17-30") -> MarketUniverse:
    return MarketUniverse(
        trade_date=trade_date,
        slot=slot,
        fetched_at=datetime(2026, 5, 9, 9, 30, tzinfo=timezone.utc),
        hot_topics=HotTopicsPayload(
            trade_date=trade_date,
            slot=slot,
            topics=[HotTopic(kind="concept", topic_id="t-1", topic_name="AI", score=98.5, increase_pct=7.2)],
            sources=["akshare"],
            fetched_at=datetime(2026, 5, 9, 9, 31, tzinfo=timezone.utc),
        ),
        topic_constituents=TopicConstituentsPayload(
            trade_date=trade_date,
            slot=slot,
            constituents=[
                TopicConstituent(
                    kind="stock_sector_v2",
                    topic_id="t-1",
                    topic_name="AI",
                    symbol="000001.SZ",
                    name="平安银行",
                )
            ],
            sources=["akshare"],
            fetched_at=datetime(2026, 5, 9, 9, 32, tzinfo=timezone.utc),
        ),
        strong_symbols=StrongSymbolsPayload(
            trade_date=trade_date,
            slot=slot,
            symbols=[
                StrongSymbol(
                    kind="strong_fengkou",
                    symbol="000002.SZ",
                    name="万科A",
                    strength_score=87.0,
                )
            ],
            sources=["akshare"],
            fetched_at=datetime(2026, 5, 9, 9, 33, tzinfo=timezone.utc),
        ),
        metadata={"source": "snapshot"},
    )


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建带认证覆盖的测试客户端。"""
    fake_service = _FakeSnapshotService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_snapshot_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_and_get_snapshot_returns_market_universe_payload(client: AsyncClient) -> None:
    """UI 路由应支持快照列表和详情。"""
    response = await client.get(
        "/api/ui/v1/snapshots",
        params={"date_start": "2026-05-01", "date_end": "2026-05-09"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["type"] == "hot_topics"

    detail = await client.get("/api/ui/v1/snapshots/2026-05-09_17-30")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["item"]["hot_topics"]["topics"][0]["topic_name"] == "AI"
