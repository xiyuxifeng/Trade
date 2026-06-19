from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from src.common.stage2_writer_routing import canonical_write_scope
from src.db.repositories.author_profile_repository import AuthorProfileRepository
from src.db.session import get_session_factory
from src.domain.enums import AuthorProfileKind, FormalLifecycleState, QualityStatus
from src.models.stage2_canonical import AuthorProfileVersion


PROFILE_KIND_LABELS = {
    AuthorProfileKind.method: "作者方法画像",
    AuthorProfileKind.rule: "作者规则画像",
    AuthorProfileKind.validated: "作者验证画像",
}
STATE_LABELS = {
    FormalLifecycleState.draft: "草稿",
    FormalLifecycleState.pending_review: "待审核",
    FormalLifecycleState.in_review: "审核中",
    FormalLifecycleState.approved: "已审核",
    FormalLifecycleState.published: "已发布",
    FormalLifecycleState.archived: "已归档",
    FormalLifecycleState.rejected: "已驳回",
    FormalLifecycleState.superseded: "已被替代",
}
OFFICIAL_STATES = {FormalLifecycleState.published, FormalLifecycleState.archived, FormalLifecycleState.superseded}


class AuthorProfileDraftRequest(BaseModel):
    author_id: UUID
    author_profile_id: UUID | None = None
    profile_kind: AuthorProfileKind
    schema_version: str
    prompt_version: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    source_article_ids: dict[str, Any] = Field(default_factory=dict)
    source_rule_version_ids: dict[str, Any] = Field(default_factory=dict)
    source_rule_family_ids: dict[str, Any] = Field(default_factory=dict)
    source_applicability_profile_ids: dict[str, Any] = Field(default_factory=dict)
    source_backtest_run_ids: dict[str, Any] = Field(default_factory=dict)
    source_backtest_result_ids: dict[str, Any] = Field(default_factory=dict)
    source_daily_review_ids: dict[str, Any] = Field(default_factory=dict)
    source_versions: dict[str, Any] = Field(default_factory=dict)
    evidence_from: date | None = None
    evidence_to: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    parent_version_id: UUID | None = None
    supersedes_version_id: UUID | None = None
    quality_status: QualityStatus = QualityStatus.partial
    reason: str | None = None
    source_surface: str = "/authors"

    @model_validator(mode="after")
    def _validate_periods(self) -> "AuthorProfileDraftRequest":
        if self.evidence_from and self.evidence_to and self.evidence_to < self.evidence_from:
            raise ValueError("evidence_to must be on or after evidence_from")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self

    @field_validator("payload")
    @classmethod
    def _validate_conclusions(cls, value: dict[str, Any]) -> dict[str, Any]:
        conclusions = value.get("conclusions", [])
        if conclusions is None:
            return value
        if not isinstance(conclusions, list):
            raise ValueError("payload.conclusions must be a list when present")
        for index, conclusion in enumerate(conclusions):
            if not isinstance(conclusion, dict):
                raise ValueError(f"payload.conclusions[{index}] must be an object")
            missing = [key for key in ("evidence", "confidence", "provenance", "version_binding") if key not in conclusion]
            if missing:
                raise ValueError(f"payload.conclusions[{index}] missing {', '.join(missing)}")
        return value


class AuthorProfileTransitionRequest(BaseModel):
    reason: str | None = None
    source_surface: str = "/authors"


class AuthorProfileVersionView(BaseModel):
    author_profile_version_id: str
    author_profile_id: str
    author_id: str
    profile_kind: str
    profile_kind_label: str
    version_no: int
    lifecycle_state: str
    lifecycle_label: str
    review_status: str
    status_state: str
    schema_version: str
    prompt_version: str | None = None
    evidence_period: dict[str, Any]
    effective_period: dict[str, Any]
    source_versions: dict[str, Any]
    evidence_fingerprint: str | None
    profile_fingerprint: str | None
    quality_status: str
    partial_reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    source_bindings: dict[str, Any] = Field(default_factory=dict)
    supersession: dict[str, Any] = Field(default_factory=dict)
    published_at: str | None = None
    archived_at: str | None = None


class AuthorProfileDiffView(BaseModel):
    from_version_id: str
    to_version_id: str
    same_profile: bool
    changed_fields: list[str]
    payload_changes: dict[str, Any]
    source_changes: dict[str, Any]
    period_changes: dict[str, Any]


def _fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def _state(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


class AuthorProfileService:
    def __init__(self, *, repository: AuthorProfileRepository | None = None, session_scope_factory: Any | None = None) -> None:
        self.repository = repository or AuthorProfileRepository()
        self._session_scope_factory = session_scope_factory or self._default_session_scope_factory

    @staticmethod
    @asynccontextmanager
    async def _default_session_scope_factory():
        session_factory = get_session_factory()
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def create_draft(
        self,
        request: AuthorProfileDraftRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> AuthorProfileVersionView:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to create an author profile draft")

        author_profile_id = request.author_profile_id or uuid4()
        evidence_payload = {
            "evidence": request.evidence,
            "sources": {
                "article_ids": request.source_article_ids,
                "rule_version_ids": request.source_rule_version_ids,
                "rule_family_ids": request.source_rule_family_ids,
                "applicability_profile_ids": request.source_applicability_profile_ids,
                "backtest_run_ids": request.source_backtest_run_ids,
                "backtest_result_ids": request.source_backtest_result_ids,
                "daily_review_ids": request.source_daily_review_ids,
                "versions": request.source_versions,
            },
            "evidence_period": {"from": request.evidence_from, "to": request.evidence_to},
        }
        profile_payload = {
            "profile_kind": request.profile_kind.value,
            "schema_version": request.schema_version,
            "prompt_version": request.prompt_version,
            "payload": request.payload,
            "effective_period": {"from": request.effective_from, "to": request.effective_to},
        }

        async with self._session_scope_factory() as session:
            version_no = await self.repository.next_version_no(
                session,
                author_profile_id=author_profile_id,
                profile_kind=request.profile_kind,
            )
            version = AuthorProfileVersion(
                author_profile_id=author_profile_id,
                author_id=request.author_id,
                profile_kind=request.profile_kind,
                version_no=version_no,
                schema_version=request.schema_version,
                prompt_version=request.prompt_version,
                lifecycle_state=FormalLifecycleState.draft,
                review_status="draft",
                as_of_from=request.evidence_from,
                as_of_to=request.evidence_to,
                evidence_from=request.evidence_from,
                evidence_to=request.evidence_to,
                effective_from=request.effective_from,
                effective_to=request.effective_to,
                payload=request.payload,
                evidence_json=request.evidence,
                source_article_ids=request.source_article_ids,
                source_rule_version_ids=request.source_rule_version_ids,
                source_rule_family_ids=request.source_rule_family_ids,
                source_applicability_profile_ids=request.source_applicability_profile_ids,
                source_backtest_run_ids=request.source_backtest_run_ids,
                source_backtest_result_ids=request.source_backtest_result_ids,
                source_daily_review_ids=request.source_daily_review_ids,
                source_versions_json=request.source_versions,
                evidence_fingerprint=_fingerprint(evidence_payload),
                profile_fingerprint=_fingerprint(profile_payload),
                parent_version_id=request.parent_version_id,
                supersedes_version_id=request.supersedes_version_id,
                quality_status=request.quality_status,
                created_by=actor_id,
                updated_by=actor_id,
            )
            with canonical_write_scope("author_profile", "AuthorProfileService.create_draft"):
                await self.repository.add_version(session, version)
                await self.repository.record_audit(
                    session,
                    version=version,
                    transition="created_draft",
                    actor_id=actor_id,
                    actor_role=actor_role,
                    reason=request.reason,
                    source_surface=request.source_surface,
                    before_state=None,
                    after_state=self._audit_state(version),
                )
            return self._to_view(version)

    async def list_versions(
        self,
        *,
        actor_id: str,
        actor_role: str,
        author_id: UUID | None = None,
        profile_kind: AuthorProfileKind | None = None,
        lifecycle_state: FormalLifecycleState | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        del actor_id
        if actor_role not in {"viewer", "operator", "admin"}:
            raise PermissionError("viewer permission is required to view author profiles")
        async with self._session_scope_factory() as session:
            rows = await self.repository.list_versions(
                session,
                author_id=author_id,
                profile_kind=profile_kind,
                lifecycle_state=lifecycle_state,
                limit=limit,
            )
            return {
                "state": self._collection_state(rows),
                "items": [self._to_view(row).model_dump(mode="json") for row in rows],
                "count": len(rows),
            }

    async def get_version(self, version_id: str | UUID, *, actor_id: str, actor_role: str) -> AuthorProfileVersionView:
        del actor_id
        if actor_role not in {"viewer", "operator", "admin"}:
            raise PermissionError("viewer permission is required to view author profiles")
        async with self._session_scope_factory() as session:
            version = await self.repository.get(session, version_id)
            if version is None:
                raise LookupError("author profile version not found")
            return self._to_view(version)

    async def submit_for_review(
        self,
        version_id: str | UUID,
        request: AuthorProfileTransitionRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> AuthorProfileVersionView:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to submit an author profile for review")
        return await self._transition(
            version_id,
            from_states={FormalLifecycleState.draft},
            to_state=FormalLifecycleState.pending_review,
            review_status="pending_review",
            transition="submitted_for_review",
            request=request,
            actor_id=actor_id,
            actor_role=actor_role,
        )

    async def publish(
        self,
        version_id: str | UUID,
        request: AuthorProfileTransitionRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> AuthorProfileVersionView:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to publish an author profile")
        async with self._session_scope_factory() as session:
            version = await self.repository.get(session, version_id)
            if version is None:
                raise LookupError("author profile version not found")
            if version.lifecycle_state not in {FormalLifecycleState.pending_review, FormalLifecycleState.in_review, FormalLifecycleState.approved}:
                raise ValueError("只有待审核或已审核的画像版本可以发布。")
            overlapping = await self.repository.find_overlapping_published(
                session,
                author_profile_id=version.author_profile_id,
                profile_kind=version.profile_kind,
                effective_from=version.effective_from,
                effective_to=version.effective_to,
                exclude_version_id=version.author_profile_version_id,
            )
            if overlapping:
                raise ValueError("已有同一时间段的已发布画像，需先人工归档旧版本后再发布。")
            before = self._audit_state(version)
            version.lifecycle_state = FormalLifecycleState.published
            version.review_status = "published"
            version.review_reason = request.reason
            version.reviewed_by = actor_id
            version.reviewed_at = _now()
            version.published_by = actor_id
            version.published_at = _now()
            version.updated_by = actor_id
            with canonical_write_scope("author_profile", "AuthorProfileService.publish"):
                await self.repository.record_audit(
                    session,
                    version=version,
                    transition="published",
                    actor_id=actor_id,
                    actor_role=actor_role,
                    reason=request.reason,
                    source_surface=request.source_surface,
                    before_state=before,
                    after_state=self._audit_state(version),
                )
            return self._to_view(version)

    async def archive(
        self,
        version_id: str | UUID,
        request: AuthorProfileTransitionRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> AuthorProfileVersionView:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to archive an author profile")
        return await self._transition(
            version_id,
            from_states={FormalLifecycleState.published, FormalLifecycleState.pending_review, FormalLifecycleState.in_review, FormalLifecycleState.draft},
            to_state=FormalLifecycleState.archived,
            review_status="archived",
            transition="archived",
            request=request,
            actor_id=actor_id,
            actor_role=actor_role,
        )

    async def diff_versions(
        self,
        from_version_id: str | UUID,
        to_version_id: str | UUID,
        *,
        actor_id: str,
        actor_role: str,
    ) -> AuthorProfileDiffView:
        del actor_id
        if actor_role not in {"viewer", "operator", "admin"}:
            raise PermissionError("viewer permission is required to compare author profile versions")
        async with self._session_scope_factory() as session:
            before = await self.repository.get(session, from_version_id)
            after = await self.repository.get(session, to_version_id)
            if before is None or after is None:
                raise LookupError("author profile version not found")
            payload_changes = self._dict_diff(before.payload or {}, after.payload or {})
            source_changes = self._dict_diff(self._source_bindings(before), self._source_bindings(after))
            period_changes = self._dict_diff(self._periods(before), self._periods(after))
            changed_fields = []
            if payload_changes:
                changed_fields.append("payload")
            if source_changes:
                changed_fields.append("sources")
            if period_changes:
                changed_fields.append("periods")
            return AuthorProfileDiffView(
                from_version_id=str(before.author_profile_version_id),
                to_version_id=str(after.author_profile_version_id),
                same_profile=before.author_profile_id == after.author_profile_id and before.profile_kind == after.profile_kind,
                changed_fields=changed_fields,
                payload_changes=payload_changes,
                source_changes=source_changes,
                period_changes=period_changes,
            )

    async def _transition(
        self,
        version_id: str | UUID,
        *,
        from_states: set[FormalLifecycleState],
        to_state: FormalLifecycleState,
        review_status: str,
        transition: str,
        request: AuthorProfileTransitionRequest,
        actor_id: str,
        actor_role: str,
    ) -> AuthorProfileVersionView:
        async with self._session_scope_factory() as session:
            version = await self.repository.get(session, version_id)
            if version is None:
                raise LookupError("author profile version not found")
            if version.lifecycle_state in OFFICIAL_STATES and to_state != FormalLifecycleState.archived:
                raise ValueError("已发布或已归档画像不能被自动改写，只能通过新草稿或人工归档处理。")
            if version.lifecycle_state not in from_states:
                raise ValueError("当前画像状态不允许执行该操作。")
            before = self._audit_state(version)
            version.lifecycle_state = to_state
            version.review_status = review_status
            version.review_reason = request.reason
            version.reviewed_by = actor_id if to_state != FormalLifecycleState.pending_review else version.reviewed_by
            version.reviewed_at = _now() if to_state != FormalLifecycleState.pending_review else version.reviewed_at
            version.updated_by = actor_id
            with canonical_write_scope("author_profile", f"AuthorProfileService.{transition}"):
                await self.repository.record_audit(
                    session,
                    version=version,
                    transition=transition,
                    actor_id=actor_id,
                    actor_role=actor_role,
                    reason=request.reason,
                    source_surface=request.source_surface,
                    before_state=before,
                    after_state=self._audit_state(version),
                )
            return self._to_view(version)

    def _to_view(self, version: AuthorProfileVersion) -> AuthorProfileVersionView:
        partial_reasons = self._partial_reasons(version)
        limitations = list((version.payload or {}).get("limitations", []))
        lifecycle_state = version.lifecycle_state
        return AuthorProfileVersionView(
            author_profile_version_id=str(version.author_profile_version_id),
            author_profile_id=str(version.author_profile_id),
            author_id=str(version.author_id),
            profile_kind=version.profile_kind.value,
            profile_kind_label=PROFILE_KIND_LABELS[version.profile_kind],
            version_no=version.version_no,
            lifecycle_state=lifecycle_state.value,
            lifecycle_label=STATE_LABELS.get(lifecycle_state, lifecycle_state.value),
            review_status=version.review_status,
            status_state="partial" if partial_reasons else lifecycle_state.value,
            schema_version=version.schema_version,
            prompt_version=version.prompt_version,
            evidence_period={"from": version.evidence_from, "to": version.evidence_to},
            effective_period={"from": version.effective_from, "to": version.effective_to},
            source_versions=version.source_versions_json or {},
            evidence_fingerprint=version.evidence_fingerprint,
            profile_fingerprint=version.profile_fingerprint,
            quality_status=_state(version.quality_status),
            partial_reasons=partial_reasons,
            limitations=limitations,
            payload=version.payload or {},
            evidence=version.evidence_json or {},
            source_bindings=self._source_bindings(version),
            supersession={
                "parent_version_id": str(version.parent_version_id) if version.parent_version_id else None,
                "supersedes_version_id": str(version.supersedes_version_id) if version.supersedes_version_id else None,
                "superseded_by_version_id": str(version.superseded_by_version_id) if version.superseded_by_version_id else None,
            },
            published_at=version.published_at.isoformat() if version.published_at else None,
            archived_at=version.reviewed_at.isoformat() if version.lifecycle_state == FormalLifecycleState.archived and version.reviewed_at else None,
        )

    def _partial_reasons(self, version: AuthorProfileVersion) -> list[str]:
        reasons: list[str] = []
        if not version.evidence_from or not version.evidence_to:
            reasons.append("证据区间不完整，当前画像只能作为部分证据查看。")
        if not version.effective_from:
            reasons.append("生效起点缺失，不能作为完整时间分段画像。")
        if not version.source_versions_json:
            reasons.append("来源版本未完整绑定，不能显示为完整画像。")
        if version.quality_status in {QualityStatus.partial, QualityStatus.ambiguous, QualityStatus.unresolved, QualityStatus.legacy_only}:
            reasons.append("证据质量不是完整验证状态。")
        return reasons

    def _collection_state(self, rows: list[AuthorProfileVersion]) -> str:
        if not rows:
            return "empty"
        if any(self._partial_reasons(row) for row in rows):
            return "partial"
        return "ready"

    def _source_bindings(self, version: AuthorProfileVersion) -> dict[str, Any]:
        return {
            "article_revision_ids": version.source_article_ids or {},
            "rule_version_ids": version.source_rule_version_ids or {},
            "rule_family_ids": version.source_rule_family_ids or {},
            "rule_applicability_profile_ids": version.source_applicability_profile_ids or {},
            "backtest_run_ids": version.source_backtest_run_ids or {},
            "backtest_result_ids": version.source_backtest_result_ids or {},
            "daily_review_ids": version.source_daily_review_ids or {},
            "source_versions": version.source_versions_json or {},
        }

    def _periods(self, version: AuthorProfileVersion) -> dict[str, Any]:
        return {
            "evidence_period": {"from": version.evidence_from, "to": version.evidence_to},
            "effective_period": {"from": version.effective_from, "to": version.effective_to},
        }

    def _audit_state(self, version: AuthorProfileVersion) -> dict[str, Any]:
        return {
            "version_id": str(version.author_profile_version_id),
            "version_no": version.version_no,
            "lifecycle_state": _state(version.lifecycle_state),
            "review_status": version.review_status,
            "profile_fingerprint": version.profile_fingerprint,
            "effective_period": {"from": str(version.effective_from) if version.effective_from else None, "to": str(version.effective_to) if version.effective_to else None},
        }

    def _dict_diff(self, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        changes: dict[str, Any] = {}
        for key in sorted(set(before) | set(after)):
            if before.get(key) != after.get(key):
                changes[key] = {"from": before.get(key), "to": after.get(key)}
        return changes
