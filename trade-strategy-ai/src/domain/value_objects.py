from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import FactSource, QualityStatus


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FactSourceRecord(DomainModel):
    fact_source: FactSource
    source_ref: str
    detail: str | None = None


class SourceProvenance(DomainModel):
    fact_sources: list[FactSourceRecord] = Field(default_factory=list)
    source_type: str | None = None
    source_ref: str | None = None
    correlation_id: UUID | None = None


class QualityRecord(DomainModel):
    status: QualityStatus
    reason: str | None = None
    raw_value: str | None = None


class AuditStamp(DomainModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_by: str


class LifecycleEventRecord(DomainModel):
    event_id: UUID = Field(default_factory=uuid4)
    object_type: str
    object_id: UUID
    from_state: str | None = None
    to_state: str
    actor_type: str
    actor_id: str
    reason_code: str
    reason_text: str | None = None
    before_json: dict[str, object] = Field(default_factory=dict)
    after_json: dict[str, object] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: UUID | None = None
