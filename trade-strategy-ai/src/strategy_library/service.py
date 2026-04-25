"""策略库 Service：整合 schema、repository、builder，提供高层接口"""

from __future__ import annotations

from datetime import date, datetime, UTC
from typing import TYPE_CHECKING

from src.strategy_library.builder import ArticleEvidence, StrategyVersionBuilder
from src.strategy_library.repository import StrategyLibraryRepository
from src.strategy_library.schemas import StrategyVersion, StrategyVersionStatus
from src.trader_profile.schemas import TraderProfile

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class StrategyLibraryService:
    """策略库 Service。

    整合 StrategyLibraryRepository（持久化）和 StrategyVersionBuilder（构建），
    提供按 trader 读取当前发布版本、构建并保存草稿、发布版本等高层接口。
    """

    def __init__(
        self,
        repo: StrategyLibraryRepository | None = None,
        builder: StrategyVersionBuilder | None = None,
    ) -> None:
        self._repo = repo or StrategyLibraryRepository()
        self._builder = builder or StrategyVersionBuilder()

    async def get_current_released_version(
        self,
        session: AsyncSession,
        trader_id: str,
        strategy_date: date,
    ) -> StrategyVersion | None:
        """读取某 trader 指定日期的已发布版本（无则返回 None）。"""
        versions = await self._repo.get_released_by_trader_and_date(
            session=session,
            trader_id=trader_id,
            strategy_date=strategy_date,
        )
        if not versions:
            return None
        # 取最新发布的（按 released_at 倒序）
        return sorted(versions, key=lambda v: v.released_at or datetime.min, reverse=True)[0]

    async def get_latest_draft_version(
        self,
        session: AsyncSession,
        trader_id: str,
        strategy_date: date,
    ) -> StrategyVersion | None:
        """读取某 trader 指定日期的草稿版本（无则返回 None）。"""
        all_versions = await self._repo.get_by_trader_and_date(
            session=session,
            trader_id=trader_id,
            strategy_date=strategy_date,
        )
        drafts = [v for v in all_versions if v.status == StrategyVersionStatus.draft]
        if not drafts:
            return None
        return drafts[0]

    async def get_version(
        self,
        session: AsyncSession,
        version_id: str,
    ) -> StrategyVersion | None:
        """按 version_id 读取策略版本。

        用于 EvidencePack 构造时加载 rules_snapshot。

        Args:
            session: 数据库 session
            version_id: 版本 ID

        Returns:
            StrategyVersion 或 None
        """
        return await self._repo.get_by_version_id(session=session, version_id=version_id)

    async def save_version(self, session: AsyncSession, version: StrategyVersion) -> None:
        """保存或更新策略版本。"""
        await self._repo.save(session=session, version=version)

    async def build_and_save_draft(
        self,
        session: AsyncSession,
        trader_id: str,
        strategy_date: date,
        profile: TraderProfile,
        source_articles: list[ArticleEvidence],
    ) -> StrategyVersion:
        """构建草稿版本并持久化。"""
        version = self._builder.build_draft(
            trader_id=trader_id,
            strategy_date=strategy_date,
            profile=profile,
            source_articles=source_articles,
        )
        await self._repo.save(session=session, version=version)
        return version

    async def release_version(
        self,
        session: AsyncSession,
        draft_version: StrategyVersion,
    ) -> StrategyVersion:
        """将草稿版本升级为已发布版本（S3-010 唯一性保证）。"""
        # S3-010：检查是否已有 released 版本（同一 trader 同日唯一）
        existing = await self.get_current_released_version(
            session=session,
            trader_id=draft_version.trader_id,
            strategy_date=draft_version.strategy_date,
        )
        if existing is not None:
            raise ValueError(
                f" trader={draft_version.trader_id} date={draft_version.strategy_date} 已有 released 版本 "
                f"({existing.version_id})，不能重复发布"
            )

        released = StrategyVersion(
            version_id=draft_version.version_id.replace(
                StrategyVersionStatus.draft.value,
                StrategyVersionStatus.released.value,
            ),
            trader_id=draft_version.trader_id,
            strategy_date=draft_version.strategy_date,
            status=StrategyVersionStatus.released,
            recommendations=draft_version.recommendations,
            source_article_ids=draft_version.source_article_ids,
            evidence_refs=draft_version.evidence_refs,
            notes=draft_version.notes,
            released_at=datetime.now(UTC),
            rules_snapshot=draft_version.rules_snapshot,
        )
        await self._repo.save(session=session, version=released)
        return released
