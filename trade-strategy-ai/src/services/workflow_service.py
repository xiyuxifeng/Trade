from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.services.base import BaseService, ServiceResult
from src.services.job_registry import get_job_definition, validate_job_submission
from src.services.job_service import JobService


@dataclass(frozen=True)
class WorkflowStep:
    """单个 Workflow 步骤定义。"""

    step_id: str
    title: str
    description: str
    required_job_type: str
    parameters: list[str] = field(default_factory=list)
    param_schema: dict[str, Any] = field(default_factory=dict)
    risk: str = "medium"
    requires_confirmation: bool = False


@dataclass(frozen=True)
class WorkflowDefinition:
    """Workflow 的 UI 展示定义。"""

    workflow_id: str
    title: str
    description: str
    job_type: str
    steps: list[WorkflowStep]
    permissions: str = "operator"

    def summary(self) -> dict[str, Any]:
        """返回 UI 可直接展示的摘要。"""
        job_definition = get_job_definition(self.job_type)
        return {
            "workflow_id": self.workflow_id,
            "title": self.title,
            "description": self.description,
            "job_type": self.job_type,
            "permissions": self.permissions,
            "job_definition": job_definition.summary() if job_definition is not None else None,
            "steps": [
                {
                    "step_id": step.step_id,
                    "title": step.title,
                    "description": step.description,
                    "required_job_type": step.required_job_type,
                    "parameters": step.parameters,
                    "param_schema": step.param_schema,
                    "risk": step.risk,
                    "requires_confirmation": step.requires_confirmation,
                }
                for step in self.steps
            ],
        }

    def requires_confirmation(self) -> bool:
        """判断当前工作流是否需要二次确认。"""
        if self.job_type:
            job_definition = get_job_definition(self.job_type)
            if job_definition is not None and (job_definition.requires_confirmation or job_definition.risk.value in {"high", "critical"}):
                return True
        return any(step.requires_confirmation or step.risk in {"high", "critical"} for step in self.steps)


def _workflow(
    workflow_id: str,
    title: str,
    description: str,
    job_type: str,
    *,
    steps: list[WorkflowStep],
    permissions: str = "operator",
) -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id=workflow_id,
        title=title,
        description=description,
        job_type=job_type,
        steps=steps,
        permissions=permissions,
    )


def _workflow_step(
    step_id: str,
    title: str,
    description: str,
    required_job_type: str,
    *,
    parameters: list[str] | None = None,
) -> WorkflowStep:
    """从 Job 白名单派生 Workflow 步骤定义。"""
    job_definition = get_job_definition(required_job_type)
    if job_definition is None:
        raise ValueError(f"unknown job type for workflow step: {required_job_type}")

    param_schema = job_definition.param_schema.model_dump(mode="json")
    return WorkflowStep(
        step_id=step_id,
        title=title,
        description=description,
        required_job_type=required_job_type,
        parameters=parameters or list(param_schema["fields"].keys()),
        param_schema=param_schema,
        risk=job_definition.risk.value,
        requires_confirmation=job_definition.requires_confirmation,
    )


DEFAULT_WORKFLOWS: tuple[WorkflowDefinition, ...] = (
    _workflow(
        "install-config",
        "安装与配置",
        "完成项目初始化、数据库迁移和基础数据导入。",
        "init-project",
        steps=[
            _workflow_step(
                "db-migrate",
                "数据库迁移",
                "先完成数据库 schema 迁移。",
                "db-migrate",
            ),
            _workflow_step(
                "init-project",
                "初始化项目",
                "执行初始化并完成最小可运行状态。",
                "init-project",
            ),
            _workflow_step(
                "seed-data",
                "导入样例数据",
                "导入样例数据，便于首次联调。",
                "seed-data",
            ),
        ],
    ),
    _workflow(
        "database",
        "数据库维护",
        "聚焦数据库迁移、备份和恢复等操作。",
        "db-migrate",
        steps=[
            _workflow_step("db-migrate", "数据库迁移", "执行数据库 schema 迁移。", "db-migrate"),
            _workflow_step("backup-data", "数据备份", "备份数据库和处理产物。", "backup-data"),
            _workflow_step("restore-data", "数据恢复", "从备份包恢复数据库和产物。", "restore-data"),
        ],
    ),
    _workflow(
        "pipeline",
        "数据 Pipeline",
        "串联抓取、清洗、抽取、聚类与回归验证。",
        "pipeline-run",
        steps=[
            _workflow_step("crawl", "抓取文章", "执行文章抓取。", "crawl"),
            _workflow_step("import-trade-logs", "导入交易记录", "导入交易记录样例或正式数据。", "import-trade-logs"),
            _workflow_step("pipeline-run", "执行完整链路", "运行完整 pipeline。", "pipeline-run"),
            _workflow_step("pipeline-step", "执行单步", "从指定步骤继续执行 pipeline。", "pipeline-step"),
            _workflow_step("clusters-build", "构建画像聚类", "构建 persona clusters。", "clusters-build"),
            _workflow_step("e2e-regression", "端到端回归", "串起主链路进行回归验证。", "e2e-regression"),
        ],
    ),
    _workflow(
        "pre-market",
        "盘前工作台",
        "完成盘前日报、市场状态和快照相关操作。",
        "run-pre-market",
        steps=[
            _workflow_step("run-pre-market", "执行盘前日报", "生成盘前日报和可选 HTML。", "run-pre-market"),
            _workflow_step("market-state-build", "构建市场状态", "先准备市场状态数据。", "market-state-build"),
            _workflow_step("snapshot-build", "构建候选池快照", "生成盘前/盘后需要的快照。", "snapshot-build"),
        ],
    ),
    _workflow(
        "after-close",
        "盘后工作台",
        "完成盘后考核、归因与结果归档。",
        "run-after-close",
        steps=[
            _workflow_step("run-after-close", "执行盘后考核", "生成盘后考核和可选 HTML。", "run-after-close"),
        ],
    ),
    _workflow(
        "snapshot",
        "快照中心",
        "构建候选池快照，供盘前盘后和回测使用。",
        "snapshot-build",
        steps=[
            _workflow_step("snapshot-build", "构建快照", "支持单日与区间快照构建。", "snapshot-build"),
        ],
    ),
    _workflow(
        "ohlcv",
        "OHLCV 行情",
        "抓取和回灌日线 OHLCV 数据。",
        "ohlcv-crawl",
        steps=[
            _workflow_step("ohlcv-crawl", "抓取 OHLCV", "抓取日线行情并写入数据库。", "ohlcv-crawl"),
        ],
    ),
    _workflow(
        "strategy",
        "策略版本",
        "按交易员和日期构建策略版本。",
        "strategy-build",
        steps=[
            _workflow_step("strategy-build", "构建策略版本", "生成交易员策略版本。", "strategy-build"),
        ],
    ),
    _workflow(
        "backtest",
        "回测中心",
        "执行回测、规则验真和可复现性检查。",
        "backtest-run",
        steps=[
            _workflow_step("backtest-run", "执行回测", "执行离线回测。", "backtest-run"),
            _workflow_step("backtest-validate-rules", "规则验真", "执行规则验真并生成报告。", "backtest-validate-rules"),
            _workflow_step(
                "backtest-reproducibility-check",
                "可复现性检查",
                "重复运行回测并比对 fingerprint。",
                "backtest-reproducibility-check",
            ),
        ],
    ),
    _workflow(
        "optimize",
        "优化中心",
        "基于验真和回测结果生成候选版本。",
        "optimize-create-candidate",
        steps=[
            _workflow_step(
                "optimize-create-candidate",
                "生成候选版本",
                "从规则调整生成候选策略版本。",
                "optimize-create-candidate",
            ),
        ],
    ),
    _workflow(
        "rule-pool",
        "规则池管理",
        "围绕规则池回测和审核流程组织操作。",
        "rule-pool-backtest",
        steps=[
            _workflow_step("rule-pool-backtest", "规则池回测", "对规则池进行回测并回写结果。", "rule-pool-backtest"),
        ],
    ),
    _workflow(
        "scheduler",
        "调度与监控",
        "管理 Kaipan 抓取、归一化与一键运行。",
        "kaipan-run",
        steps=[
            _workflow_step("kaipan-fetch", "Kaipan 抓取", "抓取指定交易日的原始数据。", "kaipan-fetch"),
            _workflow_step("kaipan-normalize", "Kaipan 归一化", "将原始数据规范化。", "kaipan-normalize"),
            _workflow_step("kaipan-run", "Kaipan 一键运行", "构建调度计划或启动调度器。", "kaipan-run"),
        ],
    ),
    _workflow(
        "report",
        "报表与回顾",
        "汇总盘前盘后报表与回测回顾结果。",
        "run-after-close",
        steps=[
            _workflow_step("run-pre-market", "盘前报表", "回顾盘前日报结果。", "run-pre-market"),
            _workflow_step("run-after-close", "盘后报表", "回顾盘后考核结果。", "run-after-close"),
            _workflow_step("e2e-regression", "回归报表", "查看端到端回归结果。", "e2e-regression"),
        ],
    ),
)

_WORKFLOW_MAP: dict[str, WorkflowDefinition] = {item.workflow_id: item for item in DEFAULT_WORKFLOWS}


class WorkflowService(BaseService):
    """Workflow API 的 UI 服务。"""

    service_name = "workflow"

    def __init__(self, *, job_service: JobService | None = None) -> None:
        self._job_service = job_service or JobService()

    async def list_workflows(self) -> ServiceResult:
        """列出默认工作流定义。"""
        return ServiceResult(
            status="ok",
            message="workflows listed",
            payload={
                "count": len(DEFAULT_WORKFLOWS),
                "items": [workflow.summary() for workflow in DEFAULT_WORKFLOWS],
            },
        )

    async def get_workflow(self, workflow_id: str) -> ServiceResult:
        """按 workflow_id 查询定义。"""
        workflow = _WORKFLOW_MAP.get(workflow_id)
        if workflow is None:
            return ServiceResult(status="partial", message="workflow not found", payload={"workflow_id": workflow_id})
        return ServiceResult(status="ok", message="workflow loaded", payload={"workflow": workflow.summary()})

    async def run_workflow(
        self,
        *,
        workflow_id: str,
        params: dict[str, Any] | None = None,
        created_by: str | None = None,
        idempotency_key: str | None = None,
        confirmed: bool = False,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """将工作流运行映射到对应 Job。"""
        workflow = _WORKFLOW_MAP.get(workflow_id)
        if workflow is None:
            return ServiceResult(status="partial", message="workflow not found", payload={"workflow_id": workflow_id})

        if workflow.requires_confirmation() and not confirmed:
            return ServiceResult(
                status="error",
                message="confirmation required for high-risk workflow",
                payload={
                    "workflow_id": workflow_id,
                    "workflow": workflow.summary(),
                    "requires_confirmation": True,
                },
            )

        validation = validate_job_submission(
            job_type=workflow.job_type,
            params=params,
            created_by=created_by,
            confirmed=confirmed,
        )
        if validation.status != "ok":
            return ServiceResult(status="error", message=validation.message or "invalid workflow params", payload=validation.payload)

        created = await self._job_service.create_job(
            job_type=workflow.job_type,
            params=validation.payload["params"],
            created_by=created_by,
            idempotency_key=idempotency_key,
            audit_source=audit_source,
        )
        if created.status != "ok":
            return created

        return ServiceResult(
            status="ok",
            message="workflow started",
            payload={
                "workflow": workflow.summary(),
                "job": created.payload["job"],
                "job_dir": created.payload.get("job_dir"),
                "log_path": created.payload.get("log_path"),
                "params_path": created.payload.get("params_path"),
                "result_path": created.payload.get("result_path"),
                "artifacts_path": created.payload.get("artifacts_path"),
            },
        )


def make_workflow_service(job_service: JobService | None = None) -> WorkflowService:
    """构造 WorkflowService 实例，供 API 层依赖注入复用。"""
    return WorkflowService(job_service=job_service)
