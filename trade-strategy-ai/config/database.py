from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from config.settings import get_settings


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


__all__ = ["get_engine", "get_session_factory", "get_async_session"]
