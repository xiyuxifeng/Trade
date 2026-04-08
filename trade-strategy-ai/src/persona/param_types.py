"""
参数类型定义与验证 — P4-018。

提供参数类型枚举和验证逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class ParamType(Enum):
    """参数类型枚举。"""
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    STR = "str"
    LIST = "list"
    DICT = "dict"


@dataclass
class ValidationError:
    """验证错误详情。"""
    field: str
    message: str
    value: Any


@dataclass
class ValidationResult:
    """验证结果。"""
    valid: bool
    errors: list[ValidationError]

    @classmethod
    def success(cls) -> "ValidationResult":
        return cls(valid=True, errors=[])

    @classmethod
    def failure(cls, errors: list[ValidationError]) -> "ValidationResult":
        return cls(valid=False, errors=errors)


def validate_type(value: Any, expected_type: ParamType) -> ValidationResult:
    """验证值类型是否匹配。

    Args:
        value: 要验证的值
        expected_type: 期望的参数类型

    Returns:
        ValidationResult
    """
    type_map = {
        ParamType.INT: int,
        ParamType.FLOAT: (int, float),
        ParamType.BOOL: bool,
        ParamType.STR: str,
        ParamType.LIST: list,
        ParamType.DICT: dict,
    }

    expected_python_type = type_map.get(expected_type)
    if expected_python_type is None:
        return ValidationResult.failure([
            ValidationError(field="type", message=f"Unknown param type: {expected_type}", value=expected_type)
        ])

    if not isinstance(value, expected_python_type):
        return ValidationResult.failure([
            ValidationError(
                field="type",
                message=f"Expected {expected_type.value}, got {type(value).__name__}",
                value=value
            )
        ])

    return ValidationResult.success()


def validate_range(value: Any, param_type: ParamType, min_val: float | None, max_val: float | None) -> ValidationResult:
    """验证数值范围。

    Args:
        value: 要验证的值
        param_type: 参数类型
        min_val: 最小值
        max_val: 最大值

    Returns:
        ValidationResult
    """
    if param_type not in (ParamType.INT, ParamType.FLOAT):
        return ValidationResult.success()

    try:
        num_value = float(value)
    except (TypeError, ValueError):
        return ValidationResult.failure([
            ValidationError(field="value", message=f"Cannot convert {value} to number", value=value)
        ])

    errors = []
    if min_val is not None and num_value < min_val:
        errors.append(ValidationError(
            field="min",
            message=f"Value {value} is less than minimum {min_val}",
            value=value
        ))
    if max_val is not None and num_value > max_val:
        errors.append(ValidationError(
            field="max",
            message=f"Value {value} is greater than maximum {max_val}",
            value=value
        ))

    if errors:
        return ValidationResult.failure(errors)
    return ValidationResult.success()


def validate_choices(value: Any, choices: list | None) -> ValidationResult:
    """验证枚举选择。

    Args:
        value: 要验证的值
        choices: 允许的值列表

    Returns:
        ValidationResult
    """
    if choices is None:
        return ValidationResult.success()

    if value not in choices:
        return ValidationResult.failure([
            ValidationError(
                field="choices",
                message=f"Value {value!r} not in allowed choices: {choices}",
                value=value
            )
        ])

    return ValidationResult.success()


def validate_not_null(value: Any) -> ValidationResult:
    """验证非空（None）。

    Args:
        value: 要验证的值

    Returns:
        ValidationResult
    """
    if value is None:
        return ValidationResult.failure([
            ValidationError(field="value", message="Value cannot be null", value=value)
        ])
    return ValidationResult.success()


def validate_param(
    value: Any,
    param_type: ParamType,
    min_val: float | None = None,
    max_val: float | None = None,
    choices: list | None = None,
    allow_null: bool = False,
) -> ValidationResult:
    """综合参数验证。

    Args:
        value: 要验证的值
        param_type: 参数类型
        min_val: 最小值（数值类型）
        max_val: 最大值（数值类型）
        choices: 枚举选项
        allow_null: 是否允许 null

    Returns:
        ValidationResult
    """
    # 先检查 null
    if value is None:
        if allow_null:
            return ValidationResult.success()
        return ValidationResult.failure([
            ValidationError(field="value", message="Value cannot be null", value=value)
        ])

    # 类型检查
    type_result = validate_type(value, param_type)
    if not type_result.valid:
        return type_result

    # 范围检查
    range_result = validate_range(value, param_type, min_val, max_val)
    if not range_result.valid:
        return range_result

    # 枚举检查
    choices_result = validate_choices(value, choices)
    if not choices_result.valid:
        return choices_result

    return ValidationResult.success()
