"""Market UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui import market as market_ui
from api.routers.ui.market import get_market_service, get_market_snapshot_query_service


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

    async def ohlcv_scheduler_status(self, **_: Any) -> Any:
        return _result(
            {
                "config_path": "config/app.yaml",
                "base_dir": "/tmp/trade-strategy-ai",
                "latest_trade_date": "2026-05-16",
                "latest_record_count": 12,
                "scheduler_started": False,
                "scheduler_pre_market": "9:25",
                "scheduler_post_close": "17:30",
            }
        )

    def run_ohlcv_scheduler(self, **_: Any) -> Any:
        return _result(
            {
                "config_path": "config/app.yaml",
                "base_dir": "/tmp/trade-strategy-ai",
                "pre_market": "9:25",
                "post_close": "17:30",
                "started": True,
                "scheduler_started": True,
            }
        )

    def stop_ohlcv_scheduler(self, **_: Any) -> Any:
        return _result(
            {
                "config_path": "config/app.yaml",
                "base_dir": "/tmp/trade-strategy-ai",
                "started": False,
                "pre_market": "9:25",
                "post_close": "17:30",
            }
        )


@dataclass
class _FakeMarketSnapshotQueryService:
    """Market snapshot query API 单测用的替身。"""

    async def list_snapshots(self, **_: Any) -> Any:
        return _result(
            {
                "filters": {"trade_date": "2026-05-16", "market": "CN"},
                "page": {"total": 1, "limit": 50, "offset": 0, "count": 1},
                "items": [
                    {
                        "snapshot_id": "snap-001",
                        "trade_date": "2026-05-16",
                        "market": "CN",
                        "data_version": "v1",
                        "quality_status": "ok",
                        "created_at": "2026-05-16T09:30:00+00:00",
                        "section_count": 2,
                        "available_section_count": 2,
                        "partial_section_count": 0,
                        "missing_section_count": 0,
                        "profile_id": "default",
                    }
                ],
            }
        )

    async def get_snapshot_detail(self, snapshot_id: str) -> Any:
        if snapshot_id == "snap-missing":
            return _result({"error": {"type": "snapshot_not_found", "message": "snapshot not found", "detail": snapshot_id, "metadata": {"snapshot_id": snapshot_id}}}, status="partial", message="snapshot not found")
        if snapshot_id == "snap-partial":
            return _result(
                {
                    "error": {
                        "type": "partial_data",
                        "message": "market snapshot detail is partial",
                        "detail": "quality report missing",
                        "metadata": {"snapshot_id": snapshot_id, "warnings": ["quality report missing"]},
                    }
                },
                status="partial",
                message="market snapshot detail is partial",
            )
        return _result(
            {
                "snapshot": {
                    "snapshot_id": snapshot_id,
                    "trade_date": "2026-05-16",
                    "market": "CN",
                    "data_version": "v1",
                    "quality_status": "ok",
                    "created_at": "2026-05-16T09:30:00+00:00",
                    "section_count": 2,
                    "available_section_count": 2,
                    "partial_section_count": 0,
                    "missing_section_count": 0,
                    "profile_id": "default",
                },
                "sections": [
                    {
                        "id": "1",
                        "snapshot_id": snapshot_id,
                        "section_id": "overview",
                        "provider": "kaipan",
                        "source_time": "2026-05-16T09:30:00+00:00",
                        "record_count": 1,
                        "missing_reason": None,
                        "quality_status": "ok",
                        "section_version": "v1",
                        "storage_ref": {"snapshot_id": snapshot_id, "section_id": "overview"},
                    }
                ],
                "item_count": 1,
                "quality_report": {"overall_status": "ok"},
                "dataset": {"dataset_id": f"{snapshot_id}:dataset", "snapshot_id": snapshot_id},
            }
        )

    async def list_snapshot_sections(self, snapshot_id: str, **_: Any) -> Any:
        return _result(
            {
                "snapshot_id": snapshot_id,
                "page": {"total": 1, "limit": 200, "offset": 0, "count": 1},
                "items": [
                    {
                        "id": "1",
                        "snapshot_id": snapshot_id,
                        "section_id": "overview",
                        "provider": "kaipan",
                        "source_time": "2026-05-16T09:30:00+00:00",
                        "record_count": 1,
                        "missing_reason": None,
                        "quality_status": "ok",
                        "section_version": "v1",
                        "storage_ref": {"snapshot_id": snapshot_id, "section_id": "overview"},
                    }
                ],
            }
        )

    async def get_snapshot_section(self, snapshot_id: str, section: str, **_: Any) -> Any:
        return _result(
            {
                "snapshot_id": snapshot_id,
                "section": {
                    "id": "1",
                    "snapshot_id": snapshot_id,
                    "section_id": section,
                    "provider": "kaipan",
                    "source_time": "2026-05-16T09:30:00+00:00",
                    "record_count": 1,
                    "missing_reason": None,
                    "quality_status": "ok",
                    "section_version": "v1",
                    "storage_ref": {"snapshot_id": snapshot_id, "section_id": section},
                },
                "page": {"total": 1, "limit": 100, "offset": 0, "count": 1},
                "items": [
                    {
                        "id": "item-1",
                        "snapshot_id": snapshot_id,
                        "section_id": section,
                        "dataset_id": f"{snapshot_id}:dataset",
                        "symbol": "000001.SZ",
                        "item_key": f"{section}:summary",
                        "item_type": section,
                        "source_time": "2026-05-16T09:30:00+00:00",
                        "quality_status": "ok",
                        "payload_json": {"symbol": "000001.SZ"},
                    }
                ],
                "filters": {"symbol": None, "topic": None},
            }
        )

    async def list_datasets(self, **_: Any) -> Any:
        return _result(
            {
                "filters": {"trade_date": "2026-05-16", "market": "CN"},
                "page": {"total": 1, "limit": 50, "offset": 0, "count": 1},
                "items": [
                    {
                        "id": "dataset-1",
                        "dataset_id": "snap-001:dataset",
                        "dataset_type": "market_snapshot",
                        "trade_date": "2026-05-16",
                        "market": "CN",
                        "source": "snapshot-build",
                        "storage_ref": {"snapshot_id": "snap-001", "dataset_id": "snap-001:dataset"},
                        "snapshot_id": "snap-001",
                        "profile_id": "default",
                        "quality_status": "ok",
                        "created_at": "2026-05-16T09:30:00+00:00",
                        "updated_at": "2026-05-16T09:30:00+00:00",
                    }
                ],
            }
        )

    async def get_dataset_detail(self, dataset_id: str, **_: Any) -> Any:
        return _result(
            {
                "dataset": {
                    "id": "dataset-1",
                    "dataset_id": dataset_id,
                    "dataset_type": "market_snapshot",
                    "trade_date": "2026-05-16",
                    "market": "CN",
                    "source": "snapshot-build",
                    "storage_ref": {"snapshot_id": "snap-001", "dataset_id": dataset_id},
                    "snapshot_id": "snap-001",
                    "profile_id": "default",
                    "quality_status": "ok",
                    "created_at": "2026-05-16T09:30:00+00:00",
                    "updated_at": "2026-05-16T09:30:00+00:00",
                },
                "snapshot": {
                    "snapshot_id": "snap-001",
                    "trade_date": "2026-05-16",
                    "market": "CN",
                    "data_version": "v1",
                    "quality_status": "ok",
                    "created_at": "2026-05-16T09:30:00+00:00",
                    "section_count": 2,
                    "available_section_count": 2,
                    "partial_section_count": 0,
                    "missing_section_count": 0,
                    "profile_id": "default",
                },
                "page": {"total": 1, "limit": 100, "offset": 0, "count": 1},
                "items": [
                    {
                        "id": "item-1",
                        "snapshot_id": "snap-001",
                        "section_id": "overview",
                        "dataset_id": dataset_id,
                        "symbol": "000001.SZ",
                        "item_key": "overview:summary",
                        "item_type": "overview",
                        "source_time": "2026-05-16T09:30:00+00:00",
                        "quality_status": "ok",
                        "payload_json": {"symbol": "000001.SZ"},
                    }
                ],
            }
        )

    async def get_quality_report(self, snapshot_id: str) -> Any:
        if snapshot_id == "snap-missing":
            return _result({"error": {"type": "snapshot_not_found", "message": "snapshot not found", "detail": snapshot_id, "metadata": {"snapshot_id": snapshot_id}}}, status="partial", message="snapshot not found")
        if snapshot_id == "snap-partial":
            return _result(
                {
                    "error": {
                        "type": "partial_data",
                        "message": "quality report not found",
                        "detail": snapshot_id,
                        "metadata": {"snapshot_id": snapshot_id},
                    }
                },
                status="partial",
                message="quality report not found",
            )
        return _result({"quality_report": {"snapshot_id": snapshot_id, "overall_status": "ok"}})


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(status=status, message=message, payload=payload)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建带认证覆盖的测试客户端。"""
    fake_service = _FakeMarketService()
    fake_query_service = _FakeMarketSnapshotQueryService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_market_service] = lambda: fake_service
        app.dependency_overrides[get_market_snapshot_query_service] = lambda: fake_query_service
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


@pytest.mark.asyncio
async def test_ohlcv_scheduler_endpoints(monkeypatch: pytest.MonkeyPatch, client: AsyncClient) -> None:
    """Market OHLCV scheduler API 应支持状态、启动和停止。"""
    async def _fake_resolve_profile_config_path(self, profile_id: str):
        del self
        assert profile_id == "default"
        return Path("config/ohlcv.yaml")

    monkeypatch.setattr(market_ui.ConfigProfileService, "resolve_profile_config_path", _fake_resolve_profile_config_path, raising=False)

    missing_profile = await client.get("/api/ui/v1/market/ohlcv/status")
    assert missing_profile.status_code == 422

    status = await client.get("/api/ui/v1/market/ohlcv/status", params={"profile_id": "default"})
    assert status.status_code == 200
    assert status.json()["latest_trade_date"] == "2026-05-16"

    started = await client.post("/api/ui/v1/market/ohlcv/run", params={"profile_id": "default"})
    assert started.status_code == 200
    assert started.json()["scheduler_started"] is True

    stopped = await client.post("/api/ui/v1/market/ohlcv/stop", params={"profile_id": "default"})
    assert stopped.status_code == 200
    assert stopped.json()["started"] is False


@pytest.mark.asyncio
async def test_list_benchmark_options_honors_limit(monkeypatch: pytest.MonkeyPatch, client: AsyncClient) -> None:
    """benchmark 选项接口应尊重 limit。"""
    monkeypatch.setattr(market_ui, "list_index_stock_infos", AsyncMock(return_value=[]))

    resp = await client.get("/api/ui/v1/market/benchmark-options", params={"limit": 1})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["count"] == 1
    assert len(payload["items"]) == 1


@pytest.mark.asyncio
async def test_market_snapshot_query_endpoints(client: AsyncClient) -> None:
    """Market snapshot query API 应支持列表、详情、section、dataset 和 quality。"""
    snapshots = await client.get("/api/ui/v1/market/snapshots", params={"trade_date": "2026-05-16", "market": "CN"})
    assert snapshots.status_code == 200
    assert snapshots.json()["items"][0]["snapshot_id"] == "snap-001"

    snapshot_detail = await client.get("/api/ui/v1/market/snapshots/snap-001")
    assert snapshot_detail.status_code == 200
    assert snapshot_detail.json()["snapshot"]["snapshot_id"] == "snap-001"

    sections = await client.get("/api/ui/v1/market/snapshots/snap-001/sections")
    assert sections.status_code == 200
    assert sections.json()["items"][0]["section_id"] == "overview"

    section = await client.get("/api/ui/v1/market/snapshots/snap-001/sections/overview")
    assert section.status_code == 200
    assert section.json()["items"][0]["symbol"] == "000001.SZ"

    datasets = await client.get("/api/ui/v1/market/datasets", params={"trade_date": "2026-05-16", "market": "CN"})
    assert datasets.status_code == 200
    assert datasets.json()["items"][0]["dataset_id"] == "snap-001:dataset"

    dataset = await client.get("/api/ui/v1/market/datasets/snap-001:dataset")
    assert dataset.status_code == 200
    assert dataset.json()["dataset"]["dataset_id"] == "snap-001:dataset"

    quality = await client.get("/api/ui/v1/market/snapshots/snap-001/quality")
    assert quality.status_code == 200
    assert quality.json()["quality_report"]["overall_status"] == "ok"


@pytest.mark.asyncio
async def test_market_snapshot_list_endpoint_returns_empty_page_for_no_match(client: AsyncClient) -> None:
    """Market snapshot 列表在无结果时应返回空页而不是 404。"""

    class _EmptySnapshotQueryService(_FakeMarketSnapshotQueryService):
        async def list_snapshots(self, **_: Any) -> Any:
            return _result(
                {
                    "filters": {"trade_date": "2026-05-18", "market": "CN"},
                    "page": {"total": 0, "limit": 50, "offset": 0, "count": 0},
                    "items": [],
                }
            )

    empty_service = _EmptySnapshotQueryService()
    app.dependency_overrides[get_market_snapshot_query_service] = lambda: empty_service
    try:
        response = await client.get("/api/ui/v1/market/snapshots", params={"trade_date": "2026-05-18", "market": "CN"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["page"]["total"] == 0
        assert payload["page"]["count"] == 0
        assert payload["items"] == []
    finally:
        app.dependency_overrides[get_market_snapshot_query_service] = lambda: _FakeMarketSnapshotQueryService()


@pytest.mark.asyncio
async def test_market_snapshot_query_endpoint_returns_structured_error(client: AsyncClient) -> None:
    """Market snapshot query API 应返回结构化错误。"""
    resp = await client.get("/api/ui/v1/market/snapshots/snap-001/quality")
    assert resp.status_code == 200

    missing = await client.get("/api/ui/v1/market/snapshots/snap-missing")
    assert missing.status_code == 404
    assert missing.json()["detail"]["type"] == "snapshot_not_found"

    partial = await client.get("/api/ui/v1/market/snapshots/snap-partial")
    assert partial.status_code == 206
    assert partial.json()["detail"]["type"] == "partial_data"
