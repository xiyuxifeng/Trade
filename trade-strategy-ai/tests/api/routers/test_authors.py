from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest_asyncio
import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.authors import get_author_profile_service

pytestmark = pytest.mark.asyncio


@dataclass
class _FakeVersion:
    author_profile_version_id: str = "version-1"
    author_profile_id: str = "profile-1"
    author_id: str = "author-1"
    profile_kind: str = "method"
    profile_kind_label: str = "作者方法画像"
    version_no: int = 1
    lifecycle_state: str = "draft"
    lifecycle_label: str = "草稿"
    review_status: str = "draft"
    status_state: str = "partial"
    schema_version: str = "author-profile-v1"
    prompt_version: str | None = "author_method_profile_batch_v1"
    evidence_period: dict[str, Any] | None = None
    effective_period: dict[str, Any] | None = None
    source_versions: dict[str, Any] | None = None
    evidence_fingerprint: str | None = "evidence-fp"
    profile_fingerprint: str | None = "profile-fp"
    quality_status: str = "partial"
    partial_reasons: list[str] | None = None
    limitations: list[str] | None = None
    payload: dict[str, Any] | None = None
    evidence: dict[str, Any] | None = None
    source_bindings: dict[str, Any] | None = None
    supersession: dict[str, Any] | None = None
    published_at: str | None = None
    archived_at: str | None = None

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        del mode
        return {
            "author_profile_version_id": self.author_profile_version_id,
            "author_profile_id": self.author_profile_id,
            "author_id": self.author_id,
            "profile_kind": self.profile_kind,
            "profile_kind_label": self.profile_kind_label,
            "version_no": self.version_no,
            "lifecycle_state": self.lifecycle_state,
            "lifecycle_label": self.lifecycle_label,
            "review_status": self.review_status,
            "status_state": self.status_state,
            "schema_version": self.schema_version,
            "prompt_version": self.prompt_version,
            "evidence_period": self.evidence_period or {"from": None, "to": None},
            "effective_period": self.effective_period or {"from": None, "to": None},
            "source_versions": self.source_versions or {},
            "evidence_fingerprint": self.evidence_fingerprint,
            "profile_fingerprint": self.profile_fingerprint,
            "quality_status": self.quality_status,
            "partial_reasons": self.partial_reasons or ["证据区间不完整。"],
            "limitations": self.limitations or ["不是作者真实实盘表现。"],
            "payload": self.payload or {},
            "evidence": self.evidence or {},
            "source_bindings": self.source_bindings or {},
            "supersession": self.supersession or {},
            "published_at": self.published_at,
            "archived_at": self.archived_at,
        }


class _FakeAuthorProfileService:
    async def list_versions(self, **kwargs):
        assert kwargs["actor_role"] == "viewer"
        return {"state": "partial", "items": [_FakeVersion().model_dump()], "count": 1}

    async def create_draft(self, request, *, actor_id: str, actor_role: str):
        assert actor_role == "operator"
        assert request.profile_kind.value == "method"
        return _FakeVersion()

    async def submit_for_review(self, version_id: str, request, *, actor_id: str, actor_role: str):
        assert version_id == "version-1"
        assert actor_role == "operator"
        return _FakeVersion(lifecycle_state="pending_review", lifecycle_label="待审核", review_status="pending_review", status_state="pending_review")

    async def publish(self, version_id: str, request, *, actor_id: str, actor_role: str):
        assert actor_role == "operator"
        return _FakeVersion(lifecycle_state="published", lifecycle_label="已发布", review_status="published", status_state="published", published_at="2026-06-19T12:00:00+00:00")

    async def archive(self, version_id: str, request, *, actor_id: str, actor_role: str):
        assert actor_role == "operator"
        return _FakeVersion(lifecycle_state="archived", lifecycle_label="已归档", review_status="archived", status_state="archived", archived_at="2026-06-19T12:00:00+00:00")


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_author_profile_service] = lambda: _FakeAuthorProfileService()
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="viewer",
            api_key_label="viewer",
            authenticated=True,
            source="api_key",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


def _operator_override() -> CurrentPrincipal:
    return CurrentPrincipal(role="operator", api_key_label="operator", authenticated=True, source="api_key")


async def test_list_author_profiles_shows_partial_state(client: AsyncClient) -> None:
    response = await client.get("/api/ui/v1/authors/profiles")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "partial"
    assert body["items"][0]["lifecycle_state"] == "draft"
    assert body["items"][0]["partial_reasons"]


async def test_create_submit_publish_and_archive_author_profile_routes(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_principal] = _operator_override
    payload = {
        "author_id": "00000000-0000-0000-0000-000000000001",
        "profile_kind": "method",
        "schema_version": "author-profile-v1",
        "payload": {
            "conclusions": [
                {
                    "text": "偏好趋势交易",
                    "evidence": [{"id": "article-1"}],
                    "confidence": 0.7,
                    "provenance": {"lane": "article_expression"},
                    "version_binding": {"schema_version": "author-profile-v1"},
                }
            ]
        },
    }

    created = await client.post("/api/ui/v1/authors/profiles", json=payload)
    assert created.status_code == 201
    assert created.json()["lifecycle_state"] == "draft"

    submitted = await client.post("/api/ui/v1/authors/profiles/version-1/submit-review", json={"reason": "审核"})
    assert submitted.status_code == 200
    assert submitted.json()["lifecycle_state"] == "pending_review"

    published = await client.post("/api/ui/v1/authors/profiles/version-1/publish", json={"reason": "发布"})
    assert published.status_code == 200
    assert published.json()["lifecycle_state"] == "published"

    archived = await client.post("/api/ui/v1/authors/profiles/version-1/archive", json={"reason": "归档"})
    assert archived.status_code == 200
    assert archived.json()["lifecycle_state"] == "archived"
