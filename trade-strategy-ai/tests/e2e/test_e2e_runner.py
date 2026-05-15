from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

from tests.e2e.e2e_runner import run_cli_e2e_regression, run_web_acceptance_suite


def test_run_web_acceptance_suite_invokes_vitest(monkeypatch):
    calls = []

    def fake_run(cmd, cwd, env, capture_output, text, check):
        calls.append((cmd, cwd, env["CI"]))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("tests.e2e.e2e_runner.subprocess.run", fake_run)

    run_web_acceptance_suite()

    assert calls[0][0][-2:] == ["run", "src/e2e/web-acceptance.test.tsx"]
    assert calls[0][1].name == "web"
    assert calls[0][2] == "1"


def test_run_cli_e2e_regression_invokes_cli_with_expected_args(monkeypatch):
    calls = []

    def fake_run(cmd, cwd, env, capture_output, text, check):
        calls.append((cmd, cwd, env["PYTHONPATH"]))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("tests.e2e.e2e_runner.subprocess.run", fake_run)

    run_cli_e2e_regression(
        config=Path("config/app.yaml"),
        max_articles=1,
        extract_limit=1,
    )

    assert calls[0][0][0] == sys.executable
    assert calls[0][0][1:4] == ["-m", "cli.main", "e2e-regression"]
    assert calls[0][1] == Path(__file__).resolve().parents[2]
