"""
冲突检测算法 — P3-003, P3-013~P3-016。

核心算法：
  - detect_conflicts() — 综合冲突检测
  - P3-013: _detect_temporal_conflicts() — 时序冲突检测增强
  - P3-014: _detect_parameter_mismatches() — 参数冲突检测增强
  - P3-015: _detect_rule_contradictions() — 逻辑冲突检测增强
  - P3-016: _classify_conflict_severity() — 冲突严重程度智能分类
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
# P3-016: 冲突严重程度智能分类
# ---------------------------------------------------------------------------

def _classify_conflict_severity(
    conflict_type: ConflictType,
    evidence: dict[str, Any],
    rules: list[StrategyRule] | None = None,
) -> str:
    """根据冲突类型和证据智能分类严重程度。

    严重程度判断逻辑：
      - Critical：导致无法执行的冲突（如 exit 在 entry 之前）
      - Major：影响策略有效性的冲突（如矛盾规则、高频偏离）
      - Minor：低影响的冲突（如轻微重叠、参数微小差异）

    Args:
        conflict_type: 冲突类型
        evidence: 冲突证据
        rules: 相关规则列表（用于更精确的判断）

    Returns:
        严重程度：critical / major / minor
    """
    # 1. 时序冲突：Critical
    if conflict_type == ConflictType.TEMPORAL_CONFLICT:
        entry_time = evidence.get("entry_condition", {}).get("time", "")
        exit_time = evidence.get("exit_condition", {}).get("time", "")

        # 如果 exit 时间明确早于 entry 时间，Critical
        if exit_time and entry_time and exit_time < entry_time:
            return "critical"

        # 检查持仓时长不合理的时序冲突
        hold_period_conflict = evidence.get("hold_period_conflict", False)
        if hold_period_conflict:
            return "critical"

        return "major"

    # 2. 规则矛盾：Major
    if conflict_type == ConflictType.RULE_CONTRADICTION:
        # 同一规则类型的矛盾是 Major
        rule1_type = evidence.get("rule1_type", "")
        rule2_type = evidence.get("rule2_type", "")

        # 完全相反的条件（> vs <）：Critical
        cond1 = evidence.get("rule1_condition", {})
        cond2 = evidence.get("rule2_condition", {})
        if "operator" in cond1 and "operator" in cond2:
            ops = {cond1["operator"], cond2["operator"]}
            if ops == {">", "<"} or ops == {">=", "<="}:
                return "critical"

        # 同类型 entry/exit 但方向相反
        if rule1_type == rule2_type and rule1_type in ("entry", "exit"):
            return "critical"

        return "major"

    # 3. 行为偏离：Major
    if conflict_type == ConflictType.BEHAVIOR_DEVIATION:
        actual_rate = evidence.get("actual_match_rate", 1.0)
        expected_rate = evidence.get("expected_match_rate", 0.5)

        # 实际匹配率远低于预期（<30%）：Critical
        if actual_rate < expected_rate * 0.3:
            return "critical"

        # 低于预期 50%：Major
        if actual_rate < expected_rate * 0.5:
            return "major"

        return "minor"

    # 4. 参数不一致：Minor（除非影响核心参数）
    if conflict_type == ConflictType.PARAMETER_MISMATCH:
        param = evidence.get("parameter", "")
        values = evidence.get("values", [])

        # 核心参数（stop_loss, take_profit, position_size）不一致：Major
        critical_params = {"stop_loss", "take_profit", "position_size", "threshold", "threshold_pct"}
        if param in critical_params:
            # 检查差异是否显著
            if len(values) >= 2:
                try:
                    numeric_values = [float(v) for v in values if v is not None]
                    if numeric_values:
                        max_val = max(numeric_values)
                        min_val = min(numeric_values)
                        # 差异超过 20%：Major
                        if max_val > 0 and (max_val - min_val) / max_val > 0.2:
                            return "major"
                except (ValueError, TypeError):
                    pass
            return "major"

        return "minor"

    # 5. 规则重叠：Minor
    if conflict_type == ConflictType.RULE_OVERLAP:
        overlap_score = evidence.get("overlap_score", 0.0)

        # 完全重叠（>95%）：Major
        if overlap_score > 0.95:
            return "major"

        # 高度重叠（>80%）：Minor
        if overlap_score > 0.8:
            return "minor"

        return "minor"

    # 默认：Major
    return "major"


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
    """检测互相排斥的规则（P3-015）。

    增强版：检测多种逻辑冲突类型
      - 同一指标相反条件（MA20 > vs MA20 <）
      - 同类型规则方向互斥（entry buy vs entry sell）
      - 条件范围冲突（threshold 过近或互为边界）
    """
    conflicts: list[ConflictDetectionResult] = []

    for i, rule1 in enumerate(rules):
        for rule2 in rules[i + 1:]:
            conflict_result = _check_rule_logical_conflict(rule1, rule2)
            if conflict_result:
                conflicts.append(conflict_result)

    return conflicts


def _check_rule_logical_conflict(rule1: StrategyRule, rule2: StrategyRule) -> ConflictDetectionResult | None:
    """检测两条规则之间的逻辑冲突类型。

    Args:
        rule1: 规则1
        rule2: 规则2

    Returns:
        ConflictDetectionResult 如果有冲突，否则 None
    """
    # 1. 同类型规则但条件相反（如 MA20 > vs MA20 <）
    if rule1.rule_type == rule2.rule_type:
        cond1 = rule1.condition
        cond2 = rule2.condition

        # 检查同一指标相反操作符
        if "indicator" in cond1 and "indicator" in cond2:
            if cond1.get("indicator") == cond2.get("indicator"):
                op1 = cond1.get("operator", "")
                op2 = cond2.get("operator", "")
                # > 和 < 互为矛盾
                if (op1 == ">" and op2 == "<") or (op1 == "<" and op2 == ">"):
                    evidence = {
                        "rule1_type": rule1.rule_type,
                        "rule2_type": rule2.rule_type,
                        "rule1_condition": cond1,
                        "rule2_condition": cond2,
                    }
                    return ConflictDetectionResult(
                        conflict_type=ConflictType.RULE_CONTRADICTION,
                        severity=_classify_conflict_severity(ConflictType.RULE_CONTRADICTION, evidence, [rule1, rule2]),
                        message=f"Rules {rule1.rule_id} and {rule2.rule_id} have contradictory conditions: "
                               f"{cond1.get('indicator')} {op1} vs {cond2.get('indicator')} {op2}",
                        involved_rules=[rule1.rule_id, rule2.rule_id],
                        evidence=evidence,
                    )

                # >= 和 <= 互为矛盾（边界条件）
                if (op1 == ">=" and op2 == "<=") or (op1 == "<=" and op2 == ">="):
                    evidence = {
                        "rule1_type": rule1.rule_type,
                        "rule2_type": rule2.rule_type,
                        "rule1_condition": cond1,
                        "rule2_condition": cond2,
                    }
                    return ConflictDetectionResult(
                        conflict_type=ConflictType.RULE_CONTRADICTION,
                        severity=_classify_conflict_severity(ConflictType.RULE_CONTRADICTION, evidence, [rule1, rule2]),
                        message=f"Rules {rule1.rule_id} and {rule2.rule_id} have boundary conflict: "
                               f"{cond1.get('indicator')} {op1} vs {cond2.get('indicator')} {op2}",
                        involved_rules=[rule1.rule_id, rule2.rule_id],
                        evidence=evidence,
                    )

        # 检查阈值过近冲突
        if _has_threshold_conflict(cond1, cond2):
            evidence = {
                "rule1_type": rule1.rule_type,
                "rule2_type": rule2.rule_type,
                "rule1_condition": cond1,
                "rule2_condition": cond2,
            }
            return ConflictDetectionResult(
                conflict_type=ConflictType.RULE_CONTRADICTION,
                severity=_classify_conflict_severity(ConflictType.RULE_CONTRADICTION, evidence, [rule1, rule2]),
                message=f"Rules {rule1.rule_id} and {rule2.rule_id} have threshold proximity conflict",
                involved_rules=[rule1.rule_id, rule2.rule_id],
                evidence=evidence,
            )

        # 检查 side 相反（同类型规则但方向相反）
        action1 = rule1.action.get("side", "")
        action2 = rule2.action.get("side", "")
        if action1 and action2 and action1 != action2:
            if rule1.rule_type in ("entry", "exit"):
                evidence = {
                    "rule1_type": rule1.rule_type,
                    "rule2_type": rule2.rule_type,
                    "rule1_side": action1,
                    "rule2_side": action2,
                }
                return ConflictDetectionResult(
                    conflict_type=ConflictType.RULE_CONTRADICTION,
                    severity=_classify_conflict_severity(ConflictType.RULE_CONTRADICTION, evidence, [rule1, rule2]),
                    message=f"Rules {rule1.rule_id} and {rule2.rule_id} have opposite sides: {action1} vs {action2}",
                    involved_rules=[rule1.rule_id, rule2.rule_id],
                    evidence=evidence,
                )

    # 2. Entry 和 Exit 规则矛盾（同一条件既是 entry 又是 exit）
    if (rule1.rule_type == "entry" and rule2.rule_type == "exit") or \
       (rule1.rule_type == "exit" and rule2.rule_type == "entry"):
        if rule1.condition == rule2.condition and rule1.condition:
            evidence = {
                "rule1_type": rule1.rule_type,
                "rule2_type": rule2.rule_type,
                "condition": rule1.condition,
            }
            return ConflictDetectionResult(
                conflict_type=ConflictType.RULE_CONTRADICTION,
                severity=_classify_conflict_severity(ConflictType.RULE_CONTRADICTION, evidence, [rule1, rule2]),
                message=f"Rules {rule1.rule_id} and {rule2.rule_id} have same condition but opposite types",
                involved_rules=[rule1.rule_id, rule2.rule_id],
                evidence=evidence,
            )

    return None


def _has_threshold_conflict(cond1: dict[str, Any], cond2: dict[str, Any]) -> bool:
    """检查两个条件的阈值是否存在冲突。

    阈值冲突定义：同一指标、同一方向、阈值过近（差异 < 5%）
    如：MA20 > 10 与 MA20 > 10.3 可能是冲突的（取决于场景）
    """
    if "indicator" not in cond1 or "indicator" not in cond2:
        return False

    if cond1.get("indicator") != cond2.get("indicator"):
        return False

    # 检查阈值是否过近
    threshold1 = cond1.get("threshold")
    threshold2 = cond2.get("threshold")

    if threshold1 is not None and threshold2 is not None:
        try:
            t1 = float(threshold1)
            t2 = float(threshold2)
            if t1 > 0 and t2 > 0:
                diff_ratio = abs(t1 - t2) / max(t1, t2)
                # 差异小于 5% 且同方向：潜在冲突
                if diff_ratio < 0.05:
                    return True
        except (ValueError, TypeError):
            pass

    return False


def _are_rules_contradictory(rule1: StrategyRule, rule2: StrategyRule) -> bool:
    """判断两条规则是否互相矛盾（兼容旧接口）。"""
    result = _check_rule_logical_conflict(rule1, rule2)
    return result is not None


def _detect_rule_overlaps(rules: list[StrategyRule]) -> list[ConflictDetectionResult]:
    """检测规则重叠。

    使用智能严重程度分类（P3-016）。
    """
    conflicts: list[ConflictDetectionResult] = []

    for i, rule1 in enumerate(rules):
        for rule2 in rules[i + 1:]:
            overlap_score = _compute_rule_overlap(rule1, rule2)
            if overlap_score > 0.8:  # 重叠度超过 80%
                evidence = {
                    "overlap_score": overlap_score,
                    "rule1_condition": rule1.condition,
                    "rule2_condition": rule2.condition,
                }
                conflicts.append(ConflictDetectionResult(
                    conflict_type=ConflictType.RULE_OVERLAP,
                    severity=_classify_conflict_severity(ConflictType.RULE_OVERLAP, evidence, [rule1, rule2]),
                    message=f"Rules {rule1.rule_id} and {rule2.rule_id} have high overlap ({overlap_score:.2f})",
                    involved_rules=[rule1.rule_id, rule2.rule_id],
                    evidence=evidence,
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
    """检测行为偏离规则。

    使用智能严重程度分类（P3-016）。

    偏离程度判断：
      - Critical：实际匹配率 < 期望匹配率 * 30%
      - Major：实际匹配率 < 期望匹配率 * 50%
      - Minor：其他低匹配情况
    """
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
                evidence = {
                    "actual_match_rate": actual_match_rate,
                    "expected_match_rate": expected_match_rate,
                    "matched_trades": matched_trades,
                    "total_trades": total_trades,
                }
                conflicts.append(ConflictDetectionResult(
                    conflict_type=ConflictType.BEHAVIOR_DEVIATION,
                    severity=_classify_conflict_severity(ConflictType.BEHAVIOR_DEVIATION, evidence, [rule]),
                    message=f"Rule {rule.rule_id} has low match rate: {actual_match_rate:.2f} vs expected {expected_match_rate:.2f}",
                    involved_rules=[rule.rule_id],
                    involved_trades=[],
                    evidence=evidence,
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
    """检测参数不一致（P3-014）。

    增强版：检测 condition 和 action 中的参数冲突
      - action.params 参数不一致
      - condition 中的阈值参数不一致
      - 核心参数（stop_loss, take_profit, position_size）差异过大

    Args:
        rules: 策略规则列表

    Returns:
        冲突检测结果列表
    """
    conflicts: list[ConflictDetectionResult] = []

    # 按规则类型分组
    by_type: dict[str, list[StrategyRule]] = {}
    for rule in rules:
        by_type.setdefault(rule.rule_type, []).append(rule)

    # 检查同类型规则的参数一致性
    for rule_type, type_rules in by_type.items():
        if len(type_rules) < 2:
            continue

        # 1. 检查 action.params 参数
        action_conflicts = _check_action_param_consistency(type_rules)
        conflicts.extend(action_conflicts)

        # 2. 检查 condition 中的数值参数
        condition_conflicts = _check_condition_param_consistency(type_rules)
        conflicts.extend(condition_conflicts)

        # 3. 检查核心风控参数（stop_loss, take_profit）
        risk_conflicts = _check_risk_param_consistency(type_rules)
        conflicts.extend(risk_conflicts)

    return conflicts


def _check_action_param_consistency(rules: list[StrategyRule]) -> list[ConflictDetectionResult]:
    """检查 action.params 参数一致性。"""
    conflicts: list[ConflictDetectionResult] = []

    params = [r.action.get("params", {}) for r in rules]
    if not params:
        return conflicts

    # 收集所有参数
    all_params = set()
    for p in params:
        all_params.update(p.keys())

    for param in all_params:
        values = [p.get(param) for p in params if p.get(param) is not None]
        if len(set(values)) > 1:  # 存在不一致
            evidence = {
                "parameter": param,
                "values": values,
                "source": "action.params",
            }
            conflicts.append(ConflictDetectionResult(
                conflict_type=ConflictType.PARAMETER_MISMATCH,
                severity=_classify_conflict_severity(ConflictType.PARAMETER_MISMATCH, evidence, rules),
                message=f"Action parameter '{param}' inconsistent across {len(rules)} rules: {values}",
                involved_rules=[r.rule_id for r in rules],
                evidence=evidence,
            ))

    return conflicts


def _check_condition_param_consistency(rules: list[StrategyRule]) -> list[ConflictDetectionResult]:
    """检查 condition 中的数值参数一致性。"""
    conflicts: list[ConflictDetectionResult] = []

    # 收集 condition 中的阈值参数
    threshold_params = ["threshold", "threshold_pct", "stop_loss", "take_profit",
                       "volume_ratio", "price_ratio", "holding_period"]

    for param in threshold_params:
        values_by_rule: dict[str, Any] = {}
        for rule in rules:
            cond = rule.condition
            if param in cond and cond[param] is not None:
                values_by_rule[rule.rule_id] = cond[param]

        if len(values_by_rule) < 2:
            continue

        values = list(values_by_rule.values())
        if len(set(values)) > 1:
            evidence = {
                "parameter": param,
                "values": values,
                "source": "condition",
            }
            conflicts.append(ConflictDetectionResult(
                conflict_type=ConflictType.PARAMETER_MISMATCH,
                severity=_classify_conflict_severity(ConflictType.PARAMETER_MISMATCH, evidence, rules),
                message=f"Condition parameter '{param}' inconsistent: {values}",
                involved_rules=list(values_by_rule.keys()),
                evidence=evidence,
            ))

    return conflicts


def _check_risk_param_consistency(rules: list[StrategyRule]) -> list[ConflictDetectionResult]:
    """检查核心风控参数一致性。

    核心风控参数：stop_loss, take_profit
    如果不一致，标记为更高严重程度
    """
    conflicts: list[ConflictDetectionResult] = []

    risk_params = ["stop_loss", "take_profit", "max_position"]

    for param in risk_params:
        values_by_rule: dict[str, Any] = {}
        for rule in rules:
            # 检查 action.params
            action_val = rule.action.get("params", {}).get(param)
            if action_val is not None:
                values_by_rule[rule.rule_id] = ("action", action_val)

            # 检查 condition
            cond_val = rule.condition.get(param)
            if cond_val is not None:
                values_by_rule[rule.rule_id] = ("condition", cond_val)

        if len(values_by_rule) < 2:
            continue

        # 提取纯数值用于比较
        numeric_values = []
        for source, val in values_by_rule.values():
            try:
                numeric_values.append(float(val))
            except (ValueError, TypeError):
                pass

        if len(numeric_values) >= 2 and len(set(numeric_values)) > 1:
            evidence = {
                "parameter": param,
                "values": list(values_by_rule.items()),
                "source": "risk_params",
                "is_risk_param": True,
            }
            conflicts.append(ConflictDetectionResult(
                conflict_type=ConflictType.PARAMETER_MISMATCH,
                severity=_classify_conflict_severity(ConflictType.PARAMETER_MISMATCH, evidence, rules),
                message=f"Risk parameter '{param}' inconsistent across rules",
                involved_rules=list(values_by_rule.keys()),
                evidence=evidence,
            ))

    return conflicts


def _detect_temporal_conflicts(rules: list[StrategyRule]) -> list[ConflictDetectionResult]:
    """检测时序冲突（P3-013）。

    增强版：检测多种时序冲突类型
      - 规则触发时间顺序冲突（exit 时间早于 entry）
      - 持仓时长不合理（exit 触发条件应在 entry 之后）
      - 时间窗口重叠冲突
      - 交易时间与规则不匹配

    Args:
        rules: 策略规则列表

    Returns:
        冲突检测结果列表
    """
    conflicts: list[ConflictDetectionResult] = []

    # 检查 entry 和 exit 规则的时序合理性
    entry_rules = [r for r in rules if r.rule_type == "entry"]
    exit_rules = [r for r in rules if r.rule_type == "exit"]

    for entry_rule in entry_rules:
        for exit_rule in exit_rules:
            temporal_conflict = _check_entry_exit_temporal_conflict(entry_rule, exit_rule)
            if temporal_conflict:
                conflicts.append(temporal_conflict)

    # 检查同一规则内的时间条件冲突
    for rule in rules:
        rule_conflict = _check_rule_internal_temporal_conflict(rule)
        if rule_conflict:
            conflicts.append(rule_conflict)

    return conflicts


def _check_entry_exit_temporal_conflict(
    entry_rule: StrategyRule,
    exit_rule: StrategyRule,
) -> ConflictDetectionResult | None:
    """检查 entry 和 exit 规则之间的时序冲突。

    Args:
        entry_rule: 入场规则
        exit_rule: 出场规则

    Returns:
        ConflictDetectionResult 如果有时序冲突，否则 None
    """
    entry_cond = entry_rule.condition
    exit_cond = exit_rule.condition

    evidence: dict[str, Any] = {
        "entry_rule_id": entry_rule.rule_id,
        "exit_rule_id": exit_rule.rule_id,
        "entry_condition": entry_cond,
        "exit_condition": exit_cond,
    }

    # 1. 检查时间顺序冲突
    entry_time = entry_cond.get("time", "")
    exit_time = exit_cond.get("time", "")

    if entry_time and exit_time:
        if exit_time < entry_time:
            evidence["time_conflict"] = True
            evidence["entry_time"] = entry_time
            evidence["exit_time"] = exit_time
            return ConflictDetectionResult(
                conflict_type=ConflictType.TEMPORAL_CONFLICT,
                severity=_classify_conflict_severity(ConflictType.TEMPORAL_CONFLICT, evidence, [entry_rule, exit_rule]),
                message=f"Exit time {exit_time} is earlier than entry time {entry_time} for rules "
                       f"{entry_rule.rule_id} and {exit_rule.rule_id}",
                involved_rules=[entry_rule.rule_id, exit_rule.rule_id],
                evidence=evidence,
            )

    # 2. 检查持仓时长冲突
    hold_period_conflict = _check_holding_period_conflict(entry_cond, exit_cond)
    if hold_period_conflict:
        evidence["hold_period_conflict"] = True
        evidence["hold_period_details"] = hold_period_conflict
        return ConflictDetectionResult(
            conflict_type=ConflictType.TEMPORAL_CONFLICT,
            severity=_classify_conflict_severity(ConflictType.TEMPORAL_CONFLICT, evidence, [entry_rule, exit_rule]),
            message=f"Holding period conflict detected for rules {entry_rule.rule_id} and {exit_rule.rule_id}",
            involved_rules=[entry_rule.rule_id, exit_rule.rule_id],
            evidence=evidence,
        )

    # 3. 检查时间窗口重叠冲突
    entry_window = entry_cond.get("time_window", {})
    exit_window = exit_cond.get("time_window", {})
    if entry_window and exit_window:
        window_conflict = _check_time_window_overlap(entry_window, exit_window)
        if window_conflict:
            evidence["time_window_conflict"] = True
            evidence["entry_window"] = entry_window
            evidence["exit_window"] = exit_window
            return ConflictDetectionResult(
                conflict_type=ConflictType.TEMPORAL_CONFLICT,
                severity=_classify_conflict_severity(ConflictType.TEMPORAL_CONFLICT, evidence, [entry_rule, exit_rule]),
                message=f"Time window overlap conflict for rules {entry_rule.rule_id} and {exit_rule.rule_id}",
                involved_rules=[entry_rule.rule_id, exit_rule.rule_id],
                evidence=evidence,
            )

    return None


def _check_holding_period_conflict(
    entry_cond: dict[str, Any],
    exit_cond: dict[str, Any],
) -> dict[str, Any] | None:
    """检查持仓时长是否合理。

    冲突情况：
      - exit 规则的 holding_period < entry 规则的 holding_period（应该 exit >= entry）
      - exit 条件的触发时间应该在 entry 条件之后

    Returns:
        冲突详情字典，如果有冲突的话
    """
    entry_hold = entry_cond.get("holding_period")
    exit_hold = exit_cond.get("holding_period")

    # 如果都指定了持仓时长，检查一致性
    if entry_hold is not None and exit_hold is not None:
        try:
            entry_hold_val = float(entry_hold)
            exit_hold_val = float(exit_hold)

            # exit 持仓时长应该 >= entry（更长的入场应该对应更长的出场）
            if exit_hold_val < entry_hold_val * 0.5:
                return {
                    "entry_holding_period": entry_hold_val,
                    "exit_holding_period": exit_hold_val,
                    "violation": "exit_holding_period_too_short",
                }
        except (ValueError, TypeError):
            pass

    # 检查 exit 触发条件是否在 entry 之前
    entry_trigger = entry_cond.get("trigger_after", "")
    exit_trigger = exit_cond.get("trigger_after", "")

    if entry_trigger and exit_trigger:
        # 简化的触发时间检查
        if exit_trigger < entry_trigger:
            return {
                "entry_trigger_after": entry_trigger,
                "exit_trigger_after": exit_trigger,
                "violation": "exit_trigger_before_entry",
            }

    return None


def _check_time_window_overlap(
    window1: dict[str, Any],
    window2: dict[str, Any],
) -> bool:
    """检查两个时间窗口是否冲突。

    冲突定义：两个窗口完全重叠且交易方向相同
    """
    start1 = window1.get("start", "")
    end1 = window1.get("end", "")
    start2 = window2.get("start", "")
    end2 = window2.get("end", "")

    # 检查时间窗口是否完全相同
    if start1 == start2 and end1 == end2:
        # 同向交易在完全相同的时间窗口：可能冲突
        return True

    # 检查是否有交集
    if start1 and end1 and start2 and end2:
        # 假设时间格式可比较
        if start1 <= start2 <= end1 or start1 <= end2 <= end1:
            return True

    return False


def _check_rule_internal_temporal_conflict(rule: StrategyRule) -> ConflictDetectionResult | None:
    """检查单条规则内部的时间条件冲突。

    例如：
      - trigger_after 时间早于规则创建时间
      - time_window 开始时间晚于结束时间
    """
    cond = rule.condition

    # 检查 time_window
    time_window = cond.get("time_window", {})
    if time_window:
        start = time_window.get("start", "")
        end = time_window.get("end", "")
        if start and end and start > end:
            evidence = {
                "rule_id": rule.rule_id,
                "time_window": time_window,
                "violation": "start_after_end",
            }
            return ConflictDetectionResult(
                conflict_type=ConflictType.TEMPORAL_CONFLICT,
                severity=_classify_conflict_severity(ConflictType.TEMPORAL_CONFLICT, evidence, [rule]),
                message=f"Rule {rule.rule_id} has invalid time window: {start} > {end}",
                involved_rules=[rule.rule_id],
                evidence=evidence,
            )

    return None


def _has_temporal_conflict(entry_rule: StrategyRule, exit_rule: StrategyRule) -> bool:
    """判断 entry 和 exit 规则是否存在时序冲突（兼容旧接口）。"""
    result = _check_entry_exit_temporal_conflict(entry_rule, exit_rule)
    return result is not None
