from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.dependencies import verify_api_key
from src.services.job_registry import get_job_definition, list_job_definitions, validate_job_submission


router = APIRouter(prefix="/api/ui/v1/jobs", tags=["ui-jobs"])


class JobSubmissionRequest(BaseModel):
    """UI 提交 Job 前的校验请求。"""

    job_type: str
    params: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None


@router.get("/definitions")
async def list_definitions(_: str = Depends(verify_api_key)) -> list[dict[str, Any]]:
    """返回所有 Job 白名单定义。"""
    return [definition.summary() for definition in list_job_definitions()]


@router.get("/definitions/{job_type}")
async def get_definition(job_type: str, _: str = Depends(verify_api_key)) -> dict[str, Any]:
    """返回单个 Job 定义。"""
    definition = get_job_definition(job_type)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"unknown job type: {job_type}")
    return definition.summary()


@router.post("/validate")
async def validate_submission(request: JobSubmissionRequest, _: str = Depends(verify_api_key)) -> dict[str, Any]:
    """校验 UI 提交的 Job 参数。"""
    result = validate_job_submission(job_type=request.job_type, params=request.params, created_by=request.created_by)
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "invalid job submission")
    return result.payload
