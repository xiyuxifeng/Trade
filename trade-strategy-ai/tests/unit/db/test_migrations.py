from __future__ import annotations

from pathlib import Path


def test_job_audit_events_migration_defines_expected_schema() -> None:
    """验证 Job 审计表迁移定义与约定一致。"""
    migration_file = (
        Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026_05_10_0002_add_job_audit_events.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert "revision = \"2026_05_10_0002\"" in content
    assert "down_revision = \"2026_05_08_0001\"" in content
    assert "job_audit_events" in content
    assert "job_id" in content
    assert "params_summary" in content
    assert "source" in content
    assert "event_at" in content
    assert "ix_job_audit_events_job_id_created_at" in content
    assert "ix_job_audit_events_operation_created_at" in content
