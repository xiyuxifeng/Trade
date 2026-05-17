from __future__ import annotations

from src.pipelines.article_pipeline_spec import PipelineOutputArtifactSpec, PipelineSpec, PipelineStepSpec
from src.services.job_registry import JobPermission


def _step_extensions(
    *,
    permission: JobPermission,
    error_modes: tuple[str, ...],
    runtime_support: str = "current",
) -> dict[str, object]:
    """为回测步骤附加权限、错误分类和运行支持说明。"""
    return {
        "permission": permission.value,
        "error_modes": list(error_modes),
        "runtime_support": runtime_support,
    }


BACKTEST_PIPELINE_SPEC = PipelineSpec(
    pipeline_id="backtest",
    title="回测中心",
    description="把回测、规则验真和可复现性检查收敛成单一正式回测管线。",
    required_profile_sections=(
        "trader",
        "strategy",
        "market",
    ),
    input_schema={
        "description": "Backtest Pipeline 参数",
        "allow_additional_fields": False,
        "fields": {
            "trader_id": {
                "type": "string",
                "description": "交易员 ID",
                "required": True,
                "default": None,
                "enum": [],
            },
            "date_from": {
                "type": "date",
                "description": "开始日期",
                "required": True,
                "default": None,
                "enum": [],
            },
            "date_to": {
                "type": "date",
                "description": "结束日期",
                "required": True,
                "default": None,
                "enum": [],
            },
            "strategy_version_id": {
                "type": "string",
                "description": "策略版本 ID",
                "required": False,
                "default": None,
                "enum": [],
            },
            "symbols": {
                "type": "array",
                "description": "标的列表",
                "required": False,
                "default": [],
                "enum": [],
            },
            "mode": {
                "type": "string",
                "description": "回测模式",
                "required": False,
                "default": "full",
                "enum": ["full", "replay", "rule_validation"],
            },
            "use_snapshot_only": {
                "type": "boolean",
                "description": "是否仅使用快照数据",
                "required": False,
                "default": True,
                "enum": [],
            },
            "scoring_profile": {
                "type": "string",
                "description": "评分配置名",
                "required": False,
                "default": "stage5",
                "enum": [],
            },
            "config_path": {
                "type": "path",
                "description": "配置文件路径",
                "required": False,
                "default": "config/app.yaml",
                "enum": [],
            },
        },
    },
    output_artifacts=(
        PipelineOutputArtifactSpec(
            kind="result-json",
            title="回测结果 JSON",
            description="回测运行的 canonical 结果摘要，供 Job Detail 和后续自动化消费。",
            previewable=True,
            extensions={"required": True, "runtime_support": "current"},
        ),
        PipelineOutputArtifactSpec(
            kind="report-markdown",
            title="回测报告 Markdown",
            description="回测结果的人类可读 Markdown 报告，供 Job Detail 和 Backtest Center 复盘。",
            previewable=True,
            extensions={"required": True, "runtime_support": "current"},
        ),
        PipelineOutputArtifactSpec(
            kind="validation-report-markdown",
            title="规则验真报告 Markdown",
            description="规则验真的人类可读 Markdown 报告，供 Job Detail 和 Backtest Center 复盘。",
            previewable=True,
            extensions={"required": False, "runtime_support": "current"},
        ),
        PipelineOutputArtifactSpec(
            kind="records-csv",
            title="回测交易记录 CSV",
            description="回测交易记录明细，供下载和外部分析。",
            previewable=True,
            extensions={"required": True, "runtime_support": "current"},
        ),
    ),
    workflow_id="backtest",
    job_types=("backtest-run", "backtest-validate-rules", "backtest-reproducibility-check"),
    steps=(
        PipelineStepSpec(
            step_id="backtest-run",
            title="执行回测",
            description="执行离线回测并生成结果、报告和交易记录。",
            job_type="backtest-run",
            output_artifacts=("result-json", "report-markdown", "records-csv"),
            extensions=_step_extensions(
                permission=JobPermission.operator,
                error_modes=("config missing", "permission denied", "provider unavailable", "system error"),
            ),
        ),
        PipelineStepSpec(
            step_id="backtest-validate-rules",
            title="规则验真",
            description="执行规则验真并生成报告。",
            job_type="backtest-validate-rules",
            depends_on=("backtest-run",),
            output_artifacts=("result-json", "validation-report-markdown"),
            extensions=_step_extensions(
                permission=JobPermission.operator,
                error_modes=("config missing", "permission denied", "provider unavailable", "system error"),
            ),
        ),
        PipelineStepSpec(
            step_id="backtest-reproducibility-check",
            title="可复现性检查",
            description="重复运行回测并比对 fingerprint。",
            job_type="backtest-reproducibility-check",
            depends_on=("backtest-run",),
            output_artifacts=("result-json",),
            extensions=_step_extensions(
                permission=JobPermission.admin,
                error_modes=("config missing", "permission denied", "provider unavailable", "system error"),
            ),
        ),
    ),
    user_visible_success_criteria=(
        "用户可通过 Web 运行回测。",
        "用户可查看回测结果、报告和 fingerprint。",
        "回测结果通过 Job / Workflow / Artifact 体系回溯。",
        "输入 schema 可直接驱动 Backtest Center 表单，而不需要 CLI 命令入口。",
    ),
    ui_page="/backtest",
    ui_task_ids=("UI-V3-001",),
    extensions={
        "supported_input_modes": ("profile", "config_path"),
        "migration_target": "profile",
        "backtest_actions": ("backtest-run", "backtest-validate-rules", "backtest-reproducibility-check"),
        "current_runtime_support": {
            "backtest-run": ["current"],
            "backtest-validate-rules": ["current"],
            "backtest-reproducibility-check": ["current"],
        },
        "ui_note": "Backtest Center 后续只读此 spec，不再拼接 CLI 文案或临时入口。",
    },
)

BACKTEST_PIPELINE_SPECS: tuple[PipelineSpec, ...] = (BACKTEST_PIPELINE_SPEC,)
