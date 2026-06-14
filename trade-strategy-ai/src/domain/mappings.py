from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import Field

from src.domain.value_objects import DomainModel
from src.domain.enums import QualityStatus


class LegacyCanonicalMapping(DomainModel):
    mapping_id: UUID = Field(default_factory=uuid4)
    legacy_system: str
    legacy_object_type: str
    legacy_id: str
    canonical_object_type: str
    canonical_id: UUID | None = None
    canonical_version_id: UUID | None = None
    mapping_status: QualityStatus
    mapping_reason: str | None = None
    source_snapshot: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
