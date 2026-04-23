from __future__ import annotations

from src.models.hot_topics_snapshot import HotTopicsSnapshot
from src.models.signal import Signal
from src.models.strong_symbols_snapshot import StrongSymbolsSnapshot
from src.models.topic_constituents_snapshot import TopicConstituentsSnapshot
from src.models.trader_strategy_version import TraderStrategyVersion


def test_trader_strategy_version_table_metadata() -> None:
    assert TraderStrategyVersion.__tablename__ == "trader_strategy_versions"
    column_names = set(TraderStrategyVersion.__table__.columns.keys())
    assert {"trader_id", "strategy_date", "status", "evidence_refs", "source_article_ids"} <= column_names

    constraint_names = {constraint.name for constraint in TraderStrategyVersion.__table__.constraints}
    assert "uq_trader_strategy_versions_trader_id_strategy_date_version_name" in constraint_names


def test_stage1_snapshot_tables_have_daily_identity() -> None:
    for model in (HotTopicsSnapshot, TopicConstituentsSnapshot, StrongSymbolsSnapshot):
        column_names = set(model.__table__.columns.keys())
        assert {"trade_date", "slot", "source", "dataset_version", "payload"} <= column_names


def test_signal_tracks_strategy_version_and_review_context() -> None:
    column_names = set(Signal.__table__.columns.keys())
    assert {"trader_id", "strategy_version_id", "source_topic_ids", "evidence_refs", "decision_mode", "evaluation_result_id"} <= column_names

    signal = Signal(
        signal_id="signal-001",
        symbol="000001.SZ",
        side="BUY",
        confidence=0.5,
        trader_id="trader_a",
        strategy_version_id="sv_001",
        source_topic_ids=["topic_1"],
        evidence_refs=["evidence:1"],
        decision_mode="rule_based",
        evaluation_result_id="er_001",
    )

    result = signal.to_dict()
    assert result["trader_id"] == "trader_a"
    assert result["strategy_version_id"] == "sv_001"
    assert result["source_topic_ids"] == ["topic_1"]
    assert result["evaluation_result_id"] == "er_001"
