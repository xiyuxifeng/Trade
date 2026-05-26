from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class _FakeWorkflowRunner:
    """PipelineApplicationService 单测用的 WorkflowRunner 替身。"""

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


@dataclass
class _FakeJobRunner:
    """PipelineApplicationService 单测用的 JobRunner 替身。"""

    calls: list[dict[str, Any]]

    async def submit_job(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return type(
            "Result",
            (),
            {
                "status": "ok",
                "message": "job submitted",
                "payload": {
                    "created": {
                        "created": True,
                        "job": {
                            "id": "job-2",
                            "job_type": kwargs["job_type"],
                            "status": "success",
                        },
                    },
                    "execution": {
                        "job": {
                            "id": "job-2",
                            "job_type": kwargs["job_type"],
                            "status": "success",
                        },
                    },
                },
            },
        )()


@dataclass
class _FakeJobService:
    """PipelineApplicationService 单测用的 JobService 替身。"""

    list_responses: list[dict[str, Any]]
    list_calls: list[dict[str, Any]]

    async def list_jobs(self, **kwargs: Any) -> Any:
        self.list_calls.append(kwargs)
        index = min(len(self.list_calls) - 1, len(self.list_responses) - 1)
        payload = self.list_responses[index] if self.list_responses else {"count": 0, "items": []}
        return type(
            "Result",
            (),
            {
                "status": "ok",
                "message": "jobs listed",
                "payload": payload,
            },
        )()


def test_pipeline_application_service_lists_only_article_pipeline() -> None:
    """PipelineApplicationService 应只公开 article_pipeline canonical 入口。"""
    from src.services import PipelineApplicationService

    service = PipelineApplicationService()
    result = __import__("asyncio").run(service.list_pipelines())

    assert result.status == "ok"
    assert result.payload["count"] == 1
    assert result.payload["items"][0]["pipeline_id"] == "article_pipeline"
    assert result.payload["items"][0]["workflow_id"] == "article_pipeline"


def test_pipeline_application_service_returns_article_pipeline_detail() -> None:
    """PipelineApplicationService 应返回 article_pipeline 详情。"""
    from src.services import PipelineApplicationService

    service = PipelineApplicationService()
    result = __import__("asyncio").run(service.get_pipeline("article_pipeline"))

    assert result.status == "ok"
    assert result.payload["pipeline"]["pipeline_id"] == "article_pipeline"
    assert result.payload["pipeline"]["workflow_id"] == "article_pipeline"
    assert result.payload["pipeline"]["workflow"]["job_type"] == "pipeline-run"


def test_pipeline_application_service_runs_article_pipeline_through_workflow_runner(monkeypatch) -> None:
    """PipelineApplicationService 应通过 WorkflowRunner 运行 article_pipeline。"""
    from src.services import PipelineApplicationService
    from pathlib import Path
    from src.services.config_profile_service import ConfigProfileService

    async def _resolve_profile_config_path(self, profile_id: str) -> Path:
        return Path("config/app.yaml")

    monkeypatch.setattr(ConfigProfileService, "resolve_profile_config_path", _resolve_profile_config_path)

    fake_runner = _FakeWorkflowRunner(calls=[])
    service = PipelineApplicationService(workflow_runner=fake_runner)
    result = __import__("asyncio").run(
        service.run_pipeline(
            pipeline_id="article_pipeline",
            params={"profile_id": "default"},
            created_by="web",
            confirmed=True,
        )
    )

    assert result.status == "ok"
    assert result.payload["pipeline"]["pipeline_id"] == "article_pipeline"
    assert result.payload["job"]["job_type"] == "pipeline-run"
    assert fake_runner.calls[0]["workflow"].workflow_id == "article_pipeline"
    assert fake_runner.calls[0]["params"]["profile_id"] == "default"
    assert "config_path" not in fake_runner.calls[0]["params"]
    assert fake_runner.calls[0]["confirmed"] is True
    assert result.payload["profile_id"] == "default"


def test_pipeline_application_service_runs_single_article_step_through_job_runner(monkeypatch) -> None:
    """PipelineApplicationService 应支持单步运行并把 step 映射到对应 job。"""
    from src.services import PipelineApplicationService
    from pathlib import Path
    from src.services.config_profile_service import ConfigProfileService

    async def _resolve_profile_config_path(self, profile_id: str) -> Path:
        return Path("config/app.yaml")

    monkeypatch.setattr(ConfigProfileService, "resolve_profile_config_path", _resolve_profile_config_path)

    fake_job_runner = _FakeJobRunner(calls=[])
    service = PipelineApplicationService(job_runner=fake_job_runner)
    result = __import__("asyncio").run(
        service.run_pipeline_step(
            pipeline_id="article_pipeline",
            step_id="crawl",
            params={"profile_id": "default", "max_articles": 8, "force": True},
            created_by="web",
            confirmed=False,
        )
    )

    assert result.status == "ok"
    assert result.payload["job"]["job_type"] == "crawl"
    assert fake_job_runner.calls[0]["job_type"] == "crawl"
    assert fake_job_runner.calls[0]["params"]["profile_id"] == "default"
    assert fake_job_runner.calls[0]["params"]["force"] is True
    assert "config_path" not in fake_job_runner.calls[0]["params"]


def test_pipeline_application_service_rejects_validate_step_when_previous_profile_artifacts_do_not_match(monkeypatch) -> None:
    """validate step 不应被其他 Profile 的旧 clean job 放行。"""
    from pathlib import Path
    from src.services import PipelineApplicationService
    from src.services.config_profile_service import ConfigProfileService

    async def _resolve_profile_config_path(self, profile_id: str) -> Path:
        return Path("config/app.yaml")

    monkeypatch.setattr(ConfigProfileService, "resolve_profile_config_path", _resolve_profile_config_path)

    fake_job_service = _FakeJobService(
        list_responses=[
            {
                "count": 1,
                "items": [
                    {
                        "id": "job-clean-other",
                        "job_type": "clean",
                        "status": "success",
                        "created_at": "2026-05-26T09:00:00Z",
                        "params": {"profile_id": "other"},
                    }
                ],
            }
        ],
        list_calls=[],
    )
    fake_job_runner = _FakeJobRunner(calls=[])
    service = PipelineApplicationService(job_service=fake_job_service, job_runner=fake_job_runner)

    import pytest

    with pytest.raises(ValueError, match="请先执行 clean"):
        __import__("asyncio").run(
            service.run_pipeline_step(
                pipeline_id="article_pipeline",
                step_id="validate",
                params={"profile_id": "default", "force": False},
                created_by="web",
                confirmed=False,
            )
        )

    assert fake_job_service.list_calls[0]["job_type"] == "clean"
    assert fake_job_service.list_calls[0]["status"] == "success"


def test_pipeline_application_service_rejects_unknown_pipeline() -> None:
    """未知 pipeline 不应进入运行入口。"""
    from src.services import PipelineApplicationService

    service = PipelineApplicationService()
    result = __import__("asyncio").run(service.get_pipeline("unknown"))

    assert result.status == "partial"
    assert result.message == "pipeline not found"
