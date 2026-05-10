from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import yaml


def test_config_edit_service_reads_schema_validates_and_masks(tmp_path: Path) -> None:
    """ConfigEditService 应返回脱敏配置、编辑 schema 和草稿 diff。"""
    from src.services.config_edit_service import ConfigEditService

    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
database:
  url: postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai
  echo: false
llm:
  api_key: secret-key
api:
  auth:
    enabled: true
    api_keys:
      - web-key
""",
        encoding="utf-8",
    )

    service = ConfigEditService(backup_root=tmp_path / "backups")
    current = service.get_current_config(config_path)
    schema = service.get_edit_schema(config_path)
    draft = {
        "database": {"echo": True},
        "llm": {"api_key": "new-secret"},
        "api": {"auth": {"api_keys": ["new-key"]}},
    }
    validation = service.validate_draft(config_path, draft)

    assert current.status == "ok"
    assert current.payload["config"]["llm"]["api_key"] == "***"
    assert schema.status == "ok"
    assert schema.payload["sections"][0]["key"] == "database"
    assert validation.status == "ok"
    assert validation.payload["diff"]["database"]["echo"]["after"] is True
    assert validation.payload["diff"]["llm"]["api_key"]["before"] == "***"


def test_save_creates_backup_and_restore_requires_confirmation(tmp_path: Path) -> None:
    """保存时应创建备份，恢复时应要求确认。"""
    from src.services.config_edit_service import ConfigEditService

    config_path = tmp_path / "app.yaml"
    config_path.write_text("api:\n  timeout_seconds: 1\n", encoding="utf-8")
    service = ConfigEditService(backup_root=tmp_path / "backups")

    saved = service.save_config(config_path, {"api": {"timeout_seconds": 5}}, confirmed=True)
    backups = service.list_backups(config_path)
    restore_rejected = service.restore_backup(config_path, backups.payload["items"][0]["path"], confirmed=False)
    restore_ok = service.restore_backup(config_path, backups.payload["items"][0]["path"], confirmed=True)

    assert saved.status == "ok"
    assert saved.payload["reload_required"] is True
    assert saved.payload["reload_targets"] == ["api", "worker"]
    assert backups.status == "ok"
    assert backups.payload["count"] >= 1
    assert restore_rejected.status == "error"
    assert restore_ok.status == "ok"
    assert restore_ok.payload["reload_required"] is True
    assert restore_ok.payload["current_backup_path"]


def test_save_preserves_masked_sensitive_values_and_clears_auth_cache(tmp_path: Path, monkeypatch) -> None:
    """未修改的敏感字段应保持原值，且保存后应刷新鉴权配置缓存。"""
    from src.services.config_edit_service import ConfigEditService

    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
database:
  url: postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai
  echo: false
llm:
  api_key: secret-key
api:
  auth:
    api_keys:
      - key: web-key-1
        role: viewer
        label: Viewer
""",
        encoding="utf-8",
    )

    cleared: list[bool] = []
    monkeypatch.setattr("api.dependencies.clear_cached_app_config", lambda: cleared.append(True))

    service = ConfigEditService(backup_root=tmp_path / "backups")
    result = service.save_config(
        config_path,
        {
            "database": {
                "url": "postgresql+asyncpg://trade:***@localhost:5432/trade_strategy_ai",
                "echo": True,
            },
            "llm": {"api_key": "***"},
            "api": {
                "auth": {
                    "api_keys": [
                        {
                            "key": "***",
                            "role": "viewer",
                            "label": "Viewer",
                        }
                    ],
                }
            },
        },
        confirmed=True,
    )

    saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert result.status == "ok"
    assert saved["database"]["url"] == "postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai"
    assert saved["database"]["echo"] is True
    assert saved["llm"]["api_key"] == "secret-key"
    assert saved["api"]["auth"]["api_keys"][0]["key"] == "web-key-1"
    assert cleared


def test_save_rolls_back_when_reload_validation_fails(tmp_path: Path) -> None:
    """保存后重新加载失败时应自动回滚原配置。"""
    from src.services.config_edit_service import ConfigEditService

    config_path = tmp_path / "app.yaml"
    original_content = "api:\n  timeout_seconds: 1\n"
    config_path.write_text(original_content, encoding="utf-8")

    def failing_loader(_: str | Path) -> SimpleNamespace:
        raise RuntimeError("reload failed")

    service = ConfigEditService(backup_root=tmp_path / "backups", config_loader=failing_loader)

    result = service.save_config(config_path, {"api": {"timeout_seconds": 5}}, confirmed=True)

    assert result.status == "error"
    assert result.message == "config reload failed"
    assert config_path.read_text(encoding="utf-8") == original_content


def test_save_rejects_when_lock_is_held(tmp_path: Path) -> None:
    """已有编辑锁时应拒绝新的保存事务。"""
    from src.services.config_edit_service import ConfigEditService

    config_path = tmp_path / "app.yaml"
    config_path.write_text("api:\n  timeout_seconds: 1\n", encoding="utf-8")
    service = ConfigEditService(backup_root=tmp_path / "backups")

    lock_path = service._lock_path(service._resolve_config_path(config_path))
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("busy", encoding="utf-8")

    result = service.save_config(config_path, {"api": {"timeout_seconds": 5}}, confirmed=True)

    assert result.status == "error"
    assert result.message == "config edit locked"


def test_restore_rolls_back_when_reload_validation_fails(tmp_path: Path) -> None:
    """恢复备份后重新加载失败时应回滚到原配置。"""
    from src.services.config_edit_service import ConfigEditService

    config_path = tmp_path / "app.yaml"
    config_path.write_text("api:\n  timeout_seconds: 1\n", encoding="utf-8")
    backup_dir = tmp_path / "backups" / "app"
    backup_dir.mkdir(parents=True, exist_ok=True)
    restore_source = backup_dir / "app.20260510-080000.yaml"
    restore_source.write_text("api:\n  timeout_seconds: 5\n", encoding="utf-8")

    def failing_loader(_: str | Path) -> SimpleNamespace:
        raise RuntimeError("reload failed")

    service = ConfigEditService(backup_root=tmp_path / "backups", config_loader=failing_loader)

    result = service.restore_backup(config_path, restore_source, confirmed=True)

    assert result.status == "error"
    assert result.message == "config reload failed"
    assert config_path.read_text(encoding="utf-8") == "api:\n  timeout_seconds: 1\n"
