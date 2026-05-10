from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class _FakeJobService:
    """WorkflowService 单测用的 JobService 替身。"""

    calls: list[dict[str, Any]]

    async def create_job(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return type(
            "Result",
            (),
            {
                "status": "ok",
                "message": "job created",
                "payload": {
                    "created": True,
                    "job": {
                        "id": "job-1",
                        "job_type": kwargs["job_type"],
                        "params": kwargs.get("params", {}),
                        "created_by": kwargs.get("created_by"),
                    },
                },
            },
        )()


def test_workflow_service_exports_and_lists_default_definitions() -> None:
    """WorkflowService 应可导入并返回默认工作流定义。"""
    from src.services import WorkflowService

    service = WorkflowService(job_service=_FakeJobService(calls=[]))
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


def test_workflow_service_runs_workflow_through_job_service() -> None:
    """WorkflowService 应将工作流运行映射到对应 Job。"""
    from src.services import WorkflowService

    fake_job_service = _FakeJobService(calls=[])
    service = WorkflowService(job_service=fake_job_service)
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
    assert fake_job_service.calls[0]["job_type"] == "run-pre-market"


def test_workflow_service_rejects_unconfirmed_high_risk_workflow() -> None:
    """高风险工作流未确认时不应创建 Job。"""
    from src.services import WorkflowService

    fake_job_service = _FakeJobService(calls=[])
    service = WorkflowService(job_service=fake_job_service)
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
    assert fake_job_service.calls == []


def test_workflow_service_allows_confirmed_high_risk_workflow() -> None:
    """高风险工作流确认后应允许创建 Job。"""
    from src.services import WorkflowService

    fake_job_service = _FakeJobService(calls=[])
    service = WorkflowService(job_service=fake_job_service)
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
    assert fake_job_service.calls[0]["job_type"] == "init-project"
