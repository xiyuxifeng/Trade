"""CLI snapshot 命令测试（S7-006）。"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from typer.testing import CliRunner
import pytest

from cli.snapshot import app


@pytest.fixture
def runner():
    return CliRunner()


def test_snapshot_build_help(runner):
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--date" in result.stdout
    assert "--start-date" in result.stdout
    assert "--end-date" in result.stdout
    assert "--type" in result.stdout
    assert "--force" in result.stdout


def test_snapshot_build_date_required(runner):
    """缺少 --date 时报错"""
    result = runner.invoke(app, [])
    assert result.exit_code != 0


def test_snapshot_build_date_range_invokes_each_day(monkeypatch, runner):
    """--start-date/--end-date 应展开为包含首尾的日期序列。"""
    calls: list[dict[str, str]] = []

    async def _handler(details, config):
        calls.append(details)

    monkeypatch.setattr("src.common.config.load_app_config", lambda path: SimpleNamespace(config=SimpleNamespace()))
    monkeypatch.setattr("config.database.run_async_with_cleanup", lambda coro: asyncio.run(coro))
    monkeypatch.setattr("src.pipeline.tasks.snapshot_tasks.handle_hot_topics_snapshot", _handler)
    monkeypatch.setattr("src.pipeline.tasks.snapshot_tasks.handle_topic_constituents_snapshot", _handler)
    monkeypatch.setattr("src.pipeline.tasks.snapshot_tasks.handle_strong_symbols_snapshot", _handler)

    result = runner.invoke(
        app,
        [
            "--start-date",
            "2026-04-29",
            "--end-date",
            "2026-05-01",
            "--type",
            "hot_topics",
        ],
    )

    assert result.exit_code == 0
    assert [item["trade_date"] for item in calls] == ["2026-04-29", "2026-04-30", "2026-05-01"]
    assert all(item["slot"] == "17-30" for item in calls)


def test_snapshot_build_date_range_requires_both_bounds(runner):
    """范围模式必须同时提供起止日期。"""
    result = runner.invoke(app, ["--start-date", "2026-04-29"])
    assert result.exit_code != 0
    assert "--start-date 和 --end-date" in result.stdout


def test_snapshot_build_date_range_rejects_inverted_bounds(runner):
    """开始日期晚于结束日期时应直接失败。"""
    result = runner.invoke(
        app,
        [
            "--start-date",
            "2026-05-02",
            "--end-date",
            "2026-05-01",
        ],
    )
    assert result.exit_code != 0
    assert "开始日期不能晚于结束日期" in result.stdout
