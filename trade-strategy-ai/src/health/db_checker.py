"""数据库健康检查器。"""
from __future__ import annotations

import time

from src.common.logger import get_logger
from src.health.models import ComponentCheck, HealthStatus

logger = get_logger("health.db")


class DatabaseHealthChecker:
    """检查 PostgreSQL 连接池可用性。"""

    name: str = "database"

    async def check(self) -> ComponentCheck:
        """执行 DB 健康检查。

        尝试执行 SELECT 1，测量延迟，获取连接池状态。
        """
        start = time.perf_counter()
        try:
            from src.db.session import session_scope

            from sqlalchemy import text
            async with session_scope() as session:
                await session.execute(text("SELECT 1"))
            latency_ms = (time.perf_counter() - start) * 1000

            # 获取连接池信息（从 engine 获取）
            from src.db.session import get_engine
            engine = get_engine()
            pool = engine.pool
            pool_size = getattr(pool, "size", lambda: 0)()
            pool_checked_in = getattr(pool, "checked_in", lambda: 0)()
            pool_overflow = getattr(pool, "overflow", lambda: 0)()

            return ComponentCheck(
                name=self.name,
                status=HealthStatus.OK,
                latency_ms=round(latency_ms, 2),
                details={
                    "pool_size": pool_size,
                    "pool_checked_in": pool_checked_in,
                    "pool_overflow": pool_overflow,
                },
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error("database health check failed: %s", e)
            return ComponentCheck(
                name=self.name,
                status=HealthStatus.ERROR,
                latency_ms=round(latency_ms, 2),
                error=str(e),
            )
