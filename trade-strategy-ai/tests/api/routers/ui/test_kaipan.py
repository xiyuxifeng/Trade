"""Kaipan UI BFF 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui.kaipan import get_kaipan_service
from src.services.base import ServiceResult


@dataclass
class _FakeKaipanService:
    calls: list[dict[str, Any]] = field(default_factory=list)

    def fetch(
        self,
        *,
        config_path: str,
        trade_date: str | None = None,
        slot: str = "all",
    ) -> ServiceResult:
        self.calls.append({"action": "fetch", "config_path": config_path, "trade_date": trade_date, "slot": slot})
        return ServiceResult(
            status="ok",
            message="kaipan fetch completed",
            payload={
                "config_path": config_path,
                "base_dir": "/tmp/project",
                "trade_date": trade_date or "2026-05-09",
                "slots": [slot] if slot != "all" else ["09-25", "17-30"],
                "slot_results": {"all": {"success": ["board_strength"], "failed": []}},
                "normalize_results": {"all": []},
            },
        )

    def status(self, *, config_path: str) -> ServiceResult:
        self.calls.append({"action": "status", "config_path": config_path})
        return ServiceResult(
            status="ok",
            message="latest slot 2026-05-09_17-30",
            payload={
                "config_path": config_path,
                "base_dir": "/tmp/project",
                "raw_base": "/tmp/project/data/processed/kaipan/raw",
                "latest_slot": "2026-05-09_17-30",
            },
        )

    def normalize(
        self,
        *,
        config_path: str,
        trade_date: str | None = None,
        slot: str = "all",
    ) -> ServiceResult:
        self.calls.append({"action": "normalize", "config_path": config_path, "trade_date": trade_date, "slot": slot})
        return ServiceResult(
            status="ok",
            message="kaipan normalize completed",
            payload={
                "config_path": config_path,
                "base_dir": "/tmp/project",
                "trade_date": trade_date or "2026-05-09",
                "slots": [slot] if slot != "all" else ["09-25", "17-30"],
                "results": [],
            },
        )

    def run(
        self,
        *,
        config_path: str,
        start_scheduler: bool = False,
        block: bool = False,
    ) -> ServiceResult:
        self.calls.append(
            {
                "action": "run",
                "config_path": config_path,
                "start_scheduler": start_scheduler,
                "block": block,
            }
        )
        return ServiceResult(
            status="ok",
            message="kaipan scheduler plan prepared" if not start_scheduler else "kaipan scheduler started",
            payload={
                "config_path": config_path,
                "base_dir": "/tmp/project",
                "pre_market": "9:25",
                "post_close": "17:30",
                "started": start_scheduler,
            },
        )


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    fake_service = _FakeKaipanService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_kaipan_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_kaipan_status_returns_latest_slot(client: AsyncClient) -> None:
    """状态接口应返回最近可用槽位。"""
    response = await client.get("/api/ui/v1/kaipan/status")
    assert response.status_code == 200
    payload = response.json()
    assert "latest_slot" in payload


@pytest.mark.asyncio
async def test_kaipan_fetch_returns_payload(client: AsyncClient) -> None:
    """抓取接口应返回槽位结果。"""
    response = await client.post("/api/ui/v1/kaipan/fetch?slot=all")
    assert response.status_code == 200
    payload = response.json()
    assert "slot_results" in payload


@pytest.mark.asyncio
async def test_kaipan_normalize_returns_results(client: AsyncClient) -> None:
    """标准化接口应返回结果列表。"""
    response = await client.post("/api/ui/v1/kaipan/normalize", json={"slot": "all"})
    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload


@pytest.mark.asyncio
async def test_kaipan_run_returns_payload(client: AsyncClient) -> None:
    """run 接口应返回计划或启动状态。"""
    response = await client.post("/api/ui/v1/kaipan/run", json={"start_scheduler": False})
    assert response.status_code == 200
    payload = response.json()
    assert "started" in payload or "pre_market" in payload
