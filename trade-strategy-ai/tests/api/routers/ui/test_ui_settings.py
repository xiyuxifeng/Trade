"""Settings UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.settings import get_config_edit_service


@dataclass
class _FakeConfigEditService:
    """用于 settings 路由测试的替身。"""

    calls: list[dict[str, Any]]

    def __init__(self) -> None:
        self.calls = []

    def get_current_config(self, config_path: str | Path) -> Any:
        self.calls.append({"method": "get_current_config", "config_path": str(config_path)})
        return _result({"config_path": str(config_path), "config": {"api": {"timeout_seconds": 300}}})

    def get_edit_schema(self, config_path: str | Path) -> Any:
        self.calls.append({"method": "get_edit_schema", "config_path": str(config_path)})
        return _result({"config_path": str(config_path), "sections": [{"key": "api"}]})

    def validate_draft(self, config_path: str | Path, draft: dict[str, Any]) -> Any:
        self.calls.append({"method": "validate_draft", "config_path": str(config_path), "draft": draft})
        return _result({"config_path": str(config_path), "diff": {"api": {"timeout_seconds": {"before": 300, "after": 5}}}})

    def save_config(self, config_path: str | Path, draft: dict[str, Any], *, confirmed: bool = False) -> Any:
        self.calls.append({"method": "save_config", "config_path": str(config_path), "draft": draft, "confirmed": confirmed})
        if not confirmed:
            return _result({"confirmed": confirmed}, status="error", message="confirmation required")
        return _result(
            {
                "config_path": str(config_path),
                "backup_path": "/tmp/backups/app.yaml",
                "reload_required": True,
                "reload_targets": ["api", "worker"],
                "restart_required": False,
                "restart_targets": [],
                "reload_message": "app.yaml 已写入，API 和 Worker 需要重新加载配置。",
            }
        )

    def list_backups(self, config_path: str | Path) -> Any:
        self.calls.append({"method": "list_backups", "config_path": str(config_path)})
        return _result({"count": 1, "items": [{"path": "/tmp/backups/app.yaml"}]})

    def restore_backup(self, config_path: str | Path, backup_path: str | Path, *, confirmed: bool = False) -> Any:
        self.calls.append(
            {
                "method": "restore_backup",
                "config_path": str(config_path),
                "backup_path": str(backup_path),
                "confirmed": confirmed,
            }
        )
        if not confirmed:
            return _result({"confirmed": confirmed}, status="error", message="confirmation required")
        return _result(
            {
                "config_path": str(config_path),
                "backup_path": str(backup_path),
                "current_backup_path": "/tmp/backups/current.yaml",
                "reload_required": True,
                "reload_targets": ["api", "worker"],
                "restart_required": False,
                "restart_targets": [],
                "reload_message": "app.yaml 已写入，API 和 Worker 需要重新加载配置。",
            }
        )


class _LockedConfigEditService(_FakeConfigEditService):
    """返回编辑锁冲突的 settings 服务替身。"""

    def save_config(self, config_path: str | Path, draft: dict[str, Any], *, confirmed: bool = False) -> Any:
        self.calls.append({"method": "save_config", "config_path": str(config_path), "draft": draft, "confirmed": confirmed})
        return _result({"config_path": str(config_path), "lock_path": "/tmp/backups/app/.edit.lock"}, status="error", message="config edit locked")


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    """构造测试用 ServiceResult 替身。"""
    return SimpleNamespace(status=status, message=message, payload=payload)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建带认证覆盖的测试客户端。"""
    fake_service = _FakeConfigEditService()
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
        app.dependency_overrides[get_config_edit_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_settings_api_supports_read_validate_save_backup_restore(client: AsyncClient) -> None:
    """Settings UI API 应支持读取、校验、保存、列出备份和恢复。"""
    current = await client.get("/api/ui/v1/settings/config")
    schema = await client.get("/api/ui/v1/settings/schema")
    validation = await client.post("/api/ui/v1/settings/validate", json={"config_path": "config/app.yaml", "draft": {"api": {"timeout_seconds": 5}}})
    save_rejected = await client.post("/api/ui/v1/settings/save", json={"config_path": "config/app.yaml", "draft": {"api": {"timeout_seconds": 5}}})
    save_ok = await client.post(
        "/api/ui/v1/settings/save",
        json={"config_path": "config/app.yaml", "draft": {"api": {"timeout_seconds": 5}}, "confirmed": True},
    )
    backups = await client.get("/api/ui/v1/settings/backups")
    restore_rejected = await client.post(
        "/api/ui/v1/settings/restore",
        json={"config_path": "config/app.yaml", "backup_path": "data/backups/app/app.20260510-080000.yaml"},
    )
    restore_ok = await client.post(
        "/api/ui/v1/settings/restore",
        json={"config_path": "config/app.yaml", "backup_path": "data/backups/app/app.20260510-080000.yaml", "confirmed": True},
    )

    assert current.status_code == 200
    assert schema.status_code == 200
    assert validation.status_code == 200
    assert save_rejected.status_code == 400
    assert save_ok.status_code == 200
    assert save_ok.json()["reload_required"] is True
    assert backups.status_code == 200
    assert restore_rejected.status_code == 400
    assert restore_ok.status_code == 200
    assert restore_ok.json()["reload_required"] is True


@pytest.mark.asyncio
async def test_settings_api_rejects_config_paths_outside_project_root(client: AsyncClient) -> None:
    """settings 路由不应接受项目根目录之外的配置路径。"""
    response = await client.get("/api/ui/v1/settings/config", params={"config_path": "/tmp/escape.yaml"})
    assert response.status_code == 400
    assert response.json()["detail"] == "config path must stay within project root"


@pytest.mark.asyncio
async def test_settings_api_rejects_backup_paths_outside_backup_root(client: AsyncClient) -> None:
    """settings 恢复接口不应接受备份目录之外的路径。"""
    response = await client.post(
        "/api/ui/v1/settings/restore",
        json={"config_path": "config/app.yaml", "backup_path": "/tmp/backups/app.yaml", "confirmed": True},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "backup path must stay within backup root"


@pytest.mark.asyncio
async def test_operator_cannot_save_settings(client: AsyncClient) -> None:
    """operator 不能保存或恢复配置。"""
    previous = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="operator",
        api_key_label="Operator",
        authenticated=True,
        source="api_key",
        api_key="operator-key",
    )
    try:
        response = await client.post(
            "/api/ui/v1/settings/save",
            json={"config_path": "config/app.yaml", "draft": {"api": {"timeout_seconds": 5}}, "confirmed": True},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "insufficient permissions"
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous


@pytest.mark.asyncio
async def test_save_conflict_returns_409_when_lock_is_held(client: AsyncClient) -> None:
    """配置编辑锁已被占用时应返回 409。"""
    app.dependency_overrides[get_config_edit_service] = lambda: _LockedConfigEditService()
    try:
        response = await client.post(
            "/api/ui/v1/settings/save",
            json={"config_path": "config/app.yaml", "draft": {"api": {"timeout_seconds": 5}}, "confirmed": True},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "config edit locked"
    finally:
        app.dependency_overrides[get_config_edit_service] = lambda: _FakeConfigEditService()
