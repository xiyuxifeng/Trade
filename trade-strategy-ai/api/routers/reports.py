"""报告查询接口：日报、考核报告的查询与下载。

P1-033: 实现报告查询接口
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.agents.manager_agent.agent import ManagerAgent
from src.common.utils import read_json
from src.schemas.contracts import DailyReport, EvaluationResult
from api.routers.run import get_manager_agent

router = APIRouter(prefix="/reports", tags=["reports"])


# ============================================================================
# 辅助函数
# ============================================================================

def _parse_date(date_str: str) -> date:
    """解析日期字符串。"""
    return date.fromisoformat(date_str)


def _find_report_files(output_dir: Path, prefix: str) -> list[Path]:
    """查找输出目录中匹配前缀的报告文件。"""
    if not output_dir.exists():
        return []
    return sorted(output_dir.glob(f"{prefix}_*.json"))


def _load_report(path: Path, model_cls: type) -> BaseModel:
    """加载报告 JSON 文件并验证模型。"""
    payload = read_json(path)
    return model_cls.model_validate(payload)


# ============================================================================
# 请求/响应模型
# ============================================================================

class ReportSummary(BaseModel):
    """报告摘要。"""
    as_of_date: date
    file_path: str
    file_size: int | None = None


class DailyReportListResponse(BaseModel):
    """日报列表响应。"""
    status: str = "success"
    count: int
    reports: list[ReportSummary]


class EvaluationListResponse(BaseModel):
    """考核报告列表响应。"""
    status: str = "success"
    count: int
    reports: list[ReportSummary]


class DailyReportResponse(BaseModel):
    """日报详情响应。"""
    status: str = "success"
    report: DailyReport


class EvaluationResponse(BaseModel):
    """考核报告详情响应。"""
    status: str = "success"
    result: EvaluationResult


class ErrorResponse(BaseModel):
    """错误响应。"""
    status: str = "error"
    error: str
    detail: str | None = None


# ============================================================================
# API 端点
# ============================================================================

@router.get(
    "/daily",
    response_model=DailyReportListResponse,
    responses={200: {"description": "日报列表"}},
)
async def list_daily_reports(
    mgr: ManagerAgent = Depends(get_manager_agent),
) -> DailyReportListResponse:
    """列出所有可用的日报。"""
    output_dir = mgr.output_dir
    report_files = _find_report_files(output_dir, "daily_report")

    reports = []
    for path in report_files:
        try:
            date_str = path.stem.replace("daily_report_", "")
            as_of = _parse_date(date_str)
            reports.append(
                ReportSummary(
                    as_of_date=as_of,
                    file_path=str(path),
                    file_size=path.stat().st_size if path.exists() else None,
                )
            )
        except ValueError:
            # 跳过日期解析失败的文件
            continue

    return DailyReportListResponse(
        status="success",
        count=len(reports),
        reports=reports,
    )


@router.get(
    "/daily/{date_str}",
    response_model=DailyReportResponse,
    responses={
        200: {"description": "日报详情"},
        404: {"description": "日报未找到"},
    },
)
async def get_daily_report(
    date_str: str,
    mgr: ManagerAgent = Depends(get_manager_agent),
) -> DailyReportResponse:
    """获取指定日期的日报详情。"""
    as_of_date = _parse_date(date_str)
    report_path = mgr.output_dir / f"daily_report_{as_of_date.isoformat()}.json"

    if not report_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"日报未找到: {report_path}",
        )

    try:
        report = _load_report(report_path, DailyReport)
        return DailyReportResponse(status="success", report=report)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"日报解析失败: {exc}",
        )


@router.get(
    "/daily/{date_str}/html",
    responses={
        200: {"description": "日报 HTML 文件", "content": {"text/html": {}}},
        404: {"description": "HTML 文件未找到"},
    },
)
async def download_daily_report_html(
    date_str: str,
    mgr: ManagerAgent = Depends(get_manager_agent),
) -> FileResponse:
    """下载指定日期的日报 HTML 文件。"""
    as_of_date = _parse_date(date_str)
    html_path = mgr.output_dir / f"daily_report_{as_of_date.isoformat()}.html"

    if not html_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"HTML 文件未找到: {html_path}",
        )

    return FileResponse(
        path=html_path,
        media_type="text/html",
        filename=f"daily_report_{as_of_date.isoformat()}.html",
    )


@router.get(
    "/evaluation",
    response_model=EvaluationListResponse,
    responses={200: {"description": "考核报告列表"}},
)
async def list_evaluation_reports(
    mgr: ManagerAgent = Depends(get_manager_agent),
) -> EvaluationListResponse:
    """列出所有可用的考核报告。"""
    output_dir = mgr.output_dir
    report_files = _find_report_files(output_dir, "evaluation")

    reports = []
    for path in report_files:
        try:
            date_str = path.stem.replace("evaluation_", "")
            as_of = _parse_date(date_str)
            reports.append(
                ReportSummary(
                    as_of_date=as_of,
                    file_path=str(path),
                    file_size=path.stat().st_size if path.exists() else None,
                )
            )
        except ValueError:
            # 跳过日期解析失败的文件
            continue

    return EvaluationListResponse(
        status="success",
        count=len(reports),
        reports=reports,
    )


@router.get(
    "/evaluation/{date_str}",
    response_model=EvaluationResponse,
    responses={
        200: {"description": "考核报告详情"},
        404: {"description": "考核报告未找到"},
    },
)
async def get_evaluation_report(
    date_str: str,
    mgr: ManagerAgent = Depends(get_manager_agent),
) -> EvaluationResponse:
    """获取指定日期的考核报告详情。"""
    as_of_date = _parse_date(date_str)
    report_path = mgr.output_dir / f"evaluation_{as_of_date.isoformat()}.json"

    if not report_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"考核报告未找到: {report_path}",
        )

    try:
        result = _load_report(report_path, EvaluationResult)
        return EvaluationResponse(status="success", result=result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"考核报告解析失败: {exc}",
        )


@router.get(
    "/evaluation/{date_str}/html",
    responses={
        200: {"description": "考核报告 HTML 文件", "content": {"text/html": {}}},
        404: {"description": "HTML 文件未找到"},
    },
)
async def download_evaluation_html(
    date_str: str,
    mgr: ManagerAgent = Depends(get_manager_agent),
) -> FileResponse:
    """下载指定日期的考核报告 HTML 文件。"""
    as_of_date = _parse_date(date_str)
    html_path = mgr.output_dir / f"evaluation_{as_of_date.isoformat()}.html"

    if not html_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"HTML 文件未找到: {html_path}",
        )

    return FileResponse(
        path=html_path,
        media_type="text/html",
        filename=f"evaluation_{as_of_date.isoformat()}.html",
    )
