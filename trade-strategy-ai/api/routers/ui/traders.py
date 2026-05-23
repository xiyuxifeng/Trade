"""Trader 选项 UI 接口。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.dependencies import verify_api_key
from src.services.trader_option_service import TraderOptionService, make_trader_option_service

router = APIRouter(prefix="/api/ui/v1/traders", tags=["ui-traders"])


class TraderOptionListResponse(BaseModel):
    """Trader 选项列表响应。"""

    status: str = "success"
    count: int
    items: list[str]


def get_trader_option_service() -> TraderOptionService:
    """获取 Trader 选项服务。"""
    return make_trader_option_service()


@router.get("", response_model=TraderOptionListResponse)
async def list_trader_options(
    source: Literal["all", "strategy", "backtest"] = Query(default="all"),
    service: TraderOptionService = Depends(get_trader_option_service),
    _: str = Depends(verify_api_key),
) -> TraderOptionListResponse:
    """列出 trader_id 下拉选项。"""
    result = await service.list_trader_options(source=source)
    payload = result.payload or {"count": 0, "items": []}
    return TraderOptionListResponse.model_validate(payload)
