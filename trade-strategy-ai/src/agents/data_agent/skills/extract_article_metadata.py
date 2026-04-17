from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID

# 并发处理限制：每次同时处理的文章数
CONCURRENCY_LIMIT = 3

from sqlalchemy import or_, select
from src.common.config import AppConfig
from src.common.utils import append_jsonl, ensure_dir
from src.db.session import session_scope
from src.llm.client import LLMClient, LLMError, LLMResult, from_env_and_config
from src.market_data.stock_info_service import get_stock_name_to_symbol_map
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


_STOCK_CODE_RE = re.compile(r"\b([0-9]{6})\.(SZ|SH|BJ)\b", re.I)
_MIXED_CASE_RE = re.compile(r"\b(sz|sh|bj)([0-9]{6})\b", re.I)
_PLAIN_CODE_RE = re.compile(r"\b([0-9]{6})\b")
_POSITIVE_WORDS = ("涨", "盈利", "买入", "做多", "突破", "拉升", "看好", "多头", "关注", "试错", "扫板", "打板")
_NEGATIVE_WORDS = ("下跌", "亏损", "卖出", "做空", "止损", "看空", "空头", "观望", "谨慎", "风险", "取关", "止盈", "板砸", "割肉")


def _normalize_symbol(code: str, suffix: str | None = None) -> str:
    """将各种格式转为标准格式 000000.XX"""
    code = code.upper()
    if suffix:
        suffix = suffix.upper()
        if suffix in ("SZ", "SH", "BJ"):
            return f"{code}.{suffix}"
    # 纯数字，根据前缀推断交易所
    if code.startswith(("000", "001", "002", "003", "300", "400")):
        return f"{code}.SZ"
    elif code.startswith(("600", "601", "603", "605", "688", "900")):
        return f"{code}.SH"
    elif code.startswith(("430", "830", "870")):
        return f"{code}.BJ"
    return f"{code}.SZ"  # 默认深圳


def _extract_symbols_from_content(content: str) -> list[str]:
    """从内容中提取股票代码，支持多种格式"""
    symbols: list[str] = []
    seen: set[str] = set()

    def _add_symbol(sym: str) -> bool:
        """添加符号，返回是否成功（去重）"""
        sym_upper = sym.upper()
        if sym_upper not in seen:
            seen.add(sym_upper)
            symbols.append(sym_upper)
            return True
        return False

    # 1. 标准格式 000000.XX
    for match in _STOCK_CODE_RE.finditer(content):
        _add_symbol(f"{match.group(1)}.{match.group(2).upper()}")

    # 2. 混合格式 sz002547, SZ002547
    for match in _MIXED_CASE_RE.finditer(content):
        _add_symbol(_normalize_symbol(match.group(2), match.group(1)))

    # 3. 纯数字 002547, 600519
    for match in _PLAIN_CODE_RE.finditer(content):
        code = match.group(1)
        if code.isdigit() and len(code) == 6:
            _add_symbol(_normalize_symbol(code))

    return symbols[:10]  # 最多10条


async def _normalize_symbols_with_db(symbols: list[str]) -> list[str]:
    """使用数据库映射将中文股票名称转为标准代码

    1. 先用现有逻辑标准化各种代码格式
    2. 对可能是中文名称的项，查询数据库进行映射

    Args:
        symbols: LLM 提取的 trading_symbols，可能包含中文名称或各种代码格式

    Returns:
        标准化后的代码列表
    """
    if not symbols:
        return []

    # 先对已有符号进行格式标准化
    normalized: list[str] = []
    name_candidates: list[str] = []  # 可能是中文名称的

    for sym in symbols:
        sym = sym.strip()
        if not sym:
            continue

        # 已经是标准格式 000000.XX
        if len(sym) == 10 and "." in sym:
            normalized.append(sym.upper())
            continue

        # 小写/混合格 sz002547
        if sym.lower().startswith(("sz", "sh", "bj")) and len(sym) == 8:
            normalized.append(_normalize_symbol(sym[2:], sym[:2]))
            continue

        # 纯6位数字
        if sym.isdigit() and len(sym) == 6:
            normalized.append(_normalize_symbol(sym))
            continue

        # 可能是中文名称
        name_candidates.append(sym)

    # 如果有中文名称候选，查询数据库进行映射
    if name_candidates:
        try:
            name_to_code = await get_stock_name_to_symbol_map()
            for name in name_candidates:
                if name in name_to_code:
                    normalized.append(name_to_code[name])
                # else: 无法映射，丢弃（因为 LLM 应该已经尽量填代码了）
        except Exception:
            # 数据库查询失败，跳过映射
            pass

    # 去重并返回
    seen: set[str] = set()
    result: list[str] = []
    for sym in normalized:
        sym_upper = sym.upper()
        if sym_upper not in seen:
            seen.add(sym_upper)
            result.append(sym_upper)

    return result[:10]


def _read_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _now_utc() -> datetime:
    return datetime.now(UTC)


def default_pending_tasks_path(*, base_dir: Path) -> Path:
    return base_dir / "data" / "processed" / "pipeline" / "pending_tasks.jsonl"


def default_checkpoint_path(*, base_dir: Path) -> Path:
    """LLM 调用全部失败后的断点记录文件路径。"""
    return base_dir / "data" / "processed" / "pipeline" / "llm_checkpoint.jsonl"


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


def _load_checkpoint(*, checkpoint_path: Path) -> set[str]:
    """加载断点集合（已确认所有模型都失败的 article_id）。"""
    if not checkpoint_path.exists():
        return set()
    failed_ids: set[str] = set()
    with checkpoint_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if "article_id" in record:
                    failed_ids.add(record["article_id"])
            except json.JSONDecodeError:
                continue
    return failed_ids


def _add_to_checkpoint(*, article_id: str, error: str, checkpoint_path: Path) -> None:
    """将 article_id 添加到断点文件。"""
    ensure_dir(checkpoint_path.parent)
    record = {
        "article_id": article_id,
        "error": error,
        "timestamp": _now_utc().isoformat(),
    }
    append_jsonl(checkpoint_path, record)


def _remove_from_checkpoint(*, article_id: str, checkpoint_path: Path) -> None:
    """从断点文件移除 article_id（处理成功后调用）。"""
    if not checkpoint_path.exists():
        return
    # 重新写入，排除该 article_id
    remaining: list[dict[str, Any]] = []
    with checkpoint_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("article_id") != article_id:
                    remaining.append(record)
            except json.JSONDecodeError:
                continue
    # 写回
    with checkpoint_path.open("w", encoding="utf-8") as f:
        for record in remaining:
            f.write(json.dumps(record, ensure_ascii=False, default=str))
            f.write("\n")


def _clear_checkpoint(*, checkpoint_path: Path) -> None:
    """清空断点文件（force 模式时调用）。"""
    if checkpoint_path.exists():
        checkpoint_path.unlink()


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

    # 支持多种格式的股票代码提取
    symbols = _extract_symbols_from_content(content)

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
            '  "trading_symbols": [...],       // 0-8 个，优先提取有把握的\n'
            '  "strategy_rules": [...],        // 0-8 条，宁缺毋滥\n'
            '  "preconditions": [...],         // 0-8 条\n'
            '  "comment_insights": [...],      // 0-5 条，从评论中提炼\n'
            '  "sentiment_score": float,       // -1.0 ~ 1.0\n'
            '  "confidence_score": float       // 0.0 ~ 1.0\n'
            "}"
        ),
    ])

    # 控制输入长度：避免把超长评论一次性塞爆
    content = article.content_text.strip()
    if len(content) > 20000:
        content = content[:20000]

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


async def _process_one_article(
    *,
    session: Any,
    article: BlogArticle,
    meta: ArticleMetadata,
    client: LLMClient,
    prompts_dir: Path,
    stats: ExtractStats,
    pending_path: Path,
    error_log_path: Path,
    checkpoint_path: Path,
    version: str,
) -> bool:
    """处理单篇文章的 LLM 抽取和数据库更新。

    Returns: True if processed successfully, False otherwise.
    """
    stats.scanned += 1

    if not article.content_text or len(article.content_text.strip()) < 80:
        stats.skipped += 1
        return False

    error_message: str | None = None
    mode = "unknown"
    raw = None

    if not client.is_enabled():
        raw = _heuristic_extract(article)
        mode = "fallback_heuristic"
        stats.fallback_calls += 1
    else:
        stats.llm_calls += 1
        try:
            raw = await _extract_one_with_retry(client=client, prompts_dir=prompts_dir, article=article)
            mode = "llm"
        except LLMError as exc:
            error_message = str(exc)
            stats.failed += 1
            stats.errors_by_type[ExtractErrorType.NETWORK.value] += 1
            _record_error(
                article_id=str(article.id),
                source_url=article.source_url,
                error_type=ExtractErrorType.NETWORK,
                error_message=error_message,
                raw_output=None,
                error_log_path=error_log_path,
            )
            _add_to_checkpoint(
                article_id=str(article.id),
                error=error_message,
                checkpoint_path=checkpoint_path,
            )
            return False
        except Exception as exc:  # noqa: BLE001
            error_msg = str(exc)
            stats.failed += 1
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
            return False

    try:
        raw_rules = raw.get("strategy_rules")
        raw_preconds = raw.get("preconditions")
        raw_rules_count = len(raw_rules) if isinstance(raw_rules, list) else 0
        raw_preconds_count = len(raw_preconds) if isinstance(raw_preconds, list) else 0

        rules = _validate_rules(raw_rules, source_url=article.source_url, published_at=article.published_at)
        preconds = _validate_preconditions(raw_preconds, source_url=article.source_url, published_at=article.published_at)

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
        return False

    meta.extracted_concepts = raw.get("extracted_concepts") if isinstance(raw.get("extracted_concepts"), list) else []
    raw_symbols = raw.get("trading_symbols") if isinstance(raw.get("trading_symbols"), list) else []
    meta.trading_symbols = await _normalize_symbols_with_db(raw_symbols)
    meta.strategy_rules = rules
    meta.preconditions = preconds
    meta.comment_insights = raw.get("comment_insights") if isinstance(raw.get("comment_insights"), list) else []
    meta.sentiment_score = _clamp(_safe_float(raw.get("sentiment_score")), -1.0, 1.0)
    meta.confidence_score = _clamp(_safe_float(raw.get("confidence_score")), 0.0, 1.0)
    meta.raw_llm_output = {"mode": mode, "raw": raw, "version": version}
    if error_message:
        meta.raw_llm_output["error"] = error_message
    meta.processed_at = _now_utc()

    stats.extracted += 1

    # 每篇文章处理完立即写入数据库
    await session.commit()

    # 输出抽取结果摘要
    concepts_count = len(meta.extracted_concepts)
    symbols_count = len(meta.trading_symbols)
    rules_count = len(meta.strategy_rules)
    preconds_count = len(meta.preconditions)
    print(f"  [extracted] {article.title[:30]}... concepts={concepts_count} symbols={symbols_count} rules={rules_count} preconds={preconds_count}")

    # 触发后续聚类/记忆刷新（先落盘待办）
    task = AgentTask(
        type="article_metadata_extracted",
        title="Article metadata extracted",
        trader_id=(article.raw_payload.get("trader_id") if isinstance(article.raw_payload, dict) else None),
        details={
            "article_id": str(article.id),
            "source_url": article.source_url,
            "mode": mode,
            "version": version,
            "strategy_rules": len(rules),
            "preconditions": len(preconds),
        },
    )
    append_jsonl(pending_path, task.model_dump())
    stats.generated_tasks += 1

    return True


async def _process_article_isolated(
    *,
    article_id: UUID,
    version: str,
    llm_provider: str,
    client: LLMClient,
    prompts_dir: Path,
    pending_path: Path,
    error_log_path: Path,
    checkpoint_path: Path,
) -> dict:
    """独立的文章处理函数，每个调用使用自己的数据库 session。

    用于并发处理：从 session_scope 内部加载 article 和 meta，
    完成 LLM 抽取后 commit，调用方不管理 session。

    Returns: dict with 'success' (bool) and stats delta
    """
    result = {
        "success": False,
        "error": None,
        "scanned": 0,
        "skipped": 0,
        "failed": 0,
        "extracted": 0,
        "generated_tasks": 0,
        "llm_calls": 0,
        "fallback_calls": 0,
        "schema_valid_rules": 0,
        "schema_invalid_rules": 0,
        "schema_valid_preconds": 0,
        "schema_invalid_preconds": 0,
        "error_type": None,
        "llm_provider": None,
        "llm_model": None,
    }

    async with session_scope() as session:
        article = await session.get(BlogArticle, article_id)
        if not article:
            result["error"] = f"Article not found: {article_id}"
            return result

        # 查找或创建该版本的 ArticleMetadata
        if version == "v1":
            # 先查找该文章是否有任何 metadata 记录
            meta = await session.scalar(
                select(ArticleMetadata).where(
                    ArticleMetadata.article_id == article_id,
                )
            )
            if meta and meta.processed_at is not None:
                # 已有处理完成的 metadata，跳过
                result["scanned"] = 1
                result["error"] = "Already processed"
                return result
            if not meta:
                # 没有记录，创建新记录
                meta = ArticleMetadata(article_id=article_id, version=version)
                session.add(meta)
                await session.flush()
        else:
            # v2+：查找该版本的元数据记录是否已存在
            existing = await session.scalar(
                select(ArticleMetadata).where(
                    ArticleMetadata.article_id == article_id,
                    ArticleMetadata.version == version,
                )
            )
            if existing:
                result["scanned"] = 1
                result["error"] = f"Version {version} metadata already exists"
                return result
            # 创建新记录
            meta = ArticleMetadata(article_id=article_id, version=version)
            session.add(meta)
            await session.flush()

        result["scanned"] = 1

        if not article.content_text or len(article.content_text.strip()) < 80:
            result["skipped"] = 1
            return result

        error_message: str | None = None
        mode = "unknown"
        raw = None

        if not client.is_enabled():
            raw = _heuristic_extract(article)
            mode = "fallback_heuristic"
            result["fallback_calls"] = 1
            result["llm_provider"] = llm_provider
            result["llm_model"] = None
        else:
            result["llm_calls"] = 1
            try:
                llm_result = await _extract_one_with_retry(client=client, prompts_dir=prompts_dir, article=article)
                raw = llm_result.data
                result["llm_model"] = llm_result.model
                result["llm_provider"] = llm_provider
                mode = "llm"
            except LLMError as exc:
                error_message = str(exc)
                result["failed"] = 1
                result["error_type"] = ExtractErrorType.NETWORK.value
                result["llm_provider"] = llm_provider
                _record_error(
                    article_id=str(article.id),
                    source_url=article.source_url,
                    error_type=ExtractErrorType.NETWORK,
                    error_message=error_message,
                    raw_output=None,
                    error_log_path=error_log_path,
                )
                _add_to_checkpoint(
                    article_id=str(article.id),
                    error=error_message,
                    checkpoint_path=checkpoint_path,
                )
                return result
            except Exception as exc:  # noqa: BLE001
                error_msg = str(exc)
                result["failed"] = 1
                result["error_type"] = ExtractErrorType.QUALITY.value
                meta.raw_llm_output = {"error": error_msg}
                _record_error(
                    article_id=str(article.id),
                    source_url=article.source_url,
                    error_type=ExtractErrorType.QUALITY,
                    error_message=error_msg,
                    raw_output=None,
                    error_log_path=error_log_path,
                )
                return result

        try:
            raw_rules = raw.get("strategy_rules")
            raw_preconds = raw.get("preconditions")
            raw_rules_count = len(raw_rules) if isinstance(raw_rules, list) else 0
            raw_preconds_count = len(raw_preconds) if isinstance(raw_preconds, list) else 0

            rules = _validate_rules(raw_rules, source_url=article.source_url, published_at=article.published_at)
            preconds = _validate_preconditions(raw_preconds, source_url=article.source_url, published_at=article.published_at)

            result["schema_valid_rules"] = len(rules)
            result["schema_invalid_rules"] = raw_rules_count - len(rules)
            result["schema_valid_preconds"] = len(preconds)
            result["schema_invalid_preconds"] = raw_preconds_count - len(preconds)
        except Exception as exc:  # noqa: BLE001
            result["failed"] = 1
            error_msg = str(exc)
            result["error_type"] = ExtractErrorType.SCHEMA_VALIDATION.value
            meta.raw_llm_output = {"error": error_msg}
            _record_error(
                article_id=str(article.id),
                source_url=article.source_url,
                error_type=ExtractErrorType.SCHEMA_VALIDATION,
                error_message=error_msg,
                raw_output=raw if isinstance(raw, dict) else None,
                error_log_path=error_log_path,
            )
            return result

        meta.extracted_concepts = raw.get("extracted_concepts") if isinstance(raw.get("extracted_concepts"), list) else []
        raw_symbols = raw.get("trading_symbols") if isinstance(raw.get("trading_symbols"), list) else []
        meta.trading_symbols = await _normalize_symbols_with_db(raw_symbols)
        meta.strategy_rules = rules
        meta.preconditions = preconds
        meta.comment_insights = raw.get("comment_insights") if isinstance(raw.get("comment_insights"), list) else []
        meta.sentiment_score = _clamp(_safe_float(raw.get("sentiment_score")), -1.0, 1.0)
        meta.confidence_score = _clamp(_safe_float(raw.get("confidence_score")), 0.0, 1.0)
        meta.raw_llm_output = {"mode": mode, "raw": raw, "version": version}
        if error_message:
            meta.raw_llm_output["error"] = error_message
        meta.processed_at = _now_utc()
        meta.provider = result.get("llm_provider")
        meta.model = result.get("llm_model")

        result["extracted"] = 1
        await session.commit()

        # 输出抽取结果摘要
        concepts_count = len(meta.extracted_concepts)
        symbols_count = len(meta.trading_symbols)
        rules_count = len(meta.strategy_rules)
        preconds_count = len(meta.preconditions)
        print(f"  [extracted] {article.title[:30]}... concepts={concepts_count} symbols={symbols_count} rules={rules_count} preconds={preconds_count}")

        # 触发后续聚类/记忆刷新（先落盘待办）
        task = AgentTask(
            type="article_metadata_extracted",
            title="Article metadata extracted",
            trader_id=(article.raw_payload.get("trader_id") if isinstance(article.raw_payload, dict) else None),
            details={
                "article_id": str(article.id),
                "source_url": article.source_url,
                "mode": mode,
                "version": version,
                "strategy_rules": len(rules),
                "preconditions": len(preconds),
            },
        )
        append_jsonl(pending_path, task.model_dump())
        result["generated_tasks"] = 1

        result["success"] = True
        return result


async def _extract_one_with_retry(
    *,
    client: LLMClient,
    prompts_dir: Path,
    article: BlogArticle,
) -> LLMResult:
    """带重试和模型降级的 LLM 调用。

    使用 complete_json_with_retry 实现：
    - 每个模型重试 3 次（指数退避）
    - 所有模型都失败后抛出异常

    Returns:
        LLMResult: 包含 data (dict) 和 model (str)
    """
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
            '  "trading_symbols": [...],       // 0-8 个，优先提取有把握的\n'
            '  "strategy_rules": [...],        // 0-8 条，宁缺毋滥\n'
            '  "preconditions": [...],         // 0-8 条\n'
            '  "comment_insights": [...],      // 0-5 条，从评论中提炼\n'
            '  "sentiment_score": float,       // -1.0 ~ 1.0\n'
            '  "confidence_score": float       // 0.0 ~ 1.0\n'
            "}"
        ),
    ])

    # 控制输入长度：避免把超长评论一次性塞爆
    content = article.content_text.strip()
    if len(content) > 20000:
        content = content[:20000]

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

    # 使用带重试和模型降级的调用
    return await client.complete_json_with_retry(system_prompt=system_prompt, user_prompt=user_prompt)


async def extract_and_store_metadata(
    *,
    config: AppConfig,
    base_dir: Path,
    pending_tasks_path: Path | None = None,
    force: bool = False,
    version: str = "v1",
    total_limit: int | None = None,
) -> ExtractStats:
    """流式批次处理：每批加载 CONCURRENCY_LIMIT * 7 = 21 条，并发处理完后再加载下一批，直到没有数据为止。"""
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
    llm_provider = llm_cfg.provider or "unknown"

    stats = ExtractStats()
    pending_path = pending_tasks_path or default_pending_tasks_path(base_dir=base_dir)
    ensure_dir(pending_path.parent)
    error_log_path = default_error_log_path(base_dir=base_dir)
    ensure_dir(error_log_path.parent)

    # 断点文件：仅用于日志追踪，记录所有模型都失败的文章
    checkpoint_path = default_checkpoint_path(base_dir=base_dir)
    if force:
        # force 模式：清空断点记录
        _clear_checkpoint(checkpoint_path=checkpoint_path)

    # 每批大小：并发数的 7 倍，确保每批能充分利用并发
    BATCH_SIZE = CONCURRENCY_LIMIT * 7
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    async def process_one(article_id: UUID) -> dict:
        async with semaphore:
            return await _process_article_isolated(
                article_id=article_id,
                version=version,
                llm_provider=llm_provider,
                client=client,
                prompts_dir=prompts_dir,
                pending_path=pending_path,
                error_log_path=error_log_path,
                checkpoint_path=checkpoint_path,
            )

    async def load_batch() -> list[UUID]:
        """加载一批 article_id，不重复已处理的文章。

        不使用 offset 分页：因为 WHERE 条件过滤掉已处理文章后，
        后续查询从 offset=0 开始不会重复拉取已处理的文章。
        """
        async with session_scope() as session:
            if version == "v1":
                rows = await session.execute(
                    select(BlogArticle.id)
                    .outerjoin(ArticleMetadata, ArticleMetadata.article_id == BlogArticle.id)
                    .where(
                        or_(
                            ArticleMetadata.id.is_(None),
                            ArticleMetadata.processed_at.is_(None)
                        )
                    )
                    .order_by(BlogArticle.crawled_at.desc())
                    .limit(BATCH_SIZE)
                )
            else:
                subq = (
                    select(ArticleMetadata.article_id)
                    .where(ArticleMetadata.version == version)
                )
                rows = await session.execute(
                    select(BlogArticle.id)
                    .where(BlogArticle.id.not_in(subq))
                    .order_by(BlogArticle.crawled_at.desc())
                    .limit(BATCH_SIZE)
                )
            return [row[0] for row in rows.all()]

    async def process_batch(article_ids: list[UUID]) -> list[dict]:
        results = await asyncio.gather(
            *[process_one(aid) for aid in article_ids],
            return_exceptions=True,
        )
        return list(results)

    async def run() -> ExtractStats:
        total_processed = 0
        while True:
            batch_ids = await load_batch()
            if not batch_ids:
                break
            # 如果设置了 total_limit，检查是否超过
            if total_limit is not None and total_processed + len(batch_ids) > total_limit:
                batch_ids = batch_ids[: total_limit - total_processed]
                if not batch_ids:
                    break
            print(f"[extract_and_store_metadata] processing batch of {len(batch_ids)} articles (total_processed={total_processed})")
            results = await process_batch(batch_ids)

            # 汇总统计结果
            for r in results:
                if isinstance(r, Exception):
                    stats.failed += 1
                    continue
                stats.scanned += r.get("scanned", 0)
                stats.extracted += r.get("extracted", 0)
                stats.skipped += r.get("skipped", 0)
                stats.failed += r.get("failed", 0)
                stats.generated_tasks += r.get("generated_tasks", 0)
                stats.llm_calls += r.get("llm_calls", 0)
                stats.fallback_calls += r.get("fallback_calls", 0)
                stats.schema_valid_rules += r.get("schema_valid_rules", 0)
                stats.schema_invalid_rules += r.get("schema_invalid_rules", 0)
                stats.schema_valid_preconds += r.get("schema_valid_preconds", 0)
                stats.schema_invalid_preconds += r.get("schema_invalid_preconds", 0)

            total_processed += len(batch_ids)

        return stats

    return await run()
