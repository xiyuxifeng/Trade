from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.article_metadata import ArticleMetadata
from src.models.article_metadata_selection import ArticleMetadataSelection
from src.services.article_analysis_selection_service import ArticleAnalysisRecord, ArticleAnalysisSelectionService


def _count_items(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    return 0


def _decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _schema_rank(version: str | None) -> int:
    if not version:
        return 0
    digits = "".join(ch for ch in version if ch.isdigit())
    if digits:
        try:
            return int(digits)
        except ValueError:
            return 0
    return 0


@dataclass(frozen=True)
class ArticleMetadataCandidateResolution:
    """单篇文章的候选 metadata 评分结果。"""

    schema_version: str
    score: float
    score_reasons: list[str]
    processed_at: datetime | None
    provider: str | None
    model: str | None
    article_type: str | None
    extraction_version: str | None
    sentiment_score: float | None
    confidence_score: float | None
    extracted_concepts_count: int
    trading_symbols_count: int
    strategy_rules_count: int
    preconditions_count: int
    comment_insights_count: int
    raw_llm_output_keys: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "score": self.score,
            "score_reasons": self.score_reasons,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "provider": self.provider,
            "model": self.model,
            "article_type": self.article_type,
            "extraction_version": self.extraction_version,
            "sentiment_score": self.sentiment_score,
            "confidence_score": self.confidence_score,
            "extracted_concepts_count": self.extracted_concepts_count,
            "trading_symbols_count": self.trading_symbols_count,
            "strategy_rules_count": self.strategy_rules_count,
            "preconditions_count": self.preconditions_count,
            "comment_insights_count": self.comment_insights_count,
            "raw_llm_output_keys": self.raw_llm_output_keys,
        }


@dataclass(frozen=True)
class ArticleMetadataResolution:
    """单篇文章的版本选择结果。"""

    article_id: UUID
    selected_schema_version: str | None
    selected_by: str | None
    selected_at: datetime | None
    selection_mode: str | None
    selection_score: float | None
    selection_reason: str | None
    recommended_schema_version: str | None
    recommended_score: float | None
    recommended_reason: str | None
    effective_schema_version: str | None
    effective_score: float | None
    effective_reason: str | None
    warning: str | None
    candidates: list[ArticleMetadataCandidateResolution]

    def to_dict(self) -> dict[str, Any]:
        return {
            "article_id": str(self.article_id),
            "selected_schema_version": self.selected_schema_version,
            "selected_by": self.selected_by,
            "selected_at": self.selected_at.isoformat() if self.selected_at else None,
            "selection_mode": self.selection_mode,
            "selection_score": self.selection_score,
            "selection_reason": self.selection_reason,
            "recommended_schema_version": self.recommended_schema_version,
            "recommended_score": self.recommended_score,
            "recommended_reason": self.recommended_reason,
            "effective_schema_version": self.effective_schema_version,
            "effective_score": self.effective_score,
            "effective_reason": self.effective_reason,
            "warning": self.warning,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


class ArticleMetadataSelectionService:
    """文章元数据版本选择与解析服务。"""

    def _score_metadata(self, meta: ArticleMetadata) -> tuple[float, list[str]]:
        """根据字段完整性和可用性给 metadata 打分。"""
        reasons: list[str] = []
        score = 0.0

        if meta.processed_at is not None:
            score += 1.5
            reasons.append("已完成处理")
        if meta.provider:
            score += 0.2
            reasons.append(f"provider={meta.provider}")
        if meta.model:
            score += 0.4
            reasons.append(f"model={meta.model}")
        if meta.article_type:
            score += 0.2
            reasons.append(f"article_type={meta.article_type}")
        if meta.extraction_version:
            score += 0.2
            reasons.append(f"extraction_version={meta.extraction_version}")

        concept_count = _count_items(meta.extracted_concepts)
        symbol_count = _count_items(meta.trading_symbols)
        strategy_rule_count = _count_items(meta.strategy_rules)
        precondition_count = _count_items(meta.preconditions)
        insight_count = _count_items(meta.comment_insights)
        llm_output_count = len(meta.raw_llm_output or {}) if isinstance(meta.raw_llm_output, dict) else 0

        if concept_count:
            score += min(2.0, concept_count * 0.35)
            reasons.append(f"concepts={concept_count}")
        if symbol_count:
            score += min(1.5, symbol_count * 0.4)
            reasons.append(f"symbols={symbol_count}")
        if strategy_rule_count:
            score += min(2.5, strategy_rule_count * 0.5)
            reasons.append(f"strategy_rules={strategy_rule_count}")
        if precondition_count:
            score += min(1.5, precondition_count * 0.35)
            reasons.append(f"preconditions={precondition_count}")
        if insight_count:
            score += min(1.0, insight_count * 0.25)
            reasons.append(f"comment_insights={insight_count}")
        if meta.sentiment_score is not None:
            score += 0.2
            reasons.append(f"sentiment={float(meta.sentiment_score)}")
        if meta.confidence_score is not None:
            score += 0.8
            reasons.append(f"confidence={float(meta.confidence_score)}")
        if llm_output_count:
            score += 0.3
            reasons.append("raw_llm_output_present")

        if not reasons:
            reasons.append("字段较少，作为兜底候选")

        return round(score, 4), reasons

    def _candidate_from_metadata(self, meta: ArticleMetadata) -> ArticleMetadataCandidateResolution:
        score, reasons = self._score_metadata(meta)
        return ArticleMetadataCandidateResolution(
            schema_version=meta.version,
            score=score,
            score_reasons=reasons,
            processed_at=meta.processed_at,
            provider=meta.provider,
            model=meta.model,
            article_type=meta.article_type,
            extraction_version=meta.extraction_version,
            sentiment_score=_decimal_to_float(meta.sentiment_score),
            confidence_score=_decimal_to_float(meta.confidence_score),
            extracted_concepts_count=_count_items(meta.extracted_concepts),
            trading_symbols_count=_count_items(meta.trading_symbols),
            strategy_rules_count=_count_items(meta.strategy_rules),
            preconditions_count=_count_items(meta.preconditions),
            comment_insights_count=_count_items(meta.comment_insights),
            raw_llm_output_keys=len(meta.raw_llm_output or {}) if isinstance(meta.raw_llm_output, dict) else 0,
        )

    def _candidate_from_analysis(self, analysis: ArticleAnalysisRecord) -> ArticleMetadataCandidateResolution:
        reasons: list[str] = ["Stage3结构化分析"]
        score = 1.5
        concept_count = _count_items(analysis.extracted_concepts)
        symbol_count = _count_items(analysis.trading_symbols)
        strategy_rule_count = _count_items(analysis.strategy_rules)
        precondition_count = _count_items(analysis.preconditions)
        llm_output_count = len(analysis.raw_llm_output or {}) if isinstance(analysis.raw_llm_output, dict) else 0

        if concept_count:
            score += min(2.0, concept_count * 0.35)
            reasons.append(f"concepts={concept_count}")
        if symbol_count:
            score += min(1.5, symbol_count * 0.4)
            reasons.append(f"symbols={symbol_count}")
        if strategy_rule_count:
            score += min(2.5, strategy_rule_count * 0.5)
            reasons.append(f"strategy_rules={strategy_rule_count}")
        if precondition_count:
            score += min(1.5, precondition_count * 0.35)
            reasons.append(f"preconditions={precondition_count}")
        if analysis.confidence_score is not None:
            score += 0.8
            reasons.append(f"confidence={float(analysis.confidence_score)}")
        if llm_output_count:
            score += 0.3
            reasons.append("raw_llm_output_present")

        return ArticleMetadataCandidateResolution(
            schema_version=analysis.schema_version,
            score=round(score, 4),
            score_reasons=reasons,
            processed_at=analysis.processed_at,
            provider=analysis.provider,
            model=analysis.model,
            article_type=analysis.article_type,
            extraction_version=analysis.extraction_version,
            sentiment_score=analysis.sentiment_score,
            confidence_score=analysis.confidence_score,
            extracted_concepts_count=concept_count,
            trading_symbols_count=symbol_count,
            strategy_rules_count=strategy_rule_count,
            preconditions_count=precondition_count,
            comment_insights_count=_count_items(analysis.comment_insights),
            raw_llm_output_keys=llm_output_count,
        )

    @staticmethod
    def _select_best_candidate(candidates: list[ArticleMetadataCandidateResolution]) -> ArticleMetadataCandidateResolution | None:
        if not candidates:
            return None
        return sorted(
            candidates,
            key=lambda item: (
                item.score,
                item.processed_at or datetime.min.replace(tzinfo=timezone.utc),
                _schema_rank(item.schema_version),
                item.schema_version,
            ),
            reverse=True,
        )[0]

    @staticmethod
    def _ordered_candidates(candidates: list[ArticleMetadataCandidateResolution]) -> list[ArticleMetadataCandidateResolution]:
        """按推荐优先级排序候选版本，便于 UI 和默认选中使用。"""
        return sorted(
            candidates,
            key=lambda item: (
                item.score,
                item.processed_at or datetime.min.replace(tzinfo=timezone.utc),
                _schema_rank(item.schema_version),
                item.schema_version,
            ),
            reverse=True,
        )

    @staticmethod
    def _selection_reason(best: ArticleMetadataCandidateResolution | None, selected_mode: str) -> str | None:
        if best is None:
            return None
        if selected_mode == "manual":
            return "用户手动确认"
        return "自动推荐：字段完整度、规则覆盖和置信度综合得分最高"

    async def load_candidates(
        self,
        session: AsyncSession,
        *,
        article_ids: list[UUID],
    ) -> dict[UUID, list[ArticleMetadataCandidateResolution]]:
        """批量加载文章候选 metadata。"""
        if not article_ids:
            return {}

        result = await session.scalars(
            select(ArticleMetadata)
            .where(ArticleMetadata.article_id.in_(article_ids))
            .where(ArticleMetadata.processed_at.is_not(None))
            .order_by(
                ArticleMetadata.article_id.asc(),
                ArticleMetadata.processed_at.desc(),
                ArticleMetadata.version.desc(),
            )
        )

        grouped: dict[UUID, list[ArticleMetadataCandidateResolution]] = {}
        for meta in result.all():
            grouped.setdefault(meta.article_id, []).append(self._candidate_from_metadata(meta))
        if await session.run_sync(lambda sync_session: inspect(sync_session.get_bind()).has_table("article_structures")):
            analysis_map = await ArticleAnalysisSelectionService().load_effective_analysis_map(session, article_ids=article_ids)
            for article_id, analysis in analysis_map.items():
                grouped.setdefault(article_id, []).append(self._candidate_from_analysis(analysis))
        return grouped

    async def load_selection_map(self, session: AsyncSession, *, article_ids: list[UUID]) -> dict[UUID, ArticleMetadataSelection]:
        """批量加载当前已保存的选择记录。"""
        if not article_ids:
            return {}

        result = await session.scalars(
            select(ArticleMetadataSelection).where(ArticleMetadataSelection.article_id.in_(article_ids))
        )
        return {row.article_id: row for row in result.all()}

    async def resolve_resolutions(
        self,
        session: AsyncSession,
        *,
        article_ids: list[UUID],
        persist_missing: bool = True,
        selected_by: str = "system",
    ) -> dict[UUID, ArticleMetadataResolution]:
        """解析文章版本选择结果。

        当某篇文章没有显式选择记录时，会根据候选评分生成一条自动选择记录，
        这样后续策略生成、画像和回测都能使用稳定的当前版本。
        """
        if not article_ids:
            return {}

        candidate_map = await self.load_candidates(session, article_ids=article_ids)
        selection_map = await self.load_selection_map(session, article_ids=article_ids)
        resolutions: dict[UUID, ArticleMetadataResolution] = {}

        for article_id in article_ids:
            candidates = self._ordered_candidates(candidate_map.get(article_id, []))
            selection_row = selection_map.get(article_id)
            best_candidate = self._select_best_candidate(candidates)

            selected_candidate = None
            selected_mode = None
            selected_by_value = None
            selected_at_value = None
            selection_score = None
            selection_reason = None

            if selection_row is not None:
                selected_mode = selection_row.selection_mode
                selected_by_value = selection_row.selected_by
                selected_at_value = selection_row.selected_at
                selection_score = float(selection_row.selection_score)
                selection_reason = selection_row.selection_reason
                selected_candidate = next(
                    (candidate for candidate in candidates if candidate.schema_version == selection_row.selected_schema_version),
                    None,
                )

            if selected_candidate is None:
                selected_candidate = best_candidate
                selected_mode = "auto"
                selected_by_value = selected_by
                selected_at_value = selection_row.selected_at if selection_row is not None else None
                selection_score = float(best_candidate.score) if best_candidate is not None else None
                selection_reason = self._selection_reason(best_candidate, selected_mode)

                if persist_missing and best_candidate is not None and selection_row is None:
                    selection_row = ArticleMetadataSelection(
                        selection_id=str(uuid4()),
                        article_id=article_id,
                        selected_schema_version=best_candidate.schema_version,
                        recommended_schema_version=best_candidate.schema_version,
                        selection_mode="auto",
                        selection_score=best_candidate.score,
                        recommended_score=best_candidate.score,
                        selection_reason=selection_reason,
                        recommended_reason="自动推荐：当前候选即最优候选",
                        selected_by=selected_by,
                        selected_at=datetime.now(timezone.utc),
                        candidate_versions_json=[candidate.to_dict() for candidate in candidates],
                    )
                    session.add(selection_row)
                    await session.flush()
                    selection_map[article_id] = selection_row
                    selected_at_value = selection_row.selected_at

            recommended_candidate = best_candidate
            recommended_reason = self._selection_reason(recommended_candidate, "auto") if recommended_candidate else None

            effective_candidate = selected_candidate or recommended_candidate
            if selected_candidate is not None:
                effective_reason = selection_reason
                if effective_reason is None and selection_row is not None:
                    effective_reason = selection_row.selection_reason
            else:
                effective_reason = recommended_reason
            effective_score = float(effective_candidate.score) if effective_candidate is not None else None
            warning = None
            if selection_row is not None and selected_candidate is None and best_candidate is not None:
                warning = "当前选择版本在候选集中未找到，已回退到推荐版本"

            resolutions[article_id] = ArticleMetadataResolution(
                article_id=article_id,
                selected_schema_version=selection_row.selected_schema_version if selection_row is not None else (selected_candidate.schema_version if selected_candidate else None),
                selected_by=selected_by_value,
                selected_at=selected_at_value,
                selection_mode=selected_mode,
                selection_score=selection_score,
                selection_reason=selection_reason,
                recommended_schema_version=recommended_candidate.schema_version if recommended_candidate else None,
                recommended_score=float(recommended_candidate.score) if recommended_candidate is not None else None,
                recommended_reason=recommended_reason,
                effective_schema_version=effective_candidate.schema_version if effective_candidate else None,
                effective_score=effective_score,
                effective_reason=effective_reason,
                warning=warning,
                candidates=candidates,
            )

        return resolutions

    async def resolve_resolution(
        self,
        session: AsyncSession,
        *,
        article_id: UUID,
        persist_missing: bool = True,
        selected_by: str = "system",
    ) -> ArticleMetadataResolution:
        """解析单篇文章的版本选择结果。"""
        resolutions = await self.resolve_resolutions(
            session,
            article_ids=[article_id],
            persist_missing=persist_missing,
            selected_by=selected_by,
        )
        return resolutions[article_id]

    async def select_version(
        self,
        session: AsyncSession,
        *,
        article_id: UUID,
        selected_schema_version: str,
        selected_by: str,
        selection_reason: str | None = None,
    ) -> ArticleMetadataResolution:
        """手动设置文章的当前生效 metadata 版本。"""
        candidates = await self.load_candidates(session, article_ids=[article_id])
        candidate_list = candidates.get(article_id, [])
        chosen = next((item for item in candidate_list if item.schema_version == selected_schema_version), None)
        if chosen is None:
            raise ValueError(f"article metadata version not found: article_id={article_id}, schema_version={selected_schema_version}")

        recommended = self._select_best_candidate(candidate_list)
        existing = await self.load_selection_map(session, article_ids=[article_id])
        row = existing.get(article_id)

        effective_reason = selection_reason or "用户手动确认"
        if row is None:
            row = ArticleMetadataSelection(
                selection_id=str(uuid4()),
                article_id=article_id,
                selected_schema_version=selected_schema_version,
                recommended_schema_version=recommended.schema_version if recommended else selected_schema_version,
                selection_mode="manual",
                selection_score=chosen.score,
                recommended_score=float(recommended.score) if recommended is not None else chosen.score,
                selection_reason=effective_reason,
                recommended_reason=self._selection_reason(recommended, "auto"),
                selected_by=selected_by,
                selected_at=datetime.now(timezone.utc),
                candidate_versions_json=[candidate.to_dict() for candidate in candidate_list],
            )
            session.add(row)
        else:
            row.selected_schema_version = selected_schema_version
            row.recommended_schema_version = recommended.schema_version if recommended else selected_schema_version
            row.selection_mode = "manual"
            row.selection_score = chosen.score
            row.recommended_score = float(recommended.score) if recommended is not None else chosen.score
            row.selection_reason = effective_reason
            row.recommended_reason = self._selection_reason(recommended, "auto")
            row.selected_by = selected_by
            row.selected_at = datetime.now(timezone.utc)
            row.candidate_versions_json = [candidate.to_dict() for candidate in candidate_list]

        await session.flush()
        return await self.resolve_resolution(
            session,
            article_id=article_id,
            persist_missing=False,
            selected_by=selected_by,
        )

    async def load_effective_metadata_map(
        self,
        session: AsyncSession,
        *,
        article_ids: list[UUID],
        selected_by: str = "system",
    ) -> dict[UUID, ArticleMetadata]:
        """返回每篇文章当前应使用的 ArticleMetadata 行。"""
        if not article_ids:
            return {}

        resolutions = await self.resolve_resolutions(
            session,
            article_ids=article_ids,
            persist_missing=True,
            selected_by=selected_by,
        )

        result = await session.scalars(
            select(ArticleMetadata)
            .where(ArticleMetadata.article_id.in_(article_ids))
            .where(ArticleMetadata.processed_at.is_not(None))
        )
        grouped: dict[UUID, list[ArticleMetadata]] = {}
        for meta in result.all():
            grouped.setdefault(meta.article_id, []).append(meta)

        effective_map: dict[UUID, ArticleMetadata] = {}
        for article_id, resolution in resolutions.items():
            selected_version = resolution.effective_schema_version
            if not selected_version:
                continue
            candidates = grouped.get(article_id, [])
            chosen = next((meta for meta in candidates if meta.version == selected_version), None)
            if chosen is not None:
                effective_map[article_id] = chosen
                continue
            fallback = self._select_best_candidate([self._candidate_from_metadata(meta) for meta in candidates])
            if fallback is None:
                continue
            chosen = next((meta for meta in candidates if meta.version == fallback.schema_version), None)
            if chosen is not None:
                effective_map[article_id] = chosen

        return effective_map
