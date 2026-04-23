"""级联降级 provider 实现。"""

from __future__ import annotations

from typing import Any

from src.providers.base import ProviderBase, ProviderError, ProviderResult, ProviderStatus


# 用于标记部分成功的哨兵对象
class _PartialResult:
    """内部哨兵，用于标记部分成功场景。"""
    def __init__(self, errors: list[str], partials: list[dict[str, Any]]) -> None:
        self.errors = errors
        self.partials = partials


class FallbackProvider(ProviderBase):
    """级联降级 provider。

    内部维护 capability -> 有序 provider 列表的映射。
    run() 遍历候选链，直到某个 provider 成功；全部失败时返回聚合错误。
    """

    def __init__(
        self,
        *,
        chains: dict[str, list[ProviderBase]],
        provider_name: str = "fallback",
    ) -> None:
        super().__init__(provider_name=provider_name)
        self.chains = chains

    def request(self, *, capability: str, **kwargs: Any) -> dict[str, Any]:
        """遍历候选链，返回首个成功结果的 payload。"""
        providers = self.chains.get(capability)
        if not providers:
            self.unsupported(capability)

        errors: list[str] = []
        partials: list[dict[str, Any]] = []

        for p in providers:
            try:
                result = p.run(capability, request=kwargs)
                if result.status == ProviderStatus.ok:
                    return result.payload
                # 记录错误和部分结果，供 partial 返回使用
                errors.extend(result.errors)
                if result.payload:
                    partials.append(result.payload)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{type(exc).__name__}: {exc}")

        # 所有 provider 都失败，返回 partial 状态（即使没有 partial results）
        return _PartialResult(errors=errors, partials=partials)

    def run(self, capability: str, *, request: dict[str, Any] | None = None, **kwargs: Any) -> ProviderResult:
        """执行 fallback capability 请求，支持部分结果返回。"""
        request_payload = request or {}
        merged_kwargs = {**request_payload, **kwargs}
        try:
            raw = self.request(capability=capability, **merged_kwargs)
            # 检查是否返回了 partial 结果（通过哨兵对象）
            if isinstance(raw, _PartialResult):
                payload = self.normalize(
                    capability=capability,
                    raw={"partial": True, "errors": raw.errors, "partial_payloads": raw.partials},
                    request=request_payload,
                    **kwargs,
                )
                return ProviderResult(
                    provider=self.provider_name,
                    capability=capability,
                    status=ProviderStatus.partial,
                    payload=payload,
                    errors=raw.errors,
                    metadata={"request": request_payload},
                )
            payload = self.normalize(capability=capability, raw=raw, request=request_payload, **kwargs)
            return ProviderResult(
                provider=self.provider_name,
                capability=capability,
                status=ProviderStatus.ok,
                payload=payload,
                metadata={"request": request_payload},
            )
        except ProviderError:
            # 不捕获 ProviderError，让其直接传播（用于 unsupported capability）
            raise
        except Exception as exc:  # noqa: BLE001
            return ProviderResult(
                provider=self.provider_name,
                capability=capability,
                status=ProviderStatus.error,
                errors=[f"{type(exc).__name__}: {exc}"],
                metadata={"request": request_payload},
            )

    def normalize(
        self,
        *,
        capability: str,
        raw: dict[str, Any],
        request: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """fallback 不做额外归一，直接透传。"""
        if isinstance(raw, dict):
            return raw
        return {"data": raw}
