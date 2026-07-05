from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.stage2_canonical import ArticleStructure, PromptRun, RuleCandidate
from src.persona.claim_keys import ClaimKey


@dataclass(frozen=True, slots=True)
class ArticleAnalysisRecord:
    article_id: UUID
    schema_version: str
    processed_at: datetime | None
    provider: str | None
    model: str | None
    article_type: str | None
    extraction_version: str | None
    extracted_concepts: list[dict[str, Any]]
    trading_symbols: list[str]
    strategy_rules: list[dict[str, Any]]
    preconditions: list[dict[str, Any]]
    comment_insights: list[dict[str, Any]]
    raw_llm_output: dict[str, Any]
    sentiment_score: float | None
    confidence_score: float | None


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    return None


def _first_string(values: Any, *, default: str | None = None) -> str | None:
    if isinstance(values, str) and values.strip():
        return values.strip()
    if isinstance(values, list):
        for item in values:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return default


def _claim_key_for_rule(rule_type: str | None) -> str:
    match str(rule_type or "").lower():
        case "entry":
            return ClaimKey.entry_trigger.value
        case "exit":
            return ClaimKey.exit_invalidation.value
        case "filter":
            return ClaimKey.filter_market_regime.value
        case "sizing":
            return ClaimKey.sizing_base_pct.value
        case "risk":
            return ClaimKey.risk_no_trade_conditions.value
        case _:
            return ClaimKey.entry_trigger.value


def _action_from_stage3(action: Any) -> dict[str, Any]:
    if not isinstance(action, dict):
        return {"type": "filter", "params": {}}
    params = dict(action.get("params") or {}) if isinstance(action.get("params"), dict) else {}
    price_reference = action.get("price_reference")
    if price_reference is not None:
        params.setdefault("price_reference", price_reference)
    return {
        "type": str(action.get("type") or "filter"),
        "side": action.get("side") if isinstance(action.get("side"), str) else None,
        "order": action.get("order") if isinstance(action.get("order"), str) else None,
        "price": action.get("price"),
        "params": params,
    }


def _quoted_text_from_evidence(evidence: Any) -> str | None:
    if isinstance(evidence, list):
        for item in evidence:
            if isinstance(item, dict) and isinstance(item.get("quote"), str):
                return item["quote"]
            if isinstance(item, str):
                return item
    return None


def _project_rule(candidate: RuleCandidate, *, published_at: datetime | None, source_url: str | None) -> dict[str, Any]:
    payload = candidate.canonical_payload if isinstance(candidate.canonical_payload, dict) else {}
    rule_type = str(payload.get("rule_type") or candidate.rule_type or "filter")
    return {
        "schema_version": "stage3_article_analysis_v1",
        "claim_key": _claim_key_for_rule(rule_type),
        "source_rule_key": payload.get("rule_key"),
        "rule_type": rule_type,
        "instrument_focus": _first_string(payload.get("instrument_focus"), default="mixed") or "mixed",
        "condition": payload.get("condition") if isinstance(payload.get("condition"), dict) else {},
        "action": _action_from_stage3(payload.get("action")),
        "params": {
            "timeframe": payload.get("timeframe"),
            "holding_period": payload.get("holding_period"),
            "risk_controls": payload.get("risk_controls") if isinstance(payload.get("risk_controls"), list) else [],
            "backtestability_status": candidate.backtestability_status,
        },
        "confidence": _float_or_none(payload.get("confidence")),
        "source_url": source_url,
        "quoted_text": _quoted_text_from_evidence(payload.get("evidence")),
        "published_at": published_at,
    }


def _project_precondition(item: Any, *, published_at: datetime | None, source_url: str | None) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    return {
        "schema_version": "stage3_article_analysis_v1",
        "claim_key": ClaimKey.filter_market_regime.value,
        "instrument_focus": "mixed",
        "condition": item.get("condition") if isinstance(item.get("condition"), dict) else {},
        "confidence": _float_or_none(item.get("confidence")),
        "source_url": source_url,
        "quoted_text": _quoted_text_from_evidence(item.get("evidence")),
        "published_at": published_at,
    }


def _symbol_values(raw_symbols: Any) -> list[str]:
    values: list[str] = []
    if not isinstance(raw_symbols, list):
        return values
    for item in raw_symbols:
        if isinstance(item, str) and item.strip():
            values.append(item.strip())
        elif isinstance(item, dict):
            symbol = item.get("symbol")
            raw_name = item.get("raw_name")
            if isinstance(symbol, str) and symbol.strip():
                values.append(symbol.strip())
            elif isinstance(raw_name, str) and raw_name.strip():
                values.append(raw_name.strip())
    return values


class ArticleAnalysisSelectionService:
    """Read the current canonical article analysis outputs for downstream business flows."""

    async def load_effective_analysis_map(
        self,
        session: AsyncSession,
        *,
        article_ids: list[UUID],
    ) -> dict[UUID, ArticleAnalysisRecord]:
        if not article_ids:
            return {}

        rows = await session.execute(
            select(ArticleStructure, PromptRun)
            .join(PromptRun, PromptRun.prompt_run_id == ArticleStructure.prompt_run_id)
            .where(ArticleStructure.article_id.in_(article_ids))
            .order_by(
                ArticleStructure.article_id.asc(),
                ArticleStructure.updated_at.desc(),
                ArticleStructure.created_at.desc(),
            )
        )
        latest: dict[UUID, tuple[ArticleStructure, PromptRun]] = {}
        for structure, prompt_run in rows.all():
            latest.setdefault(structure.article_id, (structure, prompt_run))
        if not latest:
            return {}

        candidate_rows = await session.execute(
            select(RuleCandidate)
            .where(RuleCandidate.article_structure_id.in_([item[0].article_structure_id for item in latest.values()]))
            .order_by(RuleCandidate.article_structure_id.asc(), RuleCandidate.candidate_index.asc())
        )
        candidates_by_structure: dict[UUID, list[RuleCandidate]] = {}
        for candidate in candidate_rows.scalars().all():
            candidates_by_structure.setdefault(candidate.article_structure_id, []).append(candidate)

        result: dict[UUID, ArticleAnalysisRecord] = {}
        for article_id, (structure, prompt_run) in latest.items():
            raw_output = prompt_run.raw_output if isinstance(prompt_run.raw_output, dict) else {}
            classification = raw_output.get("classification") if isinstance(raw_output.get("classification"), dict) else {}
            concepts = raw_output.get("concept_extraction") if isinstance(raw_output.get("concept_extraction"), dict) else {}
            explicit_preconditions = raw_output.get("explicit_preconditions") if isinstance(raw_output.get("explicit_preconditions"), dict) else {}
            sentiment = concepts.get("sentiment") if isinstance(concepts.get("sentiment"), dict) else {}
            request_json = prompt_run.request_json if isinstance(prompt_run.request_json, dict) else {}
            published_at = request_json.get("published_at")
            if isinstance(published_at, str):
                try:
                    published_at_dt = datetime.fromisoformat(published_at)
                except ValueError:
                    published_at_dt = None
            else:
                published_at_dt = None
            source_url = request_json.get("source_url") if isinstance(request_json.get("source_url"), str) else None

            result[article_id] = ArticleAnalysisRecord(
                article_id=article_id,
                schema_version=structure.schema_version,
                processed_at=prompt_run.completed_at or structure.updated_at,
                provider=prompt_run.provider,
                model=prompt_run.model,
                article_type=classification.get("article_type") if isinstance(classification.get("article_type"), str) else structure.payload.get("article_type"),
                extraction_version=prompt_run.prompt_version,
                extracted_concepts=list(concepts.get("concepts") or []) if isinstance(concepts.get("concepts"), list) else [],
                trading_symbols=_symbol_values(concepts.get("trading_symbols")),
                strategy_rules=[
                    _project_rule(candidate, published_at=published_at_dt, source_url=source_url)
                    for candidate in candidates_by_structure.get(structure.article_structure_id, [])
                ],
                preconditions=[
                    item
                    for item in (
                        _project_precondition(item, published_at=published_at_dt, source_url=source_url)
                        for item in (explicit_preconditions.get("preconditions") if isinstance(explicit_preconditions.get("preconditions"), list) else [])
                    )
                    if item is not None
                ],
                comment_insights=[],
                raw_llm_output=raw_output,
                sentiment_score=_float_or_none(sentiment.get("score")),
                confidence_score=_float_or_none(classification.get("confidence")),
            )

        return result
