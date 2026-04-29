"""CLI snapshot 命令测试（S7-006）。"""
from typer.testing import CliRunner
import pytest

from cli.snapshot import app


@pytest.fixture
def runner():
    return CliRunner()


def test_snapshot_build_help(runner):
    result = runner.invoke(app, ["build", "--help"])
    assert result.exit_code == 0
    assert "--date" in result.stdout
    assert "--type" in result.stdout
    assert "--force" in result.stdout


def test_snapshot_build_date_required(runner):
    """缺少 --date 时报错"""
    result = runner.invoke(app, ["build"])
    assert result.exit_code != 0
