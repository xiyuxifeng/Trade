from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON as SAJSON, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin
from src.schemas.extraction_taxonomy import PrimaryType, ReviewDestination


def _jsonb_type() -> JSONB:
    return JSONB(astext_type=Text()).with_variant(SAJSON(), "sqlite")


class ExtractionQualityState(StrEnum):
    valid = "valid"
    partial = "partial"
    invalid = "invalid"
    needs_review = "needs_review"
    rejected = "rejected"
    superseded = "superseded"


class ExtractionReviewState(StrEnum):
    unreviewed = "unreviewed"
    queued = "queued"
    in_review = "in_review"
    accepted = "accepted"
    rejected = "rejected"
    repaired = "repaired"
    promoted = "promoted"
    archived = "archived"


class ReclassificationRunStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ReclassificationReviewState(StrEnum):
    unreviewed = "unreviewed"
    accepted = "accepted"
    rejected = "rejected"
    superseded = "superseded"


class ExtractionItem(TimestampMixin, Base):
    __tablename__ = "extraction_items"
    __table_args__ = (
        Index("uq_extraction_item_run_index", "prompt_run_id", "item_index", unique=True),
        Index("uq_extraction_item_fingerprint", "item_fingerprint", unique=True),
        Index("ix_extraction_item_article_type", "article_id", "primary_type"),
        Index("ix_extraction_item_destination_state", "review_destination", "review_state"),
    )

    extraction_item_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    article_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("blog_articles.id", name="fk_ei_article", ondelete="CASCADE"),
        nullable=False,
    )
    article_revision_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("article_revisions.article_revision_id", name="fk_ei_revision", ondelete="SET NULL"),
    )
    article_structure_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("article_structures.article_structure_id", name="fk_ei_structure", ondelete="CASCADE"),
        nullable=False,
    )
    prompt_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("prompt_runs.prompt_run_id", name="fk_ei_prompt_run", ondelete="CASCADE"),
        nullable=False,
    )
    item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    item_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    primary_type: Mapped[PrimaryType] = mapped_column(String(32), nullable=False)
    secondary_tags: Mapped[list[str]] = mapped_column(_jsonb_type(), nullable=False, default=list)
    taxonomy_payload: Mapped[dict[str, Any]] = mapped_column(_jsonb_type(), nullable=False, default=dict)
    source_evidence: Mapped[dict[str, Any]] = mapped_column(_jsonb_type(), nullable=False, default=dict)
    confidence: Mapped[dict[str, Any]] = mapped_column(_jsonb_type(), nullable=False, default=dict)
    quality_state: Mapped[ExtractionQualityState] = mapped_column(String(32), nullable=False)
    review_destination: Mapped[ReviewDestination] = mapped_column(String(48), nullable=False)
    review_state: Mapped[ExtractionReviewState] = mapped_column(String(32), nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(_jsonb_type(), nullable=False, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(64))
    updated_by: Mapped[str | None] = mapped_column(String(64))


class ExtractionReclassificationRun(Base):
    __tablename__ = "extraction_reclassification_runs"
    __table_args__ = (
        Index(
            "uq_extraction_reclass_identity",
            "taxonomy_version",
            "schema_version",
            "input_query_fingerprint",
            "classifier",
            unique=True,
        ),
    )

    reclassification_run_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    taxonomy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_population: Mapped[str] = mapped_column(String(256), nullable=False)
    input_query_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    classifier: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReclassificationRunStatus] = mapped_column(String(32), nullable=False)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)


class ExtractionReclassificationItem(TimestampMixin, Base):
    __tablename__ = "extraction_reclassification_items"
    __table_args__ = (
        Index("uq_extraction_reclass_candidate", "reclassification_run_id", "old_rule_candidate_id", unique=True),
    )

    reclassification_item_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    reclassification_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "extraction_reclassification_runs.reclassification_run_id",
            name="fk_eri_run",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    old_rule_candidate_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("rule_candidates.rule_candidate_id", name="fk_eri_old_candidate", ondelete="RESTRICT"),
        nullable=False,
    )
    extraction_item_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("extraction_items.extraction_item_id", name="fk_eri_extraction_item", ondelete="SET NULL"),
    )
    proposed_primary_type: Mapped[PrimaryType] = mapped_column(String(32), nullable=False)
    proposed_secondary_tags: Mapped[list[str]] = mapped_column(_jsonb_type(), nullable=False, default=list)
    proposed_taxonomy_payload: Mapped[dict[str, Any]] = mapped_column(_jsonb_type(), nullable=False, default=dict)
    confidence: Mapped[dict[str, Any]] = mapped_column(_jsonb_type(), nullable=False, default=dict)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    review_state: Mapped[ReclassificationReviewState] = mapped_column(String(32), nullable=False)
    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(_jsonb_type(), nullable=False, default=dict)
