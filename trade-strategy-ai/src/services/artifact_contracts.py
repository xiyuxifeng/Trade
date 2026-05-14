from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.services.runtime_contracts import ArtifactRef, ConfigSnapshotRef, DatasetRef, SnapshotRef, StorageRef


class ArtifactCatalogItem(BaseModel):
    """产物目录项的对外契约。

    只暴露 UI 需要的解释性元数据，不暴露服务器绝对路径。
    """

    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    name: str
    title: str
    kind: str
    source: str
    exists: bool
    size_bytes: int | None = None
    modified_at: str | None = None
    previewable: bool = False
    job_id: str | None = None
    workflow_id: str | None = None
    step_id: str | None = None
    safe_download_url: str | None = None
    download_token: str | None = None
    download_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    storage_ref: StorageRef | None = None
    dataset_ref: DatasetRef | None = None
    snapshot_ref: SnapshotRef | None = None
    config_snapshot_ref: ConfigSnapshotRef | None = None
    preview: str | None = None


class ArtifactDetail(ArtifactCatalogItem):
    """产物详情契约。"""

    artifact_ref: ArtifactRef | None = None

