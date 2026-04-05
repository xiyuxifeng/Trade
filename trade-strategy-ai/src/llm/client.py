from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
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
        # 优先从 DASHSCOPE_API_KEY 获取（如无则用 config/api_key 字段）
        api_key=_env_or(api_key, "DASHSCOPE_API_KEY"),
    )


class LLMClient:
    def __init__(self, cfg: LLMClientConfig) -> None:
        self.cfg = cfg

    def is_enabled(self) -> bool:
        return bool(self.cfg.provider and self.cfg.model and self.cfg.api_key)

    def _missing_fields(self) -> list[str]:
        missing: list[str] = []
        if not (self.cfg.provider and str(self.cfg.provider).strip()):
            missing.append("provider")
        if not (self.cfg.model and str(self.cfg.model).strip()):
            missing.append("model")
        if not (self.cfg.url and str(self.cfg.url).strip()):
            missing.append("url")
        if not (self.cfg.api_key and str(self.cfg.api_key).strip()):
            missing.append("api_key")
        return missing

    async def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        missing = self._missing_fields()
        if missing:
            raise LLMError(f"LLM is not configured (missing: {', '.join(missing)})")

        provider = (self.cfg.provider or "").lower().strip()
        # 支持 qwen 走 openai 兼容模式
        if provider in {"openai", "openai_compatible", "qwen", "deepseek"}:
            return await self._openai_chat_json(system_prompt=system_prompt, user_prompt=user_prompt)
        if provider == "anthropic":
            return await self._anthropic_json(system_prompt=system_prompt, user_prompt=user_prompt)
        raise LLMError(f"Unsupported LLM provider: {self.cfg.provider}")

    async def complete_text(self, *, system_prompt: str, user_prompt: str) -> str:
        """按 llm_test.py 的方式返回纯文本（不强制 JSON）。"""

        missing = self._missing_fields()
        if missing:
            raise LLMError(f"LLM is not configured (missing: {', '.join(missing)})")

        provider = (self.cfg.provider or "").lower().strip()
        if provider in {"openai", "openai_compatible", "qwen", "deepseek"}:
            return await self._openai_chat_text(system_prompt=system_prompt, user_prompt=user_prompt)
        if provider == "anthropic":
            raise LLMError("complete_text for anthropic is not implemented")
        raise LLMError(f"Unsupported LLM provider: {self.cfg.provider}")

    async def _openai_chat_content(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None,
    ) -> str:
        if not self.cfg.url:
            raise LLMError("LLM URL (llm.url) 未配置！")

        client = AsyncOpenAI(
            api_key=str(self.cfg.api_key),
            base_url=self.cfg.url.rstrip("/"),
            timeout=self.cfg.timeout_seconds,
        )

        request: dict[str, Any] = {
            "model": str(self.cfg.model),
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if response_format is not None:
            request["response_format"] = response_format

        try:
            completion = await client.chat.completions.create(**request)
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"LLM request failed: {exc}") from exc

        try:
            content = completion.choices[0].message.content
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Unexpected LLM response shape: {completion}") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMError(f"Empty LLM content: {content!r}")
        return content

    async def _openai_chat_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        content = await self._openai_chat_content(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            # 尽量要求 JSON 输出；不支持的兼容实现会忽略
            response_format={"type": "json_object"},
        )

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM output is not valid JSON: {content[:500]}") from exc

    async def _openai_chat_text(self, *, system_prompt: str, user_prompt: str) -> str:
        return await self._openai_chat_content(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=None,
        )

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
