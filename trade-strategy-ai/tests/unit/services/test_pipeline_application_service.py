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


def test_pipeline_application_service_runs_article_pipeline_through_workflow_runner() -> None:
    """PipelineApplicationService 应通过 WorkflowRunner 运行 article_pipeline。"""
    from src.services import PipelineApplicationService

    fake_runner = _FakeWorkflowRunner(calls=[])
    service = PipelineApplicationService(workflow_runner=fake_runner)
    result = __import__("asyncio").run(
        service.run_pipeline(
            pipeline_id="article_pipeline",
            params={"config_path": "config/app.yaml"},
            created_by="web",
            confirmed=True,
        )
    )

    assert result.status == "ok"
    assert result.payload["pipeline"]["pipeline_id"] == "article_pipeline"
    assert result.payload["job"]["job_type"] == "pipeline-run"
    assert fake_runner.calls[0]["workflow"].workflow_id == "article_pipeline"
    assert fake_runner.calls[0]["params"]["config_path"].endswith("config/app.yaml")


def test_pipeline_application_service_rejects_unknown_pipeline() -> None:
    """未知 pipeline 不应进入运行入口。"""
    from src.services import PipelineApplicationService

    service = PipelineApplicationService()
    result = __import__("asyncio").run(service.get_pipeline("unknown"))

    assert result.status == "partial"
    assert result.message == "pipeline not found"
