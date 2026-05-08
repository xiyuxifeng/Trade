from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path


class _FakeReport:
    def __init__(self, as_of_date: date) -> None:
        self.as_of_date = as_of_date

    def model_dump(self) -> dict[str, object]:
        return {"kind": "daily_report", "as_of_date": self.as_of_date.isoformat()}


class _FakeResult:
    def __init__(self, as_of_date: date) -> None:
        self.as_of_date = as_of_date

    def model_dump(self) -> dict[str, object]:
        return {"kind": "evaluation_result", "as_of_date": self.as_of_date.isoformat()}


class _FakeManager:
    def __init__(self) -> None:
        self.pre_market_calls: list[tuple[date, bool]] = []
        self.after_close_calls: list[tuple[date, bool]] = []
        self.exported_daily_reports: list[object] = []
        self.exported_evaluations: list[object] = []

    async def run_pre_market(self, *, as_of_date: date, force: bool = False) -> _FakeReport:
        self.pre_market_calls.append((as_of_date, force))
        return _FakeReport(as_of_date)

    async def run_after_close(self, *, as_of_date: date, force: bool = False) -> _FakeResult:
        self.after_close_calls.append((as_of_date, force))
        return _FakeResult(as_of_date)

    def export_daily_report_html(self, *, report) -> Path:
        self.exported_daily_reports.append(report)
        return Path("/tmp/daily_report.html")

    def export_evaluation_html(self, *, result) -> Path:
        self.exported_evaluations.append(result)
        return Path("/tmp/evaluation.html")


def test_run_service_triggers_pre_market_and_optional_html_export() -> None:
    """RunService 应调用盘前流程并可导出 HTML。"""
    from src.services.run_service import RunService

    manager = _FakeManager()
    service = RunService(manager)

    result = asyncio.run(
        service.run_pre_market(as_of_date=date(2026, 5, 8), force=True, export_html=True)
    )

    assert result.status == "ok"
    assert result.payload["as_of_date"] == "2026-05-08"
    assert result.payload["report"]["kind"] == "daily_report"
    assert result.payload["html_path"] == "/tmp/daily_report.html"
    assert manager.pre_market_calls == [(date(2026, 5, 8), True)]
    assert len(manager.exported_daily_reports) == 1


def test_run_service_triggers_after_close_and_optional_html_export() -> None:
    """RunService 应调用盘后流程并可导出 HTML。"""
    from src.services.run_service import RunService

    manager = _FakeManager()
    service = RunService(manager)

    result = asyncio.run(
        service.run_after_close(as_of_date=date(2026, 5, 8), force=False, export_html=True)
    )

    assert result.status == "ok"
    assert result.payload["as_of_date"] == "2026-05-08"
    assert result.payload["result"]["kind"] == "evaluation_result"
    assert result.payload["html_path"] == "/tmp/evaluation.html"
    assert manager.after_close_calls == [(date(2026, 5, 8), False)]
    assert len(manager.exported_evaluations) == 1
