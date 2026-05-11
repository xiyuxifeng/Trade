"""快照查询接口。

NTL-S7-005
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.dependencies import verify_api_key
from src.market_universe.snapshot_service import SnapshotService
from src.common.logger import get_logger

router = APIRouter(prefix="/snapshots", tags=["snapshots"])
logger = get_logger(__name__)


class PaginatedResponse(BaseModel):
    status: str = "success"
    count: int
    total: int
    skip: int
    limit: int
    items: list[dict]


class SnapshotDetail(BaseModel):
    status: str = "success"
    item: dict


def _get_snapshot_service() -> SnapshotService:
    """获取 SnapshotService 实例。"""
    return SnapshotService(base_dir="data/market_universe/snapshots")


@router.get("/", response_model=PaginatedResponse)
async def list_snapshots(
    _key: str = Depends(verify_api_key),
    snapshot_type: str | None = Query(default=None, alias="type", description="快照类型"),
    date: str | None = Query(default=None, description="交易日期 YYYY-MM-DD"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse:
    """列出快照（分页）。"""
    service = _get_snapshot_service()

    if date:
        snapshots = []
        date_dir = service.base_dir / date
        if date_dir.exists():
            for slot_file in sorted(date_dir.glob("*.json")):
                slot = slot_file.stem
                mu = service.load(date, slot)
                if mu:
                    snapshots.append((date, slot, mu))
        all_items = [
            {
                "snapshot_id": f"{d}_{s}",
                "trade_date": d,
                "slot": s,
                "type": _guess_type(mu),
            }
            for d, s, mu in snapshots
        ]
    else:
        all_items = []
        if service.base_dir.exists():
            for date_dir in sorted(service.base_dir.iterdir()):
                if not date_dir.is_dir():
                    continue
                trade_date = date_dir.name
                for slot_file in sorted(date_dir.glob("*.json")):
                    slot = slot_file.stem
                    mu = service.load(trade_date, slot)
                    if mu:
                        all_items.append({
                            "snapshot_id": f"{trade_date}_{slot}",
                            "trade_date": trade_date,
                            "slot": slot,
                            "type": _guess_type(mu),
                        })

    if snapshot_type:
        all_items = [it for it in all_items if it["type"] == snapshot_type]

    total = len(all_items)
    paginated = all_items[skip: skip + limit]

    return PaginatedResponse(
        count=len(paginated),
        total=total,
        skip=skip,
        limit=limit,
        items=paginated,
    )


def _guess_type(mu) -> str:
    """猜测快照类型（基于内容）。"""
    if mu.hot_topics and mu.hot_topics.topics:
        return "hot_topics"
    if mu.topic_constituents and mu.topic_constituents.constituents:
        return "topic_constituents"
    if mu.strong_symbols and mu.strong_symbols.symbols:
        return "strong_symbols"
    return "market_universe"


@router.get("/{snapshot_id}", response_model=SnapshotDetail)
async def get_snapshot(snapshot_id: str, _key: str = Depends(verify_api_key)) -> SnapshotDetail:
    """获取快照详情。"""
    parts = snapshot_id.rsplit("_", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的 snapshot_id")
    trade_date, slot = parts[0], parts[1]

    service = _get_snapshot_service()
    mu = service.load(trade_date, slot)

    if mu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="快照未找到")

    payload = _serialize_market_universe(mu)
    return SnapshotDetail(item=payload)


@router.get("/{snapshot_id}/download")
async def download_snapshot(snapshot_id: str, _key: str = Depends(verify_api_key)) -> FileResponse:
    """下载快照 JSON 文件。"""
    parts = snapshot_id.rsplit("_", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的 snapshot_id")
    trade_date, slot = parts[0], parts[1]

    service = _get_snapshot_service()
    mu = service.load(trade_date, slot)

    if mu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="快照未找到")

    import tempfile
    tmp = Path(tempfile.gettempdir()) / f"snapshot_{snapshot_id}.json"
    tmp.write_text(json.dumps(_serialize_market_universe(mu), ensure_ascii=False, indent=2), encoding="utf-8")

    return FileResponse(
        path=tmp,
        media_type="application/json",
        filename=f"snapshot_{snapshot_id}.json",
    )


def _serialize_market_universe(mu) -> dict:
    """将 MarketUniverse 序列化为 dict。"""
    return {
        "trade_date": mu.trade_date,
        "slot": mu.slot,
        "fetched_at": mu.fetched_at.isoformat() if mu.fetched_at else None,
        "hot_topics": {
            "trade_date": mu.hot_topics.trade_date,
            "slot": mu.hot_topics.slot,
            "topics": [
                {
                    "kind": t.kind,
                    "topic_id": t.topic_id,
                    "topic_name": t.topic_name,
                    "score": t.score,
                    "increase_pct": t.increase_pct,
                }
                for t in (mu.hot_topics.topics or [])
            ],
        } if mu.hot_topics else None,
        "topic_constituents": {
            "constituents": [
                {
                    "kind": c.kind,
                    "topic_id": c.topic_id,
                    "topic_name": c.topic_name,
                    "symbol": c.symbol,
                    "name": c.name,
                }
                for c in (mu.topic_constituents.constituents or [])
            ],
        } if mu.topic_constituents else None,
        "strong_symbols": {
            "symbols": [
                {
                    "kind": s.kind,
                    "symbol": s.symbol,
                    "name": s.name,
                    "strength_score": s.strength_score,
                }
                for s in (mu.strong_symbols.symbols or [])
            ],
        } if mu.strong_symbols else None,
        "metadata": mu.metadata,
    }