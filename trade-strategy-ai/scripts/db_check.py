import os
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/trade_strategy_ai")

async def check() -> None:
    engine = create_async_engine(DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ PostgreSQL 连接成功！", result.scalar_one())
    except Exception as e:  # noqa: BLE001
        print("❌ PostgreSQL 连接失败：", e)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
