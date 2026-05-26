"""Pipeline UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app


@dataclass
class _FakePipelineApplicationService:
    """Pipeline API 测试用的 PipelineApplicationService 替身。"""

    run_calls: list[dict[str, Any]] = field(default_factory=list)
    schedule_started: bool = False
    schedule_time: str | None = None
    schedule_profile_id: str | None = None
    schedule_force: bool = False

    async def list_pipelines(self) -> Any:
        return _result(
            {
                "count": 1,
                "items": [
                    {
                        "pipeline_id": "article_pipeline",
                        "workflow_id": "article_pipeline",
                        "job_type": "pipeline-run",
                        "title": "article_pipeline",
                        "description": "通过 Workflow/Job 体系运行文章处理主链路。",
                    }
                ],
            }
        )

    async def get_pipeline(self, pipeline_id: str) -> Any:
        assert pipeline_id == "article_pipeline"
        return _result(
            {
                "pipeline": {
                    "pipeline_id": "article_pipeline",
                    "workflow_id": "article_pipeline",
                    "job_type": "pipeline-run",
                    "title": "article_pipeline",
                    "description": "通过 Workflow/Job 体系运行文章处理主链路。",
                    "workflow": {
                        "workflow_id": "article_pipeline",
                        "job_type": "pipeline-run",
                    },
                }
            }
        )

    async def run_pipeline(self, **kwargs: Any) -> Any:
        self.run_calls.append(kwargs)
        return _result(
            {
                "pipeline": {"pipeline_id": "article_pipeline", "workflow_id": "article_pipeline"},
                "workflow": {"workflow_id": "article_pipeline", "job_type": "pipeline-run"},
                "job": {"id": "job-article-1", "job_type": "pipeline-run", "status": "pending"},
            }
        )

    async def run_pipeline_step(self, **kwargs: Any) -> Any:
        self.run_calls.append(kwargs)
        return _result(
            {
                "pipeline": {"pipeline_id": "article_pipeline", "workflow_id": "article_pipeline"},
                "workflow": {"workflow_id": "article_pipeline", "job_type": kwargs.get("step_id", "crawl")},
                "job": {"id": "job-article-step-1", "job_type": kwargs.get("step_id", "crawl"), "status": "pending"},
            }
        )

    async def start_schedule(self, **kwargs: Any) -> Any:
        self.run_calls.append({"schedule_start": kwargs})
        self.schedule_started = True
        self.schedule_time = kwargs.get("schedule_time")
        self.schedule_profile_id = kwargs.get("profile_id")
        self.schedule_force = bool(kwargs.get("force"))
        return _result({"scheduler_started": True, "schedule_time": self.schedule_time, "profile_id": self.schedule_profile_id})

    async def stop_schedule(self, **kwargs: Any) -> Any:
        self.run_calls.append({"schedule_stop": kwargs})
        self.schedule_started = False
        return _result({"scheduler_started": False, "schedule_time": self.schedule_time, "profile_id": self.schedule_profile_id})

    async def schedule_status(self, **kwargs: Any) -> Any:
        self.run_calls.append({"schedule_status": kwargs})
        return _result({"scheduler_started": self.schedule_started, "schedule_time": self.schedule_time, "profile_id": self.schedule_profile_id, "force": self.schedule_force})


@dataclass
class _FakeJobService:
    """Pipeline API 调度测试用的 JobService 替身。"""

    async def list_jobs(self, **_: Any) -> Any:
        return _result({"count": 0, "items": []})


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    """构造测试用 ServiceResult 替身。"""
    from types import SimpleNamespace

    return SimpleNamespace(status=status, message=message, payload=payload)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建带认证覆盖的测试客户端。"""
    from api.routers.ui.pipelines import get_pipeline_application_service
    from api.routers.ui.jobs import get_job_service

    fake_service = _FakePipelineApplicationService()
    fake_job_service = _FakeJobService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="operator",
            api_key_label="Operator",
            authenticated=True,
            source="api_key",
            api_key="operator-key",
        )
        app.dependency_overrides[get_pipeline_application_service] = lambda: fake_service
        app.dependency_overrides[get_job_service] = lambda: fake_job_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.fake_service = fake_service  # type: ignore[attr-defined]
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_article_pipeline_list_detail_and_run(client: AsyncClient) -> None:
    """Pipeline UI API 应暴露 article_pipeline 列表、详情和运行入口。"""
    listed = await client.get("/api/ui/v1/pipelines")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["pipeline_id"] == "article_pipeline"
    assert listed.json()["items"][0]["workflow_id"] == "article_pipeline"

    detail = await client.get("/api/ui/v1/pipelines/article_pipeline")
    assert detail.status_code == 200
    assert detail.json()["pipeline"]["pipeline_id"] == "article_pipeline"
    assert detail.json()["pipeline"]["workflow"]["job_type"] == "pipeline-run"

    run = await client.post(
        "/api/ui/v1/pipelines/article_pipeline/run",
        json={"params": {"config_path": "config/app.yaml"}, "created_by": "web"},
    )
    assert run.status_code == 200
    assert run.json()["job"]["id"] == "job-article-1"
    assert client.fake_service.run_calls[0]["pipeline_id"] == "article_pipeline"  # type: ignore[attr-defined]
    assert client.fake_service.run_calls[0]["confirmed"] is False  # type: ignore[attr-defined]
    assert client.fake_service.run_calls[0]["audit_source"]["path"] == "/api/ui/v1/pipelines/article_pipeline/run"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_article_pipeline_step_run_and_schedule_control(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pipeline UI API 应支持 step 运行和 schedule 控制。"""
    from pathlib import Path

    async def _resolve_profile_config_path(self, profile_id: str) -> Path:
        return Path("config/app.yaml")

    from src.services.config_profile_service import ConfigProfileService

    monkeypatch.setattr(ConfigProfileService, "resolve_profile_config_path", _resolve_profile_config_path)

    step_run = await client.post(
        "/api/ui/v1/pipelines/article_pipeline/steps/crawl/run",
        json={"params": {"profile_id": "default", "force": True}, "created_by": "web"},
    )
    assert step_run.status_code == 200
    assert step_run.json()["job"]["job_type"] == "crawl"
    assert client.fake_service.run_calls[-1]["step_id"] == "crawl"  # type: ignore[attr-defined]

    schedule_start = await client.post(
        "/api/ui/v1/pipelines/article_pipeline/schedule/start",
        json={"profile_id": "default", "schedule_time": "09:30", "force": False},
    )
    assert schedule_start.status_code == 200
    assert schedule_start.json()["scheduler_started"] is True
    assert schedule_start.json()["profile_id"] == "default"

    schedule_status = await client.get("/api/ui/v1/pipelines/article_pipeline/schedule/status")
    assert schedule_status.status_code == 200
    assert schedule_status.json()["scheduler_started"] is True
    assert schedule_status.json()["profile_id"] == "default"

    schedule_stop = await client.post("/api/ui/v1/pipelines/article_pipeline/schedule/stop", json={"profile_id": "default"})
    assert schedule_stop.status_code == 200
    assert schedule_stop.json()["scheduler_started"] is False
    assert schedule_stop.json()["profile_id"] == "default"


@pytest.mark.asyncio
async def test_unknown_pipeline_uses_structured_error(client: AsyncClient) -> None:
    """未知 Pipeline 应返回统一错误结构。"""
    response = await client.get("/api/ui/v1/pipelines/unknown")
    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "pipeline_not_found",
        "message": "pipeline not found",
        "status": "not_found",
        "fields": {},
    }


@pytest.mark.asyncio
async def test_viewer_cannot_run_article_pipeline(client: AsyncClient) -> None:
    """viewer 不能运行 article_pipeline。"""
    previous = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="viewer",
        api_key_label="Viewer",
        authenticated=True,
        source="api_key",
        api_key="viewer-key",
    )
    try:
        response = await client.post(
            "/api/ui/v1/pipelines/article_pipeline/run",
            json={"params": {"config_path": "config/app.yaml"}, "created_by": "web"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "insufficient permissions"
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous
