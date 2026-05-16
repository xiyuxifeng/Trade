from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

from src.services.workflow_service import WorkflowDefinition, WorkflowStep


@dataclass
class _FakeJobService:
    """WorkflowRunner 单测用的 JobService 替身。"""

    created_jobs: list[dict[str, Any]] = field(default_factory=list)
    started_jobs: list[dict[str, Any]] = field(default_factory=list)
    completed_jobs: list[dict[str, Any]] = field(default_factory=list)
    failed_jobs: list[dict[str, Any]] = field(default_factory=list)
    cancelled_jobs: list[dict[str, Any]] = field(default_factory=list)
    next_job_id: int = 1

    async def create_job(self, **kwargs: Any) -> Any:
        job_id = f"job-{self.next_job_id}"
        self.next_job_id += 1
        job = {
            "id": job_id,
            "job_type": kwargs["job_type"],
            "status": "pending",
            "params": kwargs.get("params", {}),
            "result": None,
            "error": None,
            "artifacts": [],
            "created_by": kwargs.get("created_by") or "system",
            "created_at": "2026-05-15T00:00:00+00:00",
            "updated_at": "2026-05-15T00:00:00+00:00",
            "started_at": None,
            "finished_at": None,
            "audit_events": [],
        }
        self.created_jobs.append(kwargs)
        return _result(
            {
                "created": True,
                "job": job,
                "job_dir": f"/tmp/{job_id}",
                "log_path": f"/tmp/{job_id}/job.log",
                "params_path": f"/tmp/{job_id}/params.json",
                "result_path": f"/tmp/{job_id}/result.json",
                "artifacts_path": f"/tmp/{job_id}/artifacts.json",
            }
        )

    async def start_job(self, **kwargs: Any) -> Any:
        self.started_jobs.append(kwargs)
        job = {
            "id": kwargs["job_id"],
            "job_type": "workflow-run",
            "status": "running",
            "params": {},
            "result": None,
            "error": None,
            "artifacts": [],
            "created_by": "web",
            "created_at": "2026-05-15T00:00:00+00:00",
            "updated_at": "2026-05-15T00:00:00+00:00",
            "started_at": "2026-05-15T00:00:00+00:00",
            "finished_at": None,
            "audit_events": [],
        }
        return _result({"job": job})

    async def complete_job(self, **kwargs: Any) -> Any:
        self.completed_jobs.append(kwargs)
        job = {
            "id": kwargs["job_id"],
            "job_type": "workflow-run",
            "status": "success",
            "params": {},
            "result": kwargs.get("result", {}),
            "error": None,
            "artifacts": [],
            "created_by": "web",
            "created_at": "2026-05-15T00:00:00+00:00",
            "updated_at": "2026-05-15T00:00:00+00:00",
            "started_at": "2026-05-15T00:00:00+00:00",
            "finished_at": "2026-05-15T00:01:00+00:00",
            "audit_events": [],
        }
        return _result(
            {
                "job": job,
                "job_dir": f"/tmp/{kwargs['job_id']}",
                "log_path": f"/tmp/{kwargs['job_id']}/job.log",
                "params_path": f"/tmp/{kwargs['job_id']}/params.json",
                "result_path": f"/tmp/{kwargs['job_id']}/result.json",
                "artifacts_path": f"/tmp/{kwargs['job_id']}/artifacts.json",
            }
        )

    async def fail_job(self, **kwargs: Any) -> Any:
        self.failed_jobs.append(kwargs)
        job = {
            "id": kwargs["job_id"],
            "job_type": "workflow-run",
            "status": "failed",
            "params": {},
            "result": None,
            "error": kwargs.get("error"),
            "artifacts": [],
            "created_by": "web",
            "created_at": "2026-05-15T00:00:00+00:00",
            "updated_at": "2026-05-15T00:00:00+00:00",
            "started_at": "2026-05-15T00:00:00+00:00",
            "finished_at": "2026-05-15T00:01:00+00:00",
            "audit_events": [],
        }
        return _result(
            {
                "job": job,
                "job_dir": f"/tmp/{kwargs['job_id']}",
                "log_path": f"/tmp/{kwargs['job_id']}/job.log",
                "params_path": f"/tmp/{kwargs['job_id']}/params.json",
                "result_path": f"/tmp/{kwargs['job_id']}/result.json",
                "artifacts_path": f"/tmp/{kwargs['job_id']}/artifacts.json",
            }
        )

    async def cancel_job(self, **kwargs: Any) -> Any:
        self.cancelled_jobs.append(kwargs)
        job = {
            "id": kwargs["job_id"],
            "job_type": "workflow-run",
            "status": "cancelled",
            "params": {},
            "result": None,
            "error": {"type": "cancelled", "message": kwargs.get("reason", "cancelled")},
            "artifacts": [],
            "created_by": "web",
            "created_at": "2026-05-15T00:00:00+00:00",
            "updated_at": "2026-05-15T00:00:00+00:00",
            "started_at": "2026-05-15T00:00:00+00:00",
            "finished_at": "2026-05-15T00:01:00+00:00",
            "audit_events": [],
        }
        return _result(
            {
                "job": job,
                "job_dir": f"/tmp/{kwargs['job_id']}",
                "log_path": f"/tmp/{kwargs['job_id']}/job.log",
                "params_path": f"/tmp/{kwargs['job_id']}/params.json",
                "result_path": f"/tmp/{kwargs['job_id']}/result.json",
                "artifacts_path": f"/tmp/{kwargs['job_id']}/artifacts.json",
            }
        )


@dataclass
class _FakeJobRunner:
    """WorkflowRunner 单测用的 JobRunner 替身。"""

    outcomes: dict[str, Any]
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def submit_job(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        job_type = kwargs["job_type"]
        outcome = self.outcomes.get(job_type)
        if outcome is None:
            outcome = {
                "status": "ok",
                "job": {
                    "id": f"{job_type}-job",
                    "job_type": job_type,
                    "status": "success",
                    "params": kwargs.get("params", {}),
                    "result": {"job_type": job_type},
                    "error": None,
                    "artifacts": [],
                    "started_at": "2026-05-15T00:00:00+00:00",
                    "finished_at": "2026-05-15T00:01:00+00:00",
                },
            }

        return _result(
            {
                "created": {
                    "created": True,
                    "job": {
                        "id": f"created-{job_type}",
                        "job_type": job_type,
                        "status": "pending",
                    },
                },
                "execution": {
                    "job": outcome["job"],
                    "result": outcome["job"].get("result"),
                    "result_path": f"/tmp/{job_type}/result.json",
                },
            },
            status=outcome.get("status", "ok"),
            message=outcome.get("message", "job executed"),
        )


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    return SimpleNamespace(status=status, message=message, payload=payload)


def _build_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="article-pipeline",
        title="Article Pipeline",
        description="test workflow",
        job_type="pipeline-run",
        permissions="operator",
        steps=[
            WorkflowStep(
                step_id="crawl",
                title="抓取文章",
                description="crawl",
                required_job_type="crawl",
                parameters=["config_path"],
                param_schema={"description": "crawl", "fields": {}, "allow_additional_fields": False},
                risk="low",
                requires_confirmation=False,
            ),
            WorkflowStep(
                step_id="pipeline-run",
                title="执行完整链路",
                description="pipeline",
                required_job_type="pipeline-run",
                parameters=["config_path"],
                param_schema={"description": "pipeline", "fields": {}, "allow_additional_fields": False},
                risk="low",
                requires_confirmation=False,
            ),
        ],
    )


def _build_market_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="scheduler",
        title="Market Scheduler",
        description="market workflow",
        job_type="kaipan-run",
        permissions="operator",
        steps=[
            WorkflowStep(
                step_id="kaipan-fetch",
                title="Kaipan 抓取",
                description="fetch",
                required_job_type="kaipan-fetch",
                parameters=["config_path", "trade_date", "slot"],
                param_schema={"description": "fetch", "fields": {}, "allow_additional_fields": False},
                risk="medium",
                requires_confirmation=False,
            ),
            WorkflowStep(
                step_id="kaipan-normalize",
                title="Kaipan 归一化",
                description="normalize",
                required_job_type="kaipan-normalize",
                parameters=["config_path", "trade_date", "slot"],
                param_schema={"description": "normalize", "fields": {}, "allow_additional_fields": False},
                risk="medium",
                requires_confirmation=False,
            ),
            WorkflowStep(
                step_id="kaipan-run",
                title="Kaipan 一键运行",
                description="run",
                required_job_type="kaipan-run",
                parameters=["config_path", "trade_date", "slot"],
                param_schema={"description": "run", "fields": {}, "allow_additional_fields": False},
                risk="medium",
                requires_confirmation=False,
            ),
            WorkflowStep(
                step_id="ohlcv-crawl",
                title="抓取 OHLCV",
                description="ohlcv",
                required_job_type="ohlcv-crawl",
                parameters=["config_path", "symbols", "start_date", "end_date"],
                param_schema={"description": "ohlcv", "fields": {}, "allow_additional_fields": False},
                risk="medium",
                requires_confirmation=False,
            ),
            WorkflowStep(
                step_id="market-state-build",
                title="构建市场状态",
                description="state",
                required_job_type="market-state-build",
                parameters=["config_path", "as_of"],
                param_schema={"description": "state", "fields": {}, "allow_additional_fields": False},
                risk="medium",
                requires_confirmation=False,
            ),
            WorkflowStep(
                step_id="snapshot-build",
                title="构建快照",
                description="snapshot",
                required_job_type="snapshot-build",
                parameters=["config_path", "date", "slot"],
                param_schema={"description": "snapshot", "fields": {}, "allow_additional_fields": False},
                risk="medium",
                requires_confirmation=False,
            ),
        ],
    )


def test_workflow_runner_executes_steps_in_order() -> None:
    """WorkflowRunner 应按步骤顺序执行并汇总结果。"""
    from src.services.workflow_runner import WorkflowRunner

    workflow = _build_workflow()
    job_service = _FakeJobService()
    job_runner = _FakeJobRunner(outcomes={})
    runner = WorkflowRunner(job_service=job_service, job_runner_factory=lambda _: job_runner, worker_id="runner-1")

    result = __import__("asyncio").run(
        runner.run_workflow(
            workflow=workflow,
            params={"config_path": "config/app.yaml"},
            created_by="web",
            idempotency_key="run-001",
            audit_source={"channel": "ui"},
        )
    )

    assert result.status == "ok"
    assert [call["job_type"] for call in job_runner.calls] == ["crawl", "pipeline-run"]
    assert job_service.created_jobs[0]["job_type"] == "pipeline-run"
    assert job_service.started_jobs[0]["job_id"] == "job-1"
    assert job_service.completed_jobs[0]["job_id"] == "job-1"
    assert result.payload["job"]["status"] == "success"
    assert result.payload["workflow_run"]["run_context"]["status"] == "success"
    assert result.payload["workflow_run"]["step_results"][0]["step_name"] == "crawl"
    assert result.payload["workflow_run"]["step_results"][1]["step_name"] == "pipeline-run"


def test_workflow_runner_stops_after_failed_step() -> None:
    """WorkflowRunner 遇到失败 step 时应停止后续执行并失败收口。"""
    from src.services.workflow_runner import WorkflowRunner

    workflow = _build_workflow()
    job_service = _FakeJobService()
    job_runner = _FakeJobRunner(
        outcomes={
            "crawl": {
                "status": "ok",
                "job": {
                    "id": "crawl-job",
                    "job_type": "crawl",
                    "status": "success",
                    "params": {"config_path": "config/app.yaml"},
                    "result": {"done": True},
                    "error": None,
                    "artifacts": [],
                    "started_at": "2026-05-15T00:00:00+00:00",
                    "finished_at": "2026-05-15T00:01:00+00:00",
                },
            },
            "pipeline-run": {
                "status": "error",
                "message": "handler failed",
                "job": {
                    "id": "pipeline-job",
                    "job_type": "pipeline-run",
                    "status": "failed",
                    "params": {"config_path": "config/app.yaml"},
                    "result": None,
                    "error": {"type": "system_error", "message": "boom"},
                    "artifacts": [],
                    "started_at": "2026-05-15T00:02:00+00:00",
                    "finished_at": "2026-05-15T00:03:00+00:00",
                },
            },
        }
    )
    runner = WorkflowRunner(job_service=job_service, job_runner_factory=lambda _: job_runner, worker_id="runner-1")

    result = __import__("asyncio").run(
        runner.run_workflow(
            workflow=workflow,
            params={"config_path": "config/app.yaml"},
            created_by="web",
            idempotency_key="run-002",
            audit_source={"channel": "ui"},
        )
    )

    assert result.status == "ok"
    assert [call["job_type"] for call in job_runner.calls] == ["crawl", "pipeline-run"]
    assert job_service.failed_jobs[0]["job_id"] == "job-1"
    assert result.payload["job"]["status"] == "failed"
    assert result.payload["workflow_run"]["run_context"]["status"] == "failed"
    assert len(result.payload["workflow_run"]["step_results"]) == 2
    assert result.payload["workflow_run"]["errors"][0]["type"] == "system_error"


def test_workflow_runner_executes_market_workflow_steps() -> None:
    """WorkflowRunner 应能按 scheduler market workflow 顺序执行 market 步骤。"""
    from src.services.workflow_runner import WorkflowRunner

    workflow = _build_market_workflow()
    job_service = _FakeJobService()
    job_runner = _FakeJobRunner(outcomes={})
    runner = WorkflowRunner(job_service=job_service, job_runner_factory=lambda _: job_runner, worker_id="runner-1")

    result = __import__("asyncio").run(
        runner.run_workflow(
            workflow=workflow,
            params={
                "config_path": "config/app.yaml",
                "trade_date": "2026-05-16",
                "slot": "17-30",
                "symbols": ["000001.SZ"],
                "as_of": "2026-05-16",
                "date": "2026-05-16",
            },
            created_by="web",
            idempotency_key="run-market-001",
            audit_source={"channel": "ui"},
        )
    )

    assert result.status == "ok"
    assert [call["job_type"] for call in job_runner.calls] == [
        "kaipan-fetch",
        "kaipan-normalize",
        "kaipan-run",
        "ohlcv-crawl",
        "market-state-build",
        "snapshot-build",
    ]
    assert job_runner.calls[0]["params"] == {
        "config_path": "config/app.yaml",
        "trade_date": "2026-05-16",
        "slot": "17-30",
    }
    assert job_runner.calls[3]["params"] == {
        "config_path": "config/app.yaml",
        "symbols": ["000001.SZ"],
    }
    assert job_runner.calls[4]["params"] == {
        "config_path": "config/app.yaml",
        "as_of": "2026-05-16",
    }
    assert job_runner.calls[5]["params"] == {
        "config_path": "config/app.yaml",
        "date": "2026-05-16",
        "slot": "17-30",
    }
    assert result.payload["workflow_run"]["run_context"]["status"] == "success"
    assert [step["step_name"] for step in result.payload["workflow_run"]["step_results"]] == [
        "kaipan-fetch",
        "kaipan-normalize",
        "kaipan-run",
        "ohlcv-crawl",
        "market-state-build",
        "snapshot-build",
    ]
