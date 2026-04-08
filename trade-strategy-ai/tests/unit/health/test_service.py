"""HealthCheckService 单元测试。"""
import pytest
from unittest.mock import AsyncMock, PropertyMock

from src.health.models import ComponentCheck, HealthStatus, OverallStatus
from src.health.service import HealthCheckService


@pytest.mark.asyncio
async def test_check_live_returns_alive():
    service = HealthCheckService()
    result = await service.check_live()
    assert result.status == "alive"


@pytest.mark.asyncio
async def test_check_ready_db_ok():
    mock_checker = AsyncMock()
    type(mock_checker).name = PropertyMock(return_value="database")
    mock_checker.check.return_value = ComponentCheck(name="database", status=HealthStatus.OK, latency_ms=5.0)
    service = HealthCheckService(db_checker=mock_checker)
    result = await service.check_ready()
    assert result.status == "ready"
    assert result.checks["database"] == "ok"


@pytest.mark.asyncio
async def test_check_ready_db_failed():
    mock_checker = AsyncMock()
    type(mock_checker).name = PropertyMock(return_value="database")
    mock_checker.check.return_value = ComponentCheck(name="database", status=HealthStatus.ERROR, error="connection refused")
    service = HealthCheckService(db_checker=mock_checker)
    result = await service.check_ready()
    assert result.status == "not_ready"
    assert result.checks["database"] == "failed"


@pytest.mark.asyncio
async def test_check_detailed_all_healthy():
    def make_mock_ok(name: str):
        mock = AsyncMock()
        type(mock).name = PropertyMock(return_value=name)
        mock.check.return_value = ComponentCheck(name=name, status=HealthStatus.OK)
        return mock

    service = HealthCheckService(
        db_checker=make_mock_ok("database"),
        pipeline_checker=make_mock_ok("pipeline"),
        agent_net_checker=make_mock_ok("agent_net"),
        alerting_checker=make_mock_ok("alerting"),
        circuit_breaker_checker=make_mock_ok("circuit_breaker"),
    )
    result = await service.check_detailed(timeout=5.0)
    assert result.status == OverallStatus.HEALTHY
    assert len(result.components) == 5
    assert len(result.issues) == 0


@pytest.mark.asyncio
async def test_check_detailed_with_errors():
    mock_ok = AsyncMock()
    type(mock_ok).name = PropertyMock(return_value="database")
    mock_ok.check.return_value = ComponentCheck(name="database", status=HealthStatus.OK)

    mock_err = AsyncMock()
    type(mock_err).name = PropertyMock(return_value="pipeline")
    mock_err.check.return_value = ComponentCheck(name="pipeline", status=HealthStatus.ERROR, error="snapshot missing")

    service = HealthCheckService(
        db_checker=mock_ok,
        pipeline_checker=mock_err,
        agent_net_checker=mock_ok,
        alerting_checker=mock_ok,
        circuit_breaker_checker=mock_ok,
    )
    result = await service.check_detailed(timeout=5.0)
    assert result.status == OverallStatus.UNHEALTHY
    assert "pipeline" in result.components
    assert any("pipeline" in issue for issue in result.issues)
