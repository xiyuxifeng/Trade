from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from src.common.config import AppConfig, load_app_config

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


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


async def verify_api_key(
    key: str | None = Security(_api_key_header),
) -> str:
    """Verify API key from X-API-Key header."""
    api_config = _get_api_config()

    if not api_config.get("auth", {}).get("enabled", False):
        return "anonymous"

    valid_keys = api_config.get("auth", {}).get("api_keys", [])
    if key in valid_keys:
        return key

    if not valid_keys:
        return "anonymous"

    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN,
        detail="Invalid or missing API key",
    )


async def get_current_key(key: str = Security(_api_key_header)) -> str:
    """Get current API key, returns 'anonymous' if not set."""
    api_config = _get_api_config()

    if not api_config.get("auth", {}).get("enabled", False):
        return "anonymous"

    valid_keys = api_config.get("auth", {}).get("api_keys", [])
    if key in valid_keys:
        return key
    return "anonymous"
