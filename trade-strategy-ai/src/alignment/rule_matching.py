"""
规则匹配与评分 — P3-005~P3-008。

扩展 P3-001 的规则匹配功能：
  - P3-005: 规则漏配检测
  - P3-006: 规则覆盖率计算
  - P3-007: 规则准确度计算
  - P3-008: 规则冲突检测
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.alignment.types import (
    ConflictDetectionResult,
    ConflictType,
    MatchResult,
    RuleMatchScore,
    StrategyRule,
    TradeRecord,
)
from src.alignment.scoring import _evaluate_rule_trade_match
from src.alignment.conflict import _are_rules_contradictory


# ---------------------------------------------------------------------------
# P3-005: 规则漏配检测
# ---------------------------------------------------------------------------

@dataclass
class UnmatchedTrade:
    """未被规则覆盖的交易。"""
    trade: TradeRecord
    reason: str
    closest_rule_id: str | None = None
    closest_score: float = 0.0


@dataclass
class RuleMissDetectionResult:
    """规则漏配检测结果。"""
    unmatched_trades: list[UnmatchedTrade] = field(default_factory=list)
    total_trades: int = 0
    unmatched_count: int = 0
    unmatched_rate: float = 0.0


def detect_unmatched_trades(
    trades: list[TradeRecord],
    rules: list[StrategyRule],
    min_match_score: float = 0.3,
) -> RuleMissDetectionResult:
    """检测未被规则覆盖的交易（P3-005）。

    找出历史交易中没有被任何规则匹配的条目，分析漏配原因。

    Args:
        trades: 交易记录列表
        rules: 策略规则列表
        min_match_score: 最小匹配分数阈值

    Returns:
        RuleMissDetectionResult
    """
    if not trades:
        return RuleMissDetectionResult()

    unmatched_trades: list[UnmatchedTrade] = []

    for trade in trades:
        best_match: tuple[str, float] | None = None
        is_matched = False

        for rule in rules:
            result = _evaluate_rule_trade_match(rule, trade)
            if result.matched and result.score >= min_match_score:
                is_matched = True
                break
            if best_match is None or result.score > best_match[1]:
                best_match = (rule.rule_id, result.score)

        if not is_matched:
            reason = _analyze_unmatched_reason(trade, rules)
            unmatched_trades.append(UnmatchedTrade(
                trade=trade,
                reason=reason,
                closest_rule_id=best_match[0] if best_match else None,
                closest_score=best_match[1] if best_match else 0.0,
            ))

    unmatched_count = len(unmatched_trades)
    total_trades = len(trades)

    return RuleMissDetectionResult(
        unmatched_trades=unmatched_trades,
        total_trades=total_trades,
        unmatched_count=unmatched_count,
        unmatched_rate=unmatched_count / total_trades if total_trades > 0 else 0.0,
    )


def _analyze_unmatched_reason(trade: TradeRecord, rules: list[StrategyRule]) -> str:
    """分析交易未匹配的原因。"""
    if not rules:
        return "No rules defined"

    # 检查是否有匹配规则的类型
    entry_rules = [r for r in rules if r.rule_type == "entry"]
    exit_rules = [r for r in rules if r.rule_type == "exit"]

    if trade.side == "buy" and not entry_rules:
        return "No entry rules defined"
    if trade.side == "sell" and not exit_rules:
        return "No exit rules defined"

    # 检查标的类型
    matching_rules = [
        r for r in rules
        if _check_symbol_match(r, trade.symbol)
    ]
    if not matching_rules:
        return f"Symbol {trade.symbol} not covered by any rule"

    return "Condition mismatch"


def _check_symbol_match(rule: StrategyRule, symbol: str) -> bool:
    """检查规则是否适用于该标的。"""
    focus = rule.instrument_focus
    if focus == "mixed":
        return True

    # 简化检查
    if focus == "stock":
        return ".SZ" in symbol or ".SH" in symbol
    elif focus == "etf":
        return "ETF" in symbol.upper() or symbol.startswith("510") or symbol.startswith("159")
    elif focus == "cb":
        return symbol.startswith("CB")

    return True


# ---------------------------------------------------------------------------
# P3-006: 规则覆盖率计算
# ---------------------------------------------------------------------------

@dataclass
class RuleCoverageResult:
    """规则覆盖率结果。"""
    # 每条规则的覆盖率
    rule_coverage: dict[str, float] = field(default_factory=dict)
    # 总体覆盖率（被至少一条规则覆盖的交易比例）
    overall_coverage: float = 0.0
    # 被覆盖的交易数
    covered_trades: int = 0
    # 总交易数
    total_trades: int = 0


def compute_rule_coverage(
    trades: list[TradeRecord],
    rules: list[StrategyRule],
    min_match_score: float = 0.3,
) -> RuleCoverageResult:
    """计算规则覆盖率（P3-006）。

    计算每条规则覆盖的交易比例，以及总体覆盖率。

    Args:
        trades: 交易记录列表
        rules: 策略规则列表
        min_match_score: 最小匹配分数

    Returns:
        RuleCoverageResult
    """
    if not trades:
        return RuleCoverageResult()

    total_trades = len(trades)
    rule_matched_counts: dict[str, int] = {r.rule_id: 0 for r in rules}
    covered_trade_ids: set[str] = set()

    # 统计每条规则匹配的交易
    for trade in trades:
        for rule in rules:
            result = _evaluate_rule_trade_match(rule, trade)
            if result.matched and result.score >= min_match_score:
                rule_matched_counts[rule.rule_id] += 1
                covered_trade_ids.add(trade.trade_id)

    # 计算覆盖率
    rule_coverage = {
        rule_id: count / total_trades
        for rule_id, count in rule_matched_counts.items()
    }

    overall_coverage = len(covered_trade_ids) / total_trades

    return RuleCoverageResult(
        rule_coverage=rule_coverage,
        overall_coverage=overall_coverage,
        covered_trades=len(covered_trade_ids),
        total_trades=total_trades,
    )


# ---------------------------------------------------------------------------
# P3-007: 规则准确度计算
# ---------------------------------------------------------------------------

@dataclass
class RuleAccuracyResult:
    """规则准确度结果。"""
    # 每条规则的准确度
    rule_accuracy: dict[str, float] = field(default_factory=dict)
    # 触发次数
    rule_trigger_counts: dict[str, int] = field(default_factory=dict)
    # 准确交易数
    rule_true_counts: dict[str, int] = field(default_factory=dict)
    # 平均准确度
    average_accuracy: float = 0.0


def compute_rule_accuracy(
    trades: list[TradeRecord],
    rules: list[StrategyRule],
    min_match_score: float = 0.3,
) -> RuleAccuracyResult:
    """计算规则准确度（P3-007）。

    规则准确度 = 规则触发中真实交易的比例。
    即：规则预测的买卖方向与实际一致的比例。

    Args:
        trades: 交易记录列表
        rules: 策略规则列表
        min_match_score: 最小匹配分数

    Returns:
        RuleAccuracyResult
    """
    if not trades:
        return RuleAccuracyResult()

    rule_trigger_counts: dict[str, int] = {r.rule_id: 0 for r in rules}
    rule_true_counts: dict[str, int] = {r.rule_id: 0 for r in rules}

    for trade in trades:
        for rule in rules:
            result = _evaluate_rule_trade_match(rule, trade)
            if result.matched and result.score >= min_match_score:
                rule_trigger_counts[rule.rule_id] += 1
                # 检查规则预测是否与实际一致
                if _is_rule_prediction_correct(rule, trade):
                    rule_true_counts[rule.rule_id] += 1

    # 计算准确度
    rule_accuracy = {}
    for rule_id in rule_trigger_counts:
        trigger_count = rule_trigger_counts[rule_id]
        if trigger_count > 0:
            rule_accuracy[rule_id] = rule_true_counts[rule_id] / trigger_count
        else:
            rule_accuracy[rule_id] = 0.0

    # 平均准确度
    accuracies = [acc for acc in rule_accuracy.values() if acc > 0]
    average_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0.0

    return RuleAccuracyResult(
        rule_accuracy=rule_accuracy,
        rule_trigger_counts=rule_trigger_counts,
        rule_true_counts=rule_true_counts,
        average_accuracy=average_accuracy,
    )


def _is_rule_prediction_correct(rule: StrategyRule, trade: TradeRecord) -> bool:
    """判断规则预测是否与实际交易一致。"""
    if rule.rule_type == "entry":
        return trade.side == "buy"
    elif rule.rule_type == "exit":
        return trade.side == "sell"
    # filter/sizing/risk 规则不涉及方向
    return True


# ---------------------------------------------------------------------------
# P3-008: 规则冲突检测
# ---------------------------------------------------------------------------

@dataclass
class RuleConflictResult:
    """规则冲突检测结果。"""
    # 冲突规则对
    conflicting_pairs: list[tuple[str, str]] = field(default_factory=list)
    # 冲突类型分组
    conflicts_by_type: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    # 总冲突数
    total_conflicts: int = 0


def detect_rule_conflicts(rules: list[StrategyRule]) -> RuleConflictResult:
    """检测规则之间的冲突（P3-008）。

    检测互相排斥的规则对。

    Args:
        rules: 策略规则列表

    Returns:
        RuleConflictResult
    """
    conflicting_pairs: list[tuple[str, str]] = []
    conflicts_by_type: dict[str, list[tuple[str, str]]] = {}

    for i, rule1 in enumerate(rules):
        for rule2 in rules[i + 1:]:
            conflict_type = _get_conflict_type(rule1, rule2)
            if conflict_type:
                pair = (rule1.rule_id, rule2.rule_id)
                conflicting_pairs.append(pair)
                conflicts_by_type.setdefault(conflict_type, []).append(pair)

    return RuleConflictResult(
        conflicting_pairs=conflicting_pairs,
        conflicts_by_type=conflicts_by_type,
        total_conflicts=len(conflicting_pairs),
    )


def _get_conflict_type(rule1: StrategyRule, rule2: StrategyRule) -> str | None:
    """判断两条规则的冲突类型。"""
    # 1. 矛盾规则（同一指标相反条件）
    if _are_rules_contradictory(rule1, rule2):
        return "contradiction"

    # 2. 互斥规则（同一标的相反方向）
    if _are_rules_mutually_exclusive(rule1, rule2):
        return "mutual_exclusion"

    # 3. 重叠规则（完全相同的条件）
    if _are_rules_overlapping(rule1, rule2):
        return "overlap"

    return None


def _are_rules_mutually_exclusive(rule1: StrategyRule, rule2: StrategyRule) -> bool:
    """判断两条规则是否互斥。"""
    # entry 和 exit 规则但方向相同（应该是相反的）
    if rule1.rule_type == rule2.rule_type:
        return False

    # 检查 action 中的方向
    side1 = rule1.action.get("side", "")
    side2 = rule2.action.get("side", "")

    # 如果两个规则都是 buy 或都是 sell 且类型不同，可能是互斥
    if side1 and side2 and side1 == side2:
        if rule1.rule_type in ("entry", "exit") and rule2.rule_type in ("entry", "exit"):
            return True

    return False


def _are_rules_overlapping(rule1: StrategyRule, rule2: StrategyRule) -> bool:
    """判断两条规则是否完全重叠。"""
    # 条件完全相同
    if rule1.condition and rule2.condition:
        return rule1.condition == rule2.condition

    # action 完全相同
    if rule1.action and rule2.action:
        return rule1.action == rule2.action

    return False


# ---------------------------------------------------------------------------
# 综合报告
# ---------------------------------------------------------------------------

@dataclass
class RuleMatchingReport:
    """规则匹配综合报告。"""
    trader_id: str
    coverage: RuleCoverageResult | None = None
    accuracy: RuleAccuracyResult | None = None
    conflicts: RuleConflictResult | None = None
    unmatched: RuleMissDetectionResult | None = None


def generate_rule_matching_report(
    trader_id: str,
    trades: list[TradeRecord],
    rules: list[StrategyRule],
) -> RuleMatchingReport:
    """生成规则匹配综合报告。

    Args:
        trader_id: 交易员 ID
        trades: 交易记录列表
        rules: 策略规则列表

    Returns:
        RuleMatchingReport
    """
    return RuleMatchingReport(
        trader_id=trader_id,
        coverage=compute_rule_coverage(trades, rules),
        accuracy=compute_rule_accuracy(trades, rules),
        conflicts=detect_rule_conflicts(rules),
        unmatched=detect_unmatched_trades(trades, rules),
    )
