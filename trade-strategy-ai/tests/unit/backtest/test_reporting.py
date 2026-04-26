"""NTL-S6-005: 回测报告模块单元测试"""

from __future__ import annotations

from datetime import date

import pytest

from src.backtest.schemas import (
    BacktestRequest,
    BacktestResult,
    BacktestSummary,
    BacktestTradeRecord,
)


def _sample_result() -> BacktestResult:
    """构造样例回测结果（用于报告测试）"""
    records = [
        BacktestTradeRecord(
            trade_date=date(2026, 4, 1),
            trader_id="trader_a",
            strategy_version_id="v1",
            symbol="000001.SZ",
            status="closed",
            entry_price=10.0,
            exit_price=10.6,
            entry_date=date(2026, 4, 1),
            exit_date=date(2026, 4, 3),
            return_pct=0.06,
            mfe=0.08,
            mae=0.01,
        ),
        BacktestTradeRecord(
            trade_date=date(2026, 4, 2),
            trader_id="trader_a",
            strategy_version_id="v1",
            symbol="000002.SZ",
            status="closed",
            entry_price=20.0,
            exit_price=19.0,
            entry_date=date(2026, 4, 2),
            exit_date=date(2026, 4, 6),
            return_pct=-0.05,
            mfe=0.01,
            mae=-0.06,
        ),
        BacktestTradeRecord(
            trade_date=date(2026, 4, 3),
            trader_id="trader_a",
            strategy_version_id="v1",
            symbol="000003.SZ",
            status="skipped",
            skip_reason="no_snapshot",
        ),
    ]
    summary = BacktestSummary(
        total_days=10,
        total_trades=3,
        valid_trades=2,
        skipped_trades=1,
        win_rate=0.5,
        avg_return_pct=0.005,
    )
    return BacktestResult(
        request_trader_id="trader_a",
        request_date_from=date(2026, 4, 1),
        request_date_to=date(2026, 4, 10),
        records=records,
        summary=summary,
    )


class TestRenderMarkdownSummary:
    """Markdown 报告渲染测试"""

    def test_render_markdown_summary_contains_key_metrics(self):
        """报告应包含样本天数、交易数、胜率"""
        from src.backtest.reporting import render_backtest_markdown

        result = _sample_result()
        report = render_backtest_markdown(result)

        assert "胜率" in report or "win_rate" in report.lower()
        assert "样本覆盖天数" in report or "total_days" in report.lower()
        assert "trader_a" in report

    def test_render_markdown_summary_contains_trader_id(self):
        """报告应包含 trader_id"""
        from src.backtest.reporting import render_backtest_markdown

        result = _sample_result()
        report = render_backtest_markdown(result)
        assert "trader_a" in report

    def test_render_markdown_summary_contains_date_range(self):
        """报告应包含日期区间"""
        from src.backtest.reporting import render_backtest_markdown

        result = _sample_result()
        report = render_backtest_markdown(result)
        assert "2026-04-01" in report or "04-01" in report

    def test_render_markdown_summary_contains_symbol(self):
        """报告应包含标的列表"""
        from src.backtest.reporting import render_backtest_markdown

        result = _sample_result()
        report = render_backtest_markdown(result)
        assert "000001.SZ" in report

    def test_render_markdown_summary_skip_reason_shown(self):
        """skipped 记录应显示 skip_reason"""
        from src.backtest.reporting import render_backtest_markdown

        result = _sample_result()
        report = render_backtest_markdown(result)
        assert "no_snapshot" in report or "skipped" in report.lower()


class TestRenderJSONResult:
    """JSON 报告渲染测试"""

    def test_render_json_result_is_serializable(self):
        """JSON 报告应可序列化"""
        from src.backtest.reporting import render_backtest_json

        result = _sample_result()
        json_str = render_backtest_json(result)

        import json

        parsed = json.loads(json_str)
        assert parsed["request_trader_id"] == "trader_a"
        assert len(parsed["records"]) == 3

    def test_render_json_result_contains_all_fields(self):
        """JSON 输出应包含所有关键字段"""
        from src.backtest.reporting import render_backtest_json

        result = _sample_result()
        json_str = render_backtest_json(result)

        import json

        parsed = json.loads(json_str)
        assert "request_trader_id" in parsed
        assert "request_date_from" in parsed
        assert "records" in parsed
        assert "summary" in parsed


class TestRuleValidationMarkdown:
    """规则验真报告测试"""

    def test_render_rule_validation_markdown_contains_coverage(self):
        """规则报告应包含覆盖率"""
        from src.backtest.reporting import render_rule_validation_markdown
        from src.backtest.schemas import RuleValidationResult

        rule_results = [
            RuleValidationResult(
                trader_id="trader_a",
                strategy_version_id="v1",
                rule_id="r1",
                rule_text="RSI < 30",
                programmable=True,
                validation_status="validated",
                hit_count=5,
                sample_count=10,
                hit_rate=0.5,
            ),
            RuleValidationResult(
                trader_id="trader_a",
                strategy_version_id="v1",
                rule_id="r2",
                rule_text="关注宏观",
                programmable=False,
                validation_status="unsupported_rule",
                hit_count=0,
                sample_count=0,
            ),
        ]
        report = render_rule_validation_markdown(rule_results)
        assert "覆盖率" in report or "coverage" in report.lower() or "hit" in report.lower()

    def test_render_rule_validation_markdown_contains_posterior_return(self):
        """NTL-S6-011: 规则报告应包含后验收益标签"""
        from src.backtest.reporting import render_rule_validation_markdown
        from src.backtest.schemas import RuleValidationResult

        rule_results = [
            RuleValidationResult(
                trader_id="trader_a",
                strategy_version_id="v1",
                rule_id="r1",
                rule_text="RSI < 30",
                programmable=True,
                validation_status="validated",
                hit_count=5,
                sample_count=10,
                hit_rate=0.5,
                posterior_return_mean=0.023,
                posterior_return_median=0.015,
            ),
        ]
        report = render_rule_validation_markdown(rule_results)
        assert "后验收益" in report
