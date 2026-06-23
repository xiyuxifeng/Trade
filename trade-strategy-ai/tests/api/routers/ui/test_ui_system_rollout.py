from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.system import get_system_rollout_service


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(status=status, message=message, payload=payload)


@dataclass
class _FakeSystemRolloutService:
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def get_summary(self, *, actor_role: str) -> Any:
        self.calls.append({"actor_role": actor_role})
        return _result(
            {
                "generated_at": "2026-06-23T10:00:00Z",
                "supported_rollout_states": [
                    {"state": "legacy_new_comparison", "label": "新旧链路对照", "description": "对照"},
                    {"state": "new_read_only", "label": "新链路只读展示", "description": "只读"},
                    {"state": "limited_enablement", "label": "小范围启用", "description": "受控"},
                    {"state": "new_default", "label": "新链路成为默认", "description": "默认"},
                    {"state": "legacy_read_only", "label": "旧入口只读", "description": "只读旧入口"},
                    {"state": "retired", "label": "最终退役", "description": "退役"},
                ],
                "items": [
                    {
                        "migration_id": "stage2_canonical_database",
                        "label": "正式数据库迁移",
                        "domain": "database",
                        "current_state": "new_default",
                        "state_label": "新链路成为默认",
                        "formal_source": "Stage 2 canonical 数据库结构",
                        "legacy_mode": "compatibility_only",
                        "duplicate_formal_source_detected": False,
                        "happened": "正式数据库已切到 canonical 结构。",
                        "affected": "可核对计数和恢复证据。",
                        "repair_guidance": "补齐 migration report。",
                        "comparison": {
                            "status": "ready",
                            "pre_counts": {"raw_articles": 2},
                            "post_counts": {"raw_articles": 2},
                            "rejected_rows": 0,
                            "conflicted_rows": 1,
                        },
                        "rollback_or_recovery": {
                            "status": "ready",
                            "mode": "recovery",
                            "evidence_file_names": ["apply_report.json", "recovery_export.json"],
                            "no_silent_data_loss": True,
                        },
                    }
                ],
            }
        )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    fake_service = _FakeSystemRolloutService()
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
        app.dependency_overrides[get_system_rollout_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.fake_service = fake_service  # type: ignore[attr-defined]
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_system_rollout_endpoint_returns_rollout_and_recovery_summary(client: AsyncClient) -> None:
    response = await client.get("/api/ui/v1/system/rollout")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["supported_rollout_states"]) == 6
    assert payload["items"][0]["current_state"] == "new_default"
    assert payload["items"][0]["comparison"]["rejected_rows"] == 0
    assert payload["items"][0]["rollback_or_recovery"]["no_silent_data_loss"] is True
    assert client.fake_service.calls[0] == {"actor_role": "admin"}  # type: ignore[attr-defined]
