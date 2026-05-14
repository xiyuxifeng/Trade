from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.common.paths import resolve_project_path
from src.services.base import BaseService, ServiceResult
from src.services.config_service import ConfigService


def _stable_json(value: Any) -> str:
    """把配置对象规范化为稳定的 JSON 字符串，便于生成 hash。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class ConfigSnapshotService(BaseService):
    """配置快照服务。

    负责把运行时配置转成可追溯、可脱敏、可落盘的快照摘要。
    """

    service_name = "config-snapshot"

    def __init__(
        self,
        *,
        config_service: ConfigService | None = None,
        snapshot_root: str | Path | None = None,
    ) -> None:
        self._config_service = config_service or ConfigService()
        self._snapshot_root = resolve_project_path(snapshot_root or "data/config_snapshots")

    def _snapshot_path(self, job_id: str | None, config_hash: str) -> Path:
        """返回快照文件路径。"""
        name = f"{job_id}.json" if job_id else f"{config_hash}.json"
        return self._snapshot_root / name

    def capture_config_snapshot(self, config_path: str | Path, *, job_id: str | None = None) -> ServiceResult:
        """读取配置并生成脱敏快照。"""
        resolved = Path(config_path).expanduser().resolve()
        if not resolved.exists():
            return ServiceResult(
                status="error",
                message="config file missing",
                payload={"config_path": str(resolved), "job_id": job_id},
            )

        loaded = self._config_service.load_config(resolved)
        normalized_config = loaded.config.model_dump(mode="json")
        config_hash = hashlib.sha256(_stable_json(normalized_config).encode("utf-8")).hexdigest()
        masked_snapshot = self._config_service.mask_config(normalized_config)
        captured_at = datetime.now(UTC).isoformat()
        snapshot_path = self._snapshot_path(job_id, config_hash)
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_payload = {
            "config_snapshot_id": config_hash,
            "job_id": job_id,
            "config_path": str(resolved),
            "config_source": str(loaded.config_path),
            "config_hash": config_hash,
            "masked_snapshot": masked_snapshot,
            "captured_at": captured_at,
        }
        snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return ServiceResult(
            status="ok",
            message="config snapshot captured",
            payload={
                **snapshot_payload,
                "snapshot_path": str(snapshot_path),
            },
        )

