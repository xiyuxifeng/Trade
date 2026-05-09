from __future__ import annotations

import os
from functools import lru_cache

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from src.common.config import AppConfig, load_app_config

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_AUTH_ERROR_DETAIL = "Invalid or missing API key"


@lru_cache
def _get_app_config() -> AppConfig:
    """Load and cache app config."""
    config_path = os.environ.get("CONFIG_PATH", "config/app.yaml")
    loaded = load_app_config(config_path)
    return loaded.config


def _get_api_config() -> dict:
    """Get API config dict from app config."""
    cfg = _get_app_config()
    return {
        "auth": {
            "enabled": cfg.api.auth.enabled,
            "api_keys": cfg.api.auth.api_keys,
        }
    }


def _is_api_key_enabled() -> bool:
    """判断 UI API 鉴权是否启用。"""
    return bool(_get_api_config().get("auth", {}).get("enabled", False))


def _get_valid_api_keys() -> list[str]:
    """返回当前允许的 API Key 列表。"""
    keys = _get_api_config().get("auth", {}).get("api_keys", [])
    return [key for key in keys if key]


def _require_valid_api_key(key: str | None) -> str:
    """校验 API Key，并在失败时抛出统一错误。"""
    if key and key in _get_valid_api_keys():
        return key

    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN,
        detail=_AUTH_ERROR_DETAIL,
    )


async def verify_api_key(
    key: str | None = Security(_api_key_header),
) -> str:
    """Verify API key from X-API-Key header."""
    if not _is_api_key_enabled():
        return "anonymous"

    return _require_valid_api_key(key)


async def get_current_key(key: str = Security(_api_key_header)) -> str:
    """获取当前 API Key；鉴权开启时必须返回有效 key。"""
    if not _is_api_key_enabled():
        return "anonymous"

    return _require_valid_api_key(key)
