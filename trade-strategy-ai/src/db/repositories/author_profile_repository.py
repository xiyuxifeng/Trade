from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import AuthorProfileKind, FormalLifecycleState
from src.models.stage2_canonical import AuthorProfileVersion, AuthorProfileVersionAudit
from src.common.stage2_writer_routing import require_canonical_write


class AuthorProfileRepository:
    """Canonical author profile version repository."""

    async def get(self, session: AsyncSession, version_id: str | UUID) -> AuthorProfileVersion | None:
        if not isinstance(version_id, UUID):
            version_id = UUID(str(version_id))
        return await session.get(AuthorProfileVersion, version_id)

    async def list_versions(
        self,
        session: AsyncSession,
        *,
        author_id: UUID | None = None,
        profile_kind: AuthorProfileKind | None = None,
        lifecycle_state: FormalLifecycleState | None = None,
        limit: int = 50,
    ) -> list[AuthorProfileVersion]:
        stmt = select(AuthorProfileVersion)
        if author_id is not None:
            stmt = stmt.where(AuthorProfileVersion.author_id == author_id)
        if profile_kind is not None:
            stmt = stmt.where(AuthorProfileVersion.profile_kind == profile_kind)
        if lifecycle_state is not None:
            stmt = stmt.where(AuthorProfileVersion.lifecycle_state == lifecycle_state)
        stmt = stmt.order_by(AuthorProfileVersion.updated_at.desc(), AuthorProfileVersion.version_no.desc()).limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())

    async def next_version_no(
        self,
        session: AsyncSession,
        *,
        author_profile_id: UUID,
        profile_kind: AuthorProfileKind,
    ) -> int:
        value = await session.scalar(
            select(func.max(AuthorProfileVersion.version_no)).where(
                AuthorProfileVersion.author_profile_id == author_profile_id,
                AuthorProfileVersion.profile_kind == profile_kind,
            )
        )
        return int(value or 0) + 1

    async def add_version(self, session: AsyncSession, version: AuthorProfileVersion) -> AuthorProfileVersion:
        require_canonical_write("author_profile", "AuthorProfileRepository.add_version")
        session.add(version)
        await session.flush()
        return version

    async def find_overlapping_published(
        self,
        session: AsyncSession,
        *,
        author_profile_id: UUID,
        profile_kind: AuthorProfileKind,
        effective_from: date | None,
        effective_to: date | None,
        exclude_version_id: UUID | None = None,
    ) -> list[AuthorProfileVersion]:
        stmt = select(AuthorProfileVersion).where(
            AuthorProfileVersion.author_profile_id == author_profile_id,
            AuthorProfileVersion.profile_kind == profile_kind,
            AuthorProfileVersion.lifecycle_state == FormalLifecycleState.published,
        )
        if exclude_version_id is not None:
            stmt = stmt.where(AuthorProfileVersion.author_profile_version_id != exclude_version_id)
        if effective_from is not None:
            stmt = stmt.where(or_(AuthorProfileVersion.effective_to.is_(None), AuthorProfileVersion.effective_to >= effective_from))
        if effective_to is not None:
            stmt = stmt.where(or_(AuthorProfileVersion.effective_from.is_(None), AuthorProfileVersion.effective_from <= effective_to))
        result = await session.scalars(stmt)
        return list(result.all())

    async def record_audit(
        self,
        session: AsyncSession,
        *,
        version: AuthorProfileVersion,
        transition: str,
        actor_id: str,
        actor_role: str,
        reason: str | None,
        source_surface: str,
        before_state: dict | None,
        after_state: dict | None,
    ) -> None:
        require_canonical_write("author_profile", "AuthorProfileRepository.record_audit")
        now = datetime.now(UTC)
        session.add(
            AuthorProfileVersionAudit(
                author_profile_version_id=version.author_profile_version_id,
                transition=transition,
                actor_id=actor_id,
                actor_role=actor_role,
                reason=reason,
                source_surface=source_surface,
                before_state_json=before_state,
                after_state_json=after_state,
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()
