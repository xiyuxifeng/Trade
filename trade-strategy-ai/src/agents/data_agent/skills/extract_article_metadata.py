from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from src.common.config import AppConfig
from src.common.utils import append_jsonl, ensure_dir
from src.db.session import session_scope
from src.llm.client import LLMClient, LLMError, from_env_and_config
from src.models.article_metadata import ArticleMetadata
from src.models.blog_article import BlogArticle
from src.persona.schemas import ArticlePrecondition, ArticleStrategyRule
from src.schemas.contracts import AgentTask


@dataclass(slots=True)
class ExtractStats:
    scanned: int = 0
    extracted: int = 0
    skipped: int = 0
    failed: int = 0
    generated_tasks: int = 0


def _read_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _now_utc() -> datetime:
    return datetime.now(UTC)


def default_pending_tasks_path(*, base_dir: Path) -> Path:
    return base_dir / "data" / "processed" / "pipeline" / "pending_tasks.jsonl"


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return None


def _clamp(value: float | None, lo: float, hi: float) -> float | None:
    if value is None:
        return None
    return max(lo, min(hi, value))


def _validate_rules(rules: Any, *, source_url: str | None, published_at: datetime | None) -> list[dict[str, Any]]:
    if not isinstance(rules, list):
        return []

    out: list[dict[str, Any]] = []
    for item in rules:
        if not isinstance(item, dict):
            continue
        enriched = {**item}
        enriched.setdefault("schema_version", "v0")
        enriched.setdefault("source_url", source_url)
        enriched.setdefault("published_at", published_at)

        # action 是必填：缺失时给一个最保守的占位
        if "action" not in enriched:
            rule_type = str(enriched.get("rule_type") or "").lower()
            if rule_type == "exit":
                enriched["action"] = {"type": "exit", "side": "sell", "order": "market", "price": None, "params": {}}
            elif rule_type == "filter":
                enriched["action"] = {"type": "filter", "params": {}}
            else:
                enriched["action"] = {"type": "enter", "side": "buy", "order": "limit", "price": {"var": "close"}, "params": {}}

        try:
            rule = ArticleStrategyRule.model_validate(enriched)
        except Exception:
            continue
        out.append(rule.model_dump())
    return out


def _validate_preconditions(
    preconditions: Any,
    *,
    source_url: str | None,
    published_at: datetime | None,
) -> list[dict[str, Any]]:
    if not isinstance(preconditions, list):
        return []

    out: list[dict[str, Any]] = []
    for item in preconditions:
        if not isinstance(item, dict):
            continue
        enriched = {**item}
        enriched.setdefault("schema_version", "v0")
        enriched.setdefault("source_url", source_url)
        enriched.setdefault("published_at", published_at)
        try:
            pre = ArticlePrecondition.model_validate(enriched)
        except Exception:
            continue
        out.append(pre.model_dump())
    return out


async def _extract_one(
    *,
    client: LLMClient,
    prompts_dir: Path,
    article: BlogArticle,
) -> dict[str, Any]:
    concept_p = _read_prompt(prompts_dir / "concept_extraction.md")
    rule_p = _read_prompt(prompts_dir / "rule_extraction.md")
    pre_p = _read_prompt(prompts_dir / "precondition_extraction.md")

    system_prompt = "\n\n".join([
        "你必须只输出严格 JSON，不要输出 Markdown。",
        concept_p,
        rule_p,
        pre_p,
        "最终输出必须合并为一个 JSON 对象，包含字段：extracted_concepts, trading_symbols, strategy_rules, preconditions, comment_insights, sentiment_score, confidence_score。",
    ])

    # 控制输入长度：避免把超长评论一次性塞爆
    content = article.content_text.strip()
    if len(content) > 12000:
        content = content[:12000]

    user_prompt = json.dumps(
        {
            "title": article.title,
            "source_url": article.source_url,
            "author_name": article.author_name,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "content_text": content,
        },
        ensure_ascii=False,
    )

    return await client.complete_json(system_prompt=system_prompt, user_prompt=user_prompt)


async def extract_and_store_metadata(
    *,
    config: AppConfig,
    base_dir: Path,
    limit: int = 20,
    pending_tasks_path: Path | None = None,
) -> ExtractStats:
    prompts_dir = base_dir / "prompts"
    if not prompts_dir.exists():
        raise FileNotFoundError(f"prompts dir not found: {prompts_dir}")

    llm_cfg = from_env_and_config(
        provider=config.llm.provider,
        model=config.llm.model,
        url=config.llm.url,
        api_key=config.llm.api_key,
    )
    client = LLMClient(llm_cfg)

    stats = ExtractStats()
    pending_path = pending_tasks_path or default_pending_tasks_path(base_dir=base_dir)
    ensure_dir(pending_path.parent)

    async with session_scope() as session:
        rows = await session.execute(
            select(BlogArticle, ArticleMetadata)
            .join(ArticleMetadata, ArticleMetadata.article_id == BlogArticle.id)
            .where(ArticleMetadata.processed_at.is_(None))
            .order_by(BlogArticle.crawled_at.desc())
            .limit(limit)
        )

        for article, meta in rows.all():
            stats.scanned += 1

            if not article.content_text or len(article.content_text.strip()) < 80:
                stats.skipped += 1
                continue

            try:
                raw = await _extract_one(client=client, prompts_dir=prompts_dir, article=article)
                mode = "llm"
            except LLMError as exc:
                raw = {
                    "extracted_concepts": [],
                    "trading_symbols": [],
                    "strategy_rules": [],
                    "preconditions": [],
                    "comment_insights": [],
                    "sentiment_score": None,
                    "confidence_score": None,
                    "_fallback": {"error": str(exc)},
                }
                mode = "fallback"
            except Exception as exc:  # noqa: BLE001
                stats.failed += 1
                meta.raw_llm_output = {"error": str(exc)}
                continue

            rules = _validate_rules(raw.get("strategy_rules"), source_url=article.source_url, published_at=article.published_at)
            preconds = _validate_preconditions(raw.get("preconditions"), source_url=article.source_url, published_at=article.published_at)

            meta.extracted_concepts = raw.get("extracted_concepts") if isinstance(raw.get("extracted_concepts"), list) else []
            meta.trading_symbols = raw.get("trading_symbols") if isinstance(raw.get("trading_symbols"), list) else []
            meta.strategy_rules = rules
            meta.preconditions = preconds
            meta.comment_insights = raw.get("comment_insights") if isinstance(raw.get("comment_insights"), list) else []
            meta.sentiment_score = _clamp(_safe_float(raw.get("sentiment_score")), -1.0, 1.0)
            meta.confidence_score = _clamp(_safe_float(raw.get("confidence_score")), 0.0, 1.0)
            meta.raw_llm_output = {"mode": mode, "raw": raw}
            meta.processed_at = _now_utc()

            stats.extracted += 1

            # 触发后续聚类/记忆刷新（先落盘待办）
            task = AgentTask(
                type="article_metadata_extracted",
                title="Article metadata extracted",
                trader_id=(article.raw_payload.get("trader_id") if isinstance(article.raw_payload, dict) else None),
                details={
                    "article_id": str(article.id),
                    "source_url": article.source_url,
                    "mode": mode,
                    "strategy_rules": len(rules),
                    "preconditions": len(preconds),
                },
            )
            append_jsonl(pending_path, task.model_dump())
            stats.generated_tasks += 1

        await session.flush()

    return stats
