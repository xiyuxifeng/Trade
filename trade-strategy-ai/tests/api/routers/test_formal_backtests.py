from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.formal_backtests import get_backtest_application_service


@dataclass
class _FakeDependencyResult:
    business_state: str = "可运行"
    canonical_state: str = "runnable"
    can_create_run: bool = True
    requested_level: str = "level_1"
    effective_level: str = "level_1"
    selection: dict[str, Any] | None = None
    coverage: dict[str, Any] | None = None
    unavailable_reasons: list[dict[str, Any]] | None = None
    limitations: list[str] | None = None
    next_actions: list[str] | None = None
    level_policy_version: str = "stage6-level-policy-v1"
    minimum_required_level: str = "level_1"
    missing_requirements: list[dict[str, Any]] | None = None
    downgrade_reason: str | None = None
    repair_guidance: list[str] | None = None
    required_market_snapshot_slot: str | None = None
    rule_dependency_details: list[dict[str, Any]] | None = None
    downgrade_requires_confirmation: bool = False
    downgrade_allowed: bool = False


@dataclass
class _FakeRun:
    run_id: str = "run-1"
    status: str = "dependency_checked"
    business_status: str = "已创建"
    rule_version_id: str | None = "rv-1"
    rule_family_id: str | None = None
    frozen_rule_version_ids: list[str] | None = None
    dataset_snapshot_id: str = "ds-1"
    request_fingerprint: str = "request-fp"
    reproducibility_fingerprint: str = "repro-fp"
    snapshot_only: bool = True
    progress: dict[str, Any] | None = None
    limitations: list[str] | None = None
    next_actions: list[str] | None = None
    requested_level: str = "level_1"
    effective_level: str = "level_1"
    level_policy_version: str = "stage6-level-policy-v1"
    coverage_state: str = "runnable"
    quality_state: str = "not_executed"
    downgrade_reason: str | None = None
    repair_guidance: list[str] | None = None


@dataclass
class _FakeResult:
    result_id: str = "result-1"
    run_id: str = "run-1"
    status: str = "completed_valid"
    requested_level: str = "level_2"
    effective_level: str = "level_2"
    market_state_model_version: str | None = "market-state-v1"
    market_state_source_version: str | None = "features-v1"
    market_state_result_version: str = "stage6-market-state-result-v1"
    overall_metrics: dict[str, Any] | None = None
    per_market_state_metrics: list[dict[str, Any]] | None = None
    sample_state_counts: dict[str, int] | None = None
    coverage: dict[str, Any] | None = None
    warnings: list[str] | None = None
    limitations: list[str] | None = None
    result_fingerprint: str = "result-fp"
    reproducibility_fingerprint: str = "market-state-v1:features-v1:result-fp"
    level_policy_version: str = "stage6-level-policy-v1"


class _FakeBacktestApplicationService:
    def __init__(self) -> None:
        self.create_calls = 0
        self.execute_calls = 0

    async def check_dependencies(self, selection, *, actor_id: str, actor_role: str):
        assert actor_role == "viewer"
        return _FakeDependencyResult(selection=selection.model_dump(mode="json"), coverage={"ohlcv": {"state": "ready"}})

    async def create_run(self, request):
        self.create_calls += 1
        assert request.actor_role == "operator"
        assert request.source_surface == "/rules/backtests"
        if request.selection.requested_level == "level_3":
            assert request.accept_downgrade is True
            assert request.accepted_effective_level == "level_1"
        return _FakeRun()

    async def get_run(self, run_id: str, *, actor_id: str, actor_role: str):
        assert run_id == "run-1"
        return _FakeRun()

    async def execute_run(self, run_id: str, *, actor_id: str, actor_role: str):
        self.execute_calls += 1
        assert run_id == "run-1"
        assert actor_role == "operator"
        return _FakeResult(
            overall_metrics={"hit_trade_count": 1},
            per_market_state_metrics=[
                {
                    "market_state_label": "强势",
                    "market_state_model_version": "market-state-v1",
                    "market_state_source_version": "features-v1",
                    "eligible_sample_count": 2,
                    "evaluated_sample_count": 2,
                    "unavailable_sample_count": 0,
                    "invalid_sample_count": 0,
                    "conflict_sample_count": 0,
                    "hit_trade_count": 1,
                    "win_rate": 1.0,
                    "coverage": 1.0,
                    "warnings": [],
                    "result_fingerprint": "bucket-fp",
                }
            ],
            sample_state_counts={"eligible": 2, "condition_unavailable": 1},
            coverage={"market_state": {"state": "ready", "available": True}},
            warnings=[],
            limitations=[],
        )

    async def get_result(self, run_id: str, *, actor_id: str, actor_role: str):
        assert run_id == "run-1"
        assert actor_role in {"viewer", "operator"}
        return _FakeResult(
            per_market_state_metrics=[],
            sample_state_counts={},
            coverage={"market_state": {"state": "ready", "available": True}},
            warnings=[],
            limitations=[],
        )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    fake_service = _FakeBacktestApplicationService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_backtest_application_service] = lambda: fake_service
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


def _selection_payload() -> dict[str, Any]:
    return {
        "rule_version_id": "00000000-0000-0000-0000-000000000001",
        "date_from": "2026-04-01",
        "date_to": "2026-04-10",
        "universe": {"symbols": ["000001.SZ"]},
        "benchmark_symbol": "000300.SH",
        "mode": "full",
        "requested_level": "level_1",
        "profile_id": "context-only",
    }


@pytest.mark.asyncio()
async def test_viewer_can_check_dependencies(client: AsyncClient) -> None:
    response = await client.post("/api/ui/v1/rules/backtests/dependency-check", json=_selection_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["business_state"] == "可运行"
    assert body["canonical_state"] == "runnable"
    assert body["coverage"]["ohlcv"]["state"] == "ready"
    assert body["level_policy_version"] == "stage6-level-policy-v1"
    assert body["minimum_required_level"] == "level_1"


@pytest.mark.asyncio()
async def test_viewer_cannot_create_formal_run_before_service_call() -> None:
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_backtest_application_service] = lambda: _FakeBacktestApplicationService()
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="viewer",
            api_key_label="viewer",
            authenticated=True,
            source="api_key",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/ui/v1/rules/backtests/runs",
                json={"selection": _selection_payload(), "reason": "验证规则"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio()
async def test_operator_can_create_and_read_formal_run() -> None:
    fake_service = _FakeBacktestApplicationService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_backtest_application_service] = lambda: fake_service
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="operator",
            api_key_label="operator",
            authenticated=True,
            source="api_key",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            created = await ac.post(
                "/api/ui/v1/rules/backtests/runs",
                json={"selection": _selection_payload(), "reason": "验证规则"},
            )
            loaded = await ac.get("/api/ui/v1/rules/backtests/runs/run-1")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["run_id"] == "run-1"
    assert created.json()["snapshot_only"] is True
    assert loaded.status_code == 200
    assert loaded.json()["request_fingerprint"] == "request-fp"
    assert fake_service.create_calls == 1


@pytest.mark.asyncio()
async def test_operator_can_accept_visible_downgrade_when_creating_formal_run() -> None:
    fake_service = _FakeBacktestApplicationService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_backtest_application_service] = lambda: fake_service
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="operator",
            api_key_label="operator",
            authenticated=True,
            source="api_key",
        )
        payload = {
            **_selection_payload(),
            "requested_level": "level_3",
            "date_to": "2026-04-01",
        }
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            created = await ac.post(
                "/api/ui/v1/rules/backtests/runs",
                json={
                    "selection": payload,
                    "reason": "接受缺少 Kaipan 数据时先按 Level 1 回测",
                    "accept_downgrade": True,
                    "accepted_effective_level": "level_1",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["level_policy_version"] == "stage6-level-policy-v1"
    assert fake_service.create_calls == 1


@pytest.mark.asyncio()
async def test_operator_can_execute_and_viewer_can_read_formal_result() -> None:
    fake_service = _FakeBacktestApplicationService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_backtest_application_service] = lambda: fake_service
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="operator",
            api_key_label="operator",
            authenticated=True,
            source="api_key",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            executed = await ac.post("/api/ui/v1/rules/backtests/runs/run-1/execute")

        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="viewer",
            api_key_label="viewer",
            authenticated=True,
            source="api_key",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            loaded = await ac.get("/api/ui/v1/rules/backtests/runs/run-1/result")
    finally:
        app.dependency_overrides.clear()

    assert executed.status_code == 200
    assert executed.json()["market_state_model_version"] == "market-state-v1"
    assert executed.json()["per_market_state_metrics"][0]["market_state_label"] == "强势"
    assert "features-v1" in executed.json()["reproducibility_fingerprint"]
    assert loaded.status_code == 200
    assert loaded.json()["result_fingerprint"] == "result-fp"
    assert fake_service.execute_calls == 1


@pytest.mark.asyncio()
async def test_viewer_cannot_execute_formal_result() -> None:
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_backtest_application_service] = lambda: _FakeBacktestApplicationService()
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="viewer",
            api_key_label="viewer",
            authenticated=True,
            source="api_key",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/ui/v1/rules/backtests/runs/run-1/execute")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
