from __future__ import annotations

from src.persona.behavior_rules import load_behavior_rules_preview


def test_load_behavior_rules_preview_returns_grouped_metadata() -> None:
    """行为规则预览应包含可展示的元数据与分组信息。"""
    preview = load_behavior_rules_preview()

    assert preview.schema_version == "v1"
    assert preview.title == "交易行为标签规则"
    assert preview.rule_count > 0
    assert preview.enabled_rule_count == preview.rule_count
    assert preview.category_count >= 1
    assert preview.source_path == "config/rules/behavior_rules.yaml"

    first_rule = preview.rules[0]
    assert first_rule.category
    assert first_rule.priority > 0
    assert first_rule.condition_summary

    category_names = {category.name for category in preview.categories}
    assert "追涨类" in category_names
