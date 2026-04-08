"""
LLM 抽取结果到 StrategyRule 的转换器。

负责：
  - 将 LLM 输出的 DSL 字典转换为 StrategyRule 对象
  - 批量构建规则
  - 从验证结果中提取有效规则
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.alignment.types import StrategyRule
from src.knowledge.validator import (
    ValidationResult,
    validate_extraction_result,
)


# ---------------------------------------------------------------------------
# 异常定义
# ---------------------------------------------------------------------------


class RuleBuildError(Exception):
    """规则构建失败。"""
    pass


# ---------------------------------------------------------------------------
# 单条规则构建
# ---------------------------------------------------------------------------


def from_llm_extraction(
    llm_output: dict[str, Any],
    source_url: str | None = None,
) -> StrategyRule:
    """从 LLM 抽取结果构建 StrategyRule。

    Args:
        llm_output: LLM 返回的 DSL 字典
        source_url: 来源 URL（可选）

    Returns:
        StrategyRule 对象

    Raises:
        RuleBuildError: 验证失败时抛出
    """
    # 验证输入
    validation_result = validate_extraction_result(llm_output)

    if not validation_result.valid:
        error_messages = [
            f"{e.field}: {e.message}" for e in validation_result.errors
        ]
        raise RuleBuildError(
            f"LLM extraction validation failed: {', '.join(error_messages)}"
        )

    # 生成规则 ID
    rule_id = llm_output.get("rule_id") or str(uuid.uuid4())

    # 构建 StrategyRule
    rule = StrategyRule(
        rule_id=rule_id,
        rule_type=llm_output["rule_type"],
        instrument_focus=llm_output.get("instrument_focus", "mixed"),
        condition=llm_output.get("condition", {}),
        action=llm_output["action"],
        confidence=llm_output.get("confidence", 0.5),
        source_url=source_url,
    )

    return rule


# ---------------------------------------------------------------------------
# 批量规则构建
# ---------------------------------------------------------------------------


@dataclass
class StrategyRuleBuilder:
    """StrategyRule 构建器。

    提供流式构建接口，支持逐步添加字段。
    """
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    rule_type: str | None = None
    instrument_focus: str = "mixed"
    condition: dict[str, Any] = field(default_factory=dict)
    action: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    source_url: str | None = None

    def set_rule_type(self, rule_type: str) -> "StrategyRuleBuilder":
        """设置规则类型。"""
        self.rule_type = rule_type
        return self

    def set_instrument_focus(self, focus: str) -> "StrategyRuleBuilder":
        """设置标的类型。"""
        self.instrument_focus = focus
        return self

    def set_condition(self, condition: dict[str, Any]) -> "StrategyRuleBuilder":
        """设置条件表达式。"""
        self.condition = condition
        return self

    def set_action(self, action: dict[str, Any]) -> "StrategyRuleBuilder":
        """设置动作规格。"""
        self.action = action
        return self

    def set_confidence(self, confidence: float) -> "StrategyRuleBuilder":
        """设置置信度。"""
        self.confidence = confidence
        return self

    def set_source_url(self, url: str) -> "StrategyRuleBuilder":
        """设置来源 URL。"""
        self.source_url = url
        return self

    def build(self) -> StrategyRule:
        """构建 StrategyRule。

        Returns:
            StrategyRule 对象

        Raises:
            RuleBuildError: 必填字段缺失时抛出
        """
        if self.rule_type is None:
            raise RuleBuildError("Missing required field: rule_type")
        if not self.action:
            raise RuleBuildError("Missing required field: action")

        return StrategyRule(
            rule_id=self.rule_id,
            rule_type=self.rule_type,
            instrument_focus=self.instrument_focus,
            condition=self.condition,
            action=self.action,
            confidence=self.confidence,
            source_url=self.source_url,
        )


def build_strategy_rules(
    llm_outputs: list[dict[str, Any]],
    source_url: str | None = None,
) -> tuple[list[StrategyRule], list[tuple[dict[str, Any], str]]]:
    """批量从 LLM 抽取结果构建 StrategyRule 列表。

    Args:
        llm_outputs: LLM 返回的 DSL 字典列表
        source_url: 来源 URL（可选）

    Returns:
        (成功构建的规则列表, 失败项列表)
        失败项为 (原始输入, 错误信息) 元组
    """
    rules: list[StrategyRule] = []
    failures: list[tuple[dict[str, Any], str]] = []

    for llm_output in llm_outputs:
        try:
            rule = from_llm_extraction(llm_output, source_url)
            rules.append(rule)
        except RuleBuildError as e:
            failures.append((llm_output, str(e)))

    return rules, failures


def build_rules_from_validated_results(
    validated_outputs: list[tuple[dict[str, Any], ValidationResult]],
    source_url: str | None = None,
) -> list[StrategyRule]:
    """从已验证的结果批量构建规则。

    适用于已经过验证的 LLM 输出，避免重复验证。

    Args:
        validated_outputs: (LLM 输出, 验证结果) 元组列表
        source_url: 来源 URL（可选）

    Returns:
        StrategyRule 列表（仅包含验证通过的项目）
    """
    rules: list[StrategyRule] = []

    for llm_output, validation_result in validated_outputs:
        if not validation_result.valid:
            continue

        rule_id = llm_output.get("rule_id") or str(uuid.uuid4())
        rule = StrategyRule(
            rule_id=rule_id,
            rule_type=llm_output["rule_type"],
            instrument_focus=llm_output.get("instrument_focus", "mixed"),
            condition=llm_output.get("condition", {}),
            action=llm_output["action"],
            confidence=llm_output.get("confidence", 0.5),
            source_url=source_url,
        )
        rules.append(rule)

    return rules
