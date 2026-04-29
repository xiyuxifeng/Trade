# tests/unit/cli/test_ohlcv.py
import pytest
from typer.testing import CliRunner
from cli.ohlcv import app

runner = CliRunner()


def test_crawl_command_help():
    result = runner.invoke(app, ["crawl", "--help"])
    assert result.exit_code == 0
    assert "crawl" in result.output.lower()
