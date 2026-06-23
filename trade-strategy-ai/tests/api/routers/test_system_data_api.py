"""System data scheduling API tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(status=status, message=message, payload=payload)


@dataclass
class _FakeSystemDataService:
    submit_calls: list[dict[str, Any]]
    cancel_calls: list[dict[str, Any]]
    retry_calls: list[dict[str, Any]]
    resume_calls: list[dict[str, Any]]

    async def get_readiness(self, **_: Any) -> Any:
        return _result(
            {
                "status": "partial",
                "summary": "盘前数据尚未完整到位，当前只能判定为部分就绪。",
                "phase": "pre_market",
                "target_trade_date": "2026-06-17",
                "latest_update_at": "2026-06-17T09:12:00+00:00",
                "repair_available": True,
                "repair_plan": {
                    "status": "needs_repair",
                    "steps": [
                        {
                            "action": "refresh_pre_market_kaipan",
                            "label": "补齐盘前市场数据",
                            "reason": "今天盘前可用数据仍未准备完成。",
                            "target_trade_date": "2026-06-17",
                        }
                    ],
                },
            }
        )

    async def build_schedule_summary(self) -> Any:
        return _result(
            {
                "timezone": "Asia/Shanghai",
                "entries": [
                    {
                        "key": "pre_market_kaipan",
                        "label": "盘前数据更新",
                        "window_start": "09:20",
                        "window_end": "09:25",
                        "dependency_order": ["refresh_pre_market_kaipan", "recompute_market_state"],
                    }
                ],
            }
        )

    async def list_operations(self, **_: Any) -> Any:
        return _result(
            {
                "count": 1,
                "items": [
                    {
                        "operation_id": "op-1",
                        "label": "补齐盘前市场数据",
                        "action": "repair",
                        "status": "failed",
                    }
                ],
            }
        )

    async def submit_operation(self, **kwargs: Any) -> Any:
        self.submit_calls.append(kwargs)
        return _result(
            {
                "created": True,
                "operation": {
                    "operation_id": "op-1",
                    "label": "补齐盘前市场数据",
                    "action": kwargs["action"],
                    "status": "pending",
                },
            }
        )

    async def cancel_operation(self, **kwargs: Any) -> Any:
        self.cancel_calls.append(kwargs)
        return _result({"operation_id": kwargs["operation_id"], "status": "cancelled"})

    async def retry_operation(self, **kwargs: Any) -> Any:
        self.retry_calls.append(kwargs)
        return _result({"operation_id": kwargs["operation_id"], "status": "pending"})

    async def resume_operation(self, **kwargs: Any) -> Any:
        self.resume_calls.append(kwargs)
        return _result({"operation_id": kwargs["operation_id"], "status": "running"})


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from api.routers.ui.system_data import get_data_scheduling_service

    fake_service = _FakeSystemDataService([], [], [], [])

    async def _principal() -> CurrentPrincipal:
        return CurrentPrincipal(
            role="operator",
            api_key_label="System Operator",
            authenticated=True,
            source="api_key",
            api_key="operator",
        )

    app.dependency_overrides[verify_api_key] = lambda: "test-key"
    app.dependency_overrides[get_current_principal] = _principal
    app.dependency_overrides[get_data_scheduling_service] = lambda: fake_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        async_client._fake_system_data_service = fake_service  # type: ignore[attr-defined]
        yield async_client
    app.dependency_overrides.clear()


async def test_system_data_readiness_and_schedule_endpoints(client: AsyncClient) -> None:
    readiness = await client.get("/api/ui/v1/system/data/readiness")
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "partial"
    assert readiness.json()["repair_plan"]["steps"][0]["action"] == "refresh_pre_market_kaipan"

    schedule = await client.get("/api/ui/v1/system/data/schedule")
    assert schedule.status_code == 200
    assert schedule.json()["timezone"] == "Asia/Shanghai"


async def test_system_data_operation_mutations_require_operator_role() -> None:
    from api.routers.ui.system_data import get_data_scheduling_service

    fake_service = _FakeSystemDataService([], [], [], [])

    async def _viewer() -> CurrentPrincipal:
        return CurrentPrincipal(
            role="viewer",
            api_key_label="Viewer",
            authenticated=True,
            source="api_key",
            api_key="viewer",
        )

    app.dependency_overrides[verify_api_key] = lambda: "viewer-key"
    app.dependency_overrides[get_current_principal] = _viewer
    app.dependency_overrides[get_data_scheduling_service] = lambda: fake_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as viewer_client:
        response = await viewer_client.post("/api/ui/v1/system/data/operations", json={"action": "repair"})
        assert response.status_code == 403
    app.dependency_overrides.clear()


async def test_system_data_operation_mutations_call_formal_facade(client: AsyncClient) -> None:
    fake_service = client._fake_system_data_service  # type: ignore[attr-defined]

    created = await client.post(
        "/api/ui/v1/system/data/operations",
        json={"action": "repair", "target_trade_date": "2026-06-17"},
    )
    assert created.status_code == 200
    assert created.json()["operation"]["status"] == "pending"
    assert fake_service.submit_calls[0]["action"] == "repair"

    cancelled = await client.post("/api/ui/v1/system/data/operations/op-1/cancel", json={"reason": "stop"})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    retried = await client.post("/api/ui/v1/system/data/operations/op-1/retry", json={"reason": "retry"})
    assert retried.status_code == 200
    assert retried.json()["status"] == "pending"

    resumed = await client.post("/api/ui/v1/system/data/operations/op-1/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "running"


async def test_system_data_backfill_returns_approval_required_payload(client: AsyncClient) -> None:
    fake_service = client._fake_system_data_service  # type: ignore[attr-defined]

    async def _submit_operation(**kwargs: Any) -> Any:
        fake_service.submit_calls.append(kwargs)
        return _result(
            {
                "created": False,
                "requires_admin_approval": True,
                "operation": {
                    "operation_id": "approval-required",
                    "label": "回灌历史数据",
                    "action": "backfill",
                    "status": "pending_approval",
                    "action_level": "admin_approval_required",
                },
            },
            status="partial",
            message="admin approval required for backfill",
        )

    fake_service.submit_operation = _submit_operation  # type: ignore[method-assign]
    response = await client.post(
        "/api/ui/v1/system/data/operations",
        json={"action": "backfill", "start_date": "2026-06-01", "end_date": "2026-06-03"},
    )

    assert response.status_code == 200
    assert response.json()["created"] is False
    assert response.json()["requires_admin_approval"] is True
    assert response.json()["operation"]["action_level"] == "admin_approval_required"
