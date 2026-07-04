from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.system import get_system_run_trace_service


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(status=status, message=message, payload=payload)


@dataclass
class _FakeSystemRunTraceService:
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def list_run_traces(
        self,
        *,
        actor_role: str,
        limit: int = 20,
        cursor: str | None = None,
        status_filter: str = "all",
        business_type_filter: str = "all",
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> Any:
        self.calls.append(
            {
                "actor_role": actor_role,
                "limit": limit,
                "cursor": cursor,
                "status_filter": status_filter,
                "business_type_filter": business_type_filter,
                "date_from": date_from,
                "date_to": date_to,
            }
        )
        return _result(
            {
                "summary": {
                    "overall_status": "needs_attention",
                    "headline": "有 1 项运行仍需处理。",
                    "counts": {"total": 1, "needs_attention": 1, "ready": 0},
                    "next_action": {"label": "查看今日计划", "target_path": "/daily/pre-market"},
                },
                "needs_attention": [
                    {
                        "run_id": "daily-plan:2026-06-22",
                        "business_label": "生成今日交易计划",
                        "business_type": "trading-plan",
                        "status": "partial",
                        "started_at": "2026-06-22T08:55:00+00:00",
                        "finished_at": "2026-06-22T08:58:00+00:00",
                        "duration_seconds": 180,
                        "happened": "今日交易计划已生成，但仍有部分输入处于降级状态。",
                        "reason": "盘前输入仍有降级项。",
                        "affected": "普通用户可以查看今日计划，但需要关注降级输入对执行范围的影响。",
                        "impact": "限制部分执行范围。",
                        "blocks_user": False,
                        "repair_guidance": "先补齐缺失的盘前输入，或在降级范围内继续查看本次结果。",
                        "next_action": {"label": "查看今日计划", "target_path": "/daily/pre-market"},
                        "safe_next_action": {"label": "查看今日计划", "target_path": "/daily/pre-market"},
                        "attempt": {"attempt_id": "attempt-1", "retry_count": 0},
                        "steps": [
                            {
                                "step_id": "generate-plan",
                                "business_label": "生成今日交易计划",
                                "status": "partial",
                                "started_at": "2026-06-22T08:55:00+00:00",
                                "finished_at": "2026-06-22T08:58:00+00:00",
                                "duration_seconds": 180,
                                "error": None,
                                "retry_count": 0,
                                "input_references": [{"type": "strategy_version", "id": "strategy-v3", "label": "正式策略 v3"}],
                                "output_references": [{"type": "trading_day_plan", "id": "plan-1", "label": "今日交易计划"}],
                                "repair_guidance": "先补齐降级输入，再重新生成。",
                            }
                        ],
                        "prompt_calls": [],
                        "data_fetches": [
                            {
                                "source": "dataset_snapshot",
                                "provider": "wind",
                                "date_range": {"date_from": "2026-06-01", "date_to": "2026-06-22"},
                                "trade_date": "2026-06-22",
                                "slot": "pre_market",
                                "coverage": {"symbols": 120},
                                "captured_at": "2026-06-22T08:30:00+00:00",
                                "available_at": "2026-06-22T08:35:00+00:00",
                                "effective_at": "2026-06-22T08:35:00+00:00",
                                "quality_status": "ready",
                                "missing_ranges": [],
                                "repair_guidance": "如缺失，请补齐今日盘前数据。",
                            }
                        ],
                        "backtests": [
                            {
                                "dataset_snapshot_id": "dataset-1",
                                "data_fingerprints": {"dataset": "dataset-fp", "market_snapshots": ["market-fp"]},
                                "rule_version": {
                                    "rule_version_id": "rule-version-1",
                                    "rule_version_no": 3,
                                    "rule_version_fingerprint": "rule-fp",
                                },
                                "market_state_model_version": "market-state-v2",
                                "code_version": "engine-v5",
                                "decision_time_policy": "t+0-close",
                                "reproducibility_fingerprint": "repro-fp",
                                "coverage": {"coverage_state": "ready"},
                                "limitations": ["coverage-limited"],
                            }
                        ],
                        "linked_records": [],
                        "admin_diagnostics": {
                            "technical_status": "partial",
                            "linked_ids": {"job_ids": ["job-1"], "workflow_run_ids": ["workflow-1"]},
                        } if actor_role in {"operator", "admin"} else None,
                    }
                ],
                "history": {
                    "groups": [
                        {
                            "group_key": "2026-06-22",
                            "label": "2026-06-22",
                            "items": [
                                {
                                    "run_id": "daily-plan:2026-06-22",
                                    "business_label": "生成今日交易计划",
                                    "business_type": "trading-plan",
                                    "status": "partial",
                                    "started_at": "2026-06-22T08:55:00+00:00",
                                    "finished_at": "2026-06-22T08:58:00+00:00",
                                    "duration_seconds": 180,
                                    "happened": "今日交易计划已生成，但仍有部分输入处于降级状态。",
                                    "reason": "盘前输入仍有降级项。",
                                    "affected": "普通用户可以查看今日计划，但需要关注降级输入对执行范围的影响。",
                                    "impact": "限制部分执行范围。",
                                    "blocks_user": False,
                                    "repair_guidance": "先补齐缺失的盘前输入，或在降级范围内继续查看本次结果。",
                                    "next_action": {"label": "查看今日计划", "target_path": "/daily/pre-market"},
                                    "safe_next_action": {"label": "查看今日计划", "target_path": "/daily/pre-market"},
                                    "attempt": {"attempt_id": "attempt-1", "retry_count": 0},
                                    "steps": [],
                                    "prompt_calls": [],
                                    "data_fetches": [],
                                    "backtests": [],
                                    "linked_records": [],
                                    "admin_diagnostics": {
                                        "technical_status": "partial",
                                        "linked_ids": {"job_ids": ["job-1"], "workflow_run_ids": ["workflow-1"]},
                                    } if actor_role in {"operator", "admin"} else None,
                                }
                            ],
                        }
                    ],
                    "page": {"limit": 5, "has_more": False, "next_cursor": None, "total_filtered": 1},
                },
                "filters": {
                    "applied": {
                        "status": status_filter,
                        "business_type": business_type_filter,
                        "date_from": date_from,
                        "date_to": date_to,
                    }
                },
            }
        )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    fake_service = _FakeSystemRunTraceService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="admin",
            api_key_label="Admin",
            authenticated=True,
            source="api_key",
            api_key="admin-key",
        )
        app.dependency_overrides[get_system_run_trace_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.fake_service = fake_service  # type: ignore[attr-defined]
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_system_runs_endpoint_returns_run_trace_summary(client: AsyncClient) -> None:
    response = await client.get(
        "/api/ui/v1/system/runs",
        params={
            "limit": 5,
            "cursor": "cursor-1",
            "status": "partial",
            "business_type": "trading-plan",
            "date_from": "2026-06-22",
            "date_to": "2026-06-23",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["overall_status"] == "needs_attention"
    assert payload["needs_attention"][0]["run_id"] == "daily-plan:2026-06-22"
    assert payload["needs_attention"][0]["steps"][0]["step_id"] == "generate-plan"
    assert payload["history"]["groups"][0]["items"][0]["admin_diagnostics"]["linked_ids"]["job_ids"] == ["job-1"]
    assert client.fake_service.calls[0] == {  # type: ignore[attr-defined]
        "actor_role": "admin",
        "limit": 5,
        "cursor": "cursor-1",
        "status_filter": "partial",
        "business_type_filter": "trading-plan",
        "date_from": "2026-06-22",
        "date_to": "2026-06-23",
    }


@pytest.mark.asyncio
async def test_system_runs_endpoint_hides_admin_diagnostics_from_viewer(client: AsyncClient) -> None:
    previous = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="viewer",
        api_key_label="Viewer",
        authenticated=True,
        source="api_key",
        api_key="viewer-key",
    )
    try:
        response = await client.get("/api/ui/v1/system/runs")
        assert response.status_code == 200
        payload = response.json()
        assert payload["needs_attention"][0]["admin_diagnostics"] is None
        assert payload["history"]["groups"][0]["items"][0]["admin_diagnostics"] is None
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous
