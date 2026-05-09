from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import verify_api_key
from src.market_universe.schemas import MarketUniverse
from src.services.snapshot_service import SnapshotService


router = APIRouter(prefix="/api/ui/v1/snapshots", tags=["ui-snapshots"])


def get_snapshot_service() -> SnapshotService:
    """获取 SnapshotService 实例，便于测试覆盖。"""
    return SnapshotService()


@router.get("")
async def list_snapshots(
    date_start: str = Query(..., description="开始日期 YYYY-MM-DD"),
    date_end: str = Query(..., description="结束日期 YYYY-MM-DD"),
    type: str | None = Query(default=None, description="快照类型"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """列出快照。"""
    snapshots = snapshot_service.list_snapshots(date_start, date_end)
    items = [
        {
            "snapshot_id": f"{snapshot.trade_date}_{snapshot.slot}",
            "trade_date": snapshot.trade_date,
            "slot": snapshot.slot,
            "type": _guess_type(snapshot),
        }
        for snapshot in snapshots
    ]
    if type:
        items = [item for item in items if item["type"] == type]

    total = len(items)
    paginated = items[skip : skip + limit]
    return {
        "count": len(paginated),
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": paginated,
    }


@router.get("/{snapshot_id}")
async def get_snapshot(
    snapshot_id: str,
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """返回单个快照详情。"""
    trade_date, slot = _split_snapshot_id(snapshot_id)
    snapshot = snapshot_service.load_snapshot(trade_date, slot)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="快照未找到")
    return {"item": _serialize_market_universe(snapshot)}


def _split_snapshot_id(snapshot_id: str) -> tuple[str, str]:
    parts = snapshot_id.rsplit("_", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="无效的 snapshot_id")
    return parts[0], parts[1]


def _guess_type(snapshot: MarketUniverse) -> str:
    if snapshot.hot_topics and snapshot.hot_topics.topics:
        return "hot_topics"
    if snapshot.topic_constituents and snapshot.topic_constituents.constituents:
        return "topic_constituents"
    if snapshot.strong_symbols and snapshot.strong_symbols.symbols:
        return "strong_symbols"
    return "market_universe"


def _serialize_market_universe(snapshot: MarketUniverse) -> dict[str, Any]:
    return {
        "trade_date": snapshot.trade_date,
        "slot": snapshot.slot,
        "fetched_at": snapshot.fetched_at.isoformat() if snapshot.fetched_at else None,
        "hot_topics": {
            "trade_date": snapshot.hot_topics.trade_date,
            "slot": snapshot.hot_topics.slot,
            "topics": [
                {
                    "kind": item.kind,
                    "topic_id": item.topic_id,
                    "topic_name": item.topic_name,
                    "score": item.score,
                    "increase_pct": item.increase_pct,
                    "speed_pct": item.speed_pct,
                    "turnover": item.turnover,
                    "net_inflow": item.net_inflow,
                }
                for item in (snapshot.hot_topics.topics or [])
            ],
            "sources": snapshot.hot_topics.sources,
            "fetched_at": snapshot.hot_topics.fetched_at.isoformat() if snapshot.hot_topics.fetched_at else None,
        }
        if snapshot.hot_topics
        else None,
        "topic_constituents": {
            "trade_date": snapshot.topic_constituents.trade_date,
            "slot": snapshot.topic_constituents.slot,
            "constituents": [
                {
                    "kind": item.kind,
                    "topic_id": item.topic_id,
                    "topic_name": item.topic_name,
                    "symbol": item.symbol,
                    "name": item.name,
                    "topic_change_pct": item.topic_change_pct,
                    "leader_symbol": item.leader_symbol,
                    "leader_name": item.leader_name,
                    "leader_change_pct": item.leader_change_pct,
                    "board_num": item.board_num,
                    "net_buy": item.net_buy,
                    "brief_intro": item.brief_intro,
                }
                for item in (snapshot.topic_constituents.constituents or [])
            ],
            "sources": snapshot.topic_constituents.sources,
            "fetched_at": snapshot.topic_constituents.fetched_at.isoformat() if snapshot.topic_constituents.fetched_at else None,
        }
        if snapshot.topic_constituents
        else None,
        "strong_symbols": {
            "trade_date": snapshot.strong_symbols.trade_date,
            "slot": snapshot.strong_symbols.slot,
            "symbols": [
                {
                    "kind": item.kind,
                    "symbol": item.symbol,
                    "name": item.name,
                    "strength_score": item.strength_score,
                    "change_pct": item.change_pct,
                    "turnover": item.turnover,
                    "turnover_ratio": item.turnover_ratio,
                    "return_pct": item.return_pct,
                    "net_inflow": item.net_inflow,
                    "main_force_buy": item.main_force_buy,
                    "main_force_sell": item.main_force_sell,
                    "rt_change_pct": item.rt_change_pct,
                    "bid_net": item.bid_net,
                    "bid_turnover": item.bid_turnover,
                    "topic_tags": item.topic_tags,
                }
                for item in (snapshot.strong_symbols.symbols or [])
            ],
            "sources": snapshot.strong_symbols.sources,
            "fetched_at": snapshot.strong_symbols.fetched_at.isoformat() if snapshot.strong_symbols.fetched_at else None,
        }
        if snapshot.strong_symbols
        else None,
        "metadata": snapshot.metadata,
    }
