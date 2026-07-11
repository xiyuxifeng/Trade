from __future__ import annotations

from typing import Any


def common_draft(primary_type: str, payload: dict[str, Any], quote: str) -> dict[str, Any]:
    return {
        "primary_type": primary_type,
        "secondary_tags": [],
        "taxonomy_payload": {"primary_type": primary_type, **payload},
        "source_evidence": {
            "quote": quote,
            "span": {"start": 0, "end": len(quote)},
            "section": 0,
            "evidence_kind": "explicit_quote",
            "rationale": "deterministic fixture label grounded in the quoted source",
        },
        "confidence": {
            "score": 0.9,
            "level": "high",
            "rationale": "deterministic reviewed fixture",
            "requires_human_confirmation": False,
        },
    }


PAYLOADS: dict[str, dict[str, Any]] = {
    "executable_rule": {
        "title": "共振日低点跌破退出",
        "rule_type": "exit",
        "instrument_universe": {"source_strategy": "resonance_day_positions"},
        "entry_condition": {"inherited_strategy": "resonance_day_entry_v1"},
        "entry_timing": "resonance day close",
        "entry_price_reference": "close",
        "exit_condition": {"field": "index_low", "operator": "lt", "reference": "resonance_day_low"},
        "exit_timing": "intraday immediately after trigger",
        "exit_price_reference": "next executable market price",
        "stop_loss_or_invalidation": {"same_as": "exit_condition"},
        "position_sizing": {"fraction": 1.0, "scope": "matched positions"},
        "holding_period": {"maximum": "until exit trigger"},
        "data_dependencies": [{"dataset": "index_ohlcv_1m", "fields": ["low"]}],
        "timestamp_availability": [{"dataset": "index_ohlcv_1m", "available": "at bar close"}],
        "lookahead_check": {"passed": True, "rationale": "only closed/current price observations are used", "risks": []},
        "ambiguous_terms": [],
        "parameterization": [],
        "rule_version_candidate": {"condition": "index_low < resonance_day_low", "action": "exit"},
        "not_directly_backtestable": False,
    },
    "rule_candidate": {
        "candidate_rule_summary": "突破需成交量确认",
        "known_components": {"entry": "price breakout", "confirmation": "volume expansion"},
        "missing_fields": ["volume_expansion_threshold"],
        "repair_tasks": ["locate an explicit threshold in source evidence"],
        "repair_source": "source_text",
        "repairability": "high",
        "instrument_universe_status": "complete",
        "entry_exit_status": {"entry": "present", "exit": "present"},
        "data_dependencies": [{"dataset": "ohlcv_1d"}],
        "timestamp_availability_risk": [],
        "ambiguous_terms": [{"term": "放量", "core": False}],
        "not_directly_backtestable": True,
    },
    "research_hypothesis": {
        "hypothesis_statement": "退潮阶段高位股次日回撤风险更高",
        "source_experience": "退潮期不要接高位",
        "dependent_variables": ["next_day_return", "max_drawdown"],
        "independent_variables": ["retreat_phase_proxy", "board_height"],
        "candidate_observable_indicators": ["failed_board_rate", "limit_down_count"],
        "required_data": ["ohlcv_1d", "limit_up_down_stats"],
        "validation_method": "grouped event study",
        "timestamp_availability_assumptions": ["phase proxies must be frozen before entry"],
        "research_status": "proposed",
        "not_directly_backtestable": True,
    },
    "semantic_experience": {
        "term_or_phrase": "弱转强",
        "source_context": "author describes an improvement from weak prior action",
        "plain_language_interpretation": "perceived short-term strength improves relative to expectation",
        "related_market_state": "sentiment",
        "possible_observable_proxies": ["auction_gap", "auction_volume"],
        "semantic_dictionary_action": "clarify",
        "ambiguity_level": "high",
        "not_directly_backtestable": True,
    },
    "risk_control_hint": {
        "risk_context": "退潮期",
        "risk_action": "降低仓位",
        "sizing_boundary": None,
        "trigger_terms": ["退潮期"],
        "missing_definitions": ["retreat phase definition", "target position cap"],
        "system_design_use": ["portfolio risk throttle backlog"],
        "data_dependencies": [],
        "not_directly_backtestable": True,
    },
    "data_requirement_hint": {
        "data_name": "kaipan_pre_market_bid",
        "data_description": "pre-market auction observations for weak-to-strong analysis",
        "needed_by": ["semantic term: 弱转强"],
        "timestamp_requirement": "available before the opening decision",
        "granularity": "auction",
        "source_or_provider": None,
        "availability_status": "unknown",
        "data_contract_gap": ["provider", "timestamp coverage"],
        "not_directly_backtestable": True,
    },
    "unusable_noise": {
        "reason": "motivational statement without measurable trading meaning",
        "noise_category": "motivational",
        "retain_source_reference_only": True,
        "dedupe_key": None,
    },
}


QUOTES = {
    "executable_rule": "指数跌破共振日低点立即退出。",
    "rule_candidate": "突破必须放量确认。",
    "research_hypothesis": "退潮期不要接高位。",
    "semantic_experience": "弱转强要看是否超预期。",
    "risk_control_hint": "退潮期降低仓位。",
    "data_requirement_hint": "弱转强需要看竞价数据。",
    "unusable_noise": "理解力才是复利的本质。",
}


def draft_for(primary_type: str) -> dict[str, Any]:
    return common_draft(primary_type, PAYLOADS[primary_type], QUOTES[primary_type])


REPRESENTATIVE_ARTICLES = [
    {"category": "情绪周期", "text": "情绪回暖后赚钱效应可能扩散。", "expected": ["semantic_experience", "research_hypothesis"]},
    {"category": "情绪周期", "text": "高潮后的分歧通常更剧烈。", "expected": ["semantic_experience", "research_hypothesis"]},
    {"category": "弱转强", "text": "弱转强需要竞价超预期。", "expected": ["semantic_experience", "data_requirement_hint"]},
    {"category": "弱转强", "text": "竞价量决定弱转强可信度。", "expected": ["research_hypothesis", "data_requirement_hint"]},
    {"category": "龙头 / 主线", "text": "主线龙头的承接更强。", "expected": ["semantic_experience"]},
    {"category": "龙头 / 主线", "text": "最强题材才值得关注。", "expected": ["semantic_experience"]},
    {"category": "退潮 / 冰点", "text": "退潮期不要接高位。", "expected": ["research_hypothesis", "risk_control_hint"]},
    {"category": "退潮 / 冰点", "text": "冰点之后可能出现修复。", "expected": ["semantic_experience", "research_hypothesis"]},
    {"category": "放量 / 共振", "text": "突破必须放量确认。", "expected": ["rule_candidate"]},
    {"category": "放量 / 共振", "text": "指数跌破共振日低点立即退出。", "expected": ["executable_rule"]},
    {"category": "风控纪律", "text": "连续亏损后暂停交易。", "expected": ["risk_control_hint"]},
    {"category": "风控纪律", "text": "弱市只用小仓位试错。", "expected": ["risk_control_hint"]},
    {"category": "纯市场复盘", "text": "今天指数低开高走，午后回落。", "expected": ["research_hypothesis", "unusable_noise"]},
    {"category": "纯市场复盘", "text": "理解力才是复利的本质。", "expected": ["unusable_noise"]},
]


def article_taxonomy_output(primary_types: list[str]) -> dict[str, Any]:
    return {
        "prompt_version": "article_taxonomy_v1",
        "schema_version": "article_taxonomy_v1",
        "classification": {"article_type": "mixed", "confidence": 0.9, "evidence": ["fixture"]},
        "concept_extraction": {
            "prompt_version": "concept_extraction_v1",
            "schema_version": "concept_v1",
            "concepts": [], "trading_symbols": [], "indicators": [], "chart_patterns": [],
            "market_themes": [], "risk_concepts": [], "data_dependencies": [],
            "sentiment": {"score": 0.0, "confidence": 0.0}, "warnings": [],
        },
        "article_structure": {
            "prompt_version": "article_structure_extraction_v1",
            "schema_version": "article_structure_v1",
            "article_id": "11111111-1111-1111-1111-111111111111",
            "author_id": "author-1", "published_at": "2026-06-15T09:30:00Z",
            "article_type": "mixed", "method_tags": [], "analysis_dimensions": [],
            "instrument_focus": ["stock"],
            "holding_period": {"value": "unknown", "source": "unknown", "confidence": 0.0, "evidence": []},
            "entry_patterns": [], "exit_patterns": [], "risk_concepts": [], "data_dependencies": [],
            "market_state": {"status": "not_declared", "explicit_conditions": [], "inferred_hypotheses": []},
            "key_claims": [],
            "article_quality": {"information_density": "medium", "quantifiability": "medium", "duplicate_risk": "low", "needs_manual_review": False, "warnings": []},
        },
        "taxonomy_extraction": {
            "taxonomy_version": "extraction_taxonomy_v1",
            "schema_version": "extraction_item_v1",
            "extraction_items": [draft_for(primary_type) for primary_type in primary_types],
        },
        "explicit_preconditions": {
            "prompt_version": "explicit_precondition_extraction_v1",
            "schema_version": "explicit_precondition_v1",
            "status": "not_declared", "preconditions": [], "warnings": [],
        },
        "quality": {"needs_repair": False, "repair_reasons": [], "warnings": []},
    }
