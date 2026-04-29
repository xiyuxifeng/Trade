# src/trader_memory/service.py
"""TraderMemory 数据服务 - 数据库实现

TraderMemoryStore 的数据库实现，替代原来的 JSONL 文件存储。
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.common.config import AppConfig
from src.common.logger import get_logger
from src.models.trader_memory import TraderMemory
from src.trader_memory.schemas import (
    TraderMemoryFilter,
    TraderMemoryItem,
    TraderMemorySummary,
    TraderMemoryType,
)

logger = get_logger(__name__)


class TraderMemoryStore:
    """交易员记忆存储服务（数据库实现）。

    替代原来的 JSONL 文件存储，支持软删除、硬删除和条件查询。
    """

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        path: Path | None = None,
    ) -> None:
        """初始化存储服务。

        Args:
            session_factory: SQLAlchemy async session factory。
                           如果不提供，使用默认的 get_session_factory()。
            path: 已废弃参数，仅保留向后兼容。不再用于主存储。
        """
        if session_factory is None:
            from config.database import get_session_factory
            session_factory = get_session_factory()
        self._factory = session_factory
        self._legacy_path = path  # 仅保留向后兼容，不用于实际存储

    def _item_to_model(self, item: TraderMemoryItem) -> dict[str, Any]:
        """将 TraderMemoryItem 转换为数据库模型字典"""
        return {
            "id": item.memory_id,
            "trader_id": item.trader_id,
            "memory_type": item.memory_type.value if isinstance(item.memory_type, TraderMemoryType) else item.memory_type,
            "as_of_date": item.as_of_date,
            "symbol": item.symbol,
            "title": item.title,
            "content": item.content,
            "source": item.source,
            "source_ref": item.source_ref,
            "tags": item.tags,
            "importance": item.importance,
            "archived": item.archived,
            "archived_at": item.archived_at,
            "idea_id": item.idea_id,
            "strategy_version_id": item.strategy_version_id,
            "ranking_entry_id": item.ranking_entry_id,
            "topic_source": item.topic_source,
            "raw_topic_ids": item.raw_topic_ids,
            "postmortem_data": item.postmortem_data,
            "strategy_adjustment_data": item.strategy_adjustment_data,
            "market_regime_data": item.market_regime_data,
            "extra": item.extra,
        }

    def _model_to_item(self, model: TraderMemory) -> TraderMemoryItem:
        """将数据库模型转换为 TraderMemoryItem"""
        return TraderMemoryItem(
            memory_id=model.id,
            trader_id=model.trader_id,
            memory_type=TraderMemoryType(model.memory_type),
            as_of_date=model.as_of_date,
            symbol=model.symbol,
            title=model.title,
            content=model.content,
            source=model.source,
            source_ref=model.source_ref,
            tags=model.tags or [],
            importance=model.importance,
            archived=model.archived,
            archived_at=model.archived_at,
            idea_id=model.idea_id,
            strategy_version_id=model.strategy_version_id,
            ranking_entry_id=model.ranking_entry_id,
            topic_source=model.topic_source,
            raw_topic_ids=model.raw_topic_ids,
            postmortem_data=model.postmortem_data,
            strategy_adjustment_data=model.strategy_adjustment_data,
            market_regime_data=model.market_regime_data,
            extra=model.extra or {},
            created_at=model.created_at,
        )

    def _build_where_clause(self, filter: TraderMemoryFilter) -> list[Any]:
        """根据 filter 构建查询条件"""
        conditions = [TraderMemory.trader_id == filter.trader_id]

        if not filter.include_archived:
            conditions.append(TraderMemory.archived == False)

        if filter.memory_types:
            type_values = [t.value if isinstance(t, TraderMemoryType) else t for t in filter.memory_types]
            conditions.append(TraderMemory.memory_type.in_(type_values))

        if filter.symbol:
            conditions.append(TraderMemory.symbol == filter.symbol)

        if filter.date_from:
            conditions.append(TraderMemory.as_of_date >= filter.date_from)

        if filter.date_to:
            conditions.append(TraderMemory.as_of_date <= filter.date_to)

        if filter.keyword:
            keyword = f"%{filter.keyword.lower()}%"
            conditions.append(
                or_(
                    func.lower(TraderMemory.title).like(keyword),
                    func.lower(TraderMemory.content).like(keyword),
                )
            )

        if filter.tags:
            # 匹配任一 tag
            conditions.append(TraderMemory.tags.overlap(filter.tags))

        if filter.strategy_version_id:
            conditions.append(TraderMemory.strategy_version_id == filter.strategy_version_id)

        return conditions

    async def append(self, item: TraderMemoryItem) -> None:
        """追加一条记忆到数据库"""
        async with self._factory() as session:
            model = TraderMemory(**self._item_to_model(item))
            session.add(model)
            await session.commit()

    async def list_filtered(self, filter: TraderMemoryFilter) -> list[TraderMemoryItem]:
        """返回符合条件的记忆列表"""
        async with self._factory() as session:
            stmt = (
                select(TraderMemory)
                .where(and_(*self._build_where_clause(filter)))
                .order_by(TraderMemory.created_at.desc())
                .offset(filter.offset)
                .limit(filter.limit)
            )
            result = await session.scalars(stmt)
            return [self._model_to_item(m) for m in result.all()]

    async def count_filtered(self, filter: TraderMemoryFilter) -> int:
        """返回符合条件的记忆总数"""
        async with self._factory() as session:
            stmt = select(func.count()).select_from(TraderMemory).where(
                and_(*self._build_where_clause(filter))
            )
            return await session.scalar(stmt) or 0

    async def archive(self, memory_id: UUID) -> bool:
        """软删除：标记记忆为已归档"""
        async with self._factory() as session:
            stmt = select(TraderMemory).where(TraderMemory.id == memory_id)
            model = await session.scalar(stmt)
            if model is None:
                return False
            model.archived = True
            model.archived_at = datetime.now(UTC)
            await session.commit()
            return True

    async def restore(self, memory_id: UUID) -> bool:
        """恢复已归档的记忆"""
        async with self._factory() as session:
            stmt = select(TraderMemory).where(TraderMemory.id == memory_id)
            model = await session.scalar(stmt)
            if model is None:
                return False
            model.archived = False
            model.archived_at = None
            await session.commit()
            return True

    async def update(self, memory_id: UUID, updated_item: TraderMemoryItem) -> bool:
        """更新指定记忆"""
        async with self._factory() as session:
            stmt = select(TraderMemory).where(TraderMemory.id == memory_id)
            model = await session.scalar(stmt)
            if model is None:
                return False
            for key, value in self._item_to_model(updated_item).items():
                setattr(model, key, value)
            await session.commit()
            return True

    async def hard_delete(self, memory_id: UUID) -> bool:
        """永久删除记忆"""
        async with self._factory() as session:
            stmt = select(TraderMemory).where(TraderMemory.id == memory_id)
            model = await session.scalar(stmt)
            if model is None:
                return False
            await session.delete(model)
            await session.commit()
            return True

    async def list_recent(
        self,
        *,
        trader_id: str,
        limit: int = 10,
        memory_types: list[TraderMemoryType] | None = None,
    ) -> list[TraderMemoryItem]:
        """返回指定交易员最近的记忆"""
        f = TraderMemoryFilter(
            trader_id=trader_id,
            memory_types=memory_types,
            limit=limit,
        )
        return await self.list_filtered(f)

    async def search_by_symbol(
        self,
        *,
        trader_id: str,
        symbol: str,
        limit: int = 10,
    ) -> list[TraderMemoryItem]:
        """返回指定交易员和标的的记忆"""
        f = TraderMemoryFilter(
            trader_id=trader_id,
            symbol=symbol,
            limit=limit,
        )
        return await self.list_filtered(f)

    async def summarize_context(
        self,
        *,
        trader_id: str,
        symbol: str | None = None,
        limit: int = 5,
    ) -> TraderMemorySummary:
        """构建记忆摘要，用于交易想法生成"""
        async with self._factory() as session:
            base_conditions = [TraderMemory.trader_id == trader_id]
            if symbol:
                base_conditions.append(TraderMemory.symbol == symbol)

            # 活跃记忆
            active_conditions = base_conditions + [TraderMemory.archived == False]
            stmt = (
                select(TraderMemory)
                .where(and_(*active_conditions))
                .order_by(TraderMemory.created_at.desc())
            )
            result = await session.scalars(stmt)
            active_items = list(result.all())

            by_type: dict[str, int] = {}
            for item in active_items:
                key = item.memory_type
                by_type[key] = by_type.get(key, 0) + 1

            symbol_items = [i for i in active_items if symbol and i.symbol == symbol]

            # 归档记忆数量（需单独查询）
            archived_conditions = base_conditions + [TraderMemory.archived == True]
            archived_stmt = select(func.count()).select_from(TraderMemory).where(
                and_(*archived_conditions)
            )
            archived_count = await session.scalar(archived_stmt) or 0

            return TraderMemorySummary(
                trader_id=trader_id,
                symbol=symbol,
                total_items=len(active_items),
                total_symbol_items=len(symbol_items),
                archived_items=archived_count,
                by_type=by_type,
                recent_titles=[item.title for item in active_items[: max(0, int(limit))]],
                symbol_titles=[item.title for item in symbol_items[: max(0, int(limit))]],
                review_notes=[
                    item.content
                    for item in active_items
                    if item.memory_type == TraderMemoryType.review_note.value
                ][: max(0, int(limit))],
                postmortem_notes=[
                    item.content
                    for item in active_items
                    if item.memory_type == TraderMemoryType.postmortem.value
                ][: max(0, int(limit))],
                strategy_adjustments=[
                    item.content
                    for item in active_items
                    if item.memory_type == TraderMemoryType.strategy_adjustment.value
                ][: max(0, int(limit))],
                market_regime_notes=[
                    item.content
                    for item in active_items
                    if item.memory_type == TraderMemoryType.market_regime_note.value
                ][: max(0, int(limit))],
            )

    # ========== 兼容性别名（同步转异步）==========

    def append_sync(self, item: TraderMemoryItem) -> None:
        """同步版本追加（仅用于兼容旧代码，建议使用 async 版本）"""
        import asyncio
        asyncio.get_event_loop().run_until_complete(self.append(item))

    def list_filtered_sync(self, filter: TraderMemoryFilter) -> list[TraderMemoryItem]:
        """同步版本查询（仅用于兼容旧代码，建议使用 async 版本）"""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.list_filtered(filter))