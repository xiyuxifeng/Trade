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
from src.common.paths import resolve_project_path

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


def _get_backtest_results_dirs() -> list[Path]:
    """获取回测结果存储目录列表。"""
    return [
        resolve_project_path("data/backtest/results"),
        resolve_project_path("data/processed/backtest"),
    ]


def _extract_meta(data: dict) -> tuple[str | None, str | None, str | None]:
    trader_id = data.get("trader_id") or data.get("request_trader_id")
    date_from = data.get("date_from") or data.get("request_date_from")
    date_to = data.get("date_to") or data.get("request_date_to")
    return trader_id, date_from, date_to


def _iter_result_files() -> list[Path]:
    files: list[Path] = []
    for results_dir in _get_backtest_results_dirs():
        if results_dir.exists():
            files.extend(results_dir.glob("*.json"))
    return sorted(files, reverse=True)


def _find_result_file(result_id: str) -> Path | None:
    for results_dir in _get_backtest_results_dirs():
        candidate = results_dir / f"{result_id}.json"
        if candidate.exists():
            return candidate
    return None


@router.get("/", response_model=PaginatedResponse)
async def list_backtest_results(
    trader_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None, description="开始日期 YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="结束日期 YYYY-MM-DD"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse:
    """列出回测结果（基于文件，分页）。"""
    all_files = _iter_result_files()
    if not all_files:
        return PaginatedResponse(count=0, total=0, skip=skip, limit=limit, items=[])

    items = []
    for f in all_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            meta_trader_id, meta_date_from, meta_date_to = _extract_meta(data)
            if trader_id and meta_trader_id != trader_id:
                continue
            if date_from and (meta_date_from or "") < date_from:
                continue
            if date_to and (meta_date_to or "") > date_to:
                continue

            items.append({
                "result_id": f.stem,
                "trader_id": meta_trader_id,
                "date_from": meta_date_from,
                "date_to": meta_date_to,
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
    result_file = _find_result_file(result_id)
    if result_file is None:
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
    report_file = None
    for results_dir in _get_backtest_results_dirs():
        candidate = results_dir / f"{result_id}_report.md"
        if candidate.exists():
            report_file = candidate
            break
    if report_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="回测报告文件未找到")

    return FileResponse(
        path=report_file,
        media_type="text/markdown",
        filename=f"backtest_report_{result_id}.md",
    )


@router.get("/{result_id}/validate_rules")
async def download_validate_rules(result_id: str) -> FileResponse:
    """下载规则验真报告（Markdown）。"""
    validate_file = None
    for results_dir in _get_backtest_results_dirs():
        candidate = results_dir / f"{result_id}_validate_rules.md"
        if candidate.exists():
            validate_file = candidate
            break
    if validate_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则验真报告未找到")

    return FileResponse(
        path=validate_file,
        media_type="text/markdown",
        filename=f"rule_validation_{result_id}.md",
    )
