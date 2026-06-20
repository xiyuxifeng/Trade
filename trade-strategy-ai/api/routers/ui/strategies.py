from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from src.db.session import get_session_factory as async_session_factory
from src.services.strategy_center_service import StrategyCenterService, StrategyDraftRequest, StrategyTransitionRequest


router = APIRouter(prefix="/api/ui/v1/strategies", tags=["ui-strategies"])


def get_strategy_center_service() -> StrategyCenterService:
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

    return StrategyCenterService(session_scope_factory=_session_scope)


def _actor_id(principal: CurrentPrincipal) -> str:
    return principal.api_key_label or principal.role or "anonymous"


def _serialize(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _error(status_code: int, message: str, impact: str, action: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"message": message, "impact": impact, "action": action})


@router.get("")
async def list_strategies(
    limit: int = Query(default=50, ge=1, le=100),
    principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: StrategyCenterService = Depends(get_strategy_center_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return await service.list_versions(actor_id=_actor_id(principal), actor_role=principal.role, limit=limit)
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "你暂时不能查看正式策略。", "切换到有查看权限的账号。") from exc


@router.get("/draft-options")
async def get_strategy_draft_options(
    principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: StrategyCenterService = Depends(get_strategy_center_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return await service.get_draft_options(actor_id=_actor_id(principal), actor_role=principal.role)
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "你暂时不能查看策略草稿输入项。", "切换到有查看权限的账号。") from exc


@router.get("/{version_id}")
async def get_strategy_version(
    version_id: str,
    principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: StrategyCenterService = Depends(get_strategy_center_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return _serialize(await service.get_version(version_id, actor_id=_actor_id(principal), actor_role=principal.role))
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "你暂时不能查看该策略版本。", "切换到有查看权限的账号。") from exc
    except LookupError as exc:
        raise _error(status.HTTP_404_NOT_FOUND, "未找到策略版本", "当前页面不能展示该版本。", "返回策略中心重新选择。") from exc


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_strategy_draft(
    request: StrategyDraftRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: StrategyCenterService = Depends(get_strategy_center_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return _serialize(await service.create_draft(request, actor_id=_actor_id(principal), actor_role=principal.role))
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "不会保存策略草稿。", "切换到有操作权限的账号。") from exc
    except (LookupError, ValueError) as exc:
        raise _error(status.HTTP_409_CONFLICT, str(exc), "草稿未保存，正式策略不会被自动改写。", "修正正式规则、画像或证据绑定后重试。") from exc


@router.post("/{version_id}/submit-review")
async def submit_strategy_review(
    version_id: str,
    request: StrategyTransitionRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: StrategyCenterService = Depends(get_strategy_center_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return _serialize(await service.submit_for_review(version_id, request, actor_id=_actor_id(principal), actor_role=principal.role))
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "策略不会进入审核。", "切换到有操作权限的账号。") from exc
    except LookupError as exc:
        raise _error(status.HTTP_404_NOT_FOUND, "未找到策略版本", "当前版本不能进入审核。", "返回列表重新选择。") from exc
    except ValueError as exc:
        raise _error(status.HTTP_409_CONFLICT, str(exc), "策略状态未改变。", "查看当前状态后再选择下一步。") from exc


@router.post("/{version_id}/publish")
async def publish_strategy(
    version_id: str,
    request: StrategyTransitionRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: StrategyCenterService = Depends(get_strategy_center_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        return _serialize(await service.publish(version_id, request, actor_id=_actor_id(principal), actor_role=principal.role))
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "策略不会发布。", "切换到有发布权限的账号。") from exc
    except LookupError as exc:
        raise _error(status.HTTP_404_NOT_FOUND, "未找到策略版本", "当前版本不能发布。", "返回列表重新选择。") from exc
    except ValueError as exc:
        raise _error(status.HTTP_409_CONFLICT, str(exc), "策略未发布，当前正式版本不会被静默覆盖。", "先完成审核或修正正式输入后重试。") from exc
