"""策略库 Repository：TraderStrategyVersion ORM 与 StrategyVersion schema 的转换与持久化"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.trader_strategy_version import TraderStrategyVersion
from src.strategy_library.schemas import (
    StrategyRecommendation,
    StrategyVersion,
    StrategyVersionStatus,
    StrategyVersionType,
)

if TYPE_CHECKING:
    from src.strategy_library.schemas import StrategyVersion


def _get_version_type(orm_obj: TraderStrategyVersion) -> StrategyVersionType:
    """从 ORM 对象安全读取 version_type，兼容旧记录和 mock 对象。"""
    raw = getattr(orm_obj, "version_type", None)
    if isinstance(raw, str) and raw in ("manual", "candidate"):
        return StrategyVersionType(raw)
    return StrategyVersionType.manual


class StrategyLibraryRepository:
    """策略库 Repository。

    负责 TraderStrategyVersion ORM 模型与 StrategyVersion schema 之间的转换，
    并提供按 trader / 日期 / 状态的查询接口。
    """

    # ---- 公共查询接口 ----

    async def get_by_trader_and_date(
        self, session: AsyncSession, trader_id: str, strategy_date: date
    ) -> list[StrategyVersion]:
        """按交易员 ID 和策略日期查询版本列表（异步）。"""
        stmt = select(TraderStrategyVersion).where(
            TraderStrategyVersion.trader_id == trader_id,
            TraderStrategyVersion.strategy_date == strategy_date,
        ).order_by(TraderStrategyVersion.version_name)

        result = await session.execute(stmt)
        orm_objects = result.scalars().all()
        return [self._from_orm_model(obj) for obj in orm_objects]

    async def get_released_by_trader_and_date(
        self, session: AsyncSession, trader_id: str, strategy_date: date
    ) -> list[StrategyVersion]:
        """按交易员 ID 和策略日期查询已发布版本列表（异步）。"""
        stmt = select(TraderStrategyVersion).where(
            TraderStrategyVersion.trader_id == trader_id,
            TraderStrategyVersion.strategy_date == strategy_date,
            TraderStrategyVersion.status == StrategyVersionStatus.released.value,
        ).order_by(TraderStrategyVersion.version_name)

        result = await session.execute(stmt)
        orm_objects = result.scalars().all()
        return [self._from_orm_model(obj) for obj in orm_objects]

    async def get_by_version_id(
        self, session: AsyncSession, version_id: str
    ) -> StrategyVersion | None:
        """按 version_id 精确查询策略版本。

        用于 EvidencePack 构造时加载 rules_snapshot。

        Args:
            session: 数据库 session
            version_id: 版本 ID（如 "trader_001_2026-04-25_released"）

        Returns:
            StrategyVersion 或 None（不存在时）
        """
        stmt = select(TraderStrategyVersion).where(
            TraderStrategyVersion.version_name == version_id,
        )
        result = await session.execute(stmt)
        orm_obj = result.scalar_one_or_none()
        if orm_obj is None:
            return None
        return self._from_orm_model(orm_obj)

    async def save(self, session: AsyncSession, version: StrategyVersion) -> None:
        """保存或更新策略版本（异步）。"""
        existing = await self._get_existing(session, version)
        if existing:
            self._update_existing(existing, version)
        else:
            orm_obj = self._to_orm_model(version)
            session.add(orm_obj)

    # ---- ORM <-> Schema 转换 ----

    @staticmethod
    def _to_orm_model(version: StrategyVersion) -> TraderStrategyVersion:
        """将 StrategyVersion schema 转换为 TraderStrategyVersion ORM 对象。"""
        return TraderStrategyVersion(
            trader_id=version.trader_id,
            strategy_date=version.strategy_date,
            version_name=version.version_id,
            status=version.status.value,
            released_at=version.released_at,
            source_article_ids=version.source_article_ids,
            evidence_refs=version.evidence_refs,
            strategy_payload={
                "recommendations": [
                    {
                        "symbol": rec.symbol,
                        "decision": rec.decision,
                        "confidence": rec.confidence,
                        "entry_price": rec.entry_price,
                        "target_price": rec.target_price,
                        "stop_loss_price": rec.stop_loss_price,
                        "rationale": rec.rationale,
                        "evidence_refs": rec.evidence_refs,
                    }
                    for rec in version.recommendations
                ],
                "rules_snapshot": version.rules_snapshot,
            },
            notes=version.notes,
            version_type=version.version_type.value,
            parent_version_id=version.parent_version_id,
        )

    @staticmethod
    def _from_orm_model(orm_obj: TraderStrategyVersion) -> StrategyVersion:
        """将 TraderStrategyVersion ORM 对象转换为 StrategyVersion schema。"""
        recommendations = []
        for rec_data in orm_obj.strategy_payload.get("recommendations", []):
            recommendations.append(StrategyRecommendation(
                symbol=rec_data["symbol"],
                decision=rec_data["decision"],
                confidence=rec_data["confidence"],
                entry_price=rec_data.get("entry_price"),
                target_price=rec_data.get("target_price"),
                stop_loss_price=rec_data.get("stop_loss_price"),
                rationale=rec_data.get("rationale"),
                evidence_refs=rec_data.get("evidence_refs", []),
            ))

        return StrategyVersion(
            version_id=orm_obj.version_name,
            trader_id=orm_obj.trader_id,
            strategy_date=orm_obj.strategy_date,
            status=StrategyVersionStatus(orm_obj.status),
            recommendations=recommendations,
            source_article_ids=orm_obj.source_article_ids or [],
            evidence_refs=orm_obj.evidence_refs or [],
            notes=orm_obj.notes,
            released_at=orm_obj.released_at,
            rules_snapshot=orm_obj.strategy_payload.get("rules_snapshot", []),
            version_type=_get_version_type(orm_obj),
            parent_version_id=getattr(orm_obj, "parent_version_id", None),
        )

    # ---- 内部辅助方法 ----

    async def _get_existing(
        self, session: AsyncSession, version: StrategyVersion
    ) -> TraderStrategyVersion | None:
        """查询是否已存在同名版本。"""
        stmt = select(TraderStrategyVersion).where(
            TraderStrategyVersion.trader_id == version.trader_id,
            TraderStrategyVersion.strategy_date == version.strategy_date,
            TraderStrategyVersion.version_name == version.version_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    def _update_existing(self, existing: TraderStrategyVersion, version: StrategyVersion) -> None:
        """更新已有 ORM 对象。"""
        existing.status = version.status.value
        existing.released_at = version.released_at
        existing.source_article_ids = version.source_article_ids
        existing.evidence_refs = version.evidence_refs
        existing.strategy_payload = {
            "recommendations": [
                {
                    "symbol": rec.symbol,
                    "decision": rec.decision,
                    "confidence": rec.confidence,
                    "entry_price": rec.entry_price,
                    "target_price": rec.target_price,
                    "stop_loss_price": rec.stop_loss_price,
                    "rationale": rec.rationale,
                    "evidence_refs": rec.evidence_refs,
                }
                for rec in version.recommendations
            ],
            "rules_snapshot": version.rules_snapshot,
        }
        existing.notes = version.notes
        existing.version_type = version.version_type.value
        existing.parent_version_id = version.parent_version_id
