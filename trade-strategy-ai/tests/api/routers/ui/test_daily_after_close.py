from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app


@dataclass
class _FakeResult:
    payload: dict[str, Any]

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        del mode
        return self.payload


class _FakePostMarketReviewService:
    def __init__(self) -> None:
        self.actual_calls: list[dict[str, Any]] = []
        self.evaluate_calls: list[dict[str, Any]] = []

    async def get_actuals_for_signals(self, *, trading_day_plan_id: str, post_close_market_snapshot_id: str, actor_id: str, actor_role: str):
        self.actual_calls.append(
            {
                "trading_day_plan_id": trading_day_plan_id,
                "post_close_market_snapshot_id": post_close_market_snapshot_id,
                "actor_id": actor_id,
                "actor_role": actor_role,
            }
        )
        return _FakeResult(
            {
                "trading_day_plan_id": trading_day_plan_id,
                "trade_date": date(2026, 6, 21).isoformat(),
                "coverage_state": "partial",
                "signals": [
                    {
                        "signal_id": "signal-1",
                        "symbol": "000001.SZ",
                        "state": "ready",
                        "row_fingerprint": "row-1",
                        "reasons": [],
                    },
                    {
                        "signal_id": "signal-2",
                        "symbol": "600000.SH",
                        "state": "insufficient_coverage",
                        "row_fingerprint": None,
                        "reasons": ["post_close_actual_row_missing"],
                    },
                ],
                "missing_symbols": ["600000.SH"],
                "conflict_symbols": [],
            }
        )

    async def evaluate_signal_outcomes(self, request, *, actor_id: str, actor_role: str):
        self.evaluate_calls.append({"request": request.model_dump(mode="json"), "actor_id": actor_id, "actor_role": actor_role})
        return _FakeResult(
            {
                "state": "ready",
                "post_market_review_id": "review-1",
                "trading_day_plan_id": request.trading_day_plan_id,
                "trade_date": "2026-06-21",
                "post_close_market_snapshot_id": request.post_close_market_snapshot_id,
                "signal_results": [
                    {
                        "signal_id": "signal-1",
                        "symbol": "000001.SZ",
                        "triggered": {"state": "ready", "value": True},
                        "executed": {"state": "unavailable", "value": None},
                        "actual_result": {"state": "ready", "value": "up"},
                    }
                ],
                "evidence": {"attribution_state": "unavailable_RT-S10-002_not_started"},
                "happened": "已根据正式盘后行情快照评估盘前信号。",
                "affected": "页面会显示每个信号的实际结果、差异和不可用原因；不会把缺失值当作成功。",
                "repair_guidance": "可进入结构化归因任务，但本次未生成归因或优化建议。",
            }
        )


@pytest_asyncio.fixture()
async def client() -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[verify_api_key] = lambda: "test-key"
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="operator",
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
async def test_after_close_actuals_route_returns_explicit_partial_state(client: AsyncClient) -> None:
    from api.routers.ui.daily_after_close import get_post_market_review_service

    service = _FakePostMarketReviewService()
    app.dependency_overrides[get_post_market_review_service] = lambda: service
    try:
        response = await client.get(
            "/api/ui/v1/daily/after-close/actuals",
            params={
                "trading_day_plan_id": "plan-1",
                "post_close_market_snapshot_id": "snapshot-1",
            },
        )
    finally:
        app.dependency_overrides.pop(get_post_market_review_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["coverage_state"] == "partial"
    assert payload["signals"][1]["state"] == "insufficient_coverage"
    assert payload["signals"][1]["row_fingerprint"] is None
    assert service.actual_calls == [
        {
            "trading_day_plan_id": "plan-1",
            "post_close_market_snapshot_id": "snapshot-1",
            "actor_id": "tester",
            "actor_role": "operator",
        }
    ]


@pytest.mark.asyncio()
async def test_after_close_signal_results_route_uses_formal_service(client: AsyncClient) -> None:
    from api.routers.ui.daily_after_close import get_post_market_review_service

    service = _FakePostMarketReviewService()
    app.dependency_overrides[get_post_market_review_service] = lambda: service
    try:
        response = await client.post(
            "/api/ui/v1/daily/after-close/signal-results",
            json={
                "trading_day_plan_id": "plan-1",
                "post_close_market_snapshot_id": "snapshot-1",
                "post_close_market_state_id": "11111111-1111-1111-1111-111111111111",
            },
        )
    finally:
        app.dependency_overrides.pop(get_post_market_review_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "ready"
    assert payload["signal_results"][0]["executed"]["state"] == "unavailable"
    assert payload["evidence"]["attribution_state"] == "unavailable_RT-S10-002_not_started"
    assert service.evaluate_calls[0]["request"]["trading_day_plan_id"] == "plan-1"
