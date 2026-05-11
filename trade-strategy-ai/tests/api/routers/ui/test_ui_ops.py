"""Ops UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.ops import get_ops_recovery_service


@dataclass
class _FakeOpsRecoveryService:
    """用于 ops 路由测试的替身。"""

    calls: list[dict[str, Any]]

    def __init__(self) -> None:
        self.calls = []

    def list_backups(self) -> Any:
        self.calls.append({"method": "list_backups"})
        return _result(
            {
                "base_dir": "/project",
                "count": 1,
                "items": [
                    {
                        "path": "/project/data/backups/20260511-080000",
                        "name": "20260511-080000",
                        "size_bytes": 4096,
                        "modified_at": "2026-05-11T08:00:00Z",
                        "tables": ["jobs", "artifacts"],
                        "row_counts": {"jobs": 1, "artifacts": 2},
                        "include_processed": True,
                        "processed_copied": True,
                    }
                ],
            }
        )

    async def create_backup(self, *, include_processed: bool = True, backup_dir: str | None = None) -> Any:
        self.calls.append({"method": "create_backup", "include_processed": include_processed, "backup_dir": backup_dir})
        return _result(
            {
                "backup_dir": "/project/data/backups/20260511-120000",
                "tables": ["jobs", "artifacts"],
                "row_counts": {"jobs": 1, "artifacts": 2},
                "include_processed": include_processed,
                "processed_copied": include_processed,
            }
        )

    async def restore_backup(
        self,
        *,
        backup_path: str,
        include_processed: bool = True,
        confirmed: bool = False,
    ) -> Any:
        self.calls.append(
            {
                "method": "restore_backup",
                "backup_path": backup_path,
                "include_processed": include_processed,
                "confirmed": confirmed,
            }
        )
        if not confirmed:
            return _result({"confirmed": confirmed}, status="error", message="confirmation required")
        return _result(
            {
                "backup_dir": backup_path,
                "tables": ["jobs", "artifacts"],
                "row_counts": {"jobs": 1, "artifacts": 2},
                "include_processed": include_processed,
                "processed_restored": include_processed,
            }
        )


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    """构造测试用 ServiceResult 替身。"""
    return SimpleNamespace(status=status, message=message, payload=payload)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建带认证覆盖的测试客户端。"""
    fake_service = _FakeOpsRecoveryService()
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
        app.dependency_overrides[get_ops_recovery_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ops_api_supports_list_backup_create_and_restore(client: AsyncClient) -> None:
    """Ops UI API 应支持列出备份、创建备份和恢复备份。"""
    listed = await client.get("/api/ui/v1/ops/backups")
    created = await client.post("/api/ui/v1/ops/backup", json={"include_processed": True})
    restore_rejected = await client.post(
        "/api/ui/v1/ops/restore",
        json={"backup_path": "/project/data/backups/20260511-080000", "include_processed": True},
    )
    restored = await client.post(
        "/api/ui/v1/ops/restore",
        json={
            "backup_path": "/project/data/backups/20260511-080000",
            "include_processed": True,
            "confirmed": True,
        },
    )

    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert created.status_code == 200
    assert created.json()["processed_copied"] is True
    assert restore_rejected.status_code == 400
    assert restored.status_code == 200
    assert restored.json()["processed_restored"] is True


@pytest.mark.asyncio
async def test_operator_cannot_access_ops_recovery(client: AsyncClient) -> None:
    """operator 不应执行项目级恢复操作。"""
    previous = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="operator",
        api_key_label="Operator",
        authenticated=True,
        source="api_key",
        api_key="operator-key",
    )
    try:
        response = await client.post("/api/ui/v1/ops/backup", json={"include_processed": True})
        assert response.status_code == 403
        assert response.json()["detail"] == "insufficient permissions"
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous
