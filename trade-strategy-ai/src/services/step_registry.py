from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable


class StepPermission(StrEnum):
    """Step 执行所需的最小权限等级。"""

    viewer = "viewer"
    operator = "operator"
    admin = "admin"


class StepRisk(StrEnum):
    """Step 风险等级。"""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class StepFieldType(StrEnum):
    """Step 输入或输出字段的类型。"""

    string = "string"
    integer = "integer"
    number = "number"
    boolean = "boolean"
    date = "date"
    path = "path"
    object = "object"
    array = "array"


@dataclass(frozen=True)
class StepField:
    """单个 Step schema 字段的定义。"""

    type: StepFieldType
    description: str
    required: bool = False
    default: Any = None
    enum: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StepSchema:
    """Step 输入或输出 schema。"""

    description: str
    fields: dict[str, StepField]
    allow_additional_fields: bool = False

    def validate(self, params: dict[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
        """校验并归一化输入参数。"""
        incoming = dict(params or {})
        normalized: dict[str, Any] = {}
        warnings: list[str] = []

        if not self.allow_additional_fields:
            unexpected = sorted(set(incoming) - set(self.fields))
            if unexpected:
                raise ValueError(f"unexpected params: {', '.join(unexpected)}")

        for name, field in self.fields.items():
            if name in incoming:
                value = incoming[name]
            else:
                value = field.default
            if field.required and value is None:
                raise ValueError(f"missing required param: {name}")
            if value is None:
                continue
            normalized[name] = _coerce_value(name, value, field, warnings)

        if self.allow_additional_fields:
            for name, value in incoming.items():
                if name not in normalized and name not in self.fields:
                    normalized[name] = value

        return normalized, warnings


@dataclass(frozen=True)
class StepArtifactDefinition:
    """Step 输出产物定义。"""

    kind: str
    title: str
    description: str
    required: bool = False


@dataclass(frozen=True)
class StepDefinition:
    """Step 的单一 canonical 定义。"""

    name: str
    version: str
    title: str
    description: str
    input_schema: StepSchema
    output_schema: StepSchema
    risk: StepRisk
    permission: StepPermission
    execute: Callable[[dict[str, Any]], Any]
    artifact_definitions: tuple[StepArtifactDefinition, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        """返回 UI / API 可直接消费的摘要。"""
        return {
            "name": self.name,
            "version": self.version,
            "title": self.title,
            "description": self.description,
            "input_schema": _schema_summary(self.input_schema),
            "output_schema": _schema_summary(self.output_schema),
            "risk": self.risk.value,
            "permission": self.permission.value,
            "artifact_definitions": [
                {
                    "kind": artifact.kind,
                    "title": artifact.title,
                    "description": artifact.description,
                    "required": artifact.required,
                }
                for artifact in self.artifact_definitions
            ],
            "metadata": dict(self.metadata),
        }

    def validate_input(self, params: dict[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
        """校验 Step 输入。"""
        return self.input_schema.validate(params)


class StepRegistryError(Exception):
    """Step Registry 的基础异常。"""


class StepRegistryDuplicateError(StepRegistryError):
    """重复注册 Step 时抛出的异常。"""


class StepRegistryNotFoundError(StepRegistryError):
    """查询不到 Step 时抛出的异常。"""


class StepRegistry:
    """进程内 Step 注册表。"""

    def __init__(self, definitions: tuple[StepDefinition, ...] | None = None) -> None:
        self._definitions: dict[tuple[str, str], StepDefinition] = {}
        for definition in definitions or ():
            self.register(definition)

    def register(self, definition: StepDefinition) -> StepDefinition:
        """注册一个 Step 定义。"""
        key = (definition.name, definition.version)
        if key in self._definitions:
            raise StepRegistryDuplicateError(f"duplicate step definition: {definition.name}@{definition.version}")
        self._definitions[key] = definition
        return definition

    def get(self, name: str, version: str) -> StepDefinition:
        """按 name 和 version 获取 Step 定义。"""
        key = (name, version)
        try:
            return self._definitions[key]
        except KeyError as exc:
            raise StepRegistryNotFoundError(f"unknown step definition: {name}@{version}") from exc

    def list(self) -> list[StepDefinition]:
        """列出已注册的 Step 定义。"""
        return list(self._definitions.values())

    def summary(self) -> list[dict[str, Any]]:
        """列出可供 UI 展示的 Step 摘要。"""
        return [definition.summary() for definition in self.list()]


def _schema_summary(schema: StepSchema) -> dict[str, Any]:
    """把 schema 归一化成可展示结构。"""
    return {
        "description": schema.description,
        "allow_additional_fields": schema.allow_additional_fields,
        "fields": {
            name: {
                "type": field.type.value,
                "description": field.description,
                "required": field.required,
                "default": field.default,
                "enum": list(field.enum),
            }
            for name, field in schema.fields.items()
        },
    }


def _coerce_value(name: str, value: Any, field: StepField, warnings: list[str]) -> Any:
    """将 Step 参数值归一化为受控结构。"""
    coerced: Any
    if field.type == StepFieldType.string:
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string")
        coerced = value
    elif field.type == StepFieldType.integer:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
        coerced = value
    elif field.type == StepFieldType.number:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a number")
        coerced = value
    elif field.type == StepFieldType.boolean:
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be a boolean")
        coerced = value
    elif field.type == StepFieldType.date:
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a date string")
        coerced = value
    elif field.type == StepFieldType.path:
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a path-like string")
        coerced = value
    elif field.type == StepFieldType.object:
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be an object")
        coerced = value
    elif field.type == StepFieldType.array:
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{name} must be an array")
        coerced = list(value)
    else:
        warnings.append(f"unsupported schema type for {name}")
        coerced = value

    if field.enum and coerced not in field.enum:
        raise ValueError(f"{name} must be one of: {', '.join(field.enum)}")
    return coerced
