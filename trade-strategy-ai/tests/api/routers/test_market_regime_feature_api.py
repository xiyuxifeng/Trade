"""Market regime feature API 测试。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui.market import get_market_regime_feature_service, get_market_service, get_market_snapshot_query_service


@dataclass
class _FakeMarketRegimeFeatureService:
    """Market regime feature API 单测替身。"""

    async def list_features(self, **_: Any) -> Any:
        return _result(
            {
                "filters": {"trade_date": "2026-05-16", "market": "CN"},
                "page": {"total": 1, "limit": 50, "offset": 0, "count": 1},
                "items": [
                    {
                        "id": "feature-1",
                        "snapshot_id": "snap-001",
                        "trade_date": "2026-05-16",
                        "market": "CN",
                        "feature_version": "market-regime-features-v1",
                        "quality_status": "ok",
                        "available_feature_count": 9,
                        "partial_feature_count": 0,
                        "missing_feature_count": 0,
                        "created_at": "2026-05-16T09:30:00+00:00",
                    }
                ],
            }
        )

    async def get_feature_detail(self, snapshot_id: str, **_: Any) -> Any:
        if snapshot_id == "snap-missing":
            return _result(
                {
                    "error": {
                        "type": "snapshot_not_found",
                        "message": "snapshot not found",
                        "detail": snapshot_id,
                        "metadata": {"snapshot_id": snapshot_id},
                    }
                },
                status="error",
                message="snapshot not found",
            )
        if snapshot_id == "snap-partial":
            return _result(
                {
                    "feature": {
                        "id": "feature-1",
                        "snapshot_id": snapshot_id,
                        "trade_date": "2026-05-16",
                        "market": "CN",
                        "feature_version": "market-regime-features-v1",
                        "quality_status": "partial",
                        "available_feature_count": 5,
                        "partial_feature_count": 2,
                        "missing_feature_count": 2,
                        "created_at": "2026-05-16T09:30:00+00:00",
                    },
                    "feature_payload_json": {
                        "trend": {"feature_key": "trend", "value": "trend_up", "source_section": "market_state", "confidence": 0.9, "missing_reason": None}
                    },
                    "summary_json": {"source_sections": ["market_state"], "warnings": ["missing theme_strength"]},
                    "warnings": ["missing theme_strength"],
                },
                status="partial",
                message="market regime feature partial",
            )
        return _result(
            {
                "feature": {
                    "id": "feature-1",
                    "snapshot_id": snapshot_id,
                    "trade_date": "2026-05-16",
                    "market": "CN",
                    "feature_version": "market-regime-features-v1",
                    "quality_status": "ok",
                    "available_feature_count": 9,
                    "partial_feature_count": 0,
                    "missing_feature_count": 0,
                    "created_at": "2026-05-16T09:30:00+00:00",
                },
                "feature_payload_json": {
                    "trend": {"feature_key": "trend", "value": "trend_up", "source_section": "market_state", "confidence": 0.9, "missing_reason": None}
                },
                "summary_json": {"source_sections": ["market_state"]},
                "warnings": [],
            }
        )


@pytest.fixture()
async def client() -> AsyncIterator[AsyncClient]:
    """创建测试客户端。"""
    app.dependency_overrides[verify_api_key] = lambda: "test-key"
    app.dependency_overrides[get_market_service] = lambda: None
    app.dependency_overrides[get_market_snapshot_query_service] = lambda: None
    app.dependency_overrides[get_market_regime_feature_service] = lambda: _FakeMarketRegimeFeatureService()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _result(payload: dict[str, Any], status: str = "ok", message: str = "ok") -> Any:
    """构造和服务层一致的返回对象。"""
    from src.services.base import ServiceResult

    return ServiceResult(status=status, message=message, payload=payload)


@pytest.mark.asyncio()
async def test_list_market_regime_features(client: AsyncClient) -> None:
    """列表路由应暴露 market regime features。"""
    response = await client.get("/api/ui/v1/market/regime-features", params={"trade_date": "2026-05-16", "market": "CN"})

    assert response.status_code == 200
    body = response.json()
    assert body["page"]["total"] == 1
    assert body["items"][0]["snapshot_id"] == "snap-001"


@pytest.mark.asyncio()
async def test_get_market_regime_feature_detail(client: AsyncClient) -> None:
    """详情路由应返回单个 feature。"""
    response = await client.get("/api/ui/v1/market/snapshots/snap-001/regime-features")

    assert response.status_code == 200
    body = response.json()
    assert body["feature"]["snapshot_id"] == "snap-001"
    assert body["feature_payload_json"]["trend"]["value"] == "trend_up"


@pytest.mark.asyncio()
async def test_get_market_regime_feature_detail_maps_missing_snapshot(client: AsyncClient) -> None:
    """不存在的 snapshot 应返回 404。"""
    response = await client.get("/api/ui/v1/market/snapshots/snap-missing/regime-features")

    assert response.status_code == 404
    body = response.json()
    assert body["detail"]["type"] == "snapshot_not_found"


@pytest.mark.asyncio()
async def test_get_market_regime_feature_detail_returns_partial_payload(client: AsyncClient) -> None:
    """部分 feature 应以 206 返回 payload。"""
    response = await client.get("/api/ui/v1/market/snapshots/snap-partial/regime-features")

    assert response.status_code == 206
    body = response.json()
    assert body["feature"]["quality_status"] == "partial"
    assert body["warnings"] == ["missing theme_strength"]
