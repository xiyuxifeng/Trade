from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common.config import AppConfig


@dataclass(frozen=True)
class RuntimeConfigResolution:
    """把运行时入参归一成可复用的配置视图。"""

    profile_id: str | None = None
    config_path: str | None = None
    profile_snapshot_id: str | None = None
    source: str = "default"


@dataclass(frozen=True)
class ProfileRuntimeConfig:
    """Profile 运行态配置视图。

    这是 Web 主路径的事实来源：由 `profile_id` 加载 Profile 数据，再 materialize 成
    `AppConfig` 供各类业务服务直接消费，不再依赖 `config_path`。
    """

    profile_id: str
    config: AppConfig
    base_dir: Path
    profile_snapshot_id: str | None = None
    source: str = "profile"


def resolve_runtime_config(params: dict[str, Any] | None) -> RuntimeConfigResolution:
    """解析 Job / Workflow 入参中的运行时配置引用。

    Web 主路径优先使用 Profile；`config_path` 仅作为 CLI / 历史兼容入口保留，供上层统一选择快照策略。
    """

    incoming = dict(params or {})

    profile_id = incoming.get("profile_id")
    if profile_id is not None:
        profile_id = str(profile_id).strip() or None

    config_path = incoming.get("config_path")
    if config_path is not None:
        config_path = str(config_path).strip() or None

    profile_snapshot_id = incoming.get("profile_snapshot_id")
    if profile_snapshot_id is not None:
        profile_snapshot_id = str(profile_snapshot_id).strip() or None

    if profile_id:
        source = "profile"
    elif config_path:
        source = "config_path"
    else:
        source = "default"

    return RuntimeConfigResolution(
        profile_id=profile_id,
        config_path=config_path,
        profile_snapshot_id=profile_snapshot_id,
        source=source,
    )
