"""API app factory 测试。"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

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


def test_request_middleware_injects_request_id(caplog) -> None:
    """请求入口应返回 request_id 并在日志中携带该上下文。"""
    client = TestClient(create_app())

    with caplog.at_level(logging.INFO):
        response = client.get("/health")

    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id
    assert any(
        record.request_id == request_id and "request completed method=GET path=/health" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_app_lifespan_disposes_cached_engine_on_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    """应用关闭时必须释放缓存的异步数据库引擎。"""
    dispose_cached_engine = AsyncMock()
    monkeypatch.setattr("api.app.dispose_cached_engine", dispose_cached_engine, raising=False)

    application = create_app()
    async with application.router.lifespan_context(application):
        pass

    dispose_cached_engine.assert_awaited_once()
