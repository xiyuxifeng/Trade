from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app


@dataclass
class _FakeReadiness:
    state: str = "partial"
    readiness_status: str = "degraded"
    trade_date: str = "2026-06-21"
    slot: str = "09-25"
    summary_title: str = "可降级继续"
    happened: str = "正式规则适用性覆盖不完整。"
    affected: str = "今日规则选择会缺少一部分正式适用性证据。"
    repair_guidance: str = "先补齐规则适用性画像，或在降级模式下继续。"
    can_proceed: bool = True
    can_proceed_in_degraded_mode: bool = True
    checks: list[dict[str, Any]] | None = None
    traceability: dict[str, Any] | None = None
    repair_actions: list[dict[str, Any]] | None = None
    warnings: list[str] | None = None

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        del mode
        return {
            "state": self.state,
            "readiness_status": self.readiness_status,
            "trade_date": self.trade_date,
            "slot": self.slot,
            "summary_title": self.summary_title,
            "happened": self.happened,
            "affected": self.affected,
            "repair_guidance": self.repair_guidance,
            "can_proceed": self.can_proceed,
            "can_proceed_in_degraded_mode": self.can_proceed_in_degraded_mode,
            "checks": self.checks
            or [
                {
                    "code": "rule_applicability",
                    "label": "规则适用性",
                    "status": "degraded",
                    "happened": "正式规则适用性覆盖不完整。",
                    "affected": "今日规则选择会缺少一部分正式适用性证据。",
                    "repair_guidance": "先补齐规则适用性画像，或在降级模式下继续。",
                    "can_proceed_in_degraded_mode": True,
                    "traceability": {
                        "applicability_profile_ids": [],
                        "missing_rule_version_ids": ["11111111-1111-1111-1111-111111111111"],
                    },
                }
            ],
            "traceability": self.traceability
            or {
                "trade_date": self.trade_date,
                "strategy_version_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "dataset_snapshot_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "market_snapshot_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "market_state_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                "rule_applicability_profile_ids": [],
                "author_validated_profile_version_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                "data_quality_state": "degraded",
            },
            "repair_actions": self.repair_actions or [{"label": "补齐缺失数据", "to": "/system/data"}],
            "warnings": self.warnings or [],
        }


class _FakePreMarketReadinessService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def get_readiness(self, trade_date: str, *, actor_id: str, actor_role: str):
        self.calls.append({"trade_date": trade_date, "actor_id": actor_id, "actor_role": actor_role})
        return _FakeReadiness()


@pytest_asyncio.fixture()
async def client() -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[verify_api_key] = lambda: "test-key"
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="viewer",
        api_key_label="tester",
        authenticated=True,
        source="api_key",
        api_key="test-key",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio()
async def test_daily_pre_market_readiness_route_returns_business_readiness_payload(client: AsyncClient) -> None:
    from api.routers.ui.daily_pre_market import get_pre_market_readiness_service

    service = _FakePreMarketReadinessService()
    app.dependency_overrides[get_pre_market_readiness_service] = lambda: service
    try:
        response = await client.get("/api/ui/v1/daily/pre-market/readiness", params={"trade_date": "2026-06-21"})
    finally:
        app.dependency_overrides.pop(get_pre_market_readiness_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["readiness_status"] == "degraded"
    assert payload["summary_title"] == "可降级继续"
    assert payload["trade_date"] == "2026-06-21"
    assert payload["slot"] == "09-25"
    assert payload["repair_actions"][0]["to"] == "/system/data"
    assert service.calls == [{"trade_date": "2026-06-21", "actor_id": "tester", "actor_role": "viewer"}]


@pytest.mark.asyncio()
async def test_daily_pre_market_readiness_route_maps_lookup_errors_to_truthful_404(client: AsyncClient) -> None:
    from api.routers.ui.daily_pre_market import get_pre_market_readiness_service

    class _MissingService:
        async def get_readiness(self, trade_date: str, *, actor_id: str, actor_role: str):
            del trade_date, actor_id, actor_role
            raise LookupError("trade date not found")

    app.dependency_overrides[get_pre_market_readiness_service] = lambda: _MissingService()
    try:
        response = await client.get("/api/ui/v1/daily/pre-market/readiness", params={"trade_date": "2026-06-21"})
    finally:
        app.dependency_overrides.pop(get_pre_market_readiness_service, None)

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["message"] == "未找到今日盘前检查结果"
    assert "当前页面不能显示该交易日的正式盘前检查" in detail["impact"]

