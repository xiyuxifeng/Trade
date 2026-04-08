"""错误重试机制。

提供通用的重试策略和装饰器：
- RetryPolicy: 可配置的重试策略
- with_retry: 协程重试装饰器
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, TypeVar, Awaitable
import logging

from src.common.logger import get_logger


logger = get_logger("agent_net.retry")


T = TypeVar("T")


class BackoffStrategy(Enum):
    """重试退避策略。"""

    FIXED = "fixed"  # 固定延迟
    EXPONENTIAL = "exponential"  # 指数退避
    JITTER = "jitter"  # 随机抖动


class RetryExhaustedError(Exception):
    """重试次数耗尽异常。"""

    def __init__(self, attempts: int, last_error: Exception) -> None:
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Retry exhausted after {attempts} attempts: {last_error}")


@dataclass(slots=True)
class RetryPolicy:
    """重试策略配置。

    Attributes:
        max_attempts: 最大尝试次数（包括首次执行）
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        backoff: 退避策略
        retriable_exceptions: 可重试的异常类型元组
        on_retry: 重试时的回调函数 (attempt, error) -> None
    """

    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    backoff: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    retriable_exceptions: tuple[type[Exception], ...] = (Exception,)
    on_retry: Callable[[int, Exception], None] | None = None

    def compute_delay(self, attempt: int) -> float:
        """计算指定尝试次数的延迟时间。

        Args:
            attempt: 尝试次数（从0开始）

        Returns:
            延迟时间（秒）
        """
        if self.backoff == BackoffStrategy.FIXED:
            return self.base_delay

        elif self.backoff == BackoffStrategy.EXPONENTIAL:
            delay = self.base_delay * (2 ** attempt)
            return min(delay, self.max_delay)

        else:  # JITTER
            base = self.base_delay * (2 ** attempt)
            capped = min(base, self.max_delay)
            # 添加 [0.5, 1.5] 范围的随机抖动
            return capped * (0.5 + random.random() * 0.5)

    def is_retriable(self, exception: Exception) -> bool:
        """判断异常是否可重试。

        Args:
            exception: 发生的异常

        Returns:
            True if 可重试
        """
        return isinstance(exception, self.retriable_exceptions)


def with_retry(policy: RetryPolicy) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """重试装饰器。

    用法:
        @with_retry(RetryPolicy(max_attempts=3))
        async def unstable_operation():
            ...

    Args:
        policy: 重试策略

    Returns:
        装饰后的函数
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error: Exception | None = None

            for attempt in range(policy.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except policy.retriable_exceptions as e:
                    last_error = e

                    if attempt < policy.max_attempts - 1:
                        delay = policy.compute_delay(attempt)
                        logger.warning(
                            "retrying after error: %s (attempt %d/%d, delay=%.2fs)",
                            str(e),
                            attempt + 1,
                            policy.max_attempts,
                            delay,
                            extra={"func": func.__name__},
                        )
                        if policy.on_retry:
                            policy.on_retry(attempt, e)
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "retry exhausted: %s (after %d attempts)",
                            str(e),
                            policy.max_attempts,
                            extra={"func": func.__name__},
                        )

            # 所有重试都失败了
            if last_error is not None:
                raise RetryExhaustedError(policy.max_attempts, last_error) from last_error
            # 理论上不会走到这里
            raise RuntimeError("Retry logic error: no error captured")

        return wrapper
    return decorator


async def retry_async(
    coro_factory: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
) -> T:
    """异步重试辅助函数。

    用法:
        result = await retry_async(
            lambda: some_coroutine(),
            RetryPolicy(max_attempts=3),
        )

    注意：传入的是一个返回协程的函数（工厂函数），每次重试时会调用
    此函数来获取新的协程对象。

    Args:
        coro_factory: 返回协程的工厂函数
        policy: 重试策略

    Returns:
        协程执行结果

    Raises:
        RetryExhaustedError: 重试次数耗尽
    """
    last_error: Exception | None = None

    for attempt in range(policy.max_attempts):
        try:
            # 每次重试时创建新的协程
            coro = coro_factory()
            return await coro
        except policy.retriable_exceptions as e:
            last_error = e

            if attempt < policy.max_attempts - 1:
                delay = policy.compute_delay(attempt)
                logger.warning(
                    "retrying after error: %s (attempt %d/%d, delay=%.2fs)",
                    str(e),
                    attempt + 1,
                    policy.max_attempts,
                    delay,
                )
                if policy.on_retry:
                    policy.on_retry(attempt, e)
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "retry exhausted: %s (after %d attempts)",
                    str(e),
                    policy.max_attempts,
                )

    if last_error is not None:
        raise RetryExhaustedError(policy.max_attempts, last_error) from last_error
    raise RuntimeError("Retry logic error: no error captured")


@dataclass
class SimpleRetryState:
    """简单的重试状态追踪。"""

    attempts: int = 0
    last_error: Exception | None = None
    total_retries: int = 0

    def record_attempt(self, error: Exception | None = None) -> None:
        """记录一次尝试。"""
        self.attempts += 1
        if error:
            self.last_error = error
            self.total_retries += 1

    def reset(self) -> None:
        """重置状态。"""
        self.attempts = 0
        self.last_error = None
        # 不重置 total_retries，因为它记录累计重试次数


# 默认重试策略
DEFAULT_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay=1.0,
    max_delay=60.0,
    backoff=BackoffStrategy.EXPONENTIAL,
)

# 快速重试策略（用于非关键操作）
QUICK_RETRY_POLICY = RetryPolicy(
    max_attempts=2,
    base_delay=0.5,
    max_delay=2.0,
    backoff=BackoffStrategy.FIXED,
)

# 持久重试策略（用于关键操作）
PERSISTENT_RETRY_POLICY = RetryPolicy(
    max_attempts=5,
    base_delay=2.0,
    max_delay=120.0,
    backoff=BackoffStrategy.EXPONENTIAL,
    retriable_exceptions=(Exception,),  # 几乎所有异常都重试
)
