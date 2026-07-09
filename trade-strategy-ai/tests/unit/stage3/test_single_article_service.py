from __future__ import annotations

from uuid import uuid4

from src.services.stage3_single_article_service import (
    determine_automatic_review,
    resolve_summary_provenance,
)


def _candidate_payload(
    *,
    backtestability_status: str = "executable",
    manual_review_required: bool = False,
    missing_fields: list[str] | None = None,
    ambiguous_terms: list[str] | None = None,
    data_dependencies: list[str] | None = None,
    risk_controls: object | None = None,
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
                "risk_controls": risk_controls or [],
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


def test_automatic_review_allows_light_ambiguous_terms_when_candidate_is_complete() -> None:
    result = determine_automatic_review(
        _candidate_payload(
            backtestability_status="partially_executable",
            manual_review_required=True,
            ambiguous_terms=["强势", "明显放量", "附近"],
        )
    )

    assert result.status == "pending_backtest"
    assert result.risk_level == "low"
    assert "含轻度模糊词：强势, 明显放量, 附近；保留追踪但不单独触发人工" in result.reasons
    assert "抽取层标记需人工复核，但仅命中可放行不确定性" in result.reasons


def test_automatic_review_requires_human_review_when_manual_review_reason_is_unknown() -> None:
    result = determine_automatic_review(
        _candidate_payload(manual_review_required=True)
    )

    assert result.status == "needs_human_review"
    assert result.risk_level == "medium"
    assert "抽取层标记需人工复核，且未提供可放行的轻度原因" in result.reasons


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
    assert "仍有核心缺失字段：threshold" in result.reasons
    assert "依赖 Kaipan 数据" in result.reasons


def test_automatic_review_requires_human_review_for_heavy_ambiguous_terms() -> None:
    result = determine_automatic_review(
        _candidate_payload(
            ambiguous_terms=["止损边界不明确", "仓位看情况"],
        )
    )

    assert result.status == "needs_human_review"
    assert result.risk_level == "medium"
    assert "存在重度模糊词：止损边界不明确, 仓位看情况" in result.reasons


def test_automatic_review_requires_human_review_for_subjective_risk_controls() -> None:
    result = determine_automatic_review(
        _candidate_payload(risk_controls=["严格止损", "仓位看情况"])
    )

    assert result.status == "needs_human_review"
    assert result.risk_level == "medium"
    assert "风险控制边界不明确：严格止损, 仓位看情况" in result.reasons


def test_automatic_review_allows_numeric_risk_controls_with_trace_reason() -> None:
    result = determine_automatic_review(
        _candidate_payload(
            manual_review_required=True,
            risk_controls=[{"stop_loss": "5%"}, {"position_size": "10%"}],
        )
    )

    assert result.status == "pending_backtest"
    assert result.risk_level == "low"
    assert "风险控制边界可解释：stop_loss:5%, position_size:10%；保留追踪" in result.reasons
    assert "抽取层标记需人工复核，但仅命中可放行不确定性" in result.reasons


def test_automatic_review_suggests_reject_when_material_evidence_is_missing() -> None:
    result = determine_automatic_review(_candidate_payload(evidence=[]))

    assert result.status == "suggested_reject"
    assert result.risk_level == "high"
    assert "缺少原文证据" in result.reasons


def test_automatic_review_suggests_reject_when_candidate_is_not_executable() -> None:
    result = determine_automatic_review(
        _candidate_payload(backtestability_status="not_executable")
    )

    assert result.status == "suggested_reject"
    assert result.risk_level == "high"
    assert "当前不可回测" in result.reasons


def test_resolve_summary_provenance_uses_current_article_summary_for_latest_revision() -> None:
    revision_id = uuid4()
    article = type("Article", (), {"summary": "最新摘要", "content_hash": "hash-new"})()
    revision = type("Revision", (), {"article_revision_id": revision_id, "content_hash": "hash-new", "source_payload": {}})()

    result = resolve_summary_provenance(article=article, revision=revision)

    assert result.summary == "最新摘要"
    assert result.source == "blog_article_current"
    assert result.available is True
    assert result.aligned is True
    assert result.article_revision_id == str(revision_id)
    assert result.content_hash == "hash-new"


def test_resolve_summary_provenance_prefers_revision_source_payload_for_older_revision() -> None:
    revision_id = uuid4()
    article = type("Article", (), {"summary": "当前文章新摘要", "content_hash": "hash-new"})()
    revision = type(
        "Revision",
        (),
        {
            "article_revision_id": revision_id,
            "content_hash": "hash-old",
            "source_payload": {"summary": "旧版本摘要"},
        },
    )()

    result = resolve_summary_provenance(article=article, revision=revision)

    assert result.summary == "旧版本摘要"
    assert result.source == "article_revision_source_payload"
    assert result.available is True
    assert result.aligned is True
    assert result.article_revision_id == str(revision_id)
    assert result.content_hash == "hash-old"


def test_resolve_summary_provenance_marks_unavailable_when_older_revision_has_no_frozen_summary() -> None:
    revision_id = uuid4()
    article = type("Article", (), {"summary": "当前文章新摘要", "content_hash": "hash-new"})()
    revision = type("Revision", (), {"article_revision_id": revision_id, "content_hash": "hash-old", "source_payload": {}})()

    result = resolve_summary_provenance(article=article, revision=revision)

    assert result.summary is None
    assert result.source == "unavailable"
    assert result.available is False
    assert result.aligned is False
    assert result.reason == "selected revision has no frozen summary"
