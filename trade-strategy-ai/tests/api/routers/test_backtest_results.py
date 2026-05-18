"""回测结果 API 路由测试。

NTL-S7-005
"""
from pathlib import Path

from httpx import AsyncClient, ASGITransport
import pytest

from api.main import app
from src.common.paths import project_root


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_backtest_results_returns_paginated_response(client: AsyncClient):
    response = await client.get("/backtest_results/", params={"skip": 0, "limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "items" in data


@pytest.mark.asyncio
async def test_backtest_results_include_job_dir_artifacts(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """job 目录中的回测结果也应被列表和报告接口识别。"""
    from api.routers import backtest_results as router

    legacy_dir = tmp_path / "legacy"
    jobs_dir = tmp_path / "jobs"
    legacy_dir.mkdir()
    jobs_dir.mkdir()

    job_dir = jobs_dir / "job-123"
    job_dir.mkdir()
    (job_dir / "result.json").write_text(
        """
        {
          "request_trader_id": "trader_a",
          "request_date_from": "2026-05-01",
          "request_date_to": "2026-05-05",
          "benchmark_symbol": "000300.SH",
          "regime_version": "market-regime-v3",
          "source_feature_version": "market-regime-features-v3",
          "summary": {
            "total_days": 5,
            "total_trades": 3,
            "valid_trades": 2,
            "skipped_trades": 1,
            "win_rate": 0.67,
            "avg_return_pct": 0.12
          }
        }
        """,
        encoding="utf-8",
    )
    (job_dir / "backtest_report.md").write_text("# report", encoding="utf-8")

    monkeypatch.setattr(router, "_get_backtest_results_dirs", lambda: [legacy_dir, jobs_dir])

    response = await client.get("/backtest_results/", params={"skip": 0, "limit": 10})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["result_id"] == "job-123"
    assert payload["items"][0]["regime_version"] == "market-regime-v3"

    report_response = await client.get("/backtest_results/job-123/report")
    assert report_response.status_code == 200
    assert report_response.text == "# report"


def test_backtest_result_dirs_are_project_root_relative() -> None:
    """回测结果目录应锚定到 trade-strategy-ai 项目根目录。"""
    from api.routers.backtest_results import _get_backtest_results_dirs

    dirs = _get_backtest_results_dirs()
    assert dirs == [
        project_root() / "data" / "backtest" / "results",
        project_root() / "data" / "processed" / "backtest",
        project_root() / "data" / "jobs",
    ]
