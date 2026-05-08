from __future__ import annotations

from datetime import date
from typing import Any

from src.services.base import BaseService, ServiceResult


class RunService(BaseService):
    """盘前/盘后流程的共享服务。"""

    service_name = "run"

    def __init__(self, manager: Any) -> None:
        """注入 ManagerAgent 或兼容对象。"""
        self._manager = manager

    async def run_pre_market(
        self,
        *,
        as_of_date: date,
        force: bool = False,
        export_html: bool = False,
    ) -> ServiceResult:
        """触发盘前日报，并可导出 HTML。"""
        report = await self._manager.run_pre_market(as_of_date=as_of_date, force=force)
        html_path = None
        if export_html:
            html_path = str(self._manager.export_daily_report_html(report=report))

        return ServiceResult(
            status="ok",
            message="pre market completed",
            payload={
                "as_of_date": as_of_date.isoformat(),
                "ideas_count": len(getattr(report, "ideas", [])),
                "report": report.model_dump(),
                "html_path": html_path,
            },
        )

    async def run_after_close(
        self,
        *,
        as_of_date: date,
        force: bool = False,
        export_html: bool = False,
    ) -> ServiceResult:
        """触发盘后考核，并可导出 HTML。"""
        result = await self._manager.run_after_close(as_of_date=as_of_date, force=force)
        html_path = None
        if export_html:
            html_path = str(self._manager.export_evaluation_html(result=result))

        return ServiceResult(
            status="ok",
            message="after close completed",
            payload={
                "as_of_date": as_of_date.isoformat(),
                "evaluations_count": len(getattr(result, "evaluations", [])),
                "result": result.model_dump(),
                "html_path": html_path,
            },
        )

