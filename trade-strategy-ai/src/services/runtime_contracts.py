from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContractModel(BaseModel):
    """运行时 contract 的基础模型。

    统一提供 JSON 兼容序列化和反序列化入口，避免调用方自己处理嵌套结构。
    """

    model_config = ConfigDict(extra="forbid")

    def to_dict(self) -> dict[str, Any]:
        """将 contract 转成 JSON 兼容 dict。"""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContractModel":
        """从 JSON 兼容 dict 恢复 contract。"""
        return cls.model_validate(data)


class StepErrorType(StrEnum):
    """Step 执行错误分类。"""

    user_error = "user_error"
    system_error = "system_error"
    external_dependency = "external_dependency"
    permission = "permission"
    cancelled = "cancelled"


class UserContext(ContractModel):
    """触发运行的用户上下文。"""

    user_id: str
    username: str
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunContext(ContractModel):
    """一次 Job / Workflow 运行的公共上下文。"""

    run_id: str
    job_id: str | None = None
    workflow_id: str | None = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    trigger_source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StepInput(ContractModel):
    """单个 Step 的输入快照。"""

    step_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    input_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class StepError(ContractModel):
    """单个 Step 的结构化错误。"""

    type: StepErrorType
    message: str
    detail: str | None = None
    request_id: str | None = None
    code: str | None = None
    retryable: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetRef(ContractModel):
    """数据集逻辑引用，不暴露服务器绝对路径。"""

    dataset_id: str
    title: str | None = None
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SnapshotRef(ContractModel):
    """快照逻辑引用，不暴露服务器绝对路径。"""

    snapshot_id: str
    dataset_id: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConfigSnapshotRef(ContractModel):
    """配置快照引用，用于 Job 回溯和脱敏展示。"""

    config_snapshot_id: str
    config_source: str | None = None
    config_hash: str | None = None
    masked_snapshot: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StorageRef(ContractModel):
    """物理存储引用的抽象描述。

    业务层只应依赖这里的抽象字段，不直接依赖具体存储实现。
    """

    source: Literal["file", "db", "external"]
    logical_id: str
    relative_path: str | None = None
    uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("relative_path")
    @classmethod
    def _reject_absolute_path(cls, value: str | None) -> str | None:
        """阻止把服务器绝对路径写进 contract。"""
        if value and value.startswith("/"):
            raise ValueError("relative_path must not be an absolute path")
        return value


class ArtifactRef(ContractModel):
    """产物引用。

    只保留 Web UI 需要的解释性信息，不暴露服务器绝对路径。
    """

    artifact_id: str
    job_id: str
    workflow_id: str | None = None
    step_id: str | None = None
    kind: str
    title: str
    summary: str | None = None
    safe_download_url: str | None = None
    download_token: str | None = None
    size_bytes: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    visibility: Literal["public", "internal", "private"] = "internal"
    metadata: dict[str, Any] = Field(default_factory=dict)
    dataset_ref: DatasetRef | None = None
    snapshot_ref: SnapshotRef | None = None
    config_snapshot_ref: ConfigSnapshotRef | None = None
    storage_ref: StorageRef | None = None


class StepResult(ContractModel):
    """单个 Step 的执行结果。"""

    step_name: str
    status: Literal["success", "failed", "cancelled", "skipped"] = "success"
    payload: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    error: StepError | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunContext(ContractModel):
    """Workflow 执行总上下文。"""

    run_context: RunContext
    user_context: UserContext
    workflow_params: dict[str, Any] = Field(default_factory=dict)
    step_inputs: list[StepInput] = Field(default_factory=list)
    step_results: list[StepResult] = Field(default_factory=list)
    errors: list[StepError] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
