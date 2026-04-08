"""
LLM 抽取结果验证器 — 验证 LLM 输出的 DSL 是否符合 Schema 规范。

验证规则：
  1. 必填字段存在
  2. 字段类型正确
  3. rule_type 在允许值内
  4. condition 表达式结构正确
  5. confidence 在 [0, 1] 范围内
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.persona.schemas import ClaimKey, InstrumentFocus


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

class ValidationError:
    """验证错误。"""
    def __init__(self, field: str, message: str, severity: str = "error") -> None:
        self.field = field
        self.message = message
        self.severity = severity  # error, warning, info

    def __repr__(self) -> str:
        return f"ValidationError(field={self.field!r}, message={self.message!r}, severity={self.severity!r})"


@dataclass
class ValidationResult:
    """验证结果。"""
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    def add_error(self, field: str, message: str) -> None:
        self.errors.append(ValidationError(field=field, message=message, severity="error"))
        self.valid = False

    def add_warning(self, field: str, message: str) -> None:
        self.warnings.append(ValidationError(field=field, message=message, severity="warning"))


# ---------------------------------------------------------------------------
# 验证规则
# ---------------------------------------------------------------------------

# 允许的 rule_type 值
ALLOWED_RULE_TYPES = {"entry", "exit", "filter", "sizing", "risk"}

# 允许的 claim_key 值
ALLOWED_CLAIM_KEYS = {ck.value for ck in ClaimKey}

# 允许的 instrument_focus 值
ALLOWED_INSTRUMENT_FOCUS = {if_.value for if_ in InstrumentFocus}


def validate_extraction_result(llm_output: dict[str, Any]) -> ValidationResult:
    """验证 LLM 抽取结果。

    Args:
        llm_output: LLM 返回的原始 JSON

    Returns:
        ValidationResult
    """
    result = ValidationResult(valid=True)

    # 1. 检查顶层字段
    _validate_top_level(llm_output, result)

    # 2. 检查 claim_key
    _validate_claim_key(llm_output.get("claim_key"), result)

    # 3. 检查 rule_type
    _validate_rule_type(llm_output.get("rule_type"), result)

    # 4. 检查 instrument_focus
    _validate_instrument_focus(llm_output.get("instrument_focus"), result)

    # 5. 检查 condition
    _validate_condition(llm_output.get("condition"), result)

    # 6. 检查 action
    _validate_action(llm_output.get("action"), result)

    # 7. 检查 confidence
    _validate_confidence(llm_output.get("confidence"), result)

    return result


def _validate_top_level(data: dict[str, Any], result: ValidationResult) -> None:
    """验证顶层字段。"""
    required_fields = ["claim_key", "rule_type", "action"]
    for field_name in required_fields:
        if field_name not in data:
            result.add_error(field_name, f"Missing required field: {field_name}")
        elif data[field_name] is None:
            result.add_error(field_name, f"Field cannot be None: {field_name}")


def _validate_claim_key(claim_key: Any, result: ValidationResult) -> None:
    """验证 claim_key。"""
    if claim_key is None:
        return  # 已在顶层检查

    if not isinstance(claim_key, str):
        result.add_error("claim_key", f"Must be string, got {type(claim_key).__name__}")
        return

    if claim_key not in ALLOWED_CLAIM_KEYS:
        result.add_warning("claim_key", f"Unknown claim_key: {claim_key}")


def _validate_rule_type(rule_type: Any, result: ValidationResult) -> None:
    """验证 rule_type。"""
    if rule_type is None:
        return  # 已在顶层检查

    if not isinstance(rule_type, str):
        result.add_error("rule_type", f"Must be string, got {type(rule_type).__name__}")
        return

    if rule_type not in ALLOWED_RULE_TYPES:
        result.add_error("rule_type", f"Invalid rule_type: {rule_type}. Must be one of {ALLOWED_RULE_TYPES}")


def _validate_instrument_focus(focus: Any, result: ValidationResult) -> None:
    """验证 instrument_focus。"""
    if focus is None:
        return  # 有默认值

    if not isinstance(focus, str):
        result.add_error("instrument_focus", f"Must be string, got {type(focus).__name__}")
        return

    if focus not in ALLOWED_INSTRUMENT_FOCUS:
        result.add_warning("instrument_focus", f"Unknown instrument_focus: {focus}")


def _validate_condition(condition: Any, result: ValidationResult) -> None:
    """验证 condition 表达式。"""
    if condition is None:
        return  # 可选

    if not isinstance(condition, dict):
        result.add_error("condition", f"Must be dict, got {type(condition).__name__}")
        return

    # 检查常见的 condition 结构
    for key, value in condition.items():
        if not isinstance(key, str):
            result.add_warning("condition", f"Condition key should be string: {key}")


def _validate_action(action: Any, result: ValidationResult) -> None:
    """验证 action。"""
    if action is None:
        result.add_error("action", "Missing required field: action")
        return

    if not isinstance(action, dict):
        result.add_error("action", f"Must be dict, got {type(action).__name__}")
        return

    # action.type 是推荐的
    if "type" not in action:
        result.add_warning("action.type", "Missing recommended field: action.type")


def _validate_confidence(confidence: Any, result: ValidationResult) -> None:
    """验证 confidence。"""
    if confidence is None:
        return  # 可选

    if not isinstance(confidence, (int, float)):
        result.add_error("confidence", f"Must be number, got {type(confidence).__name__}")
        return

    if not (0.0 <= confidence <= 1.0):
        result.add_error("confidence", f"Must be in [0, 1], got {confidence}")


# ---------------------------------------------------------------------------
# 批量验证
# ---------------------------------------------------------------------------

def validate_batch_results(
    llm_outputs: list[dict[str, Any]],
) -> list[ValidationResult]:
    """批量验证多个 LLM 抽取结果。

    Args:
        llm_outputs: LLM 返回的 JSON 列表

    Returns:
        ValidationResult 列表
    """
    return [validate_extraction_result(output) for output in llm_outputs]


def summarize_validation_results(results: list[ValidationResult]) -> dict[str, Any]:
    """汇总验证结果。

    Args:
        results: ValidationResult 列表

    Returns:
        汇总统计字典
    """
    total = len(results)
    valid_count = sum(1 for r in results if r.valid)
    error_count = sum(len(r.errors) for r in results)
    warning_count = sum(len(r.warnings) for r in results)

    # 按字段统计错误
    field_errors: dict[str, int] = {}
    for r in results:
        for e in r.errors:
            field_errors[e.field] = field_errors.get(e.field, 0) + 1

    return {
        "total": total,
        "valid": valid_count,
        "invalid": total - valid_count,
        "valid_rate": valid_count / total if total > 0 else 0.0,
        "total_errors": error_count,
        "total_warnings": warning_count,
        "errors_by_field": field_errors,
    }
