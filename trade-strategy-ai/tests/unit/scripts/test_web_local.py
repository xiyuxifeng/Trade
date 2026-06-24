from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path("/Users/wanghui/Documents/Claude/trade-strategy-ai")


def test_build_runs_pnpm_in_web_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from scripts import web_local

    calls: list[tuple[tuple[str, ...], Path | None, dict[str, str] | None]] = []
    project_root = tmp_path / "trade-strategy-ai"
    project_root.mkdir()
    (project_root / ".env").write_text("TGB_COOKIE=from-dotenv\n", encoding="utf-8")

    def fake_run(cmd, cwd=None, check=None, env=None):  # type: ignore[no-untyped-def]
        calls.append((tuple(cmd), Path(cwd) if cwd else None, env))
        return SimpleNamespace(returncode=0)

    monkeypatch.setenv("TGB_COOKIE", "from-shell")
    monkeypatch.setattr(web_local.subprocess, "run", fake_run)
    monkeypatch.setattr(web_local, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(web_local, "_node18_bin_dir", lambda: project_root / ".nvm" / "versions" / "node" / "v18.20.8" / "bin")

    web_local.build()
    output = capsys.readouterr().out

    assert calls[0][0] == ("corepack", "pnpm", "build")
    assert calls[0][1] == project_root / "web"
    assert calls[0][2]["TGB_COOKIE"] == "from-shell"
    assert calls[0][2]["PATH"].startswith(str(project_root / ".nvm" / "versions" / "node" / "v18.20.8" / "bin"))
    assert "本机脚本已读取到以下关键配置（已设置 " in output
    assert "/10 项）" in output
    assert "TGB_COOKIE: 已设置(已脱敏)" in output
    assert "LOG_LEVEL" not in output
    assert "REDIS_URL" not in output


def test_migrate_runs_cli_command_in_repo_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from scripts import web_local

    calls: list[tuple[tuple[str, ...], Path | None, dict[str, str] | None]] = []
    project_root = tmp_path / "trade-strategy-ai"
    project_root.mkdir()
    (project_root / ".env").write_text("DATABASE_URL=postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai\n", encoding="utf-8")

    def fake_run(cmd, cwd=None, check=None, env=None):  # type: ignore[no-untyped-def]
        calls.append((tuple(cmd), Path(cwd) if cwd else None, env))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(web_local.subprocess, "run", fake_run)
    monkeypatch.setattr(web_local.sys, "executable", "python")
    monkeypatch.setattr(web_local, "PROJECT_ROOT", project_root)

    web_local.migrate()
    output = capsys.readouterr().out

    assert calls[0][0] == ("python", "-m", "cli.main", "db-migrate", "--config", "config/app.template.yaml")
    assert calls[0][1] == project_root
    assert calls[0][2]["DATABASE_URL"] == "postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai"
    assert "本机脚本已读取到以下关键配置（已设置 " in output
    assert "/10 项）" in output
    assert "DATABASE_URL: 已设置(已脱敏)" in output
    assert "LLM_PROVIDER" not in output


def test_start_supervises_api_and_worker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from scripts import web_local

    spawned: list[tuple[tuple[str, ...], Path | None, dict[str, str] | None]] = []
    project_root = tmp_path / "trade-strategy-ai"
    project_root.mkdir()
    (project_root / ".env").write_text("TGB_COOKIE=from-dotenv\n", encoding="utf-8")

    class FakeProcess:
        def __init__(self, cmd: list[str], cwd: Path | None) -> None:
            self.cmd = tuple(cmd)
            self.cwd = cwd
            self._polls = 0
            self.returncode: int | None = None
            self.pid = 12345

        def poll(self) -> int | None:
            self._polls += 1
            if self._polls < 2:
                return None
            self.returncode = 0
            return self.returncode

        def terminate(self) -> None:
            self.returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            self.returncode = 0
            return 0

    def fake_popen(cmd, cwd=None, env=None):  # type: ignore[no-untyped-def]
        spawned.append((tuple(cmd), Path(cwd) if cwd else None, env))
        return FakeProcess(cmd, Path(cwd) if cwd else None)

    def fake_sleep(_: float) -> None:
        return None

    dist = tmp_path / "web" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html><body>web</body></html>", encoding="utf-8")

    monkeypatch.setattr(web_local.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(web_local.time, "sleep", fake_sleep)
    monkeypatch.setattr(web_local, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(web_local, "DEFAULT_WEB_DIST", dist)
    monkeypatch.setattr(web_local, "_require_web_dist", lambda *_: dist)
    monkeypatch.setattr(web_local.sys, "executable", "python")
    monkeypatch.setattr(web_local, "_node18_bin_dir", lambda: project_root / ".nvm" / "versions" / "node" / "v18.20.8" / "bin")

    with pytest.raises(SystemExit) as excinfo:
        web_local.start()
    output = capsys.readouterr().out

    assert excinfo.value.code == 1

    assert spawned[0][0] == ("uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000")
    assert spawned[0][1] == project_root
    assert spawned[1][0] == ("python", "-m", "cli.main", "job-worker-start", "--config", "config/app.template.yaml")
    assert spawned[1][1] == project_root
    assert spawned[0][2]["TGB_COOKIE"] == "from-dotenv"
    assert spawned[1][2]["TGB_COOKIE"] == "from-dotenv"
    assert output.count("本机脚本已读取到以下关键配置（已设置 ") == 1
    assert "/10 项）" in output
    assert "WEB_STATIC_DIR:" in output
    assert spawned[0][2]["PATH"].startswith(str(project_root / ".nvm" / "versions" / "node" / "v18.20.8" / "bin"))


def test_env_check_reads_dotenv_without_exposing_secret_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from scripts import web_local

    project_root = tmp_path / "trade-strategy-ai"
    project_root.mkdir()
    (project_root / ".env").write_text(
        "TGB_COOKIE=fake_cookie_a=1;fake_cookie_b=2\n"
        "DATABASE_URL=postgresql+asyncpg://example:example@example.invalid:5432/example\n"
        "KAIPAN_USER_ID=fake-user-id\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(web_local, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(web_local, "_node18_bin_dir", lambda: project_root / ".nvm" / "versions" / "node" / "v18.20.8" / "bin")

    web_local.env_check()
    output = capsys.readouterr().out

    assert "TGB_COOKIE: 已设置(已脱敏)" in output
    assert "fake_cookie_a=1;fake_cookie_b=2" not in output
    assert "KAIPAN_USER_ID: 已设置(已脱敏)" in output
    assert "fake-user-id" not in output
    assert "NODE18_BIN" in output
