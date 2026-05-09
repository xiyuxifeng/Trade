"""API 入口一致性测试。"""

from __future__ import annotations

from pathlib import Path

from api.main import app as legacy_app


def test_canonical_entrypoint_exposes_critical_paths() -> None:
    """唯一入口应挂载关键路由。"""
    legacy_paths = set(legacy_app.openapi()["paths"])

    assert "/api/ui/v1/system/status" in legacy_paths
    assert "/api/ui/v1/jobs/definitions" in legacy_paths
    assert "/api/ui/v1/artifacts" in legacy_paths
    assert "/api/ui/v1/market/ohlcv" in legacy_paths
    assert "/run/pre_market" in legacy_paths
    assert "/api/ui/system/status" in legacy_paths


def test_legacy_src_api_main_is_removed() -> None:
    """旧的 src/api/main.py 应已删除，不再作为运行时入口。"""
    repo_root = Path(__file__).resolve().parents[2]
    assert not (repo_root / "src/api/main.py").exists()
