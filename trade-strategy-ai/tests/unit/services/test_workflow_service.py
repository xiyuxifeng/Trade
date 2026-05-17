from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class _FakeWorkflowRunner:
    """WorkflowService 单测用的 WorkflowRunner 替身。"""

    calls: list[dict[str, Any]]

    async def run_workflow(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return type(
            "Result",
            (),
            {
                "status": "ok",
                "message": "workflow completed",
                "payload": {
                    "workflow": kwargs["workflow"].summary(),
                    "workflow_run": {
                        "run_context": {"status": "success"},
                        "step_results": [],
                        "errors": [],
                        "artifacts": [],
                    },
                    "job": {
                        "id": "job-1",
                        "job_type": kwargs["workflow"].job_type,
                        "status": "success",
                    },
                },
            },
        )()


def test_workflow_service_exports_and_lists_default_definitions() -> None:
    """WorkflowService 应可导入并返回默认工作流定义。"""
    from src.services import WorkflowService

    service = WorkflowService()
    listed = __import__("asyncio").run(service.list_workflows())

    assert service.service_name == "workflow"
    assert listed.status == "ok"
    workflow_ids = {item["workflow_id"] for item in listed.payload["items"]}
    assert {
        "install-config",
        "database",
        "pipeline",
        "pre-market",
        "after-close",
        "snapshot",
        "ohlcv",
        "strategy",
        "backtest",
        "optimize",
        "optimize-rule-pool",
        "rule-pool",
        "scheduler",
        "report",
    } <= workflow_ids

    pre_market = next(item for item in listed.payload["items"] if item["workflow_id"] == "pre-market")
    step = pre_market["steps"][0]
    assert "param_schema" in step
    assert step["param_schema"]["description"] == "盘前执行参数"
    assert step["param_schema"]["fields"]["as_of_date"]["type"] == "date"
    assert step["param_schema"]["fields"]["export_html"]["default"] is False

    install = next(item for item in listed.payload["items"] if item["workflow_id"] == "install-config")
    assert install["steps"][0]["param_schema"]["fields"]["config_path"]["required"] is True

    scheduler = next(item for item in listed.payload["items"] if item["workflow_id"] == "scheduler")
    scheduler_step_ids = [step["step_id"] for step in scheduler["steps"]]
    assert scheduler_step_ids == [
        "kaipan-fetch",
        "kaipan-normalize",
        "kaipan-run",
        "ohlcv-crawl",
        "market-state-build",
        "snapshot-build",
    ]

    optimize_rule_pool = next(item for item in listed.payload["items"] if item["workflow_id"] == "optimize-rule-pool")
    assert [step["step_id"] for step in optimize_rule_pool["steps"]] == [
        "optimize-create-candidate",
        "rule-pool-backtest",
        "candidate-review",
        "rule-review",
    ]
    assert optimize_rule_pool["steps"][0]["param_schema"]["fields"]["adjustments_path"]["required"] is True


def test_workflow_service_runs_workflow_through_job_service() -> None:
    """WorkflowService 应将工作流运行委托给 WorkflowRunner。"""
    from src.services import WorkflowService

    fake_runner = _FakeWorkflowRunner(calls=[])
    service = WorkflowService(workflow_runner=fake_runner)
    result = __import__("asyncio").run(
        service.run_workflow(
            workflow_id="pre-market",
            params={"config_path": "config/app.yaml"},
            created_by="web",
        )
    )

    assert result.status == "ok"
    assert result.payload["workflow"]["workflow_id"] == "pre-market"
    assert result.payload["job"]["job_type"] == "run-pre-market"
    assert fake_runner.calls[0]["workflow"].workflow_id == "pre-market"
    assert fake_runner.calls[0]["params"]["config_path"] == "config/app.yaml"
    assert fake_runner.calls[0]["confirmed"] is False


def test_workflow_service_accepts_market_scheduler_params() -> None:
    """Scheduler 工作流应能承接 market 数据所需的联合参数。"""
    from src.services import WorkflowService

    fake_runner = _FakeWorkflowRunner(calls=[])
    service = WorkflowService(workflow_runner=fake_runner)
    result = __import__("asyncio").run(
        service.run_workflow(
            workflow_id="scheduler",
            params={
                "config_path": "config/app.yaml",
                "trade_date": "2026-05-16",
                "slot": "17-30",
                "symbols": ["000001.SZ"],
                "date": "2026-05-16",
                "as_of": "2026-05-16",
                "snapshot_type": "all",
            },
            created_by="web",
        )
    )

    assert result.status == "ok"
    assert fake_runner.calls[0]["workflow"].workflow_id == "scheduler"
    assert fake_runner.calls[0]["params"]["symbols"] == ["000001.SZ"]


def test_workflow_service_rejects_unconfirmed_high_risk_workflow() -> None:
    """高风险工作流未确认时不应创建 Job。"""
    from src.services import WorkflowService

    fake_runner = _FakeWorkflowRunner(calls=[])
    service = WorkflowService(workflow_runner=fake_runner)
    result = __import__("asyncio").run(
        service.run_workflow(
            workflow_id="install-config",
            params={"config_path": "config/app.yaml"},
            created_by="web",
        )
    )

    assert result.status == "error"
    assert result.message == "confirmation required for high-risk workflow"
    assert result.payload["workflow_id"] == "install-config"
    assert result.payload["requires_confirmation"] is True
    assert fake_runner.calls == []


def test_workflow_service_allows_confirmed_high_risk_workflow() -> None:
    """高风险工作流确认后应允许创建 Job。"""
    from src.services import WorkflowService

    fake_runner = _FakeWorkflowRunner(calls=[])
    service = WorkflowService(workflow_runner=fake_runner)
    result = __import__("asyncio").run(
        service.run_workflow(
            workflow_id="install-config",
            params={"config_path": "config/app.yaml"},
            created_by="web",
            confirmed=True,
        )
    )

    assert result.status == "ok"
    assert result.payload["workflow"]["workflow_id"] == "install-config"
    assert result.payload["job"]["job_type"] == "init-project"
    assert fake_runner.calls[0]["workflow"].workflow_id == "install-config"
    assert fake_runner.calls[0]["confirmed"] is True
