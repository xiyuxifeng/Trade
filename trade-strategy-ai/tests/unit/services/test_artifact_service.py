from __future__ import annotations

import asyncio
from pathlib import Path


def test_artifact_service_discovers_and_previews_files(tmp_path: Path) -> None:
    """ArtifactService 应能发现主要产物并生成预览。"""
    from src.services.artifact_service import ArtifactService

    jobs_root = tmp_path / "data" / "jobs"
    job_id = "job-123"
    job_dir = jobs_root / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "result.json").write_text('{"status": "ok", "value": 1}', encoding="utf-8")
    (job_dir / "artifacts.json").write_text("[]", encoding="utf-8")

    processed_root = tmp_path / "data" / "processed"
    processed_root.mkdir(parents=True, exist_ok=True)
    (processed_root / "daily_report.html").write_text("<html><body>report</body></html>", encoding="utf-8")

    backups_root = tmp_path / "data" / "backups"
    backups_root.mkdir(parents=True, exist_ok=True)
    (backups_root / "backup.tar.gz").write_bytes(b"fake-archive")

    config_backups_root = tmp_path / "config" / "backups"
    config_backups_root.mkdir(parents=True, exist_ok=True)
    (config_backups_root / "app.yaml").write_text("secret: should-not-be-indexed", encoding="utf-8")

    service = ArtifactService(
        roots=[
            jobs_root,
            processed_root,
            backups_root,
        ]
    )

    listed = asyncio.run(service.list_artifacts())
    items = listed.payload["items"]
    by_name = {item["name"]: item for item in items}

    assert listed.status == "ok"
    assert by_name["result.json"]["job_id"] == job_id
    assert by_name["result.json"]["kind"] == "json"
    assert "path" not in by_name["result.json"]
    assert by_name["result.json"]["safe_download_url"].endswith(f"/artifacts/{by_name['result.json']['artifact_id']}/download")
    assert by_name["daily_report.html"]["previewable"] is True
    assert by_name["backup.tar.gz"]["kind"] == "tar.gz"
    assert "app.yaml" not in by_name

    detail = asyncio.run(service.get_artifact(by_name["result.json"]["artifact_id"]))
    assert detail.status == "ok"
    assert "preview" in detail.payload
    assert '"status": "ok"' in detail.payload["preview"]
    assert "path" not in detail.payload
    assert detail.payload["safe_download_url"].endswith(f"/artifacts/{by_name['result.json']['artifact_id']}/download")
    assert detail.payload["artifact_ref"]["artifact_id"] == by_name["result.json"]["artifact_id"]
    assert service.is_download_path_allowed(job_dir / "result.json") is True
    assert service.is_download_path_allowed(tmp_path / "outside.json") is False

    download_path = service.resolve_download_path(by_name["result.json"]["artifact_id"])
    assert download_path == job_dir / "result.json"
