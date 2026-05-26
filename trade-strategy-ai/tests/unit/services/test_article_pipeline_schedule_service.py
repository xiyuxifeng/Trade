from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class _FakeJobService:
    """Article schedule service 单测用的 JobService 替身。"""

    list_calls: list[dict[str, Any]] = field(default_factory=list)

    async def list_jobs(self, **kwargs: Any) -> Any:
        self.list_calls.append(kwargs)
        return type(
            "Result",
            (),
            {
                "status": "ok",
                "message": "jobs listed",
                "payload": {
                    "count": 0,
                    "items": [],
                    "skip": kwargs.get("skip", 0),
                    "limit": kwargs.get("limit", 50),
                    "job_type": kwargs.get("job_type"),
                },
            },
        )()


@dataclass
class _PagedFakeJobService:
    """支持分页返回的 JobService 替身。"""

    list_calls: list[dict[str, Any]] = field(default_factory=list)

    async def list_jobs(self, **kwargs: Any) -> Any:
        self.list_calls.append(kwargs)
        skip = int(kwargs.get("skip", 0) or 0)
        limit = int(kwargs.get("limit", 50) or 50)
        items = []
        if skip == 0:
            items = [
                {
                    "id": f"job-success-{index}",
                    "job_type": "pipeline-run",
                    "status": "success",
                    "created_at": "2026-05-25T09:00:00+08:00",
                    "params": {"schedule_date": "2026-05-25"},
                }
                for index in range(limit)
            ]
        elif skip == limit:
            items = [
                {
                    "id": "job-success-target",
                    "job_type": "pipeline-run",
                    "status": "success",
                    "created_at": "2026-05-26T09:00:00+08:00",
                    "params": {"schedule_date": "2026-05-26"},
                }
            ]
        return type(
            "Result",
            (),
            {
                "status": "ok",
                "message": "jobs listed",
                "payload": {
                    "count": len(items),
                    "items": items,
                    "skip": skip,
                    "limit": limit,
                    "job_type": kwargs.get("job_type"),
                },
            },
        )()


@dataclass
class _FakePipelineApplicationService:
    """Article schedule service 单测用的 PipelineApplicationService 替身。"""

    run_calls: list[dict[str, Any]] = field(default_factory=list)

    async def run_pipeline(self, **kwargs: Any) -> Any:
        self.run_calls.append(kwargs)
        return type(
            "Result",
            (),
            {
                "status": "ok",
                "message": "pipeline completed",
                "payload": {
                    "job": {"id": "job-1", "job_type": "pipeline-run", "status": "success"},
                    "workflow": {"workflow_id": "article_pipeline", "job_type": "pipeline-run"},
                },
            },
        )()


def test_article_pipeline_schedule_service_can_start_stop_and_report_status(monkeypatch) -> None:
    """文章调度服务应支持启动、停止和状态查询。"""
    from src.services.article_pipeline_schedule_service import ArticlePipelineScheduleService
    from pathlib import Path

    async def _resolve_profile_config_path(self, profile_id: str) -> Path:
        return Path("config/app.yaml")

    monkeypatch.setattr("src.services.config_profile_service.ConfigProfileService.resolve_profile_config_path", _resolve_profile_config_path)

    service = ArticlePipelineScheduleService(
        job_service=_FakeJobService(),
        pipeline_application_service=_FakePipelineApplicationService(),
    )

    started = __import__("asyncio").run(
        service.start(
            profile_id="default",
            schedule_time="09:30",
            force=False,
        )
    )
    status = __import__("asyncio").run(service.status())
    stopped = __import__("asyncio").run(service.stop())
    post_stop_status = __import__("asyncio").run(service.status())

    assert started.status == "ok"
    assert started.payload["scheduler_started"] is True
    assert started.payload["profile_id"] == "default"
    assert status.payload["scheduler_started"] is True
    assert status.payload["schedule_time"] == "09:30"
    assert status.payload["profile_id"] == "default"
    assert stopped.payload["scheduler_started"] is False
    assert stopped.payload["profile_id"] == "default"
    assert post_stop_status.payload["profile_id"] == "default"


def test_article_pipeline_schedule_service_skips_completed_today_when_force_is_off(monkeypatch) -> None:
    """当天已有成功记录且 force=false 时，调度服务应直接返回已完成。"""
    from src.services.article_pipeline_schedule_service import ArticlePipelineScheduleService

    fake_job_service = _FakeJobService()

    async def _list_jobs(**kwargs: Any) -> Any:
        fake_job_service.list_calls.append(kwargs)
        return type(
            "Result",
            (),
            {
                "status": "ok",
                "message": "jobs listed",
                "payload": {
                    "count": 1,
                    "items": [
                        {
                            "id": "job-success-1",
                            "job_type": "pipeline-run",
                            "status": "success",
                            "created_at": "2026-05-26T09:00:00+08:00",
                            "params": {"schedule_date": "2026-05-26"},
                        }
                    ],
                },
            },
        )()

    fake_job_service.list_jobs = _list_jobs  # type: ignore[assignment]

    service = ArticlePipelineScheduleService(
        job_service=fake_job_service,
        pipeline_application_service=_FakePipelineApplicationService(),
    )

    result = __import__("asyncio").run(
        service.run_scheduled_pipeline(
            profile_id="default",
            force=False,
            schedule_date="2026-05-26",
        )
    )

    assert result.status == "ok"
    assert result.payload["message"] == "already completed"
    assert fake_job_service.list_calls[0]["status"] == "success"
    assert fake_job_service.list_calls[0]["job_type"] == "pipeline-run"
    assert "created_by" not in fake_job_service.list_calls[0]


def test_article_pipeline_schedule_service_scans_past_first_page_when_checking_today_completion(monkeypatch) -> None:
    """当天完成判定应分页扫描，而不是只看前一页。"""
    from src.services.article_pipeline_schedule_service import ArticlePipelineScheduleService

    service = ArticlePipelineScheduleService(
        job_service=_PagedFakeJobService(),
        pipeline_application_service=_FakePipelineApplicationService(),
    )

    result = __import__("asyncio").run(
        service.run_scheduled_pipeline(
            profile_id="default",
            force=False,
            schedule_date="2026-05-26",
        )
    )

    assert result.status == "ok"
    assert result.payload["message"] == "already completed"


def test_article_pipeline_schedule_service_returns_bound_config_path_when_started_with_custom_path() -> None:
    """调度状态与停止响应应回显真实绑定的 config_path。"""
    from src.services.article_pipeline_schedule_service import ArticlePipelineScheduleService

    service = ArticlePipelineScheduleService(
        job_service=_FakeJobService(),
        pipeline_application_service=_FakePipelineApplicationService(),
    )

    started = __import__("asyncio").run(
        service.start(
            config_path="config/custom.yaml",
            schedule_time="10:15",
            force=True,
        )
    )
    status = __import__("asyncio").run(service.status())
    stopped = __import__("asyncio").run(service.stop())
    post_stop_status = __import__("asyncio").run(service.status())

    assert started.payload["config_path"] == "config/custom.yaml"
    assert status.payload["config_path"] == "config/custom.yaml"
    assert stopped.payload["config_path"] == "config/custom.yaml"
    assert post_stop_status.payload["config_path"] == "config/custom.yaml"
