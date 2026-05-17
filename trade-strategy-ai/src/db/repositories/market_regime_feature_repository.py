from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.market_regime import MarketRegimeFeature


class MarketRegimeFeatureRepository:
    """市场状态特征仓储。"""

    async def upsert_feature(self, session: AsyncSession, feature: MarketRegimeFeature) -> MarketRegimeFeature:
        """按 snapshot_id + feature_version 写入或更新 feature。"""
        existing = await session.scalar(
            select(MarketRegimeFeature).where(
                MarketRegimeFeature.snapshot_id == feature.snapshot_id,
                MarketRegimeFeature.feature_version == feature.feature_version,
            )
        )
        if existing is None:
            session.add(feature)
            await session.flush()
            return feature

        for field in (
            "trade_date",
            "market",
            "quality_status",
            "available_feature_count",
            "partial_feature_count",
            "missing_feature_count",
            "feature_payload_json",
            "summary_json",
            "storage_ref",
        ):
            setattr(existing, field, getattr(feature, field))
        await session.flush()
        return existing

    async def get_by_snapshot_and_version(
        self,
        session: AsyncSession,
        snapshot_id: str,
        feature_version: str,
    ) -> MarketRegimeFeature | None:
        """按 snapshot_id + feature_version 查询 feature。"""
        return await session.scalar(
            select(MarketRegimeFeature).where(
                MarketRegimeFeature.snapshot_id == snapshot_id,
                MarketRegimeFeature.feature_version == feature_version,
            )
        )

    async def list_by_snapshot_id(self, session: AsyncSession, snapshot_id: str) -> list[MarketRegimeFeature]:
        """按 snapshot_id 查询 feature 列表。"""
        result = await session.scalars(
            select(MarketRegimeFeature)
            .where(MarketRegimeFeature.snapshot_id == snapshot_id)
            .order_by(MarketRegimeFeature.created_at.desc(), MarketRegimeFeature.feature_version.desc())
        )
        return list(result.all())

    async def list_features(
        self,
        session: AsyncSession,
        *,
        trade_date: date | None = None,
        snapshot_id: str | None = None,
        market: str | None = None,
        feature_version: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[MarketRegimeFeature]:
        """按条件查询 feature 列表。"""
        stmt = select(MarketRegimeFeature)
        if trade_date is not None:
            stmt = stmt.where(MarketRegimeFeature.trade_date == trade_date)
        if snapshot_id:
            stmt = stmt.where(MarketRegimeFeature.snapshot_id == snapshot_id)
        if market:
            stmt = stmt.where(MarketRegimeFeature.market == market)
        if feature_version:
            stmt = stmt.where(MarketRegimeFeature.feature_version == feature_version)
        stmt = stmt.order_by(MarketRegimeFeature.created_at.desc(), MarketRegimeFeature.snapshot_id.asc())
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())

    async def count_features(
        self,
        session: AsyncSession,
        *,
        trade_date: date | None = None,
        snapshot_id: str | None = None,
        market: str | None = None,
        feature_version: str | None = None,
    ) -> int:
        """统计满足条件的 feature 数量。"""
        stmt = select(func.count()).select_from(MarketRegimeFeature)
        if trade_date is not None:
            stmt = stmt.where(MarketRegimeFeature.trade_date == trade_date)
        if snapshot_id:
            stmt = stmt.where(MarketRegimeFeature.snapshot_id == snapshot_id)
        if market:
            stmt = stmt.where(MarketRegimeFeature.market == market)
        if feature_version:
            stmt = stmt.where(MarketRegimeFeature.feature_version == feature_version)
        result = await session.scalar(stmt)
        return int(result or 0)
