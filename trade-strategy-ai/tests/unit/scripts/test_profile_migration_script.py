from __future__ import annotations

from pathlib import Path

from src.services.base import ServiceResult


class _FakeMigrationService:
    def preview_migration(self, config_path, *, profile_id=None, created_by="system", name=None, environment=None):
        del config_path, created_by
        resolved_profile_id = profile_id or "app"
        return ServiceResult(
            status="ok",
            message="migration preview ready",
            payload={
                "config_path": "/tmp/app.yaml",
                "profile_id": resolved_profile_id,
                "profile_name": name or resolved_profile_id,
                "environment": environment or "dev",
                "validation_status": "draft",
                "masked_preview": {"llm": {"api_key": "***"}},
                "missing_sections": ["database"],
                "compatibility": {
                    "legacy_entry": "config_path",
                    "canonical_target": "profile",
                    "retire_condition": "done",
                },
            },
        )

    async def migrate_config_path(self, config_path, *, profile_id=None, created_by="system", name=None, environment=None):
        del config_path, profile_id, created_by, name, environment
        return ServiceResult(
            status="ok",
            message="config migrated to profile",
            payload={
                "profile": {
                    "profile_id": "app",
                    "version": 1,
                },
                "snapshot": {
                    "snapshot_path": "/tmp/profile_snapshot.json",
                },
            },
        )


def test_profile_migration_script_supports_dry_run(tmp_path: Path, monkeypatch, capsys) -> None:
    """内部迁移脚本应支持预览模式。"""
    config_path = tmp_path / "app.yaml"
    config_path.write_text("timezone: Asia/Shanghai\n", encoding="utf-8")

    monkeypatch.setattr("scripts.profile_migration.ConfigMigrationService", _FakeMigrationService)

    from scripts.profile_migration import main

    code = main(["--config", str(config_path), "--profile-id", "profile-dev", "--dry-run"])
    output = capsys.readouterr().out

    assert code == 0
    assert "Profile 迁移预览" in output
    assert "missing_sections: database" in output
    assert "dry-run 完成" in output


def test_profile_migration_script_saves_profile(tmp_path: Path, monkeypatch, capsys) -> None:
    """内部迁移脚本在非 dry-run 模式下应执行保存。"""
    config_path = tmp_path / "app.yaml"
    config_path.write_text("timezone: Asia/Shanghai\n", encoding="utf-8")

    monkeypatch.setattr("scripts.profile_migration.ConfigMigrationService", _FakeMigrationService)

    from scripts.profile_migration import main

    code = main(["--config", str(config_path), "--profile-id", "profile-dev"])
    output = capsys.readouterr().out

    assert code == 0
    assert "迁移完成" in output
    assert "snapshot_path: /tmp/profile_snapshot.json" in output
