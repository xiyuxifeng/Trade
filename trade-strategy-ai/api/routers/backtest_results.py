"""回测结果查询接口。

NTL-S7-005
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.common.logger import get_logger

router = APIRouter(prefix="/backtest_results", tags=["backtest_results"])
logger = get_logger(__name__)


class PaginatedResponse(BaseModel):
    status: str = "success"
    count: int
    total: int
    skip: int
    limit: int
    items: list[dict]


class BacktestResultDetail(BaseModel):
    status: str = "success"
    item: dict


def _get_backtest_results_dir() -> Path:
    """获取回测结果存储目录。"""
    return Path("data/backtest/results")


@router.get("/", response_model=PaginatedResponse)
async def list_backtest_results(
    trader_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None, description="开始日期 YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="结束日期 YYYY-MM-DD"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse:
    """列出回测结果（基于文件，分页）。"""
    results_dir = _get_backtest_results_dir()

    if not results_dir.exists():
        return PaginatedResponse(count=0, total=0, skip=skip, limit=limit, items=[])

    all_files = sorted(results_dir.glob("*.json"), reverse=True)

    items = []
    for f in all_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if trader_id and data.get("trader_id") != trader_id:
                continue
            date_str = data.get("date_from", "")
            if date_from and date_str < date_from:
                continue
            if date_to and date_str > date_to:
                continue

            items.append({
                "result_id": f.stem,
                "trader_id": data.get("trader_id"),
                "date_from": data.get("date_from"),
                "date_to": data.get("date_to"),
                "summary": data.get("summary", {}),
            })
        except Exception:
            continue

    total = len(items)
    paginated = items[skip: skip + limit]

    return PaginatedResponse(
        count=len(paginated),
        total=total,
        skip=skip,
        limit=limit,
        items=paginated,
    )


@router.get("/{result_id}", response_model=BacktestResultDetail)
async def get_backtest_result(result_id: str) -> BacktestResultDetail:
    """获取回测结果详情。"""
    results_dir = _get_backtest_results_dir()
    result_file = results_dir / f"{result_id}.json"

    if not result_file.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="回测结果未找到")

    try:
        data = json.loads(result_file.read_text(encoding="utf-8"))
        return BacktestResultDetail(item=data)
    except Exception as exc:
        logger.error(f"Failed to parse backtest result {result_id}: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="回测结果解析失败")


@router.get("/{result_id}/report")
async def download_backtest_report(result_id: str) -> FileResponse:
    """下载回测报告（Markdown）。"""
    results_dir = _get_backtest_results_dir()
    report_file = results_dir / f"{result_id}_report.md"

    if not report_file.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="回测报告文件未找到")

    return FileResponse(
        path=report_file,
        media_type="text/markdown",
        filename=f"backtest_report_{result_id}.md",
    )


@router.get("/{result_id}/validate_rules")
async def download_validate_rules(result_id: str) -> FileResponse:
    """下载规则验真报告（Markdown）。"""
    results_dir = _get_backtest_results_dir()
    validate_file = results_dir / f"{result_id}_validate_rules.md"

    if not validate_file.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则验真报告未找到")

    return FileResponse(
        path=validate_file,
        media_type="text/markdown",
        filename=f"rule_validation_{result_id}.md",
    )