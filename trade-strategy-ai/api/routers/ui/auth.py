from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import _find_api_key_record, _is_api_key_enabled
from config.database import get_async_session
from src.auth import hash_password, verify_password
from src.models.user import User, UserSession

router = APIRouter(prefix="/api/ui/v1/auth", tags=["ui-auth"])

TOKEN_EXPIRY_DAYS = 3650


def _generate_token() -> str:
    """生成安全的会话令牌。"""
    import secrets
    return secrets.token_hex(32)


async def _get_session_token(request: Request) -> str | None:
    """从请求头中获取会话令牌。

    优先使用 X-Auth-Token 头，其次读取 Cookie 中的 token。
    """
    token = request.headers.get("X-Auth-Token")
    if token:
        return token
    cookie = request.cookies.get("auth_token")
    return cookie


async def _get_user_from_token(
    token: str, session: AsyncSession
) -> User | None:
    """根据令牌查找有效会话并返回对应用户。"""
    result = await session.execute(
        select(UserSession).where(
            UserSession.token == token,
        )
    )
    user_session = result.scalar_one_or_none()
    if user_session is None:
        return None

    # 更新最后使用时间，并将过期时间固定设置为很久以后
    user_session.last_used_at = datetime.now(UTC)
    user_session.expires_at = datetime.now(UTC) + timedelta(days=TOKEN_EXPIRY_DAYS)
    await session.flush()
    await session.commit()

    result = await session.execute(
        select(User).where(User.id == user_session.user_id, User.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_current_user_with_session(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """获取当前登录用户信息（基于会话令牌），作为 API 依赖使用。"""
    token = await _get_session_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    user = await _get_user_from_token(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="会话已过期或无效")
    return {
        "id": str(user.id),
        "username": user.username,
        "role": user.role,
        "display_name": user.display_name,
        "authenticated": True,
        "source": "session",
    }


async def require_admin(
    current_user: dict[str, Any] = Depends(get_current_user_with_session),
) -> dict[str, Any]:
    """要求当前用户具有 admin 角色。"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


@router.post("/login")
async def login(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """用户登录，验证用户名密码并创建会话。"""
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")

    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    result = await db.execute(
        select(User).where(User.username == username, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 创建会话
    token = _generate_token()
    # 过期时间设置为很久以后，避免长期使用被动过期
    expires_at = datetime.now(UTC) + timedelta(days=TOKEN_EXPIRY_DAYS)
    user_session = UserSession(
        user_id=user.id, token=token, expires_at=expires_at
    )
    db.add(user_session)

    # 记录最后登录时间
    user.last_login_at = datetime.now(UTC)
    await db.flush()
    await db.commit()

    return {
        "token": token,
        "expires_at": expires_at.isoformat(),
        "user": {
            "id": str(user.id),
            "username": user.username,
            "role": user.role,
            "display_name": user.display_name,
        },
    }


@router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """登出：销毁当前会话令牌。"""
    token = await _get_session_token(request)
    if token:
        result = await db.execute(
            select(UserSession).where(UserSession.token == token)
        )
        user_session = result.scalar_one_or_none()
        if user_session:
            await db.delete(user_session)
            await db.flush()
            await db.commit()
    return {"message": "已登出"}


@router.get("/me")
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """返回当前请求的身份信息。

    优先检查会话令牌（session auth），回退到 API Key 认证。
    """
    # 尝试 session auth
    token = await _get_session_token(request)
    if token:
        user = await _get_user_from_token(token, db)
        if user:
            return {
                "role": user.role,
                "api_key_label": user.display_name or user.username,
                "authenticated": True,
                "source": "session",
                "username": user.username,
                "display_name": user.display_name,
            }

    # 回退到 API Key 认证
    if _is_api_key_enabled():
        api_key = request.headers.get("X-API-Key")
        record = _find_api_key_record(api_key)
        if record:
            return {
                "role": record["role"],
                "api_key_label": record["label"],
                "authenticated": True,
                "source": "api_key",
                "username": "",
            }

    # 未认证
    return {
        "role": "anonymous",
        "api_key_label": None,
        "authenticated": False,
        "source": "anonymous",
        "username": "",
    }


# ---- 用户管理接口 (admin only) ----

@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_async_session),
    admin: dict[str, Any] = Depends(require_admin),
) -> list[dict[str, Any]]:
    """获取所有用户列表（仅管理员）。"""
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "role": u.role,
            "is_active": u.is_active,
            "display_name": u.display_name,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/users", status_code=201)
async def create_user(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """创建新用户（仅管理员）。"""
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    role = body.get("role", "viewer")
    display_name = body.get("display_name", "").strip() or None

    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码长度不能少于6位")
    if role not in ("viewer", "operator", "admin"):
        raise HTTPException(status_code=400, detail="无效的角色")

    # 检查用户名是否已存在
    result = await db.execute(
        select(User).where(User.username == username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="用户名已存在")

    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        display_name=display_name,
    )
    db.add(user)
    await db.flush()

    return {
        "id": str(user.id),
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "display_name": user.display_name,
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """更新用户信息（仅管理员）。"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    body = await request.json()

    if "role" in body:
        new_role = body["role"]
        if new_role not in ("viewer", "operator", "admin"):
            raise HTTPException(status_code=400, detail="无效的角色")
        user.role = new_role

    if "is_active" in body:
        user.is_active = bool(body["is_active"])

    if "display_name" in body:
        user.display_name = body["display_name"].strip() or None

    if "password" in body and body["password"]:
        if len(body["password"]) < 6:
            raise HTTPException(status_code=400, detail="密码长度不能少于6位")
        user.password_hash = hash_password(body["password"])

    await db.flush()

    return {
        "id": str(user.id),
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "display_name": user.display_name,
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, str]:
    """删除用户（仅管理员）。"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 删除用户的会话
    await db.execute(
        UserSession.__table__.delete().where(UserSession.user_id == user.id)
    )
    await db.delete(user)
    await db.flush()

    return {"message": f"用户 {user.username} 已删除"}
