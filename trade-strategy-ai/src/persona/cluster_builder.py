from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from src.common.config import AppConfig
from src.db.session import session_scope
from src.models.article_metadata import ArticleMetadata
from src.models.blog_article import BlogArticle
from src.persona.schemas import (
    ClusterApplicability,
    InstrumentFocus,
    PersonaClustersFile,
    StyleCluster,
)
from src.persona.schemas import ArticlePrecondition, ArticleStrategyRule
from src.persona.storage import write_persona_clusters_file


@dataclass(slots=True)
class BuildClustersStats:
    scanned_articles: int = 0
    used_articles: int = 0
    clusters_built: int = 0


def _infer_trader_id(*, article: BlogArticle, config: AppConfig) -> str | None:
    if isinstance(article.raw_payload, dict):
        tid = article.raw_payload.get("trader_id")
        if isinstance(tid, str) and tid.strip():
            return tid.strip()

    # fallback: use crawl.sources mapping author_id -> trader_id
    for src in config.crawl.sources:
        if src.author_id and src.author_id == article.author_id and src.trader_id:
            return src.trader_id

    return None


def _safe_focus(value: Any) -> InstrumentFocus:
    try:
        if isinstance(value, str):
            return InstrumentFocus(value)
    except Exception:
        return InstrumentFocus.mixed
    return InstrumentFocus.mixed


def _safe_rule(item: dict[str, Any]) -> ArticleStrategyRule | None:
    try:
        return ArticleStrategyRule.model_validate(item)
    except Exception:
        return None


def _safe_pre(item: dict[str, Any]) -> ArticlePrecondition | None:
    try:
        return ArticlePrecondition.model_validate(item)
    except Exception:
        return None


async def build_clusters_from_db(
    *,
    config: AppConfig,
    dest: Path,
    max_articles: int | None = None,
) -> tuple[Path, BuildClustersStats]:
    stats = BuildClustersStats()

    rules_by_trader_focus: dict[str, dict[InstrumentFocus, list[ArticleStrategyRule]]] = defaultdict(
        lambda: defaultdict(list)
    )
    pres_by_trader_focus: dict[str, dict[InstrumentFocus, list[ArticlePrecondition]]] = defaultdict(
        lambda: defaultdict(list)
    )
    evidence_by_trader: dict[str, list[dict[str, Any]]] = defaultdict(list)
    article_count_by_trader: dict[str, int] = defaultdict(int)

    async with session_scope() as session:
        stmt = (
            select(BlogArticle, ArticleMetadata)
            .join(ArticleMetadata, ArticleMetadata.article_id == BlogArticle.id)
            .where(ArticleMetadata.processed_at.is_not(None))
            .order_by(ArticleMetadata.processed_at.desc())
        )
        if max_articles is not None:
            stmt = stmt.limit(max_articles)

        rows = await session.execute(stmt)

        for article, meta in rows.all():
            stats.scanned_articles += 1
            trader_id = _infer_trader_id(article=article, config=config)
            if not trader_id:
                continue

            # 仅当有规则/前置条件时才用于聚类
            if not meta.strategy_rules and not meta.preconditions:
                continue

            stats.used_articles += 1
            article_count_by_trader[trader_id] += 1
            evidence_by_trader[trader_id].append(
                {
                    "source_url": article.source_url,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "processed_at": meta.processed_at.isoformat() if meta.processed_at else None,
                }
            )

            for r in meta.strategy_rules:
                if not isinstance(r, dict):
                    continue
                rule = _safe_rule(r)
                if rule is None:
                    continue
                rules_by_trader_focus[trader_id][_safe_focus(rule.instrument_focus.value)].append(rule)

            for p in meta.preconditions:
                if not isinstance(p, dict):
                    continue
                pre = _safe_pre(p)
                if pre is None:
                    continue
                pres_by_trader_focus[trader_id][_safe_focus(pre.instrument_focus.value)].append(pre)

    clusters_by_trader: dict[str, list[StyleCluster]] = {}

    for trader in config.traders:
        tid = trader.trader_id
        clusters: list[StyleCluster] = []

        focuses = set(rules_by_trader_focus.get(tid, {}).keys()) | set(pres_by_trader_focus.get(tid, {}).keys())
        if not focuses:
            clusters_by_trader[tid] = []
            continue

        for focus in sorted(focuses, key=lambda x: x.value):
            rules = rules_by_trader_focus.get(tid, {}).get(focus, [])
            pres = pres_by_trader_focus.get(tid, {}).get(focus, [])
            if not rules and not pres:
                continue

            confs = [float(r.confidence) for r in rules if r.confidence is not None]
            avg_conf = sum(confs) / len(confs) if confs else 0.5

            count_articles = article_count_by_trader.get(tid, 0)
            activity = min(1.0, count_articles / 20.0)

            cluster = StyleCluster(
                cluster_id=f"{tid}:{focus.value}:v0",
                label=f"{trader.display_name} {focus.value} (v0)",
                instrument_focus=focus,
                applicability=ClusterApplicability(),
                rules=[r for r in rules[:30]],
                preconditions=[p for p in pres[:30]],
                activity_score=activity,
                coherence_score=0.5,
                confidence_score=float(avg_conf),
                evidence_refs=evidence_by_trader.get(tid, [])[:50],
            )
            clusters.append(cluster)
            stats.clusters_built += 1

        clusters_by_trader[tid] = clusters

    file = PersonaClustersFile(
        generated_at=datetime.utcnow(),
        clusters_by_trader=clusters_by_trader,
    )

    written = write_persona_clusters_file(path=dest, data=file)
    return written, stats
