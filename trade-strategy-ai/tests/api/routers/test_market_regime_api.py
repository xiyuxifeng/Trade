"""Market Regime API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui.market import get_market_regime_service, get_market_service, get_market_snapshot_query_service


@dataclass
class _FakeMarketRegimeService:
    """Market Regime API 单测替身。"""

    async def list_regimes(self, **_: Any) -> Any:
        return _result(
            {
                "filters": {"trade_date": "2026-05-16", "market": "CN", "regime_version": "market-regime-v1"},
                "page": {"total": 1, "limit": 50, "offset": 0, "count": 1},
                "items": [
                    {
                        "regime_id": "snap-001:market-regime-v1",
                        "snapshot_id": "snap-001",
                        "trade_date": "2026-05-16",
                        "market": "CN",
                        "regime_version": "market-regime-v1",
                        "source_feature_version": "market-regime-features-v1",
                        "primary_label": "strong_bull",
                        "labels": [
                            {
                                "label": "strong_bull",
                                "label_type": "primary",
                                "score": 5.6,
                                "confidence": 0.86,
                                "status": "active",
                                "evidence": [],
                                "reason": "combined_score=5.60",
                            }
                        ],
                        "features": [],
                        "confidence": 0.86,
                        "quality_status": "ok",
                        "missing_reason": None,
                        "storage_ref": {"snapshot_id": "snap-001", "regime_version": "market-regime-v1"},
                        "created_at": "2026-05-16T09:30:00+00:00",
                        "updated_at": "2026-05-16T09:30:00+00:00",
                    }
                ],
            }
        )

    async def get_regime_detail(self, snapshot_id: str, **_: Any) -> Any:
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
        return _result(
            {
                "regime": {
                    "regime_id": f"{snapshot_id}:market-regime-v1",
                    "snapshot_id": snapshot_id,
                    "trade_date": "2026-05-16",
                    "market": "CN",
                    "regime_version": "market-regime-v1",
                    "source_feature_version": "market-regime-features-v1",
                    "primary_label": "strong_bull",
                    "labels": [
                        {
                            "label": "strong_bull",
                            "label_type": "primary",
                            "score": 5.6,
                            "confidence": 0.86,
                            "status": "active",
                            "evidence": [],
                            "reason": "combined_score=5.60",
                        }
                    ],
                    "features": [
                        {
                            "feature_key": "trend",
                            "raw_value": {"ret_20d": 0.11},
                            "normalized_value": 0.8,
                            "source_section": "overview",
                            "source_field": "trend",
                            "source_version": "market-regime-features-v1",
                            "confidence": 0.9,
                            "weight": 0.3,
                            "missing_reason": None,
                        }
                    ],
                    "confidence": 0.86,
                    "quality_status": "ok",
                    "missing_reason": None,
                    "storage_ref": {"snapshot_id": snapshot_id, "regime_version": "market-regime-v1"},
                    "created_at": "2026-05-16T09:30:00+00:00",
                    "updated_at": "2026-05-16T09:30:00+00:00",
                },
                "features": [
                    {
                        "feature_key": "trend",
                        "raw_value": {"ret_20d": 0.11},
                        "normalized_value": 0.8,
                        "source_section": "overview",
                        "source_field": "trend",
                        "source_version": "market-regime-features-v1",
                        "confidence": 0.9,
                        "weight": 0.3,
                        "missing_reason": None,
                    }
                ],
                "warnings": [],
            }
        )


@pytest.fixture()
async def client() -> AsyncIterator[AsyncClient]:
    """创建测试客户端。"""
    app.dependency_overrides[verify_api_key] = lambda: "test-key"
    app.dependency_overrides[get_market_service] = lambda: None
    app.dependency_overrides[get_market_snapshot_query_service] = lambda: None
    app.dependency_overrides[get_market_regime_service] = lambda: _FakeMarketRegimeService()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _result(payload: dict[str, Any], status: str = "ok", message: str = "ok") -> Any:
    """构造和服务层一致的返回对象。"""
    from src.services.base import ServiceResult

    return ServiceResult(status=status, message=message, payload=payload)


@pytest.mark.asyncio()
async def test_list_market_regimes(client: AsyncClient) -> None:
    """列表路由应暴露 market regime。"""
    response = await client.get(
        "/api/ui/v1/market/regimes",
        params={"trade_date": "2026-05-16", "market": "CN", "regime_version": "market-regime-v1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["page"]["total"] == 1
    assert body["items"][0]["snapshot_id"] == "snap-001"


@pytest.mark.asyncio()
async def test_get_market_regime_detail(client: AsyncClient) -> None:
    """详情路由应返回单个 regime。"""
    response = await client.get("/api/ui/v1/market/snapshots/snap-001/regime", params={"regime_version": "market-regime-v1"})

    assert response.status_code == 200
    body = response.json()
    assert body["regime"]["snapshot_id"] == "snap-001"
    assert body["regime"]["primary_label"] == "strong_bull"
