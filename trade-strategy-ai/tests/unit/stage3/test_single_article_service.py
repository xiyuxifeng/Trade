from __future__ import annotations

from uuid import uuid4

from src.services.stage3_single_article_service import determine_automatic_review


def _candidate_payload(
    *,
    backtestability_status: str = "executable",
    manual_review_required: bool = False,
    missing_fields: list[str] | None = None,
    ambiguous_terms: list[str] | None = None,
    data_dependencies: list[str] | None = None,
    evidence: list[dict] | None = None,
) -> object:
    return type(
        "Candidate",
        (),
        {
            "rule_candidate_id": uuid4(),
            "candidate_index": 0,
            "rule_type": "entry",
            "candidate_fingerprint": "fp-1",
            "backtestability_status": backtestability_status,
            "canonical_payload": {
                "title": "测试规则",
                "condition": {"logic": "single", "clauses": [{"field": "price"}]},
                "action": {"type": "enter", "side": "buy"},
                "quantification": {
                    "status": backtestability_status,
                    "manual_review_required": manual_review_required,
                    "missing_fields": missing_fields or [],
                    "ambiguous_terms": ambiguous_terms or [],
                },
                "market_state_applicability": {"status": "not_declared"},
                "risk_controls": [],
                "data_dependencies": data_dependencies or ["ohlcv_1d"],
                "evidence": evidence if evidence is not None else [{"quote": "原文", "supports": "condition"}],
            },
            "data_dependencies": {"required": data_dependencies or ["ohlcv_1d"]},
            "evidence_json": {"items": evidence if evidence is not None else [{"quote": "原文", "supports": "condition"}]},
        },
    )()


def test_automatic_review_marks_clean_candidate_as_pending_backtest() -> None:
    result = determine_automatic_review(_candidate_payload())

    assert result.status == "pending_backtest"
    assert result.risk_level == "low"
    assert result.kaipan_dependency is False


def test_automatic_review_requires_human_review_for_partial_or_kaipan_candidates() -> None:
    result = determine_automatic_review(
        _candidate_payload(
            backtestability_status="partially_executable",
            manual_review_required=True,
            missing_fields=["threshold"],
            ambiguous_terms=["放量"],
            data_dependencies=["ohlcv_1d", "kaipan_opening_flow"],
        )
    )

    assert result.status == "needs_human_review"
    assert result.risk_level == "medium"
    assert result.kaipan_dependency is True
    assert "量化条件仍需人工确认" in result.reasons


def test_automatic_review_suggests_reject_when_material_evidence_is_missing() -> None:
    result = determine_automatic_review(_candidate_payload(evidence=[]))

    assert result.status == "suggested_reject"
    assert result.risk_level == "high"
    assert "缺少原文证据" in result.reasons
