from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from api.dependencies import verify_api_key
from src.common.paths import resolve_project_path
from src.db.session import get_session_factory
from src.services.config_profile_service import ConfigProfileService
from src.services.signal_service import SignalService

router = APIRouter(prefix="/api/ui/v1", tags=["ui-signals"])


async def _resolve_profile_id(preferred: str | None = None) -> str | None:
    """读取当前 UI BFF 使用的 Profile。"""
    service = ConfigProfileService()
    return service.resolve_runtime_profile_id(preferred)


def get_signal_service() -> SignalService:
    """构建信号查询服务。"""
    return SignalService(session_factory=get_session_factory())


def _summarize_context(context: Any) -> str:
    """把信号上下文压成适合卡片展示的短摘要。"""
    if context is None:
        return "n/a"
    if isinstance(context, dict):
        parts: list[str] = []
        for key in ("trend", "signal", "bias", "score", "summary"):
            if key in context and context[key] not in (None, ""):
                parts.append(f"{key}={context[key]}")
        if parts:
            return ", ".join(parts)
        if context:
            first_key = next(iter(context))
            return f"{first_key}={context[first_key]}"
        return "n/a"
    if isinstance(context, list):
        if not context:
            return "n/a"
        return ", ".join(str(item) for item in context[:3])
    return str(context)


@router.get("/signals", dependencies=[Depends(verify_api_key)])
async def list_signals(
    symbol: str | None = None,
    since: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    profile_id: str | None = None,
    service: SignalService = Depends(get_signal_service),
):
    """列出已生成的信号版本，补充可读的上下文摘要。"""
    runtime_profile_id = await _resolve_profile_id(profile_id)
    if runtime_profile_id is not None:
        result = service.list_signals(
            profile_id=runtime_profile_id,
            symbol=symbol,
            since=since,
            limit=limit,
        )
    else:
        result = service.list_signals(
            config_path=resolve_project_path("config/app.yaml"),
            symbol=symbol,
            since=since,
            limit=limit,
        )
    payload = dict(result.payload)
    payload.pop("config_path", None)
    payload["signals"] = [
        {**item, "context_summary": _summarize_context(item.get("context"))}
        for item in payload.get("signals", [])
    ]
    return payload
