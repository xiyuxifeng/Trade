"""CLI strategy 命令测试（S7-006）。"""
from typer.testing import CliRunner
import pytest

from cli.strategy import app


@pytest.fixture
def runner():
    return CliRunner()


def test_strategy_help_shows_commands(runner):
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "build" in result.stdout
    assert "list" in result.stdout


def test_strategy_build_help(runner):
    result = runner.invoke(app, ["build", "--help"])
    assert result.exit_code == 0
    assert "--trader" in result.stdout
    assert "--date" in result.stdout


def test_strategy_list_help(runner):
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0
    assert "--trader" in result.stdout
    assert "--status" in result.stdout


def test_strategy_build_requires_args(runner):
    """缺少必选参数时报错"""
    result = runner.invoke(app, ["build"])
    assert result.exit_code != 0


def test_strategy_list_pagination_params(runner):
    """list 命令有 limit 参数"""
    result = runner.invoke(app, ["list", "--help"])
    assert "--limit" in result.stdout
