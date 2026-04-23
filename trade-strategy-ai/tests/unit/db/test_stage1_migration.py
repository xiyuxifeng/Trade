from __future__ import annotations

from pathlib import Path


def test_stage1_migration_defines_new_tables_and_signal_columns() -> None:
    migration_path = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "db"
        / "migrations"
        / "versions"
        / "2026_04_23_0001_add_stage1_models_and_signal_tracking.py"
    )
    content = migration_path.read_text(encoding="utf-8")

    assert "trader_strategy_versions" in content
    assert "hot_topics_snapshots" in content
    assert "topic_constituents_snapshots" in content
    assert "strong_symbols_snapshots" in content
    assert "op.add_column('signals'" in content or 'op.add_column("signals"' in content
    assert "strategy_version_id" in content
    assert "evidence_refs" in content
