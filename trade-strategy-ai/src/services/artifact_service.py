from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from src.common.config import load_app_config
from src.common.paths import resolve_project_path
from src.services.base import BaseService, ServiceResult


_TEXT_EXTENSIONS = {
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
    ".md",
    ".csv",
    ".txt",
    ".log",
}
_BINARY_EXTENSIONS = {
    ".parquet",
    ".zip",
}


@dataclass(slots=True)
class ArtifactRecord:
    """Artifact 索引记录。"""

    artifact_id: str
    name: str
    path: str
    kind: str
    source: str
    exists: bool
    size_bytes: int | None
    modified_at: str | None
    previewable: bool
    job_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_payload(self, *, preview: str | None = None) -> dict[str, Any]:
        """转成前端可直接消费的结构。"""
        payload = {
            "artifact_id": self.artifact_id,
            "name": self.name,
            "path": self.path,
            "kind": self.kind,
            "source": self.source,
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "modified_at": self.modified_at,
            "previewable": self.previewable,
            "job_id": self.job_id,
            "metadata": self.metadata,
        }
        if preview is not None:
            payload["preview"] = preview
        return payload


class ArtifactService(BaseService):
    """统一发现和读取主要产物的服务。"""

    service_name = "artifact"

    def __init__(
        self,
        *,
        config_path: str | Path = "config/app.yaml",
        roots: list[str | Path] | None = None,
        max_preview_lines: int = 24,
        max_preview_chars: int = 4000,
        max_items: int = 2000,
    ) -> None:
        self._config_path = resolve_project_path(config_path)
        self._explicit_roots = [resolve_project_path(root) for root in roots] if roots is not None else None
        self._max_preview_lines = max_preview_lines
        self._max_preview_chars = max_preview_chars
        self._max_items = max_items

    def _project_root(self) -> Path:
        """推导项目根目录。"""
        if self._config_path.parent.name == "config":
            return self._config_path.parent.parent
        return self._config_path.parent

    def _candidate_roots(self) -> list[tuple[str, Path]]:
        """返回可索引的产物根目录。"""
        if self._explicit_roots is not None:
            return [(root.name or "root", root) for root in self._explicit_roots]

        project_root = self._project_root()
        roots: list[tuple[str, Path]] = [
            ("jobs", project_root / "data/jobs"),
            ("processed", project_root / "data/processed"),
            ("backups", project_root / "data/backups"),
            ("market_universe_snapshots", project_root / "data/market_universe/snapshots"),
            ("kaipan", project_root / "data/kaipan"),
        ]

        if self._config_path.exists():
            try:
                loaded = load_app_config(self._config_path)
            except Exception:  # noqa: BLE001
                loaded = None
            if loaded is not None:
                roots.extend(
                    [
                        ("storage_output", project_root / loaded.config.storage.output_dir),
                        ("market_data_cache", project_root / loaded.config.data.market_data_cache_dir),
                        ("market_universe_snapshot", project_root / loaded.config.data.market_universe_snapshot_dir),
                        ("kaipan_data", project_root / loaded.config.kaipan.data_dir),
                    ]
                )

        unique: list[tuple[str, Path]] = []
        seen: set[Path] = set()
        for source, root in roots:
            resolved = root.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            unique.append((source, resolved))
        return unique

    def _is_supported_file(self, path: Path) -> bool:
        """判断文件是否属于可展示产物。"""
        name = path.name.lower()
        if name.endswith(".tar.gz") or name.endswith(".tgz"):
            return True
        suffix = path.suffix.lower()
        return suffix in _TEXT_EXTENSIONS or suffix in _BINARY_EXTENSIONS

    def _classify_kind(self, path: Path) -> str:
        """按扩展名分类产物类型。"""
        name = path.name.lower()
        if name.endswith(".tar.gz") or name.endswith(".tgz"):
            return "tar.gz"
        suffix = path.suffix.lower()
        if suffix in {".json", ".jsonl"}:
            return "json"
        if suffix in {".yaml", ".yml"}:
            return "yaml"
        if suffix in {".html", ".htm"}:
            return "html"
        if suffix == ".md":
            return "markdown"
        if suffix == ".csv":
            return "csv"
        if suffix == ".parquet":
            return "parquet"
        if suffix in {".txt", ".log"}:
            return "text"
        if suffix == ".zip":
            return "zip"
        return suffix.lstrip(".") or "file"

    def _artifact_id(self, *, source: str, path: Path, kind: str) -> str:
        """生成稳定的产物标识。"""
        digest = hashlib.sha256(f"{source}|{kind}|{path.resolve()}".encode("utf-8")).hexdigest()
        return digest[:16]

    def _is_within_root(self, path: Path, root: Path) -> bool:
        """判断路径是否位于允许的索引根目录下。"""
        try:
            path.resolve().relative_to(root.resolve())
            return True
        except ValueError:
            return False

    def _parse_job_id(self, path: Path, root: Path) -> str | None:
        """从 job 目录推导 job_id。"""
        if root.name != "jobs":
            return None
        try:
            relative = path.resolve().relative_to(root.resolve())
        except ValueError:
            return None
        if not relative.parts:
            return None
        return relative.parts[0]

    def _format_modified_at(self, path: Path) -> str | None:
        """格式化修改时间。"""
        try:
            return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
        except FileNotFoundError:
            return None

    def _build_record(self, *, source: str, root: Path, path: Path, metadata: dict[str, Any] | None = None) -> ArtifactRecord | None:
        """为单个文件构建索引记录。"""
        if not path.is_file() or not self._is_supported_file(path):
            return None
        if not self._is_within_root(path, root):
            return None

        stat = path.stat()
        kind = self._classify_kind(path)
        return ArtifactRecord(
            artifact_id=self._artifact_id(source=source, path=path, kind=kind),
            name=path.name,
            path=str(path.resolve()),
            kind=kind,
            source=source,
            exists=True,
            size_bytes=stat.st_size,
            modified_at=self._format_modified_at(path),
            previewable=kind in {"json", "yaml", "html", "markdown", "csv", "text"},
            job_id=self._parse_job_id(path, root),
            metadata=metadata or {},
        )

    def _scan_files(self) -> list[ArtifactRecord]:
        """扫描所有候选根目录下的可展示文件。"""
        records: list[ArtifactRecord] = []
        seen: set[tuple[str, str]] = set()
        for source, root in self._candidate_roots():
            if not root.exists():
                continue
            for path in root.rglob("*"):
                record = self._build_record(source=source, root=root, path=path)
                if record is None:
                    continue
                key = (record.source, record.path)
                if key in seen:
                    continue
                seen.add(key)
                records.append(record)
                if len(records) >= self._max_items:
                    break
            if len(records) >= self._max_items:
                break
        records.sort(key=lambda item: (item.modified_at or "", item.path), reverse=True)
        return records

    def _preview_path(self, path: Path, kind: str) -> str | None:
        """为可预览文件生成文本预览。"""
        if not path.exists() or not path.is_file():
            return None

        if kind == "json":
            try:
                parsed = json.loads(path.read_text(encoding="utf-8"))
                return json.dumps(parsed, ensure_ascii=False, indent=2)[: self._max_preview_chars]
            except Exception:  # noqa: BLE001
                return path.read_text(encoding="utf-8", errors="replace")[: self._max_preview_chars]

        if kind == "yaml":
            try:
                parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
                return yaml.safe_dump(parsed, sort_keys=False, allow_unicode=True)[: self._max_preview_chars]
            except Exception:  # noqa: BLE001
                return path.read_text(encoding="utf-8", errors="replace")[: self._max_preview_chars]

        if kind in {"html", "markdown", "csv", "text"}:
            return path.read_text(encoding="utf-8", errors="replace")[: self._max_preview_chars]

        return None

    async def list_artifacts(
        self,
        *,
        kind: str | None = None,
        source: str | None = None,
        job_id: str | None = None,
        q: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> ServiceResult:
        """列出可用产物。"""
        records = self._scan_files()
        if kind is not None:
            records = [item for item in records if item.kind == kind]
        if source is not None:
            records = [item for item in records if item.source == source]
        if job_id is not None:
            records = [item for item in records if item.job_id == job_id]
        if q:
            q_lower = q.lower()
            records = [item for item in records if q_lower in item.name.lower() or q_lower in item.path.lower()]

        total = len(records)
        items = [record.to_payload() for record in records[skip : skip + limit]]
        return ServiceResult(
            status="ok",
            message="artifacts listed",
            payload={
                "count": len(items),
                "total": total,
                "skip": skip,
                "limit": limit,
                "items": items,
            },
        )

    async def get_artifact(self, artifact_id: str) -> ServiceResult:
        """按标识查询单个产物，并附带预览。"""
        for record in self._scan_files():
            if record.artifact_id != artifact_id:
                continue
            preview = self._preview_path(Path(record.path), record.kind) if record.previewable else None
            return ServiceResult(
                status="ok",
                message="artifact loaded",
                payload={
                    **record.to_payload(preview=preview),
                    "download_name": Path(record.path).name,
                },
            )

        return ServiceResult(status="partial", message="artifact not found", payload={"artifact_id": artifact_id})
