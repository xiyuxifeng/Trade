from __future__ import annotations

from src.common.paths import project_root, resolve_project_path


def test_resolve_project_path_anchors_relative_paths() -> None:
    """相对路径应锚定到 trade-strategy-ai 项目根目录。"""
    root = project_root()

    assert resolve_project_path("config/app.yaml") == root / "config" / "app.yaml"
    assert resolve_project_path("data/market_universe/snapshots") == root / "data" / "market_universe" / "snapshots"
    assert resolve_project_path("logs") == root / "logs"
