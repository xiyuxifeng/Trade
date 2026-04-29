"""S7-003b: create-candidate --db CLI 测试"""
import json
import tempfile
from pathlib import Path

from typer.testing import CliRunner

from cli.optimize import app


runner = CliRunner()


class TestCreateCandidateDBFlag:
    """测试 --db 参数解析和链路分发。"""

    def test_db_flag_appears_in_help(self):
        """验证 --db 选项在 --help 中可见。"""
        result = runner.invoke(app, ["create-candidate", "--help"])
        assert result.exit_code == 0
        assert "--db" in result.stdout

    def test_db_mode_requires_trader_and_date(self):
        """--db=True 但缺少 --trader/--date 时报错。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            adj_file = Path(tmpdir) / "adjustments.json"
            adj_file.write_text(json.dumps({
                "adjustments": [
                    {
                        "trader_id": "trader_a",
                        "rule_id": "rule_001",
                        "rule_text": "规则1",
                        "current_status": "hit_rate_too_low_and_return_negative",
                        "suggestion": "删除此规则",
                        "confidence": 0.8,
                        "hit_rate": 0.2,
                        "posterior_return_mean": None,
                        "posterior_return_median": None,
                    }
                ]
            }))

            result = runner.invoke(
                app,
                [
                    "create-candidate",
                    "--db",
                    "--adjustments", str(adj_file),
                ],
            )
            # exit_code is 0 because typer.secho does not change exit_code;
            # the error message itself proves DB mode was triggered
            assert "--db=True 时必须指定 --trader 和 --date" in result.stdout

    def test_db_mode_missing_adjustments_reports_error(self):
        """--db=True 但缺少 --adjustments 时报错。"""
        result = runner.invoke(
            app,
            [
                "create-candidate",
                "--db",
                "--trader", "trader_a",
                "--date", "2026-04-25",
            ],
        )
        # 缺少 adjustments 走文件链路也会触发这个错误
        assert "无调整建议数据" in result.stdout or "adjustments" in result.stdout.lower()
