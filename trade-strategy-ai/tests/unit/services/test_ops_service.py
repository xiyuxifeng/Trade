from __future__ import annotations

from pathlib import Path

from src.services.ops_service import OpsRecoveryService


def test_ops_recovery_service_lists_manifest_backups(tmp_path: Path) -> None:
    """OpsRecoveryService 应列出可恢复的备份包。"""
    backup_dir = tmp_path / "data" / "backups" / "20260511-080000"
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "manifest.json").write_text(
        """
        {
          "schema_version": "v1",
          "created_at": "2026-05-11T08:00:00Z",
          "tables": ["jobs", "artifacts"],
          "row_counts": {"jobs": 1, "artifacts": 2},
          "include_processed": true,
          "processed_copied": true
        }
        """,
        encoding="utf-8",
    )
    (backup_dir / "db").mkdir(parents=True, exist_ok=True)
    (backup_dir / "db" / "jobs.json").write_text("[]", encoding="utf-8")

    service = OpsRecoveryService(base_dir=tmp_path, backup_root=tmp_path / "data" / "backups")
    result = service.list_backups()

    assert result.status == "ok"
    assert result.payload["count"] == 1
    assert result.payload["items"][0]["name"] == "20260511-080000"
    assert result.payload["items"][0]["include_processed"] is True
    assert result.payload["items"][0]["processed_copied"] is True
