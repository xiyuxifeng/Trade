from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import delete, inspect, select
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.sql.schema import Table

from src.audit.service import AuditService
from config.database import get_engine
from src.common.utils import ensure_dir, read_json, write_json
from src.models import ArticleMetadata, BlogArticle, CrawlState, OHLCVBar, RawArticle, Signal, TradeLog  # noqa: F401
from src.models.base import Base


def _now_slug() -> str:
    """Build a filesystem-friendly timestamp for backup package names."""

    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


def _json_safe(value: Any) -> Any:
    """Convert SQLAlchemy row values into JSON-compatible primitives."""

    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def _parse_datetime(value: Any) -> datetime | None:
    """Parse a stored datetime string back into an aware UTC datetime."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    dt = datetime.fromisoformat(str(value))
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _coerce_table_value(column, value: Any) -> Any:
    """Coerce a serialized value back to the column's Python type."""

    if value is None:
        return None
    try:
        python_type = column.type.python_type
    except Exception:  # noqa: BLE001
        python_type = None

    if python_type is UUID:
        return UUID(str(value))
    if python_type is date:
        return date.fromisoformat(str(value))
    if python_type is datetime:
        return _parse_datetime(value)
    if python_type is Decimal:
        return Decimal(str(value))
    if python_type is bool:
        return bool(value)
    if python_type in {int, str}:
        return python_type(value)

    # Fallback for JSON columns / mixed payloads.
    return value


@dataclass(slots=True)
class BackupStats:
    """Summary for a backup run."""

    backup_dir: Path
    tables: list[str] = field(default_factory=list)
    row_counts: dict[str, int] = field(default_factory=dict)
    processed_copied: bool = False
    artifacts_copied: bool = False


@dataclass(slots=True)
class RestoreStats:
    """Summary for a restore run."""

    backup_dir: Path
    tables: list[str] = field(default_factory=list)
    row_counts: dict[str, int] = field(default_factory=dict)
    processed_restored: bool = False
    artifacts_restored: bool = False


def _processed_dir(base_dir: Path) -> Path:
    """Return the canonical processed-data directory."""

    return base_dir / "data" / "processed"


def _artifacts_dir(base_dir: Path) -> Path:
    """Return the canonical artifacts directory."""

    return base_dir / "data" / "artifacts"


def _backup_manifest_path(backup_dir: Path) -> Path:
    """Return the manifest file path inside one backup package."""

    return backup_dir / "manifest.json"


def _table_payload_path(backup_dir: Path, table_name: str) -> Path:
	"""Return the JSON payload path for one table."""

	return backup_dir / "db" / f"{table_name}.json"


async def _table_exists(conn, table: Table) -> bool:
    """Check whether a table exists in the current database."""

    return await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table(table.name))


async def backup_project_state(
    *,
    base_dir: Path,
    backup_dir: Path | None = None,
    engine: AsyncEngine | None = None,
    include_processed: bool = True,
    audit_service: AuditService | None = None,
    actor: str = "cli.backup_data",
    source: str = "backup-data",
) -> BackupStats:
    """Back up database tables and the processed-data directory into one folder."""

    engine = engine or get_engine()
    audit = audit_service or AuditService()
    target_dir = backup_dir or (base_dir / "data" / "backups" / _now_slug())
    ensure_dir(target_dir)
    ensure_dir(target_dir / "db")

    row_counts: dict[str, int] = {}
    table_names: list[str] = []

    async with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            if table.info.get("compatibility_view"):
                continue
            if not await _table_exists(conn, table):
                continue
            table_names.append(table.name)
            rows = []
            result = await conn.execute(select(table))
            for row in result.mappings().all():
                rows.append({key: _json_safe(value) for key, value in dict(row).items()})
            payload_path = _table_payload_path(target_dir, table.name)
            write_json(payload_path, rows)
            row_counts[table.name] = len(rows)

    processed_copied = False
    if include_processed:
        src_processed = _processed_dir(base_dir)
        if src_processed.exists():
            dst_processed = target_dir / "processed"
            if dst_processed.exists():
                shutil.rmtree(dst_processed)
            shutil.copytree(src_processed, dst_processed)
            processed_copied = True

    artifacts_copied = False
    src_artifacts = _artifacts_dir(base_dir)
    if src_artifacts.exists():
        dst_artifacts = target_dir / "artifacts"
        if dst_artifacts.exists():
            shutil.rmtree(dst_artifacts)
        shutil.copytree(src_artifacts, dst_artifacts)
        artifacts_copied = True

    manifest = {
        "schema_version": "v1",
        "created_at": datetime.now(UTC).isoformat(),
        "tables": table_names,
        "row_counts": row_counts,
        "include_processed": include_processed,
        "processed_copied": processed_copied,
        "artifacts_copied": artifacts_copied,
    }
    write_json(_backup_manifest_path(target_dir), manifest)
    await audit.record(
        event_type="backup_project_state",
        actor=actor,
        entity_type="backup",
        entity_id=target_dir.name,
        dataset_version=target_dir.name,
        payload=manifest,
        source=source,
    )
    return BackupStats(
        backup_dir=target_dir,
        tables=table_names,
        row_counts=row_counts,
        processed_copied=processed_copied,
        artifacts_copied=artifacts_copied,
    )


async def restore_project_state(
    *,
    base_dir: Path,
    backup_dir: Path,
    engine: AsyncEngine | None = None,
    include_processed: bool = True,
    force: bool = False,
    audit_service: AuditService | None = None,
    actor: str = "cli.restore_data",
    source: str = "restore-data",
) -> RestoreStats:
    """Restore database tables and processed data from one backup package."""

    engine = engine or get_engine()
    audit = audit_service or AuditService()
    if not backup_dir.exists():
        raise FileNotFoundError(backup_dir)
    if not force:
        raise FileExistsError("restore is destructive; pass force=True to proceed")

    manifest = read_json(_backup_manifest_path(backup_dir))
    table_names = manifest.get("tables") or [table.name for table in Base.metadata.sorted_tables]

    async with engine.begin() as conn:
        # Delete child tables first, then repopulate in dependency order.
        table_map: dict[str, Table] = {table.name: table for table in Base.metadata.sorted_tables}
        for table_name in reversed(table_names):
            table = table_map.get(table_name)
            if table is not None and not table.info.get("compatibility_view") and await _table_exists(conn, table):
                await conn.execute(delete(table))

        row_counts: dict[str, int] = {}
        for table_name in table_names:
            table = table_map.get(table_name)
            if table is None or table.info.get("compatibility_view") or not await _table_exists(conn, table):
                continue
            payload_path = _table_payload_path(backup_dir, table_name)
            if not payload_path.exists():
                continue
            rows = read_json(payload_path)
            restored_rows: list[dict[str, Any]] = []
            for row in rows:
                restored_rows.append(
                    {
                        column.name: _coerce_table_value(column, row.get(column.name))
                        for column in table.columns
                        if column.name in row
                    }
                )
            if restored_rows:
                await conn.execute(table.insert(), restored_rows)
            row_counts[table_name] = len(restored_rows)

    processed_restored = False
    if include_processed:
        src_processed = backup_dir / "processed"
        dst_processed = _processed_dir(base_dir)
        if src_processed.exists():
            if dst_processed.exists():
                shutil.rmtree(dst_processed)
            shutil.copytree(src_processed, dst_processed)
            processed_restored = True

    artifacts_restored = False
    src_artifacts = backup_dir / "artifacts"
    dst_artifacts = _artifacts_dir(base_dir)
    if src_artifacts.exists():
        if dst_artifacts.exists():
            shutil.rmtree(dst_artifacts)
        shutil.copytree(src_artifacts, dst_artifacts)
        artifacts_restored = True

    await audit.record(
        event_type="restore_project_state",
        actor=actor,
        entity_type="backup",
        entity_id=backup_dir.name,
        dataset_version=backup_dir.name,
        payload={
            "tables": table_names,
            "row_counts": row_counts,
            "include_processed": include_processed,
            "processed_restored": processed_restored,
            "artifacts_restored": artifacts_restored,
        },
        source=source,
    )

    return RestoreStats(
        backup_dir=backup_dir,
        tables=table_names,
        row_counts=row_counts,
        processed_restored=processed_restored,
        artifacts_restored=artifacts_restored,
    )
