from __future__ import annotations

from datetime import date
from uuid import UUID

from src.schemas.contracts import DataRequest, DataResponse, DataResponseStatus, EvaluationResult
from src.schemas.contracts import TradeEntry, TradeIdea
from src.schemas.review_task import ReviewTaskDetails
from src.evaluation.failure_taxonomy import FailureAttribution


def test_data_request_and_response_support_stage1_datasets() -> None:
    request = DataRequest(
        request_id=UUID("00000000-0000-0000-0000-000000000001"),
        trader_id="trader_a",
        dataset="hot_topics",
        topic_ids=["theme-1", "theme-2"],
        indicator_names=["rsi", "macd"],
        snapshot_date=date(2026, 4, 22),
        fields=["last_price"],
    )

    response = DataResponse(
        request_id=request.request_id,
        status=DataResponseStatus.ok,
        dataset="hot_topics",
        available_datasets=["hot_topics", "topic_constituents", "strong_symbols", "ohlcv_1d", "indicators"],
    )

    assert request.dataset == "hot_topics"
    assert request.topic_ids == ["theme-1", "theme-2"]
    assert request.indicator_names == ["rsi", "macd"]
    assert request.snapshot_date == date(2026, 4, 22)
    assert response.dataset == "hot_topics"
    assert "indicators" in response.available_datasets


def test_trade_idea_supports_stage1_traceability_fields() -> None:
    idea = TradeIdea(
        trader_id="trader_a",
        as_of_date=date(2026, 4, 22),
        symbol="000001.SZ",
        entry=TradeEntry(type="limit", price=10.0),
        target_price=10.5,
        stop_loss_price=9.7,
        strategy_version_id="sv_001",
        source_topic_ids=["topic_1", "topic_2"],
        evidence_refs=["raw:hot_topics:2026-04-22_09-25:RealRankingInfo", "snapshot:strong_symbols:2026-04-22_09-25"],
        decision_mode="rule_based",
    )

    assert idea.strategy_version_id == "sv_001"
    assert idea.source_topic_ids == ["topic_1", "topic_2"]
    assert idea.evidence_refs[0].startswith("raw:")
    assert idea.decision_mode == "rule_based"


def test_evaluation_result_and_review_task_support_stage1_postmortem_fields() -> None:
    evaluation = EvaluationResult(
        as_of_date=date(2026, 4, 22),
        evidence_pack_refs=["evidence:1"],
        failure_categories=["regime_mismatch"],
        ranking_features={"mfe": 0.12, "mae": -0.03},
    )
    review_task = ReviewTaskDetails(
        trigger_reason="loss",
        source_idea_id=UUID("00000000-0000-0000-0000-000000000002"),
        symbol="000001.SZ",
        trader_id="trader_a",
        evaluation_snapshot={
            "idea_id": "00000000-0000-0000-0000-000000000002",
            "symbol": "000001.SZ",
            "entry_price": 10.0,
            "current_price": 9.5,
            "return_pct": -0.05,
            "threshold": 0.0,
            "as_of_date": "2026-04-22",
        },
        evidence_refs=["evidence:1"],
        failure_attribution=FailureAttribution(
            root_causes=["entry_timing_poor"],
            stage="stage:entry",
            rule_type="rule_type:entry",
        ),
        ranking_features={"mfe": 0.12, "mae": -0.03},
    )

    assert evaluation.evidence_pack_refs == ["evidence:1"]
    assert evaluation.failure_categories == ["regime_mismatch"]
    assert evaluation.ranking_features["mfe"] == 0.12
    assert review_task.evidence_refs == ["evidence:1"]
    assert review_task.failure_attribution.root_causes == ["entry_timing_poor"]
    assert review_task.failure_attribution.stage == "stage:entry"
    assert review_task.ranking_features["mae"] == -0.03
