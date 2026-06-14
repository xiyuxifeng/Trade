from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.strategy_regime_selection import RegimeRuleSelection, StrategyRegimeSelection
from src.common.stage2_writer_routing import require_canonical_write


class StrategyRegimeSelectionRepository:
    """Regime-aware selection 摘要仓储。"""

    async def upsert_selection(self, session: AsyncSession, selection: StrategyRegimeSelection) -> StrategyRegimeSelection:
        """按 selection_id 写入或更新摘要。"""
        require_canonical_write("daily_rule_selection", "StrategyRegimeSelectionRepository.upsert_selection")
        existing = await session.scalar(
            select(StrategyRegimeSelection).where(StrategyRegimeSelection.selection_id == selection.selection_id)
        )
        if existing is None:
            session.add(selection)
            await session.flush()
            return selection

        for field in (
            "strategy_version_id",
            "snapshot_id",
            "market_regime_version",
            "source_feature_version",
            "applicability_profile_version",
            "selected_rule_count",
            "skipped_rule_count",
            "blocked_rule_count",
            "confidence",
            "quality_status",
            "selection_reason",
            "evidence_json",
            "override_json",
            "selected_by",
            "storage_ref",
            "artifact_ref",
        ):
            setattr(existing, field, getattr(selection, field))
        await session.flush()
        return existing

    async def get_by_selection_id(self, session: AsyncSession, selection_id: str) -> StrategyRegimeSelection | None:
        """按 selection_id 查询摘要。"""
        return await session.scalar(
            select(StrategyRegimeSelection).where(StrategyRegimeSelection.selection_id == selection_id)
        )

    async def list_selections(
        self,
        session: AsyncSession,
        *,
        strategy_version_id: str | None = None,
        snapshot_id: str | None = None,
        market_regime_version: str | None = None,
        selected_by: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[StrategyRegimeSelection]:
        """按条件查询摘要列表。"""
        stmt = select(StrategyRegimeSelection)
        if strategy_version_id:
            stmt = stmt.where(StrategyRegimeSelection.strategy_version_id == strategy_version_id)
        if snapshot_id:
            stmt = stmt.where(StrategyRegimeSelection.snapshot_id == snapshot_id)
        if market_regime_version:
            stmt = stmt.where(StrategyRegimeSelection.market_regime_version == market_regime_version)
        if selected_by:
            stmt = stmt.where(StrategyRegimeSelection.selected_by == selected_by)
        stmt = stmt.order_by(StrategyRegimeSelection.created_at.desc())
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())

    async def count_selections(
        self,
        session: AsyncSession,
        *,
        strategy_version_id: str | None = None,
        snapshot_id: str | None = None,
        market_regime_version: str | None = None,
        selected_by: str | None = None,
    ) -> int:
        """统计满足条件的摘要数。"""
        stmt = select(func.count()).select_from(StrategyRegimeSelection)
        if strategy_version_id:
            stmt = stmt.where(StrategyRegimeSelection.strategy_version_id == strategy_version_id)
        if snapshot_id:
            stmt = stmt.where(StrategyRegimeSelection.snapshot_id == snapshot_id)
        if market_regime_version:
            stmt = stmt.where(StrategyRegimeSelection.market_regime_version == market_regime_version)
        if selected_by:
            stmt = stmt.where(StrategyRegimeSelection.selected_by == selected_by)
        result = await session.scalar(stmt)
        return int(result or 0)


class RegimeRuleSelectionRepository:
    """Regime-aware selection 单条规则结果仓储。"""

    async def replace_for_selection(
        self,
        session: AsyncSession,
        *,
        selection_id: str,
        items: list[RegimeRuleSelection],
    ) -> list[RegimeRuleSelection]:
        """替换指定 selection 的所有规则记录。"""
        require_canonical_write("daily_rule_selection", "RegimeRuleSelectionRepository.replace_for_selection")
        await session.execute(delete(RegimeRuleSelection).where(RegimeRuleSelection.selection_id == selection_id))
        for item in items:
            session.add(item)
        await session.flush()
        return items

    async def list_by_selection_id(self, session: AsyncSession, selection_id: str) -> list[RegimeRuleSelection]:
        """按 selection_id 查询规则记录。"""
        result = await session.scalars(
            select(RegimeRuleSelection).where(RegimeRuleSelection.selection_id == selection_id).order_by(RegimeRuleSelection.rule_id.asc())
        )
        return list(result.all())

    async def list_by_rule_id(self, session: AsyncSession, rule_id: str, limit: int | None = None) -> list[RegimeRuleSelection]:
        """按 rule_id 查询规则记录。"""
        stmt = select(RegimeRuleSelection).where(RegimeRuleSelection.rule_id == rule_id).order_by(RegimeRuleSelection.created_at.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())
