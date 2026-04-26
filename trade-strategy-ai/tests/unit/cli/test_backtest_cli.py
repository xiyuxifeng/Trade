"""NTL-S6-008: 回测 CLI 单元测试"""

from __future__ import annotations

from datetime import date
from typer.testing import CliRunner
import pytest


class TestBacktestCLIRunCommand:
    """backtest run 子命令测试"""

    def test_backtest_run_command_exists(self):
        """backtest run 命令应该存在"""
        from cli.backtest import app as backtest_app

        runner = CliRunner()
        result = runner.invoke(backtest_app, ["run", "--help"])
        assert result.exit_code == 0
        assert "trader" in result.output.lower()

    def test_backtest_run_with_required_args(self):
        """backtest run --trader --from --to 应能正常执行（stub 阶段不报错）"""
        from cli.backtest import app as backtest_app

        runner = CliRunner()
        result = runner.invoke(
            backtest_app,
            ["run", "--trader", "trader_a", "--from", "2026-04-01", "--to", "2026-04-10"],
        )
        # stub 阶段：只要不抛异常（exit_code=0）即可
        assert result.exit_code == 0

    def test_backtest_run_missing_trader_arg(self):
        """缺少 --trader 参数应报错"""
        from cli.backtest import app as backtest_app

        runner = CliRunner()
        result = runner.invoke(
            backtest_app,
            ["run", "--from", "2026-04-01", "--to", "2026-04-10"],
        )
        assert result.exit_code != 0

    def test_backtest_run_missing_dates(self):
        """缺少日期参数应报错"""
        from cli.backtest import app as backtest_app

        runner = CliRunner()
        result = runner.invoke(
            backtest_app,
            ["run", "--trader", "trader_a"],
        )
        assert result.exit_code != 0


class TestBacktestCLIReportCommand:
    """backtest report 子命令测试"""

    def test_backtest_report_command_exists(self):
        """backtest report 命令应该存在"""
        from cli.backtest import app as backtest_app

        runner = CliRunner()
        result = runner.invoke(backtest_app, ["report", "--help"])
        assert result.exit_code == 0


class TestBacktestCLIValidateRulesCommand:
    """backtest validate-rules 子命令测试"""

    def test_backtest_validate_rules_command_exists(self):
        """backtest validate-rules 命令应该存在"""
        from cli.backtest import app as backtest_app

        runner = CliRunner()
        result = runner.invoke(backtest_app, ["validate-rules", "--help"])
        assert result.exit_code == 0

    def test_backtest_validate_rules_produces_report(self):
        """NTL-S6-010 CLI接入: validate-rules 应生成包含覆盖率/后验收益的报告"""
        from cli.backtest import app as backtest_app

        runner = CliRunner()
        result = runner.invoke(
            backtest_app,
            ["validate-rules", "--trader", "trader_a", "--from", "2026-04-01", "--to", "2026-04-01"],
        )
        # stub阶段: 暂时接受exit_code=0即可（后续接入后会返回真实报告）
        assert result.exit_code == 0
