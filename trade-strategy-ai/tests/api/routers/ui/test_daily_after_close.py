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
        self.generate_calls: list[dict[str, Any]] = []
        self.list_calls: list[dict[str, Any]] = []
        self.review_calls: list[dict[str, Any]] = []
        self.accept_calls: list[dict[str, Any]] = []

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

    async def generate_optimization_proposals(self, request, *, actor_id: str, actor_role: str):
        self.generate_calls.append({"request": request.model_dump(mode="json"), "actor_id": actor_id, "actor_role": actor_role})
        return _FakeResult(self._proposal_collection())

    async def list_optimization_proposals(self, *, actor_id: str, actor_role: str, post_market_review_id: str | None, proposal_type: str | None, limit: int):
        self.list_calls.append(
            {
                "actor_id": actor_id,
                "actor_role": actor_role,
                "post_market_review_id": post_market_review_id,
                "proposal_type": proposal_type,
                "limit": limit,
            }
        )
        return _FakeResult(self._proposal_collection())

    async def get_optimization_proposal(self, proposal_id: str, *, actor_id: str, actor_role: str):
        assert proposal_id == "proposal-strategy"
        return _FakeResult(self._proposal_collection()["items"][2])

    async def review_optimization_proposal(self, proposal_id: str, request, *, actor_id: str, actor_role: str):
        self.review_calls.append(
            {
                "proposal_id": proposal_id,
                "request": request.model_dump(mode="json"),
                "actor_id": actor_id,
                "actor_role": actor_role,
            }
        )
        return _FakeResult({**self._proposal_collection()["items"][0], "lifecycle_state": "rejected", "lifecycle_label": "已拒绝"})

    async def accept_optimization_proposal_to_draft(self, proposal_id: str, request, *, actor_id: str, actor_role: str):
        self.accept_calls.append(
            {
                "proposal_id": proposal_id,
                "request": request.model_dump(mode="json"),
                "actor_id": actor_id,
                "actor_role": actor_role,
            }
        )
        return _FakeResult(
            {
                **self._proposal_collection()["items"][2],
                "lifecycle_state": "accepted",
                "lifecycle_label": "已生成草稿",
                "accepted_draft_version_id": "draft-version-1",
            }
        )

    def _proposal_collection(self) -> dict[str, Any]:
        return {
            "state": "partial",
            "count": 3,
            "items": [
                {
                    "proposal_id": "proposal-rule",
                    "proposal_type": "rule_optimization",
                    "proposal_type_label": "规则优化建议",
                    "lifecycle_state": "draft",
                    "lifecycle_label": "待处理",
                    "revision_no": 1,
                    "confidence": 0.43,
                    "evidence_state": "ready",
                    "evidence_label": "证据完整",
                    "recommendation_state": "continue_observing",
                    "recommendation_label": "继续观察",
                    "rationale": "规则层仅形成观察建议。",
                    "target": {"asset_type": "RuleVersion", "asset_id": "rule-1", "label": "竞价强势跟随", "strategy_membership_ids": ["membership-1"], "rule_version_ids": ["rule-1"], "author_profile_version_ids": []},
                    "review_binding": {"post_market_review_id": "review-1", "trading_day_plan_id": "plan-1", "daily_strategy_instance_id": "instance-1", "strategy_version_id": "strategy-version-1"},
                    "base_version_id": "rule-1",
                    "accepted_draft_version_id": None,
                    "proposed_changes": {"recommended_action": "continue_observing"},
                    "evidence": {"policy_version": "stage10-optimization-proposal-v1"},
                    "created_at": "2026-06-21T17:31:00+00:00",
                    "updated_at": "2026-06-21T17:31:00+00:00",
                    "available_actions": ["start_review", "reject"],
                    "partial_reasons": [],
                    "limitations": [],
                },
                {
                    "proposal_id": "proposal-author",
                    "proposal_type": "author_profile_revision",
                    "proposal_type_label": "作者画像修订建议",
                    "lifecycle_state": "draft",
                    "lifecycle_label": "待处理",
                    "revision_no": 1,
                    "confidence": 0.4,
                    "evidence_state": "partial",
                    "evidence_label": "证据不完整",
                    "recommendation_state": "continue_observing",
                    "recommendation_label": "继续观察",
                    "rationale": "画像层仅形成观察建议。",
                    "target": {"asset_type": "AuthorProfileVersion", "asset_id": "profile-1", "label": "作者验证画像 v1", "strategy_membership_ids": [], "rule_version_ids": ["rule-1"], "author_profile_version_ids": ["profile-1"]},
                    "review_binding": {"post_market_review_id": "review-1", "trading_day_plan_id": "plan-1", "daily_strategy_instance_id": "instance-1", "strategy_version_id": "strategy-version-1"},
                    "base_version_id": "profile-1",
                    "accepted_draft_version_id": None,
                    "proposed_changes": {"recommended_action": "continue_observing"},
                    "evidence": {"policy_version": "stage10-optimization-proposal-v1"},
                    "created_at": "2026-06-21T17:31:00+00:00",
                    "updated_at": "2026-06-21T17:31:00+00:00",
                    "available_actions": ["start_review", "reject"],
                    "partial_reasons": ["证据仍需继续观察"],
                    "limitations": [],
                },
                {
                    "proposal_id": "proposal-strategy",
                    "proposal_type": "strategy_revision",
                    "proposal_type_label": "策略修订建议",
                    "lifecycle_state": "in_review",
                    "lifecycle_label": "复核中",
                    "revision_no": 1,
                    "confidence": 0.68,
                    "evidence_state": "ready",
                    "evidence_label": "证据完整",
                    "recommendation_state": "create_draft_review_suggestion",
                    "recommendation_label": "生成草稿复核建议",
                    "rationale": "策略层可安全进入草稿复核。",
                    "target": {"asset_type": "StrategyVersion", "asset_id": "strategy-version-1", "label": "正式策略 v1", "strategy_membership_ids": ["membership-1"], "rule_version_ids": ["rule-1"], "author_profile_version_ids": ["profile-1"]},
                    "review_binding": {"post_market_review_id": "review-1", "trading_day_plan_id": "plan-1", "daily_strategy_instance_id": "instance-1", "strategy_version_id": "strategy-version-1"},
                    "base_version_id": "strategy-version-1",
                    "accepted_draft_version_id": None,
                    "proposed_changes": {"recommended_action": "create_draft_review_suggestion"},
                    "evidence": {"policy_version": "stage10-optimization-proposal-v1"},
                    "created_at": "2026-06-21T17:31:00+00:00",
                    "updated_at": "2026-06-21T17:31:00+00:00",
                    "available_actions": ["continue_observing", "accept_to_draft", "reject"],
                    "partial_reasons": [],
                    "limitations": [],
                },
            ],
            "happened": "已生成分离建议。",
            "affected": "正式对象不会被直接改写。",
            "repair_guidance": "先进入复核。",
        }


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


@pytest.mark.asyncio()
async def test_after_close_generate_proposals_route_returns_separated_lanes(client: AsyncClient) -> None:
    from api.routers.ui.daily_after_close import get_post_market_review_service

    service = _FakePostMarketReviewService()
    app.dependency_overrides[get_post_market_review_service] = lambda: service
    try:
        response = await client.post(
            "/api/ui/v1/daily/after-close/proposals/generate",
            json={"post_market_review_id": "review-1"},
        )
    finally:
        app.dependency_overrides.pop(get_post_market_review_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 3
    assert {item["proposal_type"] for item in payload["items"]} == {
        "rule_optimization",
        "author_profile_revision",
        "strategy_revision",
    }
    assert service.generate_calls[0]["request"]["post_market_review_id"] == "review-1"


@pytest.mark.asyncio()
async def test_after_close_list_proposals_route_supports_filters(client: AsyncClient) -> None:
    from api.routers.ui.daily_after_close import get_post_market_review_service

    service = _FakePostMarketReviewService()
    app.dependency_overrides[get_post_market_review_service] = lambda: service
    try:
        response = await client.get(
            "/api/ui/v1/daily/after-close/proposals",
            params={"post_market_review_id": "review-1", "proposal_type": "strategy_revision", "limit": 10},
        )
    finally:
        app.dependency_overrides.pop(get_post_market_review_service, None)

    assert response.status_code == 200
    assert service.list_calls[0]["post_market_review_id"] == "review-1"
    assert service.list_calls[0]["proposal_type"] == "strategy_revision"
    assert service.list_calls[0]["limit"] == 10


@pytest.mark.asyncio()
async def test_after_close_review_and_accept_routes_use_safe_service_actions(client: AsyncClient) -> None:
    from api.routers.ui.daily_after_close import get_post_market_review_service

    service = _FakePostMarketReviewService()
    app.dependency_overrides[get_post_market_review_service] = lambda: service
    try:
        review_response = await client.post(
            "/api/ui/v1/daily/after-close/proposals/proposal-rule/review",
            json={"action": "reject", "reason": "单日证据不足"},
        )
        accept_response = await client.post(
            "/api/ui/v1/daily/after-close/proposals/proposal-strategy/accept-to-draft",
            json={"reason": "进入草稿复核"},
        )
    finally:
        app.dependency_overrides.pop(get_post_market_review_service, None)

    assert review_response.status_code == 200
    assert review_response.json()["lifecycle_state"] == "rejected"
    assert accept_response.status_code == 200
    assert accept_response.json()["accepted_draft_version_id"] == "draft-version-1"
    assert service.review_calls[0]["proposal_id"] == "proposal-rule"
    assert service.accept_calls[0]["proposal_id"] == "proposal-strategy"
