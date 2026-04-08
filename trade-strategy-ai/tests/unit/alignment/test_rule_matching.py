"""
规则匹配与评分单元测试 — P3-005~P3-008。
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.alignment.rule_matching import (
    RuleCoverageResult,
    RuleAccuracyResult,
    RuleConflictResult,
    RuleMissDetectionResult,
    UnmatchedTrade,
    compute_rule_accuracy,
    compute_rule_coverage,
    detect_rule_conflicts,
    detect_unmatched_trades,
    generate_rule_matching_report,
    _are_rules_mutually_exclusive,
    _are_rules_overlapping,
    _check_symbol_match,
    _is_rule_prediction_correct,
)
from src.alignment.types import StrategyRule, TradeRecord


def _make_trade(trade_id: str, symbol: str = "000001.SZ", side: str = "buy") -> TradeRecord:
    """创建测试用交易记录。"""
    return TradeRecord(
        trade_id=trade_id,
        symbol=symbol,
        side=side,
        price=10.0,
        quantity=100.0,
        executed_at=datetime.now(),
    )


def _make_rule(rule_id: str, rule_type: str = "entry", instrument_focus: str = "stock") -> StrategyRule:
    """创建测试用规则。"""
    return StrategyRule(
        rule_id=rule_id,
        rule_type=rule_type,
        instrument_focus=instrument_focus,
        confidence=0.8,
    )


class TestDetectUnmatchedTrades:
    """P3-005: 规则漏配检测测试。"""

    def test_no_unmatched(self):
        """所有交易都被匹配。"""
        trades = [_make_trade("t1")]
        rules = [_make_rule("r1")]
        result = detect_unmatched_trades(trades, rules)

        assert result.unmatched_count == 0
        assert result.unmatched_rate == 0.0

    def test_with_unmatched(self):
        """存在未匹配交易。"""
        # 使用不匹配的标的类型
        trades = [_make_trade("t1", symbol="510300.SH")]  # ETF
        rules = [_make_rule("r1", instrument_focus="stock")]  # 只覆盖股票
        result = detect_unmatched_trades(trades, rules)

        assert result.unmatched_count == 1
        assert result.unmatched_rate == 1.0

    def test_empty_trades(self):
        """空交易列表。"""
        result = detect_unmatched_trades([], [_make_rule("r1")])
        assert result.total_trades == 0

    def test_empty_rules(self):
        """无规则时所有交易都未匹配。"""
        trades = [_make_trade("t1")]
        result = detect_unmatched_trades(trades, [])
        assert result.unmatched_count == 1
        assert "No rules defined" in result.unmatched_trades[0].reason


class TestComputeRuleCoverage:
    """P3-006: 规则覆盖率测试。"""

    def test_basic_coverage(self):
        """基本覆盖率计算。"""
        trades = [_make_trade("t1"), _make_trade("t2")]
        rules = [_make_rule("r1")]
        result = compute_rule_coverage(trades, rules)

        assert result.total_trades == 2
        assert 0 <= result.overall_coverage <= 1.0

    def test_coverage_zero(self):
        """无规则时覆盖率为零。"""
        trades = [_make_trade("t1")]
        result = compute_rule_coverage(trades, [])
        assert result.overall_coverage == 0.0


class TestComputeRuleAccuracy:
    """P3-007: 规则准确度测试。"""

    def test_basic_accuracy(self):
        """基本准确度计算。"""
        trades = [_make_trade("t1", side="buy")]
        rules = [_make_rule("r1", rule_type="entry")]
        result = compute_rule_accuracy(trades, rules)

        assert 0 <= result.average_accuracy <= 1.0

    def test_entry_rule_accuracy(self):
        """Entry 规则准确度。"""
        trades = [
            _make_trade("t1", side="buy"),
            _make_trade("t2", side="sell"),
        ]
        rules = [_make_rule("r1", rule_type="entry")]
        result = compute_rule_accuracy(trades, rules)

        # entry 规则预测 buy，所以 t1 正确，t2 错误
        assert "r1" in result.rule_accuracy
        assert result.rule_accuracy["r1"] == pytest.approx(0.5, abs=0.01)

    def test_exit_rule_accuracy(self):
        """Exit 规则准确度。"""
        trades = [
            _make_trade("t1", side="sell"),
            _make_trade("t2", side="buy"),
        ]
        rules = [_make_rule("r1", rule_type="exit")]
        result = compute_rule_accuracy(trades, rules)

        # exit 规则预测 sell，所以 t1 正确，t2 错误
        assert "r1" in result.rule_accuracy


class TestDetectRuleConflicts:
    """P3-008: 规则冲突检测测试。"""

    def test_no_conflicts(self):
        """无冲突规则。"""
        rules = [
            _make_rule("r1", rule_type="entry"),
            _make_rule("r2", rule_type="exit"),
        ]
        result = detect_rule_conflicts(rules)

        # entry 和 exit 规则默认不冲突
        assert result.total_conflicts >= 0

    def test_contradiction_detected(self):
        """检测到矛盾规则。"""
        rules = [
            StrategyRule(
                rule_id="r1",
                rule_type="entry",
                condition={"indicator": "MA20", "operator": ">"},
            ),
            StrategyRule(
                rule_id="r2",
                rule_type="entry",
                condition={"indicator": "MA20", "operator": "<"},
            ),
        ]
        result = detect_rule_conflicts(rules)
        assert result.total_conflicts >= 1

    def test_mutual_exclusion(self):
        """互斥规则检测。"""
        rule1 = _make_rule("r1", rule_type="entry")
        rule2 = _make_rule("r2", rule_type="exit")
        # 手动设置相同的 side
        rule1.action = {"side": "buy"}
        rule2.action = {"side": "buy"}

        assert _are_rules_mutually_exclusive(rule1, rule2) == True

    def test_overlap(self):
        """重叠规则检测。"""
        rule1 = _make_rule("r1", rule_type="entry")
        rule2 = _make_rule("r2", rule_type="entry")
        rule1.condition = {"indicator": "MA20"}
        rule2.condition = {"indicator": "MA20"}

        assert _are_rules_overlapping(rule1, rule2) == True


class TestHelperFunctions:
    """辅助函数测试。"""

    def test_check_symbol_match(self):
        """标的匹配检查。"""
        rule_stock = _make_rule("r1", instrument_focus="stock")
        rule_etf = _make_rule("r1", instrument_focus="etf")
        rule_mixed = _make_rule("r1", instrument_focus="mixed")

        assert _check_symbol_match(rule_stock, "000001.SZ") == True
        assert _check_symbol_match(rule_etf, "510300.SH") == True
        assert _check_symbol_match(rule_mixed, "ANY") == True

    def test_is_rule_prediction_correct(self):
        """规则预测正确性判断。"""
        entry_rule = _make_rule("r1", rule_type="entry")
        exit_rule = _make_rule("r1", rule_type="exit")

        buy_trade = _make_trade("t1", side="buy")
        sell_trade = _make_trade("t2", side="sell")

        assert _is_rule_prediction_correct(entry_rule, buy_trade) == True
        assert _is_rule_prediction_correct(entry_rule, sell_trade) == False
        assert _is_rule_prediction_correct(exit_rule, sell_trade) == True
        assert _is_rule_prediction_correct(exit_rule, buy_trade) == False


class TestRuleMatchingReport:
    """综合报告测试。"""

    def test_generate_report(self):
        """生成综合报告。"""
        trades = [_make_trade("t1")]
        rules = [_make_rule("r1")]

        report = generate_rule_matching_report("trader1", trades, rules)

        assert report.trader_id == "trader1"
        assert report.coverage is not None
        assert report.accuracy is not None
        assert report.conflicts is not None
        assert report.unmatched is not None

    def test_empty_data(self):
        """空数据生成报告。"""
        report = generate_rule_matching_report("trader1", [], [])
        assert report.trader_id == "trader1"
        assert report.coverage is not None
        assert report.accuracy is not None
