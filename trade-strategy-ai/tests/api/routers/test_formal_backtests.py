from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.formal_backtests import get_backtest_application_service
from api.routers.ui.rule_pool_backtest_batches import get_rule_pool_backtest_batch_service


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
    per_rule_metrics: list[dict[str, Any]] | None = None
    sample_state_counts: dict[str, int] | None = None
    coverage: dict[str, Any] | None = None
    warnings: list[str] | None = None
    limitations: list[str] | None = None
    provenance: dict[str, Any] | None = None
    audit: dict[str, Any] | None = None
    result_fingerprint: str = "result-fp"
    reproducibility_fingerprint: str = "market-state-v1:features-v1:result-fp"
    level_policy_version: str = "stage6-level-policy-v1"


@dataclass
class _FakeProfile:
    profile_id: str = "profile-1"
    profile_version_no: int = 1
    rule_version_id: str | None = "rv-1"
    rule_family_id: str | None = None
    market_state_model_version: str | None = "market-state-v1"
    source_backtest_run_ids: list[str] | None = None
    source_backtest_result_ids: list[str] | None = None
    source_result_fingerprints: list[str] | None = None
    sample_count: int = 12
    eligible_sample_count: int = 12
    evaluated_sample_count: int = 12
    coverage: float = 0.92
    return_metric: float = 0.18
    win_rate: float = 0.64
    maximum_drawdown: float = -0.08
    confidence: float = 0.9
    recommendation_status: str = "recommended"
    requested_level: str = "level_3"
    effective_level: str = "level_2"
    level_policy_version: str = "stage6-level-policy-v1"
    insufficient_sample_status: str = "sufficient"
    limitations: list[str] | None = None
    warnings: list[str] | None = None
    review_status: str = "draft"


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
            per_rule_metrics=[{"rule_version_id": "rv-1", "eligible_sample_count": 2}],
            sample_state_counts={"eligible": 2, "condition_unavailable": 1},
            coverage={"market_state": {"state": "ready", "available": True}},
            warnings=[],
            limitations=[],
            provenance={"run_id": "run-1", "dataset_fingerprint": "ds-fp"},
            audit={"source_surface": "/rules/backtests", "actor_role": "operator"},
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

    async def generate_applicability_draft(self, run_id: str, result_id: str | None, *, actor_id: str, actor_role: str, reason: str | None):
        assert run_id == "run-1"
        assert result_id == "result-1"
        assert actor_role == "operator"
        return _FakeProfile(
            source_backtest_run_ids=["run-1"],
            source_backtest_result_ids=["result-1"],
            source_result_fingerprints=["result-fp"],
            limitations=["Level 3 缺少 Kaipan 数据，画像只能按有效等级解释。"],
            warnings=["样本包含缺失 Kaipan 数据。"],
        )

    async def review_applicability_profile(self, profile_id: str, review_status: str, *, actor_id: str, actor_role: str, reason: str | None):
        assert profile_id == "profile-1"
        assert actor_role == "operator"
        assert review_status == "approved"
        return _FakeProfile(review_status="approved")

    async def publish_applicability_profile(self, profile_id: str, *, actor_id: str, actor_role: str, reason: str | None):
        assert profile_id == "profile-1"
        assert actor_role == "operator"
        return _FakeProfile(review_status="published")


class _FakeRulePoolBacktestBatchService:
    def __init__(self) -> None:
        self.created = 0
        self.started = 0
        self.merged = 0

    async def create_batch_run(self, **kwargs):
        self.created += 1
        assert kwargs["rule_ids"] == ["rule-1", "rule-2", "rule-3"]
        assert kwargs["batch_size"] == 2
        assert kwargs["created_by"] == "operator"
        return {
            "batch_run_id": "batch-run-1",
            "status": "draft",
            "selected_rule_count": 3,
            "batch_size": 2,
            "batches": [
                {"batch_index": 1, "rule_ids": ["rule-1", "rule-2"], "status": "pending"},
                {"batch_index": 2, "rule_ids": ["rule-3"], "status": "pending"},
            ],
        }

    async def list_batch_runs(self, **kwargs):
        return {"items": [], "count": 0, "total": 0, "skip": kwargs["skip"], "limit": kwargs["limit"]}

    async def get_batch_run(self, batch_run_id: str):
        assert batch_run_id == "batch-run-1"
        return {
            "batch_run_id": "batch-run-1",
            "status": "draft",
            "selected_rule_count": 3,
            "batch_size": 2,
            "batches": [{"batch_index": 1, "rule_ids": ["rule-1", "rule-2"], "status": "pending"}],
        }

    async def start_batch(self, batch_run_id: str, *, batch_index: int, actor: str):
        self.started += 1
        assert batch_run_id == "batch-run-1"
        assert batch_index == 1
        assert actor == "operator"
        return {
            "batch_run_id": "batch-run-1",
            "status": "running",
            "batches": [{"batch_index": 1, "rule_ids": ["rule-1", "rule-2"], "status": "running", "job_id": "job-1"}],
        }

    async def refresh_batch_status(self, batch_run_id: str):
        assert batch_run_id == "batch-run-1"
        return await self.get_batch_run(batch_run_id)

    async def merge_batch_results(self, batch_run_id: str):
        self.merged += 1
        assert batch_run_id == "batch-run-1"
        return {
            "batch_run_id": "batch-run-1",
            "status": "merged",
            "merged_result_id": "merged-batch-run-1",
            "merged_result": {"summary": {"total_trades": 3}, "rule_results": []},
        }


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
async def test_operator_can_create_start_and_merge_rule_pool_batch_run() -> None:
    fake_service = _FakeRulePoolBacktestBatchService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_rule_pool_backtest_batch_service] = lambda: fake_service
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="operator",
            api_key_label="operator",
            authenticated=True,
            source="api_key",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            created = await ac.post(
                "/api/ui/v1/rules/backtests/batch-runs",
                json={
                    "rule_ids": ["rule-1", "rule-2", "rule-3"],
                    "batch_size": 2,
                    "start_date": "2026-01-01",
                    "end_date": "2026-06-30",
                    "min_confidence": 0.7,
                    "market_regime_version": "market-regime-v3",
                    "profile_id": "default",
                },
            )
            loaded = await ac.get("/api/ui/v1/rules/backtests/batch-runs/batch-run-1")
            started = await ac.post("/api/ui/v1/rules/backtests/batch-runs/batch-run-1/batches/1/start")
            merged = await ac.post("/api/ui/v1/rules/backtests/batch-runs/batch-run-1/merge")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["selected_rule_count"] == 3
    assert loaded.status_code == 200
    assert started.status_code == 200
    assert started.json()["batches"][0]["job_id"] == "job-1"
    assert merged.status_code == 200
    assert merged.json()["status"] == "merged"
    assert fake_service.created == 1
    assert fake_service.started == 1
    assert fake_service.merged == 1


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
    assert executed.json()["per_rule_metrics"][0]["rule_version_id"] == "rv-1"
    assert executed.json()["provenance"]["run_id"] == "run-1"
    assert executed.json()["audit"]["source_surface"] == "/rules/backtests"
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


@pytest.mark.asyncio()
async def test_operator_can_generate_formal_applicability_profile_draft() -> None:
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
            response = await ac.post(
                "/api/ui/v1/rules/backtests/runs/run-1/applicability-profiles",
                json={"result_id": "result-1", "reason": "生成草稿"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["review_status"] == "draft"
    assert body["source_backtest_run_ids"] == ["run-1"]
    assert body["source_backtest_result_ids"] == ["result-1"]
    assert body["source_result_fingerprints"] == ["result-fp"]
    assert body["requested_level"] == "level_3"
    assert body["effective_level"] == "level_2"
    assert body["recommendation_status"] == "recommended"


@pytest.mark.asyncio()
async def test_viewer_cannot_generate_formal_applicability_profile_draft() -> None:
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
                "/api/ui/v1/rules/backtests/runs/run-1/applicability-profiles",
                json={"result_id": "result-1", "reason": "生成草稿"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio()
async def test_operator_can_review_formal_applicability_profile() -> None:
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
            response = await ac.post(
                "/api/ui/v1/rules/backtests/applicability-profiles/profile-1/review",
                json={"review_status": "approved", "reason": "证据充分"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["review_status"] == "approved"


@pytest.mark.asyncio()
async def test_operator_can_publish_formal_applicability_profile() -> None:
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
            response = await ac.post(
                "/api/ui/v1/rules/backtests/applicability-profiles/profile-1/publish",
                json={"reason": "发布到策略验证"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["review_status"] == "published"


@pytest.mark.asyncio()
async def test_viewer_cannot_publish_formal_applicability_profile() -> None:
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
                "/api/ui/v1/rules/backtests/applicability-profiles/profile-1/publish",
                json={"reason": "发布到策略验证"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
