"""Kaipan UI BFF 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui.kaipan import get_kaipan_service
from src.common.config import AppConfig
from src.services.base import ServiceResult
from src.services.config_profile_service import ConfigProfileService
from src.services.runtime_config import ProfileRuntimeConfig


@dataclass
class _FakeKaipanService:
    calls: list[dict[str, Any]] = field(default_factory=list)

    def fetch(
        self,
        *,
        profile_id: str | None = None,
        config_path: str | None = None,
        runtime: Any | None = None,
        trade_date: str | None = None,
        slot: str = "all",
    ) -> ServiceResult:
        self.calls.append(
            {
                "action": "fetch",
                "profile_id": profile_id,
                "config_path": config_path,
                "runtime": runtime,
                "trade_date": trade_date,
                "slot": slot,
            }
        )
        return ServiceResult(
            status="ok",
            message="kaipan fetch completed",
            payload={
                "profile_id": profile_id,
                "config_path": config_path,
                "base_dir": "/tmp/project",
                "trade_date": trade_date or "2026-05-09",
                "slots": [slot] if slot != "all" else ["09-25", "17-30"],
                "slot_results": {"all": {"success": ["board_strength"], "failed": []}},
                "normalize_results": {"all": []},
            },
        )

    def status(self, *, profile_id: str | None = None, config_path: str | None = None, runtime: Any | None = None) -> ServiceResult:
        self.calls.append({"action": "status", "profile_id": profile_id, "config_path": config_path, "runtime": runtime})
        return ServiceResult(
            status="ok",
            message="latest slot 2026-05-09_17-30",
            payload={
                "profile_id": profile_id,
                "config_path": config_path,
                "base_dir": "/tmp/project",
                "raw_base": "/tmp/project/data/processed/kaipan/raw",
                "latest_slot": "2026-05-09_17-30",
                "scheduler_started": False,
                "scheduler_pre_market": "9:25",
                "scheduler_post_close": "17:30",
            },
        )

    def normalize(
        self,
        *,
        profile_id: str | None = None,
        config_path: str | None = None,
        runtime: Any | None = None,
        trade_date: str | None = None,
        slot: str = "all",
    ) -> ServiceResult:
        self.calls.append(
            {
                "action": "normalize",
                "profile_id": profile_id,
                "config_path": config_path,
                "runtime": runtime,
                "trade_date": trade_date,
                "slot": slot,
            }
        )
        return ServiceResult(
            status="ok",
            message="kaipan normalize completed",
            payload={
                "profile_id": profile_id,
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
        profile_id: str | None = None,
        config_path: str | None = None,
        runtime: Any | None = None,
        start_scheduler: bool = False,
        block: bool = False,
    ) -> ServiceResult:
        self.calls.append(
            {
                "action": "run",
                "profile_id": profile_id,
                "config_path": config_path,
                "runtime": runtime,
                "start_scheduler": start_scheduler,
                "block": block,
            }
        )
        return ServiceResult(
            status="ok",
            message="kaipan scheduler plan prepared" if not start_scheduler else "kaipan scheduler started",
            payload={
                "profile_id": profile_id,
                "config_path": config_path,
                "base_dir": "/tmp/project",
                "pre_market": "9:25",
                "post_close": "17:30",
                "started": start_scheduler,
                "scheduler_started": start_scheduler,
            },
        )

    def stop(self, *, profile_id: str | None = None, config_path: str | None = None, runtime: Any | None = None) -> ServiceResult:
        self.calls.append({"action": "stop", "profile_id": profile_id, "config_path": config_path, "runtime": runtime})
        return ServiceResult(
            status="ok",
            message="kaipan scheduler stopped",
            payload={
                "profile_id": profile_id,
                "config_path": config_path,
                "base_dir": "/tmp/project",
                "started": False,
                "pre_market": "9:25",
                "post_close": "17:30",
            },
        )


@pytest_asyncio.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncClient]:
    fake_service = _FakeKaipanService()
    fake_runtime = ProfileRuntimeConfig(profile_id="default", config=AppConfig(), base_dir=Path("/tmp/project"))
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_kaipan_service] = lambda: fake_service
        monkeypatch.setattr(ConfigProfileService, "resolve_runtime_profile_id", lambda self, preferred=None: "default")

        async def _load_profile_runtime_config(self, profile_id: str):
            del self, profile_id
            return fake_runtime

        monkeypatch.setattr(ConfigProfileService, "load_profile_runtime_config", _load_profile_runtime_config)
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
    assert payload["profile_id"] == "default"


@pytest.mark.asyncio
async def test_kaipan_fetch_returns_payload(client: AsyncClient) -> None:
    """抓取接口应返回槽位结果。"""
    response = await client.post("/api/ui/v1/kaipan/fetch?slot=all")
    assert response.status_code == 200
    payload = response.json()
    assert "slot_results" in payload
    assert payload["profile_id"] == "default"


@pytest.mark.asyncio
async def test_kaipan_normalize_returns_results(client: AsyncClient) -> None:
    """标准化接口应返回结果列表。"""
    response = await client.post("/api/ui/v1/kaipan/normalize", json={"slot": "all"})
    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload
    assert payload["profile_id"] == "default"


@pytest.mark.asyncio
async def test_kaipan_run_returns_payload(client: AsyncClient) -> None:
    """run 接口应返回计划或启动状态。"""
    response = await client.post("/api/ui/v1/kaipan/run", json={"start_scheduler": True, "block": False})
    assert response.status_code == 200
    payload = response.json()
    assert "started" in payload or "pre_market" in payload
    assert payload["scheduler_started"] is True
    assert payload["profile_id"] == "default"


@pytest.mark.asyncio
async def test_kaipan_stop_returns_payload(client: AsyncClient) -> None:
    """stop 接口应返回停止状态。"""
    response = await client.post("/api/ui/v1/kaipan/stop")
    assert response.status_code == 200
    payload = response.json()
    assert payload["started"] is False
    assert payload["profile_id"] == "default"
