"""
对齐报告生成器 — P3-018, P3-020。

生成文本格式的对齐分析报告，包括：
  - P3-018: 生成对齐报告（文本格式）
  - P3-020: 生成冲突清单和优化建议
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.alignment.types import (
    AlignmentReport,
    ConflictDetection,
    ConflictDetectionResult,
    ConflictType,
    ConfidenceScore,
    RuleMatchScore,
    StrategyRule,
    TradeRecord,
)
from src.alignment.scoring import (
    DetailedConfidenceScore,
    detailed_confidence_scoring,
)


# ---------------------------------------------------------------------------
# P3-018: 文本对齐报告生成
# ---------------------------------------------------------------------------

@dataclass
class AlignmentReportSection:
    """报告章节。"""
    title: str
    content: str
    level: int = 1  # 1: 一级标题, 2: 二级标题


def generate_text_report(
    trader_id: str,
    rules: list[StrategyRule],
    trades: list[TradeRecord] | None = None,
    rule_match_scores: list[RuleMatchScore] | None = None,
    conflicts: ConflictDetection | None = None,
    confidence_score: ConfidenceScore | None = None,
    detailed_score: DetailedConfidenceScore | None = None,
    include_suggestions: bool = True,
    **kwargs,
) -> str:
    """生成文本格式的对齐分析报告（P3-018）。

    报告结构：
      1. 执行摘要
      2. 规则匹配分析
      3. 行为适配度分析
      4. 冲突检测结果
      5. 综合可信度评分
      6. 优化建议（可选）

    Args:
        trader_id: 交易员 ID
        rules: 策略规则列表
        trades: 交易记录列表
        rule_match_scores: 规则匹配评分列表
        conflicts: 冲突检测结果
        confidence_score: 简单可信度评分
        detailed_score: 详细可信度评分
        include_suggestions: 是否包含优化建议

    Returns:
        文本格式报告
    """
    lines: list[str] = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 标题
    lines.append("=" * 70)
    lines.append(f"对齐分析报告 - {trader_id}")
    lines.append(f"生成时间: {timestamp}")
    lines.append("=" * 70)
    lines.append("")

    # 1. 执行摘要
    lines.extend(_generate_executive_summary(
        trader_id, rules, trades, conflicts, detailed_score
    ))
    lines.append("")

    # 2. 规则匹配分析
    if rule_match_scores:
        lines.extend(_generate_rule_match_section(rule_match_scores, rules))
        lines.append("")

    # 3. 冲突检测结果
    if conflicts:
        lines.extend(_generate_conflict_section(conflicts))
        lines.append("")

    # 4. 综合可信度评分
    lines.extend(_generate_confidence_section(detailed_score, confidence_score))
    lines.append("")

    # 5. 优化建议
    if include_suggestions and conflicts:
        lines.extend(_generate_suggestions_section(conflicts, rules))
        lines.append("")

    # 页脚
    lines.append("=" * 70)
    lines.append("报告结束")
    lines.append("=" * 70)

    return "\n".join(lines)


def _generate_executive_summary(
    trader_id: str,
    rules: list[StrategyRule],
    trades: list[TradeRecord] | None,
    conflicts: ConflictDetection | None,
    detailed_score: DetailedConfidenceScore | None,
) -> list[str]:
    """生成执行摘要章节。"""
    lines = []
    lines.append("## 执行摘要")
    lines.append("-" * 40)

    # 规则统计
    lines.append(f"分析规则数: {len(rules)}")
    if trades:
        lines.append(f"分析交易数: {len(trades)}")

    # 冲突统计
    if conflicts:
        lines.append(f"检测到冲突数: {conflicts.total_conflicts}")
        if conflicts.by_severity:
            severities = ", ".join(
                f"{k}: {v}" for k, v in conflicts.by_severity.items()
            )
            lines.append(f"  严重程度分布: {severities}")
        if conflicts.by_type:
            types = ", ".join(
                f"{k.split('_')[-1]}: {v}" for k, v in conflicts.by_type.items()
            )
            lines.append(f"  类型分布: {types}")

    # 综合评分
    if detailed_score:
        lines.append(f"综合可信度评分: {detailed_score.overall_score:.2%} ({detailed_score.grade})")
        lines.append(f"评分等级: {detailed_score.grade_label}")

    return lines


def _generate_rule_match_section(
    rule_match_scores: list[RuleMatchScore],
    rules: list[StrategyRule],
) -> list[str]:
    """生成规则匹配章节。"""
    lines = []
    lines.append("## 规则匹配分析")
    lines.append("-" * 40)

    # 总体统计
    total_match_rate = 0.0
    if rule_match_scores:
        total_match_rate = sum(s.match_rate for s in rule_match_scores) / len(rule_match_scores)
    lines.append(f"总体匹配率: {total_match_rate:.2%}")

    # 按规则类型分组
    by_type: dict[str, list[RuleMatchScore]] = {}
    for score in rule_match_scores:
        rule = next((r for r in rules if r.rule_id == score.rule_id), None)
        if rule:
            by_type.setdefault(rule.rule_type, []).append(score)

    for rule_type, scores in by_type.items():
        lines.append(f"\n### {rule_type.upper()} 规则")
        avg_rate = sum(s.match_rate for s in scores) / len(scores)
        lines.append(f"平均匹配率: {avg_rate:.2%}")

        for score in scores[:5]:  # 最多显示 5 条
            status = "✓" if score.match_rate >= 0.5 else "✗"
            lines.append(f"  {status} {score.rule_id}: {score.match_rate:.2%} "
                        f"({score.matched_trades}/{score.total_trades})")

        if len(scores) > 5:
            lines.append(f"  ... 还有 {len(scores) - 5} 条规则")

    return lines


def _generate_conflict_section(conflicts: ConflictDetection) -> list[str]:
    """生成冲突检测章节。"""
    lines = []
    lines.append("## 冲突检测结果")
    lines.append("-" * 40)

    if conflicts.total_conflicts == 0:
        lines.append("未检测到冲突 ✓")
        return lines

    lines.append(f"共检测到 {conflicts.total_conflicts} 个冲突")
    lines.append("")

    # 按严重程度分组显示
    severity_order = ["critical", "major", "minor"]
    for severity in severity_order:
        severity_conflicts = [
            c for c in conflicts.conflicts if c.severity == severity
        ]
        if not severity_conflicts:
            continue

        icon = "🔴" if severity == "critical" else "🟡" if severity == "major" else "🟢"
        lines.append(f"### {icon} {severity.upper()} ({len(severity_conflicts)} 个)")

        for conflict in severity_conflicts[:10]:  # 最多显示 10 个
            lines.append(f"\n**{conflict.conflict_type.value}**")
            lines.append(f"  规则: {', '.join(conflict.involved_rules)}")
            lines.append(f"  消息: {conflict.message}")
            if conflict.evidence:
                evidence_str = _format_evidence(conflict.evidence)
                lines.append(f"  证据: {evidence_str}")

        if len(severity_conflicts) > 10:
            lines.append(f"\n  ... 还有 {len(severity_conflicts) - 10} 个冲突")

    return lines


def _format_evidence(evidence: dict[str, Any]) -> str:
    """格式化证据信息。"""
    if not evidence:
        return "-"

    parts = []
    for key, value in evidence.items():
        if key in ("rule1_condition", "rule2_condition", "condition",
                   "entry_condition", "exit_condition"):
            parts.append(f"{key}: {value}")
        elif key in ("overlap_score", "actual_match_rate", "expected_match_rate"):
            try:
                parts.append(f"{key}: {float(value):.2%}")
            except (ValueError, TypeError):
                parts.append(f"{key}: {value}")
        elif isinstance(value, (int, float)):
            parts.append(f"{key}: {value}")
        else:
            parts.append(f"{key}: {value}")

    return "; ".join(parts[:3])  # 最多显示 3 个证据项


def _generate_confidence_section(
    detailed_score: DetailedConfidenceScore | None,
    simple_score: ConfidenceScore | None,
) -> list[str]:
    """生成可信度评分章节。"""
    lines = []
    lines.append("## 综合可信度评分")
    lines.append("-" * 40)

    if detailed_score:
        lines.append(f"**综合评分: {detailed_score.overall_score:.2%} ({detailed_score.grade})**")
        lines.append(f"评分等级: {detailed_score.grade_label}")
        lines.append("")

        lines.append("### 各维度评分")
        for dim in sorted(detailed_score.dimensions, key=lambda x: x.weight, reverse=True):
            bar = _make_score_bar(dim.score)
            lines.append(f"  {dim.name:20s} {bar} {dim.score:.2%} (权重: {dim.weight:.0%})")

        lines.append("")
        lines.append("### 评分明细")
        for key, value in detailed_score.score_breakdown.items():
            if key in ("rule_match", "rule_accuracy", "behavior_fit", "coverage"):
                lines.append(f"  {key:20s}: {value:.2%}")
            elif key == "conflict_penalty":
                lines.append(f"  {key:20s}: {value:.2f}")
            else:
                lines.append(f"  {key:20s}: {value}")

    elif simple_score:
        lines.append(f"综合评分: {simple_score.overall_score:.2%}")
        lines.append("")
        lines.append("评分明细:")
        lines.append(f"  规则匹配度: {simple_score.rule_match_score:.2%}")
        lines.append(f"  行为适配度: {simple_score.behavior_fit_score:.2%}")
        lines.append(f"  冲突扣分: {simple_score.conflict_penalty:.2f}")

    else:
        lines.append("无可用评分数据")

    return lines


def _make_score_bar(score: float, width: int = 20) -> str:
    """生成评分条形图。"""
    filled = int(score * width)
    empty = width - filled
    return "[" + "█" * filled + "░" * empty + "]"


def _generate_suggestions_section(
    conflicts: ConflictDetection,
    rules: list[StrategyRule],
) -> list[str]:
    """生成优化建议章节（P3-020）。"""
    lines = []
    lines.append("## 优化建议")
    lines.append("-" * 40)

    suggestions = generate_optimization_suggestions(conflicts, rules)

    if not suggestions:
        lines.append("暂无优化建议，规则体系运行良好 ✓")
        return lines

    for i, suggestion in enumerate(suggestions, 1):
        priority_icon = "🔴" if suggestion["priority"] == "high" else \
                        "🟡" if suggestion["priority"] == "medium" else "🟢"
        lines.append(f"\n### {priority_icon} 建议 {i}: {suggestion['title']}")
        lines.append(f"**问题**: {suggestion['problem']}")
        lines.append(f"**建议**: {suggestion['action']}")
        if suggestion.get("expected_improvement"):
            lines.append(f"**预期改善**: {suggestion['expected_improvement']}")

    return lines


# ---------------------------------------------------------------------------
# P3-020: 冲突清单和优化建议生成
# ---------------------------------------------------------------------------

@dataclass
class OptimizationSuggestion:
    """优化建议。"""
    title: str
    problem: str
    action: str
    priority: str  # high, medium, low
    expected_improvement: str | None = None
    related_rules: list[str] | None = None
    conflict_type: str | None = None


def generate_optimization_suggestions(
    conflicts: ConflictDetection,
    rules: list[StrategyRule] | None = None,
) -> list[dict[str, Any]]:
    """生成优化建议列表（P3-020）。

    基于冲突检测结果生成可操作的优化建议。

    Args:
        conflicts: 冲突检测结果
        rules: 策略规则列表（可选，用于关联建议）

    Returns:
        优化建议列表
    """
    suggestions: list[dict[str, Any]] = []

    # 按类型分析冲突并生成建议
    for conflict in conflicts.conflicts:
        suggestion = _analyze_conflict_for_suggestion(conflict, rules)
        if suggestion:
            suggestions.append(suggestion)

    # 排序：按优先级（high > medium > low）
    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda x: priority_order.get(x["priority"], 2))

    return suggestions


def _analyze_conflict_for_suggestion(
    conflict: ConflictDetectionResult,
    rules: list[StrategyRule] | None,
) -> dict[str, Any] | None:
    """分析单个冲突并生成建议。"""
    conflict_type = conflict.conflict_type
    severity = conflict.severity

    # 规则矛盾建议
    if conflict_type == ConflictType.RULE_CONTRADICTION:
        return _suggestion_for_rule_contradiction(conflict, severity)

    # 规则重叠建议
    if conflict_type == ConflictType.RULE_OVERLAP:
        return _suggestion_for_rule_overlap(conflict, severity)

    # 行为偏离建议
    if conflict_type == ConflictType.BEHAVIOR_DEVIATION:
        return _suggestion_for_behavior_deviation(conflict, severity)

    # 参数不一致建议
    if conflict_type == ConflictType.PARAMETER_MISMATCH:
        return _suggestion_for_parameter_mismatch(conflict, severity)

    # 时序冲突建议
    if conflict_type == ConflictType.TEMPORAL_CONFLICT:
        return _suggestion_for_temporal_conflict(conflict, severity)

    return None


def _suggestion_for_rule_contradiction(
    conflict: ConflictDetectionResult,
    severity: str,
) -> dict[str, Any]:
    """为规则矛盾生成建议。"""
    involved = conflict.involved_rules
    evidence = conflict.evidence

    # 检查是否是操作符冲突
    cond1 = evidence.get("rule1_condition", {})
    cond2 = evidence.get("rule2_condition", {})
    operator_conflict = (
        "operator" in cond1 and "operator" in cond2 and
        {cond1.get("operator"), cond2.get("operator")} & {">", "<", ">=", "<="}
    )

    if operator_conflict:
        return {
            "title": "规则条件矛盾",
            "problem": f"规则 {', '.join(involved)} 存在相反的条件判断，可能导致执行歧义",
            "action": "明确规则的适用条件，建议使用明确的阈值区间而非相反的操作符",
            "priority": "high" if severity == "critical" else "medium",
            "expected_improvement": "消除执行歧义，提高规则可预测性",
            "related_rules": involved,
            "conflict_type": conflict.conflict_type.value,
        }

    return {
        "title": "规则逻辑冲突",
        "problem": f"规则 {', '.join(involved)} 存在逻辑矛盾",
        "action": "检查规则定义，确保同类型规则的逻辑一致性",
        "priority": "high" if severity == "critical" else "medium",
        "expected_improvement": "提高规则体系的逻辑一致性",
        "related_rules": involved,
        "conflict_type": conflict.conflict_type.value,
    }


def _suggestion_for_rule_overlap(
    conflict: ConflictDetectionResult,
    severity: str,
) -> dict[str, Any]:
    """为规则重叠生成建议。"""
    involved = conflict.involved_rules
    overlap_score = conflict.evidence.get("overlap_score", 0.0)

    if overlap_score > 0.95:
        action = "考虑合并这两条规则，避免重复执行同一逻辑"
    else:
        action = "检查这两条规则的触发条件是否真的需要同时存在，或考虑合并"

    return {
        "title": "规则高度重叠",
        "problem": f"规则 {', '.join(involved)} 存在 {overlap_score:.0%} 的重叠",
        "action": action,
        "priority": "low",
        "expected_improvement": "简化规则体系，减少冗余",
        "related_rules": involved,
        "conflict_type": conflict.conflict_type.value,
    }


def _suggestion_for_behavior_deviation(
    conflict: ConflictDetectionResult,
    severity: str,
) -> dict[str, Any]:
    """为行为偏离生成建议。"""
    involved = conflict.involved_rules
    evidence = conflict.evidence
    actual_rate = evidence.get("actual_match_rate", 0.0)
    expected_rate = evidence.get("expected_match_rate", 0.0)

    return {
        "title": "行为偏离规则",
        "problem": f"规则声称的匹配率 {expected_rate:.0%} 与实际 {actual_rate:.0%} 存在显著差异",
        "action": "重新评估规则的适用条件，或调整规则以更准确反映实际交易行为",
        "priority": "high" if severity == "critical" else "medium",
        "expected_improvement": "提高规则与实际行为的一致性",
        "related_rules": involved,
        "conflict_type": conflict.conflict_type.value,
    }


def _suggestion_for_parameter_mismatch(
    conflict: ConflictDetectionResult,
    severity: str,
) -> dict[str, Any]:
    """为参数不一致生成建议。"""
    involved = conflict.involved_rules
    evidence = conflict.evidence
    param = evidence.get("parameter", "unknown")
    values = evidence.get("values", [])

    critical_params = {"stop_loss", "take_profit", "position_size", "threshold", "threshold_pct"}
    is_critical = param in critical_params

    return {
        "title": f"参数 '{param}' 设置不一致",
        "problem": f"同类型规则中参数 '{param}' 的值不一致: {values}",
        "action": f"统一 '{param}' 的设置，建议使用一致的默认值或明确区分不同场景",
        "priority": "high" if is_critical and severity in ("critical", "major") else "medium",
        "expected_improvement": "提高风控参数的一致性和可预测性",
        "related_rules": involved,
        "conflict_type": conflict.conflict_type.value,
    }


def _suggestion_for_temporal_conflict(
    conflict: ConflictDetectionResult,
    severity: str,
) -> dict[str, Any]:
    """为时序冲突生成建议。"""
    involved = conflict.involved_rules
    evidence = conflict.evidence

    entry_time = evidence.get("entry_condition", {}).get("time", "N/A")
    exit_time = evidence.get("exit_condition", {}).get("time", "N/A")

    return {
        "title": "交易时序冲突",
        "problem": f"入场时间 {entry_time} 晚于出场时间 {exit_time}，违反基本时序逻辑",
        "action": "重新检查并修正规则的时序条件，确保出场触发在入场触发之后",
        "priority": "high",
        "expected_improvement": "消除无法执行的规则冲突",
        "related_rules": involved,
        "conflict_type": conflict.conflict_type.value,
    }


def generate_conflict_inventory(
    conflicts: ConflictDetection,
) -> str:
    """生成冲突清单文本（P3-020）。

    Args:
        conflicts: 冲突检测结果

    Returns:
        冲突清单文本
    """
    lines = []
    lines.append("=" * 60)
    lines.append("冲突清单")
    lines.append("=" * 60)
    lines.append("")

    if conflicts.total_conflicts == 0:
        lines.append("✓ 未检测到冲突")
        return "\n".join(lines)

    lines.append(f"总计: {conflicts.total_conflicts} 个冲突")
    lines.append("")

    # 按类型汇总
    lines.append("### 按类型汇总")
    for conflict_type, count in conflicts.by_type.items():
        lines.append(f"  - {conflict_type}: {count}")
    lines.append("")

    # 按严重程度汇总
    lines.append("### 按严重程度汇总")
    for severity, count in conflicts.by_severity.items():
        icon = "🔴" if severity == "critical" else "🟡" if severity == "major" else "🟢"
        lines.append(f"  - {icon} {severity}: {count}")
    lines.append("")

    # 详细清单
    lines.append("### 详细清单")
    for i, conflict in enumerate(conflicts.conflicts, 1):
        lines.append(f"\n{i}. [{conflict.severity.upper()}] {conflict.conflict_type.value}")
        lines.append(f"   涉及规则: {', '.join(conflict.involved_rules)}")
        lines.append(f"   描述: {conflict.message}")
        if conflict.involved_trades:
            lines.append(f"   涉及交易: {', '.join(conflict.involved_trades[:3])}")
            if len(conflict.involved_trades) > 3:
                lines.append(f"            ... 共 {len(conflict.involved_trades)} 笔")

    return "\n".join(lines)
