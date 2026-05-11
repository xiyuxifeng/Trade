from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path("/Users/wanghui/Documents/Claude/trade-strategy-ai")


def test_build_runs_pnpm_in_web_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts import web_local

    calls: list[tuple[tuple[str, ...], Path | None]] = []

    def fake_run(cmd, cwd=None, check=None, env=None):  # type: ignore[no-untyped-def]
        calls.append((tuple(cmd), Path(cwd) if cwd else None))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(web_local.subprocess, "run", fake_run)
    monkeypatch.setattr(web_local, "PROJECT_ROOT", REPO_ROOT)

    web_local.build()

    assert calls == [(
        ("corepack", "pnpm", "build"),
        REPO_ROOT / "web",
    )]


def test_migrate_runs_cli_command_in_repo_root(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts import web_local

    calls: list[tuple[tuple[str, ...], Path | None]] = []

    def fake_run(cmd, cwd=None, check=None, env=None):  # type: ignore[no-untyped-def]
        calls.append((tuple(cmd), Path(cwd) if cwd else None))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(web_local.subprocess, "run", fake_run)
    monkeypatch.setattr(web_local.sys, "executable", "python")
    monkeypatch.setattr(web_local, "PROJECT_ROOT", REPO_ROOT)

    web_local.migrate()

    assert calls == [(
        ("python", "-m", "cli.main", "db-migrate", "--config", "config/app.yaml"),
        REPO_ROOT,
    )]


def test_start_supervises_api_and_worker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from scripts import web_local

    spawned: list[tuple[tuple[str, ...], Path | None]] = []

    class FakeProcess:
        def __init__(self, cmd: list[str], cwd: Path | None) -> None:
            self.cmd = tuple(cmd)
            self.cwd = cwd
            self._polls = 0
            self.returncode: int | None = None

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
        spawned.append((tuple(cmd), Path(cwd) if cwd else None))
        return FakeProcess(cmd, Path(cwd) if cwd else None)

    def fake_sleep(_: float) -> None:
        return None

    dist = tmp_path / "web" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html><body>web</body></html>", encoding="utf-8")

    monkeypatch.setattr(web_local.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(web_local.time, "sleep", fake_sleep)
    monkeypatch.setattr(web_local, "PROJECT_ROOT", REPO_ROOT)
    monkeypatch.setattr(web_local, "DEFAULT_WEB_DIST", dist)
    monkeypatch.setattr(web_local, "_require_web_dist", lambda *_: None)
    monkeypatch.setattr(web_local.sys, "executable", "python")

    with pytest.raises(SystemExit) as excinfo:
        web_local.start()

    assert excinfo.value.code == 1

    assert spawned == [
        (
            ("uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"),
            REPO_ROOT,
        ),
        (
            ("python", "-m", "cli.main", "job-worker-start", "--config", "config/app.yaml"),
            REPO_ROOT,
        ),
    ]
