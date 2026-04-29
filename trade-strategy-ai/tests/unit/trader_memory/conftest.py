"""TraderMemoryStore 测试夹具"""
from __future__ import annotations

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