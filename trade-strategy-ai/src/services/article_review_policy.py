from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from src.models.stage2_canonical import RuleCandidate


AutomaticReviewStatus = Literal["pending_backtest", "needs_human_review", "suggested_reject"]


@dataclass(frozen=True)
class AutomaticReviewResult:
    status: AutomaticReviewStatus
    reasons: list[str]
    risk_level: Literal["low", "medium", "high"]
    backtestability_status: str
    kaipan_dependency: bool
    market_state_status: str


LIGHT_AMBIGUOUS_TERM_MARKERS = (
    "强势",
    "明显放量",
    "放量",
    "企稳",
    "附近",
    "偏强",
    "博弈",
)

HEAVY_AMBIGUOUS_TERM_MARKERS = (
    "止损",
    "stop_loss",
    "stop loss",
    "止盈",
    "take_profit",
    "take profit",
    "仓位",
    "position",
    "sizing",
    "市场状态",
    "market_state",
    "market regime",
    "主观判断",
    "人工判断",
    "看情况",
)

CORE_MISSING_FIELD_MARKERS = (
    "止损",
    "stop_loss",
    "stop loss",
    "止盈",
    "take_profit",
    "take profit",
    "仓位",
    "position",
    "sizing",
    "阈值",
    "threshold",
    "明确阈值",
    "entry",
    "exit",
    "买入",
    "卖出",
    "触发条件",
    "核心参数",
)

CORE_RISK_CONTROL_MARKERS = (
    "止损",
    "stop_loss",
    "stop loss",
    "止盈",
    "take_profit",
    "take profit",
    "仓位",
    "position",
    "sizing",
    "最大亏损",
    "max_loss",
)

SUBJECTIVE_RISK_CONTROL_MARKERS = (
    "严格",
    "适当",
    "合理",
    "控制风险",
    "看情况",
    "主观",
    "人工判断",
)

_NUMERIC_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*(?:%|percent|pct|bps|bp|倍|成|手|股|元|日|天)?", re.IGNORECASE)


def _contains_kaipan_dependency(values: Any) -> bool:
    if isinstance(values, str):
        return "kaipan" in values.lower()
    if isinstance(values, list):
        return any(_contains_kaipan_dependency(item) for item in values)
    if isinstance(values, dict):
        return any(_contains_kaipan_dependency(item) for item in values.values())
    return False


def _extract_texts(values: Any, *, parent_key: str | None = None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        value = values.strip()
        return [f"{parent_key}:{value}" if parent_key and value else value] if value else []
    if isinstance(values, bool):
        return [parent_key] if parent_key and values else []
    if isinstance(values, (int, float)):
        return [f"{parent_key}:{values}" if parent_key else str(values)]
    if isinstance(values, list):
        texts: list[str] = []
        for value in values:
            texts.extend(_extract_texts(value, parent_key=parent_key))
        return texts
    if isinstance(values, dict):
        texts: list[str] = []
        for key, value in values.items():
            key_text = str(key).strip()
            if value in (None, False, "", [], {}):
                continue
            if isinstance(value, (str, int, float, bool)):
                texts.extend(_extract_texts(value, parent_key=key_text))
            else:
                texts.append(key_text)
                texts.extend(_extract_texts(value, parent_key=key_text))
        return [text for text in texts if text]
    text = str(values).strip()
    return [f"{parent_key}:{text}" if parent_key and text else text] if text else []


def _normalize_string_list(values: Any) -> list[str]:
    return _extract_texts(values)


def _matches_marker(value: str, markers: tuple[str, ...]) -> bool:
    normalized = value.strip().lower()
    return any(marker.lower() in normalized for marker in markers)


def _has_numeric_boundary(value: str) -> bool:
    return bool(_NUMERIC_PATTERN.search(value))


def _split_ambiguous_terms(values: Any) -> tuple[list[str], list[str]]:
    light_terms: list[str] = []
    heavy_terms: list[str] = []
    for term in _normalize_string_list(values):
        if _matches_marker(term, HEAVY_AMBIGUOUS_TERM_MARKERS):
            heavy_terms.append(term)
        elif _matches_marker(term, LIGHT_AMBIGUOUS_TERM_MARKERS):
            light_terms.append(term)
        else:
            heavy_terms.append(term)
    return light_terms, heavy_terms


def _split_missing_fields(values: Any) -> tuple[list[str], list[str]]:
    core_fields: list[str] = []
    non_core_fields: list[str] = []
    for field in _normalize_string_list(values):
        if _matches_marker(field, CORE_MISSING_FIELD_MARKERS):
            core_fields.append(field)
        else:
            non_core_fields.append(field)
    return core_fields, non_core_fields


def _classify_risk_controls(values: Any) -> tuple[list[str], list[str]]:
    relaxable_controls: list[str] = []
    heavy_controls: list[str] = []
    for item in _extract_texts(values):
        has_core_marker = _matches_marker(item, CORE_RISK_CONTROL_MARKERS)
        has_subjective_marker = _matches_marker(item, SUBJECTIVE_RISK_CONTROL_MARKERS)
        has_numeric_boundary = _has_numeric_boundary(item)
        if has_core_marker and not has_numeric_boundary:
            heavy_controls.append(item)
        elif has_subjective_marker and not has_numeric_boundary:
            heavy_controls.append(item)
        else:
            relaxable_controls.append(item)
    return relaxable_controls, heavy_controls


def determine_automatic_review(candidate: RuleCandidate) -> AutomaticReviewResult:
    payload = candidate.canonical_payload or {}
    quantification = payload.get("quantification") or {}
    condition = payload.get("condition") or {}
    action = payload.get("action") or {}
    evidence = payload.get("evidence") or []
    market_state = payload.get("market_state_applicability") or {}
    risk_controls = payload.get("risk_controls") or []
    data_dependencies = payload.get("data_dependencies") or []

    kaipan_dependency = _contains_kaipan_dependency(data_dependencies)
    market_state_status = str(market_state.get("status") or "not_declared")
    backtestability_status = str(candidate.backtestability_status)

    reject_reasons: list[str] = []
    if not evidence:
        reject_reasons.append("缺少原文证据")
    if not condition:
        reject_reasons.append("缺少规则条件")
    if not action:
        reject_reasons.append("缺少规则动作")
    if backtestability_status == "not_executable":
        reject_reasons.append("当前不可回测")

    if reject_reasons:
        return AutomaticReviewResult(
            status="suggested_reject",
            reasons=reject_reasons,
            risk_level="high",
            backtestability_status=backtestability_status,
            kaipan_dependency=kaipan_dependency,
            market_state_status=market_state_status,
        )

    light_ambiguous_terms, heavy_ambiguous_terms = _split_ambiguous_terms(quantification.get("ambiguous_terms"))
    core_missing_fields, non_core_missing_fields = _split_missing_fields(quantification.get("missing_fields"))
    relaxable_risk_controls, heavy_risk_controls = _classify_risk_controls(risk_controls)
    manual_review_required = bool(quantification.get("manual_review_required"))

    review_reasons: list[str] = []
    trace_reasons: list[str] = []
    if heavy_ambiguous_terms:
        review_reasons.append(f"存在重度模糊词：{', '.join(heavy_ambiguous_terms)}")
    if core_missing_fields:
        review_reasons.append(f"仍有核心缺失字段：{', '.join(core_missing_fields)}")
    if heavy_risk_controls:
        review_reasons.append(f"风险控制边界不明确：{', '.join(heavy_risk_controls)}")
    if kaipan_dependency:
        review_reasons.append("依赖 Kaipan 数据")
    if backtestability_status not in {"executable", "partially_executable"}:
        review_reasons.append("当前不满足直接回测条件")

    has_explained_relaxable_uncertainty = bool(light_ambiguous_terms or non_core_missing_fields or relaxable_risk_controls)
    if manual_review_required and not has_explained_relaxable_uncertainty:
        review_reasons.append("抽取层标记需人工复核，且未提供可放行的轻度原因")
    elif manual_review_required:
        trace_reasons.append("抽取层标记需人工复核，但未命中强风险门禁，保留追踪")

    if review_reasons:
        return AutomaticReviewResult(
            status="needs_human_review",
            reasons=review_reasons + trace_reasons,
            risk_level="medium",
            backtestability_status=backtestability_status,
            kaipan_dependency=kaipan_dependency,
            market_state_status=market_state_status,
        )

    reasons = ["证据、条件和动作完整，可进入待回测"]
    if light_ambiguous_terms:
        reasons.append(f"含轻度模糊词：{', '.join(light_ambiguous_terms)}；保留追踪但不单独触发人工")
    if non_core_missing_fields:
        reasons.append(f"含非核心缺失字段：{', '.join(non_core_missing_fields)}；保留追踪但不单独触发人工")
    if relaxable_risk_controls:
        reasons.append(f"风险控制边界可解释：{', '.join(relaxable_risk_controls)}；保留追踪")
    reasons.extend(trace_reasons)
    if manual_review_required:
        reasons.append("抽取层标记需人工复核，但仅命中可放行不确定性")
    if backtestability_status == "partially_executable":
        reasons.append("当前为 partially_executable；强风险门禁未命中，允许进入待回测队列")

    return AutomaticReviewResult(
        status="pending_backtest",
        reasons=reasons,
        risk_level="low",
        backtestability_status=backtestability_status,
        kaipan_dependency=kaipan_dependency,
        market_state_status=market_state_status,
    )
