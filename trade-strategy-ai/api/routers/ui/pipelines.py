from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from src.services.job_service import JobService, get_job_service
from src.services.article_pipeline_schedule_service import (
    ArticlePipelineScheduleService,
    make_article_pipeline_schedule_service,
)
from src.services.pipeline_application_service import PipelineApplicationService, make_pipeline_application_service


router = APIRouter(prefix="/api/ui/v1/pipelines", tags=["ui-pipelines"])

ARTICLE_PIPELINE_ID = "article_pipeline"


class PipelineRunRequest(BaseModel):
    """Pipeline 运行请求体。"""

    params: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None
    idempotency_key: str | None = None
    confirmed: bool = False


class ArticlePipelineScheduleRequest(BaseModel):
    """Article pipeline schedule 请求体。"""

    profile_id: str | None = None
    schedule_time: str | None = None
    force: bool = False


def get_pipeline_application_service(job_service: JobService = Depends(get_job_service)) -> PipelineApplicationService:
    """获取 Pipeline API 使用的 Application Service。"""
    return make_pipeline_application_service(job_service=job_service)


def get_article_pipeline_schedule_service(
    job_service: JobService = Depends(get_job_service),
    pipeline_service: PipelineApplicationService = Depends(get_pipeline_application_service),
) -> ArticlePipelineScheduleService:
    """获取 article_pipeline 调度服务。"""
    return make_article_pipeline_schedule_service(job_service=job_service, pipeline_application_service=pipeline_service)


def _audit_source_from_request(request: Request) -> dict[str, Any]:
    """提取 Pipeline 运行请求来源。"""
    client_host = request.client.host if request.client is not None else None
    return {
        "channel": "ui",
        "path": request.url.path,
        "method": request.method,
        "client_host": client_host,
        "user_agent": request.headers.get("user-agent"),
        "forwarded_for": request.headers.get("x-forwarded-for"),
    }


def _structured_error(code: str, message: str, status_value: str, fields: dict[str, Any] | None = None) -> dict[str, Any]:
    """构造 UI API 使用的结构化错误。"""
    return {
        "code": code,
        "message": message,
        "status": status_value,
        "fields": fields or {},
    }


async def _load_article_pipeline(workflow_service: PipelineApplicationService) -> dict[str, Any]:
    """读取 article_pipeline 的 canonical workflow 定义。"""
    result = await workflow_service.get_pipeline(ARTICLE_PIPELINE_ID)
    if result.status == "partial":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_structured_error("pipeline_not_found", "pipeline not found", "not_found"),
        )
    if result.status != "ok":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_structured_error("pipeline_load_failed", result.message or "pipeline load failed", "error"),
        )

    pipeline = result.payload["pipeline"]
    return {
        "pipeline_id": ARTICLE_PIPELINE_ID,
        "workflow_id": ARTICLE_PIPELINE_ID,
        "job_type": pipeline.get("job_type"),
        "title": "article_pipeline",
        "description": "通过 Workflow/Job 体系运行文章处理主链路。",
        "workflow": pipeline["workflow"],
    }


@router.get("")
async def list_pipelines(
    workflow_service: PipelineApplicationService = Depends(get_pipeline_application_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """列出 Web UI 支持的 Pipeline。"""
    result = await workflow_service.list_pipelines()
    if result.status != "ok":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_structured_error("pipeline_load_failed", result.message or "pipeline listing failed", "error"))
    return result.payload


@router.get("/article_pipeline")
async def get_article_pipeline(
    workflow_service: PipelineApplicationService = Depends(get_pipeline_application_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """返回 article_pipeline 定义。"""
    return {"pipeline": await _load_article_pipeline(workflow_service)}


@router.get("/{pipeline_id}")
async def get_pipeline_by_id(
    pipeline_id: str,
    workflow_service: PipelineApplicationService = Depends(get_pipeline_application_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """返回指定 Pipeline 定义，用于统一处理未知 Pipeline。"""
    if pipeline_id != ARTICLE_PIPELINE_ID:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_structured_error("pipeline_not_found", "pipeline not found", "not_found"),
        )
    return {"pipeline": await _load_article_pipeline(workflow_service)}


@router.post("/article_pipeline/run")
async def run_article_pipeline(
    request: PipelineRunRequest,
    http_request: Request,
    workflow_service: PipelineApplicationService = Depends(get_pipeline_application_service),
    _role_principal: CurrentPrincipal = Depends(require_role("operator")),
) -> dict[str, Any]:
    """通过 PipelineApplicationService 创建 article_pipeline Job。"""
    result = await workflow_service.run_pipeline(
        pipeline_id=ARTICLE_PIPELINE_ID,
        params=request.params,
        created_by=request.created_by,
        idempotency_key=request.idempotency_key,
        confirmed=request.confirmed,
        audit_source=_audit_source_from_request(http_request),
    )
    if result.status == "partial":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_structured_error("pipeline_not_found", "pipeline not found", "not_found"),
        )
    if result.status != "ok":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_structured_error("pipeline_run_failed", result.message or "pipeline run failed", "error"),
        )
    return result.payload


@router.post("/article_pipeline/steps/{step_id}/run")
async def run_article_pipeline_step(
    step_id: str,
    request: PipelineRunRequest,
    http_request: Request,
    workflow_service: PipelineApplicationService = Depends(get_pipeline_application_service),
    _role_principal: CurrentPrincipal = Depends(require_role("operator")),
) -> dict[str, Any]:
    """通过 PipelineApplicationService 创建 article_pipeline 的单步 Job。"""
    result = await workflow_service.run_pipeline_step(
        pipeline_id=ARTICLE_PIPELINE_ID,
        step_id=step_id,
        params=request.params,
        created_by=request.created_by,
        idempotency_key=request.idempotency_key,
        confirmed=request.confirmed,
        audit_source=_audit_source_from_request(http_request),
    )
    if result.status == "partial":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_structured_error("pipeline_not_found", result.message or "pipeline not found", "not_found"),
        )
    if result.status != "ok":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_structured_error("pipeline_run_failed", result.message or "pipeline run failed", "error"),
        )
    return result.payload


@router.get("/article_pipeline/schedule/status")
async def get_article_pipeline_schedule_status(
    schedule_service: ArticlePipelineScheduleService = Depends(get_article_pipeline_schedule_service),
    _: str = Depends(require_role("operator")),
) -> dict[str, Any]:
    """返回 article_pipeline schedule 状态。"""
    result = await schedule_service.status()
    if result.status != "ok":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_structured_error("schedule_status_failed", result.message or "schedule status failed", "error"))
    payload = dict(result.payload)
    payload.pop("config_path", None)
    return payload


@router.post("/article_pipeline/schedule/start")
async def start_article_pipeline_schedule(
    request: ArticlePipelineScheduleRequest,
    schedule_service: ArticlePipelineScheduleService = Depends(get_article_pipeline_schedule_service),
    _: str = Depends(require_role("operator")),
) -> dict[str, Any]:
    """启动 article_pipeline schedule。"""
    if not request.schedule_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_structured_error("schedule_start_failed", "schedule_time is required", "error"),
        )
    if not request.profile_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_structured_error("schedule_start_failed", "profile_id is required", "error"),
        )
    try:
        result = await schedule_service.start(
            profile_id=request.profile_id,
            schedule_time=request.schedule_time,
            force=request.force,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_structured_error("schedule_start_failed", str(exc), "error")) from exc
    if result.status != "ok":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_structured_error("schedule_start_failed", result.message or "schedule start failed", "error"))
    payload = dict(result.payload)
    payload.pop("config_path", None)
    return payload


@router.post("/article_pipeline/schedule/stop")
async def stop_article_pipeline_schedule(
    request: ArticlePipelineScheduleRequest,
    schedule_service: ArticlePipelineScheduleService = Depends(get_article_pipeline_schedule_service),
    _: str = Depends(require_role("operator")),
) -> dict[str, Any]:
    """停止 article_pipeline schedule。"""
    result = await schedule_service.stop(profile_id=request.profile_id)
    if result.status != "ok":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_structured_error("schedule_stop_failed", result.message or "schedule stop failed", "error"))
    payload = dict(result.payload)
    payload.pop("config_path", None)
    return payload
