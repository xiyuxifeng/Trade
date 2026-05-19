from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui.rule_pool import get_rule_applicability_service
from src.services.base import ServiceResult


@dataclass
class _FakeRuleApplicabilityService:
    calls: list[dict[str, Any]]

    def __init__(self) -> None:
        self.calls = []

    async def list_profiles(self, **kwargs) -> ServiceResult:
        self.calls.append({"method": "list_profiles", **kwargs})
        return ServiceResult(
            status="ok",
            message="ok",
            payload={
                "count": 1,
                "total": 1,
                "skip": 0,
                "limit": 20,
                "items": [_profile_payload("11111111-1111-1111-1111-111111111111")],
            },
        )

    async def get_profile(self, profile_id: str) -> ServiceResult:
        self.calls.append({"method": "get_profile", "profile_id": profile_id})
        return ServiceResult(status="ok", message="ok", payload={"profile": _profile_payload(profile_id)})

    async def build_profile(self, **kwargs) -> ServiceResult:
        self.calls.append({"method": "build_profile", **kwargs})
        return ServiceResult(status="ok", message="ok", payload={"profile": _profile_payload("22222222-2222-2222-2222-222222222222")})

    async def review_profile(self, **kwargs) -> ServiceResult:
        self.calls.append({"method": "review_profile", **kwargs})
        return ServiceResult(status="ok", message="ok", payload={"profile_id": kwargs["profile_id"]})


def _profile_payload(profile_id: str) -> dict[str, Any]:
    return {
        "profile_id": profile_id,
        "rule_id": "rule-1",
        "profile_version": "rule-applicability-v1",
        "source_backtest_id": "backtest-1",
        "source_rule_version": None,
        "market_regime_version": "market-regime-v3",
        "source_feature_version": "market-regime-features-v3",
        "review_status": "draft",
        "min_sample_count": 5,
        "confidence": 0.81,
        "applicable_regimes": [],
        "blocked_regimes": [],
        "neutral_regimes": [],
        "best_market_conditions": {},
        "worst_market_conditions": {},
        "summary": {},
        "storage_ref": {},
        "reviewed_by": None,
        "reviewed_at": None,
        "created_at": "2026-05-19T08:00:00Z",
        "updated_at": "2026-05-19T08:00:00Z",
    }


@pytest.fixture()
async def client() -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[verify_api_key] = lambda: "demo-key"
    fake_service = _FakeRuleApplicabilityService()
    app.dependency_overrides[get_rule_applicability_service] = lambda: fake_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(verify_api_key, None)
    app.dependency_overrides.pop(get_rule_applicability_service, None)


@pytest.mark.asyncio()
async def test_rule_pool_applicability_routes_cover_list_detail_generate_and_review(client: AsyncClient) -> None:
    """Rule pool applicability routes should expose list/detail/generate/review contracts."""
    list_response = await client.get("/api/ui/v1/rule-pool/rule-1/applicability-profiles")
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["profile_id"] == "11111111-1111-1111-1111-111111111111"

    detail_response = await client.get("/api/ui/v1/rule-pool/rule-1/applicability-profiles/11111111-1111-1111-1111-111111111111")
    assert detail_response.status_code == 200
    assert detail_response.json()["item"]["profile_id"] == "11111111-1111-1111-1111-111111111111"

    generate_response = await client.post(
        "/api/ui/v1/rule-pool/rule-1/applicability-profiles/generate",
        json={
            "source_backtest_id": "backtest-1",
            "profile_version": "rule-applicability-v1",
            "min_sample_count": 5,
            "review_status": "draft",
            "reviewed_by": "web",
        },
    )
    assert generate_response.status_code == 200
    assert generate_response.json()["item"]["profile_id"] == "22222222-2222-2222-2222-222222222222"

    review_response = await client.post(
        "/api/ui/v1/rule-pool/rule-1/applicability-profiles/11111111-1111-1111-1111-111111111111/review",
        json={"review_status": "active", "reviewed_by": "web"},
    )
    assert review_response.status_code == 200
    assert review_response.json()["item"]["profile_id"] == "11111111-1111-1111-1111-111111111111"
