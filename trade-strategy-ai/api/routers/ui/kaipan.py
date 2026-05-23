from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.dependencies import verify_api_key
from src.common.paths import resolve_project_path
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


def _config_path() -> Path:
    """读取当前 UI BFF 使用的配置文件路径。"""
    return resolve_project_path(os.environ.get("CONFIG_PATH", "config/app.yaml"))


def get_kaipan_service() -> KaipanService:
    """构建 Kaipan 服务。"""
    return KaipanService()


@router.post("/kaipan/fetch", dependencies=[Depends(verify_api_key)])
async def fetch_kaipan(
    trade_date: str | None = None,
    slot: str = "all",
    service: KaipanService = Depends(get_kaipan_service),
):
    """抓取 Kaipan 数据并同步标准化。"""
    result = service.fetch(config_path=_config_path(), trade_date=trade_date, slot=slot)
    return result.payload


@router.get("/kaipan/status", dependencies=[Depends(verify_api_key)])
async def kaipan_status(service: KaipanService = Depends(get_kaipan_service)):
    """返回最新可用的 Kaipan 时间槽状态。"""
    result = service.status(config_path=_config_path())
    return result.payload


@router.post("/kaipan/normalize", dependencies=[Depends(verify_api_key)])
async def normalize_kaipan(
    request: KaipanNormalizeRequest,
    service: KaipanService = Depends(get_kaipan_service),
):
    """仅执行标准化。"""
    result = service.normalize(config_path=_config_path(), trade_date=request.trade_date, slot=request.slot)
    return result.payload


@router.post("/kaipan/run", dependencies=[Depends(verify_api_key)])
async def run_kaipan(
    request: KaipanRunRequest,
    service: KaipanService = Depends(get_kaipan_service),
):
    """构建或启动 Kaipan 调度计划。"""
    result = service.run(
        config_path=_config_path(),
        start_scheduler=request.start_scheduler,
        block=request.block,
    )
    return result.payload


@router.post("/kaipan/stop", dependencies=[Depends(verify_api_key)])
async def stop_kaipan(service: KaipanService = Depends(get_kaipan_service)):
    """停止 Kaipan 调度器。"""
    result = service.stop(config_path=_config_path())
    return result.payload
