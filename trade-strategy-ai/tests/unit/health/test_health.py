"""健康检查模型测试。"""
import pytest

from src.health.models import (
    ComponentCheck,
    DetailedHealthResponse,
    HealthStatus,
    LiveHealthResponse,
    OverallStatus,
    ReadyHealthResponse,
)


def test_live_health_response():
    resp = LiveHealthResponse()
    assert resp.status == "alive"
    assert resp.timestamp is not None


def test_ready_health_response_ok():
    resp = ReadyHealthResponse(status="ready", checks={"database": "ok"})
    assert resp.status == "ready"
    assert resp.checks["database"] == "ok"


def test_ready_health_response_not_ready():
    resp = ReadyHealthResponse(status="not_ready", checks={"database": "failed"})
    assert resp.status == "not_ready"


def test_component_check_ok():
    check = ComponentCheck(name="database", status=HealthStatus.OK, latency_ms=12.5)
    assert check.name == "database"
    assert check.status == HealthStatus.OK
    assert check.latency_ms == 12.5


def test_component_check_error():
    check = ComponentCheck(name="pipeline", status=HealthStatus.ERROR, error="timeout")
    assert check.status == HealthStatus.ERROR
    assert check.error == "timeout"


def test_detailed_health_response_healthy():
    components = {
        "database": ComponentCheck(name="database", status=HealthStatus.OK, latency_ms=5.0),
        "pipeline": ComponentCheck(name="pipeline", status=HealthStatus.OK),
    }
    resp = DetailedHealthResponse(status=OverallStatus.HEALTHY, components=components)
    assert resp.status == OverallStatus.HEALTHY
    assert len(resp.components) == 2


def test_detailed_health_response_degraded():
    components = {
        "database": ComponentCheck(name="database", status=HealthStatus.OK),
        "pipeline": ComponentCheck(name="pipeline", status=HealthStatus.WARNING, error="no runs"),
    }
    issues = ["[WARN] pipeline: no runs"]
    resp = DetailedHealthResponse(status=OverallStatus.DEGRADED, components=components, issues=issues)
    assert resp.status == OverallStatus.DEGRADED
    assert len(resp.issues) == 1
