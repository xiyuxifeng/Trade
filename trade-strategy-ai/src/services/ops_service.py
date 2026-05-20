from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from config.database import get_engine
from src.audit.service import AuditService
from src.backup.service import BackupStats, RestoreStats, backup_project_state, restore_project_state
from src.common.paths import resolve_project_path
from src.common.utils import read_json
from src.services.job_service import JobService
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
        job_service: JobService | None = None,
    ) -> None:
        self._base_dir = resolve_project_path(base_dir or None)
        self._backup_root = resolve_project_path(backup_root or "data/backups")
        self._engine = engine or get_engine()
        self._audit_service = audit_service or AuditService()
        self._job_service = job_service or JobService()

    def _resolve_backup_dir(self, value: str | Path | None) -> Path:
        """解析并校验备份目录。"""
        if value is None:
            return self._backup_root
        resolved = resolve_project_path(value)
        if not _is_within(resolved, self._backup_root):
            raise ValueError("backup path must stay within backup root")
        return resolved

    def _backup_targets(self) -> list[dict[str, Any]]:
        """返回可用于创建备份的白名单目标。"""
        return [
            {
                "id": "default",
                "label": "默认备份目录",
                "description": "使用系统自动生成的时间戳目录",
                "path": str(self._backup_root),
                "mode": "auto",
            },
        ]

    def _resolve_backup_target(self, value: str | None) -> Path | None:
        """把白名单目标转换为实际目录。"""
        if value is None or value == "default":
            return None

        for target in self._backup_targets():
            if target["id"] == value:
                target_path = Path(target["path"])
                if target.get("mode") == "auto":
                    return None
                return self._resolve_backup_dir(target_path)

        raise ValueError("backup target is not in whitelist")

    def _resolve_backup_item_dir(self, backup_id: str | None) -> Path:
        """按备份 ID 解析备份包目录。"""
        if not backup_id:
            raise ValueError("backup id is required")
        resolved = self._resolve_backup_dir(self._backup_root / backup_id)
        return resolved

    def _backup_item(self, backup_dir: Path) -> dict[str, Any] | None:
        """把一个备份目录整理成 UI 可展示的条目。"""
        manifest_path = backup_dir / "manifest.json"
        if not manifest_path.exists():
            return None

        manifest = read_json(manifest_path)
        stat = backup_dir.stat()
        return {
            "backup_id": backup_dir.name,
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

    def list_backup_targets(self) -> ServiceResult:
        """列出创建备份时允许选择的白名单目录。"""
        targets = self._backup_targets()
        return ServiceResult(
            status="ok",
            message="backup targets listed",
            payload={
                "base_dir": str(self._base_dir),
                "backup_root": str(self._backup_root),
                "count": len(targets),
                "items": targets,
            },
        )

    async def create_backup(
        self,
        *,
        profile_id: str,
        include_processed: bool = True,
        backup_dir: str | Path | None = None,
        backup_dir_id: str | None = None,
    ) -> ServiceResult:
        """创建项目级备份。"""
        resolved_backup_dir = self._resolve_backup_target(backup_dir_id)
        if resolved_backup_dir is None and backup_dir is not None:
            resolved_backup_dir = self._resolve_backup_dir(backup_dir)
        stats: BackupStats = await backup_project_state(
            base_dir=self._base_dir,
            backup_dir=resolved_backup_dir,
            engine=self._engine,
            include_processed=include_processed,
            audit_service=self._audit_service,
            actor="ui.ops",
            source="ui",
        )
        item = self._backup_item(stats.backup_dir)
        payload = asdict(stats)
        payload["backup_dir"] = str(stats.backup_dir)
        payload["profile_id"] = profile_id
        payload["include_processed"] = include_processed
        payload["backup_item"] = item
        return ServiceResult(status="ok", message="project backup created", payload=payload)

    async def restore_backup(
        self,
        *,
        profile_id: str,
        backup_id: str | None = None,
        backup_path: str | Path | None = None,
        include_processed: bool = True,
        confirmed: bool = False,
    ) -> ServiceResult:
        """恢复项目级备份。"""
        if not confirmed:
            return ServiceResult(status="error", message="confirmation required", payload={"confirmed": confirmed})

        if backup_id is None and backup_path is None:
            return ServiceResult(status="error", message="backup path or id is required", payload={})

        resolved_backup_dir = self._resolve_backup_item_dir(backup_id) if backup_id else self._resolve_backup_dir(backup_path)
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
                actor="ui.ops",
                source="ui",
            )
        except FileNotFoundError:
            return ServiceResult(status="error", message="backup package not found", payload={"backup_path": str(resolved_backup_dir)})
        except FileExistsError as exc:
            return ServiceResult(status="error", message=str(exc), payload={"backup_path": str(resolved_backup_dir)})

        payload = asdict(stats)
        payload["backup_dir"] = str(stats.backup_dir)
        payload["profile_id"] = profile_id
        payload["include_processed"] = include_processed
        payload["backup_item"] = self._backup_item(resolved_backup_dir)
        return ServiceResult(status="ok", message="project backup restored", payload=payload)

    async def recover_stale_jobs(
        self,
        *,
        stale_before_minutes: int = 10,
        actor: str | None = None,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """回收超时未心跳的运行中 Job。"""
        if stale_before_minutes < 1:
            return ServiceResult(
                status="error",
                message="invalid stale_before_minutes",
                payload={"stale_before_minutes": stale_before_minutes},
            )

        stale_before = datetime.now(UTC) - timedelta(minutes=stale_before_minutes)
        result = await self._job_service.recover_stale_jobs(stale_before=stale_before, actor=actor, audit_source=audit_source)
        return ServiceResult(
            status=result.status,
            message=result.message,
            payload={
                **result.payload,
                "stale_before_minutes": stale_before_minutes,
            },
            warnings=result.warnings,
        )


def get_ops_recovery_service() -> OpsRecoveryService:
    """返回项目级备份恢复服务。"""
    return OpsRecoveryService()
