from __future__ import annotations


def test_resolve_runtime_config_prefers_profile_context() -> None:
    """Profile 入参应优先作为运行时配置来源。"""
    from src.services.runtime_config import resolve_runtime_config

    resolution = resolve_runtime_config(
        {
            "profile_id": " profile-001 ",
            "config_path": "config/app.yaml",
            "profile_snapshot_id": "snapshot-001",
        }
    )

    assert resolution.profile_id == "profile-001"
    assert resolution.config_path == "config/app.yaml"
    assert resolution.profile_snapshot_id == "snapshot-001"
    assert resolution.source == "profile"


def test_resolve_runtime_config_keeps_cli_config_path() -> None:
    """CLI 兼容路径应继续保留。"""
    from src.services.runtime_config import resolve_runtime_config

    resolution = resolve_runtime_config({"config_path": "config/cli.yaml"})

    assert resolution.profile_id is None
    assert resolution.config_path == "config/cli.yaml"
    assert resolution.profile_snapshot_id is None
    assert resolution.source == "config_path"


def test_resolve_runtime_config_handles_empty_input() -> None:
    """空入参应回落到默认来源。"""
    from src.services.runtime_config import resolve_runtime_config

    resolution = resolve_runtime_config({})

    assert resolution.profile_id is None
    assert resolution.config_path is None
    assert resolution.profile_snapshot_id is None
    assert resolution.source == "default"
