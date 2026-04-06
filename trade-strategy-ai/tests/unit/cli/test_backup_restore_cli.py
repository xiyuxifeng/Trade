from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app


def test_backup_data_cli_invokes_service(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("timezone: Asia/Shanghai\n", encoding="utf-8")

    calls: dict[str, object] = {}

    async def _fake_backup_project_state(*, base_dir: Path, backup_dir: Path | None = None, engine=None, include_processed: bool = True):
        del engine
        calls["base_dir"] = base_dir
        calls["backup_dir"] = backup_dir
        calls["include_processed"] = include_processed
        return type("Result", (), {"backup_dir": backup_dir or tmp_path / "backup", "tables": ["blog_articles"], "processed_copied": True})()

    monkeypatch.setattr("cli.main.backup_project_state", _fake_backup_project_state)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "backup-data",
            "--config",
            str(config_path),
            "--dest",
            str(tmp_path / "backup"),
        ],
    )

    assert result.exit_code == 0
    assert calls["base_dir"] == tmp_path
    assert calls["backup_dir"] == tmp_path / "backup"
    assert calls["include_processed"] is True


def test_restore_data_cli_invokes_service(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("timezone: Asia/Shanghai\n", encoding="utf-8")

    calls: dict[str, object] = {}

    async def _fake_restore_project_state(*, base_dir: Path, backup_dir: Path, engine=None, include_processed: bool = True, force: bool = False):
        del engine
        calls["base_dir"] = base_dir
        calls["backup_dir"] = backup_dir
        calls["include_processed"] = include_processed
        calls["force"] = force
        return type("Result", (), {"backup_dir": backup_dir, "tables": ["blog_articles"], "processed_restored": True})()

    monkeypatch.setattr("cli.main.restore_project_state", _fake_restore_project_state)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "restore-data",
            "--config",
            str(config_path),
            "--source",
            str(tmp_path / "backup"),
            "--force",
        ],
    )

    assert result.exit_code == 0
    assert calls["base_dir"] == tmp_path
    assert calls["backup_dir"] == tmp_path / "backup"
    assert calls["include_processed"] is True
    assert calls["force"] is True
