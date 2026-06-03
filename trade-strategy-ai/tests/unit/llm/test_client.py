from __future__ import annotations

import pytest

from src.llm.client import LLMClient, LLMClientConfig, LLMError


@pytest.mark.asyncio
async def test_complete_json_with_retry_stops_on_non_retryable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = LLMClient(
        LLMClientConfig(
            provider="qwen",
            model=["qwen3-8b", "qwen2-7b"],
            url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="test-key",
        )
    )

    attempts: list[str] = []

    async def fake_call(model: str, system_prompt: str, user_prompt: str) -> dict[str, object]:
        attempts.append(model)
        del system_prompt, user_prompt
        raise LLMError("LLM request failed: Error code: 401 - invalid_api_key", retryable=False, code="401")

    monkeypatch.setattr(client, "_call_with_model", fake_call)

    with pytest.raises(LLMError) as exc_info:
        await client.complete_json_with_retry(system_prompt="system", user_prompt="user")

    assert attempts == ["qwen3-8b"]
    assert exc_info.value.retryable is False
    assert exc_info.value.code == "401"


@pytest.mark.asyncio
async def test_openai_chat_content_marks_401_as_non_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.llm import client as client_mod

    class _FakeExc(Exception):
        status_code = 401

        def __str__(self) -> str:
            return "Incorrect API key provided"

    class _FakeCompletions:
        async def create(self, **kwargs):
            del kwargs
            raise _FakeExc()

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeOpenAI:
        def __init__(self, **kwargs):
            del kwargs
            self.chat = _FakeChat()

    monkeypatch.setattr(client_mod, "AsyncOpenAI", _FakeOpenAI)

    cfg = LLMClientConfig(
        provider="qwen",
        model="qwen3-8b",
        url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="test-key",
    )
    client = LLMClient(cfg)

    with pytest.raises(LLMError) as exc_info:
        await client._openai_chat_content(
            model="qwen3-8b",
            system_prompt="system",
            user_prompt="user",
            response_format=None,
        )

    assert exc_info.value.retryable is False
    assert exc_info.value.code == "401"


@pytest.mark.asyncio
async def test_complete_json_with_retry_stops_on_403_quota_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = LLMClient(
        LLMClientConfig(
            provider="qwen",
            model=["qwen3-8b", "qwen2-7b"],
            url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="test-key",
        )
    )

    attempts: list[str] = []

    async def fake_call(model: str, system_prompt: str, user_prompt: str) -> dict[str, object]:
        attempts.append(model)
        del system_prompt, user_prompt
        raise LLMError(
            "LLM request failed: Error code: 403 - AllocationQuota.FreeTierOnly",
            retryable=False,
            code="403",
        )

    monkeypatch.setattr(client, "_call_with_model", fake_call)

    with pytest.raises(LLMError) as exc_info:
        await client.complete_json_with_retry(system_prompt="system", user_prompt="user")

    assert attempts == ["qwen3-8b"]
    assert exc_info.value.retryable is False
    assert exc_info.value.code == "403"
