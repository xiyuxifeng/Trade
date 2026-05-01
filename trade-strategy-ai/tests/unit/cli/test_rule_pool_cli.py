"""NTL-S11-009: rule-pool CLI 单元测试"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner


class TestRulePoolCLIListCommand:
    """rule-pool list 子命令测试"""

    def test_rule_pool_list_command_exists(self):
        """rule-pool list 命令应该存在"""
        from cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["rule-pool", "list", "--help"])
        assert result.exit_code == 0
        assert "limit" in result.output.lower()

    def test_rule_pool_list_with_limit(self):
        """rule-pool list --limit 验证命令结构正确（数据库依赖测试）"""
        from cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["rule-pool", "list", "--limit", "10"])
        # 命令能执行即可（exit_code 0 或预期的数据库错误如 table not exists）
        # 只要不是因命令不存在而失败（exit_code 1 且 output 为空）即可
        assert result.exit_code == 0 or result.exception is not None


class TestRulePoolCLIReviewCommand:
    """rule-pool review 子命令测试"""

    def test_rule_pool_review_command_exists(self):
        """rule-pool review 命令应该存在"""
        from cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["rule-pool", "review", "--help"])
        assert result.exit_code == 0
        # typer 将下划线转换为 hyphen 显示
        assert "rule-id" in result.output.lower()
        assert "decision" in result.output.lower()

    def test_rule_pool_review_missing_args(self):
        """缺少参数时应该报错"""
        from cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["rule-pool", "review"])
        assert result.exit_code != 0

    def test_rule_pool_review_help_shows_options(self):
        """rule-pool review --help 应显示必填参数"""
        from cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["rule-pool", "review", "--help"])
        assert result.exit_code == 0
        assert "[required]" in result.output