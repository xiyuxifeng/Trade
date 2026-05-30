from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import os

import yaml

from src.common.paths import project_root, resolve_project_path

DEFAULT_BEHAVIOR_RULES_PATH = "config/rules/behavior_rules.yaml"

_RULE_OP_SYMBOLS = {
    "gt": ">",
    "ge": "≥",
    "lt": "<",
    "le": "≤",
    "eq": "=",
}


@dataclass
class BehaviorRuleConditionPreview:
    field: str
    op: str
    value: Any
    expression: str


@dataclass
class BehaviorRulePreview:
    id: str
    label: str
    category: str
    priority: int
    enabled: bool
    description: str
    signals: list[str] = field(default_factory=list)
    conditions: list[BehaviorRuleConditionPreview] = field(default_factory=list)
    condition_summary: str = ""


@dataclass
class BehaviorRulesCategorySummary:
    name: str
    rule_count: int
    enabled_rule_count: int


@dataclass
class BehaviorRulesPreview:
    schema_version: str
    title: str
    description: str
    source_path: str
    rule_count: int
    enabled_rule_count: int
    category_count: int
    categories: list[BehaviorRulesCategorySummary]
    rules: list[BehaviorRulePreview]

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def _resolve_source_path(rules_path: str | Path | None = None) -> Path:
    path_value = rules_path or os.environ.get("BEHAVIOR_RULES_PATH", DEFAULT_BEHAVIOR_RULES_PATH)
    return resolve_project_path(path_value)


def _to_relative_path(path: Path) -> str:
    root = project_root()
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _stringify_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _format_condition(condition_dict: dict[str, Any]) -> BehaviorRuleConditionPreview:
    field_name = str(condition_dict.get("field") or "")
    op = str(condition_dict.get("op") or "")
    value = condition_dict.get("value")
    symbol = _RULE_OP_SYMBOLS.get(op, op)
    expression = f"{field_name} {symbol} {_stringify_value(value)}".strip()
    return BehaviorRuleConditionPreview(
        field=field_name,
        op=op,
        value=value,
        expression=expression,
    )


def load_behavior_rules_preview(rules_path: str | Path | None = None) -> BehaviorRulesPreview:
    """加载行为规则文件并转成适合 Web 预览的结构化内容。"""

    path = _resolve_source_path(rules_path)
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if not isinstance(raw, dict):
        raise ValueError("behavior_rules.yaml 顶层必须是 YAML 对象。")

    raw_rules = raw.get("rules", [])
    if not isinstance(raw_rules, list):
        raise ValueError("behavior_rules.yaml 的 rules 字段必须是列表。")

    preview_rules: list[BehaviorRulePreview] = []
    category_stats: dict[str, BehaviorRulesCategorySummary] = {}

    total_rules = len(raw_rules)

    for index, rule_dict in enumerate(raw_rules):
        if not isinstance(rule_dict, dict):
            raise ValueError("behavior_rules.yaml 的每条规则必须是对象。")

        label = str(rule_dict.get("label") or "").strip()
        if not label:
            raise ValueError("behavior_rules.yaml 的规则缺少 label。")

        category = str(rule_dict.get("category") or "未分类").strip() or "未分类"
        enabled = bool(rule_dict.get("enabled", True))

        raw_priority = rule_dict.get("priority")
        if raw_priority is None:
            priority = (total_rules - index) * 10
        else:
            try:
                priority = int(raw_priority)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"规则 {label} 的 priority 必须是整数。") from exc

        raw_conditions = rule_dict.get("conditions", [])
        if not isinstance(raw_conditions, list):
            raise ValueError(f"规则 {label} 的 conditions 必须是列表。")

        conditions = [_format_condition(condition) for condition in raw_conditions]
        condition_summary = " 且 ".join(condition.expression for condition in conditions) if conditions else "无条件"

        raw_signals = rule_dict.get("signals", [])
        if not isinstance(raw_signals, list):
            raise ValueError(f"规则 {label} 的 signals 必须是列表。")

        preview_rules.append(
            BehaviorRulePreview(
                id=str(rule_dict.get("id") or label),
                label=label,
                category=category,
                priority=priority,
                enabled=enabled,
                description=str(rule_dict.get("description") or ""),
                signals=[str(signal) for signal in raw_signals],
                conditions=conditions,
                condition_summary=condition_summary,
            )
        )

        if category not in category_stats:
            category_stats[category] = BehaviorRulesCategorySummary(
                name=category,
                rule_count=0,
                enabled_rule_count=0,
            )
        category_summary = category_stats[category]
        category_summary.rule_count += 1
        if enabled:
            category_summary.enabled_rule_count += 1

    schema_version = str(raw.get("schema_version") or "v1")
    title = str(raw.get("title") or "交易行为标签规则")
    description = str(raw.get("description") or "用于解释单笔交易如何命中行为标签的只读规则集。")

    return BehaviorRulesPreview(
        schema_version=schema_version,
        title=title,
        description=description,
        source_path=_to_relative_path(path),
        rule_count=len(preview_rules),
        enabled_rule_count=sum(1 for item in preview_rules if item.enabled),
        category_count=len(category_stats),
        categories=list(category_stats.values()),
        rules=preview_rules,
    )
