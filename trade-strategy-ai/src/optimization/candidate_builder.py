"""S7-003: 候选版本构建器（文件链路）。

将 S7-002 的 RuleAdjustment[] 映射为修改后的 rules_snapshot，
生成候选版本（draft，candidate 类型），不写 DB。

ref: docs/superpowers/plans/2026-04-28-stage7-s7-003-plan.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from src.strategy_library.schemas import (
    StrategyAdjustment,
    StrategyRecommendation,
    StrategyVersion,
    StrategyVersionStatus,
    StrategyVersionType,
)

# RuleAdjustment.current_status → rules_snapshot 操作类型
_OPERATION_MAP: dict[str, str] = {
    "hit_rate_too_low_and_return_negative": "delete_rule",
    "high_hit_rate_but_negative_return": "review_stop_loss",
    "missed_opportunity": "upgrade_rule",
    "missing_snapshot": "check_snapshot",
    "programmable_but_rarely_hit": "delete_rule",
}


@dataclass
class CandidateBuildInput:
    """候选版本构建输入。"""
    trader_id: str
    strategy_date: date
    parent_version_id: str
    parent_rules_snapshot: list[dict]
    adjustments: list[RuleAdjustment]
    recommendations: list[StrategyRecommendation] = field(default_factory=list)


@dataclass
class CandidateBuildResult:
    """候选版本构建结果。"""
    version: StrategyVersion
    deleted_rules: list[str]
    modified_rules: list[str]
    kept_rules: list[str]


def _build_rules_snapshot(
    parent_rules: list[dict],
    adjustments: list[RuleAdjustment],
) -> tuple[list[dict], list[str], list[str], list[str]]:
    """根据 RuleAdjustment 修改 rules_snapshot。

    Returns:
        (new_rules, deleted_rule_ids, modified_rule_ids, kept_rule_ids)
    """
    # 构建 rule_id → adjustment 映射
    adjustment_map: dict[str, RuleAdjustment] = {
        adj.rule_id: adj for adj in adjustments
    }

    new_rules: list[dict] = []
    deleted: list[str] = []
    modified: list[str] = []
    kept: list[str] = []

    for rule in parent_rules:
        rule_id = rule.get("rule_id", "")
        adjustment = adjustment_map.get(rule_id)

        if adjustment is None:
            # 无对应调整，保留原规则
            new_rules.append(rule)
            kept.append(rule_id)
            continue

        op = _OPERATION_MAP.get(adjustment.current_status, "keep")

        if op == "delete_rule":
            # 删除规则
            deleted.append(rule_id)
            # 不加入 new_rules

        elif op == "review_stop_loss":
            # 复核止盈止损：修改 action 参数
            modified_rule = dict(rule)
            current_action = modified_rule.get("action", {})
            if isinstance(current_action, dict):
                adjusted_fields: dict[str, dict[str, float]] = {}
                for key in ("stop_loss", "stop_loss_pct", "stop_loss_price"):
                    value = current_action.get(key)
                    if isinstance(value, (int, float)) and value > 0:
                        new_value = float(value) * 0.9
                        current_action[key] = new_value
                        adjusted_fields[key] = {"from": float(value), "to": new_value}
                # 在原有 action 基础上标记需要复核
                modified_rule["action"] = {
                    **current_action,
                    "_review_required": True,
                    "_review_reason": adjustment.suggestion,
                    "_confidence": adjustment.confidence,
                    "_review_adjustment": adjusted_fields,
                }
            else:
                modified_rule["action"] = {
                    "_review_required": True,
                    "_review_reason": adjustment.suggestion,
                    "_confidence": adjustment.confidence,
                    "_review_adjustment": {},
                }
            new_rules.append(modified_rule)
            modified.append(rule_id)

        elif op == "upgrade_rule":
            # 升级程序化：标记 programmable=True
            modified_rule = dict(rule)
            modified_rule["programmable"] = True
            modified_rule["_upgrade_note"] = adjustment.suggestion
            new_rules.append(modified_rule)
            modified.append(rule_id)

        elif op == "check_snapshot":
            # 检查快照：保留原规则，附加 note
            modified_rule = dict(rule)
            existing_notes = modified_rule.get("_notes", [])
            if isinstance(existing_notes, str):
                existing_notes = [existing_notes]
            modified_rule["_notes"] = existing_notes + [
                f"[check_snapshot] {adjustment.suggestion}"
            ]
            new_rules.append(modified_rule)
            kept.append(rule_id)

        else:
            # 默认保留
            new_rules.append(rule)
            kept.append(rule_id)

    return new_rules, deleted, modified, kept


def build_candidate_version(input: CandidateBuildInput) -> CandidateBuildResult:
    """根据 RuleAdjustment 构建候选版本（文件链路）。

    不写 DB，返回 StrategyVersion dataclass，可序列化到 JSON。

    Args:
        input: 候选版本构建输入

    Returns:
        CandidateBuildResult，包含候选版本和操作摘要
    """
    new_rules, deleted, modified, kept = _build_rules_snapshot(
        input.parent_rules_snapshot,
        input.adjustments,
    )

    # 生成 notes
    notes_lines = ["候选版本优化建议："]
    for adj in input.adjustments:
        op = _OPERATION_MAP.get(adj.current_status, "keep")
        notes_lines.append(
            f"- [{adj.rule_id}] {adj.current_status} → {op}: {adj.suggestion} "
            f"(confidence={adj.confidence:.2f})"
        )
    notes = "\n".join(notes_lines)

    # 生成 version_id
    parent_short = input.parent_version_id[:8] if input.parent_version_id else "none"
    version_id = (
        f"{input.trader_id}_{input.strategy_date.isoformat()}_"
        f"candidate_{parent_short}"
    )

    version = StrategyVersion(
        version_id=version_id,
        trader_id=input.trader_id,
        strategy_date=input.strategy_date,
        status=StrategyVersionStatus.draft,
        version_type=StrategyVersionType.candidate,
        parent_version_id=input.parent_version_id,
        recommendations=input.recommendations,
        source_article_ids=[],
        evidence_refs=[],
        notes=notes,
        released_at=None,
        rules_snapshot=new_rules,
    )

    return CandidateBuildResult(
        version=version,
        deleted_rules=deleted,
        modified_rules=modified,
        kept_rules=kept,
    )
