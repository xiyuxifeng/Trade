from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Coroutine
from functools import lru_cache
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from config.settings import get_settings

T = TypeVar("T")


def _build_engine_kwargs(database_url: str) -> dict[str, object]:
    settings = get_settings()
    engine_kwargs: dict[str, object] = {
        "echo": settings.database_echo,
        "pool_pre_ping": True,
    }

    # SQLite 不支持这些连接池参数
    if not database_url.startswith("sqlite"):
        engine_kwargs.update(
            {
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
                "pool_timeout": settings.database_pool_timeout,
                "pool_recycle": settings.database_pool_recycle,
            }
        )
    return engine_kwargs


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    settings = get_settings()
    url = settings.database_url
    return create_async_engine(url, **_build_engine_kwargs(url))


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session


async def dispose_cached_engine() -> None:
    """Dispose the cached async engine and clear dependent caches."""
    if get_engine.cache_info().currsize == 0:
        return

    engine = get_engine()
    await engine.dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()


__all__ = ["get_engine", "get_session_factory", "get_async_session", "run_async_with_cleanup", "dispose_cached_engine"]


def run_async_with_cleanup(coro: Coroutine[object, object, T]) -> T:
    """在同步上下文中执行异步任务，并在完成后优雅关闭数据库连接池。

    解决 CLI 命令中 asyncio.run() 未 dispose engine 导致的 ResourceWarning
    和 "Future attached to a different loop" 问题。
    """
    async def _wrapper():
        try:
            return await coro
        finally:
            await get_engine().dispose()

    return asyncio.run(_wrapper())
