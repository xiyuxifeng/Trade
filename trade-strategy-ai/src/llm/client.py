from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
import httpx


class LLMError(RuntimeError):
    """LLM 调用错误。

    `retryable=False` 表示该错误不可重试，也不应切换到后续模型。
    """

    def __init__(self, message: str, *, retryable: bool = True, code: str | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.code = code


@dataclass(frozen=True, slots=True)
class LLMResult:
    """LLM 调用结果，包含原始 JSON 输出和实际使用的模型。"""
    data: dict[str, Any]
    model: str  # 实际使用的模型名称


# LLM API 调用重试次数
LLM_MAX_RETRIES = 3
_FATAL_LLM_KEYWORDS = (
    "invalid_api_key",
    "invalid api key",
    "incorrect api key",
    "unauthorized",
    "forbidden",
    "authentication",
    "api key",
    "apikey",
    "allocationquota",
    "freetieronly",
    "free tier",
    "free-tier",
    "quota exhausted",
    "quota exceeded",
    "insufficient quota",
    "insufficient_quota",
    "quota limit",
    "resource exhausted",
)


@dataclass(frozen=True, slots=True)
class LLMClientConfig:
    provider: str | None
    model: str | list[str] | None  # 支持单模型或多模型数组
    url: str | None
    api_key: str | None
    timeout_seconds: float = 60.0


def _env_or(value: str | None, env_key: str) -> str | None:
    return value or os.getenv(env_key)


def _llm_error_metadata(exc: Exception) -> tuple[bool, str | None]:
    """判断 LLM 错误是否可重试，并返回分类码。"""
    status_candidates: list[int] = []
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        status_candidates.append(status)
    response = getattr(exc, "response", None)
    if response is not None:
        response_status = getattr(response, "status_code", None)
        if isinstance(response_status, int):
            status_candidates.append(response_status)

    if any(status in {401, 403} for status in status_candidates):
        return False, str(next(status for status in status_candidates if status in {401, 403}))

    message = str(exc).lower()
    if "401" in message or "403" in message:
        return False, "401" if "401" in message else "403"
    if any(keyword in message for keyword in _FATAL_LLM_KEYWORDS):
        return False, "auth"
    if "not configured" in message or "missing:" in message or "unsupported llm provider" in message:
        return False, "config"
    return True, None


def from_env_and_config(*, provider: str | None, model: str | None, url: str | None, api_key: str | None) -> LLMClientConfig:
    # 处理 model 可能是列表的情况
    resolved_model: str | list[str] | None = None
    if isinstance(model, list):
        resolved_model = model if model else None
    elif model:
        resolved_model = _env_or(model, "LLM_MODEL")
    else:
        resolved_model = os.getenv("LLM_MODEL")

    return LLMClientConfig(
        provider=_env_or(provider, "LLM_PROVIDER"),
        model=resolved_model,
        url=_env_or(url, "LLM_URL"),
        # 优先从 DASHSCOPE_API_KEY 获取（如无则用 config/api_key 字段）
        api_key=_env_or(api_key, "DASHSCOPE_API_KEY"),
    )


class LLMClient:
    def __init__(self, cfg: LLMClientConfig) -> None:
        self.cfg = cfg

    def is_enabled(self) -> bool:
        return bool(self.cfg.provider and self.cfg.model and self.cfg.api_key)

    def _normalize_models(self) -> list[str]:
        """将 model 配置标准化为模型列表。"""
        model = self.cfg.model
        if model is None:
            return []
        if isinstance(model, str):
            return [model]
        if isinstance(model, list):
            return [m for m in model if m]
        return []

    def _missing_fields(self) -> list[str]:
        missing: list[str] = []
        if not (self.cfg.provider and str(self.cfg.provider).strip()):
            missing.append("provider")
        if not (self.cfg.model):
            missing.append("model")
        if not (self.cfg.url and str(self.cfg.url).strip()):
            missing.append("url")
        if not (self.cfg.api_key and str(self.cfg.api_key).strip()):
            missing.append("api_key")
        return missing

    async def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """单次 LLM 调用，不重试。"""
        missing = self._missing_fields()
        if missing:
            raise LLMError(f"LLM is not configured (missing: {', '.join(missing)})", retryable=False, code="config")

        models = self._normalize_models()
        if not models:
            raise LLMError("No models configured", retryable=False, code="config")

        # 使用第一个模型
        return await self._call_with_model(models[0], system_prompt, user_prompt)

    async def complete_json_with_retry(self, *, system_prompt: str, user_prompt: str) -> LLMResult:
        """带重试和模型降级的 LLM 调用。

        策略：
        1. 按顺序尝试每个模型
        2. 每个模型最多重试 3 次（指数退避）
        3. 所有模型都失败后抛出异常

        Returns:
            LLMResult: 包含实际使用的模型和数据
        """
        missing = self._missing_fields()
        if missing:
            raise LLMError(f"LLM is not configured (missing: {', '.join(missing)})", retryable=False, code="config")

        models = self._normalize_models()
        if not models:
            raise LLMError("No models configured", retryable=False, code="config")

        last_error: LLMError | None = None
        for model in models:
            for attempt in range(LLM_MAX_RETRIES):
                try:
                    data = await self._call_with_model(model, system_prompt, user_prompt)
                    return LLMResult(data=data, model=model)
                except LLMError as exc:
                    last_error = exc
                    if not exc.retryable:
                        raise
                    if attempt < LLM_MAX_RETRIES - 1:
                        await asyncio.sleep(2 ** attempt)  # 指数退避: 1, 2, 4 秒

        # 所有模型和重试都失败
        raise last_error or LLMError("All models failed")

    async def _call_with_model(self, model: str, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """使用指定模型调用 LLM。"""
        provider = (self.cfg.provider or "").lower().strip()
        if provider in {"openai", "openai_compatible", "qwen", "deepseek", "glm"}:
            return await self._openai_chat_json(model=model, system_prompt=system_prompt, user_prompt=user_prompt)
        if provider == "anthropic":
            return await self._anthropic_json(model=model, system_prompt=system_prompt, user_prompt=user_prompt)
        raise LLMError(f"Unsupported LLM provider: {self.cfg.provider}", retryable=False, code="config")

    async def complete_text(self, *, system_prompt: str, user_prompt: str) -> str:
        """按 llm_test.py 的方式返回纯文本（不强制 JSON）。"""

        missing = self._missing_fields()
        if missing:
            raise LLMError(f"LLM is not configured (missing: {', '.join(missing)})")

        provider = (self.cfg.provider or "").lower().strip()
        models = self._normalize_models()
        if not models:
            raise LLMError("No models configured")

        if provider in {"openai", "openai_compatible", "qwen", "deepseek", "glm"}:
            return await self._openai_chat_text(model=models[0], system_prompt=system_prompt, user_prompt=user_prompt)
        if provider == "anthropic":
            raise LLMError("complete_text for anthropic is not implemented", retryable=False, code="config")
        raise LLMError(f"Unsupported LLM provider: {self.cfg.provider}", retryable=False, code="config")

    async def _openai_chat_content(
        self,
        *,
        model: str,
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
            "model": model,
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
            retryable, code = _llm_error_metadata(exc)
            raise LLMError(f"LLM request failed: {exc}", retryable=retryable, code=code) from exc

        try:
            content = completion.choices[0].message.content
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Unexpected LLM response shape: {completion}") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMError(f"Empty LLM content: {content!r}")
        return content

    async def _openai_chat_json(self, *, model: str, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        content = await self._openai_chat_content(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            # 尽量要求 JSON 输出；不支持的兼容实现会忽略
            response_format={"type": "json_object"},
        )

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM output is not valid JSON: {content[:500]}") from exc

    async def _openai_chat_text(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        return await self._openai_chat_content(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=None,
        )

    async def _anthropic_json(self, *, model: str, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        base_url = (self.cfg.url or "https://api.anthropic.com").rstrip("/")
        url = f"{base_url}/v1/messages"
        headers = {
            "x-api-key": str(self.cfg.api_key),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": 2048,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        async with httpx.AsyncClient(timeout=self.cfg.timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                retryable, code = _llm_error_metadata(Exception(f"{resp.status_code} {resp.text}"))
                raise LLMError(f"Anthropic request failed: {resp.status_code} {resp.text}", retryable=retryable, code=code)
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
