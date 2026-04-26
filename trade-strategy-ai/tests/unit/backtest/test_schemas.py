"""NTL-S6-001: 回测 schema 单元测试"""

from __future__ import annotations

from datetime import date
from typing import Literal

import pytest

from src.backtest.schemas import (
    BacktestRequest,
    BacktestResult,
    BacktestSummary,
    BacktestTradeRecord,
    RuleValidationResult,
)


class TestBacktestRequest:
    """BacktestRequest 数据类测试"""

    def test_backtest_request_defaults(self):
        """请求默认值为 full 模式，snapshot only"""
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 10),
        )
        assert req.mode == "full"
        assert req.use_snapshot_only is True
        assert req.scoring_profile == "stage5"
        assert req.strategy_version_id is None
        assert req.symbols == []

    def test_backtest_request_all_fields(self):
        """完整参数构造"""
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 10),
            strategy_version_id="v1",
            symbols=["000001.SZ"],
            mode="replay",
            use_snapshot_only=False,
            scoring_profile="custom",
        )
        assert req.trader_id == "trader_a"
        assert req.date_from == date(2026, 4, 1)
        assert req.date_to == date(2026, 4, 10)
        assert req.strategy_version_id == "v1"
        assert req.symbols == ["000001.SZ"]
        assert req.mode == "replay"
        assert req.use_snapshot_only is False

    def test_backtest_request_date_order(self):
        """date_from <= date_to 校验"""
        # 正常情况不抛异常
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 10),
        )
        assert req.date_from <= req.date_to

    def test_backtest_request_mode_literal(self):
        """mode 字段必须为合法字面量"""
        for mode in ["full", "replay", "rule_validation"]:
            req = BacktestRequest(
                trader_id="trader_a",
                date_from=date(2026, 4, 1),
                date_to=date(2026, 4, 10),
                mode=mode,
            )
            assert req.mode == mode


class TestBacktestTradeRecord:
    """BacktestTradeRecord 数据类测试"""

    def test_backtest_trade_record_fields(self):
        """核心字段存在且默认值正确"""
        record = BacktestTradeRecord(
            trade_date=date(2026, 4, 1),
            trader_id="trader_a",
            strategy_version_id="v1",
            symbol="000001.SZ",
            status="skipped",
        )
        assert record.trade_date == date(2026, 4, 1)
        assert record.trader_id == "trader_a"
        assert record.strategy_version_id == "v1"
        assert record.symbol == "000001.SZ"
        assert record.status == "skipped"
        assert record.skip_reason is None
        assert record.entry_price is None
        assert record.exit_price is None

    def test_backtest_trade_record_open_status(self):
        """status=open 时持仓记录"""
        record = BacktestTradeRecord(
            trade_date=date(2026, 4, 1),
            trader_id="trader_a",
            strategy_version_id="v1",
            symbol="000001.SZ",
            status="open",
            entry_price=10.0,
            entry_date=date(2026, 4, 1),
        )
        assert record.status == "open"
        assert record.entry_price == 10.0
        assert record.exit_price is None

    def test_backtest_trade_record_closed_status(self):
        """status=closed 时有完整收益数据"""
        record = BacktestTradeRecord(
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
            mfe=0.05,
            mae=0.01,
        )
        assert record.return_pct == pytest.approx(0.06)
        assert record.mfe == pytest.approx(0.05)
        assert record.mae == pytest.approx(0.01)

    def test_backtest_trade_record_status_literal(self):
        """status 必须是合法字面量"""
        for status in ["open", "closed", "skipped", "invalid"]:
            record = BacktestTradeRecord(
                trade_date=date(2026, 4, 1),
                trader_id="trader_a",
                strategy_version_id="v1",
                symbol="000001.SZ",
                status=status,
            )
            assert record.status == status


class TestRuleValidationResult:
    """RuleValidationResult 数据类测试"""

    def test_rule_validation_result_fields(self):
        """核心字段存在，hit_rate 为手动传入字段（非自动计算）"""
        result = RuleValidationResult(
            trader_id="trader_a",
            strategy_version_id="v1",
            rule_id="r1",
            rule_text="RSI < 30",
            programmable=True,
            validation_status="validated",
            hit_count=5,
            sample_count=10,
            hit_rate=0.5,
        )
        assert result.trader_id == "trader_a"
        assert result.rule_id == "r1"
        assert result.programmable is True
        assert result.hit_count == 5
        assert result.sample_count == 10
        assert result.hit_rate == pytest.approx(0.5)
        assert result.notes == []

    def test_rule_validation_result_unsupported(self):
        """不支持的规则"""
        result = RuleValidationResult(
            trader_id="trader_a",
            strategy_version_id="v1",
            rule_id="r2",
            rule_text="关注宏观新闻",
            programmable=False,
            validation_status="unsupported_rule",
            hit_count=0,
            sample_count=0,
        )
        assert result.programmable is False
        assert result.validation_status == "unsupported_rule"

    def test_rule_validation_result_status_literal(self):
        """validation_status 必须是合法字面量"""
        for status in [
            "validated",
            "unsupported_rule",
            "missing_field",
            "missing_snapshot",
            "invalid_rule",
        ]:
            result = RuleValidationResult(
                trader_id="trader_a",
                strategy_version_id="v1",
                rule_id="r1",
                rule_text="test",
                programmable=True,
                validation_status=status,
            )
            assert result.validation_status == status


class TestBacktestSummary:
    """BacktestSummary 数据类测试"""

    def test_backtest_summary_fields(self):
        """汇总字段存在"""
        summary = BacktestSummary(
            total_days=10,
            total_trades=5,
            valid_trades=3,
            skipped_trades=2,
            win_rate=0.666,
            avg_return_pct=0.04,
        )
        assert summary.total_days == 10
        assert summary.total_trades == 5
        assert summary.valid_trades == 3
        assert summary.skipped_trades == 2
        assert summary.win_rate == pytest.approx(0.666)


class TestBacktestResult:
    """BacktestResult 数据类测试"""

    def test_backtest_result_fields(self):
        """结果包含 records 和 summary"""
        record = BacktestTradeRecord(
            trade_date=date(2026, 4, 1),
            trader_id="trader_a",
            strategy_version_id="v1",
            symbol="000001.SZ",
            status="skipped",
        )
        summary = BacktestSummary(
            total_days=10,
            total_trades=1,
            valid_trades=0,
            skipped_trades=1,
        )
        result = BacktestResult(
            request_trader_id="trader_a",
            request_date_from=date(2026, 4, 1),
            request_date_to=date(2026, 4, 10),
            records=[record],
            summary=summary,
        )
        assert result.request_trader_id == "trader_a"
        assert len(result.records) == 1
        assert result.summary.total_days == 10
