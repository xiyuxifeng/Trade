from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeConfigResolution:
    """把运行时入参归一成可复用的配置视图。"""

    profile_id: str | None = None
    config_path: str | None = None
    profile_snapshot_id: str | None = None
    source: str = "default"


def resolve_runtime_config(params: dict[str, Any] | None) -> RuntimeConfigResolution:
    """解析 Job / Workflow 入参中的运行时配置引用。

    兼容 Web 的 Profile 引用与 CLI 的 config_path 入口，供上层统一选择快照策略。
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
