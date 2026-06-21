from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from src.db.session import get_session_factory as async_session_factory
from src.services.pre_market_readiness_service import PreMarketReadinessService


router = APIRouter(prefix="/api/ui/v1/daily/pre-market", tags=["ui-daily-pre-market"])


def get_pre_market_readiness_service() -> PreMarketReadinessService:
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

    return PreMarketReadinessService(session_scope_factory=_session_scope)


def _actor_id(principal: CurrentPrincipal) -> str:
    return principal.api_key_label or principal.role or "anonymous"


def _error(status_code: int, message: str, impact: str, action: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"message": message, "impact": impact, "action": action})


@router.get("/readiness")
async def get_pre_market_readiness(
    trade_date: str = Query(..., description="交易日，格式 YYYY-MM-DD"),
    principal: CurrentPrincipal = Depends(require_role("viewer")),
    service: PreMarketReadinessService = Depends(get_pre_market_readiness_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        result = await service.get_readiness(trade_date, actor_id=_actor_id(principal), actor_role=principal.role)
        return result.model_dump(mode="json")
    except PermissionError as exc:
        raise _error(status.HTTP_403_FORBIDDEN, str(exc), "当前账号不能查看正式盘前检查。", "切换到有查看权限的账号。") from exc
    except LookupError as exc:
        raise _error(
            status.HTTP_404_NOT_FOUND,
            "未找到今日盘前检查结果",
            "当前页面不能显示该交易日的正式盘前检查。",
            "确认交易日后重试。",
        ) from exc
    except ValueError as exc:
        raise _error(
            status.HTTP_400_BAD_REQUEST,
            str(exc),
            "当前请求的交易日无效，无法读取正式盘前检查。",
            "改成有效的交易日后重试。",
        ) from exc
