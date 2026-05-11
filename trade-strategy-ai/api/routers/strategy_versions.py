"""策略版本查询接口。

NTL-S7-005
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.dependencies import verify_api_key
from src.common.logger import get_logger

router = APIRouter(prefix="/strategy_versions", tags=["strategy_versions"])
logger = get_logger(__name__)


class PaginatedResponse(BaseModel):
    status: str = "success"
    count: int
    total: int
    skip: int
    limit: int
    items: list[dict]


class StrategyVersionDetail(BaseModel):
    status: str = "success"
    item: dict


def _parse_date(date_str: str | None) -> date | None:
    if date_str is None:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的日期格式: {date_str}，请使用 YYYY-MM-DD 格式",
        )


@router.get("/", response_model=PaginatedResponse)
async def list_strategy_versions(
    _key: str = Depends(verify_api_key),
    trader_id: str | None = Query(default=None, description="交易员 ID"),
    status_filter: str | None = Query(default=None, alias="status", description="版本状态"),
    date_from: str | None = Query(default=None, description="开始日期 YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="结束日期 YYYY-MM-DD"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse:
    """列出策略版本（分页）。"""
    from sqlalchemy import select, func
    from src.models.trader_strategy_version import TraderStrategyVersion
    from src.db.session import session_scope

    async with session_scope() as session:
        conditions = []
        if trader_id:
            conditions.append(TraderStrategyVersion.trader_id == trader_id)
        if status_filter:
            conditions.append(TraderStrategyVersion.status == status_filter)
        if date_from:
            conditions.append(TraderStrategyVersion.strategy_date >= _parse_date(date_from))
        if date_to:
            conditions.append(TraderStrategyVersion.strategy_date <= _parse_date(date_to))

        count_stmt = select(func.count()).select_from(TraderStrategyVersion)
        for c in conditions:
            count_stmt = count_stmt.where(c)
        result = await session.execute(count_stmt)
        total = result.scalar() or 0

        stmt = select(TraderStrategyVersion).where(*conditions).order_by(
            TraderStrategyVersion.strategy_date.desc(), TraderStrategyVersion.version_name
        ).offset(skip).limit(limit)
        result = await session.execute(stmt)
        rows = result.scalars().all()

        items = []
        for row in rows:
            items.append({
                "version_id": row.version_name,
                "trader_id": row.trader_id,
                "strategy_date": str(row.strategy_date),
                "status": row.status,
                "version_type": getattr(row, "version_type", "manual"),
                "released_at": row.released_at.isoformat() if row.released_at else None,
            })

        return PaginatedResponse(
            count=len(items),
            total=total,
            skip=skip,
            limit=limit,
            items=items,
        )


@router.get("/{version_id}", response_model=StrategyVersionDetail)
async def get_strategy_version(version_id: str, _key: str = Depends(verify_api_key)) -> StrategyVersionDetail:
    """获取策略版本详情（包含 rules_snapshot）。"""
    from sqlalchemy import select
    from src.models.trader_strategy_version import TraderStrategyVersion
    from src.db.session import session_scope

    async with session_scope() as session:
        stmt = select(TraderStrategyVersion).where(
            TraderStrategyVersion.version_name == version_id,
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="策略版本未找到")

        return StrategyVersionDetail(item={
            "version_id": row.version_name,
            "trader_id": row.trader_id,
            "strategy_date": str(row.strategy_date),
            "status": row.status,
            "version_type": getattr(row, "version_type", "manual"),
            "released_at": row.released_at.isoformat() if row.released_at else None,
            "rules_snapshot": row.strategy_payload.get("rules_snapshot", []),
            "recommendations": row.strategy_payload.get("recommendations", []),
            "notes": row.notes,
        })


@router.get("/{version_id}/download")
async def download_strategy_version(version_id: str, _key: str = Depends(verify_api_key)) -> FileResponse:
    """下载策略版本 JSON 文件。"""
    from sqlalchemy import select
    from src.models.trader_strategy_version import TraderStrategyVersion
    from src.db.session import session_scope

    async with session_scope() as session:
        stmt = select(TraderStrategyVersion).where(
            TraderStrategyVersion.version_name == version_id,
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="策略版本未找到")

        payload = {
            "version_id": row.version_name,
            "trader_id": row.trader_id,
            "strategy_date": str(row.strategy_date),
            "status": row.status,
            "version_type": getattr(row, "version_type", "manual"),
            "released_at": row.released_at.isoformat() if row.released_at else None,
            "rules_snapshot": row.strategy_payload.get("rules_snapshot", []),
            "recommendations": row.strategy_payload.get("recommendations", []),
            "notes": row.notes,
        }

    import tempfile
    tmp = Path(tempfile.gettempdir()) / f"strategy_version_{version_id}.json"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return FileResponse(
        path=tmp,
        media_type="application/json",
        filename=f"strategy_version_{version_id}.json",
    )