from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.routers.ui.rule_lifecycle import get_rule_lifecycle_service


@dataclass
class _FakeAction:
    key: str
    label: str
    requires_reason: bool
    requires_evidence: bool


@dataclass
class _FakeLifecycleView:
    object_type: str
    object_id: str
    canonical_state: str
    display_state: str | None
    display_label: str | None
    status: str
    status_message: str | None
    restriction_message: str | None
    correlation_id: str | None
    updated_at: datetime
    allowed_next_actions: list[_FakeAction]
    metadata: dict[str, Any]


class _FakeRuleLifecycleService:
    def __init__(self) -> None:
        self.transition_calls = 0

    async def get_rule_version_lifecycle(self, *, rule_version_id: str) -> _FakeLifecycleView:
        return _FakeLifecycleView(
            object_type="rule_version",
            object_id=rule_version_id,
            canonical_state="draft",
            display_state="pending_backtest",
            display_label="待回测",
            status="ready",
            status_message=None,
            restriction_message=None,
            correlation_id="corr-1",
            updated_at=datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc),
            allowed_next_actions=[_FakeAction("start_validation", "开始验证", True, False)],
            metadata={"entry_point": "test"},
        )

    async def list_rule_version_history(self, *, rule_version_id: str) -> list[dict[str, Any]]:
        return [
            {
                "event_id": "evt-1",
                "canonical_state": "draft",
                "display_label": "待回测",
                "reason": "加入待回测队列。",
                "occurred_at": "2026-06-16T10:00:00+00:00",
            }
        ]

    async def transition_rule_version(self, **_: Any) -> _FakeLifecycleView:
        self.transition_calls += 1
        return _FakeLifecycleView(
            object_type="rule_version",
            object_id="rule-version-1",
            canonical_state="in_review",
            display_state="validating",
            display_label="验证中",
            status="ready",
            status_message=None,
            restriction_message=None,
            correlation_id="corr-2",
            updated_at=datetime(2026, 6, 16, 10, 5, tzinfo=timezone.utc),
            allowed_next_actions=[_FakeAction("mark_usable", "标记可用", True, True)],
            metadata={"entry_point": "api"},
        )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_rule_lifecycle_service] = lambda: _FakeRuleLifecycleService()
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
async def test_rule_lifecycle_router_reads_detail_history_and_transition(client: AsyncClient) -> None:
    detail = await client.get("/api/ui/v1/rule-lifecycle/rule-versions/rule-version-1")
    assert detail.status_code == 200
    assert detail.json()["display_label"] == "待回测"
    assert detail.json()["allowed_next_actions"][0]["label"] == "开始验证"

    history = await client.get("/api/ui/v1/rule-lifecycle/rule-versions/rule-version-1/history")
    assert history.status_code == 200
    assert history.json()["items"][0]["display_label"] == "待回测"

    transitioned = await client.post(
        "/api/ui/v1/rule-lifecycle/rule-versions/rule-version-1/transition",
        json={
            "target_state": "验证中",
            "reason": "开始验证。",
            "correlation_id": "corr-2",
            "expected_updated_at": "2026-06-16T10:00:00+00:00",
        },
    )
    assert transitioned.status_code == 200
    assert transitioned.json()["display_label"] == "验证中"


@pytest.mark.asyncio
async def test_rule_lifecycle_transition_requires_operator_permission() -> None:
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_rule_lifecycle_service] = lambda: _FakeRuleLifecycleService()
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="viewer",
            api_key_label="viewer",
            authenticated=True,
            source="api_key",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            transitioned = await ac.post(
                "/api/ui/v1/rule-lifecycle/rule-versions/rule-version-1/transition",
                json={
                    "target_state": "验证中",
                    "reason": "权限不足时不能变更规则生命周期。",
                    "correlation_id": "corr-forbidden",
                },
            )
            assert transitioned.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "principal",
    [
        CurrentPrincipal(role="anonymous", api_key_label=None, authenticated=False, source="anonymous"),
        CurrentPrincipal(role="viewer", api_key_label="viewer", authenticated=True, source="api_key"),
    ],
)
async def test_rule_lifecycle_mutation_endpoint_rejects_non_operator_before_service_calls(principal: CurrentPrincipal) -> None:
    fake_service = _FakeRuleLifecycleService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_rule_lifecycle_service] = lambda: fake_service
        app.dependency_overrides[get_current_principal] = lambda: principal
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/ui/v1/rule-lifecycle/rule-versions/rule-version-1/transition",
                json={
                    "target_state": "验证中",
                    "reason": "权限不足时不能变更规则生命周期。",
                    "correlation_id": "corr-forbidden",
                },
            )
        assert response.status_code == 403
        assert fake_service.transition_calls == 0
    finally:
        app.dependency_overrides.clear()
