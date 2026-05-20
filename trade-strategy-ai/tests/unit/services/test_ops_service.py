from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

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
    assert result.payload["items"][0]["backup_id"] == "20260511-080000"
    assert result.payload["items"][0]["name"] == "20260511-080000"
    assert result.payload["items"][0]["include_processed"] is True
    assert result.payload["items"][0]["processed_copied"] is True


def test_ops_recovery_service_lists_backup_targets(tmp_path: Path) -> None:
    """OpsRecoveryService 应列出创建备份时允许选择的白名单目录。"""
    service = OpsRecoveryService(base_dir=tmp_path, backup_root=tmp_path / "data" / "backups")
    result = service.list_backup_targets()

    assert result.status == "ok"
    assert result.payload["count"] == 1
    assert result.payload["items"][0]["id"] == "default"
    assert result.payload["items"][0]["path"] == str(tmp_path / "data" / "backups")


@pytest.mark.asyncio
async def test_ops_recovery_service_recover_stale_jobs_delegates_to_job_service(tmp_path: Path) -> None:
    """OpsRecoveryService 应把 stale 回收请求委托给 JobService。"""
    calls: list[dict[str, object]] = []

    class _FakeJobService:
        async def recover_stale_jobs(self, *, stale_before, actor=None, audit_source=None):
            calls.append(
                {
                    "stale_before": stale_before,
                    "actor": actor,
                    "audit_source": audit_source,
                }
            )
            return SimpleNamespace(
                status="ok",
                message="stale jobs recovered",
                payload={"count": 2, "job_ids": ["job-1", "job-2"]},
                warnings=[],
            )

    fake_job_service = _FakeJobService()
    service = OpsRecoveryService(base_dir=tmp_path, backup_root=tmp_path / "data" / "backups", job_service=fake_job_service)  # type: ignore[arg-type]
    result = await service.recover_stale_jobs(stale_before_minutes=12, actor="ui.ops", audit_source={"channel": "ui"})

    assert result.status == "ok"
    assert result.payload["count"] == 2
    assert result.payload["stale_before_minutes"] == 12
    assert calls[0]["actor"] == "ui.ops"
    assert calls[0]["audit_source"] == {"channel": "ui"}
