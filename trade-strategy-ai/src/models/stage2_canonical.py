from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, Uuid, Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.enums import (
    AuthorProfileKind,
    DailyRuleSelectionState,
    DailyStrategyInstanceState,
    FactSource,
    FormalLifecycleState,
    PostMarketReviewState,
    ProposalLifecycleState,
    ProposalType,
    QualityStatus,
    SignalState,
    TradingDayPlanState,
)
from src.models.base import Base, TimestampMixin


def _enum(enum_cls: type[StrEnum], name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda enum: [member.value for member in enum],
        validate_strings=True,
    )


class PromptValidationState(StrEnum):
    pending = "pending"
    valid = "valid"
    invalid_json = "invalid_json"
    invalid_schema = "invalid_schema"
    invalid_evidence = "invalid_evidence"
    repaired = "repaired"
    failed = "failed"


class CandidateReviewState(StrEnum):
    extracted = "extracted"
    auto_review = "auto_review"
    manual_review = "manual_review"
    approved = "approved"
    rejected = "rejected"
    superseded = "superseded"


class DatasetLifecycleState(StrEnum):
    ready = "ready"
    partial = "partial"
    invalid = "invalid"
    archived = "archived"


class MigrationRunStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class MigrationItemStatus(StrEnum):
    pending = "pending"
    migrated = "migrated"
    rejected = "rejected"
    conflicted = "conflicted"
    skipped = "skipped"


class MigrationConflictStatus(StrEnum):
    open = "open"
    accepted = "accepted"
    rejected = "rejected"
    superseded = "superseded"


class RuleApplicabilityResultStatus(StrEnum):
    ready = "ready"
    insufficient_sample = "insufficient_sample"
    partial = "partial"
    invalid = "invalid"


class Authors(TimestampMixin, Base):
    __tablename__ = "authors"
    __table_args__ = (
        Index("uq_authors_source_key", "source", "source_author_key", unique=True),
    )

    author_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_author_key: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))


class ArticleRevision(TimestampMixin, Base):
    __tablename__ = "article_revisions"
    __table_args__ = (
        Index("uq_ar_article_rev", "article_id", "revision_no", unique=True),
        Index("uq_ar_article_hash", "article_id", "content_hash", unique=True),
    )

    article_revision_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    article_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("blog_articles.id", name="fk_ar_article", ondelete="CASCADE"),
        nullable=False,
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text)
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quality_status: Mapped[QualityStatus] = mapped_column(_enum(QualityStatus, "quality_status"), nullable=False)


class PromptRun(TimestampMixin, Base):
    __tablename__ = "prompt_runs"
    __table_args__ = (
        Index(
            "uq_pr_identity_retry",
            "prompt_name",
            "prompt_version",
            "schema_version",
            "model",
            "input_hash",
            "retry_count",
            unique=True,
        ),
        Index("ix_prompt_runs_run_id", "run_id"),
        Index("ix_prompt_runs_article_id", "article_id"),
    )

    prompt_run_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[str | None] = mapped_column(String(64))
    article_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("blog_articles.id", name="fk_pr_article", ondelete="SET NULL"),
    )
    prompt_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_name: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    input_object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    input_object_id: Mapped[str | None] = mapped_column(String(128))
    input_version_id: Mapped[str | None] = mapped_column(String(128))
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    raw_output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    raw_output_text: Mapped[str | None] = mapped_column(Text)
    validation_state: Mapped[PromptValidationState] = mapped_column(
        _enum(PromptValidationState, "prompt_validation_state"),
        nullable=False,
    )
    validation_errors: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    cost_amount: Mapped[float | None] = mapped_column(Numeric(18, 8))
    cost_currency: Mapped[str | None] = mapped_column(String(8))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LegacyIdMapping(Base):
    __tablename__ = "legacy_id_mappings"
    __table_args__ = (
        Index("uq_lidmap_legacy_key", "legacy_system", "legacy_object_type", "legacy_id", unique=True),
    )

    mapping_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    legacy_system: Mapped[str] = mapped_column(String(64), nullable=False)
    legacy_object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    legacy_id: Mapped[str] = mapped_column(String(512), nullable=False)
    canonical_object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_id: Mapped[UUID | None] = mapped_column(Uuid)
    canonical_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    mapping_status: Mapped[QualityStatus] = mapped_column(_enum(QualityStatus, "quality_status"), nullable=False)
    mapping_reason: Mapped[str | None] = mapped_column(Text)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LifecycleEvent(Base):
    __tablename__ = "lifecycle_events"
    __table_args__ = (
        Index("ix_lce_obj_occ", "object_type", "object_id", "occurred_at"),
        Index("ix_lce_corr", "correlation_id"),
    )

    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(32))
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(128))
    reason_code: Mapped[str | None] = mapped_column(String(64))
    reason_text: Mapped[str | None] = mapped_column(Text)
    before_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(128))


class MigrationRun(Base):
    __tablename__ = "migration_runs"
    __table_args__ = (
        Index("uq_mrun_name_version_fp", "migration_name", "migration_version", "source_fingerprint", unique=True),
    )

    migration_run_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    migration_name: Mapped[str] = mapped_column(String(128), nullable=False)
    migration_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[MigrationRunStatus] = mapped_column(_enum(MigrationRunStatus, "migration_run_status"), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pre_counts_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    post_counts_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conflict_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    report_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    recovery_point_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class MigrationRunItem(Base):
    __tablename__ = "migration_run_items"
    __table_args__ = (
        Index("uq_mritem_run_legacy", "migration_run_id", "legacy_object_type", "legacy_id", unique=True),
    )

    migration_run_item_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    migration_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("migration_runs.migration_run_id", name="fk_mri_run", ondelete="CASCADE"),
        nullable=False,
    )
    legacy_object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    legacy_id: Mapped[str] = mapped_column(String(512), nullable=False)
    canonical_object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_id: Mapped[UUID | None] = mapped_column(Uuid)
    canonical_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    status: Mapped[MigrationItemStatus] = mapped_column(_enum(MigrationItemStatus, "migration_item_status"), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class MigrationConflict(Base):
    __tablename__ = "migration_conflicts"

    migration_conflict_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    migration_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("migration_runs.migration_run_id", name="fk_mconf_run", ondelete="CASCADE"),
        nullable=False,
    )
    conflict_key: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[MigrationConflictStatus] = mapped_column(
        _enum(MigrationConflictStatus, "migration_conflict_status"),
        nullable=False,
    )
    legacy_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    canonical_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    resolution_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MigrationQualityReport(Base):
    __tablename__ = "migration_quality_reports"

    migration_quality_report_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    migration_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("migration_runs.migration_run_id", name="fk_mqr_run", ondelete="CASCADE"),
        nullable=False,
    )
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    report_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ArticleStructure(TimestampMixin, Base):
    __tablename__ = "article_structures"
    __table_args__ = (
        Index("uq_as_article_prompt", "article_id", "prompt_run_id", unique=True),
    )

    article_structure_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    article_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("blog_articles.id", name="fk_as_article", ondelete="CASCADE"),
        nullable=False,
    )
    article_revision_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("article_revisions.article_revision_id", name="fk_as_article_revision", ondelete="SET NULL"),
    )
    prompt_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("prompt_runs.prompt_run_id", name="fk_as_prompt_run", ondelete="CASCADE"),
        nullable=False,
    )
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    missing_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    inference_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    lifecycle_state: Mapped[FormalLifecycleState] = mapped_column(_enum(FormalLifecycleState, "formal_lifecycle"), nullable=False)
    quality_status: Mapped[QualityStatus] = mapped_column(_enum(QualityStatus, "quality_status"), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(64))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("article_structures.article_structure_id", name="fk_as_supersedes", ondelete="SET NULL"),
    )
    created_by: Mapped[str | None] = mapped_column(String(64))
    updated_by: Mapped[str | None] = mapped_column(String(64))


class RuleCandidate(TimestampMixin, Base):
    __tablename__ = "rule_candidates"
    __table_args__ = (
        Index("uq_rc_struct_idx", "article_structure_id", "candidate_index", unique=True),
    )

    rule_candidate_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    article_structure_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("article_structures.article_structure_id", name="fk_rc_article_structure", ondelete="CASCADE"),
        nullable=False,
    )
    source_article_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("blog_articles.id", name="fk_rc_source_article", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_index: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    explicit_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    inferred_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    missing_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    data_dependencies: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    backtestability_status: Mapped[str] = mapped_column(String(32), nullable=False)
    review_state: Mapped[CandidateReviewState] = mapped_column(_enum(CandidateReviewState, "candidate_review_state"), nullable=False)
    quality_status: Mapped[QualityStatus] = mapped_column(_enum(QualityStatus, "quality_status"), nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(64))
    updated_by: Mapped[str | None] = mapped_column(String(64))


class Rule(Base):
    __tablename__ = "rules"

    rule_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    business_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    current_published_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(64))


class RuleVersion(TimestampMixin, Base):
    __tablename__ = "rule_versions"
    __table_args__ = (
        Index("uq_rv_rule_verno", "rule_id", "version_no", unique=True),
        Index("uq_rv_rule_fp", "rule_id", "canonical_fingerprint", unique=True),
    )

    rule_version_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    rule_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("rules.rule_id", name="fk_rv_rule", ondelete="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    source_candidate_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("rule_candidates.rule_candidate_id", name="fk_rv_source_candidate", ondelete="SET NULL"),
    )
    canonical_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    lifecycle_state: Mapped[FormalLifecycleState] = mapped_column(_enum(FormalLifecycleState, "formal_lifecycle"), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    instrument_scope: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    condition_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    action_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    parameter_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    data_dependencies: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    quality_status: Mapped[QualityStatus] = mapped_column(_enum(QualityStatus, "quality_status"), nullable=False)
    parent_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("rule_versions.rule_version_id", name="fk_rv_parent", ondelete="SET NULL"),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[str | None] = mapped_column(String(64))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str | None] = mapped_column(String(64))
    updated_by: Mapped[str | None] = mapped_column(String(64))


class RuleFamily(TimestampMixin, Base):
    __tablename__ = "rule_families"
    __table_args__ = (
        Index("uq_rf_family_key", "family_key", unique=True),
        Index("uq_rf_fp", "canonical_fingerprint", unique=True),
    )

    rule_family_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    family_key: Mapped[str | None] = mapped_column(String(128))
    canonical_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str | None] = mapped_column(String(256))
    lifecycle_state: Mapped[FormalLifecycleState] = mapped_column(_enum(FormalLifecycleState, "formal_lifecycle"), nullable=False)
    quality_status: Mapped[QualityStatus] = mapped_column(_enum(QualityStatus, "quality_status"), nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(64))
    updated_by: Mapped[str | None] = mapped_column(String(64))


class RuleFamilyMembership(Base):
    __tablename__ = "rule_family_memberships"
    __table_args__ = (
        Index("uq_rfm_family_ver", "rule_family_id", "rule_version_id", unique=True),
    )

    membership_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    rule_family_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("rule_families.rule_family_id", name="fk_rfm_family", ondelete="CASCADE"),
        nullable=False,
    )
    rule_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("rule_versions.rule_version_id", name="fk_rfm_rule_version", ondelete="CASCADE"),
        nullable=False,
    )
    member_role: Mapped[str | None] = mapped_column(String(32))
    parameter_distance: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    approved_by: Mapped[str | None] = mapped_column(String(64))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DatasetSnapshot(TimestampMixin, Base):
    __tablename__ = "dataset_snapshots"
    __table_args__ = (
        Index("uq_ds_fp", "content_fingerprint", unique=True),
    )

    dataset_snapshot_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    content_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    trade_date: Mapped[date | None] = mapped_column(Date)
    market: Mapped[str] = mapped_column(String(32), nullable=False, default="CN")
    dataset_type: Mapped[str | None] = mapped_column(String(64))
    date_from: Mapped[date | None] = mapped_column(Date)
    date_to: Mapped[date | None] = mapped_column(Date)
    symbol_manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    ohlcv_manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    kaipan_manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    benchmark_symbol: Mapped[str | None] = mapped_column(String(32))
    market_state_definition_version: Mapped[str | None] = mapped_column(String(64))
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lifecycle_state: Mapped[DatasetLifecycleState] = mapped_column(_enum(DatasetLifecycleState, "dataset_lifecycle_state"), nullable=False)
    quality_report_id: Mapped[UUID | None] = mapped_column(Uuid)
    storage_ref: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class AuthorProfileVersion(TimestampMixin, Base):
    __tablename__ = "author_profile_versions"
    __table_args__ = (
        Index("uq_apv_asset_kind_ver", "author_profile_id", "profile_kind", "version_no", unique=True),
    )

    author_profile_version_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    author_profile_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    author_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("authors.author_id", name="fk_apv_author", ondelete="CASCADE"),
        nullable=False,
    )
    profile_kind: Mapped[AuthorProfileKind] = mapped_column(_enum(AuthorProfileKind, "author_profile_kind"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    lifecycle_state: Mapped[FormalLifecycleState] = mapped_column(_enum(FormalLifecycleState, "formal_lifecycle"), nullable=False)
    as_of_from: Mapped[date | None] = mapped_column(Date)
    as_of_to: Mapped[date | None] = mapped_column(Date)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source_article_ids: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source_rule_version_ids: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source_backtest_run_ids: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source_daily_review_ids: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    prompt_run_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("prompt_runs.prompt_run_id", name="fk_apv_prompt_run", ondelete="SET NULL"),
    )
    parent_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("author_profile_versions.author_profile_version_id", name="fk_apv_parent", ondelete="SET NULL"),
    )
    quality_status: Mapped[QualityStatus] = mapped_column(_enum(QualityStatus, "quality_status"), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[str | None] = mapped_column(String(64))
    created_by: Mapped[str | None] = mapped_column(String(64))
    updated_by: Mapped[str | None] = mapped_column(String(64))


class Strategy(Base):
    __tablename__ = "strategies"

    strategy_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_type: Mapped[str | None] = mapped_column(String(32))
    owner_id: Mapped[UUID | None] = mapped_column(Uuid)
    business_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    current_published_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(64))


class StrategyVersion(TimestampMixin, Base):
    __tablename__ = "strategy_versions"
    __table_args__ = (
        Index("uq_sv_asset_ver", "strategy_id", "version_no", unique=True),
    )

    strategy_version_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    strategy_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("strategies.strategy_id", name="fk_sv_strategy", ondelete="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    lifecycle_state: Mapped[FormalLifecycleState] = mapped_column(_enum(FormalLifecycleState, "formal_lifecycle"), nullable=False)
    parent_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("strategy_versions.strategy_version_id", name="fk_sv_parent", ondelete="SET NULL"),
    )
    risk_policy_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    selection_policy_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    universe_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    author_method_profile_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("author_profile_versions.author_profile_version_id", name="fk_sv_author_method", ondelete="SET NULL"),
    )
    author_rule_profile_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("author_profile_versions.author_profile_version_id", name="fk_sv_author_rule", ondelete="SET NULL"),
    )
    author_validated_profile_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("author_profile_versions.author_profile_version_id", name="fk_sv_author_validated", ondelete="SET NULL"),
    )
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    quality_status: Mapped[QualityStatus] = mapped_column(_enum(QualityStatus, "quality_status"), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[str | None] = mapped_column(String(64))
    created_by: Mapped[str | None] = mapped_column(String(64))
    updated_by: Mapped[str | None] = mapped_column(String(64))


class StrategyRuleMembership(Base):
    __tablename__ = "strategy_rule_memberships"
    __table_args__ = (
        Index("uq_srm_sv_rv", "strategy_version_id", "rule_version_id", unique=True),
    )

    membership_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    strategy_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("strategy_versions.strategy_version_id", name="fk_srm_strategy_version", ondelete="CASCADE"),
        nullable=False,
    )
    rule_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("rule_versions.rule_version_id", name="fk_srm_rule_version", ondelete="CASCADE"),
        nullable=False,
    )
    base_weight: Mapped[float | None] = mapped_column(Numeric(18, 8))
    status: Mapped[str | None] = mapped_column(String(32))
    configuration_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class DailyRuleSelection(TimestampMixin, Base):
    __tablename__ = "daily_rule_selections"
    __table_args__ = (
        Index("uq_drs_sv_dt_ms_rev", "strategy_version_id", "trade_date", "market_state_id", "revision_no", unique=True),
    )

    daily_rule_selection_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    strategy_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("strategy_versions.strategy_version_id", name="fk_drs_strategy_version", ondelete="CASCADE"),
        nullable=False,
    )
    market_state_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_rules_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    reduced_rules_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    blocked_rules_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    quality_status: Mapped[QualityStatus] = mapped_column(_enum(QualityStatus, "quality_status"), nullable=False)
    lifecycle_state: Mapped[DailyRuleSelectionState] = mapped_column(_enum(DailyRuleSelectionState, "daily_rule_selection_state"), nullable=False)
    source_run_id: Mapped[str | None] = mapped_column(String(128))
    created_by: Mapped[str | None] = mapped_column(String(64))
    updated_by: Mapped[str | None] = mapped_column(String(64))


class DailyRuleSelectionItem(TimestampMixin, Base):
    __tablename__ = "daily_rule_selection_items"
    __table_args__ = (
        Index("uq_drsi_sel_rule", "daily_rule_selection_id", "rule_version_id", unique=True),
    )

    daily_rule_selection_item_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    daily_rule_selection_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("daily_rule_selections.daily_rule_selection_id", name="fk_drsi_selection", ondelete="CASCADE"),
        nullable=False,
    )
    rule_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("rule_versions.rule_version_id", name="fk_drsi_rule_version", ondelete="CASCADE"),
        nullable=False,
    )
    decision: Mapped[str | None] = mapped_column(String(32))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class DailyStrategyInstance(TimestampMixin, Base):
    __tablename__ = "daily_strategy_instances"
    __table_args__ = (
        Index("uq_dsi_sv_dt_rev", "strategy_version_id", "trade_date", "revision_no", unique=True),
    )

    daily_strategy_instance_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    strategy_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("strategy_versions.strategy_version_id", name="fk_dsi_strategy_version", ondelete="CASCADE"),
        nullable=False,
    )
    daily_rule_selection_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("daily_rule_selections.daily_rule_selection_id", name="fk_dsi_selection", ondelete="CASCADE"),
        nullable=False,
    )
    market_snapshot_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("market_snapshots.id", name="fk_dsi_snapshot", ondelete="CASCADE"),
        nullable=False,
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_multiplier: Mapped[float | None] = mapped_column(Numeric(18, 8))
    position_limit: Mapped[float | None] = mapped_column(Numeric(18, 8))
    candidate_pool_snapshot_id: Mapped[UUID | None] = mapped_column(Uuid)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    lifecycle_state: Mapped[DailyStrategyInstanceState] = mapped_column(
        _enum(DailyStrategyInstanceState, "daily_strategy_instance_state"),
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(String(64))
    updated_by: Mapped[str | None] = mapped_column(String(64))


class TradingDayPlan(TimestampMixin, Base):
    __tablename__ = "trading_day_plans"
    __table_args__ = (
        Index("uq_tdp_inst_rev", "daily_strategy_instance_id", "revision_no", unique=True),
    )

    trading_day_plan_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    daily_strategy_instance_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("daily_strategy_instances.daily_strategy_instance_id", name="fk_tdp_instance", ondelete="CASCADE"),
        nullable=False,
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    lifecycle_state: Mapped[TradingDayPlanState] = mapped_column(_enum(TradingDayPlanState, "trading_day_plan_state"), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    approved_by: Mapped[str | None] = mapped_column(String(64))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    source_run_id: Mapped[str | None] = mapped_column(String(128))
    created_by: Mapped[str | None] = mapped_column(String(64))
    updated_by: Mapped[str | None] = mapped_column(String(64))


class PostMarketReview(TimestampMixin, Base):
    __tablename__ = "post_market_reviews"
    __table_args__ = (
        Index("uq_pmr_plan_rev", "trading_day_plan_id", "revision_no", unique=True),
    )

    post_market_review_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    trading_day_plan_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("trading_day_plans.trading_day_plan_id", name="fk_pmr_plan", ondelete="CASCADE"),
        nullable=False,
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    market_snapshot_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("market_snapshots.id", name="fk_pmr_snapshot", ondelete="SET NULL"),
    )
    market_state_id: Mapped[UUID | None] = mapped_column(Uuid)
    signal_results_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    attribution_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    lifecycle_state: Mapped[PostMarketReviewState] = mapped_column(_enum(PostMarketReviewState, "post_market_review_state"), nullable=False)
    quality_status: Mapped[QualityStatus] = mapped_column(_enum(QualityStatus, "quality_status"), nullable=False)
    prompt_run_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("prompt_runs.prompt_run_id", name="fk_pmr_prompt_run", ondelete="SET NULL"),
    )
    created_by: Mapped[str | None] = mapped_column(String(64))
    updated_by: Mapped[str | None] = mapped_column(String(64))


class OptimizationProposal(TimestampMixin, Base):
    __tablename__ = "optimization_proposals"
    __table_args__ = (
        Index("uq_op_review_type_target_rev", "post_market_review_id", "proposal_type", "target_asset_id", "revision_no", unique=True),
    )

    optimization_proposal_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    post_market_review_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("post_market_reviews.post_market_review_id", name="fk_op_review", ondelete="CASCADE"),
        nullable=False,
    )
    proposal_type: Mapped[ProposalType] = mapped_column(_enum(ProposalType, "proposal_type"), nullable=False)
    target_asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_asset_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    base_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    proposed_changes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    confidence: Mapped[float | None] = mapped_column(Numeric(18, 8))
    lifecycle_state: Mapped[ProposalLifecycleState] = mapped_column(_enum(ProposalLifecycleState, "proposal_lifecycle_state"), nullable=False)
    accepted_draft_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_by: Mapped[str | None] = mapped_column(String(64))
    updated_by: Mapped[str | None] = mapped_column(String(64))
