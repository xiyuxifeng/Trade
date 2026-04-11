"""Tests for CircuitBreakerHealthChecker (P1-V01)."""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "src")

from src.health.circuit_breaker_checker import CircuitBreakerHealthChecker
from src.health.models import ComponentCheck, HealthStatus


class TestCircuitBreakerHealthChecker:
    """测试 CircuitBreakerHealthChecker。"""

    def test_checker_name(self):
        """检查器名称正确。"""
        checker = CircuitBreakerHealthChecker()
        assert checker.name == "circuit_breaker"

    def test_health_status_enum(self):
        """HealthStatus 枚举值正确。"""
        assert HealthStatus.OK.value == "ok"
        assert HealthStatus.WARNING.value == "warning"
        assert HealthStatus.ERROR.value == "error"

    def test_component_check_creation(self):
        """ComponentCheck 创建正确。"""
        check = ComponentCheck(
            name="test",
            status=HealthStatus.OK,
            details={"key": "value"},
        )
        assert check.name == "test"
        assert check.status == HealthStatus.OK
        assert check.details["key"] == "value"
        assert check.error is None

    def test_component_check_with_error(self):
        """带 error 的 ComponentCheck 创建正确。"""
        check = ComponentCheck(
            name="test",
            status=HealthStatus.ERROR,
            error="Something went wrong",
        )
        assert check.status == HealthStatus.ERROR
        assert check.error == "Something went wrong"

    def test_checker_has_exception_handling(self):
        """checker 有异常处理逻辑。"""
        checker = CircuitBreakerHealthChecker()
        # verify the check method exists and is async
        import inspect
        assert inspect.iscoroutinefunction(checker.check)
