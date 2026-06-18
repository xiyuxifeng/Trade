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
        "ohlcv",
        "scheduler",
    } <= workflow_ids
    assert "snapshot" not in workflow_ids
    assert "backtest" not in workflow_ids
    assert "optimize" not in workflow_ids
    assert "optimize-rule-pool" not in workflow_ids
    assert "rule-pool" not in workflow_ids
    assert "pre-market" not in workflow_ids
    assert "after-close" not in workflow_ids
    assert "pipeline" not in workflow_ids

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


def test_workflow_service_rejects_legacy_stage5_scheduler_workflow() -> None:
    """Legacy Stage 5 scheduler workflow must not bypass system-data-operation."""
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

    assert result.status == "error"
    assert "system-data-operation" in (result.message or "")
    assert result.payload["replacement_job_type"] == "system-data-operation"
    assert fake_runner.calls == []


def test_workflow_service_rejects_market_scheduler_params_as_compatibility_only() -> None:
    """Scheduler workflow params are preserved as metadata but no longer submit raw jobs."""
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

    assert result.status == "error"
    assert "系统管理 -> 数据与调度" in (result.message or "")
    assert fake_runner.calls == []


def test_workflow_service_reports_removed_backtest_workflow() -> None:
    """已移除的 backtest 工作流应返回不可用状态。"""
    from src.services import WorkflowService

    fake_runner = _FakeWorkflowRunner(calls=[])
    service = WorkflowService(workflow_runner=fake_runner)
    result = __import__("asyncio").run(
        service.run_workflow(
            workflow_id="backtest",
            params={"profile_id": "default", "trader_id": "trader_a", "date_from": "2026-05-01", "date_to": "2026-05-16"},
            created_by="web",
        )
    )

    assert result.status == "partial"
    assert result.message == "workflow not found"
    assert result.payload["workflow_id"] == "backtest"
    assert fake_runner.calls == []
