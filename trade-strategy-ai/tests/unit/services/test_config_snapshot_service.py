from __future__ import annotations

from pathlib import Path


def test_config_snapshot_service_captures_masked_snapshot(tmp_path: Path) -> None:
    """ConfigSnapshotService 应生成脱敏快照与稳定摘要。"""
    from src.services.config_snapshot_service import ConfigSnapshotService

    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
database:
  url: postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai
llm:
  api_key: secret-key
""",
        encoding="utf-8",
    )

    service = ConfigSnapshotService(snapshot_root=tmp_path / "snapshots")
    result = service.capture_config_snapshot(config_path, job_id="job-001")

    assert result.status == "ok"
    assert result.payload["config_source"] == str(config_path.resolve())
    assert result.payload["config_hash"]
    assert result.payload["masked_snapshot"]["llm"]["api_key"] == "***"
    assert result.payload["masked_snapshot"]["database"]["url"].startswith("postgresql+asyncpg://trade:")
    assert result.payload["snapshot_path"].endswith("job-001.json")


def test_config_snapshot_service_rejects_missing_config_file(tmp_path: Path) -> None:
    """缺失配置文件时应返回结构化错误。"""
    from src.services.config_snapshot_service import ConfigSnapshotService

    service = ConfigSnapshotService(snapshot_root=tmp_path / "snapshots")
    result = service.capture_config_snapshot(tmp_path / "missing.yaml", job_id="job-002")

    assert result.status == "error"
    assert result.message == "config file missing"

