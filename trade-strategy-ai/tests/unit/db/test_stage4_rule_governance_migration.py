from __future__ import annotations

from pathlib import Path


def test_stage4_rule_governance_migration_defines_source_links_and_backfill() -> None:
    migration_file = (
        Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026_06_16_0007_stage4_rule_governance.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert 'revision = "2026_06_16_0007"' in content
    assert 'down_revision = "2026_06_14_0006"' in content
    assert "rule_version_source_links" in content
    assert "rule_families" in content
    assert "rule_family_memberships" in content
    assert "uq_rvsl_rule_version_candidate" in content
    assert "uq_rvsl_candidate_version" in content
    assert "UPDATE rule_candidates" in content
    assert "candidate_fingerprint" in content
