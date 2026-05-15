from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.services.step_registry import (
    StepArtifactDefinition,
    StepDefinition,
    StepField,
    StepFieldType,
    StepPermission,
    StepRegistry,
    StepRegistryDuplicateError,
    StepRegistryNotFoundError,
    StepRisk,
    StepSchema,
)


@dataclass(frozen=True)
class _ExecMarker:
    """用于测试的执行标记。"""

    value: str


def _build_step() -> StepDefinition:
    """构造测试用的 Step 定义。"""
    input_schema = StepSchema(
        description="输入参数",
        fields={
            "config_path": StepField(type=StepFieldType.path, description="配置文件路径", required=True),
            "force": StepField(type=StepFieldType.boolean, description="是否强制执行", default=False),
            "mode": StepField(type=StepFieldType.string, description="运行模式", enum=["full", "dry-run"], default="full"),
            "tags": StepField(type=StepFieldType.array, description="标签列表", default=[]),
        },
    )
    output_schema = StepSchema(
        description="输出参数",
        fields={
            "job_id": StepField(type=StepFieldType.string, description="Job ID", required=True),
            "result": StepField(type=StepFieldType.object, description="执行结果"),
        },
    )

    def _execute(params: dict[str, object]) -> _ExecMarker:
        return _ExecMarker(value=str(params["config_path"]))

    return StepDefinition(
        name="article-crawl",
        version="v1",
        title="抓取文章",
        description="执行文章抓取。",
        input_schema=input_schema,
        output_schema=output_schema,
        risk=StepRisk.medium,
        permission=StepPermission.operator,
        execute=_execute,
        artifact_definitions=(
            StepArtifactDefinition(kind="crawl-report", title="抓取报告", description="抓取执行结果报告", required=True),
        ),
        metadata={"source": "test"},
    )


def test_registry_registers_and_returns_summary() -> None:
    """注册后应能查询并输出稳定摘要。"""
    registry = StepRegistry()
    step = _build_step()

    registry.register(step)

    loaded = registry.get("article-crawl", "v1")
    assert loaded is step

    summary = registry.summary()
    assert summary == [
        {
            "name": "article-crawl",
            "version": "v1",
            "title": "抓取文章",
            "description": "执行文章抓取。",
            "input_schema": {
                "description": "输入参数",
                "allow_additional_fields": False,
                "fields": {
                    "config_path": {
                        "type": "path",
                        "description": "配置文件路径",
                        "required": True,
                        "default": None,
                        "enum": [],
                    },
                    "force": {
                        "type": "boolean",
                        "description": "是否强制执行",
                        "required": False,
                        "default": False,
                        "enum": [],
                    },
                    "mode": {
                        "type": "string",
                        "description": "运行模式",
                        "required": False,
                        "default": "full",
                        "enum": ["full", "dry-run"],
                    },
                    "tags": {
                        "type": "array",
                        "description": "标签列表",
                        "required": False,
                        "default": [],
                        "enum": [],
                    },
                },
            },
            "output_schema": {
                "description": "输出参数",
                "allow_additional_fields": False,
                "fields": {
                    "job_id": {
                        "type": "string",
                        "description": "Job ID",
                        "required": True,
                        "default": None,
                        "enum": [],
                    },
                    "result": {
                        "type": "object",
                        "description": "执行结果",
                        "required": False,
                        "default": None,
                        "enum": [],
                    },
                },
            },
            "risk": "medium",
            "permission": "operator",
            "artifact_definitions": [
                {
                    "kind": "crawl-report",
                    "title": "抓取报告",
                    "description": "抓取执行结果报告",
                    "required": True,
                }
            ],
            "metadata": {"source": "test"},
        }
    ]


def test_registry_rejects_duplicate_definition() -> None:
    """同名同版本的 Step 不应被重复注册。"""
    registry = StepRegistry()
    step = _build_step()
    registry.register(step)

    with pytest.raises(StepRegistryDuplicateError, match="duplicate step definition: article-crawl@v1"):
        registry.register(step)


def test_registry_raises_structured_error_for_unknown_step() -> None:
    """未注册的 Step 查询应返回结构化异常。"""
    registry = StepRegistry()

    with pytest.raises(StepRegistryNotFoundError, match="unknown step definition: article-crawl@v1"):
        registry.get("article-crawl", "v1")


def test_step_input_validation_normalizes_and_rejects_invalid_values() -> None:
    """Step 输入校验应能归一化可接受值并拒绝非法值。"""
    step = _build_step()

    normalized, warnings = step.validate_input(
        {
            "config_path": "config/app.yaml",
            "force": True,
            "mode": "dry-run",
            "tags": ("news", "market"),
        }
    )
    assert warnings == []
    assert normalized == {
        "config_path": "config/app.yaml",
        "force": True,
        "mode": "dry-run",
        "tags": ["news", "market"],
    }

    with pytest.raises(ValueError, match="missing required param: config_path"):
        step.validate_input({"force": True})

    with pytest.raises(ValueError, match="unexpected params: extra"):
        step.validate_input({"config_path": "config/app.yaml", "extra": 1})

    with pytest.raises(ValueError, match="mode must be one of: full, dry-run"):
        step.validate_input({"config_path": "config/app.yaml", "mode": "invalid"})
