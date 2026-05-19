"""策略版本构建任务处理器：build_trader_strategy_version"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from src.common.config import AppConfig
from src.common.logger import get_logger
from src.common.paths import resolve_project_path
from src.db.session import session_scope
from src.db.repositories.market_regime_repository import MarketRegimeRepository
from src.db.repositories.rule_applicability_repository import RuleApplicabilityRepository
from src.models.article_metadata import ArticleMetadata
from src.models.blog_article import BlogArticle
from src.strategy_library.service import StrategyLibraryService
from src.strategy_library.schemas import StrategyVersionStatus
from src.trader_profile.service import default_profiles_path, load_trader_profiles_file

logger = get_logger(__name__)


async def handle_build_trader_strategy_version(
    details: dict[str, Any],
    *,
    config: AppConfig,
) -> None:
    """构建并保存指定交易员的策略版本（draft）。

    Details 参数：
        trader_id: str       — 交易员 ID
        strategy_date: str   — 策略日期（YYYY-MM-DD 格式）
        force: bool          — 是否强制重建（默认 False，跳过已有发布版本）

    流程：
        1. 加载 trader profile（从 JSON 文件）
        2. 查询该交易员最近的文章证据
        3. 使用 StrategyLibraryService 构建 draft 版本
        4. 保存到数据库
    """
    trader_id: str | None = details.get("trader_id")
    strategy_date_str: str | None = details.get("strategy_date")
    force: bool = details.get("force", False)
    regime_selection = details.get("regime_selection")
    selection_context = details.get("selection_context") or {}

    if not trader_id or not strategy_date_str:
        logger.warning(
            "策略版本构建跳过: trader_id或strategy_date缺失, details=%s",
            details,
        )
        return

    try:
        strategy_date = date.fromisoformat(strategy_date_str)
    except ValueError:
        logger.warning(
            "策略版本构建跳过: 日期格式错误, strategy_date=%s",
            strategy_date_str,
        )
        return

    # 加载 trader profile
    profiles_path = default_profiles_path(base_dir=resolve_project_path("."), config=config)
    if not profiles_path.exists():
        logger.warning(
            "策略版本构建跳过: Trader profiles文件不存在, path=%s",
            profiles_path,
        )
        return

    profiles_file = load_trader_profiles_file(profiles_path)
    profile = profiles_file.profiles_by_trader.get(trader_id)
    if not profile:
        logger.warning(
            "策略版本构建跳过: 未找到trader的profile, trader=%s",
            trader_id,
        )
        return

    service = StrategyLibraryService()

    # 检查是否已有发布版本（force=False 时跳过）
    if not force:
        async with session_scope() as session:
            existing = await service.get_current_released_version(
                session=session,
                trader_id=trader_id,
                strategy_date=strategy_date,
            )
            if existing is not None:
                logger.info(
                    "策略版本构建跳过（已有发布版本）: trader=%s, date=%s",
                    trader_id,
                    strategy_date,
                )
                return

    # 查询文章证据
    async with session_scope() as session:
        # 查找该交易员最近的 N 篇文章
        rows = await session.execute(
            select(
                BlogArticle.id,
                BlogArticle.raw_payload,
                ArticleMetadata.trading_symbols,
                ArticleMetadata.sentiment_score,
                ArticleMetadata.confidence_score,
            )
            .join(ArticleMetadata, ArticleMetadata.article_id == BlogArticle.id)
            .where(ArticleMetadata.processed_at.is_not(None))
            .order_by(BlogArticle.crawled_at.desc())
            .limit(50)
        )

        # 按 trader_id 过滤文章
        articles = []
        for row in rows.all():
            article_id, raw_payload, symbols, sentiment, confidence = row
            # 从 raw_payload 获取 trader_id
            payload_trader_id = None
            if isinstance(raw_payload, dict):
                payload_trader_id = raw_payload.get("trader_id")
            if payload_trader_id != trader_id:
                continue

            class _ArticleEvidence:
                """ArticleEvidence 实现（用于 builder）"""
                def __init__(self, article_id: str, symbols: list, sentiment: Any, confidence: Any):
                    self.article_id = article_id
                    self.trading_symbols = symbols if isinstance(symbols, list) else []
                    self.sentiment_score = float(sentiment) if sentiment is not None else None
                    self.confidence_score = float(confidence) if confidence is not None else None
                    self.rationale = None

            articles.append(_ArticleEvidence(
                article_id=str(article_id),
                symbols=symbols if isinstance(symbols, list) else [],
                sentiment=sentiment,
                confidence=confidence,
            ))

        # 构建并保存 draft 版本
        draft_version = await service.build_and_save_draft(
            session=session,
            trader_id=trader_id,
            strategy_date=strategy_date,
            profile=profile,
            source_articles=articles,
            regime_selection=regime_selection if isinstance(regime_selection, dict) else None,
        )

        snapshot_id = selection_context.get("snapshot_id")
        market_regime_version = selection_context.get("market_regime_version") or "market-regime-v3"
        applicability_profile_version = selection_context.get("applicability_profile_version")
        selected_by = str(selection_context.get("selected_by") or "web")

        if snapshot_id:
            from src.services.regime_rule_selection_service import RegimeRuleSelectionService

            market_regime_repo = MarketRegimeRepository()
            applicability_repo = RuleApplicabilityRepository()
            selection_service = RegimeRuleSelectionService()

            regime = await market_regime_repo.get_by_snapshot_and_version(
                session,
                str(snapshot_id),
                str(market_regime_version),
            )
            if regime is None:
                logger.warning(
                    "策略版本构建跳过 regime-aware selection: market regime not found, snapshot_id=%s, regime_version=%s",
                    snapshot_id,
                    market_regime_version,
                )
            else:
                profiles = await applicability_repo.list_profiles(
                    session,
                    profile_version=str(applicability_profile_version) if applicability_profile_version else None,
                    limit=None,
                )
                selection_result = await selection_service.build_regime_rule_selection(
                    strategy_version=draft_version,
                    trader_profile=profile,
                    market_regime=regime,
                    applicability_profiles=profiles,
                    selected_by=selected_by,
                    applicability_profile_version=str(applicability_profile_version) if applicability_profile_version else None,
                )
                selection_payload = selection_result.payload.get("selection") if isinstance(selection_result.payload, dict) else None
                if isinstance(selection_payload, dict):
                    draft_version = replace(draft_version, regime_selection=selection_payload)
                    await service.save_version(session=session, version=draft_version)
                    logger.info(
                        "策略版本 regime-aware selection 已保存: trader=%s, date=%s, version=%s, selected=%d, blocked=%d",
                        trader_id,
                        strategy_date,
                        draft_version.version_id,
                        len(selection_payload.get("selected_rules", [])),
                        len(selection_payload.get("blocked_rules", [])),
                    )

        logger.info(
            "策略版本草稿已构建: trader=%s, date=%s, version=%s, recommendations=%d",
            trader_id,
            strategy_date,
            draft_version.version_id,
            len(draft_version.recommendations),
        )
