from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query

from api.dependencies import verify_api_key
from src.common.paths import resolve_project_path
from src.services.signal_service import SignalService

router = APIRouter(prefix="/api/ui/v1", tags=["ui-signals"])


def _config_path() -> Path:
    """读取当前 UI BFF 使用的配置文件路径。"""
    return resolve_project_path(os.environ.get("CONFIG_PATH", "config/app.yaml"))


def get_signal_service() -> SignalService:
    """构建信号查询服务。"""
    return SignalService()


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
    service: SignalService = Depends(get_signal_service),
):
    """列出已生成的信号版本，补充可读的上下文摘要。"""
    result = service.list_signals(config_path=_config_path(), symbol=symbol, since=since, limit=limit)
    payload = dict(result.payload)
    payload["signals"] = [
        {**item, "context_summary": _summarize_context(item.get("context"))}
        for item in payload.get("signals", [])
    ]
    return payload
