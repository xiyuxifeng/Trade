from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from functools import lru_cache
from typing import Any

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from src.common.config import AppConfig, ApiKeyAccessConfig, load_app_config

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_AUTH_ERROR_DETAIL = "Invalid or missing API key"
_PERMISSION_ERROR_DETAIL = "insufficient permissions"
_ROLE_ORDER = {"anonymous": 0, "viewer": 1, "operator": 2, "admin": 3}


@dataclass(frozen=True)
class CurrentPrincipal:
    """当前请求的身份信息。"""

    role: str
    api_key_label: str | None
    authenticated: bool
    source: str
    api_key: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        """返回不包含原始 API Key 的公开身份信息。"""
        return {
            "role": self.role,
            "api_key_label": self.api_key_label,
            "authenticated": self.authenticated,
            "source": self.source,
        }


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


def _normalize_role(role: Any) -> str:
    """把配置里的角色值归一化到已知集合。"""
    if isinstance(role, str) and role in _ROLE_ORDER:
        return role
    return "viewer"


def _normalize_api_keys() -> list[dict[str, str]]:
    """把配置里的 API Key 统一展开成结构化记录。"""
    raw_keys = _get_api_config().get("auth", {}).get("api_keys", [])
    normalized: list[dict[str, str]] = []

    for item in raw_keys:
        if isinstance(item, str) and item:
            normalized.append({"key": item, "role": "admin", "label": item})
            continue

        if isinstance(item, ApiKeyAccessConfig):
            normalized.append(
                {
                    "key": item.key,
                    "role": _normalize_role(item.role),
                    "label": item.label or item.key,
                }
            )
            continue

        if isinstance(item, dict):
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            normalized.append(
                {
                    "key": key,
                    "role": _normalize_role(item.get("role")),
                    "label": str(item.get("label") or key),
                }
            )

    return normalized


def _find_api_key_record(key: str | None) -> dict[str, str] | None:
    """按明文 API Key 查找结构化记录。"""
    if not key:
        return None

    for item in _normalize_api_keys():
        if item["key"] == key:
            return item
    return None


def describe_api_key(key: str | None) -> dict[str, Any] | None:
    """把明文 API Key 映射成公开可展示的身份标签。"""
    record = _find_api_key_record(key)
    if record is None:
        return None
    return {
        "role": record["role"],
        "api_key_label": record["label"],
        "authenticated": True,
        "source": "api_key",
    }


def _require_valid_api_key(key: str | None) -> dict[str, str]:
    """校验 API Key，并在失败时抛出统一错误。"""
    record = _find_api_key_record(key)
    if record is not None:
        return record

    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN,
        detail=_AUTH_ERROR_DETAIL,
    )


def _role_rank(role: str) -> int:
    """返回角色等级。"""
    return _ROLE_ORDER.get(role, 0)


async def get_current_principal(
    key: str | None = Security(_api_key_header),
) -> CurrentPrincipal:
    """解析当前请求身份。"""
    if not _is_api_key_enabled():
        return CurrentPrincipal(role="anonymous", api_key_label=None, authenticated=False, source="anonymous")

    record = _require_valid_api_key(key)
    return CurrentPrincipal(
        role=record["role"],
        api_key_label=record["label"],
        authenticated=True,
        source="api_key",
        api_key=record["key"],
    )


def require_role(min_role: str):
    """创建一个最小角色校验依赖。"""

    async def _dependency(principal: CurrentPrincipal = Depends(get_current_principal)) -> CurrentPrincipal:
        if _role_rank(principal.role) < _role_rank(min_role):
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=_PERMISSION_ERROR_DETAIL)
        return principal

    return _dependency


async def verify_api_key(
    key: str | None = Security(_api_key_header),
) -> str:
    """Verify API key from X-API-Key header."""
    if not _is_api_key_enabled():
        return "anonymous"

    record = _require_valid_api_key(key)
    return record["key"]


async def get_current_key(key: str | None = Security(_api_key_header)) -> str:
    """获取当前 API Key；鉴权开启时必须返回有效 key。"""
    if not _is_api_key_enabled():
        return "anonymous"

    record = _require_valid_api_key(key)
    return record["key"]


def clear_cached_app_config() -> None:
    """清理已缓存的应用配置，供配置保存/恢复后刷新鉴权状态。"""
    _get_app_config.cache_clear()
