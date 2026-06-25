from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.enums import AuthorProfileKind
from src.models.stage2_canonical import Authors, AuthorProfileVersion, AuthorProfileVersionAudit


async def _build_session_factory(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'author_profiles.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Authors.__table__.create)
        await conn.run_sync(AuthorProfileVersion.__table__.create)
        await conn.run_sync(AuthorProfileVersionAudit.__table__.create)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def _session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return _session_scope, session_factory, engine


async def _seed_author(session_factory: async_sessionmaker[AsyncSession]) -> UUID:
    author_id = uuid4()
    async with session_factory() as session:
        session.add(Authors(author_id=author_id, source="test", source_author_key=f"author-{author_id}", display_name="测试作者"))
        await session.commit()
    return author_id


@pytest.mark.asyncio()
async def test_author_profile_audit_writer_sets_explicit_timestamps(tmp_path: Path) -> None:
    from src.common.stage2_writer_routing import canonical_write_scope
    from src.db.repositories.author_profile_repository import AuthorProfileRepository
    from src.domain.enums import FormalLifecycleState, QualityStatus

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    author_id = await _seed_author(session_factory)
    version = AuthorProfileVersion(
        author_profile_version_id=uuid4(),
        author_profile_id=uuid4(),
        author_id=author_id,
        profile_kind=AuthorProfileKind.method,
        version_no=1,
        schema_version="author-profile-v1",
        lifecycle_state=FormalLifecycleState.draft,
        payload={},
        evidence_json={},
        quality_status=QualityStatus.partial,
        created_by="operator-a",
        updated_by="operator-a",
    )

    async with session_scope() as session:
        session.add(version)
        await session.flush()
        with canonical_write_scope("author_profile", "AuthorProfileRepository.record_audit"):
            await AuthorProfileRepository().record_audit(
                session,
                version=version,
                transition="created_draft",
                actor_id="operator-a",
                actor_role="operator",
                reason="test",
                source_surface="/authors",
                before_state=None,
                after_state={"version_id": str(version.author_profile_version_id)},
            )
        audit = (await session.execute(AuthorProfileVersionAudit.__table__.select())).mappings().one()

    assert audit["created_at"] is not None
    assert audit["updated_at"] is not None

    await engine.dispose()


def _draft_payload(author_id: UUID, *, profile_id: UUID | None = None, conclusion: str = "偏好趋势交易"):
    from src.services.author_profile_service import AuthorProfileDraftRequest

    return AuthorProfileDraftRequest(
        author_id=author_id,
        author_profile_id=profile_id,
        profile_kind=AuthorProfileKind.method,
        schema_version="author-profile-v1",
        prompt_version="author_method_profile_batch_v1",
        payload={
            "conclusions": [
                {
                    "text": conclusion,
                    "evidence": [{"source": "article", "id": "article-revision-1"}],
                    "confidence": 0.72,
                    "provenance": {"lane": "article_expression"},
                    "version_binding": {"schema_version": "author-profile-v1", "prompt_version": "author_method_profile_batch_v1"},
                }
            ],
            "limitations": ["画像来自文章表达和审核证据，不代表真实实盘表现。"],
        },
        evidence={"article_expression": [{"article_revision_id": "article-revision-1"}]},
        source_article_ids={"article_revision_ids": ["article-revision-1"]},
        source_versions={"article_structure_schema": "article_analysis_v1"},
        evidence_from=date(2026, 1, 1),
        evidence_to=date(2026, 3, 31),
        effective_from=date(2026, 4, 1),
        effective_to=date(2026, 6, 30),
        reason="new evidence creates draft only",
    )


@pytest.mark.asyncio()
async def test_author_profile_lifecycle_version_creation_and_no_published_overwrite(tmp_path: Path) -> None:
    from src.services.author_profile_service import AuthorProfileService, AuthorProfileTransitionRequest

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    author_id = await _seed_author(session_factory)
    service = AuthorProfileService(session_scope_factory=session_scope)

    draft = await service.create_draft(_draft_payload(author_id), actor_id="operator-a", actor_role="operator")
    assert draft.lifecycle_state == "draft"
    assert draft.version_no == 1
    assert draft.evidence_period == {"from": date(2026, 1, 1), "to": date(2026, 3, 31)}
    assert draft.effective_period == {"from": date(2026, 4, 1), "to": date(2026, 6, 30)}
    assert draft.source_versions["article_structure_schema"] == "article_analysis_v1"

    pending = await service.submit_for_review(
        draft.author_profile_version_id,
        AuthorProfileTransitionRequest(reason="ready for human review"),
        actor_id="operator-a",
        actor_role="operator",
    )
    assert pending.lifecycle_state == "pending_review"
    published = await service.publish(
        pending.author_profile_version_id,
        AuthorProfileTransitionRequest(reason="human approved"),
        actor_id="reviewer-a",
        actor_role="operator",
    )
    assert published.lifecycle_state == "published"

    revision = await service.create_draft(
        _draft_payload(author_id, profile_id=UUID(draft.author_profile_id), conclusion="新增文章显示风险表达更保守"),
        actor_id="operator-a",
        actor_role="operator",
    )
    assert revision.version_no == 2
    assert revision.lifecycle_state == "draft"

    submitted_revision = await service.submit_for_review(
        revision.author_profile_version_id,
        AuthorProfileTransitionRequest(reason="review revision"),
        actor_id="operator-a",
        actor_role="operator",
    )
    with pytest.raises(ValueError, match="已有同一时间段的已发布画像"):
        await service.publish(
            submitted_revision.author_profile_version_id,
            AuthorProfileTransitionRequest(reason="must not overwrite published"),
            actor_id="reviewer-a",
            actor_role="operator",
        )

    still_published = await service.get_version(published.author_profile_version_id, actor_id="viewer", actor_role="viewer")
    assert still_published.lifecycle_state == "published"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_author_profile_archive_then_publish_revision_and_diff_versions(tmp_path: Path) -> None:
    from src.services.author_profile_service import AuthorProfileService, AuthorProfileTransitionRequest

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    author_id = await _seed_author(session_factory)
    service = AuthorProfileService(session_scope_factory=session_scope)

    first = await service.create_draft(_draft_payload(author_id), actor_id="operator-a", actor_role="operator")
    first = await service.submit_for_review(first.author_profile_version_id, AuthorProfileTransitionRequest(), actor_id="operator-a", actor_role="operator")
    first = await service.publish(first.author_profile_version_id, AuthorProfileTransitionRequest(reason="publish v1"), actor_id="reviewer-a", actor_role="operator")
    archived = await service.archive(first.author_profile_version_id, AuthorProfileTransitionRequest(reason="manual archive"), actor_id="reviewer-a", actor_role="operator")
    assert archived.lifecycle_state == "archived"

    second = await service.create_draft(
        _draft_payload(author_id, profile_id=UUID(first.author_profile_id), conclusion="新增证据显示更重视回撤控制"),
        actor_id="operator-a",
        actor_role="operator",
    )
    second = await service.submit_for_review(second.author_profile_version_id, AuthorProfileTransitionRequest(), actor_id="operator-a", actor_role="operator")
    second = await service.publish(second.author_profile_version_id, AuthorProfileTransitionRequest(reason="publish v2"), actor_id="reviewer-a", actor_role="operator")
    assert second.lifecycle_state == "published"

    diff = await service.diff_versions(first.author_profile_version_id, second.author_profile_version_id, actor_id="viewer", actor_role="viewer")
    assert diff.same_profile is True
    assert "payload" in diff.changed_fields
    assert "conclusions" in diff.payload_changes

    await engine.dispose()


@pytest.mark.asyncio()
async def test_author_profile_rejects_conclusions_without_evidence_binding(tmp_path: Path) -> None:
    from pydantic import ValidationError
    from src.services.author_profile_service import AuthorProfileDraftRequest

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    author_id = await _seed_author(session_factory)

    with pytest.raises(ValidationError):
        AuthorProfileDraftRequest(
            author_id=author_id,
            profile_kind=AuthorProfileKind.validated,
            schema_version="author-profile-v1",
            payload={"conclusions": [{"text": "缺少证据绑定"}]},
        )

    await engine.dispose()
