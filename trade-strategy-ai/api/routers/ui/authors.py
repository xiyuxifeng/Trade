from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from src.db.session import get_session_factory as async_session_factory
from src.domain.enums import AuthorProfileKind, FormalLifecycleState
from src.services.author_profile_service import (
    AuthorProfileDraftRequest,
    AuthorProfileService,
    AuthorProfileTransitionRequest,
)


router = APIRouter(prefix="/api/ui/v1/authors", tags=["ui-authors"])


def get_author_profile_service() -> AuthorProfileService:
    session_factory = async_session_factory()

    @asynccontextmanager
    async def _session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return AuthorProfileService(session_scope_factory=_session_scope)


def _actor_id(principal: CurrentPrincipal) -> str:
    return principal.api_key_label or principal.role or "anonymous"


def _serialize(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _error(status_code: int, message: str, impact: str, action: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"message": message, "impact": impact, "action": action},
    )


@router.get("/profiles")
async def list_author_profiles(
    author_id: UUID | None = None,
    profile_kind: AuthorProfileKind | None = None,
    lifecycle_state: FormalLifecycleState | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: AuthorProfileService = Depends(get_author_profile_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return await service.list_versions(
            actor_id=_actor_id(principal),
            actor_role=principal.role,
            author_id=author_id,
            profile_kind=profile_kind,
            lifecycle_state=lifecycle_state,
            limit=limit,
        )
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "你暂时不能查看作者画像版本。", "切换到有查看权限的账号。") from exc


@router.get("/profiles/{version_id}")
async def get_author_profile(
    version_id: str,
    principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: AuthorProfileService = Depends(get_author_profile_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return _serialize(await service.get_version(version_id, actor_id=_actor_id(principal), actor_role=principal.role))
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "你暂时不能查看作者画像版本。", "切换到有查看权限的账号。") from exc
    except LookupError as exc:
        raise _error(status.HTTP_404_NOT_FOUND, "未找到作者画像版本", "当前页面不能展示该版本。", "返回作者画像列表重新选择。") from exc


@router.post("/profiles", status_code=status.HTTP_201_CREATED)
async def create_author_profile_draft(
    request: AuthorProfileDraftRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: AuthorProfileService = Depends(get_author_profile_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return _serialize(await service.create_draft(request, actor_id=_actor_id(principal), actor_role=principal.role))
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "不会创建作者画像草稿。", "切换到有操作权限的账号。") from exc
    except ValueError as exc:
        raise _error(status.HTTP_409_CONFLICT, str(exc), "草稿未创建，已有正式画像不会被改写。", "修正证据、时间段或来源版本后重试。") from exc


@router.post("/profiles/{version_id}/submit-review")
async def submit_author_profile_review(
    version_id: str,
    request: AuthorProfileTransitionRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: AuthorProfileService = Depends(get_author_profile_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return _serialize(await service.submit_for_review(version_id, request, actor_id=_actor_id(principal), actor_role=principal.role))
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "画像不会进入审核。", "切换到有操作权限的账号。") from exc
    except LookupError as exc:
        raise _error(status.HTTP_404_NOT_FOUND, "未找到作者画像版本", "当前版本不能进入审核。", "返回列表重新选择。") from exc
    except ValueError as exc:
        raise _error(status.HTTP_409_CONFLICT, str(exc), "画像状态未改变。", "查看当前状态后再选择下一步。") from exc


@router.post("/profiles/{version_id}/publish")
async def publish_author_profile(
    version_id: str,
    request: AuthorProfileTransitionRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: AuthorProfileService = Depends(get_author_profile_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return _serialize(await service.publish(version_id, request, actor_id=_actor_id(principal), actor_role=principal.role))
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "画像不会发布。", "切换到有发布权限的账号。") from exc
    except LookupError as exc:
        raise _error(status.HTTP_404_NOT_FOUND, "未找到作者画像版本", "当前版本不能发布。", "返回列表重新选择。") from exc
    except ValueError as exc:
        raise _error(status.HTTP_409_CONFLICT, str(exc), "画像未发布，已有正式版本不会被自动覆盖。", "先人工归档冲突版本或调整时间段。") from exc


@router.post("/profiles/{version_id}/archive")
async def archive_author_profile(
    version_id: str,
    request: AuthorProfileTransitionRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: AuthorProfileService = Depends(get_author_profile_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return _serialize(await service.archive(version_id, request, actor_id=_actor_id(principal), actor_role=principal.role))
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "画像不会归档。", "切换到有操作权限的账号。") from exc
    except LookupError as exc:
        raise _error(status.HTTP_404_NOT_FOUND, "未找到作者画像版本", "当前版本不能归档。", "返回列表重新选择。") from exc
    except ValueError as exc:
        raise _error(status.HTTP_409_CONFLICT, str(exc), "画像状态未改变。", "查看当前状态后再选择下一步。") from exc


@router.get("/profiles/{from_version_id}/diff/{to_version_id}")
async def diff_author_profiles(
    from_version_id: str,
    to_version_id: str,
    principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: AuthorProfileService = Depends(get_author_profile_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return _serialize(
            await service.diff_versions(
                from_version_id,
                to_version_id,
                actor_id=_actor_id(principal),
                actor_role=principal.role,
            )
        )
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "你暂时不能比较作者画像版本。", "切换到有查看权限的账号。") from exc
    except LookupError as exc:
        raise _error(status.HTTP_404_NOT_FOUND, "未找到可比较的作者画像版本", "当前不能展示版本差异。", "返回列表重新选择两个版本。") from exc
