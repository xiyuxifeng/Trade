"""TraderMemoryStore 测试夹具"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import MagicMock, AsyncMock

import pytest

from src.trader_memory.service import TraderMemoryStore


@pytest.fixture(autouse=True)
async def _truncate_table():
    """每个测试前清空表。

    使用 yield fixture 模式：yield 之前的代码在测试前执行，
    yield 之后的代码（如果有）在测试后执行。
    确保每个测试开始时数据库是干净的。
    """
    from config.database import get_engine
    from sqlalchemy import text

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE trader_memory RESTART IDENTITY CASCADE"))

    yield  # 测试在这里执行


@pytest.fixture
async def store() -> TraderMemoryStore:
    """TraderMemoryStore 实例，共享同一 session_factory。"""
    return TraderMemoryStore()


# S10-009: 新增 mock session_scope fixtures
# 用于在不需要真实数据库连接的测试中替代 _truncate_table


@pytest.fixture
@asynccontextmanager
async def mock_session_scope():
    """
    Mock session_scope 避免依赖真实 PostgreSQL 连接。

    用法：
    async with mock_session_scope() as session:
        # 使用 mock session
        session.execute = AsyncMock()
        session.commit = AsyncMock()

    设计：
    - 返回一个 async context manager
    - yield 一个 MagicMock 对象
    - 不实际连接数据库
    """
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    yield session


@pytest.fixture
def mock_session_scope_blocking():
    """
    同步版本的 mock session_scope。

    用于不支持 async 的测试。
    """
    session = MagicMock()
    session.execute = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session
