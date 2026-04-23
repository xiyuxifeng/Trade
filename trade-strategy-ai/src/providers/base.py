from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderStatus(str, Enum):
    """Provider 统一状态。"""

    ok = "ok"
    partial = "partial"
    error = "error"


@dataclass(frozen=True)
class ProviderResult:
    """Provider 统一返回结构。"""

    provider: str
    capability: str
    status: ProviderStatus
    payload: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ProviderError(RuntimeError):
    """Provider 层统一异常。"""


class ProviderBase(ABC):
    """Provider 抽象基类。

    目标：
    - 统一 capability 请求入口
    - 统一成功/失败返回结构
    - 统一异常包装，避免上层直接依赖底层实现细节
    """

    def __init__(self, *, provider_name: str) -> None:
        self.provider_name = provider_name

    @abstractmethod
    def request(self, *, capability: str, **kwargs: Any) -> Any:
        """执行 capability 对应的原始请求。"""

    def normalize(
        self,
        *,
        capability: str,
        raw: Any,
        request: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """把原始结果转换为统一 payload。

        默认直接透传，子类按需要覆盖。
        """

        if isinstance(raw, dict):
            return raw
        return {"data": raw}

    def run(self, capability: str, *, request: dict[str, Any] | None = None, **kwargs: Any) -> ProviderResult:
        """执行一次 provider capability 请求，并返回统一结果。"""

        request_payload = request or {}
        merged_kwargs = {**request_payload, **kwargs}
        try:
            raw = self.request(capability=capability, **merged_kwargs)
            payload = self.normalize(capability=capability, raw=raw, request=request_payload, **kwargs)
            return ProviderResult(
                provider=self.provider_name,
                capability=capability,
                status=ProviderStatus.ok,
                payload=payload,
                metadata={"request": request_payload},
            )
        except ProviderError as exc:
            return ProviderResult(
                provider=self.provider_name,
                capability=capability,
                status=ProviderStatus.error,
                errors=[str(exc)],
                metadata={"request": request_payload},
            )
        except Exception as exc:  # noqa: BLE001
            return ProviderResult(
                provider=self.provider_name,
                capability=capability,
                status=ProviderStatus.error,
                errors=[f"{type(exc).__name__}: {exc}"],
                metadata={"request": request_payload},
            )

    def unsupported(self, capability: str) -> None:
        """抛出统一的不支持能力异常。"""

        raise ProviderError(f"{self.provider_name} does not support capability: {capability}")
