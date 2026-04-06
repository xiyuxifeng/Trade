from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from src.common.config import AppConfig
from src.common.utils import read_json, write_json
from src.db.session import session_scope
from src.models.article_metadata import ArticleMetadata
from src.models.blog_article import BlogArticle
from src.persona.schemas import PersonaClustersFile
from src.persona.storage import load_persona_clusters_file
from src.trader_profile.schemas import SymbolStat, TraderProfile, TraderProfilesFile


def default_profiles_path(*, base_dir: Path, config: AppConfig) -> Path:
    """Return the canonical on-disk path for trader profiles."""
    # Keep artifacts under storage.output_dir to match existing report outputs.
    return base_dir / config.storage.output_dir / "trader_profiles.json"


def _infer_trader_id(*, raw_payload: Any, author_id: Any, config: AppConfig) -> str | None:
    """Resolve a trader id from article payload or crawl source mapping."""
    if not isinstance(raw_payload, dict):
        raw_payload = {}

    tid = raw_payload.get("trader_id")
    if isinstance(tid, str) and tid.strip():
        return tid.strip()

    # fallback: use crawl.sources mapping author_id -> trader_id
    if isinstance(author_id, str) and author_id.strip():
        for src in config.crawl.sources:
            if src.author_id and src.author_id == author_id and src.trader_id:
                return src.trader_id

    return None


def _collect_concept_tags(concepts: list[dict[str, Any]]) -> list[str]:
    """Flatten concept objects into a small, de-duplicated tag list."""
    tags: list[str] = []
    seen: set[str] = set()
    for item in concepts:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str):
            continue
        tag = name.strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        tags.append(tag)
        if len(tags) >= 20:
            break
    return tags


def _aggregate_profile(
    *,
    trader_id: str,
    symbols_by_article: list[list[str]],
    concepts_by_article: list[list[dict[str, Any]]],
    clusters_file: PersonaClustersFile | None,
) -> TraderProfile:
    """Aggregate article metadata into one compact trader profile."""
    symbol_counter: Counter[str] = Counter()
    for symbols in symbols_by_article:
        for sym in symbols:
            if isinstance(sym, str) and sym.strip():
                symbol_counter[sym.strip()] += 1

    top_symbols = [
        SymbolStat(symbol=sym, mentions=count)
        for sym, count in sorted(symbol_counter.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    ]

    concept_counter: Counter[str] = Counter()
    for concepts in concepts_by_article:
        for tag in _collect_concept_tags(concepts):
            concept_counter[tag] += 1
    concept_tags = [tag for tag, _ in sorted(concept_counter.items(), key=lambda kv: (-kv[1], kv[0]))[:20]]

    style_cluster_ids: list[str] = []
    if clusters_file is not None:
        clusters = clusters_file.clusters_by_trader.get(trader_id, [])
        for c in clusters:
            if isinstance(c.cluster_id, str) and c.cluster_id.strip():
                style_cluster_ids.append(c.cluster_id.strip())

    return TraderProfile(
        trader_id=trader_id,
        updated_at=datetime.now(UTC),
        top_symbols=top_symbols,
        style_cluster_ids=style_cluster_ids,
        concept_tags=concept_tags,
        evidence={
            "articles_scanned": len(symbols_by_article),
            "symbols_mentioned": sum(s.mentions for s in top_symbols),
            "clusters": len(style_cluster_ids),
        },
    )


async def build_trader_profiles(
    *,
    config: AppConfig,
    base_dir: Path,
    clusters_path: str | Path | None = None,
    max_articles_per_trader: int = 50,
) -> TraderProfilesFile:
    """Build a compact profile for each configured trader from DB data."""

    full_clusters_path: Path | None = None
    if clusters_path is not None:
        full_clusters_path = Path(clusters_path)
        if not full_clusters_path.is_absolute():
            full_clusters_path = base_dir / full_clusters_path
    elif config.persona.clusters_path:
        p = Path(config.persona.clusters_path)
        full_clusters_path = p if p.is_absolute() else (base_dir / p)

    clusters_file: PersonaClustersFile | None = None
    if full_clusters_path is not None and full_clusters_path.exists():
        clusters_file = load_persona_clusters_file(full_clusters_path)

    profiles: dict[str, TraderProfile] = {}

    # Start with config.traders so the output is stable and includes traders
    # even if they have no data yet.
    trader_ids = [t.trader_id for t in config.traders if isinstance(t.trader_id, str) and t.trader_id.strip()]

    async with session_scope() as session:
        # Fetch a recent window then fill each trader up to `max_articles_per_trader`.
        # This avoids dialect-specific JSON filtering while still keeping work bounded.
        max_per_trader = max(1, int(max_articles_per_trader))
        window = max_per_trader * max(1, len(trader_ids)) * 3

        rows = await session.execute(
            select(
                BlogArticle.author_id,
                BlogArticle.raw_payload,
                ArticleMetadata.trading_symbols,
                ArticleMetadata.extracted_concepts,
            )
            .join(ArticleMetadata, ArticleMetadata.article_id == BlogArticle.id)
            .where(ArticleMetadata.processed_at.is_not(None))
            .order_by(BlogArticle.crawled_at.desc())
            .limit(window),
        )

        symbols_map: dict[str, list[list[str]]] = {tid: [] for tid in trader_ids}
        concepts_map: dict[str, list[list[dict[str, Any]]]] = {tid: [] for tid in trader_ids}

        for author_id, raw_payload, symbols, concepts in rows.all():
            tid = _infer_trader_id(raw_payload=raw_payload, author_id=author_id, config=config)
            if not tid or tid not in symbols_map:
                continue
            if len(symbols_map[tid]) >= max_per_trader:
                continue

            symbols_map[tid].append(symbols if isinstance(symbols, list) else [])
            concepts_map[tid].append(concepts if isinstance(concepts, list) else [])

        for tid in trader_ids:
            profiles[tid] = _aggregate_profile(
                trader_id=tid,
                symbols_by_article=symbols_map[tid],
                concepts_by_article=concepts_map[tid],
                clusters_file=clusters_file,
            )

    return TraderProfilesFile(updated_at=datetime.now(UTC), profiles_by_trader=profiles)


def write_trader_profiles_file(*, path: str | Path, data: TraderProfilesFile) -> Path:
    """Persist trader profiles as JSON for later CLI and Agent reuse."""

    p = Path(path)
    write_json(p, data.model_dump(mode="json"))
    return p


def load_trader_profiles_file(path: str | Path) -> TraderProfilesFile:
    """Load a trader profile bundle from disk."""

    payload = read_json(path)
    return TraderProfilesFile.model_validate(payload)
