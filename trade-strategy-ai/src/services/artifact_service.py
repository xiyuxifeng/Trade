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
from src.services.artifact_contracts import ArtifactCatalogItem, ArtifactDetail
from src.services.base import BaseService, ServiceResult
from src.services.runtime_contracts import StorageRef


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
    title: str
    _path: Path = field(repr=False)
    kind: str
    source: str
    exists: bool
    size_bytes: int | None
    modified_at: str | None
    previewable: bool
    job_id: str | None = None
    job_type: str | None = None
    workflow_id: str | None = None
    step_id: str | None = None
    safe_download_url: str | None = None
    download_token: str | None = None
    download_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    storage_ref: StorageRef | None = None

    def to_payload(self, *, preview: str | None = None) -> dict[str, Any]:
        """转成前端可直接消费的结构。"""
        catalog_item = ArtifactCatalogItem(
            artifact_id=self.artifact_id,
            name=self.name,
            title=self.title,
            kind=self.kind,
            source=self.source,
            exists=self.exists,
            size_bytes=self.size_bytes,
            modified_at=self.modified_at,
            previewable=self.previewable,
            job_id=self.job_id,
            job_type=self.job_type,
            workflow_id=self.workflow_id,
            step_id=self.step_id,
            safe_download_url=self.safe_download_url,
            download_token=self.download_token,
            download_name=self.download_name,
            metadata=self.metadata,
            storage_ref=self.storage_ref,
            preview=preview,
        )
        payload = catalog_item.model_dump(mode="json")
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
                        ("runtime_output", project_root / loaded.config.runtime.output_dir),
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

    def _safe_download_url(self, artifact_id: str) -> str:
        """返回对外安全下载地址。"""
        return f"/api/ui/v1/artifacts/{artifact_id}/download"

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
        relative_path = None
        try:
            relative_path = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            relative_path = None
        artifact_id = self._artifact_id(source=source, path=path, kind=kind)
        return ArtifactRecord(
            artifact_id=artifact_id,
            name=path.name,
            title=path.name,
            _path=path.resolve(),
            kind=kind,
            source=source,
            exists=True,
            size_bytes=stat.st_size,
            modified_at=self._format_modified_at(path),
            previewable=kind in {"json", "yaml", "html", "markdown", "csv", "text"},
            job_id=self._parse_job_id(path, root),
            job_type=None,
            safe_download_url=self._safe_download_url(artifact_id),
            download_name=path.name,
            metadata=metadata or {},
            storage_ref=StorageRef(
                source="file",
                logical_id=relative_path or artifact_id,
                relative_path=relative_path,
                metadata={"root": root.name, "source": source},
            ),
        )

    def is_download_path_allowed(self, path: str | Path) -> bool:
        """判断下载路径是否位于允许的产物根目录内。"""
        candidate = Path(path).resolve()
        if not candidate.is_file():
            return False
        for _, root in self._candidate_roots():
            if self._is_within_root(candidate, root):
                return True
        return False

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
                key = (record.source, str(record._path))
                if key in seen:
                    continue
                seen.add(key)
                records.append(record)
                if len(records) >= self._max_items:
                    break
            if len(records) >= self._max_items:
                break
        records.sort(key=lambda item: (item.modified_at or "", str(item._path)), reverse=True)
        return records

    async def _job_metadata_by_id(self, job_ids: set[str]) -> dict[str, dict[str, Any]]:
        """按 job_id 拉取可用于筛选和展示的作业元数据。"""
        if not job_ids:
            return {}

        try:
            from src.services.job_service import JobService
        except Exception:  # noqa: BLE001
            return {}

        metadata: dict[str, dict[str, Any]] = {}
        service = JobService()
        for job_id in sorted(job_ids):
            try:
                result = await service.get_job(job_id)
            except Exception:  # noqa: BLE001
                continue
            if result.status != "ok":
                continue
            job_payload = result.payload.get("job") if isinstance(result.payload, dict) else None
            if not isinstance(job_payload, dict):
                continue
            metadata[job_id] = {
                "job_type": job_payload.get("job_type"),
                "created_at": job_payload.get("created_at"),
            }
        return metadata

    def _apply_job_metadata(self, records: list[ArtifactRecord], job_metadata: dict[str, dict[str, Any]]) -> None:
        """把作业元数据回填到产物记录，便于筛选和展示。"""
        for record in records:
            if not record.job_id:
                continue
            metadata = job_metadata.get(record.job_id)
            if metadata:
                record.job_type = metadata.get("job_type")

    async def _records_with_job_metadata(self) -> list[ArtifactRecord]:
        """返回已经补齐 job 元数据的产物记录。"""
        records = self._scan_files()
        job_ids = {record.job_id for record in records if record.job_id}
        self._apply_job_metadata(records, await self._job_metadata_by_id(job_ids))
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

    def resolve_download_path(self, artifact_id: str) -> Path | None:
        """解析 artifact 对应的内部下载路径。"""
        for record in self._scan_files():
            if record.artifact_id == artifact_id:
                return record._path
        return None

    async def list_artifacts(
        self,
        *,
        kind: str | None = None,
        source: str | None = None,
        job_type: str | None = None,
        date: str | None = None,
        job_id: str | None = None,
        q: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> ServiceResult:
        """列出可用产物。"""
        records = await self._records_with_job_metadata()
        if kind is not None:
            records = [item for item in records if item.kind == kind]
        if source is not None:
            records = [item for item in records if item.source == source]
        if job_type is not None:
            records = [item for item in records if item.job_type == job_type]
        if date is not None:
            date_prefix = date.strip()
            if date_prefix:
                records = [item for item in records if item.modified_at and item.modified_at.startswith(date_prefix)]
        if job_id is not None:
            records = [item for item in records if item.job_id == job_id]
        if q:
            q_lower = q.lower()
            records = [item for item in records if q_lower in item.name.lower() or q_lower in str(item._path).lower()]

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

    async def list_filter_options(self) -> ServiceResult:
        """列出产物筛选下拉选项。"""
        records = await self._records_with_job_metadata()

        job_id_latest_modified: dict[str, str] = {}
        for record in records:
            if not record.job_id:
                continue
            current_modified = record.modified_at or ""
            previous_modified = job_id_latest_modified.get(record.job_id)
            if previous_modified is None or current_modified > previous_modified:
                job_id_latest_modified[record.job_id] = current_modified

        job_ids = [
            job_id
            for job_id, _ in sorted(
                job_id_latest_modified.items(),
                key=lambda item: (item[1], item[0]),
                reverse=True,
            )
        ]

        return ServiceResult(
            status="ok",
            message="artifact filter options listed",
            payload={
                "kinds": sorted({record.kind for record in records if record.kind}),
                "sources": sorted({record.source for record in records if record.source}),
                "job_types": sorted({record.job_type for record in records if record.job_type}),
                "job_ids": job_ids,
            },
        )

    async def get_artifact(self, artifact_id: str) -> ServiceResult:
        """按标识查询单个产物，并附带预览。"""
        for record in self._scan_files():
            if record.artifact_id != artifact_id:
                continue
            self._apply_job_metadata([record], await self._job_metadata_by_id({record.job_id} if record.job_id else set()))
            preview = self._preview_path(record._path, record.kind) if record.previewable else None
            detail = ArtifactDetail(**record.to_payload(preview=preview))
            return ServiceResult(
                status="ok",
                message="artifact loaded",
                payload={
                    **detail.model_dump(mode="json"),
                    "artifact_ref": {
                        "artifact_id": record.artifact_id,
                        "job_id": record.job_id,
                        "workflow_id": record.workflow_id,
                        "step_id": record.step_id,
                        "kind": record.kind,
                        "title": record.title,
                        "summary": record.metadata.get("summary"),
                        "safe_download_url": record.safe_download_url,
                        "download_token": record.download_token,
                        "size_bytes": record.size_bytes,
                        "created_at": record.modified_at,
                        "visibility": record.metadata.get("visibility", "internal"),
                        "metadata": record.metadata,
                        "storage_ref": record.storage_ref.model_dump(mode="json") if record.storage_ref else None,
                    },
                },
            )

        return ServiceResult(status="partial", message="artifact not found", payload={"artifact_id": artifact_id})
