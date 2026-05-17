"""API app factory 测试。"""

from __future__ import annotations

from api.app import create_app


def test_create_app_registers_critical_routes() -> None:
    """共享 app factory 应挂载关键路由。"""
    app = create_app()
    paths = set(app.openapi()["paths"])
    assert "/health" in paths
    assert "/run/pre_market" in paths
    assert "/reports/daily" in paths
    assert "/api/ui/v1/system/status" in paths
    assert "/api/ui/v1/jobs/definitions" in paths
    assert "/api/ui/v1/workflows" in paths
    assert "/api/ui/v1/optimize/versions" in paths
    assert "/api/ui/v1/rule-pool" in paths
    assert "/api/ui/v1/profiles" in paths
    assert "/api/ui/v1/artifacts" in paths
    assert "/api/ui/v1/market/ohlcv" in paths
    assert "/api/ui/v1/market/snapshots" in paths
