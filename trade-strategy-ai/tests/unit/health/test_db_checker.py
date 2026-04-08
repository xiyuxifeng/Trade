"""DatabaseHealthChecker 单元测试。"""
import pytest

from src.health.db_checker import DatabaseHealthChecker
from src.health.models import HealthStatus


@pytest.mark.asyncio
async def test_db_checker_returns_component_check():
    checker = DatabaseHealthChecker()
    result = await checker.check()
    assert result.name == "database"
    assert result.status in [HealthStatus.OK, HealthStatus.ERROR]
    assert result.latency_ms is not None
    assert isinstance(result.latency_ms, float)
