from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any


def _to_plain(value: Any) -> Any:
    """把 dataclass / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if is_dataclass(value):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    return value


@dataclass(frozen=True)
class PipelineOutputArtifactSpec:
    """Pipeline 输出产物的 canonical 说明。"""

    kind: str
    title: str
    description: str
    previewable: bool = False
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineStepSpec:
    """Pipeline 逻辑步骤的 canonical 说明。"""

    step_id: str
    title: str
    description: str
    job_type: str
    depends_on: tuple[str, ...] = ()
    output_artifacts: tuple[str, ...] = ()
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineSpec:
    """单条业务 Pipeline 的 canonical 定义。"""

    pipeline_id: str
    title: str
    description: str
    required_profile_sections: tuple[str, ...]
    input_schema: dict[str, Any]
    output_artifacts: tuple[PipelineOutputArtifactSpec, ...]
    workflow_id: str
    job_types: tuple[str, ...]
    steps: tuple[PipelineStepSpec, ...]
    user_visible_success_criteria: tuple[str, ...]
    ui_page: str
    ui_task_ids: tuple[str, ...]
    extensions: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        """返回可供 catalog / API / UI 消费的摘要。"""
        return {
            "pipeline_id": self.pipeline_id,
            "title": self.title,
            "description": self.description,
            "required_profile_sections": list(self.required_profile_sections),
            "input_schema": _to_plain(self.input_schema),
            "output_artifacts": [_to_plain(item) for item in self.output_artifacts],
            "workflow_id": self.workflow_id,
            "job_types": list(self.job_types),
            "steps": [_to_plain(item) for item in self.steps],
            "user_visible_success_criteria": list(self.user_visible_success_criteria),
            "ui_page": self.ui_page,
            "ui_task_ids": list(self.ui_task_ids),
            "extensions": _to_plain(self.extensions),
        }


ARTICLE_PIPELINE_SPEC = PipelineSpec(
    pipeline_id="article_pipeline",
    title="文章处理链路",
    description="把文章抓取、清洗、处理和回归验收收敛为第一条可交付业务切片。",
    required_profile_sections=(
        "top_symbols",
        "style_cluster_ids",
        "concept_tags",
        "strategy_preference",
        "risk_style",
        "theme_preference",
        "position_bias",
    ),
    input_schema={
        "description": "Article Pipeline 参数",
        "allow_additional_fields": False,
        "fields": {
            "profile_id": {
                "type": "string",
                "description": "Profile ID",
                "required": True,
                "default": None,
                "enum": [],
            },
            "max_articles": {
                "type": "integer",
                "description": "最多文章数",
                "required": False,
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
            "skip_crawl": {
                "type": "boolean",
                "description": "是否跳过抓取",
                "required": False,
                "default": False,
                "enum": [],
            },
            "from_step": {
                "type": "string",
                "description": "起始步骤",
                "required": False,
                "default": None,
                "enum": [],
            },
            "use_db": {
                "type": "boolean",
                "description": "是否使用数据库链路",
                "required": False,
                "default": False,
                "enum": [],
            },
            "retry_failed": {
                "type": "boolean",
                "description": "是否重试失败任务",
                "required": False,
                "default": False,
                "enum": [],
            },
        },
    },
    output_artifacts=(
        PipelineOutputArtifactSpec(
            kind="result-json",
            title="执行结果 JSON",
            description="机器可读的运行结果摘要，供 Job Detail 和后续自动化消费。",
            previewable=True,
            extensions={"required": True},
        ),
        PipelineOutputArtifactSpec(
            kind="html",
            title="HTML 报告",
            description="可选的人类可读报告，便于复盘和验收。",
            previewable=True,
            extensions={"required": False},
        ),
    ),
    workflow_id="pipeline",
    job_types=("crawl", "clean", "validate", "store", "process", "pipeline-run"),
    steps=(
        PipelineStepSpec(
            step_id="crawl",
            title="抓取文章",
            description="抓取并整理文章原始数据。",
            job_type="crawl",
            output_artifacts=("result-json",),
        ),
        PipelineStepSpec(
            step_id="clean",
            title="清洗文章",
            description="对抓取结果做清洗、去重和格式归一化。",
            job_type="clean",
            depends_on=("crawl",),
            output_artifacts=("result-json",),
        ),
        PipelineStepSpec(
            step_id="validate",
            title="校验文章",
            description="对清洗后的文章进行质量校验和可抽取性标记。",
            job_type="validate",
            depends_on=("clean",),
            output_artifacts=("result-json",),
        ),
        PipelineStepSpec(
            step_id="store",
            title="入库文章",
            description="将校验后的文章写入数据库并生成后续处理任务。",
            job_type="store",
            depends_on=("validate",),
            output_artifacts=("result-json",),
        ),
        PipelineStepSpec(
            step_id="process",
            title="处理任务",
            description="消费待处理任务并生成后续结构化结果。",
            job_type="process",
            depends_on=("store",),
            output_artifacts=("result-json",),
        ),
    ),
    user_visible_success_criteria=(
        "用户可从 /articles 通过 Profile 触发 article_pipeline。",
        "运行后能进入 Job Detail 查看结果和产物。",
        "输入 schema 可直接驱动 Web 表单。",
        "失败结果可回到 Job Detail 定位。",
    ),
    ui_page="/articles",
    ui_task_ids=("UI-V1-010", "UI-V1-007"),
    extensions={
        "supported_input_modes": ("profile",),
        "migration_target": "profile",
        "ui_note": "Profile 输入是 canonical 执行入口。",
    },
)

ARTICLE_PIPELINE_SPECS: tuple[PipelineSpec, ...] = (ARTICLE_PIPELINE_SPEC,)
