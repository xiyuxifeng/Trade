from __future__ import annotations

from pathlib import Path


def test_config_profile_migration_defines_expected_schema() -> None:
    """Config Profile 迁移应定义正式 Profile 表。"""
    migration_file = (
        Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026_05_16_0001_create_config_profiles_table.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert "revision = \"2026_05_16_0001\"" in content
    assert "down_revision = \"2026_05_11_0002\"" in content
    assert "config_profiles" in content
    assert "profile_id" in content
    assert "sections" in content
    assert "secret_refs" in content
    assert "validation_status" in content
    assert "archived_at" in content

