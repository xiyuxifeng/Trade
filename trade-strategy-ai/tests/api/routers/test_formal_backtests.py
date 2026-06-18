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


class _FakeBacktestApplicationService:
    def __init__(self) -> None:
        self.create_calls = 0

    async def check_dependencies(self, selection, *, actor_id: str, actor_role: str):
        assert actor_role == "viewer"
        return _FakeDependencyResult(selection=selection.model_dump(mode="json"), coverage={"ohlcv": {"state": "ready"}})

    async def create_run(self, request):
        self.create_calls += 1
        assert request.actor_role == "operator"
        assert request.source_surface == "/rules/backtests"
        return _FakeRun()

    async def get_run(self, run_id: str, *, actor_id: str, actor_role: str):
        assert run_id == "run-1"
        return _FakeRun()


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
