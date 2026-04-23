"""策略版本构建任务处理器：build_trader_strategy_version"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from src.common.config import AppConfig
from src.db.session import session_scope
from src.models.article_metadata import ArticleMetadata
from src.models.blog_article import BlogArticle
from src.strategy_library.service import StrategyLibraryService
from src.strategy_library.schemas import StrategyVersionStatus
from src.trader_profile.service import default_profiles_path, load_trader_profiles_file


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

    if not trader_id or not strategy_date_str:
        print(f"[strategy_version] trader_id 或 strategy_date 缺失，跳过: {details}")
        return

    try:
        strategy_date = date.fromisoformat(strategy_date_str)
    except ValueError:
        print(f"[strategy_version] 日期格式错误: {strategy_date_str}")
        return

    # 加载 trader profile
    profiles_path = default_profiles_path(base_dir=Path("."), config=config)
    if not profiles_path.exists():
        print(f"[strategy_version] Trader profiles 文件不存在: {profiles_path}，跳过")
        return

    profiles_file = load_trader_profiles_file(profiles_path)
    profile = profiles_file.profiles_by_trader.get(trader_id)
    if not profile:
        print(f"[strategy_version] 未找到 trader {trader_id} 的 profile，跳过")
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
                print(f"[strategy_version] trader={trader_id} date={strategy_date} 已有发布版本，跳过")
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
        )
        print(
            f"[strategy_version] 已构建 trader={trader_id} date={strategy_date} "
            f"version={draft_version.version_id} recommendations={len(draft_version.recommendations)}"
        )
