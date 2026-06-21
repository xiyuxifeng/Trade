from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app


@dataclass
class _FakeSelection:
    state: str = "partial"
    selection_status: str = "degraded"
    generated: bool = True
    trade_date: str = "2026-06-21"
    happened: str = "部分规则因为样本不足被降权。"
    affected: str = "今日规则选择可继续，但需要关注降级输入。"
    repair_guidance: str = "先补齐适用性证据，或按降级结果继续。"
    daily_rule_selection_id: str = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    revision_no: int = 1
    strategy_version_id: str = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    quality_status: str = "partial"
    readiness_status: str = "degraded"
    enabled_rules: list[dict[str, Any]] | None = None
    reduced_rules: list[dict[str, Any]] | None = None
    suspended_rules: list[dict[str, Any]] | None = None
    traceability: dict[str, Any] | None = None
    degraded_inputs: list[str] | None = None
    unresolved_inputs: list[str] | None = None

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        del mode
        return {
            "state": self.state,
            "selection_status": self.selection_status,
            "generated": self.generated,
            "trade_date": self.trade_date,
            "happened": self.happened,
            "affected": self.affected,
            "repair_guidance": self.repair_guidance,
            "daily_rule_selection_id": self.daily_rule_selection_id,
            "revision_no": self.revision_no,
            "strategy_version_id": self.strategy_version_id,
            "quality_status": self.quality_status,
            "readiness_status": self.readiness_status,
            "enabled_rules": self.enabled_rules
            or [
                {
                    "rule_version_id": "rule-version-1",
                    "strategy_rule_membership_id": "membership-1",
                    "decision": "selected",
                    "controlling_priority_tier": "current_market_state",
                    "controlling_priority_label": "当前市场状态",
                    "evidence_ids": ["applicability-1", "market-state-1"],
                    "quality_states": ["verified", "ready"],
                    "reason_tiers": ["formal_rule_applicability", "current_market_state"],
                    "reason_list": ["规则适用性已发布。", "当前市场状态与规则适配。"],
                    "degraded_inputs": [],
                    "unresolved_inputs": [],
                }
            ],
            "reduced_rules": self.reduced_rules
            or [
                {
                    "rule_version_id": "rule-version-2",
                    "strategy_rule_membership_id": "membership-2",
                    "decision": "reduced",
                    "controlling_priority_tier": "formal_rule_applicability",
                    "controlling_priority_label": "正式规则适用性",
                    "evidence_ids": ["applicability-2"],
                    "quality_states": ["partial", "insufficient_sample"],
                    "reason_tiers": ["formal_rule_applicability"],
                    "reason_list": ["样本不足，今日降权处理。"],
                    "degraded_inputs": ["insufficient_sample"],
                    "unresolved_inputs": [],
                }
            ],
            "suspended_rules": self.suspended_rules
            or [
                {
                    "rule_version_id": "rule-version-3",
                    "strategy_rule_membership_id": "membership-3",
                    "decision": "suspended",
                    "controlling_priority_tier": "formal_rule_applicability",
                    "controlling_priority_label": "正式规则适用性",
                    "evidence_ids": [],
                    "quality_states": ["unavailable"],
                    "reason_tiers": ["formal_rule_applicability"],
                    "reason_list": ["缺少正式规则适用性，今日暂停。"],
                    "degraded_inputs": [],
                    "unresolved_inputs": ["missing_rule_applicability"],
                }
            ],
            "traceability": self.traceability
            or {
                "trade_date": self.trade_date,
                "strategy_version_id": self.strategy_version_id,
                "dataset_snapshot_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "market_snapshot_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                "market_state_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                "rule_applicability_profile_ids": ["applicability-1", "applicability-2"],
                "author_method_profile_version_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "author_rule_profile_version_id": "11111111-1111-1111-1111-111111111111",
                "author_validated_profile_version_id": "22222222-2222-2222-2222-222222222222",
                "data_quality_state": "degraded",
                "readiness_status": "degraded",
            },
            "degraded_inputs": self.degraded_inputs or ["insufficient_sample"],
            "unresolved_inputs": self.unresolved_inputs or [],
        }


class _FakeDailyRuleSelectionService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def get_rule_selection(self, trade_date: str, *, actor_id: str, actor_role: str):
        self.calls.append({"trade_date": trade_date, "actor_id": actor_id, "actor_role": actor_role})
        return _FakeSelection()


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
async def test_daily_rule_selection_route_returns_traceable_payload(client: AsyncClient) -> None:
    from api.routers.ui.daily_pre_market import get_daily_rule_selection_service

    service = _FakeDailyRuleSelectionService()
    app.dependency_overrides[get_daily_rule_selection_service] = lambda: service
    try:
        response = await client.get("/api/ui/v1/daily/pre-market/rule-selection", params={"trade_date": "2026-06-21"})
    finally:
        app.dependency_overrides.pop(get_daily_rule_selection_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["selection_status"] == "degraded"
    assert payload["generated"] is True
    assert payload["reduced_rules"][0]["controlling_priority_tier"] == "formal_rule_applicability"
    assert payload["suspended_rules"][0]["unresolved_inputs"] == ["missing_rule_applicability"]
    assert payload["traceability"]["market_state_id"] == "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    assert service.calls == [{"trade_date": "2026-06-21", "actor_id": "tester", "actor_role": "viewer"}]
