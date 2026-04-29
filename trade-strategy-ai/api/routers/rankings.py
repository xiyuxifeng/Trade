"""Ranking 查询接口。

NTL-S7-005
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.common.logger import get_logger

router = APIRouter(prefix="/rankings", tags=["rankings"])
logger = get_logger(__name__)


class PaginatedResponse(BaseModel):
    status: str = "success"
    count: int
    total: int
    skip: int
    limit: int
    items: list[dict]


class RankingDetail(BaseModel):
    status: str = "success"
    item: dict


async def get_db_session():
    from src.db.session import session_scope
    async with session_scope() as session:
        yield session


@router.get("/", response_model=PaginatedResponse)
async def list_rankings(
    trader_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None, description="开始日期 YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="结束日期 YYYY-MM-DD"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse:
    """列出 ranking 条目（分页）。"""
    from sqlalchemy import select, func
    from src.models.ranking_entry import RankingEntryRecord
    from src.db.session import session_scope

    async with session_scope() as session:
        conditions = []
        if trader_id:
            conditions.append(RankingEntryRecord.trader_id == trader_id)
        if date_from:
            conditions.append(RankingEntryRecord.trade_date >= date_from)
        if date_to:
            conditions.append(RankingEntryRecord.trade_date <= date_to)

        count_stmt = select(func.count()).select_from(RankingEntryRecord)
        for c in conditions:
            count_stmt = count_stmt.where(c)
        result = await session.execute(count_stmt)
        total = result.scalar() or 0

        stmt = select(RankingEntryRecord).where(*conditions).order_by(
            RankingEntryRecord.trade_date.desc(), RankingEntryRecord.rank
        ).offset(skip).limit(limit)
        result = await session.execute(stmt)
        rows = result.scalars().all()

        items = [
            {
                "entry_id": str(row.entry_id),
                "trade_date": str(row.trade_date),
                "trader_id": row.trader_id,
                "strategy_version_id": row.strategy_version_id,
                "symbol": row.symbol,
                "return_pct": row.return_pct,
                "mfe": row.mfe,
                "mae": row.mae,
                "composite_score": row.composite_score,
                "rank": row.rank,
            }
            for row in rows
        ]

        return PaginatedResponse(
            count=len(items),
            total=total,
            skip=skip,
            limit=limit,
            items=items,
        )


@router.get("/{entry_id}", response_model=RankingDetail)
async def get_ranking(entry_id: str) -> RankingDetail:
    """获取 ranking 条目详情。"""
    from sqlalchemy import select
    from src.models.ranking_entry import RankingEntryRecord
    from src.db.session import session_scope

    async with session_scope() as session:
        stmt = select(RankingEntryRecord).where(RankingEntryRecord.entry_id == entry_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ranking 条目未找到")

        return RankingDetail(item={
            "entry_id": str(row.entry_id),
            "trade_date": str(row.trade_date),
            "trader_id": row.trader_id,
            "strategy_version_id": row.strategy_version_id,
            "symbol": row.symbol,
            "return_pct": row.return_pct,
            "mfe": row.mfe,
            "mae": row.mae,
            "composite_score": row.composite_score,
            "rank": row.rank,
            "is_latest": row.is_latest,
            "extra": row.extra,
        })


@router.get("/{entry_id}/download")
async def download_ranking(entry_id: str) -> FileResponse:
    """下载 ranking 条目 JSON 文件。"""
    from sqlalchemy import select
    from src.models.ranking_entry import RankingEntryRecord
    from src.db.session import session_scope

    async with session_scope() as session:
        stmt = select(RankingEntryRecord).where(RankingEntryRecord.entry_id == entry_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ranking 条目未找到")

        payload = {
            "entry_id": str(row.entry_id),
            "trade_date": str(row.trade_date),
            "trader_id": row.trader_id,
            "strategy_version_id": row.strategy_version_id,
            "symbol": row.symbol,
            "return_pct": row.return_pct,
            "mfe": row.mfe,
            "mae": row.mae,
            "composite_score": row.composite_score,
            "rank": row.rank,
            "is_latest": row.is_latest,
            "extra": row.extra,
        }

    import tempfile
    tmp = Path(tempfile.gettempdir()) / f"ranking_{entry_id}.json"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return FileResponse(
        path=tmp,
        media_type="application/json",
        filename=f"ranking_{entry_id}.json",
    )