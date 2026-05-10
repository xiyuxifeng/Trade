from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.dependencies import CurrentPrincipal, get_current_principal


router = APIRouter(prefix="/api/ui/v1/auth", tags=["ui-auth"])


@router.get("/me")
async def get_current_user(principal: CurrentPrincipal = Depends(get_current_principal)) -> dict[str, Any]:
    """返回当前请求的公开身份信息。"""
    return principal.to_public_dict()
