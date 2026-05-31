"""Imports UI BFF 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
import api.routers.ui.imports as imports_module
from api.routers.ui.imports import get_setup_service
from src.services.base import ServiceResult


@dataclass
class _FakeSetupService:
    import_calls: list[dict[str, Any]] = field(default_factory=list)
    migrate_calls: list[dict[str, Any]] = field(default_factory=list)

    async def import_trade_logs(
        self,
        *,
        profile_id: str | None = None,
        config_path: str | None = None,
        csv_path: str | None = None,
        source: str = "csv_import",
        trader_account_map: dict[str, str] | None = None,
        dry_run: bool = False,
    ) -> ServiceResult:
        self.import_calls.append(
            {
                "profile_id": profile_id,
                "config_path": config_path,
                "csv_path": csv_path,
                "source": source,
                "trader_account_map": trader_account_map,
                "dry_run": dry_run,
            }
        )
        return ServiceResult(
            status="ok",
            message="trade logs parsed",
            payload={
                "config_path": config_path,
                "csv_path": csv_path,
                "rows_seen": 1,
                "invalid": 0,
                "duplicates": 0,
                "issues": [],
                "parsed_count": 1,
                "stored_count": 0,
                "dry_run": dry_run,
            },
        )

    async def migrate_crawl_state(self, *, profile_id: str | None = None, config_path: str | None = None) -> ServiceResult:
        self.migrate_calls.append({"profile_id": profile_id, "config_path": config_path})
        return ServiceResult(
            status="ok",
            message="crawl state migrated",
            payload={
                "profile_id": profile_id,
                "config_path": config_path,
                "base_dir": "/tmp/project",
                "migrated": 2,
                "skipped": 0,
                "results": [{"source": "tgb", "author_id": "10461311", "status": "migrated"}],
            },
        )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    fake_service = _FakeSetupService()
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_setup_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_import_trade_logs_dry_run_returns_summary(client: AsyncClient, tmp_path) -> None:
    """上传交易日志应走临时后端副本并返回干跑摘要。"""
    sample = tmp_path / "sample.csv"
    sample.write_text("date,symbol,qty\n2026-05-09,000001.SZ,10\n", encoding="utf-8")
    with sample.open("rb") as fh:
        response = await client.post(
            "/api/ui/v1/imports/trade-logs",
            data={"dry_run": "true"},
            files={"file": ("sample.csv", fh, "text/csv")},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run"] is True
    assert payload["rows_seen"] == 1


@pytest.mark.asyncio
async def test_import_trade_logs_rejects_unsupported_extension(client: AsyncClient, tmp_path) -> None:
    """路由应拒绝不支持的文件扩展名。"""
    sample = tmp_path / "sample.txt"
    sample.write_text("noop", encoding="utf-8")
    with sample.open("rb") as fh:
        response = await client.post(
            "/api/ui/v1/imports/trade-logs",
            data={"dry_run": "true"},
            files={"file": ("sample.txt", fh, "text/plain")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_import_trade_logs_rejects_invalid_content_type(client: AsyncClient, tmp_path) -> None:
    """路由应拒绝与扩展名不匹配的 MIME 类型。"""
    sample = tmp_path / "sample.csv"
    sample.write_text("noop", encoding="utf-8")
    with sample.open("rb") as fh:
        response = await client.post(
            "/api/ui/v1/imports/trade-logs",
            data={"dry_run": "true"},
            files={"file": ("sample.csv", fh, "application/json")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_import_trade_logs_rejects_path_like_filename(client: AsyncClient, tmp_path) -> None:
    """路由应拒绝带路径段的上传文件名。"""
    sample = tmp_path / "sample.csv"
    sample.write_text("noop", encoding="utf-8")
    with sample.open("rb") as fh:
        response = await client.post(
            "/api/ui/v1/imports/trade-logs",
            data={"dry_run": "true"},
            files={"file": ("../sample.csv", fh, "text/csv")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_import_trade_logs_rejects_backslash_path_like_filename(client: AsyncClient, tmp_path) -> None:
    """路由应拒绝带反斜杠路径段的上传文件名。"""
    sample = tmp_path / "sample.csv"
    sample.write_text("noop", encoding="utf-8")
    with sample.open("rb") as fh:
        response = await client.post(
            "/api/ui/v1/imports/trade-logs",
            data={"dry_run": "true"},
            files={"file": ("..\\sample.csv", fh, "text/csv")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_import_trade_logs_rejects_oversized_file(client: AsyncClient, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """路由应拒绝超出大小上限的上传文件。"""
    monkeypatch.setattr(imports_module, "_MAX_UPLOAD_BYTES", 8)
    sample = tmp_path / "sample.csv"
    sample.write_text("123456789", encoding="utf-8")
    with sample.open("rb") as fh:
        response = await client.post(
            "/api/ui/v1/imports/trade-logs",
            data={"dry_run": "true"},
            files={"file": ("sample.csv", fh, "text/csv")},
        )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_migrate_crawl_state_returns_job_or_summary(client: AsyncClient) -> None:
    """crawl state 迁移应返回结果摘要。"""
    response = await client.post("/api/ui/v1/imports/crawl-state/migrate", json={})
    assert response.status_code == 200
    payload = response.json()
    assert payload["migrated"] == 2
