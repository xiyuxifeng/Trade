from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.dependencies import verify_api_key
from api.schemas.common import PaginatedResponse, paginated_response
from api.schemas.report import (
    DailyReportResponse,
    DailyReportSummary,
    EvaluationResultResponse,
    EvaluationResultSummary,
)
from src.common.utils import read_json
from src.schemas.contracts import DailyReport, EvaluationResult
from src.services.config_profile_service import ConfigProfileService

router = APIRouter(prefix="/reports", tags=["reports"])


async def _resolve_runtime_output_dir(profile_id: str | None = None) -> tuple[Path, str | None, str | None]:
    """解析 Web 报告输出目录。

    优先从 Profile runtime 解析，找不到则回退到默认 Profile。
    """
    service = ConfigProfileService()
    resolved_profile_id = service.resolve_runtime_profile_id(profile_id)
    runtime = await service.load_profile_runtime_config(resolved_profile_id)
    return runtime.base_dir / runtime.config.runtime.output_dir, runtime.profile_id, runtime.profile_snapshot_id


def _daily_report_path(output_dir: Path, as_of_date: date) -> Path:
    return output_dir / f"daily_report_{as_of_date.isoformat()}.json"


def _evaluation_path(output_dir: Path, as_of_date: date) -> Path:
    return output_dir / f"evaluation_{as_of_date.isoformat()}.json"


def _daily_report_html_path(output_dir: Path, as_of_date: date) -> Path:
    return output_dir / f"daily_report_{as_of_date.isoformat()}.html"


def _evaluation_html_path(output_dir: Path, as_of_date: date) -> Path:
    return output_dir / f"evaluation_{as_of_date.isoformat()}.html"


@router.get("/daily/{as_of_date}", response_model=DailyReportResponse)
async def get_daily_report(
    as_of_date: date,
    profile_id: str | None = Query(default=None),
    _: str = Depends(verify_api_key),
):
    """Get daily report by date."""
    output_dir, _, _ = await _resolve_runtime_output_dir(profile_id)
    path = _daily_report_path(output_dir, as_of_date)

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"未找到 {as_of_date} 的盘前日报")

    data = read_json(path)
    report = DailyReport.model_validate(data)
    return DailyReportResponse.model_validate(report)


@router.get("/daily", response_model=PaginatedResponse[DailyReportSummary])
async def list_daily_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    start_date: date | None = None,
    end_date: date | None = None,
    profile_id: str | None = Query(default=None),
    _: str = Depends(verify_api_key),
):
    """List daily reports with optional date range filter."""
    output_dir, _, _ = await _resolve_runtime_output_dir(profile_id)

    reports: list[DailyReportSummary] = []
    if output_dir.exists():
        for f in sorted(output_dir.iterdir(), reverse=True):
            if f.name.startswith("daily_report_") and f.suffix == ".json":
                try:
                    as_of_str = f.stem.replace("daily_report_", "")
                    as_of = date.fromisoformat(as_of_str)
                except ValueError:
                    continue

                if start_date and as_of < start_date:
                    continue
                if end_date and as_of > end_date:
                    continue

                data = read_json(f)
                report = DailyReport.model_validate(data)
                reports.append(
                    DailyReportSummary(
                        report_id=report.report_id,
                        as_of_date=report.as_of_date,
                        generated_at=report.generated_at,
                        ideas_count=len(report.ideas),
                        highlights_count=len(report.highlights),
                    )
                )

    total = len(reports)
    start = (page - 1) * page_size
    end = start + page_size
    items = reports[start:end]

    return paginated_response(items=items, total=total, page=page, page_size=page_size)


@router.get("/daily/{as_of_date}/export")
async def export_daily_report(
    as_of_date: date,
    format: str = Query(default="json", pattern="^(json|html)$"),
    profile_id: str | None = Query(default=None),
    _: str = Depends(verify_api_key),
):
    """Export daily report as JSON or HTML."""
    output_dir, _, _ = await _resolve_runtime_output_dir(profile_id)

    if format == "html":
        path = _daily_report_html_path(output_dir, as_of_date)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"未找到 {as_of_date} 的盘前日报 HTML 文件")
        content = path.read_bytes()
        media_type = "text/html"
        filename = f"daily_report_{as_of_date.isoformat()}.html"
    else:
        path = _daily_report_path(output_dir, as_of_date)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"未找到 {as_of_date} 的盘前日报")
        content = path.read_bytes()
        media_type = "application/json"
        filename = f"daily_report_{as_of_date.isoformat()}.json"

    buffer = BytesIO(content)
    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/evaluation/{as_of_date}", response_model=EvaluationResultResponse)
async def get_evaluation_result(
    as_of_date: date,
    profile_id: str | None = Query(default=None),
    _: str = Depends(verify_api_key),
):
    """Get evaluation result by date."""
    output_dir, _, _ = await _resolve_runtime_output_dir(profile_id)
    path = _evaluation_path(output_dir, as_of_date)

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"未找到 {as_of_date} 的盘后考核结果")

    data = read_json(path)
    result = EvaluationResult.model_validate(data)
    return EvaluationResultResponse.model_validate(result)


@router.get("/evaluation", response_model=PaginatedResponse[EvaluationResultSummary])
async def list_evaluation_results(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    start_date: date | None = None,
    end_date: date | None = None,
    profile_id: str | None = Query(default=None),
    _: str = Depends(verify_api_key),
):
    """List evaluation results with optional date range filter."""
    output_dir, _, _ = await _resolve_runtime_output_dir(profile_id)

    results: list[EvaluationResultSummary] = []
    if output_dir.exists():
        for f in sorted(output_dir.iterdir(), reverse=True):
            if f.name.startswith("evaluation_") and f.suffix == ".json":
                try:
                    as_of_str = f.stem.replace("evaluation_", "")
                    as_of = date.fromisoformat(as_of_str)
                except ValueError:
                    continue

                if start_date and as_of < start_date:
                    continue
                if end_date and as_of > end_date:
                    continue

                data = read_json(f)
                result = EvaluationResult.model_validate(data)
                results.append(
                    EvaluationResultSummary(
                        result_id=result.result_id,
                        as_of_date=result.as_of_date,
                        generated_at=result.generated_at,
                        evaluations_count=len(result.evaluations),
                        summary_count=len(result.summary),
                    )
                )

    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size
    items = results[start:end]

    return paginated_response(items=items, total=total, page=page, page_size=page_size)


@router.get("/evaluation/{as_of_date}/export")
async def export_evaluation_result(
    as_of_date: date,
    format: str = Query(default="json", pattern="^(json|html)$"),
    profile_id: str | None = Query(default=None),
    _: str = Depends(verify_api_key),
):
    """Export evaluation result as JSON or HTML."""
    output_dir, _, _ = await _resolve_runtime_output_dir(profile_id)

    if format == "html":
        path = _evaluation_html_path(output_dir, as_of_date)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"未找到 {as_of_date} 的盘后考核 HTML 文件")
        content = path.read_bytes()
        media_type = "text/html"
        filename = f"evaluation_{as_of_date.isoformat()}.html"
    else:
        path = _evaluation_path(output_dir, as_of_date)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"未找到 {as_of_date} 的盘后考核结果")
        content = path.read_bytes()
        media_type = "application/json"
        filename = f"evaluation_{as_of_date.isoformat()}.json"

    buffer = BytesIO(content)
    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _persona_route_path(output_dir: Path, as_of_date: date) -> Path:
    return output_dir / f"persona_route_{as_of_date.isoformat()}.json"


@router.get("/persona-route/{as_of_date}")
async def get_persona_route(
    as_of_date: date,
    profile_id: str | None = Query(default=None),
    _: str = Depends(verify_api_key),
):
    """Get persona route decision by date."""
    output_dir, _, _ = await _resolve_runtime_output_dir(profile_id)
    path = _persona_route_path(output_dir, as_of_date)

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"未找到 {as_of_date} 的画像路由结果")

    data = read_json(path)
    return data


@router.get("/persona-route")
async def list_persona_routes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    start_date: date | None = None,
    end_date: date | None = None,
    profile_id: str | None = Query(default=None),
    _: str = Depends(verify_api_key),
):
    """List persona route decisions with optional date range filter."""
    output_dir, _, _ = await _resolve_runtime_output_dir(profile_id)

    routes: list[dict] = []
    if output_dir.exists():
        for f in sorted(output_dir.iterdir(), reverse=True):
            if f.name.startswith("persona_route_") and f.suffix == ".json":
                try:
                    as_of_str = f.stem.replace("persona_route_", "")
                    as_of = date.fromisoformat(as_of_str)
                except ValueError:
                    continue

                if start_date and as_of < start_date:
                    continue
                if end_date and as_of > end_date:
                    continue

                data = read_json(f)
                routes.append({
                    "as_of_date": as_of.isoformat(),
                    "clusters_path": data.get("clusters_path"),
                    "decisions_count": len(data.get("decisions") or []),
                })

    total = len(routes)
    start = (page - 1) * page_size
    end = start + page_size
    items = routes[start:end]

    return paginated_response(items=items, total=total, page=page, page_size=page_size)


@router.get("/persona-route/{as_of_date}/export")
async def export_persona_route(
    as_of_date: date,
    profile_id: str | None = Query(default=None),
    _: str = Depends(verify_api_key),
):
    """Export persona route decision as JSON."""
    output_dir, _, _ = await _resolve_runtime_output_dir(profile_id)
    path = _persona_route_path(output_dir, as_of_date)

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"未找到 {as_of_date} 的画像路由结果")

    content = path.read_bytes()
    buffer = BytesIO(content)
    filename = f"persona_route_{as_of_date.isoformat()}.json"

    return StreamingResponse(
        buffer,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
