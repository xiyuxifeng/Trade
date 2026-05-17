from __future__ import annotations

from src.pipelines.article_pipeline_spec import PipelineOutputArtifactSpec, PipelineSpec, PipelineStepSpec
from src.services.job_registry import JobPermission


def _step_extensions(
    *,
    permission: JobPermission,
    error_modes: tuple[str, ...],
    runtime_support: str = "current",
) -> dict[str, object]:
    """为优化 / 规则池步骤附加权限、错误分类和运行支持说明。"""
    return {
        "permission": permission.value,
        "error_modes": list(error_modes),
        "runtime_support": runtime_support,
    }


OPTIMIZE_RULE_POOL_PIPELINE_SPEC = PipelineSpec(
    pipeline_id="optimize-rule-pool",
    title="优化与规则池",
    description="把候选创建、规则池回测、候选审核和规则审核收敛成单一正式工作流。",
    required_profile_sections=(
        "trader",
        "strategy",
        "market",
    ),
    input_schema={
        "description": "Optimize / Rule Pool Pipeline 参数",
        "allow_additional_fields": False,
        "fields": {
            "parent_version_id": {
                "type": "string",
                "description": "父版本 ID",
                "required": True,
                "default": None,
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
            "adjustments": {
                "type": "array",
                "description": "策略调整列表",
                "required": False,
                "default": [],
                "enum": [],
            },
            "recommendations": {
                "type": "array",
                "description": "候选版本推荐列表",
                "required": False,
                "default": [],
                "enum": [],
            },
            "rule_id": {
                "type": "string",
                "description": "规则 ID",
                "required": False,
                "default": None,
                "enum": [],
            },
            "config_path": {
                "type": "path",
                "description": "配置文件路径",
                "required": False,
                "default": "config/app.yaml",
                "enum": [],
            },
            "review_decision": {
                "type": "string",
                "description": "审核决策",
                "required": False,
                "default": "pending",
                "enum": ["approve", "reject", "pending"],
            },
            "reviewed_by": {
                "type": "string",
                "description": "审核人",
                "required": False,
                "default": "web",
                "enum": [],
            },
            "force": {
                "type": "boolean",
                "description": "是否强制覆盖",
                "required": False,
                "default": False,
                "enum": [],
            },
            "notes": {
                "type": "string",
                "description": "备注",
                "required": False,
                "default": None,
                "enum": [],
            },
        },
    },
    output_artifacts=(
        PipelineOutputArtifactSpec(
            kind="candidate-json",
            title="候选版本 JSON",
            description="候选版本的 canonical JSON 摘要，供策略工作台和 Job Detail 消费。",
            previewable=True,
            extensions={"required": True, "runtime_support": "current"},
        ),
        PipelineOutputArtifactSpec(
            kind="backtest-evidence-json",
            title="规则池回测证据 JSON",
            description="规则池回测的证据摘要，供审核流程和 Job Detail 消费。",
            previewable=True,
            extensions={"required": True, "runtime_support": "current"},
        ),
        PipelineOutputArtifactSpec(
            kind="review-report-markdown",
            title="审核报告 Markdown",
            description="候选审核与规则审核的人类可读报告。",
            previewable=True,
            extensions={"required": False, "runtime_support": "current"},
        ),
        PipelineOutputArtifactSpec(
            kind="audit-log-json",
            title="审核审计 JSON",
            description="审核动作的结构化审计记录。",
            previewable=True,
            extensions={"required": False, "runtime_support": "current"},
        ),
    ),
    workflow_id="optimize-rule-pool",
    job_types=("optimize-create-candidate", "rule-pool-backtest", "candidate-review", "rule-review"),
    steps=(
        PipelineStepSpec(
            step_id="optimize-create-candidate",
            title="生成候选版本",
            description="基于规则调整生成候选策略版本。",
            job_type="optimize-create-candidate",
            output_artifacts=("candidate-json",),
            extensions=_step_extensions(
                permission=JobPermission.operator,
                error_modes=("config missing", "permission denied", "system error"),
            ),
        ),
        PipelineStepSpec(
            step_id="rule-pool-backtest",
            title="规则池回测",
            description="对规则池候选进行回测并生成证据。",
            job_type="rule-pool-backtest",
            depends_on=("optimize-create-candidate",),
            output_artifacts=("backtest-evidence-json",),
            extensions=_step_extensions(
                permission=JobPermission.admin,
                error_modes=("config missing", "permission denied", "system error"),
            ),
        ),
        PipelineStepSpec(
            step_id="candidate-review",
            title="候选版本审核",
            description="对候选版本执行人工审核并生成审核结果。",
            job_type="candidate-review",
            depends_on=("rule-pool-backtest",),
            output_artifacts=("review-report-markdown", "audit-log-json"),
            extensions=_step_extensions(
                permission=JobPermission.operator,
                error_modes=("permission denied", "invalid candidate", "system error"),
                runtime_support="current",
            ),
        ),
        PipelineStepSpec(
            step_id="rule-review",
            title="规则审核",
            description="对规则池条目执行批准、拒绝或待定审核。",
            job_type="rule-review",
            depends_on=("candidate-review",),
            output_artifacts=("review-report-markdown", "audit-log-json"),
            extensions=_step_extensions(
                permission=JobPermission.operator,
                error_modes=("permission denied", "invalid rule", "system error"),
                runtime_support="current",
            ),
        ),
    ),
    user_visible_success_criteria=(
        "用户可通过 Web 创建候选版本。",
        "用户可通过 Web 审核规则池和候选版本。",
        "候选版本与规则审核结果都能回溯到 Job / Artifact / Audit。",
        "输入 schema 可直接驱动 Web 表单，而不需要 CLI 命令入口。",
    ),
    ui_page="/rule-pool",
    ui_task_ids=("UI-V3-002", "UI-V3-003"),
    extensions={
        "supported_input_modes": ("profile", "config_path"),
        "migration_target": "profile",
        "optimize_actions": ("optimize-create-candidate", "candidate-review"),
        "rule_pool_actions": ("rule-pool-backtest", "rule-review"),
        "current_runtime_support": {
            "optimize-create-candidate": ["current"],
            "rule-pool-backtest": ["current"],
            "candidate-review": ["current"],
            "rule-review": ["current"],
        },
        "canonical_ui_pages": ["/rule-pool", "/strategies"],
        "ui_note": "优化与规则池后续只读此 spec，不再拼接 legacy 策略实验室文案。",
    },
)

OPTIMIZE_RULE_POOL_PIPELINE_SPECS: tuple[PipelineSpec, ...] = (OPTIMIZE_RULE_POOL_PIPELINE_SPEC,)

