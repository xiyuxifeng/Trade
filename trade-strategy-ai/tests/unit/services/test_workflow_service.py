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
    assert any(item["workflow_id"] == "pre-market" for item in listed.payload["items"])


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
