"""Canonical rule-pool UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.routers.ui.rule_pool import get_rule_pool_service, get_session_scope_factory


def _build_rule_row(
    *,
    rule_id: str,
    source_type: str,
    rule_type: str,
    instrument_focus: str,
    mapping_status: str,
    review_status: str,
    mapped_condition: dict[str, Any] | None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id='11111111-1111-1111-1111-111111111111',
        rule_id=rule_id,
        source_article_ids=['article-1'],
        source_type=source_type,
        rule_type=rule_type,
        instrument_focus=instrument_focus,
        extraction_layer={
            'raw_text': 'price above moving average',
            'mapped_condition': mapped_condition,
        },
        mapping_status=mapping_status,
        mapped_by='analyst' if mapping_status == 'mapped' else None,
        mapped_at=datetime(2026, 5, 9, 11, 0, tzinfo=timezone.utc) if mapping_status == 'mapped' else None,
        initial_confidence=0.61,
        validated_confidence=0.74 if mapping_status == 'mapped' else None,
        review_status=review_status,
        reviewed_by='web' if review_status != 'pending' else None,
        reviewed_at=datetime(2026, 5, 9, 11, 15, tzinfo=timezone.utc) if review_status != 'pending' else None,
        backtest_triggered_at=datetime(2026, 5, 9, 11, 30, tzinfo=timezone.utc),
        backtest_result={'run_id': 'run-1', 'hit_rate': 0.65},
        backtest_hits=13,
        backtest_misses=7,
        backtest_samples=20,
        used_in_prediction=True,
        prediction_count=3,
        last_used_at=datetime(2026, 5, 9, 12, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 9, 12, 30, tzinfo=timezone.utc),
    )


class _FakeResult:
    def __init__(self, rows: list[Any]):
        self._rows = rows

    def scalars(self) -> "_FakeResult":
        return self

    def all(self) -> list[Any]:
        return list(self._rows)

    def scalar_one_or_none(self) -> Any | None:
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, rule_rows: list[Any]):
        self.rule_rows = rule_rows

    @staticmethod
    def _criterion_value(stmt: Any, field_name: str) -> Any | None:
        for criterion in getattr(stmt, '_where_criteria', ()):
            left = getattr(criterion, 'left', None)
            right = getattr(criterion, 'right', None)
            if left is not None and field_name in str(left) and hasattr(right, 'value'):
                return right.value
        return None

    async def execute(self, stmt: Any) -> _FakeResult:
        text = str(stmt)
        if 'rule_pool' in text:
            rule_id = self._criterion_value(stmt, 'rule_id')
            if rule_id:
                matched = [row for row in self.rule_rows if row.rule_id == rule_id]
                return _FakeResult(matched)
            return _FakeResult(self.rule_rows)
        return _FakeResult([])


class _FakeSessionScope:
    def __init__(self, session: _FakeSession):
        self.session = session

    async def __aenter__(self) -> _FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@dataclass
class _FakeRulePoolService:
    review_calls: list[tuple[str, str, bool, str]] = field(default_factory=list)
    review_batch_calls: list[tuple[str, str, int, bool, str]] = field(default_factory=list)

    async def review_rule(self, rule_id: str, *, decision: str, force: bool = False, reviewed_by: str = 'web') -> Any:
        self.review_calls.append((rule_id, decision, force, reviewed_by))
        return SimpleNamespace(
            status='error',
            payload={
                'rule_id': rule_id,
                'status': 'compatibility_only',
                'force': force,
                'reviewed_by': reviewed_by,
            },
        )

    async def review_batch(
        self,
        *,
        decision: str,
        status: str = 'pending',
        limit: int = 50,
        force: bool = False,
        reviewed_by: str = 'web',
    ) -> Any:
        self.review_batch_calls.append((decision, status, limit, force, reviewed_by))
        return SimpleNamespace(
            status='error',
            payload={
                'decision': decision,
                'status': 'compatibility_only',
                'filter_status': status,
                'updated_count': limit,
                'reviewed_by': reviewed_by,
            },
        )

    async def list_filter_options(self) -> Any:
        return SimpleNamespace(
            status='ok',
            payload={
                'review_statuses': ['pending', 'approved', 'rejected'],
                'mapping_statuses': ['mapped', 'unmapped'],
                'source_types': ['standalone', 'derived', 'experience'],
                'rule_types': ['breakout', 'pullback'],
                'instrument_focuses': ['mixed', 'stock'],
            },
        )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    rule_rows = [
        _build_rule_row(
            rule_id='rule-1',
            source_type='standalone',
            rule_type='breakout',
            instrument_focus='stock',
            mapping_status='unmapped',
            review_status='pending',
            mapped_condition=None,
        ),
        _build_rule_row(
            rule_id='rule-2',
            source_type='derived',
            rule_type='pullback',
            instrument_focus='mixed',
            mapping_status='mapped',
            review_status='approved',
            mapped_condition={'price': 'above_ma20'},
        ),
    ]
    fake_session = _FakeSession(rule_rows)
    fake_rule_pool_service = _FakeRulePoolService()

    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: 'test-key'
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            role="operator",
            api_key_label="tester",
            authenticated=True,
            source="api_key",
        )
        app.dependency_overrides[get_session_scope_factory] = lambda: (lambda: _FakeSessionScope(fake_session))
        app.dependency_overrides[get_rule_pool_service] = lambda: fake_rule_pool_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url='http://test') as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_canonical_rule_pool_router_keeps_reads_and_rejects_legacy_review_actions(client: AsyncClient) -> None:
    options = await client.get('/api/ui/v1/rule-pool/filter-options')
    assert options.status_code == 200
    assert options.json()['review_statuses'] == ['pending', 'approved', 'rejected']

    rules = await client.get(
        '/api/ui/v1/rule-pool',
        params={
            'status': 'pending',
            'rule_type': 'breakout',
            'mapping_status': 'unmapped',
            'source_type': 'standalone',
            'instrument_focus': 'stock',
            'skip_no_mapped': False,
            'skip': 0,
            'limit': 10,
        },
    )
    assert rules.status_code == 200
    assert rules.json()['count'] == 1
    assert rules.json()['items'][0]['rule_id'] == 'rule-1'
    assert rules.json()['items'][0]['mapped'] is False

    rule_detail = await client.get('/api/ui/v1/rule-pool/rule-2')
    assert rule_detail.status_code == 200
    assert rule_detail.json()['item']['mapped'] is True
    assert rule_detail.json()['item']['extraction_layer']['mapped_condition']['price'] == 'above_ma20'

    review = await client.post(
        '/api/ui/v1/rule-pool/rule-1/review',
        json={'decision': 'approve', 'force': False, 'reviewed_by': 'web'},
    )
    assert review.status_code == 409
    assert review.json()['detail']['status'] == 'compatibility_only'

    batch = await client.post(
        '/api/ui/v1/rule-pool/review-batch',
        json={'decision': 'reject', 'status': 'pending', 'limit': 25, 'force': True, 'reviewed_by': 'web'},
    )
    assert batch.status_code == 409
    assert batch.json()['detail']['status'] == 'compatibility_only'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("principal", "path", "payload"),
    [
        (
            CurrentPrincipal(role="anonymous", api_key_label=None, authenticated=False, source="anonymous"),
            "/api/ui/v1/rule-pool/rule-1/review",
            {"decision": "approve", "force": False, "reviewed_by": "web"},
        ),
        (
            CurrentPrincipal(role="viewer", api_key_label="viewer", authenticated=True, source="api_key"),
            "/api/ui/v1/rule-pool/rule-1/review",
            {"decision": "approve", "force": False, "reviewed_by": "web"},
        ),
        (
            CurrentPrincipal(role="anonymous", api_key_label=None, authenticated=False, source="anonymous"),
            "/api/ui/v1/rule-pool/review-batch",
            {"decision": "reject", "status": "pending", "limit": 25, "force": True, "reviewed_by": "web"},
        ),
        (
            CurrentPrincipal(role="viewer", api_key_label="viewer", authenticated=True, source="api_key"),
            "/api/ui/v1/rule-pool/review-batch",
            {"decision": "reject", "status": "pending", "limit": 25, "force": True, "reviewed_by": "web"},
        ),
    ],
)
async def test_rule_pool_compat_mutation_endpoints_reject_non_operator_before_service_calls(
    principal: CurrentPrincipal,
    path: str,
    payload: dict[str, Any],
) -> None:
    fake_session = _FakeSession([])
    fake_rule_pool_service = _FakeRulePoolService()

    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_current_principal] = lambda: principal
        app.dependency_overrides[get_session_scope_factory] = lambda: (lambda: _FakeSessionScope(fake_session))
        app.dependency_overrides[get_rule_pool_service] = lambda: fake_rule_pool_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(path, json=payload)
        assert response.status_code == 403
        assert fake_rule_pool_service.review_calls == []
        assert fake_rule_pool_service.review_batch_calls == []
    finally:
        app.dependency_overrides.clear()
