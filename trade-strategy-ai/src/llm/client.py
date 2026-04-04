from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LLMClientConfig:
    provider: str | None
    model: str | None
    url: str | None
    api_key: str | None
    timeout_seconds: float = 60.0


def _env_or(value: str | None, env_key: str) -> str | None:
    return value or os.getenv(env_key)


def from_env_and_config(*, provider: str | None, model: str | None, url: str | None, api_key: str | None) -> LLMClientConfig:
    return LLMClientConfig(
        provider=_env_or(provider, "LLM_PROVIDER"),
        model=_env_or(model, "LLM_MODEL"),
        url=_env_or(url, "LLM_URL"),
        api_key=_env_or(api_key, "LLM_API_KEY"),
    )


class LLMClient:
    def __init__(self, cfg: LLMClientConfig) -> None:
        self.cfg = cfg

    def is_enabled(self) -> bool:
        return bool(self.cfg.provider and self.cfg.model and self.cfg.api_key)

    async def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.is_enabled():
            raise LLMError("LLM is not configured (provider/model/api_key missing)")

        provider = (self.cfg.provider or "").lower().strip()
        if provider in {"openai", "openai_compatible"}:
            return await self._openai_chat_json(system_prompt=system_prompt, user_prompt=user_prompt)
        if provider == "anthropic":
            return await self._anthropic_json(system_prompt=system_prompt, user_prompt=user_prompt)
        raise LLMError(f"Unsupported LLM provider: {self.cfg.provider}")

    async def _openai_chat_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        base_url = (self.cfg.url or "https://api.openai.com/v1").rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.cfg.api_key}"}
        payload: dict[str, Any] = {
            "model": self.cfg.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            # 尽量要求 JSON 输出；不支持的兼容实现会忽略
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=self.cfg.timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise LLMError(f"OpenAI-compatible request failed: {resp.status_code} {resp.text}")
            data = resp.json()

        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Unexpected OpenAI response shape: {data}") from exc

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM output is not valid JSON: {content[:500]}") from exc

    async def _anthropic_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        base_url = (self.cfg.url or "https://api.anthropic.com").rstrip("/")
        url = f"{base_url}/v1/messages"
        headers = {
            "x-api-key": str(self.cfg.api_key),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.cfg.model,
            "max_tokens": 2048,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        async with httpx.AsyncClient(timeout=self.cfg.timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise LLMError(f"Anthropic request failed: {resp.status_code} {resp.text}")
            data = resp.json()

        try:
            # Claude messages API: content is a list of blocks
            blocks = data.get("content")
            if not isinstance(blocks, list) or not blocks:
                raise ValueError("Missing content blocks")
            text = blocks[0].get("text")
            if not isinstance(text, str):
                raise ValueError("Missing text in content block")
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Unexpected Anthropic response shape: {data}") from exc

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM output is not valid JSON: {text[:500]}") from exc
