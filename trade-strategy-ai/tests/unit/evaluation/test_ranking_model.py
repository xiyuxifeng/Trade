"""验证 RankingEntryRecord ORM 模型可正常导入和实例化。"""
import pytest
from src.models.ranking_entry import RankingEntryRecord
from src.models.base import Base


def test_ranking_entry_record_tablename():
    assert RankingEntryRecord.__tablename__ == "ranking_entries"


def test_ranking_entry_record_columns():
    """验证关键列存在。"""
    cols = [c.name for c in RankingEntryRecord.__table__.columns]
    assert "entry_id" in cols
    assert "trade_date" in cols
    assert "trader_id" in cols
    assert "strategy_version_id" in cols
    assert "symbol" in cols
    assert "return_pct" in cols
    assert "mfe" in cols
    assert "mae" in cols
    assert "composite_score" in cols
    assert "rank" in cols
    assert "is_latest" in cols
    assert "attribution_source" in cols


def test_ranking_entry_unique_constraint():
    """验证唯一约束存在。"""
    constraints = RankingEntryRecord.__table__.constraints
    uq_names = [c.name for c in constraints if c.name == "uq_ranking_entry"]
    assert len(uq_names) == 1