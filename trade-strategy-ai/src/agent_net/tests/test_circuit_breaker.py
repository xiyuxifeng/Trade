"""单元测试 - 熔断器。"""

from __future__ import annotations

import asyncio
import pytest

from src.agent_net.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitOpenError,
    CircuitBreakerRegistry,
    get_global_breaker_registry,
)


class TestCircuitBreaker:
    """测试 CircuitBreaker。"""

    @pytest.fixture
    def breaker(self) -> CircuitBreaker:
        """创建测试熔断器。"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,
            half_open_attempts=2,
            success_threshold=2,
        )
        return CircuitBreaker("test_circuit", config)

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, breaker: CircuitBreaker) -> None:
        """测试初始状态为 CLOSED。"""
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_success_keeps_circuit_closed(self, breaker: CircuitBreaker) -> None:
        """测试成功后保持 CLOSED 状态。"""
        async def succeed() -> str:
            return "success"
        await breaker.call(succeed())
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_failure_increments_count(self, breaker: CircuitBreaker) -> None:
        """测试失败增加计数。"""
        async def fail_once() -> str:
            raise ValueError("fail")

        try:
            await breaker.call(fail_once())
        except ValueError:
            pass

        assert breaker.failure_count == 1
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self, breaker: CircuitBreaker) -> None:
        """测试失败达到阈值后熔断器打开。"""
        async def always_fail() -> str:
            raise ValueError("fail")

        for _ in range(3):
            try:
                await breaker.call(always_fail())
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_open_error(self, breaker: CircuitBreaker) -> None:
        """测试熔断打开时抛出 CircuitOpenError。"""
        async def always_fail() -> str:
            raise ValueError("fail")

        # 先打开熔断器
        for _ in range(3):
            try:
                await breaker.call(always_fail())
            except ValueError:
                pass

        with pytest.raises(CircuitOpenError) as exc_info:
            async def should_fail() -> str:
                return "should fail"
            await breaker.call(should_fail())

        assert exc_info.value.circuit_name == "test_circuit"

    @pytest.mark.asyncio
    async def test_circuit_half_open_after_timeout(self, breaker: CircuitBreaker) -> None:
        """测试超过恢复时间后进入 HALF_OPEN。"""
        async def always_fail() -> str:
            raise ValueError("fail")

        # 打开熔断器
        for _ in range(3):
            try:
                await breaker.call(always_fail())
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

        # 等待恢复超时
        await asyncio.sleep(1.1)

        # 下一次调用会进入 HALF_OPEN
        async def attempt() -> str:
            return "attempt"
        try:
            await breaker.call(attempt())
        except Exception:
            pass

        # 如果成功，应该进入 HALF_OPEN 或 CLOSED
        assert breaker.state in (CircuitState.HALF_OPEN, CircuitState.CLOSED)

    @pytest.mark.asyncio
    async def test_recovery_after_success_threshold(self) -> None:
        """测试 HALF_OPEN 状态下成功后恢复。"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.5,
            half_open_attempts=3,
            success_threshold=2,
        )
        breaker = CircuitBreaker("test_recovery", config)

        async def always_fail() -> str:
            raise ValueError("fail")

        # 打开熔断器
        for _ in range(2):
            try:
                await breaker.call(always_fail())
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

        # 等待恢复
        await asyncio.sleep(0.6)

        # 在 HALF_OPEN 状态下成功
        async def succeed() -> str:
            return "success"
        for _ in range(2):
            await breaker.call(succeed())

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_manual_reset(self, breaker: CircuitBreaker) -> None:
        """测试手动重置熔断器。"""
        async def always_fail() -> str:
            raise ValueError("fail")

        # 打开熔断器
        for _ in range(3):
            try:
                await breaker.call(always_fail())
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

        # 手动重置
        await breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_get_stats(self, breaker: CircuitBreaker) -> None:
        """测试获取统计信息。"""
        stats = breaker.get_stats()

        assert stats["name"] == "test_circuit"
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0
        assert "remaining_timeout" in stats

    @pytest.mark.asyncio
    async def test_exception_propagates_after_circuit_open(self, breaker: CircuitBreaker) -> None:
        """测试熔断打开后异常正常传播。"""
        async def always_fail() -> str:
            raise ValueError("fail")

        # 打开熔断器
        for _ in range(3):
            try:
                await breaker.call(always_fail())
            except ValueError:
                pass

        with pytest.raises(CircuitOpenError):
            async def test() -> str:
                return "test"
            await breaker.call(test())


class TestCircuitBreakerConfig:
    """测试 CircuitBreakerConfig。"""

    def test_default_values(self) -> None:
        """测试默认值。"""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.recovery_timeout == 30.0
        assert config.half_open_attempts == 3
        assert config.success_threshold == 2

    def test_custom_values(self) -> None:
        """测试自定义值。"""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=60.0,
            half_open_attempts=5,
            success_threshold=3,
        )

        assert config.failure_threshold == 10
        assert config.recovery_timeout == 60.0


class TestCircuitState:
    """测试 CircuitState 枚举。"""

    def test_state_values(self) -> None:
        """测试状态值。"""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitOpenError:
    """测试 CircuitOpenError。"""

    def test_error_message(self) -> None:
        """测试错误消息。"""
        error = CircuitOpenError("my_circuit", 10.5)

        assert error.circuit_name == "my_circuit"
        assert error.remaining_timeout == 10.5
        assert "my_circuit" in str(error)
        assert "10.5" in str(error)

    def test_error_without_timeout(self) -> None:
        """测试没有超时信息的错误。"""
        error = CircuitOpenError("my_circuit")

        assert error.remaining_timeout is None


class TestCircuitBreakerRegistry:
    """测试 CircuitBreakerRegistry。"""

    @pytest.mark.asyncio
    async def test_get_or_create(self) -> None:
        """测试获取或创建熔断器。"""
        registry = CircuitBreakerRegistry()

        breaker1 = await registry.get_or_create("test_1")
        breaker2 = await registry.get_or_create("test_1")

        assert breaker1 is breaker2  # 同一实例

        breaker3 = await registry.get_or_create("test_2")
        assert breaker3 is not breaker1

    @pytest.mark.asyncio
    async def test_get_existing(self) -> None:
        """测试获取已存在的熔断器。"""
        registry = CircuitBreakerRegistry()

        await registry.get_or_create("test")
        breaker = await registry.get("test")

        assert breaker is not None
        assert breaker.name == "test"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self) -> None:
        """测试获取不存在的熔断器。"""
        registry = CircuitBreakerRegistry()

        breaker = await registry.get("nonexistent")
        assert breaker is None

    @pytest.mark.asyncio
    async def test_reset_all(self) -> None:
        """测试重置所有熔断器。"""
        registry = CircuitBreakerRegistry()

        breaker = await registry.get_or_create("test")

        async def always_fail() -> str:
            raise ValueError("fail")

        # 打开熔断器
        for _ in range(5):
            try:
                await breaker.call(always_fail())
            except ValueError:
                pass

        # 重置所有
        await registry.reset_all()

        assert breaker.state == CircuitState.CLOSED

    def test_list_breakers(self) -> None:
        """测试列出所有熔断器。"""
        registry = CircuitBreakerRegistry()

        assert registry.list_breakers() == []

    @pytest.mark.asyncio
    async def test_global_registry(self) -> None:
        """测试全局注册表。"""
        registry = get_global_breaker_registry()
        breaker = await registry.get_or_create("global_test")

        assert breaker.name == "global_test"
