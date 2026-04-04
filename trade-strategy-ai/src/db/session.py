from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_async_session, get_engine, get_session_factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    AsyncSessionFactory = get_session_factory()
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


__all__ = ["get_engine", "get_async_session", "session_scope"]
