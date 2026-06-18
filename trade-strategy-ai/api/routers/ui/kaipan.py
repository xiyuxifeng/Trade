from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies import verify_api_key
from src.services.config_profile_service import ConfigProfileService
from src.services.kaipan_service import KaipanService

router = APIRouter(prefix="/api/ui/v1", tags=["ui-kaipan"])
_LEGACY_SYSTEM_DATA_WRITE_REDIRECT = "该入口已退役，请使用 系统管理 -> 数据与调度 执行正式数据操作。"


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


async def _resolve_profile_id(preferred: str | None = None) -> str:
    """解析当前 UI 应使用的 Profile。"""
    return ConfigProfileService().resolve_runtime_profile_id(preferred)


async def _resolve_profile_runtime(preferred: str | None = None):
    """在主事件循环里解析 Profile runtime，避免把 DB 访问丢进线程。"""
    runtime_profile_id = await _resolve_profile_id(preferred)
    runtime = await ConfigProfileService().load_profile_runtime_config(runtime_profile_id)
    return runtime_profile_id, runtime


@router.post("/kaipan/fetch", dependencies=[Depends(verify_api_key)])
async def fetch_kaipan(
    trade_date: str | None = None,
    slot: str = "all",
    profile_id: str | None = None,
    service: KaipanService = Depends(get_kaipan_service),
):
    """抓取 Kaipan 数据并同步标准化。"""
    del trade_date, slot, profile_id, service
    raise HTTPException(status_code=409, detail=_LEGACY_SYSTEM_DATA_WRITE_REDIRECT)


@router.get("/kaipan/status", dependencies=[Depends(verify_api_key)])
async def kaipan_status(profile_id: str | None = None, service: KaipanService = Depends(get_kaipan_service)):
    """返回最新可用的 Kaipan 时间槽状态。"""
    runtime_profile_id, runtime = await _resolve_profile_runtime(profile_id)
    result = await asyncio.to_thread(service.status, runtime=runtime, profile_id=runtime_profile_id)
    return result.payload


@router.post("/kaipan/normalize", dependencies=[Depends(verify_api_key)])
async def normalize_kaipan(
    request: KaipanNormalizeRequest,
    profile_id: str | None = None,
    service: KaipanService = Depends(get_kaipan_service),
):
    """仅执行标准化。"""
    del request, profile_id, service
    raise HTTPException(status_code=409, detail=_LEGACY_SYSTEM_DATA_WRITE_REDIRECT)


@router.post("/kaipan/run", dependencies=[Depends(verify_api_key)])
async def run_kaipan(
    request: KaipanRunRequest,
    profile_id: str | None = None,
    service: KaipanService = Depends(get_kaipan_service),
):
    """构建或启动 Kaipan 调度计划。"""
    del request, profile_id, service
    raise HTTPException(status_code=409, detail=_LEGACY_SYSTEM_DATA_WRITE_REDIRECT)


@router.post("/kaipan/stop", dependencies=[Depends(verify_api_key)])
async def stop_kaipan(profile_id: str | None = None, service: KaipanService = Depends(get_kaipan_service)):
    """停止 Kaipan 调度器。"""
    del profile_id, service
    raise HTTPException(status_code=409, detail=_LEGACY_SYSTEM_DATA_WRITE_REDIRECT)
