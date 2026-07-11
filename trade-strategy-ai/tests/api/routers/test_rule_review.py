from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app


@dataclass
class _FakeAutomaticReview:
    status: str
    label: str
    risk_level: str
    reasons: list[str]
    requires_human_review: bool
    blocked_reason: str | None = None


@dataclass
class _FakeCandidateItem:
    candidate_id: str
    title: str
    source_article_title: str
    automatic_review: _FakeAutomaticReview
    current_review_state: str
    lifecycle_state: str
    allowed_actions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class _FakeActionResult:
    candidate_id: str
    current_review_state: str
    current_lifecycle_state: str | None
    rule_version_id: str | None
    last_action: str
    allowed_actions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class _FakeBatchResult:
    processed_count: int
    skipped_count: int
    items: list[dict[str, Any]] = field(default_factory=list)


class _FakeRuleReviewService:
    def __init__(self) -> None:
        self.action_calls = 0
        self.batch_calls = 0

    async def list_candidates(self, **_: Any) -> list[_FakeCandidateItem]:
        return [
            _FakeCandidateItem(
                candidate_id="candidate-1",
                title="低风险规则",
                source_article_title="示例文章",
                automatic_review=_FakeAutomaticReview(
                    status="recommend_pass",
                    label="建议通过",
                    risk_level="low",
                    reasons=["证据完整"],
                    requires_human_review=False,
                ),
                current_review_state="待审核",
                lifecycle_state="候选",
                allowed_actions=[{"key": "approve", "label": "批准"}],
            )
        ]

    async def get_candidate_detail(self, *, candidate_id: str) -> dict[str, Any]:
        return {
            "candidate_id": candidate_id,
            "title": "低风险规则",
            "source_article": {"title": "示例文章", "summary": "冻结摘要"},
            "automatic_review": {
                "status": "recommend_pass",
                "label": "建议通过",
                "risk_level": "low",
                "reasons": ["证据完整"],
                "requires_human_review": False,
                "blocked_reason": None,
            },
            "current_review_state": "待审核",
            "current_lifecycle_state": "候选",
            "allowed_actions": [{"key": "approve", "label": "批准"}],
            "history": [],
        }

    async def apply_action(self, **_: Any) -> _FakeActionResult:
        self.action_calls += 1
        return _FakeActionResult(
            candidate_id="candidate-1",
            current_review_state="已批准",
            current_lifecycle_state="已批准",
            rule_version_id="rule-version-1",
            last_action="approve",
            allowed_actions=[{"key": "queue_backtest", "label": "进入待回测"}],
        )

    async def apply_batch_action(self, **_: Any) -> _FakeBatchResult:
        self.batch_calls += 1
        return _FakeBatchResult(
            processed_count=1,
            skipped_count=0,
            items=[{"candidate_id": "candidate-1", "status": "processed"}],
        )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from api.routers.ui.rule_review import get_rule_review_service

    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_rule_review_service] = lambda: _FakeRuleReviewService()
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="operator",
            api_key_label="tester",
            authenticated=True,
            source="api_key",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rule_review_router_keeps_old_candidates_read_only(client: AsyncClient) -> None:
    listing = await client.get("/api/ui/v1/rule-review/candidates")
    assert listing.status_code == 200
    assert listing.json()["items"][0]["automatic_review"]["status"] == "recommend_pass"

    detail = await client.get("/api/ui/v1/rule-review/candidates/candidate-1")
    assert detail.status_code == 200
    assert detail.json()["source_article"]["title"] == "示例文章"

    action = await client.post(
        "/api/ui/v1/rule-review/candidates/candidate-1/actions",
        json={"action": "approve", "reason": "人工确认通过。", "correlation_id": "corr-1"},
    )
    assert action.status_code == 410
    assert action.json()["detail"]["status"] == "retired_read_only"

    batch = await client.post(
        "/api/ui/v1/rule-review/candidates/batch-actions",
        json={"action": "approve_low_risk", "reason": "批量通过。", "correlation_id": "corr-batch", "candidate_ids": ["candidate-1"]},
    )
    assert batch.status_code == 410
    assert batch.json()["detail"]["status"] == "retired_read_only"


@pytest.mark.asyncio
async def test_rule_review_router_enforces_permissions() -> None:
    from api.routers.ui.rule_review import get_rule_review_service

    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_rule_review_service] = lambda: _FakeRuleReviewService()
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="viewer",
            api_key_label="viewer",
            authenticated=True,
            source="api_key",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/ui/v1/rule-review/candidates/candidate-1/actions",
                json={"action": "approve", "reason": "forbidden", "correlation_id": "corr-2"},
            )
            assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("principal", "path", "payload"),
    [
        (
            CurrentPrincipal(role="anonymous", api_key_label=None, authenticated=False, source="anonymous"),
            "/api/ui/v1/rule-review/candidates/candidate-1/actions",
            {"action": "approve", "reason": "forbidden", "correlation_id": "corr-anon"},
        ),
        (
            CurrentPrincipal(role="viewer", api_key_label="viewer", authenticated=True, source="api_key"),
            "/api/ui/v1/rule-review/candidates/candidate-1/actions",
            {"action": "approve", "reason": "forbidden", "correlation_id": "corr-viewer"},
        ),
        (
            CurrentPrincipal(role="anonymous", api_key_label=None, authenticated=False, source="anonymous"),
            "/api/ui/v1/rule-review/candidates/batch-actions",
            {"action": "approve_low_risk", "reason": "forbidden", "correlation_id": "corr-batch-anon", "candidate_ids": ["candidate-1"]},
        ),
        (
            CurrentPrincipal(role="viewer", api_key_label="viewer", authenticated=True, source="api_key"),
            "/api/ui/v1/rule-review/candidates/batch-actions",
            {"action": "approve_low_risk", "reason": "forbidden", "correlation_id": "corr-batch-viewer", "candidate_ids": ["candidate-1"]},
        ),
    ],
)
async def test_rule_review_mutation_endpoints_reject_non_operator_before_service_calls(
    principal: CurrentPrincipal,
    path: str,
    payload: dict[str, Any],
) -> None:
    from api.routers.ui.rule_review import get_rule_review_service

    fake_service = _FakeRuleReviewService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_rule_review_service] = lambda: fake_service
        app.dependency_overrides[get_current_principal] = lambda: principal
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(path, json=payload)
        assert response.status_code == 403
        assert fake_service.action_calls == 0
        assert fake_service.batch_calls == 0
    finally:
        app.dependency_overrides.clear()
