from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.market_regime_record import MarketRegimeRecord


class MarketRegimeRepository:
    """市场状态主记录仓储。"""

    async def upsert_regime(self, session: AsyncSession, regime: MarketRegimeRecord) -> MarketRegimeRecord:
        """按 snapshot_id + regime_version 写入或更新 regime。"""
        existing = await session.scalar(
            select(MarketRegimeRecord).where(
                MarketRegimeRecord.snapshot_id == regime.snapshot_id,
                MarketRegimeRecord.regime_version == regime.regime_version,
            )
        )
        if existing is None:
            session.add(regime)
            await session.flush()
            return regime

        for field in (
            "regime_id",
            "trade_date",
            "market",
            "source_feature_version",
            "primary_label",
            "labels_json",
            "features_json",
            "confidence",
            "quality_status",
            "missing_reason",
            "storage_ref",
        ):
            setattr(existing, field, getattr(regime, field))
        await session.flush()
        return existing

    async def get_by_snapshot_and_version(
        self,
        session: AsyncSession,
        snapshot_id: str,
        regime_version: str,
    ) -> MarketRegimeRecord | None:
        """按 snapshot_id + regime_version 查询 regime。"""
        return await session.scalar(
            select(MarketRegimeRecord).where(
                MarketRegimeRecord.snapshot_id == snapshot_id,
                MarketRegimeRecord.regime_version == regime_version,
            )
        )

    async def list_regimes(
        self,
        session: AsyncSession,
        *,
        trade_date: date | None = None,
        snapshot_id: str | None = None,
        market: str | None = None,
        regime_version: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[MarketRegimeRecord]:
        """按条件查询 regime 列表。"""
        stmt = select(MarketRegimeRecord)
        if trade_date is not None:
            stmt = stmt.where(MarketRegimeRecord.trade_date == trade_date)
        if snapshot_id:
            stmt = stmt.where(MarketRegimeRecord.snapshot_id == snapshot_id)
        if market:
            stmt = stmt.where(MarketRegimeRecord.market == market)
        if regime_version:
            stmt = stmt.where(MarketRegimeRecord.regime_version == regime_version)
        stmt = stmt.order_by(MarketRegimeRecord.created_at.desc(), MarketRegimeRecord.snapshot_id.asc())
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())

    async def count_regimes(
        self,
        session: AsyncSession,
        *,
        trade_date: date | None = None,
        snapshot_id: str | None = None,
        market: str | None = None,
        regime_version: str | None = None,
    ) -> int:
        """统计满足条件的 regime 数量。"""
        stmt = select(func.count()).select_from(MarketRegimeRecord)
        if trade_date is not None:
            stmt = stmt.where(MarketRegimeRecord.trade_date == trade_date)
        if snapshot_id:
            stmt = stmt.where(MarketRegimeRecord.snapshot_id == snapshot_id)
        if market:
            stmt = stmt.where(MarketRegimeRecord.market == market)
        if regime_version:
            stmt = stmt.where(MarketRegimeRecord.regime_version == regime_version)
        result = await session.scalar(stmt)
        return int(result or 0)
