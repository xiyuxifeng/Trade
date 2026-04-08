"""
冲突检测算法 — P3-003。

核心算法：
  - detect_conflicts() — 综合冲突检测
"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.alignment.types import (
    ConflictDetection,
    ConflictDetectionResult,
    ConflictType,
    StrategyRule,
    TradeRecord,
)


# ---------------------------------------------------------------------------
# P3-003: 冲突检测算法
# ---------------------------------------------------------------------------

def detect_conflicts(
    rules: list[StrategyRule],
    trades: list[TradeRecord] | None = None,
    **kwargs,
) -> ConflictDetection:
    """检测规则和交易之间的冲突。

    检测类型：
      1. 规则矛盾（Rule Contradiction）：互相排斥的规则同时存在
      2. 规则重叠（Rule Overlap）：规则覆盖范围重叠
      3. 行为偏离（Behavior Deviation）：实际交易偏离声称规则
      4. 参数不一致（Parameter Mismatch）：相似规则的参数不一致
      5. 时序冲突（Temporal Conflict）：规则触发时序矛盾

    Args:
        rules: 策略规则列表
        trades: 交易记录列表（可选）

    Returns:
        ConflictDetection
    """
    conflicts: list[ConflictDetectionResult] = []

    # 1. 规则矛盾检测
    contradictions = _detect_rule_contradictions(rules)
    conflicts.extend(contradictions)

    # 2. 规则重叠检测
    overlaps = _detect_rule_overlaps(rules)
    conflicts.extend(overlaps)

    # 3. 行为偏离检测
    if trades:
        deviations = _detect_behavior_deviations(rules, trades)
        conflicts.extend(deviations)

    # 4. 参数不一致检测
    param_issues = _detect_parameter_mismatches(rules)
    conflicts.extend(param_issues)

    # 5. 时序冲突检测
    temporal_issues = _detect_temporal_conflicts(rules)
    conflicts.extend(temporal_issues)

    # 汇总统计
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for conflict in conflicts:
        by_type[conflict.conflict_type.value] = by_type.get(conflict.conflict_type.value, 0) + 1
        by_severity[conflict.severity] = by_severity.get(conflict.severity, 0) + 1

    return ConflictDetection(
        trader_id="",  # 可后续填充
        total_conflicts=len(conflicts),
        by_type=by_type,
        by_severity=by_severity,
        conflicts=conflicts,
    )


def _detect_rule_contradictions(rules: list[StrategyRule]) -> list[ConflictDetectionResult]:
    """检测互相排斥的规则。

    例如：
      - 同时规定"MA20之上买入"和"MA20之下买入"
      - 同时规定"突破买入"和"跌破买入"
    """
    conflicts: list[ConflictDetectionResult] = []

    for i, rule1 in enumerate(rules):
        for rule2 in rules[i + 1:]:
            if _are_rules_contradictory(rule1, rule2):
                conflicts.append(ConflictDetectionResult(
                    conflict_type=ConflictType.RULE_CONTRADICTION,
                    severity="major",
                    message=f"Rules {rule1.rule_id} and {rule2.rule_id} are contradictory",
                    involved_rules=[rule1.rule_id, rule2.rule_id],
                    evidence={
                        "rule1_type": rule1.rule_type,
                        "rule2_type": rule2.rule_type,
                        "rule1_condition": rule1.condition,
                        "rule2_condition": rule2.condition,
                    },
                ))

    return conflicts


def _are_rules_contradictory(rule1: StrategyRule, rule2: StrategyRule) -> bool:
    """判断两条规则是否互相矛盾。"""
    # 1. 同类型规则但条件相反
    if rule1.rule_type == rule2.rule_type:
        cond1 = rule1.condition
        cond2 = rule2.condition

        # 检查 MA 条件相反
        if "indicator" in cond1 and "indicator" in cond2:
            if cond1.get("indicator") == cond2.get("indicator"):
                op1 = cond1.get("operator", "")
                op2 = cond2.get("operator", "")
                # > 和 < 互为矛盾
                if (op1 == ">" and op2 == "<") or (op1 == "<" and op2 == ">"):
                    return True

        # 检查 side 相反
        action1 = rule1.action.get("side", "")
        action2 = rule2.action.get("side", "")
        if action1 and action2 and action1 != action2:
            # 同类型规则但方向相反
            if rule1.rule_type in ("entry", "exit"):
                return True

    # 2. Entry 和 Exit 规则矛盾
    # 简化：如果 entry 和 exit 同时存在但条件完全相同
    if (rule1.rule_type == "entry" and rule2.rule_type == "exit") or \
       (rule1.rule_type == "exit" and rule2.rule_type == "entry"):
        if rule1.condition == rule2.condition and rule1.condition:
            return True

    return False


def _detect_rule_overlaps(rules: list[StrategyRule]) -> list[ConflictDetectionResult]:
    """检测规则重叠。"""
    conflicts: list[ConflictDetectionResult] = []

    for i, rule1 in enumerate(rules):
        for rule2 in rules[i + 1:]:
            overlap_score = _compute_rule_overlap(rule1, rule2)
            if overlap_score > 0.8:  # 重叠度超过 80%
                conflicts.append(ConflictDetectionResult(
                    conflict_type=ConflictType.RULE_OVERLAP,
                    severity="minor",
                    message=f"Rules {rule1.rule_id} and {rule2.rule_id} have high overlap ({overlap_score:.2f})",
                    involved_rules=[rule1.rule_id, rule2.rule_id],
                    evidence={"overlap_score": overlap_score},
                ))

    return conflicts


def _compute_rule_overlap(rule1: StrategyRule, rule2: StrategyRule) -> float:
    """计算两条规则的重叠度。"""
    # 简化：基于条件相似度
    cond1 = rule1.condition
    cond2 = rule2.condition

    if not cond1 or not cond2:
        return 0.0

    # 检查共同键
    common_keys = set(cond1.keys()) & set(cond2.keys())
    if not common_keys:
        return 0.0

    # 计算相似度
    matches = 0
    for key in common_keys:
        if cond1[key] == cond2[key]:
            matches += 1

    overlap = matches / max(len(cond1), len(cond2), 1)
    return float(overlap)


def _detect_behavior_deviations(
    rules: list[StrategyRule],
    trades: list[TradeRecord],
) -> list[ConflictDetectionResult]:
    """检测行为偏离规则。"""
    conflicts: list[ConflictDetectionResult] = []

    # 为每条规则检查是否有匹配的违规交易
    for rule in rules:
        if rule.rule_type not in ("entry", "exit"):
            continue

        # 简化：检查规则是否被使用
        matched_trades = _count_rule_matched_trades(rule, trades)
        total_trades = len(trades)

        if total_trades > 0:
            # 如果规则声称是某类行为，但实际很少匹配
            expected_match_rate = _get_expected_match_rate(rule)
            actual_match_rate = matched_trades / total_trades

            # 显著偏离
            if actual_match_rate < expected_match_rate * 0.3:
                conflicts.append(ConflictDetectionResult(
                    conflict_type=ConflictType.BEHAVIOR_DEVIATION,
                    severity="major",
                    message=f"Rule {rule.rule_id} has low match rate: {actual_match_rate:.2f} vs expected {expected_match_rate:.2f}",
                    involved_rules=[rule.rule_id],
                    involved_trades=[],
                    evidence={
                        "actual_match_rate": actual_match_rate,
                        "expected_match_rate": expected_match_rate,
                        "matched_trades": matched_trades,
                        "total_trades": total_trades,
                    },
                ))

    return conflicts


def _count_rule_matched_trades(rule: StrategyRule, trades: list[TradeRecord]) -> int:
    """计算匹配规则的交易数量。"""
    count = 0
    for trade in trades:
        if _trade_matches_rule(trade, rule):
            count += 1
    return count


def _trade_matches_rule(trade: TradeRecord, rule: StrategyRule) -> bool:
    """判断交易是否匹配规则。"""
    # 简化：检查规则类型与交易方向
    if rule.rule_type == "entry" and trade.side == "buy":
        return True
    if rule.rule_type == "exit" and trade.side == "sell":
        return True
    return False


def _get_expected_match_rate(rule: StrategyRule) -> float:
    """获取规则的期望匹配率。"""
    # 基于置信度估算
    return rule.confidence


def _detect_parameter_mismatches(rules: list[StrategyRule]) -> list[ConflictDetectionResult]:
    """检测参数不一致。"""
    conflicts: list[ConflictDetectionResult] = []

    # 按规则类型分组
    by_type: dict[str, list[StrategyRule]] = {}
    for rule in rules:
        by_type.setdefault(rule.rule_type, []).append(rule)

    # 检查同类型规则的参数一致性
    for rule_type, type_rules in by_type.items():
        if len(type_rules) < 2:
            continue

        # 简化：检查 action 中的参数
        params = [r.action.get("params", {}) for r in type_rules]
        if not params:
            continue

        # 检查关键参数是否一致
        key_params = set()
        for p in params:
            key_params.update(p.keys())

        for param in key_params:
            values = [p.get(param) for p in params if p.get(param) is not None]
            if len(set(values)) > 1:  # 存在不一致
                conflicts.append(ConflictDetectionResult(
                    conflict_type=ConflictType.PARAMETER_MISMATCH,
                    severity="minor",
                    message=f"Parameter '{param}' inconsistent across {rule_type} rules",
                    involved_rules=[r.rule_id for r in type_rules],
                    evidence={"parameter": param, "values": values},
                ))

    return conflicts


def _detect_temporal_conflicts(rules: list[StrategyRule]) -> list[ConflictDetectionResult]:
    """检测时序冲突。"""
    conflicts: list[ConflictDetectionResult] = []

    # 检查 entry 和 exit 规则的时序合理性
    entry_rules = [r for r in rules if r.rule_type == "entry"]
    exit_rules = [r for r in rules if r.rule_type == "exit"]

    for entry_rule in entry_rules:
        for exit_rule in exit_rules:
            if _has_temporal_conflict(entry_rule, exit_rule):
                conflicts.append(ConflictDetectionResult(
                    conflict_type=ConflictType.TEMPORAL_CONFLICT,
                    severity="critical",
                    message=f"Entry rule {entry_rule.rule_id} and exit rule {exit_rule.rule_id} have temporal conflict",
                    involved_rules=[entry_rule.rule_id, exit_rule.rule_id],
                    evidence={
                        "entry_condition": entry_rule.condition,
                        "exit_condition": exit_rule.condition,
                    },
                ))

    return conflicts


def _has_temporal_conflict(entry_rule: StrategyRule, exit_rule: StrategyRule) -> bool:
    """判断 entry 和 exit 规则是否存在时序冲突。"""
    # 简化：如果 exit 条件早于 entry 条件触发
    entry_cond = entry_rule.condition
    exit_cond = exit_rule.condition

    # 检查是否有矛盾的时间条件
    entry_time = entry_cond.get("time", "")
    exit_time = exit_cond.get("time", "")

    if entry_time and exit_time:
        # 简化：假设 exit 时间在 entry 之前是冲突的
        if exit_time < entry_time:
            return True

    return False
