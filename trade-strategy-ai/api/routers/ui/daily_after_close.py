from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from src.db.session import get_session_factory as async_session_factory
from src.services.post_close_actuals_service import (
    OptimizationProposalAcceptRequest,
    OptimizationProposalGenerationRequest,
    OptimizationProposalReviewRequest,
    PostMarketReviewService,
    SignalOutcomeEvaluationRequest,
)


router = APIRouter(prefix="/api/ui/v1/daily/after-close", tags=["ui-daily-after-close"])


def get_post_market_review_service() -> PostMarketReviewService:
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

    return PostMarketReviewService(session_scope_factory=_session_scope)


def _actor_id(principal: CurrentPrincipal) -> str:
    return principal.api_key_label or principal.role or "anonymous"


def _error(status_code: int, message: str, impact: str, action: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"message": message, "impact": impact, "action": action})


@router.get("/actuals")
async def get_post_close_actuals(
    trading_day_plan_id: str = Query(..., description="已批准的每日计划 ID"),
    post_close_market_snapshot_id: str = Query(..., description="盘后行情快照 ID"),
    principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: PostMarketReviewService = Depends(get_post_market_review_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result = await service.get_actuals_for_signals(
            trading_day_plan_id=trading_day_plan_id,
            post_close_market_snapshot_id=post_close_market_snapshot_id,
            actor_id=_actor_id(principal),
            actor_role=principal.role,
        )
        return result.model_dump(mode="json")
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "当前账号不能查看盘后信号实际结果。", "切换到有查看权限的账号。") from exc
    except LookupError as exc:
        raise _error(
            status.HTTP_404_NOT_FOUND,
            "未找到盘后信号实际结果",
            "当前页面不能显示该每日计划的正式盘后行情结果。",
            "确认每日计划和盘后行情快照后重试。",
        ) from exc
    except ValueError as exc:
        raise _error(status.HTTP_400_BAD_REQUEST, str(exc), "当前请求无效，无法读取盘后信号实际结果。", "修正请求后重试。") from exc


@router.get("/review")
async def get_post_market_review(
    trading_day_plan_id: str = Query(..., description="每日运行计划 ID"),
    post_market_review_id: str | None = Query(default=None, description="盘后复盘 ID"),
    principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: PostMarketReviewService = Depends(get_post_market_review_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result = await service.get_post_market_review(
            trading_day_plan_id=trading_day_plan_id,
            post_market_review_id=post_market_review_id,
            actor_id=_actor_id(principal),
            actor_role=principal.role,
        )
        return result.model_dump(mode="json")
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "当前账号不能查看正式盘后复盘。", "切换到有查看权限的账号。") from exc
    except LookupError as exc:
        raise _error(status.HTTP_404_NOT_FOUND, "未找到正式盘后复盘", "当前页面不能显示该每日计划的盘后复盘。", "确认每日计划和盘后复盘后重试。") from exc
    except ValueError as exc:
        raise _error(status.HTTP_400_BAD_REQUEST, str(exc), "当前请求无效，无法读取正式盘后复盘。", "修正请求后重试。") from exc


@router.post("/signal-results")
async def evaluate_signal_results(
    request: SignalOutcomeEvaluationRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: PostMarketReviewService = Depends(get_post_market_review_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result = await service.evaluate_signal_outcomes(
            request,
            actor_id=_actor_id(principal),
            actor_role=principal.role,
        )
        return result.model_dump(mode="json")
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "当前账号不能评估盘后信号结果。", "切换到有操作权限的账号。") from exc
    except LookupError as exc:
        raise _error(
            status.HTTP_404_NOT_FOUND,
            "未找到盘后信号评估所需记录",
            "当前页面不能完成该每日计划的盘后信号评估。",
            "确认每日计划、盘后行情快照和信号记录后重试。",
        ) from exc
    except ValueError as exc:
        raise _error(status.HTTP_400_BAD_REQUEST, str(exc), "当前评估请求无效，无法生成盘后信号结果。", "修正请求后重试。") from exc


@router.post("/proposals/generate")
async def generate_optimization_proposals(
    request: OptimizationProposalGenerationRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: PostMarketReviewService = Depends(get_post_market_review_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result = await service.generate_optimization_proposals(
            request,
            actor_id=_actor_id(principal),
            actor_role=principal.role,
        )
        return result.model_dump(mode="json")
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "当前账号不能生成盘后优化建议。", "切换到有操作权限的账号。") from exc
    except LookupError as exc:
        raise _error(status.HTTP_404_NOT_FOUND, "未找到盘后复盘记录", "当前页面不能生成本次优化建议。", "确认已完成盘后结果评估和结构化归因后重试。") from exc
    except ValueError as exc:
        raise _error(status.HTTP_409_CONFLICT, str(exc), "当前建议未生成，正式对象不会被改写。", "修正证据状态后重新生成。") from exc


@router.get("/proposals")
async def list_optimization_proposals(
    post_market_review_id: str | None = Query(default=None, description="盘后复盘 ID"),
    proposal_type: str | None = Query(default=None, description="建议类型"),
    limit: int = Query(default=50, ge=1, le=100),
    principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: PostMarketReviewService = Depends(get_post_market_review_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result = await service.list_optimization_proposals(
            actor_id=_actor_id(principal),
            actor_role=principal.role,
            post_market_review_id=post_market_review_id,
            proposal_type=proposal_type,
            limit=limit,
        )
        return result.model_dump(mode="json")
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "当前账号不能查看盘后优化建议。", "切换到有查看权限的账号。") from exc
    except ValueError as exc:
        raise _error(status.HTTP_400_BAD_REQUEST, str(exc), "当前请求无效，无法读取盘后优化建议。", "修正查询条件后重试。") from exc


@router.get("/proposals/{proposal_id}")
async def get_optimization_proposal(
    proposal_id: str,
    principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: PostMarketReviewService = Depends(get_post_market_review_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result = await service.get_optimization_proposal(
            proposal_id,
            actor_id=_actor_id(principal),
            actor_role=principal.role,
        )
        return result.model_dump(mode="json")
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "当前账号不能查看该盘后优化建议。", "切换到有查看权限的账号。") from exc
    except LookupError as exc:
        raise _error(status.HTTP_404_NOT_FOUND, "未找到盘后优化建议", "当前页面不能展示该建议。", "返回建议列表重新选择。") from exc


@router.post("/proposals/{proposal_id}/review")
async def review_optimization_proposal(
    proposal_id: str,
    request: OptimizationProposalReviewRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: PostMarketReviewService = Depends(get_post_market_review_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result = await service.review_optimization_proposal(
            proposal_id,
            request,
            actor_id=_actor_id(principal),
            actor_role=principal.role,
        )
        return result.model_dump(mode="json")
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "当前账号不能处理盘后优化建议。", "切换到有操作权限的账号。") from exc
    except LookupError as exc:
        raise _error(status.HTTP_404_NOT_FOUND, "未找到盘后优化建议", "当前建议不能处理。", "返回建议列表重新选择。") from exc
    except ValueError as exc:
        raise _error(status.HTTP_409_CONFLICT, str(exc), "当前建议状态未改变。", "查看当前状态后再选择下一步。") from exc


@router.post("/proposals/{proposal_id}/accept-to-draft")
async def accept_optimization_proposal_to_draft(
    proposal_id: str,
    request: OptimizationProposalAcceptRequest,
    principal: CurrentPrincipal = Depends(require_role("operator")),
    service: PostMarketReviewService = Depends(get_post_market_review_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result = await service.accept_optimization_proposal_to_draft(
            proposal_id,
            request,
            actor_id=_actor_id(principal),
            actor_role=principal.role,
        )
        return result.model_dump(mode="json")
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "当前账号不能把建议转成草稿。", "切换到有操作权限的账号。") from exc
    except LookupError as exc:
        raise _error(status.HTTP_404_NOT_FOUND, "未找到盘后优化建议", "当前建议不能生成草稿。", "返回建议列表重新选择。") from exc
    except ValueError as exc:
        raise _error(status.HTTP_409_CONFLICT, str(exc), "正式对象不会被发布或静默改写。", "仅对允许的策略修订建议执行生成草稿。") from exc
