"""FallbackProvider 单元测试。"""

import pytest
from src.providers.base import ProviderBase, ProviderResult, ProviderStatus


def test_fallback_provider_basic_structure():
    """FallbackProvider 应继承 ProviderBase 并实现 request/normalize。"""
    from src.providers.fallback_provider import FallbackProvider

    provider = FallbackProvider(chains={"hot_topics": []})
    assert isinstance(provider, ProviderBase)
    assert provider.provider_name == "fallback"


def test_run_falls_back_on_second_provider():
    """主 provider 失败时，FallbackProvider 应自动尝试下一个。"""
    from src.providers.base import ProviderError, ProviderStatus
    from src.providers.fallback_provider import FallbackProvider

    primary = _MakeFailingProvider(provider_name="primary")
    secondary = _MakeSucceedProvider(provider_name="secondary", payload={"dataset": "hot_topics", "value": 42})

    provider = FallbackProvider(chains={"hot_topics": [primary, secondary]})
    result = provider.run("hot_topics", request={"trade_date": "2026-04-23"})

    assert result.status == ProviderStatus.ok
    assert result.provider == "fallback"
    assert result.payload == {"dataset": "hot_topics", "value": 42}


def test_run_returns_partial_when_all_fail():
    """所有 provider 都失败时，应返回 partial 状态和完整错误列表。"""
    from src.providers.base import ProviderStatus
    from src.providers.fallback_provider import FallbackProvider

    p1 = _MakeFailingProvider(provider_name="p1", error_msg="connection error")
    p2 = _MakeFailingProvider(provider_name="p2", error_msg="timeout")

    provider = FallbackProvider(chains={"hot_topics": [p1, p2]})
    result = provider.run("hot_topics", request={"trade_date": "2026-04-23"})

    assert result.status == ProviderStatus.partial
    assert len(result.errors) == 2
    assert "connection error" in result.errors[0]
    assert "timeout" in result.errors[1]


def test_run_returns_ok_with_single_provider():
    """只有一个 provider 且成功时，直接返回其结果。"""
    from src.providers.base import ProviderStatus
    from src.providers.fallback_provider import FallbackProvider

    ok_provider = _MakeSucceedProvider(provider_name="only", payload={"dataset": "ohlcv_1d", "bars": []})
    provider = FallbackProvider(chains={"ohlcv_1d": [ok_provider]})
    result = provider.run("ohlcv_1d", request={"symbol": "000001"})

    assert result.status == ProviderStatus.ok
    assert result.provider == "fallback"


def test_unsupported_capability_raises():
    """未配置 capability 时应抛出 ProviderError。"""
    from src.providers.base import ProviderError
    from src.providers.fallback_provider import FallbackProvider

    provider = FallbackProvider(chains={})
    with pytest.raises(ProviderError, match="fallback does not support capability"):
        provider.run("unknown_cap", request={})


# --- helpers ---

class _MakeSucceedProvider:
    def __init__(self, provider_name: str, payload: dict):
        self.provider_name = provider_name
        self._payload = payload

    def run(self, capability: str, *, request=None):
        from src.providers.base import ProviderResult, ProviderStatus
        return ProviderResult(
            provider=self.provider_name,
            capability=capability,
            status=ProviderStatus.ok,
            payload=self._payload,
        )

    def request(self, **kwargs):
        return self._payload


class _MakeFailingProvider:
    def __init__(self, provider_name: str, error_msg: str = "failed"):
        self.provider_name = provider_name
        self._error_msg = error_msg

    def run(self, capability: str, *, request=None):
        from src.providers.base import ProviderResult, ProviderStatus
        return ProviderResult(
            provider=self.provider_name,
            capability=capability,
            status=ProviderStatus.error,
            errors=[self._error_msg],
            payload={},
        )

    def request(self, **kwargs):
        raise Exception(self._error_msg)
