from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from src.common.config import ConfigError
from src.services.config_profile_service import ConfigProfileService


router = APIRouter(prefix="/api/ui/v1/profiles", tags=["ui-profiles"])


class ProfileImportRequest(BaseModel):
    """Profile 导入请求。"""

    profile_id: str
    config_path: str
    created_by: str | None = None


class ProfileEditDraftRequest(BaseModel):
    """Profile 编辑草稿。"""

    name: str | None = None
    environment: str | None = None
    sections: dict[str, Any] | None = None


class ProfileUpdateRequest(ProfileEditDraftRequest):
    """Profile 保存请求。"""

    confirmed: bool = False


class ProfileArchiveRequest(BaseModel):
    """Profile 归档请求。"""

    archived_by: str | None = None


def get_profile_service() -> ConfigProfileService:
    """获取 ProfileService 实例，便于测试覆盖。"""
    return ConfigProfileService()


def _ensure_profile_payload(service: ConfigProfileService, profile: Any) -> dict[str, Any]:
    """把 ORM Profile 转成 API payload。"""
    return service.serialize_profile(profile)


def _find_snapshot(payloads: list[dict[str, Any]], snapshot_id: str) -> dict[str, Any] | None:
    """在快照集合中查找指定 snapshot。"""
    for item in payloads:
        if str(item.get("snapshot_id") or item.get("profile_snapshot_id")) == snapshot_id:
            return item
    return None


@router.get("")
async def list_profiles(
    environment: str | None = Query(default=None),
    validation_status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    service: ConfigProfileService = Depends(get_profile_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """列出 Profile。"""
    profiles = await service.list_profiles()
    items = [_ensure_profile_payload(service, profile) for profile in profiles]
    if environment:
        items = [item for item in items if item["environment"] == environment]
    if validation_status:
        items = [item for item in items if item["validation_status"] == validation_status]
    total = len(items)
    paged = items[skip : skip + limit]
    return {"count": len(paged), "total": total, "skip": skip, "limit": limit, "items": paged}


@router.get("/{profile_id}")
async def get_profile(
    profile_id: str,
    service: ConfigProfileService = Depends(get_profile_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """返回 Profile 详情。"""
    result = await service.get_profile_detail_payload(profile_id)
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "profile not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "profile load failed")
    return result.payload


@router.get("/{profile_id}/edit")
async def get_profile_edit(
    profile_id: str,
    service: ConfigProfileService = Depends(get_profile_service),
    _role_principal: CurrentPrincipal = Depends(require_role("operator")),
) -> dict[str, Any]:
    """返回 Profile 编辑页数据。"""
    result = await service.build_profile_edit_payload(profile_id)
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "profile not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "profile edit payload failed")
    return result.payload


@router.post("/{profile_id}/validate")
async def validate_profile_update(
    profile_id: str,
    request: ProfileEditDraftRequest,
    service: ConfigProfileService = Depends(get_profile_service),
    _role_principal: CurrentPrincipal = Depends(require_role("operator")),
) -> dict[str, Any]:
    """校验 Profile 更新草稿。"""
    result = await service.validate_profile_update(profile_id, request.model_dump(mode="json"))
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "profile not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "profile validation failed")
    return result.payload


@router.put("/{profile_id}")
async def update_profile(
    profile_id: str,
    request: ProfileUpdateRequest,
    service: ConfigProfileService = Depends(get_profile_service),
    _role_principal: CurrentPrincipal = Depends(require_role("operator")),
) -> dict[str, Any]:
    """保存 Profile 更新。"""
    if not request.confirmed:
        raise HTTPException(status_code=400, detail="confirmation required")
    result = await service.save_profile_update(profile_id, request.model_dump(mode="json"), created_by="web")
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "profile not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "profile save failed")
    return result.payload


@router.post("/{profile_id}/archive")
async def archive_profile(
    profile_id: str,
    request: ProfileArchiveRequest,
    service: ConfigProfileService = Depends(get_profile_service),
    _role_principal: CurrentPrincipal = Depends(require_role("admin")),
) -> dict[str, Any]:
    """归档 Profile。"""
    result = await service.archive_profile(profile_id, archived_by=request.archived_by or "web")
    return {"profile": _ensure_profile_payload(service, result)}


@router.post("/import")
async def import_profile(
    request: ProfileImportRequest,
    service: ConfigProfileService = Depends(get_profile_service),
    _role_principal: CurrentPrincipal = Depends(require_role("operator")),
) -> dict[str, Any]:
    """从旧 config_path 导入正式 Profile。"""
    existing = await service.get_profile(request.profile_id)
    try:
        profile = await service.import_from_config_path(
            request.config_path,
            profile_id=request.profile_id,
            created_by=request.created_by or "web",
        )
        snapshot_result = await service.capture_profile_snapshot(
            profile.profile_id,
            source=request.config_path,
            config_path=Path(request.config_path),
        )
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "profile import failed") from exc
    if snapshot_result.status != "ok":
        raise HTTPException(status_code=400, detail=snapshot_result.message or "profile snapshot failed")
    return {
        "created": existing is None,
        "profile": _ensure_profile_payload(service, profile),
        "snapshot": snapshot_result.payload,
    }


@router.get("/{profile_id}/snapshots/{snapshot_id}")
async def get_profile_snapshot(
    profile_id: str,
    snapshot_id: str,
    service: ConfigProfileService = Depends(get_profile_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """返回单个 Profile snapshot。"""
    profile = await service.get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"profile not found: {profile_id}")
    snapshots = await service.list_profile_snapshots(profile_id)
    snapshot = _find_snapshot(snapshots, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="profile snapshot not found")
    linked_jobs = await service.list_profile_linked_jobs(profile_id)
    linked_job = None
    snapshot_job_id = snapshot.get("job_id")
    if snapshot_job_id:
        linked_job = next((job for job in linked_jobs if job.get("job_id") == snapshot_job_id), None)
    return {
        "profile": _ensure_profile_payload(service, profile),
        "snapshot": snapshot,
        "linked_job": linked_job,
    }


__all__ = ["get_profile_service", "router"]
