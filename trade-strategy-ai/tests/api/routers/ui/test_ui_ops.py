"""Ops UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator
from types import SimpleNamespace

import pytest
import pytest_asyncio
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
                        "backup_id": "20260511-080000",
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

    def list_backup_targets(self) -> Any:
        self.calls.append({"method": "list_backup_targets"})
        return _result(
            {
                "base_dir": "/project",
                "backup_root": "/project/data/backups",
                "count": 1,
                "items": [
                    {
                        "id": "default",
                        "label": "默认备份目录",
                        "description": "使用系统自动生成的时间戳目录",
                        "path": "/project/data/backups",
                        "mode": "auto",
                    }
                ],
            }
        )

    async def create_backup(
        self,
        *,
        profile_id: str,
        include_processed: bool = True,
        backup_dir: str | None = None,
        backup_dir_id: str | None = None,
    ) -> Any:
        self.calls.append(
            {
                "method": "create_backup",
                "profile_id": profile_id,
                "include_processed": include_processed,
                "backup_dir": backup_dir,
                "backup_dir_id": backup_dir_id,
            }
        )
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
        profile_id: str,
        backup_id: str | None = None,
        backup_path: str | None = None,
        include_processed: bool = True,
        confirmed: bool = False,
    ) -> Any:
        target = backup_path or f"/project/data/backups/{backup_id}"
        if not target.startswith("/project/data/backups/"):
            raise ValueError("backup path must stay within backup root")
        self.calls.append(
            {
                "method": "restore_backup",
                "profile_id": profile_id,
                "backup_id": backup_id,
                "backup_path": backup_path,
                "include_processed": include_processed,
                "confirmed": confirmed,
            }
        )
        if not confirmed:
            return _result({"confirmed": confirmed}, status="error", message="confirmation required")
        return _result(
            {
                "backup_dir": target,
                "tables": ["jobs", "artifacts"],
                "row_counts": {"jobs": 1, "artifacts": 2},
                "include_processed": include_processed,
                "processed_restored": include_processed,
            }
        )

    async def recover_stale_jobs(
        self,
        *,
        stale_before_minutes: int = 10,
        actor: str | None = None,
        audit_source: dict[str, Any] | None = None,
    ) -> Any:
        self.calls.append(
            {
                "method": "recover_stale_jobs",
                "stale_before_minutes": stale_before_minutes,
                "actor": actor,
                "audit_source": audit_source,
            }
        )
        return _result(
            {
                "count": 1,
                "job_ids": ["job-stale-1"],
                "stale_before": "2026-05-17T08:50:00Z",
                "stale_before_minutes": stale_before_minutes,
            }
        )


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    """构造测试用 ServiceResult 替身。"""
    return SimpleNamespace(status=status, message=message, payload=payload)


@pytest_asyncio.fixture
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
    targets = await client.get("/api/ui/v1/ops/backup-targets")
    created = await client.post("/api/ui/v1/ops/backup", json={"profile_id": "profile-1", "include_processed": True})
    restore_rejected = await client.post(
        "/api/ui/v1/ops/restore",
        json={"profile_id": "profile-1", "backup_id": "20260511-080000", "include_processed": True},
    )
    restored = await client.post(
        "/api/ui/v1/ops/restore",
        json={
            "profile_id": "profile-1",
            "backup_id": "20260511-080000",
            "include_processed": True,
            "confirmed": True,
        },
    )

    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert targets.status_code == 200
    assert targets.json()["count"] == 1
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


@pytest.mark.asyncio
async def test_ops_api_rejects_backup_paths_outside_root(client: AsyncClient) -> None:
    """Ops 恢复入口不应接受备份根目录之外的路径。"""
    response = await client.post(
        "/api/ui/v1/ops/restore",
        json={"profile_id": "profile-1", "backup_path": "/tmp/outside", "include_processed": True, "confirmed": True},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "backup path must stay within backup root"


@pytest.mark.asyncio
async def test_ops_api_supports_stale_job_recovery(client: AsyncClient) -> None:
    """Ops UI API 应支持 stale job 回收。"""
    response = await client.post("/api/ui/v1/ops/recover-stale", json={"stale_before_minutes": 12})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["stale_before_minutes"] == 12
