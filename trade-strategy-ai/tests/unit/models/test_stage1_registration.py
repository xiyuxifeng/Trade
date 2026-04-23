from __future__ import annotations

from src.models import HotTopicsSnapshot, StrongSymbolsSnapshot, TopicConstituentsSnapshot, TraderStrategyVersion
from src.models.base import Base


def test_stage1_models_are_registered_in_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())

    assert "trader_strategy_versions" in table_names
    assert "hot_topics_snapshots" in table_names
    assert "topic_constituents_snapshots" in table_names
    assert "strong_symbols_snapshots" in table_names


def test_stage1_models_are_exported_from_models_package() -> None:
    assert TraderStrategyVersion.__tablename__ == "trader_strategy_versions"
    assert HotTopicsSnapshot.__tablename__ == "hot_topics_snapshots"
    assert TopicConstituentsSnapshot.__tablename__ == "topic_constituents_snapshots"
    assert StrongSymbolsSnapshot.__tablename__ == "strong_symbols_snapshots"
