from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ServiceResult(BaseModel):
    """服务层统一返回结构。

    说明：
    - `status` 统一表达执行结果，供 CLI / Web API 复用。
    - `message` 用于给上层展示简短摘要。
    - `payload` 放结构化业务数据，不直接拼接终端文本。
    """

    status: Literal["ok", "partial", "error"] = "ok"
    message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class BaseService:
    """Web/CLI 共用的服务基类。

    该类只承载服务层公共约定，不依赖 Typer，也不负责终端输出。
    """

    service_name: str = "base"

