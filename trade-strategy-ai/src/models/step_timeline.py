from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StepTimelineStatus(StrEnum):
    """Step Timeline 的状态枚举。"""

    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"
    skipped = "skipped"


class StepTimelineItem(BaseModel):
    """Job / Workflow 执行过程中的单个时间线节点。"""

    model_config = ConfigDict(extra="forbid")

    step_id: str
    step_name: str
    title: str
    status: Literal["pending", "running", "success", "failed", "cancelled", "skipped"] = "pending"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    error: dict[str, Any] | None = None
    artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    order: int = 0
    operation: str | None = None
    actor: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobTimeline(BaseModel):
    """Job 时间线的结构化结果。"""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    job_status: str
    items: list[StepTimelineItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def count(self) -> int:
        """返回时间线条目数。"""
        return len(self.items)

    def to_payload(self) -> dict[str, Any]:
        """转成 API 可直接返回的 payload。"""
        return {
            "job_id": self.job_id,
            "job_status": self.job_status,
            "count": self.count,
            "items": [item.model_dump(mode="json") for item in self.items],
            "metadata": self.metadata,
        }
