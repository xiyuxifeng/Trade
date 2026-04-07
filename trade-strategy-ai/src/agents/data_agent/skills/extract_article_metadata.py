from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
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


class ExtractErrorType(StrEnum):
    """LLM 抽取错误分类"""
    NETWORK = "network"      # 网络请求失败
    JSON_PARSE = "json_parse"  # JSON 解析失败
    SCHEMA_VALIDATION = "schema_validation"  # Schema 校验失败（输出不合规）
    QUALITY = "quality"    # 输出质量不达标（空结果、置信度低）


@dataclass(frozen=True, slots=True)
class ExtractErrorRecord:
    """错误记录"""
    article_id: str
    source_url: str | None
    error_type: str
    error_message: str
    raw_output: dict[str, Any] | None
    timestamp: str


@dataclass(slots=True)
class ExtractStats:
    scanned: int = 0
    extracted: int = 0
    skipped: int = 0
    failed: int = 0
    generated_tasks: int = 0
    llm_calls: int = 0
    fallback_calls: int = 0
    # P2-LLM-001: 合规率统计
    schema_valid_rules: int = 0
    schema_invalid_rules: int = 0
    schema_valid_preconds: int = 0
    schema_invalid_preconds: int = 0
    # P2-LLM-002: 错误分类统计
    errors_by_type: dict[str, int] = None

    def __post_init__(self):
        if self.errors_by_type is None:
            object.__setattr__(self, 'errors_by_type', {t.value: 0 for t in ExtractErrorType})


_STOCK_CODE_RE = re.compile(r"\b([0-9]{6})\.(SZ|SH|BJ)\b")
_POSITIVE_WORDS = ("涨", "盈利", "买入", "做多", "突破", "拉升", "看好", "多头", "关注", "试错", "扫板", "打板")
_NEGATIVE_WORDS = ("下跌", "亏损", "卖出", "做空", "止损", "看空", "空头", "观望", "谨慎", "风险", "取关", "止盈", "板砸", "割肉")


def _read_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _now_utc() -> datetime:
    return datetime.now(UTC)


def default_pending_tasks_path(*, base_dir: Path) -> Path:
    return base_dir / "data" / "processed" / "pipeline" / "pending_tasks.jsonl"


def default_error_log_path(*, base_dir: Path) -> Path:
    return base_dir / "data" / "processed" / "llm_extraction_errors.jsonl"


def _record_error(
    *,
    article_id: str,
    source_url: str | None,
    error_type: ExtractErrorType,
    error_message: str,
    raw_output: dict[str, Any] | None,
    error_log_path: Path,
) -> None:
    """Write an error record to the JSONL error log."""
    record = ExtractErrorRecord(
        article_id=article_id,
        source_url=source_url,
        error_type=error_type.value,
        error_message=error_message,
        raw_output=raw_output,
        timestamp=_now_utc().isoformat(),
    )
    append_jsonl(error_log_path, asdict(record))


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


def _heuristic_extract(article: BlogArticle) -> dict[str, Any]:
    """LLM 不可用时，用轻量规则提取最基础的 metadata。"""
    content = article.content_text or ""
    raw_payload = article.raw_payload if isinstance(article.raw_payload, dict) else {}

    symbols: list[str] = []
    for match in _STOCK_CODE_RE.finditer(content):
        code, exchange = match.group(1), match.group(2)
        symbol = f"{code}.{exchange}"
        if symbol not in symbols:
            symbols.append(symbol)
        if len(symbols) >= 5:
            break

    concepts: list[dict[str, str]] = []
    trader_id = raw_payload.get("trader_id")
    if isinstance(trader_id, str) and trader_id.strip():
        concepts.append(
            {
                "name": trader_id.strip(),
                "type": "trader",
                "evidence": f"来源: {article.author_name or trader_id.strip()}",
            }
        )
    elif article.author_name:
        concepts.append(
            {
                "name": article.author_name,
                "type": "author",
                "evidence": "作者标注",
            }
        )

    pos_count = sum(content.count(word) for word in _POSITIVE_WORDS)
    neg_count = sum(content.count(word) for word in _NEGATIVE_WORDS)
    total = pos_count + neg_count
    sentiment = (pos_count - neg_count) / total if total else 0.0

    return {
        "extracted_concepts": concepts,
        "trading_symbols": symbols,
        "strategy_rules": [],
        "preconditions": [],
        "comment_insights": [],
        "sentiment_score": sentiment,
        "confidence_score": 0.1,
    }


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
        out.append(rule.model_dump(mode="json"))
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
        out.append(pre.model_dump(mode="json"))
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
        (
            "输出格式要求：\n"
            "{\n"
            '  "extracted_concepts": [...],   // 0-10 条，太多说明提取不精准\n'
            '  "trading_symbols": [...],       // 0-5 个，优先提取有把握的\n'
            '  "strategy_rules": [...],        // 0-5 条，宁缺毋滥\n'
            '  "preconditions": [...],         // 0-5 条\n'
            '  "comment_insights": [...],      // 0-3 条，从评论中提炼\n'
            '  "sentiment_score": float,       // -1.0 ~ 1.0\n'
            '  "confidence_score": float       // 0.0 ~ 1.0\n'
            "}"
        ),
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
    error_log_path = default_error_log_path(base_dir=base_dir)
    ensure_dir(error_log_path.parent)

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

            error_message: str | None = None
            if not client.is_enabled():
                raw = _heuristic_extract(article)
                mode = "fallback_heuristic"
                stats.fallback_calls += 1
            else:
                stats.llm_calls += 1
                try:
                    raw = await _extract_one(client=client, prompts_dir=prompts_dir, article=article)
                    mode = "llm"
                except LLMError as exc:
                    raw = _heuristic_extract(article)
                    mode = "fallback_on_error"
                    error_message = str(exc)
                    stats.failed += 1
                    stats.fallback_calls += 1
                    stats.errors_by_type[ExtractErrorType.NETWORK.value] += 1
                    _record_error(
                        article_id=str(article.id),
                        source_url=article.source_url,
                        error_type=ExtractErrorType.NETWORK,
                        error_message=error_message,
                        raw_output=None,
                        error_log_path=error_log_path,
                    )
                except Exception as exc:  # noqa: BLE001
                    stats.failed += 1
                    error_msg = str(exc)
                    stats.errors_by_type[ExtractErrorType.QUALITY.value] += 1
                    meta.raw_llm_output = {"error": error_msg}
                    _record_error(
                        article_id=str(article.id),
                        source_url=article.source_url,
                        error_type=ExtractErrorType.QUALITY,
                        error_message=error_msg,
                        raw_output=None,
                        error_log_path=error_log_path,
                    )
                    continue

            try:
                raw_rules = raw.get("strategy_rules")
                raw_preconds = raw.get("preconditions")
                raw_rules_count = len(raw_rules) if isinstance(raw_rules, list) else 0
                raw_preconds_count = len(raw_preconds) if isinstance(raw_preconds, list) else 0

                rules = _validate_rules(raw_rules, source_url=article.source_url, published_at=article.published_at)
                preconds = _validate_preconditions(raw_preconds, source_url=article.source_url, published_at=article.published_at)

                # P2-LLM-001: 统计 schema 合规率
                stats.schema_valid_rules += len(rules)
                stats.schema_invalid_rules += raw_rules_count - len(rules)
                stats.schema_valid_preconds += len(preconds)
                stats.schema_invalid_preconds += raw_preconds_count - len(preconds)
            except Exception as exc:  # noqa: BLE001
                stats.failed += 1
                error_msg = str(exc)
                stats.errors_by_type[ExtractErrorType.SCHEMA_VALIDATION.value] += 1
                meta.raw_llm_output = {"error": error_msg}
                _record_error(
                    article_id=str(article.id),
                    source_url=article.source_url,
                    error_type=ExtractErrorType.SCHEMA_VALIDATION,
                    error_message=error_msg,
                    raw_output=raw if isinstance(raw, dict) else None,
                    error_log_path=error_log_path,
                )
                continue

            meta.extracted_concepts = raw.get("extracted_concepts") if isinstance(raw.get("extracted_concepts"), list) else []
            meta.trading_symbols = raw.get("trading_symbols") if isinstance(raw.get("trading_symbols"), list) else []
            meta.strategy_rules = rules
            meta.preconditions = preconds
            meta.comment_insights = raw.get("comment_insights") if isinstance(raw.get("comment_insights"), list) else []
            meta.sentiment_score = _clamp(_safe_float(raw.get("sentiment_score")), -1.0, 1.0)
            meta.confidence_score = _clamp(_safe_float(raw.get("confidence_score")), 0.0, 1.0)
            meta.raw_llm_output = {"mode": mode, "raw": raw}
            if error_message:
                meta.raw_llm_output["error"] = error_message
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
