from __future__ import annotations

from pathlib import Path

from scripts.migrate_stage2_data import main
from src.migrations.stage2_data_migration import (
    InMemoryStage2MigrationStore,
    Stage2MigrationCategory,
    Stage2MigrationFixture,
    Stage2MigrationRunner,
)


def _fixture() -> Stage2MigrationFixture:
    return Stage2MigrationFixture.sample()


def test_dry_run_report_includes_required_fields_for_every_category(tmp_path: Path) -> None:
    runner = Stage2MigrationRunner(
        store=InMemoryStage2MigrationStore(_fixture()),
        report_dir=tmp_path,
        batch_size=2,
    )

    report = runner.run_sync(mode="dry-run")

    required_fields = {
        "source_count",
        "eligible_count",
        "migrated_count",
        "skipped_idempotent_count",
        "rejected_count",
        "conflict_count",
        "target_count_before",
        "target_count_after",
        "quality_status_counts",
        "orphan_count",
        "hash_mismatch_count",
    }
    assert report.mode == "dry-run"
    assert {category.value for category in Stage2MigrationCategory} == set(report.categories)
    for payload in report.categories.values():
        assert required_fields.issubset(payload)


def test_apply_is_idempotent_and_preserves_single_legacy_mapping(tmp_path: Path) -> None:
    store = InMemoryStage2MigrationStore(_fixture())
    runner = Stage2MigrationRunner(store=store, report_dir=tmp_path, batch_size=2)

    first_report = runner.run_sync(mode="apply")
    second_report = runner.run_sync(mode="apply")

    assert first_report.categories["articles"]["migrated_count"] == 2
    assert second_report.categories["articles"]["migrated_count"] == 0
    assert second_report.categories["articles"]["skipped_idempotent_count"] == 2
    assert store.has_duplicate_legacy_mappings() is False


def test_second_apply_reports_only_idempotent_skips_for_all_migrated_categories(tmp_path: Path) -> None:
    store = InMemoryStage2MigrationStore(_fixture())
    runner = Stage2MigrationRunner(store=store, report_dir=tmp_path, batch_size=2)

    runner.run_sync(mode="apply")
    second_report = runner.run_sync(mode="apply")

    for category in ("articles", "article_analysis", "rules", "backtests", "market_data"):
        assert second_report.categories[category]["migrated_count"] == 0
        assert second_report.categories[category]["skipped_idempotent_count"] == second_report.categories[category]["eligible_count"]


def test_apply_resume_continues_from_saved_cursor_after_injected_failure(tmp_path: Path) -> None:
    store = InMemoryStage2MigrationStore(_fixture())
    runner = Stage2MigrationRunner(
        store=store,
        report_dir=tmp_path,
        batch_size=1,
        fail_after_items=2,
    )

    failed = runner.run_sync(mode="apply")
    assert failed.status == "failed"

    resumed = Stage2MigrationRunner(
        store=store,
        report_dir=tmp_path,
        batch_size=1,
    ).run_sync(mode="resume")

    assert resumed.status == "completed"
    assert resumed.categories["articles"]["target_count_after"] == 2
    assert resumed.categories["article_analysis"]["migrated_count"] >= 2


def test_stage2_migration_cli_supports_required_modes(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, int, Path]] = []

    class _FakeRunner:
        def __init__(self, *, report_dir: Path, batch_size: int, mode: str | None = None, **_: object) -> None:
            self.report_dir = report_dir
            self.batch_size = batch_size
            self.mode = mode

        def run_sync(self, *, mode: str):
            calls.append((mode, self.batch_size, self.report_dir))

            class _Result:
                status = "completed"

            return _Result()

    monkeypatch.setattr("scripts.migrate_stage2_data.Stage2MigrationRunner", _FakeRunner)
    monkeypatch.setattr("scripts.migrate_stage2_data.build_default_store", lambda: object())

    assert main(["--dry-run", "--report-dir", str(tmp_path)]) == 0
    assert main(["--apply", "--batch-size", "50", "--report-dir", str(tmp_path)]) == 0
    assert main(["--verify", "--report-dir", str(tmp_path)]) == 0
    assert main(["--resume", "--report-dir", str(tmp_path)]) == 0

    assert calls == [
        ("dry-run", 100, tmp_path),
        ("apply", 50, tmp_path),
        ("verify", 100, tmp_path),
        ("resume", 100, tmp_path),
    ]
