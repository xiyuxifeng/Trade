from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowRunQueryPage(BaseModel):
    """Workflow run 查询分页信息。"""

    model_config = ConfigDict(from_attributes=True)

    total: int
    limit: int
    offset: int
    count: int


class WorkflowRunSummary(BaseModel):
    """Workflow run 主记录摘要。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_id: str
    workflow_title: str
    workflow_version: str
    status: str
    trigger_source: str
    created_by: str | None = None
    confirmed: bool = False
    idempotency_key: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    input_params_json: dict[str, Any] = Field(default_factory=dict)
    output_summary_json: dict[str, Any] = Field(default_factory=dict)
    error_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class WorkflowRunStepSummary(BaseModel):
    """Workflow run step 摘要。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_run_id: str
    step_id: str
    step_name: str
    step_order: int
    job_id: str | None = None
    job_type: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    input_json: dict[str, Any] = Field(default_factory=dict)
    output_json: dict[str, Any] = Field(default_factory=dict)
    error_json: dict[str, Any] | None = None
    artifact_refs_json: list[dict[str, Any]] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class WorkflowRunListResponse(BaseModel):
    """Workflow run 列表响应。"""

    model_config = ConfigDict(from_attributes=True)

    filters: dict[str, Any] = Field(default_factory=dict)
    page: WorkflowRunQueryPage
    items: list[WorkflowRunSummary] = Field(default_factory=list)


class WorkflowRunDetailResponse(BaseModel):
    """Workflow run 详情响应。"""

    model_config = ConfigDict(from_attributes=True)

    workflow_run: WorkflowRunSummary
    steps: list[WorkflowRunStepSummary] = Field(default_factory=list)
    page: WorkflowRunQueryPage


class WorkflowRunStepListResponse(BaseModel):
    """Workflow run step 列表响应。"""

    model_config = ConfigDict(from_attributes=True)

    workflow_run_id: str
    page: WorkflowRunQueryPage
    items: list[WorkflowRunStepSummary] = Field(default_factory=list)
