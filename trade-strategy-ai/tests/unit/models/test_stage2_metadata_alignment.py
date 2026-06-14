from __future__ import annotations

from sqlalchemy.types import JSON


def test_metadata_registers_existing_legacy_tables() -> None:
    from src.models.base import Base
    import src.models as models  # noqa: F401

    expected_tables = {
        "alert_history",
        "article_classification",
        "evidence_packs",
        "market_data",
        "rule_pool",
        "topic_mapping",
        "trade_sample",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_trader_strategy_version_uses_existing_database_constraint_names() -> None:
    from src.models.trader_strategy_version import TraderStrategyVersion

    constraint_names = {constraint.name for constraint in TraderStrategyVersion.__table__.constraints}
    index_names = {index.name for index in TraderStrategyVersion.__table__.indexes}

    assert "uq_tsv_trader_dt_ver" in constraint_names
    assert "uq_trader_strategy_versions_trader_id_strategy_date_version_name" not in constraint_names
    assert "ix_trader_strategy_versions_version_type" in index_names
    assert "ux_trader_strategy_versions_one_released_per_day" in index_names


def test_article_metadata_json_columns_match_legacy_storage_types() -> None:
    from src.models.article_metadata import ArticleMetadata

    for column_name in (
        "extracted_concepts",
        "trading_symbols",
        "strategy_rules",
        "preconditions",
        "comment_insights",
        "raw_llm_output",
        "standalone_rule_ids",
        "derived_rule_ids",
        "trade_sample_ids",
    ):
        assert isinstance(ArticleMetadata.__table__.c[column_name].type, JSON)


def test_trade_log_model_retains_stage1_additive_fields() -> None:
    from src.models.trade_log import TradeLog

    assert {
        "source",
        "market",
        "position_side",
        "order_type",
        "currency",
        "strategy_tag",
        "rationale",
    }.issubset(TradeLog.__table__.columns.keys())
