"""单元测试 - 重试策略。"""

from __future__ import annotations

import asyncio
import pytest

from src.agent_net.retry import (
    RetryPolicy,
    RetryExhaustedError,
    BackoffStrategy,
    with_retry,
    retry_async,
    DEFAULT_RETRY_POLICY,
    QUICK_RETRY_POLICY,
    PERSISTENT_RETRY_POLICY,
)


class TestRetryPolicy:
    """测试 RetryPolicy。"""

    def test_default_policy_values(self) -> None:
        """测试默认策略值。"""
        policy = RetryPolicy()

        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.backoff == BackoffStrategy.EXPONENTIAL
        assert policy.retriable_exceptions == (Exception,)

    def test_fixed_backoff(self) -> None:
        """测试固定延迟。"""
        policy = RetryPolicy(backoff=BackoffStrategy.FIXED, base_delay=2.0)

        assert policy.compute_delay(0) == 2.0
        assert policy.compute_delay(1) == 2.0
        assert policy.compute_delay(2) == 2.0

    def test_exponential_backoff(self) -> None:
        """测试指数退避。"""
        policy = RetryPolicy(backoff=BackoffStrategy.EXPONENTIAL, base_delay=1.0)

        assert policy.compute_delay(0) == 1.0
        assert policy.compute_delay(1) == 2.0
        assert policy.compute_delay(2) == 4.0
        assert policy.compute_delay(3) == 8.0

    def test_exponential_backoff_capped(self) -> None:
        """测试指数退避上限。"""
        policy = RetryPolicy(backoff=BackoffStrategy.EXPONENTIAL, base_delay=10.0, max_delay=30.0)

        assert policy.compute_delay(0) == 10.0
        assert policy.compute_delay(1) == 20.0
        assert policy.compute_delay(2) == 30.0  # capped
        assert policy.compute_delay(3) == 30.0  # still capped

    def test_jitter_backoff(self) -> None:
        """测试抖动退避。"""
        policy = RetryPolicy(backoff=BackoffStrategy.JITTER, base_delay=1.0, max_delay=10.0)

        # 抖动范围应该在 [0.5*base, 1.5*base] 范围内
        for _ in range(10):
            delay = policy.compute_delay(1)  # 2^1 * base = 2.0
            assert 1.0 <= delay <= 3.0  # [0.5*2, 1.5*2]

    def test_is_retriable(self) -> None:
        """测试异常是否可重试。"""
        policy = RetryPolicy(retriable_exceptions=(ValueError, TypeError))

        assert policy.is_retriable(ValueError("test")) is True
        assert policy.is_retriable(TypeError("test")) is True
        assert policy.is_retriable(RuntimeError("test")) is False

    def test_is_retriable_all_exceptions(self) -> None:
        """测试捕获所有异常。"""
        policy = RetryPolicy(retriable_exceptions=(Exception,))

        assert policy.is_retriable(ValueError("test")) is True
        assert policy.is_retriable(RuntimeError("test")) is True
        # BaseException 不是 Exception 的子类，所以不会被捕获
        assert policy.is_retriable(BaseException("test")) is False

    def test_is_retriable_with_base_exception(self) -> None:
        """测试捕获 BaseException（包括所有异常）。"""
        policy = RetryPolicy(retriable_exceptions=(BaseException,))

        assert policy.is_retriable(ValueError("test")) is True
        assert policy.is_retriable(BaseException("test")) is True


class TestWithRetry:
    """测试 with_retry 装饰器。"""

    @pytest.mark.asyncio
    async def test_success_without_retry(self) -> None:
        """测试成功后不重试。"""
        call_count = 0

        @with_retry(RetryPolicy(max_attempts=3))
        async def succeed_once() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await succeed_once()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure_then_success(self) -> None:
        """测试失败后重试成功。"""
        call_count = 0

        @with_retry(RetryPolicy(max_attempts=3, base_delay=0.01))
        async def fail_once_then_succeed() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary error")
            return "success"

        result = await fail_once_then_succeed()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self) -> None:
        """测试重试次数耗尽。"""
        call_count = 0

        @with_retry(RetryPolicy(max_attempts=3, base_delay=0.01))
        async def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("permanent error")

        with pytest.raises(RetryExhaustedError) as exc_info:
            await always_fail()

        assert exc_info.value.attempts == 3
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_non_retriable_exception(self) -> None:
        """测试不可重试的异常立即失败。"""
        call_count = 0

        @with_retry(RetryPolicy(max_attempts=3, retriable_exceptions=(ValueError,)))
        async def raise_type_error() -> str:
            nonlocal call_count
            call_count += 1
            raise TypeError("not retriable")

        with pytest.raises(TypeError):
            await raise_type_error()

        assert call_count == 1  # 立即失败，不重试


class TestRetryAsync:
    """测试 retry_async 函数。"""

    @pytest.mark.asyncio
    async def test_retry_async_success(self) -> None:
        """测试 retry_async 成功。"""
        async def succeed() -> str:
            return "success"
        result = await retry_async(lambda: succeed(), DEFAULT_RETRY_POLICY)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_async_with_backoff(self) -> None:
        """测试 retry_async 指数退避。"""
        call_count = 0

        async def unstable() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "ok"

        policy = RetryPolicy(max_attempts=5, base_delay=0.01)
        result = await retry_async(lambda: unstable(), policy)

        assert result == "ok"
        assert call_count == 3


class TestPredefinedPolicies:
    """测试预定义策略。"""

    def test_default_retry_policy(self) -> None:
        """测试默认重试策略。"""
        assert DEFAULT_RETRY_POLICY.max_attempts == 3
        assert DEFAULT_RETRY_POLICY.backoff == BackoffStrategy.EXPONENTIAL

    def test_quick_retry_policy(self) -> None:
        """测试快速重试策略。"""
        assert QUICK_RETRY_POLICY.max_attempts == 2
        assert QUICK_RETRY_POLICY.backoff == BackoffStrategy.FIXED
        assert QUICK_RETRY_POLICY.base_delay == 0.5

    def test_persistent_retry_policy(self) -> None:
        """测试持久重试策略。"""
        assert PERSISTENT_RETRY_POLICY.max_attempts == 5
        assert PERSISTENT_RETRY_POLICY.base_delay == 2.0
        assert PERSISTENT_RETRY_POLICY.backoff == BackoffStrategy.EXPONENTIAL


class TestRetryExhaustedError:
    """测试 RetryExhaustedError。"""

    def test_error_message(self) -> None:
        """测试错误消息。"""
        original = ValueError("original error")
        error = RetryExhaustedError(3, original)

        assert error.attempts == 3
        assert error.last_error is original
        assert "3 attempts" in str(error)
        assert "original error" in str(error)
