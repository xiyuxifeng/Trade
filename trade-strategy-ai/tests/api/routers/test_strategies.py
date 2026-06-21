from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app

RULE_VERSION_ID = "11111111-1111-1111-1111-111111111111"
METHOD_PROFILE_ID = "22222222-2222-2222-2222-222222222222"
RULE_PROFILE_ID = "33333333-3333-3333-3333-333333333333"
VALIDATED_PROFILE_ID = "44444444-4444-4444-4444-444444444444"
DATASET_SNAPSHOT_ID = "55555555-5555-5555-5555-555555555555"
MARKET_SNAPSHOT_ID = "66666666-6666-6666-6666-666666666666"
APPLICABILITY_PROFILE_ID = "77777777-7777-7777-7777-777777777777"
POST_MARKET_REVIEW_ID = "88888888-8888-8888-8888-888888888888"
PROPOSAL_ID = "99999999-9999-9999-9999-999999999999"
AFFECTED_STRATEGY_VERSION_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


@dataclass
class _FakeStrategyVersion:
    strategy_version_id: str = "strategy-version-1"
    strategy_id: str = "strategy-1"
    business_key: str = "cn-swing-core"
    title: str = "A股趋势轮动策略"
    summary: str = "正式策略草稿"
    version_no: int = 1
    lifecycle_state: str = "draft"
    lifecycle_label: str = "草稿"
    review_status: str = "draft"
    status_state: str = "draft"
    schema_version: str = "strategy-schema-v1"
    quality_status: str = "verified"
    rule_pool: list[dict[str, Any]] | None = None
    profiles: dict[str, Any] | None = None
    policies: dict[str, Any] | None = None
    evidence: dict[str, Any] | None = None
    current_status: dict[str, Any] | None = None
    validation: dict[str, Any] | None = None
    published_at: str | None = None
    partial_reasons: list[str] | None = None
    limitations: list[str] | None = None

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        del mode
        return {
            "strategy_version_id": self.strategy_version_id,
            "strategy_id": self.strategy_id,
            "business_key": self.business_key,
            "title": self.title,
            "summary": self.summary,
            "version_no": self.version_no,
            "lifecycle_state": self.lifecycle_state,
            "lifecycle_label": self.lifecycle_label,
            "review_status": self.review_status,
            "status_state": self.status_state,
            "schema_version": self.schema_version,
            "quality_status": self.quality_status,
            "rule_pool": self.rule_pool or [],
            "profiles": self.profiles
            or {
                "author_method_profile_version_id": METHOD_PROFILE_ID,
                "author_rule_profile_version_id": RULE_PROFILE_ID,
                "author_validated_profile_version_id": VALIDATED_PROFILE_ID,
            },
            "policies": self.policies
            or {
                "risk_policy_json": {"position_constraints": {"single_position_pct": 0.2}},
                "selection_policy_json": {"degradation_policy": {"missing_canonical_data": "unavailable"}},
                "universe_json": {"market": "CN"},
            },
            "evidence": self.evidence
            or {
                "dataset_snapshot_id": DATASET_SNAPSHOT_ID,
                "market_snapshot_ids": [MARKET_SNAPSHOT_ID],
                "rule_applicability_profile_ids": [APPLICABILITY_PROFILE_ID],
            },
            "current_status": self.current_status
            or {
                "is_current": False,
                "current_version_id": None,
                "previous_current_version_id": None,
            },
            "validation": self.validation
            or {
                "state": "not_run",
                "label": "尚未验证",
                "reviewer_decision": "review_required",
                "reviewer_decision_label": "待复核",
                "dataset_binding": {"state": "unavailable", "dataset_snapshot_id": None, "market_state_definition_version": None},
                "market_snapshot_binding": {"state": "unavailable", "market_snapshot_ids": []},
                "backtest": {
                    "state": "unavailable",
                    "out_of_sample_state": "unavailable",
                    "backtest_run_ids": [],
                    "backtest_result_ids": [],
                    "requested_level": None,
                    "effective_level": None,
                    "annual_return": None,
                    "max_drawdown": None,
                    "win_rate": None,
                },
                "rule_applicability": {
                    "state": "unavailable",
                    "covered_rule_count": 0,
                    "total_rule_count": 0,
                    "coverage_ratio": 0.0,
                    "uncovered_rule_version_ids": [],
                },
                "sample_coverage": {"state": "unknown", "sample_count": None, "insufficient_sample": False},
                "data_quality": {"state": "unavailable", "warnings": [], "limitations": []},
            },
            "published_at": self.published_at,
            "partial_reasons": self.partial_reasons or [],
            "limitations": self.limitations or [],
        }


class _FakeStrategyCenterService:
    async def list_versions(self, **kwargs):
        assert kwargs["actor_role"] == "viewer"
        return {
            "state": "ready",
            "current_strategy": {"business_key": "cn-swing-core", "current_version_id": "strategy-version-2"},
            "items": [_FakeStrategyVersion().model_dump()],
            "count": 1,
        }

    async def get_version(self, version_id: str, *, actor_id: str, actor_role: str):
        assert actor_role == "viewer"
        assert version_id == "strategy-version-1"
        return _FakeStrategyVersion()

    async def get_draft_options(self, *, actor_id: str, actor_role: str):
        assert actor_role == "viewer"
        return {
            "rule_options": [{"rule_version_id": RULE_VERSION_ID, "title": "放量突破"}],
            "author_profile_options": {
                "method": [{"author_profile_version_id": METHOD_PROFILE_ID, "label": "作者方法画像 v1"}],
                "rule": [{"author_profile_version_id": RULE_PROFILE_ID, "label": "作者规则画像 v1"}],
                "validated": [{"author_profile_version_id": VALIDATED_PROFILE_ID, "label": "作者验证画像 v1"}],
            },
            "dataset_options": [{"dataset_snapshot_id": DATASET_SNAPSHOT_ID, "label": "OHLCV 2026-06-19"}],
            "market_snapshot_options": [{"market_snapshot_id": MARKET_SNAPSHOT_ID, "label": "2026-06-19 盘后市场快照"}],
            "rule_applicability_options": [{"applicability_profile_id": APPLICABILITY_PROFILE_ID, "label": "放量突破适用性画像"}],
        }

    async def create_draft(self, request, *, actor_id: str, actor_role: str):
        assert actor_role == "operator"
        assert request.business_key == "cn-swing-core"
        return _FakeStrategyVersion(rule_pool=[{"rule_version_id": RULE_VERSION_ID, "title": "放量突破", "base_weight": 0.65}])

    async def submit_for_review(self, version_id: str, request, *, actor_id: str, actor_role: str):
        assert actor_role == "operator"
        return _FakeStrategyVersion(
            strategy_version_id=version_id,
            lifecycle_state="pending_review",
            lifecycle_label="待审核",
            review_status="pending_review",
            status_state="pending_review",
        )

    async def publish(self, version_id: str, request, *, actor_id: str, actor_role: str):
        assert actor_role == "operator"
        return _FakeStrategyVersion(
            strategy_version_id=version_id,
            lifecycle_state="published",
            lifecycle_label="已发布",
            review_status="published",
            status_state="published",
            current_status={
                "is_current": True,
                "current_version_id": version_id,
                "previous_current_version_id": "strategy-version-0",
            },
            published_at="2026-06-20T12:00:00+00:00",
        )

    async def validate_version(self, version_id: str, request, *, actor_id: str, actor_role: str):
        assert actor_role == "operator"
        assert request.reason == "校验正式策略"
        version = _FakeStrategyVersion(
            strategy_version_id=version_id,
            lifecycle_state="draft",
            lifecycle_label="草稿",
        ).model_dump()
        version["validation"] = {
            "state": "passed",
            "label": "验证通过",
            "reviewer_decision": "approved",
            "reviewer_decision_label": "已批准",
            "reason": "校验正式策略",
            "backtest": {"out_of_sample_state": "available"},
            "rule_applicability": {"coverage_ratio": 1.0},
            "sample_coverage": {"state": "sufficient"},
            "data_quality": {"state": "verified", "warnings": [], "limitations": []},
        }
        return version

    async def compare_with_current(self, version_id: str, *, actor_id: str, actor_role: str):
        assert actor_role == "viewer"
        return {
            "state": "ready",
            "current_version": _FakeStrategyVersion(strategy_version_id="strategy-version-current", lifecycle_state="published", lifecycle_label="已发布").model_dump(),
            "candidate_version": _FakeStrategyVersion(strategy_version_id=version_id).model_dump(),
            "delta": {
                "rule_count_change": 0,
                "rule_weight_changes": 1,
                "annual_return_change": 0.03,
                "max_drawdown_change": -0.01,
            },
        }

    async def diff_versions(self, version_id: str, *, actor_id: str, actor_role: str, base_version_id: str | None = None):
        assert actor_role == "viewer"
        assert base_version_id in {None, "strategy-version-current"}
        return {
            "state": "ready",
            "base_version": _FakeStrategyVersion(strategy_version_id="strategy-version-current", lifecycle_state="published", lifecycle_label="已发布").model_dump(),
            "target_version": _FakeStrategyVersion(strategy_version_id=version_id).model_dump(),
            "changes": [
                {"field": "title", "label": "策略名称", "before": "A股趋势轮动策略", "after": "A股趋势轮动策略 v2"},
                {"field": "rule_pool", "label": "规则池", "before": [{"rule_version_id": RULE_VERSION_ID, "base_weight": 0.65}], "after": [{"rule_version_id": RULE_VERSION_ID, "base_weight": 0.8}]},
            ],
        }

    async def rollback_to_version(self, version_id: str, request, *, actor_id: str, actor_role: str):
        assert actor_role == "operator"
        assert request.reason == "回退到上一正式版本"
        return _FakeStrategyVersion(
            strategy_version_id=version_id,
            lifecycle_state="published",
            lifecycle_label="已发布",
            current_status={
                "is_current": True,
                "current_version_id": version_id,
                "previous_current_version_id": "strategy-version-2",
            },
            published_at="2026-06-20T12:00:00+00:00",
        ).model_dump()

    async def list_proposals(self, **kwargs):
        assert kwargs["actor_role"] == "viewer"
        return {"state": "partial", "items": [self._proposal()], "count": 1}

    async def get_proposal(self, proposal_id: str, *, actor_id: str, actor_role: str):
        assert actor_role == "viewer"
        assert proposal_id == PROPOSAL_ID
        return _FakeProposal()

    async def create_proposal(self, request, *, actor_id: str, actor_role: str):
        assert actor_role == "operator"
        assert str(request.post_market_review_id) == POST_MARKET_REVIEW_ID
        assert str(request.affected_strategy_version_id) == AFFECTED_STRATEGY_VERSION_ID
        return _FakeProposal()

    async def review_proposal(self, proposal_id: str, request, *, actor_id: str, actor_role: str):
        assert actor_role == "operator"
        assert proposal_id == PROPOSAL_ID
        assert request.action == "reject"
        return _FakeProposal(lifecycle_state="rejected", lifecycle_label="已拒绝", available_actions=["archive"])

    async def accept_proposal_to_draft(self, proposal_id: str, request, *, actor_id: str, actor_role: str):
        assert actor_role == "operator"
        assert proposal_id == PROPOSAL_ID
        return _FakeProposal(
            lifecycle_state="accepted",
            lifecycle_label="已生成草稿",
            accepted_draft_version_id="draft-version-2",
            available_actions=["archive", "supersede"],
        )

    def _proposal(self) -> dict[str, Any]:
        return _FakeProposal().model_dump()


@dataclass
class _FakeProposal:
    proposal_id: str = PROPOSAL_ID
    proposal_type: str = "strategy_revision"
    lifecycle_state: str = "in_review"
    lifecycle_label: str = "复核中"
    revision_no: int = 1
    confidence: float = 0.82
    rationale: str = "近期样本表现回撤扩大，需要降低核心规则权重。"
    trigger_type: str = "manual_review"
    evidence_state: str = "partial"
    evidence_label: str = "证据不完整"
    accepted_draft_version_id: str | None = None
    available_actions: list[str] | None = None

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        del mode
        return {
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type,
            "lifecycle_state": self.lifecycle_state,
            "lifecycle_label": self.lifecycle_label,
            "revision_no": self.revision_no,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "trigger_type": self.trigger_type,
            "evidence_state": self.evidence_state,
            "evidence_label": self.evidence_label,
            "affected_strategy_version": {
                "strategy_version_id": "strategy-version-1",
                "strategy_id": "strategy-1",
                "business_key": "cn-swing-core",
                "title": "A股趋势轮动策略",
                "version_no": 1,
                "lifecycle_state": "published",
                "lifecycle_label": "已发布",
                "validation_summary": _FakeStrategyVersion().model_dump()["validation"],
                "current_status": {"is_current": True, "current_version_id": "strategy-version-1", "previous_current_version_id": None},
            },
            "base_version_id": "strategy-version-1",
            "accepted_draft_version_id": self.accepted_draft_version_id,
            "proposed_changes": {
                "summary": "降低核心规则仓位，增加回撤保护。",
                "proposed_weight_changes": [{"rule_version_id": RULE_VERSION_ID, "base_weight": 0.5}],
            },
            "evidence": {
                "rationale": self.rationale,
                "trigger_type": self.trigger_type,
                "validation_summary": _FakeStrategyVersion().model_dump()["validation"],
            },
            "created_at": "2026-06-20T12:00:00+00:00",
            "updated_at": "2026-06-20T12:30:00+00:00",
            "available_actions": self.available_actions or ["generate_draft", "reject", "return_to_draft"],
            "partial_reasons": ["样本外验证仍在补齐"],
            "limitations": ["尚未补齐全部市场状态切片"],
        }


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from api.routers.ui.strategies import get_strategy_center_service

    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_strategy_center_service] = lambda: _FakeStrategyCenterService()
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="viewer",
            api_key_label="viewer",
            authenticated=True,
            source="api_key",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


def _operator_override() -> CurrentPrincipal:
    return CurrentPrincipal(role="operator", api_key_label="operator", authenticated=True, source="api_key")


@pytest.mark.asyncio
async def test_strategy_routes_cover_list_detail_options_and_lifecycle_actions(client: AsyncClient) -> None:
    listed = await client.get("/api/ui/v1/strategies")
    assert listed.status_code == 200
    assert listed.json()["current_strategy"]["current_version_id"] == "strategy-version-2"
    assert listed.json()["items"][0]["business_key"] == "cn-swing-core"

    detail = await client.get("/api/ui/v1/strategies/strategy-version-1")
    assert detail.status_code == 200
    assert detail.json()["strategy_version_id"] == "strategy-version-1"

    options = await client.get("/api/ui/v1/strategies/draft-options")
    assert options.status_code == 200
    assert options.json()["rule_options"][0]["rule_version_id"] == RULE_VERSION_ID

    app.dependency_overrides[get_current_principal] = _operator_override
    payload = {
        "business_key": "cn-swing-core",
        "schema_version": "strategy-schema-v1",
        "title": "A股趋势轮动策略",
        "summary": "正式策略草稿",
        "rule_memberships": [
                {
                    "rule_version_id": RULE_VERSION_ID,
                    "base_weight": 0.65,
                    "status": "active",
                    "configuration_json": {"position_role": "core"},
                }
            ],
        "author_method_profile_version_id": METHOD_PROFILE_ID,
        "author_rule_profile_version_id": RULE_PROFILE_ID,
        "author_validated_profile_version_id": VALIDATED_PROFILE_ID,
        "risk_policy_json": {"position_constraints": {"single_position_pct": 0.2}},
        "selection_policy_json": {"degradation_policy": {"missing_canonical_data": "unavailable"}},
        "universe_json": {"market": "CN"},
        "evidence_json": {
            "dataset_snapshot_id": DATASET_SNAPSHOT_ID,
            "market_snapshot_ids": [MARKET_SNAPSHOT_ID],
            "rule_applicability_profile_ids": [APPLICABILITY_PROFILE_ID],
        },
    }

    created = await client.post("/api/ui/v1/strategies", json=payload)
    assert created.status_code == 201
    assert created.json()["lifecycle_state"] == "draft"
    assert created.json()["rule_pool"][0]["rule_version_id"] == RULE_VERSION_ID

    submitted = await client.post("/api/ui/v1/strategies/strategy-version-1/submit-review", json={"reason": "提交审核"})
    assert submitted.status_code == 200
    assert submitted.json()["lifecycle_state"] == "pending_review"

    published = await client.post("/api/ui/v1/strategies/strategy-version-1/publish", json={"reason": "审核通过"})
    assert published.status_code == 200
    assert published.json()["lifecycle_state"] == "published"
    assert published.json()["current_status"]["is_current"] is True

    validated = await client.post("/api/ui/v1/strategies/strategy-version-1/validate", json={"reason": "校验正式策略"})
    assert validated.status_code == 200
    assert validated.json()["validation"]["state"] == "passed"

    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="viewer",
        api_key_label="viewer",
        authenticated=True,
        source="api_key",
    )
    comparison = await client.get("/api/ui/v1/strategies/strategy-version-1/comparison")
    assert comparison.status_code == 200
    assert comparison.json()["delta"]["rule_weight_changes"] == 1

    diff = await client.get("/api/ui/v1/strategies/strategy-version-1/diff")
    assert diff.status_code == 200
    assert diff.json()["changes"][0]["field"] == "title"

    app.dependency_overrides[get_current_principal] = _operator_override
    rolled_back = await client.post("/api/ui/v1/strategies/strategy-version-1/rollback", json={"reason": "回退到上一正式版本"})
    assert rolled_back.status_code == 200
    assert rolled_back.json()["current_status"]["is_current"] is True

    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="viewer",
        api_key_label="viewer",
        authenticated=True,
        source="api_key",
    )
    proposals = await client.get("/api/ui/v1/strategies/proposals")
    assert proposals.status_code == 200
    assert proposals.json()["state"] == "partial"
    assert proposals.json()["items"][0]["proposal_id"] == PROPOSAL_ID

    proposal_detail = await client.get(f"/api/ui/v1/strategies/proposals/{PROPOSAL_ID}")
    assert proposal_detail.status_code == 200
    assert proposal_detail.json()["affected_strategy_version"]["strategy_version_id"] == "strategy-version-1"

    app.dependency_overrides[get_current_principal] = _operator_override
    created_proposal = await client.post(
        "/api/ui/v1/strategies/proposals",
        json={
            "post_market_review_id": POST_MARKET_REVIEW_ID,
            "affected_strategy_version_id": AFFECTED_STRATEGY_VERSION_ID,
            "rationale": "近期样本表现回撤扩大，需要降低核心规则权重。",
            "trigger_type": "manual_review",
            "confidence": 0.82,
            "proposed_changes": {"proposed_weight_changes": [{"rule_version_id": RULE_VERSION_ID, "base_weight": 0.5}]},
            "evidence_json": {"evidence_state": "partial"},
        },
    )
    assert created_proposal.status_code == 201
    assert created_proposal.json()["proposal_type"] == "strategy_revision"

    reviewed_proposal = await client.post(
        f"/api/ui/v1/strategies/proposals/{PROPOSAL_ID}/review",
        json={"action": "reject", "reason": "证据不足"},
    )
    assert reviewed_proposal.status_code == 200
    assert reviewed_proposal.json()["lifecycle_state"] == "rejected"

    accepted_proposal = await client.post(
        f"/api/ui/v1/strategies/proposals/{PROPOSAL_ID}/accept-to-draft",
        json={"reason": "生成策略草稿继续复核"},
    )
    assert accepted_proposal.status_code == 200
    assert accepted_proposal.json()["lifecycle_state"] == "accepted"
    assert accepted_proposal.json()["accepted_draft_version_id"] == "draft-version-2"
