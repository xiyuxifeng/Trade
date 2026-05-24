"""回测结果 API 路由测试。

NTL-S7-005
"""
from dataclasses import dataclass
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any

from httpx import AsyncClient, ASGITransport
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.main import app
from api.routers import backtest_results as router
from src.models.backtest_result_run import BacktestResultRun


@dataclass
class _FakeJobResult:
    status: str
    payload: dict[str, Any]


class _FakeJobService:
    def __init__(self, *, jobs: list[dict[str, Any]], job_lookup: dict[str, dict[str, Any]]) -> None:
        self.jobs = jobs
        self.job_lookup = job_lookup
        self.list_calls: list[dict[str, Any]] = []
        self.get_calls: list[str] = []

    async def list_jobs(self, *, status: str | None = None, job_type: str | None = None, created_by: str | None = None, skip: int = 0, limit: int = 50):
        del created_by, skip, limit
        self.list_calls.append({"status": status, "job_type": job_type})
        filtered = [job for job in self.jobs if (status is None or job.get("status") == status) and (job_type is None or job.get("job_type") == job_type)]
        return _FakeJobResult(status="ok", payload={"count": len(filtered), "total": len(filtered), "skip": 0, "limit": 50, "items": filtered})

    async def get_job(self, job_id: str):
        self.get_calls.append(job_id)
        job = self.job_lookup.get(job_id)
        if job is None:
            return _FakeJobResult(status="partial", payload={"job_id": job_id})
        return _FakeJobResult(status="ok", payload={"job": job, "job_dir": job.get("job_dir")})


def _build_backtest_result_session(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'backtest_results.db'}")

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def _session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return _session_scope, engine


async def _init_backtest_result_schema(engine) -> None:
    """初始化回测摘要表。"""
    async with engine.begin() as conn:
        await conn.run_sync(BacktestResultRun.__table__.create)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _skip_db_backtest_result_runs(**kwargs):  # noqa: ANN003
    del kwargs
    return None


@pytest.mark.asyncio
async def test_list_backtest_results_returns_paginated_response(client: AsyncClient):
    fake_service = _FakeJobService(jobs=[], job_lookup={})
    router_get_job_service = router.get_job_service
    router.get_job_service = lambda: fake_service
    router_load_db_runs = router._load_db_backtest_result_runs
    router._load_db_backtest_result_runs = _skip_db_backtest_result_runs
    try:
        response = await client.get("/backtest_results/", params={"skip": 0, "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "items" in data
    finally:
        router.get_job_service = router_get_job_service
        router._load_db_backtest_result_runs = router_load_db_runs


@pytest.mark.asyncio
async def test_backtest_results_include_job_dir_artifacts(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """job 目录中的回测结果也应被列表和报告接口识别。"""
    jobs_dir = tmp_path / "jobs"
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

    fake_service = _FakeJobService(
        jobs=[
            {
                "id": "job-123",
                "job_type": "backtest-run",
                "status": "success",
                "result": {
                    "status": "ok",
                    "message": "backtest completed",
                    "payload": {
                        "request": {
                            "trader_id": "trader_a",
                            "date_from": "2026-05-01",
                            "date_to": "2026-05-05",
                            "benchmark_symbol": "000300.SH",
                            "market_regime_version": "market-regime-v3",
                            "source_feature_version": "market-regime-features-v3",
                        },
                        "result": {
                            "benchmark_symbol": "000300.SH",
                            "regime_version": "market-regime-v3",
                            "source_feature_version": "market-regime-features-v3",
                            "summary": {
                                "total_days": 5,
                                "total_trades": 3,
                                "valid_trades": 2,
                                "skipped_trades": 1,
                                "win_rate": 0.67,
                                "avg_return_pct": 0.12,
                            },
                        },
                        "summary": {
                            "total_days": 5,
                            "total_trades": 3,
                            "valid_trades": 2,
                            "skipped_trades": 1,
                            "win_rate": 0.67,
                            "avg_return_pct": 0.12,
                        },
                    },
                },
            }
        ],
        job_lookup={
            "job-123": {
                "id": "job-123",
                "job_dir": str(job_dir),
                "result": {
                    "status": "ok",
                    "message": "backtest completed",
                    "payload": {
                        "request": {
                            "trader_id": "trader_a",
                            "date_from": "2026-05-01",
                            "date_to": "2026-05-05",
                            "benchmark_symbol": "000300.SH",
                            "market_regime_version": "market-regime-v3",
                            "source_feature_version": "market-regime-features-v3",
                        },
                        "result": {
                            "benchmark_symbol": "000300.SH",
                            "regime_version": "market-regime-v3",
                            "source_feature_version": "market-regime-features-v3",
                            "summary": {
                                "total_days": 5,
                                "total_trades": 3,
                                "valid_trades": 2,
                                "skipped_trades": 1,
                                "win_rate": 0.67,
                                "avg_return_pct": 0.12,
                            },
                        },
                        "summary": {
                            "total_days": 5,
                            "total_trades": 3,
                            "valid_trades": 2,
                            "skipped_trades": 1,
                            "win_rate": 0.67,
                            "avg_return_pct": 0.12,
                        },
                    },
                },
            }
        },
    )
    monkeypatch.setattr(router, "get_job_service", lambda: fake_service)
    monkeypatch.setattr(router, "_load_db_backtest_result_runs", _skip_db_backtest_result_runs)

    response = await client.get("/backtest_results/", params={"skip": 0, "limit": 10})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["result_id"] == "job-123"
    assert payload["items"][0]["regime_version"] == "market-regime-v3"
    assert fake_service.list_calls

    report_response = await client.get("/backtest_results/job-123/report")
    assert report_response.status_code == 200
    assert report_response.text == "# report"


@pytest.mark.asyncio
async def test_list_backtest_results_paginates_beyond_page_size(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """回测结果列表应分页拉取 jobs，避免 1000 条上限截断。"""

    class _PagedJobService:
        def __init__(self) -> None:
            self.list_calls: list[dict[str, int | str | None]] = []
            self.jobs = [
                {
                    "id": f"job-{i}",
                    "job_type": "backtest-run",
                    "status": "success",
                    "result": {
                        "status": "ok",
                        "payload": {
                            "request": {
                                "trader_id": "trader_a",
                                "date_from": "2026-05-01",
                                "date_to": "2026-05-05",
                            },
                            "result": {"summary": {"total_days": i}},
                            "summary": {"total_days": i},
                        },
                    },
                }
                for i in range(501)
            ]

        async def list_jobs(self, *, status: str | None = None, job_type: str | None = None, created_by: str | None = None, skip: int = 0, limit: int = 50):
            del created_by
            self.list_calls.append({"status": status, "job_type": job_type, "skip": skip, "limit": limit})
            items = [job for job in self.jobs if (status is None or job.get("status") == status) and (job_type is None or job.get("job_type") == job_type)]
            paginated = items[skip : skip + limit]
            return _FakeJobResult(
                status="ok",
                payload={"count": len(paginated), "total": len(items), "skip": skip, "limit": limit, "items": paginated},
            )

        async def get_job(self, job_id: str):
            return _FakeJobResult(status="partial", payload={"job_id": job_id})

    fake_service = _PagedJobService()
    monkeypatch.setattr(router, "get_job_service", lambda: fake_service)
    monkeypatch.setattr(router, "_load_db_backtest_result_runs", _skip_db_backtest_result_runs)

    response = await client.get("/backtest_results/", params={"skip": 0, "limit": 10})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 501
    assert len(payload["items"]) == 10
    assert len(fake_service.list_calls) >= 2


@pytest.mark.asyncio
async def test_list_backtest_results_prefers_summary_table(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """列表接口应优先读取 backtest_result_runs。"""
    session_scope, engine = _build_backtest_result_session(tmp_path)
    await _init_backtest_result_schema(engine)

    async def _seed() -> None:
        async with session_scope() as session:
            session.add(
                BacktestResultRun(
                    result_run_id="run-1",
                    source_job_id="job-1",
                    job_type="backtest-run",
                    request_trader_id="trader_a",
                    strategy_version_id="sv-1",
                    request_date_from=date(2026, 5, 1),
                    request_date_to=date(2026, 5, 5),
                    benchmark_symbol="000300.SH",
                    regime_version="market-regime-v3",
                    source_feature_version="market-regime-features-v3",
                    mode="full",
                    scoring_profile="stage5",
                    result_version="1.0",
                    status="success",
                    quality_status="ok",
                    total_days=5,
                    total_trades=3,
                    valid_trades=2,
                    skipped_trades=1,
                    win_rate=0.67,
                    avg_return_pct=0.12,
                    summary_json={"total_days": 5, "total_trades": 3},
                    regime_metrics_json=[{"regime_version": "market-regime-v3"}],
                    rule_regime_metrics_json={"rule-1": {"score": 0.9}},
                    fingerprint="fp-1",
                    storage_ref={"source": "file"},
                    artifact_ref={"artifact_type": "backtest-result-json"},
                )
            )

    await _seed()

    fake_service = _FakeJobService(jobs=[], job_lookup={})
    monkeypatch.setattr(router, "get_job_service", lambda: fake_service)
    monkeypatch.setattr(router, "session_scope", session_scope)

    response = await client.get("/backtest_results/", params={"skip": 0, "limit": 10, "trader_id": "trader_a"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["count"] == 1
    assert payload["items"][0]["result_id"] == "run-1"
    assert payload["items"][0]["summary"]["total_days"] == 5
    assert fake_service.list_calls == []

    await engine.dispose()
