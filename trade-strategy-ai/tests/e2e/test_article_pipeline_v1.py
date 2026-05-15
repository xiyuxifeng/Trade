from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.e2e.e2e_runner import run_cli_e2e_regression, run_web_acceptance_suite


def run_article_pipeline_v1(config: Path) -> None:
    """串起 V1 的回归命令和 Web 验收，作为内部验证入口。"""
    run_cli_e2e_regression(config=config, max_articles=1, extract_limit=1)
    run_web_acceptance_suite()


def test_article_pipeline_v1_runs_cli_gate_and_web_acceptance(monkeypatch):
    calls = []

    def fake_cli(*, config, max_articles, extract_limit):
        calls.append(("cli", config, max_articles, extract_limit))

    def fake_web():
        calls.append(("web",))

    monkeypatch.setattr("tests.e2e.test_article_pipeline_v1.run_cli_e2e_regression", fake_cli)
    monkeypatch.setattr("tests.e2e.test_article_pipeline_v1.run_web_acceptance_suite", fake_web)

    run_article_pipeline_v1(Path("config/app.yaml"))

    assert calls == [
        ("cli", Path("config/app.yaml"), 1, 1),
        ("web",),
    ]


@pytest.mark.skipif(os.environ.get("RUN_V1_E2E") != "1", reason="需要显式启用真实 CLI 回归环境")
def test_article_pipeline_v1() -> None:
    run_article_pipeline_v1(Path("config/app.yaml"))
