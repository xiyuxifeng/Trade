from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from src.health.models import ComponentCheck, DetailedHealthResponse, HealthStatus, OverallStatus
from src.services.base import ServiceResult


@dataclass
class _FakeHealthService:
    async def check_detailed(self, timeout: float = 10.0) -> DetailedHealthResponse:
        return DetailedHealthResponse(
            status=OverallStatus.HEALTHY,
            components={
                "database": ComponentCheck(name="database", status=HealthStatus.OK, latency_ms=3.2),
            },
            issues=[],
        )


@dataclass
class _FakeJobService:
    calls: list[dict[str, Any]]

    def __init__(self) -> None:
        self.calls = []

    async def list_jobs(self, *, status=None, job_type=None, created_by=None, skip=0, limit=50) -> ServiceResult:
        self.calls.append({"status": status, "job_type": job_type, "created_by": created_by, "skip": skip, "limit": limit})
        if status == "failed":
            return ServiceResult(
                status="ok",
                message="jobs listed",
                payload={
                    "count": 1,
                    "total": 1,
                    "skip": 0,
                    "limit": limit,
                    "items": [
                        {
                            "id": "job-failed-1",
                            "job_type": "run_after_close",
                            "status": "failed",
                            "started_at": "2026-05-11T09:00:00+00:00",
                            "finished_at": "2026-05-11T09:03:00+00:00",
                            "heartbeat_at": "2026-05-11T09:02:30+00:00",
                            "error": {"message": "boom"},
                            "audit_events": [
                                {
                                    "job_id": "job-failed-1",
                                    "payload": {"request_context": {"path": "/api/ui/v1/jobs", "method": "POST", "client_host": "127.0.0.1"}},
                                }
                            ],
                        }
                    ],
                },
            )
        if status == "running":
            return ServiceResult(
                status="ok",
                message="jobs listed",
                payload={
                    "count": 1,
                    "total": 1,
                    "skip": 0,
                    "limit": limit,
                    "items": [
                        {
                            "id": "job-running-1",
                            "job_type": "crawl",
                            "status": "running",
                            "started_at": "2026-05-11T09:05:00+00:00",
                            "finished_at": None,
                            "heartbeat_at": "2026-05-11T09:05:30+00:00",
                            "error": None,
                            "audit_events": [],
                        }
                    ],
                },
            )
        if status == "success":
            return ServiceResult(
                status="ok",
                message="jobs listed",
                payload={
                    "count": 2,
                    "total": 2,
                    "skip": 0,
                    "limit": limit,
                    "items": [
                        {
                            "id": "job-success-1",
                            "job_type": "crawl",
                            "status": "success",
                            "started_at": "2026-05-11T08:50:00+00:00",
                            "finished_at": "2026-05-11T08:53:00+00:00",
                            "heartbeat_at": None,
                            "error": None,
                            "audit_events": [],
                        },
                        {
                            "id": "job-success-2",
                            "job_type": "backtest",
                            "status": "success",
                            "started_at": "2026-05-11T08:40:00+00:00",
                            "finished_at": "2026-05-11T08:45:00+00:00",
                            "heartbeat_at": None,
                            "error": None,
                            "audit_events": [],
                        },
                    ],
                },
            )
        return ServiceResult(status="ok", message="jobs listed", payload={"count": 0, "total": 0, "skip": 0, "limit": limit, "items": []})


@dataclass
class _FakeDashboardService:
    async def build_report(self, *, config_path, mode="cli", output=None) -> ServiceResult:
        return ServiceResult(
            status="ok",
            message="dashboard report built",
            payload={
                "config_path": str(config_path),
                "report": {
                    "source_freshness": [
                        {"source": "articles", "entity_type": "article", "freshness_hours": 1.5, "is_stale": False},
                        {"source": "market_data", "entity_type": "market", "freshness_hours": 24.0, "is_stale": True},
                    ],
                    "alerts": [
                        {"level": "critical", "title": "stale market data", "message": "market data is stale", "timestamp": "2026-05-11T09:00:00+00:00"},
                    ],
                },
                "html_path": None,
                "critical_alerts": 1,
                "exit_code": 1,
            },
        )


@pytest.mark.asyncio
async def test_build_dashboard_summary_combines_health_jobs_freshness_and_alerts() -> None:
    """系统 Dashboard 汇总应聚合健康、任务、新鲜度和告警信息。"""
    from src.services.system_service import SystemService

    service = SystemService(
        health_service=_FakeHealthService(),
        job_service=_FakeJobService(),
        dashboard_service=_FakeDashboardService(),
    )

    result = await service.build_dashboard_summary()

    assert result.status == "partial"
    assert result.payload["health"]["database"]["status"] == "ok"
    assert result.payload["worker"]["heartbeat_at"] == "2026-05-11T09:05:30+00:00"
    assert result.payload["failed_jobs"][0]["id"] == "job-failed-1"
    assert result.payload["duration_summary"]["average_seconds"] == 240.0
    assert result.payload["freshness"]["sources"][1]["is_stale"] is True
    assert result.payload["alerts"]["critical"] == 1
    assert result.payload["traces"][0]["request_context"]["path"] == "/api/ui/v1/jobs"
    assert result.payload["traces"][0]["request_context"]["client_host"] == "127.0.0.1"
