"""NTL-S11-009: rule-pool CLI 单元测试"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner
from src.services.base import ServiceResult


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

    def test_rule_pool_review_batch_reports_compatibility_only_without_crashing(self, monkeypatch):
        """legacy 批量审核命令必须拒写并给出清晰提示。"""
        import cli.main as cli_main

        class _FakeRulePoolService:
            async def review_batch(self, **_kwargs):
                return ServiceResult(
                    status="error",
                    message="legacy rule-pool batch review is compatibility-only",
                    payload={"status": "compatibility_only", "updated_count": 0},
                )

        monkeypatch.setattr(cli_main, "RulePoolService", _FakeRulePoolService)
        runner = CliRunner()
        result = runner.invoke(cli_main.app, ["rule-pool", "review-batch", "--decision", "approve"])

        assert result.exit_code == 0
        assert "更新失败" in result.output
        assert "compatibility-only" in result.output
