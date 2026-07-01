from __future__ import annotations

from uuid import uuid4

from src.domain.enums import AuthorProfileKind, FormalLifecycleState
from src.models.stage2_canonical import AuthorProfileVersion
from src.services.system_cost_control_service import SystemCostControlService


def test_incremental_profile_sample_reads_author_profile_version_source_versions_json() -> None:
    service = SystemCostControlService(session_scope_factory=None)
    row = AuthorProfileVersion(
        author_profile_version_id=uuid4(),
        author_profile_id=uuid4(),
        author_id=uuid4(),
        profile_kind=AuthorProfileKind.method,
        version_no=1,
        schema_version="author-profile-v1",
        lifecycle_state=FormalLifecycleState.draft,
        source_article_ids={"article_revision_ids": ["revision-1"]},
        source_versions_json={
            "incremental_update_scope": "changed_article_revision_group",
            "invalidation_reasons": ["new_article_revision"],
        },
        payload={},
        evidence_json={},
    )

    sample = service._build_incremental_profile_sample(row)

    assert sample["profile_kind"] == "method"
    assert sample["author_id"] == str(row.author_id)
    assert sample["update_scope"] == "changed_article_revision_group"
    assert sample["status"] == "draft_only"
    assert sample["invalidation_reasons"] == ["new_article_revision"]
