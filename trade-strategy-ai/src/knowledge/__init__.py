"""
Knowledge Agent 适配层 — LLM 抽取结果与现有代码的桥梁。

当 LLM API 可用时，只需要实现 extractor.py 中的抽取逻辑，
本模块提供：
  - validator.py: LLM 输出 DSL 验证
  - rule_builder.py: StrategyRule 对象构造
"""

from __future__ import annotations

from src.knowledge.validator import (
    ValidationError,
    ValidationResult,
    validate_extraction_result,
)

from src.knowledge.rule_builder import (
    RuleBuildError,
    StrategyRuleBuilder,
    build_rules_from_validated_results,
    build_strategy_rules,
    from_llm_extraction,
)

__all__ = [
    "ValidationError",
    "ValidationResult",
    "validate_extraction_result",
    "RuleBuildError",
    "StrategyRuleBuilder",
    "build_strategy_rules",
    "build_rules_from_validated_results",
    "from_llm_extraction",
]
