"""回测结果查询接口。

NTL-S7-005
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.dependencies import verify_api_key
from src.common.logger import get_logger
from src.db.repositories import BacktestResultRunRepository
from src.db.session import session_scope
from src.services.job_service import JobService

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


def get_job_service() -> JobService:
    """构建 Job 查询服务。"""
    return JobService()


def _extract_meta(data: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    payload = data.get("payload")
    if isinstance(payload, dict):
        request = payload.get("request")
        if isinstance(request, dict):
            return (
                request.get("trader_id"),
                request.get("date_from"),
                request.get("date_to"),
            )

    return (
        data.get("trader_id") or data.get("request_trader_id"),
        data.get("date_from") or data.get("request_date_from"),
        data.get("date_to") or data.get("request_date_to"),
    )


def _extract_summary(data: dict[str, Any]) -> dict[str, Any]:
    payload = data.get("payload")
    if isinstance(payload, dict):
        summary = payload.get("summary")
        if isinstance(summary, dict):
            return summary
        result = payload.get("result")
        if isinstance(result, dict):
            nested_summary = result.get("summary")
            if isinstance(nested_summary, dict):
                return nested_summary
    summary = data.get("summary")
    if isinstance(summary, dict):
        return summary
    return {}


def _extract_result_body(data: dict[str, Any]) -> dict[str, Any]:
    payload = data.get("payload")
    if isinstance(payload, dict):
        result = payload.get("result")
        if isinstance(result, dict):
            return result
    return data


def _parse_optional_date(value: str | None) -> date | None:
    """将可选日期参数统一解析。"""
    if value in {None, ""}:
        return None
    return date.fromisoformat(value)


def _serialize_backtest_result_run(run: Any) -> dict[str, Any]:
    """把 backtest_result_runs 记录转成 API 输出。"""
    return {
        "result_id": run.result_run_id,
        "trader_id": run.request_trader_id,
        "date_from": run.request_date_from.isoformat() if run.request_date_from else None,
        "date_to": run.request_date_to.isoformat() if run.request_date_to else None,
        "benchmark_symbol": run.benchmark_symbol,
        "regime_version": run.regime_version,
        "source_feature_version": run.source_feature_version,
        "strategy_version_id": run.strategy_version_id,
        "summary": run.summary_json or {},
        "status": run.status,
        "quality_status": run.quality_status,
        "_mtime": run.updated_at or run.created_at,
    }


async def _load_db_backtest_result_runs(
    *,
    trader_id: str | None,
    date_from: str | None,
    date_to: str | None,
    skip: int,
    limit: int,
) -> tuple[list[dict[str, Any]], int] | None:
    """优先从 backtest_result_runs 加载摘要。"""
    try:
        async with session_scope() as session:
            repo = BacktestResultRunRepository()
            parsed_date_from = _parse_optional_date(date_from)
            parsed_date_to = _parse_optional_date(date_to)
            total = await repo.count_runs(
                session,
                trader_id=trader_id,
                date_from=parsed_date_from,
                date_to=parsed_date_to,
            )
            if total == 0:
                return None
            runs = await repo.list_runs(
                session,
                trader_id=trader_id,
                date_from=parsed_date_from,
                date_to=parsed_date_to,
                offset=skip,
                limit=limit,
            )
    except Exception as exc:  # noqa: BLE001
        logger.debug("backtest_result_runs query failed, fallback to jobs: %s", exc)
        return None

    items = [_serialize_backtest_result_run(run) for run in runs]
    if total == 0:
        return None
    return items, total


async def _load_legacy_backtest_results(*, job_service: JobService, job_type: str) -> list[dict[str, Any]]:
    """从 jobs 表加载回测结果摘要。"""
    summaries: list[dict[str, Any]] = []
    skip = 0
    page_size = 500
    total: int | None = None
    while True:
        result = await job_service.list_jobs(job_type=job_type, status="success", skip=skip, limit=page_size)
        items = result.payload.get("items", [])
        if total is None:
            total = int(result.payload.get("total") or len(items) or 0)
        for item in items:
            if not isinstance(item, dict):
                continue
            body = item.get("result")
            if not isinstance(body, dict):
                continue
            meta_trader_id, meta_date_from, meta_date_to = _extract_meta(body)
            if not (meta_trader_id or meta_date_from or meta_date_to):
                continue
            payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
            request = payload.get("request") if isinstance(payload, dict) else {}
            summaries.append(
                {
                    "result_id": item.get("id"),
                    "trader_id": meta_trader_id,
                    "date_from": meta_date_from,
                    "date_to": meta_date_to,
                    "benchmark_symbol": request.get("benchmark_symbol") if isinstance(request, dict) else body.get("benchmark_symbol"),
                    "regime_version": request.get("market_regime_version") if isinstance(request, dict) else body.get("regime_version"),
                    "source_feature_version": request.get("source_feature_version") if isinstance(request, dict) else body.get("source_feature_version"),
                    "summary": _extract_summary(body),
                    "_mtime": item.get("finished_at") or item.get("updated_at") or item.get("created_at"),
                }
            )
        skip += len(items)
        if not items or (total is not None and skip >= total):
            break
    return summaries


@router.get("/", response_model=PaginatedResponse)
async def list_backtest_results(
    _key: str = Depends(verify_api_key),
    trader_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None, description="开始日期 YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="结束日期 YYYY-MM-DD"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse:
    """列出回测结果。"""
    db_result = await _load_db_backtest_result_runs(
        trader_id=trader_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    if db_result is not None:
        items, total_count = db_result
        return PaginatedResponse(
            count=len(items),
            total=total_count,
            skip=skip,
            limit=limit,
            items=[{k: v for k, v in item.items() if k != "_mtime"} for item in items],
        )

    job_service = get_job_service()
    items = []
    seen: set[str] = set()
    for job_type in ("backtest-run", "rule-pool-backtest"):
        for item in await _load_legacy_backtest_results(job_service=job_service, job_type=job_type):
            result_id = str(item.get("result_id") or "")
            if not result_id or result_id in seen:
                continue
            seen.add(result_id)
            if trader_id and item.get("trader_id") != trader_id:
                continue
            if date_from and (item.get("date_from") or "") < date_from:
                continue
            if date_to and (item.get("date_to") or "") > date_to:
                continue
            item.pop("_mtime", None)
            items.append(item)

    items.sort(key=lambda item: item.get("date_to") or item.get("date_from") or "", reverse=True)
    total = len(items)
    paginated = items[skip : skip + limit]

    return PaginatedResponse(
        count=len(paginated),
        total=total,
        skip=skip,
        limit=limit,
        items=paginated,
    )


@router.get("/{result_id}", response_model=BacktestResultDetail)
async def get_backtest_result(result_id: str, _key: str = Depends(verify_api_key)) -> BacktestResultDetail:
    """获取回测结果详情。"""
    job_service = get_job_service()
    job_result = await job_service.get_job(result_id)
    if job_result.status != "ok" or not isinstance(job_result.payload.get("job"), dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="回测结果未找到")

    job = job_result.payload["job"]
    result = job.get("result")
    if not isinstance(result, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="回测结果未找到")
    return BacktestResultDetail(item=result)


@router.get("/{result_id}/report")
async def download_backtest_report(result_id: str, _key: str = Depends(verify_api_key)) -> FileResponse:
    """下载回测报告（Markdown）。"""
    job_result = await get_job_service().get_job(result_id)
    if job_result.status != "ok":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="回测报告文件未找到")

    job_dir = Path(job_result.payload.get("job_dir") or "")
    report_file = job_dir / "backtest_report.md"
    if not report_file.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="回测报告文件未找到")

    return FileResponse(
        path=report_file,
        media_type="text/markdown",
        filename=f"backtest_report_{result_id}.md",
    )


@router.get("/{result_id}/validate_rules")
async def download_validate_rules(result_id: str, _key: str = Depends(verify_api_key)) -> FileResponse:
    """下载规则验真报告（Markdown）。"""
    job_result = await get_job_service().get_job(result_id)
    if job_result.status != "ok":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则验真报告未找到")

    job_dir = Path(job_result.payload.get("job_dir") or "")
    validate_file = job_dir / "backtest_validation_report.md"
    if not validate_file.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则验真报告未找到")

    return FileResponse(
        path=validate_file,
        media_type="text/markdown",
        filename=f"rule_validation_{result_id}.md",
    )
