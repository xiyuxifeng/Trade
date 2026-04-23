from __future__ import annotations

from src.providers.base import ProviderBase, ProviderError, ProviderStatus


class DummyProvider(ProviderBase):
    def __init__(self) -> None:
        super().__init__(provider_name="dummy")

    def request(self, *, capability: str, **kwargs):
        if capability == "boom":
            raise ProviderError("boom")
        return {"capability": capability, "kwargs": kwargs}

    def normalize(self, *, capability: str, raw, request=None, **kwargs):
        return {"capability": capability, "raw": raw, "request": request or {}, "kwargs": kwargs}


def test_provider_base_wraps_successful_request_and_normalization() -> None:
    provider = DummyProvider()

    result = provider.run("hot_topics", request={"trade_date": "2026-04-22"}, slot="09-25")

    assert result.provider == "dummy"
    assert result.capability == "hot_topics"
    assert result.status == ProviderStatus.ok
    assert result.payload["capability"] == "hot_topics"
    assert result.payload["request"]["trade_date"] == "2026-04-22"
    assert result.payload["kwargs"]["slot"] == "09-25"


def test_provider_base_wraps_provider_error() -> None:
    provider = DummyProvider()

    result = provider.run("boom")

    assert result.status == ProviderStatus.error
    assert result.errors == ["boom"]
