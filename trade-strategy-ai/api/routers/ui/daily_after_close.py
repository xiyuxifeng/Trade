from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from src.db.session import get_session_factory as async_session_factory
from src.services.post_close_actuals_service import (
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
