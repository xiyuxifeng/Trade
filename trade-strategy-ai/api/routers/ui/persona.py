from __future__ import annotations

import inspect

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from pydantic import BaseModel

from api.dependencies import verify_api_key
from src.persona.behavior_rules import load_behavior_rules_preview
from src.services.config_profile_service import ConfigProfileService
from src.services.persona_service import PersonaService

router = APIRouter(prefix="/api/ui/v1", tags=["ui-persona"])


class MarketStateBuildRequest(BaseModel):
    """MarketState 构建请求体。"""

    benchmark_symbol: str
    as_of: str | None = None
    from_akshare: bool = False
    cache_csv: bool = True


async def _resolve_profile_id(preferred: str | None = None) -> str:
    """读取当前 UI BFF 使用的 Profile。"""
    service = ConfigProfileService()
    return service.resolve_runtime_profile_id(preferred)


def get_persona_service() -> PersonaService:
    """构建 Persona / MarketState 共享服务。"""
    return PersonaService()


@router.post("/persona/sample", dependencies=[Depends(verify_api_key)])
async def build_sample_clusters(
    profile_id: str | None = None,
    service: PersonaService = Depends(get_persona_service),
):
    """生成 Persona 样例聚类文件。"""
    runtime_profile_id = await _resolve_profile_id(profile_id)
    maybe_result = service.build_sample_clusters(profile_id=runtime_profile_id)
    result = await maybe_result if inspect.isawaitable(maybe_result) else maybe_result
    payload = dict(result.payload)
    payload.pop("config_path", None)
    return payload


@router.get("/persona/rules", dependencies=[Depends(verify_api_key)])
async def list_behavior_rules():
    """返回行为标签规则的只读预览。"""
    try:
        preview = load_behavior_rules_preview()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"行为规则文件不存在: {exc.filename or 'config/rules/behavior_rules.yaml'}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return preview.to_payload()


@router.post("/persona/market-state/build", dependencies=[Depends(verify_api_key)])
async def build_market_state(
    request: MarketStateBuildRequest,
    profile_id: str | None = None,
    service: PersonaService = Depends(get_persona_service),
):
    """构建 MarketState 快照。"""
    runtime_profile_id = await _resolve_profile_id(profile_id)
    maybe_result = service.build_market_state(
        profile_id=runtime_profile_id,
        benchmark_symbol=request.benchmark_symbol,
        as_of=request.as_of,
        from_akshare=request.from_akshare,
        cache_csv=request.cache_csv,
    )
    result = await maybe_result if inspect.isawaitable(maybe_result) else maybe_result
    payload = dict(result.payload)
    payload.pop("config_path", None)
    if "snapshot_path" not in payload and "market_state_path" in payload:
        payload["snapshot_path"] = payload["market_state_path"]
    return payload
