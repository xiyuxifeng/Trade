from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.dependencies import verify_api_key
from src.common.paths import resolve_project_path
from src.services.persona_service import PersonaService

router = APIRouter(prefix="/api/ui/v1", tags=["ui-persona"])


class MarketStateBuildRequest(BaseModel):
    """MarketState 构建请求体。"""

    benchmark_symbol: str
    as_of: str | None = None
    from_akshare: bool = False
    cache_csv: bool = True


def _config_path() -> Path:
    """读取当前 UI BFF 使用的配置文件路径。"""
    return resolve_project_path(os.environ.get("CONFIG_PATH", "config/app.yaml"))


def get_persona_service() -> PersonaService:
    """构建 Persona / MarketState 共享服务。"""
    return PersonaService()


@router.post("/persona/sample", dependencies=[Depends(verify_api_key)])
async def build_sample_clusters(service: PersonaService = Depends(get_persona_service)):
    """生成 Persona 样例聚类文件。"""
    result = service.build_sample_clusters(config_path=_config_path())
    return result.payload


@router.post("/persona/market-state/build", dependencies=[Depends(verify_api_key)])
async def build_market_state(
    request: MarketStateBuildRequest,
    service: PersonaService = Depends(get_persona_service),
):
    """构建 MarketState 快照。"""
    result = service.build_market_state(
        config_path=_config_path(),
        benchmark_symbol=request.benchmark_symbol,
        as_of=request.as_of,
        from_akshare=request.from_akshare,
        cache_csv=request.cache_csv,
    )
    payload = dict(result.payload)
    if "snapshot_path" not in payload and "market_state_path" in payload:
        payload["snapshot_path"] = payload["market_state_path"]
    return payload
