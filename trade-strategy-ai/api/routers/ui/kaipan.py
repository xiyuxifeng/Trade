from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.dependencies import verify_api_key
from src.services.kaipan_service import KaipanService

router = APIRouter(prefix="/api/ui/v1", tags=["ui-kaipan"])


class KaipanNormalizeRequest(BaseModel):
    """Kaipan 标准化请求体。"""

    trade_date: str | None = None
    slot: str = "all"


class KaipanRunRequest(BaseModel):
    """Kaipan 调度请求体。"""

    start_scheduler: bool = True
    block: bool = False


def get_kaipan_service() -> KaipanService:
    """构建 Kaipan 服务。"""
    return KaipanService()


@router.post("/kaipan/fetch", dependencies=[Depends(verify_api_key)])
async def fetch_kaipan(
    trade_date: str | None = None,
    slot: str = "all",
    profile_id: str | None = None,
    service: KaipanService = Depends(get_kaipan_service),
):
    """抓取 Kaipan 数据并同步标准化。"""
    result = await asyncio.to_thread(service.fetch, profile_id=profile_id, trade_date=trade_date, slot=slot)
    return result.payload


@router.get("/kaipan/status", dependencies=[Depends(verify_api_key)])
async def kaipan_status(profile_id: str | None = None, service: KaipanService = Depends(get_kaipan_service)):
    """返回最新可用的 Kaipan 时间槽状态。"""
    result = await asyncio.to_thread(service.status, profile_id=profile_id)
    return result.payload


@router.post("/kaipan/normalize", dependencies=[Depends(verify_api_key)])
async def normalize_kaipan(
    request: KaipanNormalizeRequest,
    profile_id: str | None = None,
    service: KaipanService = Depends(get_kaipan_service),
):
    """仅执行标准化。"""
    result = await asyncio.to_thread(
        service.normalize,
        profile_id=profile_id,
        trade_date=request.trade_date,
        slot=request.slot,
    )
    return result.payload


@router.post("/kaipan/run", dependencies=[Depends(verify_api_key)])
async def run_kaipan(
    request: KaipanRunRequest,
    profile_id: str | None = None,
    service: KaipanService = Depends(get_kaipan_service),
):
    """构建或启动 Kaipan 调度计划。"""
    result = await asyncio.to_thread(
        service.run,
        profile_id=profile_id,
        start_scheduler=request.start_scheduler,
        block=request.block,
    )
    return result.payload


@router.post("/kaipan/stop", dependencies=[Depends(verify_api_key)])
async def stop_kaipan(profile_id: str | None = None, service: KaipanService = Depends(get_kaipan_service)):
    """停止 Kaipan 调度器。"""
    result = await asyncio.to_thread(service.stop, profile_id=profile_id)
    return result.payload
