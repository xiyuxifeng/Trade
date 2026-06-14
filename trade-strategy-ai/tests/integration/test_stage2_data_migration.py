from __future__ import annotations

from pathlib import Path

from src.migrations.stage2_data_migration import (
    InMemoryStage2MigrationStore,
    Stage2MigrationFixture,
    Stage2MigrationRunner,
)


def test_stage2_data_migration_end_to_end_generates_reports_and_recovery_export(tmp_path: Path) -> None:
    store = InMemoryStage2MigrationStore(Stage2MigrationFixture.sample())
    runner = Stage2MigrationRunner(store=store, report_dir=tmp_path, batch_size=2)

    dry_run = runner.run_sync(mode="dry-run")
    apply_report = runner.run_sync(mode="apply")
    verify_report = runner.run_sync(mode="verify")

    assert dry_run.status == "completed"
    assert apply_report.status == "completed"
    assert verify_report.status == "completed"
    assert (tmp_path / "preflight_inventory.json").exists()
    assert (tmp_path / "dry_run_report.json").exists()
    assert (tmp_path / "apply_report.json").exists()
    assert (tmp_path / "verify_report.json").exists()
    assert (tmp_path / "recovery_export.json").exists()
    assert store.has_orphan_foreign_keys() is False
