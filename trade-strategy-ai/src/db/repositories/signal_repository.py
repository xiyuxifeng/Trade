from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.converters import schema_to_signal_context_orm, schema_to_signal_orm
from src.models.signal import Signal
from src.strategy.types import SignalContext


class SignalRepository:
    """交易信号仓储。"""

    def _parse_signal_id(self, signal_id: str | UUID) -> UUID:
        """把 signal_id 规范化为 UUID。"""
        if isinstance(signal_id, UUID):
            return signal_id
        return UUID(str(signal_id))

    async def list_signals(
        self,
        session: AsyncSession,
        *,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Signal]:
        """按条件查询信号列表。"""
        stmt = select(Signal)
        if symbol:
            stmt = stmt.where(Signal.symbol == symbol)
        if since is not None:
            stmt = stmt.where(Signal.created_at >= since)
        stmt = stmt.order_by(Signal.created_at.desc(), Signal.id.desc())
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())

    async def count_signals(
        self,
        session: AsyncSession,
        *,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> int:
        """统计满足条件的信号数量。"""
        stmt = select(func.count()).select_from(Signal)
        if symbol:
            stmt = stmt.where(Signal.symbol == symbol)
        if since is not None:
            stmt = stmt.where(Signal.created_at >= since)
        result = await session.scalar(stmt)
        return int(result or 0)

    async def get_by_signal_id(self, session: AsyncSession, signal_id: str | UUID) -> Signal | None:
        """按 signal_id 查询单条信号。"""
        signal_uuid = self._parse_signal_id(signal_id)
        stmt = select(Signal).where(Signal.signal_id == signal_uuid)
        return await session.scalar(stmt)

    async def upsert_signal(
        self,
        session: AsyncSession,
        signal: "Signal",
        *,
        context: SignalContext | dict | None = None,
    ) -> Signal:
        """写入或更新信号。"""
        signal_uuid = self._parse_signal_id(signal.signal_id)
        existing = await session.scalar(select(Signal).where(Signal.signal_id == signal_uuid))
        if not isinstance(existing, Signal):
            existing = None

        payload = Signal()
        schema_to_signal_orm(signal, payload)
        payload.signal_id = signal_uuid
        if context is not None:
            metadata = dict(payload.signal_metadata or {})
            if isinstance(context, SignalContext):
                metadata["context"] = schema_to_signal_context_orm(context)
            else:
                metadata["context"] = context
            payload.signal_metadata = metadata

        if existing is None:
            session.add(payload)
            await session.flush()
            return payload

        for field in (
            "symbol",
            "side",
            "confidence",
            "triggered_rules",
            "synthesis_mode",
            "entry_price",
            "position_size",
            "stop_loss",
            "take_profit",
            "trader_id",
            "strategy_version_id",
            "source_topic_ids",
            "evidence_refs",
            "decision_mode",
            "evaluation_result_id",
            "rejected",
            "rejection_reason",
            "degraded",
            "degradation_reason",
            "version",
            "signal_metadata",
        ):
            setattr(existing, field, getattr(payload, field))
        await session.flush()
        return existing

    def list_signals_sync(
        self,
        session_factory,
        *,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Signal]:
        """同步入口中执行列表查询。"""

        async def _run() -> list[Signal]:
            async with session_factory() as session:
                return await self.list_signals(
                    session,
                    symbol=symbol,
                    since=since,
                    limit=limit,
                    offset=offset,
                )

        return asyncio.run(_run())
