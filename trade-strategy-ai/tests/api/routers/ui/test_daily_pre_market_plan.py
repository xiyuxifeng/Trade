from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app


@dataclass
class _FakePlan:
    state: str = "partial"
    plan_status: str = "degraded"
    generated: bool = True
    trade_date: str = "2026-06-21"
    happened: str = "已根据已接受的每日规则选择生成每日运行计划。"
    affected: str = "今日盘前执行对象、信号和风险提示已经固定，可在批准后执行。"
    repair_guidance: str = "若需降低风险，请先补齐降级输入后重新生成计划。"
    daily_strategy_instance_id: str = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    trading_day_plan_id: str = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    daily_rule_selection_id: str = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    revision_no: int = 1
    strategy_version_id: str = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    instance_lifecycle_state: str = "generated"
    plan_lifecycle_state: str = "in_review"
    approval_state: str = "pending"
    approved_by: str | None = None
    approved_at: str | None = None
    rejection_reason: str | None = None

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        del mode
        return {
            "state": self.state,
            "plan_status": self.plan_status,
            "generated": self.generated,
            "trade_date": self.trade_date,
            "happened": self.happened,
            "affected": self.affected,
            "repair_guidance": self.repair_guidance,
            "daily_strategy_instance_id": self.daily_strategy_instance_id,
            "trading_day_plan_id": self.trading_day_plan_id,
            "daily_rule_selection_id": self.daily_rule_selection_id,
            "revision_no": self.revision_no,
            "strategy_version_id": self.strategy_version_id,
            "instance_lifecycle_state": self.instance_lifecycle_state,
            "plan_lifecycle_state": self.plan_lifecycle_state,
            "approval_state": self.approval_state,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "rejection_reason": self.rejection_reason,
            "market_judgment": {"state": "degraded", "summary": "强势上行（置信度 74%（中等））", "details": []},
            "enabled_rules": [],
            "reduced_rules": [],
            "suspended_rules": [],
            "candidate_symbols": [{"symbol": "000001.SZ", "name": "平安银行", "rank": 1, "state": "ready"}],
            "candidate_symbols_state": {"state": "ready", "summary": "候选标的来自正式盘前市场快照 strong_symbols section。", "details": []},
            "signals": [],
            "entry_conditions": {"state": "ready", "summary": "已整理入场条件。", "details": ["规则 1"]},
            "invalidation_conditions": {"state": "ready", "summary": "若市场状态变化，本计划即时失效。", "details": []},
            "stop_loss_take_profit": {"state": "ready", "summary": "已绑定正式策略风险控制参数。", "details": ["止损：5%"]},
            "suggested_position": {"state": "degraded", "summary": "建议单日总仓位不超过 35.0%。", "details": []},
            "risk_warnings": {"state": "degraded", "summary": "执行前请先确认今日盘前依赖状态。", "details": ["降级输入：insufficient_sample"]},
            "confidence": {"state": "degraded", "summary": "74%（中等）", "details": []},
            "traceability": {
                "trade_date": self.trade_date,
                "strategy_version_id": self.strategy_version_id,
                "daily_rule_selection_id": self.daily_rule_selection_id,
                "dataset_snapshot_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                "market_snapshot_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "market_state_id": "11111111-1111-1111-1111-111111111111",
                "current_market_state_label": "强势上行",
                "rule_applicability_profile_ids": ["22222222-2222-2222-2222-222222222222"],
                "author_method_profile_version_id": "33333333-3333-3333-3333-333333333333",
                "author_rule_profile_version_id": "44444444-4444-4444-4444-444444444444",
                "author_validated_profile_version_id": "55555555-5555-5555-5555-555555555555",
                "data_quality_state": "degraded",
                "readiness_status": "degraded",
                "selected_rules": [],
                "reduced_rules": [],
                "suspended_rules": [],
                "degraded_inputs": ["insufficient_sample"],
                "unresolved_inputs": [],
            },
        }


class _FakeTradingPlanService:
    def __init__(self) -> None:
        self.get_calls: list[dict[str, Any]] = []
        self.review_calls: list[dict[str, Any]] = []

    async def get_trading_day_plan(self, trade_date: str, *, actor_id: str, actor_role: str):
        self.get_calls.append({"trade_date": trade_date, "actor_id": actor_id, "actor_role": actor_role})
        return _FakePlan()

    async def review_trading_day_plan(self, trade_date: str, *, actor_id: str, actor_role: str, request):
        self.review_calls.append(
            {"trade_date": trade_date, "actor_id": actor_id, "actor_role": actor_role, "action": request.action, "reason": request.reason}
        )
        return _FakePlan(plan_lifecycle_state="approved", approval_state="approved", approved_by=actor_id, approved_at="2026-06-21T08:40:00+00:00")


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
async def test_daily_trading_plan_route_returns_traceable_runtime_plan(client: AsyncClient) -> None:
    from api.routers.ui.daily_pre_market import get_daily_trading_plan_service

    service = _FakeTradingPlanService()
    app.dependency_overrides[get_daily_trading_plan_service] = lambda: service
    try:
        response = await client.get("/api/ui/v1/daily/pre-market/plan", params={"trade_date": "2026-06-21"})
    finally:
        app.dependency_overrides.pop(get_daily_trading_plan_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan_status"] == "degraded"
    assert payload["approval_state"] == "pending"
    assert payload["traceability"]["daily_rule_selection_id"] == "cccccccc-cccc-cccc-cccc-cccccccccccc"
    assert service.get_calls == [{"trade_date": "2026-06-21", "actor_id": "tester", "actor_role": "operator"}]


@pytest.mark.asyncio()
async def test_daily_trading_plan_review_route_accepts_approval_action(client: AsyncClient) -> None:
    from api.routers.ui.daily_pre_market import get_daily_trading_plan_service

    service = _FakeTradingPlanService()
    app.dependency_overrides[get_daily_trading_plan_service] = lambda: service
    try:
        response = await client.post(
            "/api/ui/v1/daily/pre-market/plan/review",
            params={"trade_date": "2026-06-21"},
            json={"action": "approve"},
        )
    finally:
        app.dependency_overrides.pop(get_daily_trading_plan_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["approval_state"] == "approved"
    assert payload["approved_by"] == "tester"
    assert service.review_calls == [
        {"trade_date": "2026-06-21", "actor_id": "tester", "actor_role": "operator", "action": "approve", "reason": None}
    ]
