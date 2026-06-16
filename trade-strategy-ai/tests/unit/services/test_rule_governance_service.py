from __future__ import annotations

from src.services.rule_governance_service import compare_rule_payloads, fingerprint_rule_payload


def _payload(
    *,
    title: str = "放量突破介入",
    threshold: float = 1.5,
    side: str = "buy",
    timeframe: str = "5m",
) -> dict:
    return {
        "title": title,
        "description": "不同文案不应改变正式语义",
        "rule_type": "entry",
        "instrument_focus": ["stock"],
        "timeframe": timeframe,
        "holding_period": "intraday",
        "condition": {
            "logic": "single",
            "clauses": [
                {
                    "field": "volume",
                    "operator": "gt",
                    "value": threshold,
                    "unit": "x",
                    "lookback": 5,
                    "raw_expression": "放量",
                }
            ],
        },
        "action": {"type": "enter", "side": side, "price_reference": "market"},
        "risk_controls": [],
        "data_dependencies": ["ohlcv_1d"],
        "market_state_applicability": {"status": "not_declared", "explicit_conditions": [], "inferred_hypotheses": []},
        "quantification": {"status": "executable", "missing_fields": [], "ambiguous_terms": [], "manual_review_required": False},
        "evidence": [{"quote": "放量突破介入", "supports": "condition"}],
    }


def test_fingerprint_is_stable_for_semantically_equivalent_rules() -> None:
    baseline = fingerprint_rule_payload(_payload(title="放量突破介入"))
    rewritten = fingerprint_rule_payload(_payload(title="成交量放大时进场"))

    assert baseline.exact_fingerprint == rewritten.exact_fingerprint
    assert baseline.family_fingerprint == rewritten.family_fingerprint
    assert baseline.algorithm_version == rewritten.algorithm_version


def test_compare_rule_payloads_distinguishes_duplicate_variant_and_conflict() -> None:
    duplicate = compare_rule_payloads(_payload(), _payload(title="改个标题"))
    variant = compare_rule_payloads(_payload(), _payload(threshold=2.0))
    conflict = compare_rule_payloads(_payload(), _payload(side="sell"))

    assert duplicate.relation == "exact_duplicate"
    assert duplicate.parameter_differences == {}

    assert variant.relation == "parameter_variant"
    assert "condition.clauses[0].value" in variant.parameter_differences

    assert conflict.relation == "conflict"
    assert "action.side" in conflict.conflict_reasons
