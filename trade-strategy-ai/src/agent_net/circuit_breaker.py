"""熔断器模式实现。

提供熔断器机制防止级联故障：
- CircuitBreaker: 熔断器实现
- CircuitState: 熔断状态
- CircuitOpenError: 熔断开启异常
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, TypeVar, Awaitable
import logging

from src.common.logger import get_logger


logger = get_logger("agent_net.circuit_breaker")


T = TypeVar("T")


class CircuitState(Enum):
    """熔断器状态。"""

    CLOSED = "closed"  # 正常，允许请求通过
    OPEN = "open"  # 熔断中，拒绝请求
    HALF_OPEN = "half_open"  # 尝试恢复


class CircuitOpenError(Exception):
    """熔断器开启异常。"""

    def __init__(self, circuit_name: str, remaining_timeout: float | None = None) -> None:
        self.circuit_name = circuit_name
        self.remaining_timeout = remaining_timeout
        msg = f"Circuit '{circuit_name}' is OPEN"
        if remaining_timeout is not None:
            msg += f" (remaining {remaining_timeout:.1f}s)"
        super().__init__(msg)


@dataclass
class CircuitBreakerConfig:
    """熔断器配置。"""

    failure_threshold: int = 5  # 失败次数阈值，达到后开启熔断
    recovery_timeout: float = 30.0  # 恢复等待时间（秒）
    half_open_attempts: int = 3  # 半开状态下允许的尝试次数
    success_threshold: int = 2  # 关闭熔断需要的成功次数（half_open 模式下）


class CircuitBreaker:
    """熔断器实现。

    熔断器有三种状态：
    1. CLOSED: 正常状态，请求通过，失败会计数
    2. OPEN: 熔断状态，请求被拒绝，等待恢复超时
    3. HALF_OPEN: 尝试恢复，允许有限请求通过

    用法:
        breaker = CircuitBreaker("data_agent")
        result = await breaker.call(some_coroutine)
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        """初始化熔断器。

        Args:
            name: 熔断器名称（用于日志和错误信息）
            config: 熔断器配置
        """
        self._name = name
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: datetime | None = None
        self._half_open_attempts = 0
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        """熔断器名称。"""
        return self._name

    @property
    def state(self) -> CircuitState:
        """当前熔断器状态。"""
        return self._state

    @property
    def failure_count(self) -> int:
        """当前失败计数。"""
        return self._failure_count

    async def call(self, coro: Awaitable[T]) -> T:
        """通过熔断器执行协程。

        Args:
            coro: 要执行的协程

        Returns:
            协程执行结果

        Raises:
            CircuitOpenError: 熔断器处于 OPEN 状态
        """
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info("circuit %s transitioning to HALF_OPEN", self._name)
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_attempts = 0
                else:
                    remaining = self._remaining_timeout()
                    raise CircuitOpenError(self._name, remaining)

            elif self._state == CircuitState.HALF_OPEN:
                # half_open 状态下限制并发请求
                if self._half_open_attempts >= self._config.half_open_attempts:
                    raise CircuitOpenError(
                        self._name,
                        self._remaining_timeout() or 0.0,
                    )

        try:
            result = await coro
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise

    async def _on_success(self) -> None:
        """处理成功回调。"""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._config.success_threshold:
                    logger.info("circuit %s CLOSED after recovery", self._name)
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                # 成功后重置失败计数
                self._failure_count = 0

    async def _on_failure(self) -> None:
        """处理失败回调。"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now(UTC)

            if self._state == CircuitState.HALF_OPEN:
                # half_open 状态下失败，立即回到 OPEN
                logger.warning("circuit %s back to OPEN from HALF_OPEN", self._name)
                self._state = CircuitState.OPEN
                self._half_open_attempts = 0
                self._success_count = 0

            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self._config.failure_threshold:
                    logger.warning(
                        "circuit %s OPEN after %d failures",
                        self._name,
                        self._failure_count,
                    )
                    self._state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试恢复。"""
        if self._last_failure_time is None:
            return True
        elapsed = (datetime.now(UTC) - self._last_failure_time).total_seconds()
        return elapsed >= self._config.recovery_timeout

    def _remaining_timeout(self) -> float | None:
        """获取剩余等待时间。"""
        if self._last_failure_time is None:
            return None
        elapsed = (datetime.now(UTC) - self._last_failure_time).total_seconds()
        remaining = self._config.recovery_timeout - elapsed
        return max(0.0, remaining)

    async def reset(self) -> None:
        """手动重置熔断器。"""
        async with self._lock:
            logger.info("circuit %s manually reset", self._name)
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_attempts = 0
            self._last_failure_time = None

    def get_stats(self) -> dict[str, Any]:
        """获取熔断器统计信息。"""
        return {
            "name": self._name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None,
            "remaining_timeout": self._remaining_timeout(),
        }


def circuit_breaker(
    name: str,
    config: CircuitBreakerConfig | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """熔断器装饰器。

    用法:
        @circuit_breaker("data_agent")
        async def fetch_data():
            ...

    Args:
        name: 熔断器名称
        config: 熔断器配置

    Returns:
        装饰器函数
    """
    _breakers: dict[str, CircuitBreaker] = {}

    def get_breaker() -> CircuitBreaker:
        if name not in _breakers:
            _breakers[name] = CircuitBreaker(name, config)
        return _breakers[name]

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            breaker = get_breaker()
            return await breaker.call(func(*args, **kwargs))
        return wrapper

    # 暴露 breaker 给装饰器使用者
    wrapper.breaker = get_breaker  # type: ignore[attr-defined]
    return wrapper


class CircuitBreakerRegistry:
    """熔断器注册表，管理多个熔断器。"""

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        """获取或创建熔断器。"""
        async with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
            return self._breakers[name]

    async def get(self, name: str) -> CircuitBreaker | None:
        """获取熔断器。"""
        async with self._lock:
            return self._breakers.get(name)

    async def reset_all(self) -> None:
        """重置所有熔断器。"""
        async with self._lock:
            for breaker in self._breakers.values():
                await breaker.reset()

    def list_breakers(self) -> list[str]:
        """列出所有熔断器名称。"""
        return list(self._breakers.keys())


# 全局熔断器注册表
_global_registry = CircuitBreakerRegistry()


def get_global_breaker_registry() -> CircuitBreakerRegistry:
    """获取全局熔断器注册表。"""
    return _global_registry
