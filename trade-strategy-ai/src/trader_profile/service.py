"""Trader Profile Service（扩展版）：支持策略偏好、风险风格、主题偏好、仓位倾向聚合"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from src.common.config import AppConfig
from src.common.utils import read_json, write_json
from src.db.session import session_scope
from src.models.blog_article import BlogArticle
from src.models.trade_log import TradeLog
from src.services.article_metadata_selection_service import ArticleMetadataSelectionService
from src.persona.schemas import PersonaClustersFile
from src.persona.storage import load_persona_clusters_file
from src.trader_profile.schemas import (
    PositionBias,
    RiskStyle,
    StrategyPreference,
    StrategyTimeframe,
    SymbolStat,
    ThemeStat,
    TraderProfile,
    TraderProfilesFile,
)


def default_profiles_path(*, base_dir: Path, config: AppConfig) -> Path:
    """Return the canonical on-disk path for trader profiles."""
    return base_dir / config.runtime.output_dir / "trader_profiles.json"


def _infer_trader_id(*, raw_payload: Any, author_id: Any, config: AppConfig) -> str | None:
    """Resolve a trader id from article payload or crawl source mapping."""
    if not isinstance(raw_payload, dict):
        raw_payload = {}

    tid = raw_payload.get("trader_id")
    if isinstance(tid, str) and tid.strip():
        return tid.strip()

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


def _aggregate_strategy_preference(rules_by_article: list[list[dict[str, Any]]]) -> StrategyPreference | None:
    """从策略规则列表中聚合策略偏好（时间框架、入场类型等）。"""
    timeframe_counter: Counter[str] = Counter()
    entry_types: list[str] = []

    for rules in rules_by_article:
        for rule in rules:
            tf = rule.get("timeframe")
            if isinstance(tf, str) and tf:
                timeframe_counter[tf.lower()] += 1
            et = rule.get("entry_type") or rule.get("rule_type")
            if isinstance(et, str) and et and et not in entry_types:
                entry_types.append(et)

    if not timeframe_counter:
        return None

    # 取最常见 timeframe
    dominant_tf = timeframe_counter.most_common(1)[0][0]
    # 映射到 StrategyTimeframe
    tf_map = {"intraday": StrategyTimeframe.INTRADAY, "swing": StrategyTimeframe.SWING, "position": StrategyTimeframe.POSITION}
    timeframe = tf_map.get(dominant_tf)

    return StrategyPreference(
        timeframe=timeframe,
        entry_type=entry_types[0] if entry_types else None,
        position_style=None,
        max_positions=None,
        avg_holding_period=None,
    )


def _infer_risk_style(rules_by_article: list[list[dict[str, Any]]]) -> RiskStyle:
    """从策略规则中推断风险风格。

    规则：
    - 日内交易为主（>60%）→ CONSERVATIVE（止损严、持仓短）
    - 波段持仓为主（>60%）→ BALANCED
    - 混合无明显偏好 → AGGRESSIVE（高持仓、高杠杆）
    """
    if not rules_by_article:
        return RiskStyle.BALANCED

    intraday_count = 0
    total_count = 0
    avg_position_pct = 0.0
    position_sum = 0.0
    position_count = 0

    for rules in rules_by_article:
        for rule in rules:
            total_count += 1
            tf = str(rule.get("timeframe", "")).lower()
            if tf == "intraday":
                intraday_count += 1
            pct = rule.get("position_size_pct")
            if isinstance(pct, (int, float)):
                position_sum += pct
                position_count += 1

    if total_count == 0:
        return RiskStyle.BALANCED

    intraday_ratio = intraday_count / total_count
    avg_pos = (position_sum / position_count) if position_count > 0 else 10.0

    if intraday_ratio > 0.6 or avg_pos < 8:
        return RiskStyle.CONSERVATIVE
    elif intraday_ratio < 0.3 and avg_pos > 20:
        return RiskStyle.AGGRESSIVE
    return RiskStyle.BALANCED


def _aggregate_position_bias(rules_by_article: list[list[dict[str, Any]]]) -> PositionBias:
    """从策略规则中聚合方向性仓位倾向。"""
    direction_counter: Counter[str] = Counter()
    position_pcts: list[float] = []

    for rules in rules_by_article:
        for rule in rules:
            d = rule.get("direction")
            if isinstance(d, str) and d:
                direction_counter[d.lower()] += 1
            pct = rule.get("position_size_pct")
            if isinstance(pct, (int, float)):
                position_pcts.append(pct)

    dominant_dir = direction_counter.most_common(1)[0][0] if direction_counter else "neutral"
    avg_pct = sum(position_pcts) / len(position_pcts) if position_pcts else None

    return PositionBias(
        directional=dominant_dir,
        max_position_pct=max(position_pcts) if position_pcts else None,
        avg_position_pct=avg_pct,
    )


def _aggregate_theme_preference(concepts_by_article: list[list[dict[str, Any]]]) -> list[ThemeStat]:
    """从概念标签中聚合并统计主题偏好。"""
    # 按 type=theme 过滤
    theme_counter: Counter[str] = Counter()
    for concepts in concepts_by_article:
        for item in concepts:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "theme":
                name = item.get("name")
                if isinstance(name, str) and name.strip():
                    theme_counter[name.strip()] += 1

    return [
        ThemeStat(theme=theme, mentions=count)
        for theme, count in sorted(theme_counter.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    ]


def _aggregate_profile(
    *,
    trader_id: str,
    symbols_by_article: list[list[str]],
    concepts_by_article: list[list[dict[str, Any]]],
    rules_by_article: list[list[dict[str, Any]]],
    clusters_file: PersonaClustersFile | None,
) -> TraderProfile:
    """聚合文章元数据为交易员画像（支持策略偏好、风险风格、主题偏好、仓位倾向）。"""

    # === 原有聚合逻辑 ===
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

    # === 扩展聚合逻辑 ===
    strategy_preference = _aggregate_strategy_preference(rules_by_article) if rules_by_article else None
    risk_style = _infer_risk_style(rules_by_article) if rules_by_article else RiskStyle.BALANCED
    theme_preference = _aggregate_theme_preference(concepts_by_article)
    position_bias = _aggregate_position_bias(rules_by_article) if rules_by_article else PositionBias(directional="neutral")

    return TraderProfile(
        trader_id=trader_id,
        updated_at=datetime.now(UTC),
        top_symbols=top_symbols,
        style_cluster_ids=style_cluster_ids,
        concept_tags=concept_tags,
        strategy_preference=strategy_preference,
        risk_style=risk_style,
        theme_preference=theme_preference,
        position_bias=position_bias,
        evidence={
            "articles_scanned": len(symbols_by_article) if symbols_by_article else len(concepts_by_article),
            "symbols_mentioned": sum(s.mentions for s in top_symbols),
            "clusters": len(style_cluster_ids),
            "themes_found": len(theme_preference),
        },
    )


def _build_trade_account_map(config: AppConfig) -> dict[str, str]:
    """根据配置里的账户绑定关系构建 account_id → trader_id 映射。"""
    account_map: dict[str, str] = {}
    for trader in config.traders:
        if not isinstance(trader.trader_id, str) or not trader.trader_id.strip():
            continue
        trader_id = trader.trader_id.strip()
        for account_id in trader.trade_log_sources.account_ids:
            if isinstance(account_id, str) and account_id.strip():
                account_map[account_id.strip()] = trader_id
    return account_map


async def build_trader_profiles(
    *,
    config: AppConfig,
    base_dir: Path,
    clusters_path: str | Path | None = None,
    max_articles_per_trader: int = 50,
) -> TraderProfilesFile:
    """Build a compact profile for each configured trader from DB data（扩展版）。"""

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
    trader_ids = [t.trader_id for t in config.traders if isinstance(t.trader_id, str) and t.trader_id.strip()]
    metadata_selection_service = ArticleMetadataSelectionService()

    async with session_scope() as session:
        max_per_trader = max(1, int(max_articles_per_trader))
        window = max_per_trader * max(1, len(trader_ids)) * 3

        rows = await session.execute(
            select(
                BlogArticle.id,
                BlogArticle.author_id,
                BlogArticle.raw_payload,
            )
            .order_by(BlogArticle.crawled_at.desc())
            .limit(window),
        )

        article_rows = rows.all()
        effective_metadata_map = await metadata_selection_service.load_effective_metadata_map(
            session,
            article_ids=[row[0] for row in article_rows],
            selected_by="system",
        )

        symbols_map: dict[str, list[list[str]]] = {tid: [] for tid in trader_ids}
        concepts_map: dict[str, list[list[dict[str, Any]]]] = {tid: [] for tid in trader_ids}
        rules_map: dict[str, list[list[dict[str, Any]]]] = {tid: [] for tid in trader_ids}
        article_rows_by_trader: dict[str, int] = {tid: 0 for tid in trader_ids}
        trade_log_rows_by_trader: dict[str, int] = {tid: 0 for tid in trader_ids}
        account_map = _build_trade_account_map(config)

        for article_id, author_id, raw_payload in article_rows:
            tid = _infer_trader_id(raw_payload=raw_payload, author_id=author_id, config=config)
            if not tid or tid not in symbols_map:
                continue
            if len(symbols_map[tid]) >= max_per_trader:
                continue

            meta = effective_metadata_map.get(article_id)
            if meta is None or meta.processed_at is None:
                continue

            symbols_map[tid].append(meta.trading_symbols if isinstance(meta.trading_symbols, list) else [])
            concepts_map[tid].append(meta.extracted_concepts if isinstance(meta.extracted_concepts, list) else [])
            rules_map[tid].append(meta.strategy_rules if isinstance(meta.strategy_rules, list) else [])
            article_rows_by_trader[tid] += 1

        trade_account_ids = list(account_map.keys())
        if trade_account_ids:
            trade_rows = await session.execute(
                select(
                    TradeLog.account_id,
                    TradeLog.symbol,
                )
                .where(TradeLog.account_id.in_(trade_account_ids))
                .order_by(TradeLog.executed_at.desc())
                .limit(window),
            )
            for account_id, symbol in trade_rows.all():
                tid = account_map.get(account_id)
                if not tid or tid not in symbols_map:
                    continue
                if isinstance(symbol, str) and symbol.strip():
                    symbols_map[tid].append([symbol.strip()])
                    trade_log_rows_by_trader[tid] += 1

        for tid in trader_ids:
            profile = _aggregate_profile(
                trader_id=tid,
                symbols_by_article=symbols_map[tid],
                concepts_by_article=concepts_map[tid],
                rules_by_article=rules_map[tid],
                clusters_file=clusters_file,
            )
            profile.evidence["articles_scanned"] = article_rows_by_trader[tid]
            profile.evidence["trade_logs_scanned"] = trade_log_rows_by_trader[tid]
            profiles[tid] = profile

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
