from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.system import get_system_cost_control_service


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(status=status, message=message, payload=payload)


@dataclass
class _FakeSystemCostControlService:
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def get_summary(self, *, actor_role: str) -> Any:
        self.calls.append({"actor_role": actor_role})
        return _result(
            {
                "generated_at": "2026-06-23T09:00:00Z",
                "llm_cost_summary": {
                    "currency": "USD",
                    "total_cost": 12.48,
                    "prompt_run_count": 3,
                    "total_tokens": 1200,
                },
                "budget_warning": {
                    "status": "warning",
                    "message": "最近 7 天的 LLM 成本已接近预算上限。",
                    "enforcement": "notify_only",
                    "affected_flows": ["文章结构化"],
                },
                "concurrency_limits": [
                    {"task_type": "stage3_article_batch", "label": "文章批处理", "limit": 2},
                ],
                "retry_caps": [
                    {"task_type": "stage3_article_batch", "label": "文章批处理", "max_retries": 1},
                ],
                "prompt_cache_samples": [
                    {
                        "prompt_name": "article_analysis_v1",
                        "prompt_version": "article_analysis_v1",
                        "schema_version": "article_analysis_v1",
                        "model": "gpt-5.4",
                        "input_hash": "hash-1",
                        "retry_count": 0,
                        "cache_status": "stale",
                        "invalidation_reasons": ["schema_version_changed"],
                        "content_hash_status": "ready",
                        "article_revision_id": "revision-2",
                        "content_hash": "content-hash-1",
                    }
                ],
                "backtest_reuse_samples": [
                    {
                        "run_id": "backtest-run-1",
                        "reuse_status": "reused",
                        "invalidation_reasons": [],
                        "metric_cache_status": "ready",
                        "calculation_version": "stage6-market-state-metric-v1",
                    }
                ],
                "incremental_profile_samples": [
                    {
                        "profile_kind": "method",
                        "author_id": "author-1",
                        "update_scope": "changed_article_revision_group",
                        "status": "draft_only",
                        "invalidation_reasons": [],
                    }
                ],
            }
        )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    fake_service = _FakeSystemCostControlService()
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
        app.dependency_overrides[get_system_cost_control_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.fake_service = fake_service  # type: ignore[attr-defined]
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_system_cost_control_endpoint_returns_admin_summary(client: AsyncClient) -> None:
    response = await client.get("/api/ui/v1/system/cost-control")

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_cost_summary"]["total_cost"] == 12.48
    assert payload["budget_warning"]["enforcement"] == "notify_only"
    assert payload["concurrency_limits"][0]["limit"] == 2
    assert payload["prompt_cache_samples"][0]["cache_status"] == "stale"
    assert payload["backtest_reuse_samples"][0]["reuse_status"] == "reused"
    assert payload["incremental_profile_samples"][0]["status"] == "draft_only"
    assert client.fake_service.calls[0] == {"actor_role": "admin"}  # type: ignore[attr-defined]
