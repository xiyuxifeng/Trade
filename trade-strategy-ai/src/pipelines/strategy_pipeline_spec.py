from __future__ import annotations

from src.pipelines.article_pipeline_spec import PipelineOutputArtifactSpec, PipelineSpec, PipelineStepSpec
from src.services.job_registry import JobPermission


def _step_extensions(*, permission: JobPermission, error_modes: tuple[str, ...], runtime_support: str = "current") -> dict[str, object]:
    """为策略步骤附加权限、错误分类和运行支持说明。"""
    return {
        "permission": permission.value,
        "error_modes": list(error_modes),
        "runtime_support": runtime_support,
    }


STRATEGY_PIPELINE_SPEC = PipelineSpec(
    pipeline_id="strategy",
    title="策略工作台",
    description="把策略版本构建、盘前运行和盘后运行收敛成单一正式策略管线。",
    required_profile_sections=("profile", "strategy", "market", "trader"),
    input_schema={
        "description": "Strategy Pipeline 参数",
        "allow_additional_fields": False,
        "fields": {
            "config_path": {
                "type": "path",
                "description": "配置文件路径",
                "required": True,
                "default": None,
                "enum": [],
            },
            "profile_id": {
                "type": "string",
                "description": "Profile ID",
                "required": False,
                "default": "default",
                "enum": [],
            },
            "trader_id": {
                "type": "string",
                "description": "交易员 ID",
                "required": True,
                "default": None,
                "enum": [],
            },
            "strategy_date": {
                "type": "date",
                "description": "策略日期",
                "required": True,
                "default": None,
                "enum": [],
            },
            "as_of_date": {
                "type": "date",
                "description": "盘前/盘后执行日期",
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
            "export_html": {
                "type": "boolean",
                "description": "是否导出 HTML 报告",
                "required": False,
                "default": False,
                "enum": [],
            },
        },
    },
    output_artifacts=(
        PipelineOutputArtifactSpec(
            kind="strategy-version-json",
            title="策略版本 JSON",
            description="交易员策略版本的 canonical 结果摘要，供 Job Detail 和策略工作台消费。",
            previewable=True,
            extensions={"required": True, "runtime_support": "current"},
        ),
        PipelineOutputArtifactSpec(
            kind="evidence-pack-json",
            title="证据包 JSON",
            description="策略版本对应的证据包摘要或兼容引用，用于回溯策略来源。",
            previewable=True,
            extensions={"required": False, "runtime_support": "planned"},
        ),
        PipelineOutputArtifactSpec(
            kind="pre-market-report-json",
            title="盘前报告 JSON",
            description="盘前运行的结构化结果，供策略工作台和 Job Detail 复盘。",
            previewable=True,
            extensions={"required": False, "runtime_support": "current"},
        ),
        PipelineOutputArtifactSpec(
            kind="pre-market-report-html",
            title="盘前 HTML 报告",
            description="盘前运行的人类可读 HTML 报告。",
            previewable=True,
            extensions={"required": False, "runtime_support": "current"},
        ),
        PipelineOutputArtifactSpec(
            kind="after-close-report-json",
            title="盘后报告 JSON",
            description="盘后考核的结构化结果，供策略工作台和 Job Detail 复盘。",
            previewable=True,
            extensions={"required": False, "runtime_support": "current"},
        ),
        PipelineOutputArtifactSpec(
            kind="after-close-report-html",
            title="盘后 HTML 报告",
            description="盘后考核的人类可读 HTML 报告。",
            previewable=True,
            extensions={"required": False, "runtime_support": "current"},
        ),
        PipelineOutputArtifactSpec(
            kind="ranking-report-json",
            title="排名报告 JSON",
            description="策略排名或筛选结果的结构化摘要，当前作为兼容扩展保留。",
            previewable=True,
            extensions={"required": False, "runtime_support": "planned"},
        ),
        PipelineOutputArtifactSpec(
            kind="memory-update-json",
            title="记忆更新 JSON",
            description="策略记忆更新结果的结构化摘要，当前仅在支持时启用。",
            previewable=True,
            extensions={"required": False, "runtime_support": "planned"},
        ),
    ),
    workflow_id="strategy",
    job_types=("strategy-build", "run-pre-market", "run-after-close"),
    steps=(
        PipelineStepSpec(
            step_id="strategy-build",
            title="构建策略版本",
            description="生成交易员策略版本并保留证据链。",
            job_type="strategy-build",
            output_artifacts=("strategy-version-json", "evidence-pack-json"),
            extensions=_step_extensions(
                permission=JobPermission.operator,
                error_modes=("config missing", "permission denied", "system error"),
            ),
        ),
        PipelineStepSpec(
            step_id="run-pre-market",
            title="盘前运行",
            description="生成盘前日报与可选 HTML 报告。",
            job_type="run-pre-market",
            depends_on=("strategy-build",),
            output_artifacts=("pre-market-report-json", "pre-market-report-html", "ranking-report-json"),
            extensions=_step_extensions(
                permission=JobPermission.operator,
                error_modes=("config missing", "permission denied", "provider unavailable", "system error"),
            ),
        ),
        PipelineStepSpec(
            step_id="run-after-close",
            title="盘后运行",
            description="生成盘后考核与可选 HTML 报告，并预留记忆更新扩展。",
            job_type="run-after-close",
            depends_on=("run-pre-market",),
            output_artifacts=("after-close-report-json", "after-close-report-html", "memory-update-json"),
            extensions=_step_extensions(
                permission=JobPermission.operator,
                error_modes=("config missing", "permission denied", "provider unavailable", "system error"),
                runtime_support="current",
            ),
        ),
    ),
    user_visible_success_criteria=(
        "用户可通过 Web 理解策略版本、盘前和盘后构成的正式运行链路。",
        "策略版本、盘前和盘后结果都能回溯到 Job 和 Artifact。",
        "输入 schema 可直接驱动策略工作台表单，而不需要 CLI 命令入口。",
        "错误与权限状态可以在 Web 中被明确解释。",
    ),
    ui_page="/strategies",
    ui_task_ids=("UI-V2-006", "UI-V2-007"),
    extensions={
        "supported_input_modes": ("profile", "config_path"),
        "migration_target": "profile",
        "strategy_actions": ("strategy-build", "run-pre-market", "run-after-close"),
        "current_runtime_support": {
            "strategy-build": ["current"],
            "run-pre-market": ["current"],
            "run-after-close": ["current"],
        },
        "future_extensions": ("ranking-report-json", "memory-update-json"),
        "ui_note": "策略工作台后续只读此 spec，不再拼接临时入口或 CLI 文案。",
    },
)


STRATEGY_PIPELINE_SPECS: tuple[PipelineSpec, ...] = (STRATEGY_PIPELINE_SPEC,)
