from __future__ import annotations

import hashlib
import os
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit

from sqlalchemy import select

from src.common.config import ConfigError, build_app_config
from src.common.paths import project_root, resolve_project_path
from src.models.config_profile import ConfigProfile
from src.services.base import BaseService, ServiceResult
from src.services.config_service import ConfigService
from src.services.runtime_config import ProfileRuntimeConfig
from src.db.session import session_scope


_SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "api_keys", "cookie"}

_PATH_TOKEN_RE = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def _to_plain(value: Any) -> Any:
    """把 ORM / 容器值转成稳定可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _stable_json(value: Any) -> str:
    """生成稳定 JSON 表达，供 hash 计算使用。"""
    return json.dumps(_to_plain(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _profile_payload(profile: ConfigProfile) -> dict[str, Any]:
    """把 Profile ORM 对象转成稳定 payload。"""
    return {
        "profile_id": profile.profile_id,
        "name": profile.name,
        "environment": profile.environment,
        "version": profile.version,
        "sections": _to_plain(profile.sections),
        "secret_refs": _to_plain(profile.secret_refs),
        "validation_status": profile.validation_status,
        "created_by": profile.created_by,
        "created_at": _to_plain(profile.created_at),
        "updated_at": _to_plain(profile.updated_at),
        "archived_at": _to_plain(profile.archived_at),
    }


def _iter_path_tokens(path: str) -> list[str | int]:
    tokens: list[str | int] = []
    for match in _PATH_TOKEN_RE.finditer(path):
        key, index = match.groups()
        if key is not None:
            tokens.append(key)
        elif index is not None:
            tokens.append(int(index))
    return tokens


def _mask_sensitive_runtime_values(value: Any, secret_refs: dict[str, Any]) -> Any:
    """把 Profile 中已脱敏的敏感字段在运行态中清空，让环境变量接管。"""

    if not isinstance(secret_refs, dict) or not secret_refs:
        return value

    import copy

    result = copy.deepcopy(value)

    for path, state in secret_refs.items():
        if state != "masked":
            continue
        tokens = _iter_path_tokens(str(path))
        if not tokens:
            continue

        current = result
        for token in tokens[:-1]:
            if isinstance(token, int):
                if not isinstance(current, list) or token >= len(current):
                    current = None
                    break
                current = current[token]
            else:
                if not isinstance(current, dict) or token not in current:
                    current = None
                    break
                current = current[token]
        if current is None:
            continue

        last = tokens[-1]
        if isinstance(last, int):
            if isinstance(current, list) and 0 <= last < len(current):
                current[last] = None
        elif isinstance(current, dict):
            current[last] = [] if last == "api_keys" else None

    return result



class ConfigProfileService(BaseService):
    """Profile 的正式管理服务。

    负责创建、导入、更新、归档与快照，不再把 `config_path` 当长期事实源。
    """

    service_name = "config-profile"

    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any] | None = None,
        snapshot_root: str | Path | None = None,
        config_service: ConfigService | None = None,
    ) -> None:
        self._session_scope_factory = session_scope_factory
        self._snapshot_root = resolve_project_path(snapshot_root or "data/profile_snapshots")
        self._config_service = config_service or ConfigService()

    def _ensure_session_factory(self) -> Callable[[], Any]:
        """确保存在数据库 session_scope 工厂。"""
        if self._session_scope_factory is not None:
            return self._session_scope_factory
        self._session_scope_factory = session_scope
        return self._session_scope_factory

    def _snapshot_path(self, snapshot_id: str) -> Path:
        """返回 Profile snapshot 的落盘路径。"""
        return self._snapshot_root / f"{snapshot_id}.json"

    def _snapshot_payload_for_profile(
        self,
        profile: ConfigProfile,
        *,
        job_id: str | None = None,
        source: str | None = None,
        config_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """根据当前 Profile 对象生成快照 payload。"""
        captured_at = datetime.now(UTC).isoformat()
        plain_sections = _to_plain(profile.sections)
        masked_sections = sorted(plain_sections.keys()) if isinstance(plain_sections, dict) else []
        snapshot_body = {
            "profile_id": profile.profile_id,
            "name": profile.name,
            "environment": profile.environment,
            "version": profile.version,
            "sections": plain_sections,
            "secret_refs": _to_plain(profile.secret_refs),
            "validation_status": profile.validation_status,
            "created_by": profile.created_by,
            "created_at": _to_plain(profile.created_at),
            "updated_at": _to_plain(profile.updated_at),
            "archived_at": _to_plain(profile.archived_at),
        }
        profile_hash = hashlib.sha256(_stable_json(snapshot_body).encode("utf-8")).hexdigest()
        snapshot_id = profile_hash
        snapshot_path = self._snapshot_path(snapshot_id if job_id is None else job_id)
        return {
            "profile_snapshot_id": snapshot_id,
            "profile_id": profile.profile_id,
            "job_id": job_id,
            "source": source or (f"job:{job_id}" if job_id else "profile"),
            "config_path": str(config_path) if config_path else "",
            "profile_hash": profile_hash,
            "name": profile.name,
            "environment": profile.environment,
            "version": profile.version,
            "sections": plain_sections,
            "secret_refs": _to_plain(profile.secret_refs),
            "validation_status": profile.validation_status,
            "masked_snapshot": plain_sections,
            "masked_sections": masked_sections,
            "created_by": profile.created_by,
            "created_at": _to_plain(profile.created_at),
            "updated_at": _to_plain(profile.updated_at),
            "archived_at": _to_plain(profile.archived_at),
            "captured_at": captured_at,
            "snapshot_path": str(snapshot_path),
            "profile_snapshot_path": str(snapshot_path),
        }

    def _persist_snapshot_payload(self, snapshot_payload: dict[str, Any]) -> None:
        """将快照 payload 写入磁盘。"""
        snapshot_path = Path(snapshot_payload["snapshot_path"])
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        with NamedTemporaryFile("w", encoding="utf-8", dir=snapshot_path.parent, delete=False) as tmp_file:
            tmp_file.write(json.dumps(snapshot_payload, ensure_ascii=False, indent=2))
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            temp_path = Path(tmp_file.name)

        try:
            if temp_path is not None:
                os.replace(temp_path, snapshot_path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def serialize_profile(self, profile: ConfigProfile) -> dict[str, Any]:
        """把 Profile ORM 对象转成 API payload。"""
        return _profile_payload(profile)

    def _snapshot_records(self) -> list[dict[str, Any]]:
        """读取所有已保存的 Profile snapshot 记录。"""
        if not self._snapshot_root.exists():
            return []
        records: list[dict[str, Any]] = []
        for path in sorted(self._snapshot_root.glob("*.json")):
            try:
                records.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                continue
        return records

    def _collect_secret_refs(self, value: Any, *, prefix: str = "") -> dict[str, str]:
        """递归收集敏感字段引用，供 UI 展示与审计使用。"""
        refs: dict[str, str] = {}
        if isinstance(value, dict):
            for key, item in value.items():
                key_name = str(key)
                path = f"{prefix}.{key_name}" if prefix else key_name
                lowered = key_name.lower()
                if lowered in _SENSITIVE_KEYS:
                    refs[path] = "masked"
                if lowered == "url" and isinstance(item, str):
                    parsed = urlsplit(item)
                    if parsed.password is not None:
                        refs[path] = "masked"
                refs.update(self._collect_secret_refs(item, prefix=path))
            return refs
        if isinstance(value, list):
            for index, item in enumerate(value):
                refs.update(self._collect_secret_refs(item, prefix=f"{prefix}[{index}]"))
        return refs

    async def _load_profile(self, session: Any, profile_id: str) -> ConfigProfile | None:
        """按 profile_id 读取 Profile。"""
        stmt = select(ConfigProfile).where(ConfigProfile.profile_id == profile_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _save_profile(self, profile: ConfigProfile) -> ConfigProfile:
        """把 Profile 写回数据库并刷新。"""
        session_scope_factory = self._ensure_session_factory()
        async with session_scope_factory() as session:
            session.add(profile)
            await session.flush()
            await session.refresh(profile)
        return profile

    async def create_default_profile(self, *, environment: str, created_by: str) -> ConfigProfile:
        """创建默认 Profile。"""
        session_scope_factory = self._ensure_session_factory()
        now = datetime.now(UTC)
        async with session_scope_factory() as session:
            existing = await self._load_profile(session, "default")
            if existing is not None:
                return existing
            profile = ConfigProfile(
                profile_id="default",
                name="Default Profile",
                environment=environment,
                version=1,
                sections={},
                secret_refs={},
                validation_status="draft",
                created_by=created_by,
                archived_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(profile)
            await session.flush()
            await session.refresh(profile)
            return profile

    async def import_from_config_path(
        self,
        config_path: str | Path,
        *,
        profile_id: str,
        created_by: str,
        name: str | None = None,
        environment: str | None = None,
        validation_status: str | None = None,
    ) -> ConfigProfile:
        """从现有 config_path 导入正式 Profile。"""
        resolved = resolve_project_path(config_path)
        if not resolved.exists():
            raise ConfigError(f"Config file not found: {resolved}")

        raw_payload = self._config_service.load_raw_config(resolved)
        loaded = self._config_service.load_config(resolved)
        raw_config = loaded.config.model_dump(mode="json")
        masked_sections = self._config_service.mask_config(raw_config)
        secret_refs = self._collect_secret_refs(raw_config)
        now = datetime.now(UTC)

        session_scope_factory = self._ensure_session_factory()
        try:
            async with session_scope_factory() as session:
                existing = await self._load_profile(session, profile_id)
                if existing is None:
                    profile = ConfigProfile(
                        profile_id=profile_id,
                        name=name or profile_id,
                        environment=str(environment or raw_payload.get("environment") or raw_config.get("environment") or "default"),
                        version=1,
                        sections=masked_sections,
                        secret_refs=secret_refs,
                        validation_status=validation_status or "validated",
                        created_by=created_by,
                        archived_at=None,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(profile)
                else:
                    existing.name = name or profile_id
                    existing.environment = str(environment or raw_payload.get("environment") or raw_config.get("environment") or existing.environment or "default")
                    existing.version = int(existing.version or 1) + 1
                    existing.sections = masked_sections
                    existing.secret_refs = secret_refs
                    existing.validation_status = validation_status or "validated"
                    existing.archived_at = None
                    existing.updated_at = now
                    profile = existing
                await session.flush()
                await session.refresh(profile)
                snapshot_payload = self._snapshot_payload_for_profile(profile, source=str(resolved), config_path=resolved)
                self._persist_snapshot_payload(snapshot_payload)
                return profile
        except Exception as exc:  # noqa: BLE001
            raise ConfigError(str(exc) or "profile import failed") from exc

    async def get_profile(self, profile_id: str) -> ConfigProfile | None:
        """按 profile_id 查询 Profile。"""
        session_scope_factory = self._ensure_session_factory()
        async with session_scope_factory() as session:
            return await self._load_profile(session, profile_id)

    async def load_profile_runtime_config(self, profile_id: str) -> ProfileRuntimeConfig:
        """将 Profile materialize 成 Web 运行时直接消费的 AppConfig。"""
        profile = await self.get_profile(profile_id)
        if profile is None:
            raise ConfigError(f"profile not found: {profile_id}")

        raw_sections = _to_plain(profile.sections)
        if not isinstance(raw_sections, dict):
            raise ConfigError(f"invalid profile sections for {profile_id}")

        cleaned_sections = _mask_sensitive_runtime_values(raw_sections, _to_plain(profile.secret_refs))
        config = build_app_config(cleaned_sections)
        snapshots = await self.list_profile_snapshots(profile_id)
        latest_snapshot_id = None
        if snapshots:
            latest_snapshot_id = str(
                snapshots[-1].get("snapshot_id")
                or snapshots[-1].get("profile_snapshot_id")
                or ""
            ) or None

        return ProfileRuntimeConfig(
            profile_id=profile.profile_id,
            config=config,
            base_dir=project_root().resolve(),
            profile_snapshot_id=latest_snapshot_id,
        )

    def resolve_runtime_profile_id(self, preferred: str | None = None) -> str:
        """解析 Web 运行时应使用的 Profile ID。

        优先使用显式传入的 Profile，其次使用环境变量绑定的 Profile，最后回退到
        canonical 的 `default` Profile。
        """
        candidates = [
            preferred,
            os.environ.get("PROFILE_ID"),
            os.environ.get("ACTIVE_PROFILE_ID"),
            "default",
        ]
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return "default"

    async def list_profiles(self) -> list[ConfigProfile]:
        """列出全部 Profile。"""
        session_scope_factory = self._ensure_session_factory()
        async with session_scope_factory() as session:
            result = await session.execute(select(ConfigProfile).order_by(ConfigProfile.updated_at.desc()))
            return list(result.scalars().all())

    async def list_profile_snapshots(self, profile_id: str) -> list[dict[str, Any]]:
        """列出某个 Profile 的历史快照。"""
        records = [record for record in self._snapshot_records() if str(record.get("profile_id")) == profile_id]
        records.sort(key=lambda item: str(item.get("captured_at") or item.get("updated_at") or item.get("snapshot_id") or ""))
        return records

    async def resolve_profile_config_path(self, profile_id: str) -> Path | None:
        """解析 Profile 最新可用的配置路径。"""
        profile = await self.get_profile(profile_id)
        if profile is None:
            return None

        snapshots = await self.list_profile_snapshots(profile_id)
        for snapshot in reversed(snapshots):
            config_path = str(snapshot.get("config_path") or "").strip()
            if config_path:
                return resolve_project_path(config_path)

        return resolve_project_path("config/app.yaml")

    async def list_profile_linked_jobs(self, profile_id: str) -> list[dict[str, Any]]:
        """列出与 Profile 关联的 Job。"""
        from src.services.job_service import JobService

        result = await JobService().list_jobs(limit=500)
        if result.status != "ok":
            return []

        items: list[dict[str, Any]] = []
        for job in result.payload.get("items", []):
            params = job.get("params") or {}
            profile_snapshot = job.get("profile_snapshot") or {}
            if str(params.get("profile_id") or profile_snapshot.get("profile_id")) != profile_id:
                continue
            items.append(
                {
                    "job_id": job.get("id"),
                    "job_type": job.get("job_type"),
                    "status": job.get("status"),
                    "created_at": job.get("created_at"),
                    "updated_at": job.get("updated_at"),
                }
            )
        return items

    async def get_profile_detail_payload(self, profile_id: str) -> ServiceResult:
        """返回 Profile 详情页面所需的完整 payload。"""
        profile = await self.get_profile(profile_id)
        if profile is None:
            return ServiceResult(status="partial", message="profile not found", payload={"profile_id": profile_id})

        linked_jobs = await self.list_profile_linked_jobs(profile_id)
        snapshots = await self.list_profile_snapshots(profile_id)
        return ServiceResult(
            status="ok",
            message="profile detail loaded",
            payload={
                "profile": _profile_payload(profile),
                "linked_jobs": linked_jobs,
                "snapshots": snapshots,
            },
        )

    def _build_section_guide(self, profile: ConfigProfile, draft_sections: dict[str, Any]) -> list[dict[str, Any]]:
        """生成 UI 可渲染的分区说明。"""
        current_sections = _to_plain(profile.sections)
        section_keys = sorted(set(current_sections) | set(draft_sections))
        guide: list[dict[str, Any]] = []
        for key in section_keys:
            current_value = current_sections.get(key) if isinstance(current_sections, dict) else None
            draft_value = draft_sections.get(key)
            guide.append(
                {
                    "key": key,
                    "title": key.replace("_", " ").title(),
                    "description": "可编辑 JSON 分区，不包含 secret 原文。",
                    "source": "当前 Profile 版本",
                    "default_value": current_value,
                    "current_value": current_value,
                    "draft_value": draft_value if draft_value is not None else current_value,
                }
            )
        return guide

    async def build_profile_edit_payload(self, profile_id: str, draft: dict[str, Any] | None = None) -> ServiceResult:
        """构建 Profile 编辑页/预览所需 payload。"""
        profile = await self.get_profile(profile_id)
        if profile is None:
            return ServiceResult(status="partial", message="profile not found", payload={"profile_id": profile_id})

        draft = _to_plain(draft or {})
        issues: list[dict[str, Any]] = []
        if "name" in draft and not str(draft.get("name") or "").strip():
            issues.append({"field": "name", "message": "配置名称不能为空"})
        if "environment" in draft and not str(draft.get("environment") or "").strip():
            issues.append({"field": "environment", "message": "运行环境不能为空"})
        draft_sections = draft.get("sections") if isinstance(draft.get("sections"), dict) else _to_plain(profile.sections)
        if not isinstance(draft_sections, dict):
            issues.append({"field": "sections", "message": "配置分区必须是对象"})
            draft_sections = _to_plain(profile.sections)

        section_guide = self._build_section_guide(profile, draft_sections)
        next_version = int(profile.version or 1) + 1
        validation_status = "validated" if not issues else "invalid_config"
        preview_profile = {
            **_profile_payload(profile),
            "name": str(draft.get("name") or profile.name),
            "environment": str(draft.get("environment") or profile.environment),
            "sections": self._config_service.mask_config(_to_plain(draft_sections)),
            "validation_status": validation_status,
            "version": next_version,
        }

        return ServiceResult(
            status="ok",
            message="profile edit payload ready",
            payload={
                "profile": _profile_payload(profile),
                "draft": {
                    "name": draft.get("name") or profile.name,
                    "environment": draft.get("environment") or profile.environment,
                    "sections": draft_sections,
                },
                "preview": preview_profile,
                "section_guide": section_guide,
                "validation": {
                    "valid": not issues,
                    "issues": issues,
                    "next_version": next_version,
                    "validation_status": validation_status,
                },
            },
        )

    async def validate_profile_update(self, profile_id: str, draft: dict[str, Any]) -> ServiceResult:
        """校验 Profile 更新草稿。"""
        return await self.build_profile_edit_payload(profile_id, draft)

    async def save_profile_update(self, profile_id: str, draft: dict[str, Any], *, created_by: str) -> ServiceResult:
        """校验通过后保存 Profile 更新。"""
        del created_by
        preview_result = await self.build_profile_edit_payload(profile_id, draft)
        if preview_result.status != "ok":
            return preview_result
        validation = preview_result.payload["validation"]
        if not validation["valid"]:
            return ServiceResult(
                status="error",
                message="validation failed",
                payload=preview_result.payload,
            )

        session_scope_factory = self._ensure_session_factory()
        now = datetime.now(UTC)
        try:
            async with session_scope_factory() as session:
                profile = await self._load_profile(session, profile_id)
                if profile is None:
                    return ServiceResult(status="partial", message="profile not found", payload={"profile_id": profile_id})
                profile.name = str(preview_result.payload["draft"]["name"])
                profile.environment = str(preview_result.payload["draft"]["environment"])
                profile.sections = self._config_service.mask_config(_to_plain(preview_result.payload["draft"]["sections"]))
                profile.secret_refs = self._collect_secret_refs(_to_plain(preview_result.payload["draft"]["sections"]))
                profile.validation_status = "validated"
                profile.version = int(profile.version or 1) + 1
                profile.updated_at = now
                await session.flush()
                await session.refresh(profile)
                snapshot_payload = self._snapshot_payload_for_profile(profile)
                self._persist_snapshot_payload(snapshot_payload)
        except Exception as exc:  # noqa: BLE001
            return ServiceResult(
                status="error",
                message=str(exc) or "profile update failed",
                payload=preview_result.payload,
            )

        return ServiceResult(
            status="ok",
            message="profile updated",
            payload={
                "profile": _profile_payload(profile),
                "snapshot": snapshot_payload,
                "validation": validation,
            },
        )

    async def update_profile(self, profile_id: str, **changes: Any) -> ConfigProfile:
        """更新 Profile 的内容并提升版本号。"""
        session_scope_factory = self._ensure_session_factory()
        now = datetime.now(UTC)
        async with session_scope_factory() as session:
            profile = await self._load_profile(session, profile_id)
            if profile is None:
                raise ValueError(f"profile not found: {profile_id}")
            if "name" in changes and isinstance(changes["name"], str):
                profile.name = changes["name"]
            if "environment" in changes and isinstance(changes["environment"], str):
                profile.environment = changes["environment"]
            if "sections" in changes and isinstance(changes["sections"], dict):
                profile.sections = self._config_service.mask_config(_to_plain(changes["sections"]))
                profile.secret_refs = self._collect_secret_refs(_to_plain(changes["sections"]))
            if "secret_refs" in changes and isinstance(changes["secret_refs"], dict):
                profile.secret_refs = _to_plain(changes["secret_refs"])
            if "validation_status" in changes and isinstance(changes["validation_status"], str):
                profile.validation_status = changes["validation_status"]
            if "archived_at" in changes:
                profile.archived_at = changes["archived_at"]
            profile.version = int(profile.version or 1) + 1
            profile.updated_at = now
            await session.flush()
            await session.refresh(profile)
            return profile

    async def archive_profile(self, profile_id: str, *, archived_by: str) -> ConfigProfile:
        """归档 Profile。"""
        del archived_by
        profile = await self.get_profile(profile_id)
        if profile is None:
            raise ValueError(f"profile not found: {profile_id}")
        profile.archived_at = datetime.now(UTC)
        profile.validation_status = "archived"
        profile.version = int(profile.version or 1) + 1
        profile.updated_at = datetime.now(UTC)
        return await self._save_profile(profile)

    async def capture_profile_snapshot(
        self,
        profile_id: str,
        *,
        job_id: str | None = None,
        source: str | None = None,
        config_path: str | Path | None = None,
    ) -> ServiceResult:
        """生成 Profile 的冻结快照。"""
        profile = await self.get_profile(profile_id)
        if profile is None:
            return ServiceResult(
                status="error",
                message="profile not found",
                payload={"profile_id": profile_id, "job_id": job_id},
            )

        snapshot_payload = self._snapshot_payload_for_profile(profile, job_id=job_id, source=source, config_path=config_path)
        self._persist_snapshot_payload(snapshot_payload)

        return ServiceResult(
            status="ok",
            message="profile snapshot captured",
            payload=snapshot_payload,
        )
