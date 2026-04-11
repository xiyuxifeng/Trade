"""报告查询接口：日报、考核报告的查询与下载。

P1-033: 实现报告查询接口
"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.agents.manager_agent.agent import ManagerAgent
from src.common.logger import get_logger
from src.common.utils import read_json
from src.schemas.contracts import DailyReport, EvaluationResult
from api.routers.run import get_manager_agent

router = APIRouter(prefix="/reports", tags=["reports"])
logger = get_logger("api.reports")


# ============================================================================
# 辅助函数
# ============================================================================

def _parse_date(date_str: str) -> date:
    """解析日期字符串，支持 YYYY-MM-DD 格式。

    Raises:
        HTTPException: 日期格式无效或超出合理范围时
    """
    try:
        parsed = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的日期格式: {date_str}，请使用 YYYY-MM-DD 格式",
        )
    # 合理范围校验：2020-01-01 至今天
    if parsed.year < 2020 or parsed > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"日期超出合理范围: {date_str}",
        )
    return parsed


async def _find_report_files(output_dir: Path, prefix: str) -> list[Path]:
    """查找输出目录中匹配前缀的报告文件（异步）。"""
    def _sync_find():
        if not output_dir.exists():
            return []
        return sorted(output_dir.glob(f"{prefix}_*.json"))
    return await asyncio.to_thread(_sync_find)


async def _load_report(path: Path, model_cls: type) -> BaseModel:
    """加载报告 JSON 文件并验证模型（异步）。"""
    def _sync_load():
        payload = read_json(path)
        return model_cls.model_validate(payload)
    return await asyncio.to_thread(_sync_load)


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
    total: int  # 总数
    skip: int  # 跳过数量
    limit: int  # 限制数量
    reports: list[ReportSummary]


class EvaluationListResponse(BaseModel):
    """考核报告列表响应。"""
    status: str = "success"
    count: int
    total: int
    skip: int
    limit: int
    reports: list[ReportSummary]


class DailyReportResponse(BaseModel):
    """日报详情响应。"""
    status: str = "success"
    report: DailyReport


class EvaluationResponse(BaseModel):
    """考核报告详情响应。"""
    status: str = "success"
    result: EvaluationResult


# ============================================================================
# API 端点
# ============================================================================

@router.get(
    "/daily",
    response_model=DailyReportListResponse,
    responses={200: {"description": "日报列表"}},
)
async def list_daily_reports(
    skip: int = Query(default=0, ge=0, description="跳过的数量"),
    limit: int = Query(default=50, ge=1, le=100, description="返回数量限制"),
    mgr: ManagerAgent = Depends(get_manager_agent),
) -> DailyReportListResponse:
    """列出所有可用的日报（分页）。"""
    output_dir = mgr.output_dir
    all_files = await _find_report_files(output_dir, "daily_report")

    total = len(all_files)
    # 分页
    paginated_files = all_files[skip: skip + limit]

    reports = []
    for path in paginated_files:
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
        except HTTPException:
            # 跳过日期解析失败的条目
            continue

    return DailyReportListResponse(
        status="success",
        count=len(reports),
        total=total,
        skip=skip,
        limit=limit,
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
        report = await _load_report(report_path, DailyReport)
        return DailyReportResponse(status="success", report=report)
    except Exception as exc:
        logger.error(f"Failed to parse daily report {report_path}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="日报解析失败",
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
    skip: int = Query(default=0, ge=0, description="跳过的数量"),
    limit: int = Query(default=50, ge=1, le=100, description="返回数量限制"),
    mgr: ManagerAgent = Depends(get_manager_agent),
) -> EvaluationListResponse:
    """列出所有可用的考核报告（分页）。"""
    output_dir = mgr.output_dir
    all_files = await _find_report_files(output_dir, "evaluation")

    total = len(all_files)
    paginated_files = all_files[skip: skip + limit]

    reports = []
    for path in paginated_files:
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
        except HTTPException:
            # 跳过日期解析失败的条目
            continue

    return EvaluationListResponse(
        status="success",
        count=len(reports),
        total=total,
        skip=skip,
        limit=limit,
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
        result = await _load_report(report_path, EvaluationResult)
        return EvaluationResponse(status="success", result=result)
    except Exception as exc:
        logger.error(f"Failed to parse evaluation report {report_path}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="考核报告解析失败",
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
