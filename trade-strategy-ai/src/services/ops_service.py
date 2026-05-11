from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config.database import get_engine
from src.audit.service import AuditService
from src.backup.service import BackupStats, RestoreStats, backup_project_state, restore_project_state
from src.common.paths import resolve_project_path
from src.common.utils import read_json
from src.services.base import BaseService, ServiceResult


def _is_within(path: Path, root: Path) -> bool:
    """判断路径是否位于指定根目录下。"""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _dir_size_bytes(path: Path) -> int:
    """统计目录中文件总大小。"""
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


class OpsRecoveryService(BaseService):
    """项目级备份、恢复和回滚演练服务。"""

    service_name = "ops-recovery"

    def __init__(
        self,
        *,
        base_dir: str | Path | None = None,
        backup_root: str | Path | None = None,
        engine: Any | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self._base_dir = resolve_project_path(base_dir or None)
        self._backup_root = resolve_project_path(backup_root or "data/backups")
        self._engine = engine or get_engine()
        self._audit_service = audit_service or AuditService()

    def _resolve_backup_dir(self, value: str | Path | None) -> Path:
        """解析并校验备份目录。"""
        if value is None:
            return self._backup_root
        resolved = resolve_project_path(value)
        if not _is_within(resolved, self._backup_root):
            raise ValueError("backup path must stay within backup root")
        return resolved

    def _backup_item(self, backup_dir: Path) -> dict[str, Any] | None:
        """把一个备份目录整理成 UI 可展示的条目。"""
        manifest_path = backup_dir / "manifest.json"
        if not manifest_path.exists():
            return None

        manifest = read_json(manifest_path)
        stat = backup_dir.stat()
        return {
            "path": str(backup_dir),
            "name": backup_dir.name,
            "size_bytes": _dir_size_bytes(backup_dir),
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
            "tables": manifest.get("tables", []),
            "row_counts": manifest.get("row_counts", {}),
            "include_processed": bool(manifest.get("include_processed", True)),
            "processed_copied": bool(manifest.get("processed_copied", False)),
        }

    def list_backups(self) -> ServiceResult:
        """列出项目级备份包。"""
        if not self._backup_root.exists():
            return ServiceResult(
                status="ok",
                message="backup packages listed",
                payload={"base_dir": str(self._base_dir), "backup_root": str(self._backup_root), "count": 0, "items": []},
            )

        items: list[dict[str, Any]] = []
        for backup_dir in sorted((item for item in self._backup_root.iterdir() if item.is_dir()), key=lambda item: item.name, reverse=True):
            payload = self._backup_item(backup_dir)
            if payload is not None:
                items.append(payload)

        return ServiceResult(
            status="ok",
            message="backup packages listed",
            payload={
                "base_dir": str(self._base_dir),
                "backup_root": str(self._backup_root),
                "count": len(items),
                "items": items,
            },
        )

    async def create_backup(self, *, include_processed: bool = True, backup_dir: str | Path | None = None) -> ServiceResult:
        """创建项目级备份。"""
        resolved_backup_dir = self._resolve_backup_dir(backup_dir) if backup_dir is not None else None
        stats: BackupStats = await backup_project_state(
            base_dir=self._base_dir,
            backup_dir=resolved_backup_dir,
            engine=self._engine,
            include_processed=include_processed,
            audit_service=self._audit_service,
        )
        item = self._backup_item(stats.backup_dir)
        payload = asdict(stats)
        payload["backup_dir"] = str(stats.backup_dir)
        payload["include_processed"] = include_processed
        payload["backup_item"] = item
        return ServiceResult(status="ok", message="project backup created", payload=payload)

    async def restore_backup(
        self,
        *,
        backup_path: str | Path,
        include_processed: bool = True,
        confirmed: bool = False,
    ) -> ServiceResult:
        """恢复项目级备份。"""
        if not confirmed:
            return ServiceResult(status="error", message="confirmation required", payload={"confirmed": confirmed})

        resolved_backup_dir = self._resolve_backup_dir(backup_path)
        if not resolved_backup_dir.exists():
            return ServiceResult(status="error", message="backup package not found", payload={"backup_path": str(resolved_backup_dir)})

        try:
            stats: RestoreStats = await restore_project_state(
                base_dir=self._base_dir,
                backup_dir=resolved_backup_dir,
                engine=self._engine,
                include_processed=include_processed,
                force=True,
                audit_service=self._audit_service,
            )
        except FileNotFoundError:
            return ServiceResult(status="error", message="backup package not found", payload={"backup_path": str(resolved_backup_dir)})
        except FileExistsError as exc:
            return ServiceResult(status="error", message=str(exc), payload={"backup_path": str(resolved_backup_dir)})

        payload = asdict(stats)
        payload["backup_dir"] = str(stats.backup_dir)
        payload["include_processed"] = include_processed
        payload["backup_item"] = self._backup_item(resolved_backup_dir)
        return ServiceResult(status="ok", message="project backup restored", payload=payload)


def get_ops_recovery_service() -> OpsRecoveryService:
    """返回项目级备份恢复服务。"""
    return OpsRecoveryService()
