from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from sqlalchemy import select

from src.common.config import ConfigError
from src.common.paths import resolve_project_path
from src.models.config_profile import ConfigProfile
from src.services.base import BaseService, ServiceResult
from src.services.config_service import ConfigService
from src.db.session import session_scope


_SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "api_keys", "cookie"}


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
        async with session_scope_factory() as session:
            existing = await self._load_profile(session, profile_id)
            if existing is None:
                profile = ConfigProfile(
                    profile_id=profile_id,
                    name=profile_id,
                    environment=str(raw_payload.get("environment") or raw_config.get("environment") or "default"),
                    version=1,
                    sections=masked_sections,
                    secret_refs=secret_refs,
                    validation_status="validated",
                    created_by=created_by,
                    archived_at=None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(profile)
            else:
                existing.name = profile_id
                existing.environment = str(raw_payload.get("environment") or raw_config.get("environment") or existing.environment or "default")
                existing.version = int(existing.version or 1) + 1
                existing.sections = masked_sections
                existing.secret_refs = secret_refs
                existing.validation_status = "validated"
                existing.archived_at = None
                existing.updated_at = now
                profile = existing
            await session.flush()
            await session.refresh(profile)
            return profile

    async def get_profile(self, profile_id: str) -> ConfigProfile | None:
        """按 profile_id 查询 Profile。"""
        session_scope_factory = self._ensure_session_factory()
        async with session_scope_factory() as session:
            return await self._load_profile(session, profile_id)

    async def list_profiles(self) -> list[ConfigProfile]:
        """列出全部 Profile。"""
        session_scope_factory = self._ensure_session_factory()
        async with session_scope_factory() as session:
            result = await session.execute(select(ConfigProfile).order_by(ConfigProfile.updated_at.desc()))
            return list(result.scalars().all())

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
        profile = await self.get_profile(profile_id)
        if profile is None:
            raise ValueError(f"profile not found: {profile_id}")
        profile.archived_at = datetime.now(UTC)
        profile.validation_status = "archived"
        profile.version = int(profile.version or 1) + 1
        profile.updated_at = datetime.now(UTC)
        return await self._save_profile(profile)

    async def capture_profile_snapshot(self, profile_id: str, *, job_id: str | None = None) -> ServiceResult:
        """生成 Profile 的冻结快照。"""
        profile = await self.get_profile(profile_id)
        if profile is None:
            return ServiceResult(
                status="error",
                message="profile not found",
                payload={"profile_id": profile_id, "job_id": job_id},
            )

        captured_at = datetime.now(UTC).isoformat()
        snapshot_body = {
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
        profile_hash = hashlib.sha256(_stable_json(snapshot_body).encode("utf-8")).hexdigest()
        snapshot_id = profile_hash
        snapshot_payload = {
            "profile_snapshot_id": snapshot_id,
            "profile_id": profile.profile_id,
            "profile_hash": profile_hash,
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
            "captured_at": captured_at,
        }
        snapshot_path = self._snapshot_path(snapshot_id if job_id is None else job_id)
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_payload["snapshot_path"] = str(snapshot_path)
        snapshot_payload["profile_snapshot_path"] = str(snapshot_path)
        snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return ServiceResult(
            status="ok",
            message="profile snapshot captured",
            payload=snapshot_payload,
        )
