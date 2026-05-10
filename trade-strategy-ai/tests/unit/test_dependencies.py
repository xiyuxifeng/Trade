from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.dependencies import CurrentPrincipal, get_current_key, get_current_principal, require_role, verify_api_key


@pytest.mark.asyncio
async def test_verify_api_key_allows_when_auth_disabled(monkeypatch) -> None:
    """关闭鉴权时应允许匿名访问。"""
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": False, "api_keys": []}},
    )

    assert await verify_api_key(None) == "anonymous"


@pytest.mark.asyncio
async def test_verify_api_key_accepts_matching_key(monkeypatch) -> None:
    """鉴权开启且 key 命中时应通过。"""
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": True, "api_keys": ["demo-key"]}},
    )

    assert await verify_api_key("demo-key") == "demo-key"


@pytest.mark.asyncio
async def test_verify_api_key_rejects_missing_or_unknown_key(monkeypatch) -> None:
    """鉴权开启但未提供有效 key 时应拒绝。"""
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": True, "api_keys": ["demo-key"]}},
    )

    with pytest.raises(HTTPException) as exc:
        await verify_api_key(None)
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        await verify_api_key("other-key")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_verify_api_key_rejects_empty_key_list(monkeypatch) -> None:
    """鉴权开启但 key 列表为空时仍应拒绝。"""
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": True, "api_keys": []}},
    )

    with pytest.raises(HTTPException) as exc:
        await verify_api_key("demo-key")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_key_requires_valid_key_when_enabled(monkeypatch) -> None:
    """get_current_key 在启用鉴权时也不应掩盖无效配置。"""
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": True, "api_keys": ["demo-key"]}},
    )

    with pytest.raises(HTTPException) as exc:
        await get_current_key("wrong-key")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_principal_supports_structured_keys(monkeypatch) -> None:
    """结构化 API Key 配置应解析出角色与标签。"""
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {
            "auth": {
                "enabled": True,
                "api_keys": [
                    {"key": "viewer-key", "role": "viewer", "label": "Viewer"},
                    {"key": "admin-key", "role": "admin", "label": "Admin"},
                ],
            }
        },
    )

    principal = await get_current_principal("admin-key")
    assert isinstance(principal, CurrentPrincipal)
    assert principal.role == "admin"
    assert principal.api_key_label == "Admin"
    assert principal.api_key == "admin-key"
    assert principal.authenticated is True


@pytest.mark.asyncio
async def test_get_current_principal_defaults_invalid_role_to_viewer(monkeypatch) -> None:
    """非法角色值不应被提升为 admin。"""
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {
            "auth": {
                "enabled": True,
                "api_keys": [
                    {"key": "broken-key", "role": "superuser", "label": "Broken"},
                ],
            }
        },
    )

    principal = await get_current_principal("broken-key")
    assert principal.role == "viewer"
    assert principal.api_key_label == "Broken"


@pytest.mark.asyncio
async def test_require_role_rejects_insufficient_permissions(monkeypatch) -> None:
    """权限不足时应返回统一 403。"""
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {
            "auth": {
                "enabled": True,
                "api_keys": [
                    {"key": "viewer-key", "role": "viewer", "label": "Viewer"},
                ],
            }
        },
    )

    dependency = require_role("operator")

    with pytest.raises(HTTPException) as exc:
        await dependency(await get_current_principal("viewer-key"))

    assert exc.value.status_code == 403
    assert exc.value.detail == "insufficient permissions"
