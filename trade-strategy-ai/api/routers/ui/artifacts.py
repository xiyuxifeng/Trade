from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from api.dependencies import verify_api_key
from src.services.artifact_service import ArtifactService


router = APIRouter(prefix="/api/ui/v1/artifacts", tags=["ui-artifacts"])


def get_artifact_service() -> ArtifactService:
    """获取 ArtifactService 实例，便于测试覆盖。"""
    return ArtifactService()


@router.get("")
async def list_artifacts(
    kind: str | None = Query(default=None),
    source: str | None = Query(default=None),
    job_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    artifact_service: ArtifactService = Depends(get_artifact_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """列出主要产物。"""
    result = await artifact_service.list_artifacts(kind=kind, source=source, job_id=job_id, q=q, skip=skip, limit=limit)
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "artifact listing failed")
    return result.payload


@router.get("/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    artifact_service: ArtifactService = Depends(get_artifact_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """返回单个产物的预览信息。"""
    result = await artifact_service.get_artifact(artifact_id)
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "artifact not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "artifact load failed")
    return result.payload


@router.get("/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    artifact_service: ArtifactService = Depends(get_artifact_service),
    _: str = Depends(verify_api_key),
) -> FileResponse:
    """下载单个产物文件。"""
    result = await artifact_service.get_artifact(artifact_id)
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "artifact not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "artifact load failed")

    path = Path(result.payload["path"])
    if not artifact_service.is_download_path_allowed(path):
        raise HTTPException(status_code=404, detail="artifact file not found")
    if not path.exists():
        raise HTTPException(status_code=404, detail="artifact file not found")
    return FileResponse(path, filename=result.payload.get("download_name") or path.name)
