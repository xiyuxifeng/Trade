"""策略库 Service：整合 schema、repository、builder，提供高层接口"""

from __future__ import annotations

from datetime import date, datetime, UTC
from typing import TYPE_CHECKING

from src.common.logger import get_logger
from src.strategy_library.builder import ArticleEvidence, StrategyVersionBuilder
from src.strategy_library.repository import StrategyLibraryRepository
from src.strategy_library.schemas import (
    StrategyAdjustment,
    StrategyRecommendation,
    StrategyVersion,
    StrategyVersionStatus,
    StrategyVersionType,
)
from src.trader_profile.schemas import TraderProfile

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


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

    async def get_latest_candidate_version(
        self,
        session: AsyncSession,
        trader_id: str,
        strategy_date: date,
    ) -> StrategyVersion | None:
        """读取某 trader 指定日期的最新候选版本（无则返回 None）。"""
        all_versions = await self._repo.get_by_trader_and_date(
            session=session,
            trader_id=trader_id,
            strategy_date=strategy_date,
        )
        candidates = [
            v for v in all_versions
            if v.status == StrategyVersionStatus.draft and v.version_type == StrategyVersionType.candidate
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda v: v.released_at or datetime.min, reverse=True)[0]

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
        logger.info(
            "策略版本草稿已保存: trader=%s, date=%s, version=%s, recommendations=%d",
            trader_id,
            strategy_date,
            version.version_id,
            len(version.recommendations),
        )
        return version

    async def release_version(
        self,
        session: AsyncSession,
        draft_version: StrategyVersion,
    ) -> StrategyVersion:
        """将草稿版本升级为已发布版本（S3-010 唯一性保证）。

        约束：
        - candidate 类型的 draft 版本不能通过此方法晋升，必须人工确认
        - 同一 trader 同日只能有一个 released 版本（S3-010）
        """
        logger.info(
            "策略版本发布: trader=%s, date=%s, draft_version=%s, version_type=%s",
            draft_version.trader_id,
            draft_version.strategy_date,
            draft_version.version_id,
            draft_version.version_type,
        )

        # S7-003：candidate 类型不能自动晋升
        if draft_version.version_type == StrategyVersionType.candidate:
            raise ValueError(
                f"候选版本（candidate）不能自动晋升为 released，必须人工确认。 "
                f"version_id={draft_version.version_id}"
            )

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
            version_type=draft_version.version_type,
            parent_version_id=draft_version.parent_version_id,
            recommendations=draft_version.recommendations,
            source_article_ids=draft_version.source_article_ids,
            evidence_refs=draft_version.evidence_refs,
            notes=draft_version.notes,
            released_at=datetime.now(UTC),
            rules_snapshot=draft_version.rules_snapshot,
        )
        await self._repo.save(session=session, version=released)
        logger.info(
            "策略版本已发布: trader=%s, date=%s, released_version=%s",
            released.trader_id,
            released.strategy_date,
            released.version_id,
        )
        return released

    async def create_candidate_version(
        self,
        session: AsyncSession,
        trader_id: str,
        strategy_date: date,
        parent_version_id: str,
        adjustments: list[StrategyAdjustment],
        recommendations: list[StrategyRecommendation],
    ) -> StrategyVersion:
        """基于正式版本创建候选优化版本（S7-003）。

        候选版本：
        - 状态为 draft，version_type 为 candidate
        - 引用 parent_version_id 追溯正式版本
        - 由优化流程（S7-001/S7-002）生成
        - 不得自动晋升为 released，必须人工确认

        Args:
            session: 数据库 session
            trader_id: 交易员 ID
            strategy_date: 策略日期
            parent_version_id: 父版本 ID（正式版本）
            adjustments: 策略调整建议列表
            recommendations: 调整后的推荐列表

        Returns:
            创建的候选版本
        """
        # 生成调整说明
        notes = self._format_adjustment_notes(adjustments)

        # 使用 builder 创建候选版本
        candidate = self._builder.build_candidate(
            trader_id=trader_id,
            strategy_date=strategy_date,
            parent_version_id=parent_version_id,
            recommendations=recommendations,
            notes=notes,
        )

        await self._repo.save(session=session, version=candidate)
        logger.info(
            "候选版本已创建: trader=%s, date=%s, candidate_version=%s, parent_version=%s, adjustments=%d",
            trader_id,
            strategy_date,
            candidate.version_id,
            parent_version_id,
            len(adjustments),
        )
        return candidate

    def _format_adjustment_notes(self, adjustments: list[StrategyAdjustment]) -> str:
        """将策略调整建议格式化为 notes 字符串。"""
        if not adjustments:
            return "基于优化流程生成的候选版本"
        lines = ["候选版本优化建议："]
        for adj in adjustments:
            lines.append(
                f"- [{adj.trader_id}] {adj.rule_id}: {adj.current_status} → {adj.suggestion} "
                f"(依据: {adj.依据}, confidence={adj.confidence:.2f})"
            )
        return "\n".join(lines)
