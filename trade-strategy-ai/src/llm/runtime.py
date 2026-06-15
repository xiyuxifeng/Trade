from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Protocol

from src.llm.client import LLMClient, LLMClientConfig, LLMError


class PromptRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LLMInvocationTrace:
    provider: str
    model: str
    data: dict[str, Any]
    raw_output: dict[str, Any] | None
    raw_output_text: str | None
    token_usage: dict[str, Any]
    cost_amount: float | None
    cost_currency: str | None


class PromptGateway(Protocol):
    async def invoke_json(
        self,
        *,
        prompt_name: str,
        system_prompt: str,
        user_prompt: str,
        model: str,
    ) -> LLMInvocationTrace: ...


class LLMClientGateway:
    def __init__(self, client: LLMClient) -> None:
        self._client = client

    @classmethod
    def from_config(cls, config: LLMClientConfig) -> "LLMClientGateway":
        return cls(LLMClient(config))

    async def invoke_json(
        self,
        *,
        prompt_name: str,
        system_prompt: str,
        user_prompt: str,
        model: str,
    ) -> LLMInvocationTrace:
        del prompt_name, model
        trace = await self._client.complete_json_with_trace(system_prompt=system_prompt, user_prompt=user_prompt)
        return LLMInvocationTrace(
            provider=str(self._client.cfg.provider or "unknown"),
            model=trace.model,
            data=trace.data,
            raw_output=trace.raw_output,
            raw_output_text=trace.raw_output_text,
            token_usage=trace.token_usage,
            cost_amount=trace.cost_amount,
            cost_currency=trace.cost_currency,
        )


async def invoke_with_bounded_retry(
    gateway: PromptGateway,
    *,
    prompt_name: str,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_attempts: int = 3,
) -> tuple[LLMInvocationTrace, int]:
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            trace = await gateway.invoke_json(
                prompt_name=prompt_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
            )
            return trace, attempt
        except LLMError as exc:
            last_error = exc
            if not exc.retryable or attempt == max_attempts - 1:
                raise PromptRuntimeError(f"{prompt_name} invocation failed: {exc}") from exc
            await asyncio.sleep(2**attempt)
    raise PromptRuntimeError(f"{prompt_name} invocation failed") from last_error
