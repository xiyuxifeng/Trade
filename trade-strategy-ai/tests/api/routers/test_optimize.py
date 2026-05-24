"""Canonical optimize UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.dependencies import verify_api_key
from api.routers.ui.optimize import get_optimize_service, get_session_scope_factory, get_strategy_library_service
from src.strategy_library.schemas import StrategyVersion, StrategyVersionStatus, StrategyVersionType


def _build_version_row(
    *,
    version_id: str,
    trader_id: str,
    strategy_date: date,
    status: str,
    version_type: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        version_name=version_id,
        trader_id=trader_id,
        strategy_date=strategy_date,
        status=status,
        version_type=version_type,
        released_at=datetime(2026, 5, 9, 10, 30, tzinfo=timezone.utc) if status == 'released' else None,
        source_article_ids=['article-1'],
        evidence_refs=['evidence-1'],
        strategy_payload={
            'recommendations': [
                {
                    'symbol': '000001.SZ',
                    'decision': 'buy',
                    'confidence': 0.91,
                    'entry_price': 10.0,
                    'target_price': 11.5,
                    'stop_loss_price': 9.2,
                    'volume': 100,
                    'rationale': 'trend confirmed',
                    'evidence_refs': ['evidence-1'],
                }
            ],
            'rules_snapshot': [{'rule_id': 'r-1'}],
        },
        notes='candidate notes',
        parent_version_id='parent-1',
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
    def __init__(self, version_rows: list[Any]):
        self.version_rows = version_rows

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
        if 'trader_strategy_versions' in text:
            version_name = self._criterion_value(stmt, 'version_name')
            if version_name:
                matched = [row for row in self.version_rows if row.version_name == version_name]
                return _FakeResult(matched)
            return _FakeResult(self.version_rows)
        return _FakeResult([])

    async def commit(self) -> None:
        return None


class _FakeSessionScope:
    def __init__(self, session: _FakeSession):
        self.session = session

    async def __aenter__(self) -> _FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@dataclass
class _FakeOptimizeService:
    advised: list[Any] = field(default_factory=list)

    def advise_rule_validations(self, rule_validations: list[Any]) -> Any:
        self.advised = list(rule_validations)
        return SimpleNamespace(payload={'count': len(rule_validations), 'rule_ids': [item.rule_id for item in rule_validations]})

    def filter_active_traders(
        self,
        *,
        backtest_results: dict[str, Any],
        config: Any | None = None,
        rule_validations: dict[str, list[Any]] | None = None,
    ) -> Any:
        return SimpleNamespace(
            payload={
                'config': config.__dict__ if config is not None else None,
                'results': [
                    {'trader_id': trader_id, 'rule_count': len(rule_validations.get(trader_id, [])) if rule_validations else 0}
                    for trader_id in backtest_results
                ],
            }
        )


@dataclass
class _FakeStrategyService:
    versions: dict[str, Any]
    create_calls: list[dict[str, Any]] = field(default_factory=list)

    async def get_version(self, session: Any, version_id: str) -> Any | None:
        return self.versions.get(version_id)

    async def create_candidate_version(
        self,
        session: Any,
        trader_id: str,
        strategy_date: date,
        parent_version_id: str,
        adjustments: list[Any],
        recommendations: list[Any],
        notes: str | None = None,
    ) -> Any:
        self.create_calls.append(
            {
                'trader_id': trader_id,
                'strategy_date': strategy_date,
                'parent_version_id': parent_version_id,
                'adjustments': adjustments,
                'recommendations': recommendations,
                'notes': notes,
            }
        )
        return StrategyVersion(
            version_id=f'{trader_id}_{strategy_date.isoformat()}_candidate_{parent_version_id[:8]}',
            trader_id=trader_id,
            strategy_date=strategy_date,
            status=StrategyVersionStatus.draft,
            version_type=StrategyVersionType.candidate,
            parent_version_id=parent_version_id,
            recommendations=recommendations,
            source_article_ids=[],
            evidence_refs=[],
            notes=notes,
            released_at=None,
            rules_snapshot=[],
        )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    version_rows = [
        _build_version_row(
            version_id='trader_a_2026-05-09_released',
            trader_id='trader_a',
            strategy_date=date(2026, 5, 9),
            status='released',
            version_type='manual',
        ),
        _build_version_row(
            version_id='trader_a_2026-05-09_candidate_parent123',
            trader_id='trader_a',
            strategy_date=date(2026, 5, 9),
            status='draft',
            version_type='candidate',
        ),
    ]
    fake_session = _FakeSession(version_rows)
    fake_optimize_service = _FakeOptimizeService()
    fake_strategy_service = _FakeStrategyService(
        versions={row.version_name: SimpleNamespace(**{
            'version_id': row.version_name,
            'trader_id': row.trader_id,
            'strategy_date': row.strategy_date,
            'status': row.status,
            'version_type': row.version_type,
            'parent_version_id': row.parent_version_id,
            'recommendations': [],
            'source_article_ids': [],
            'evidence_refs': [],
            'notes': row.notes,
            'released_at': row.released_at,
            'rules_snapshot': [],
        }) for row in version_rows},
    )

    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: 'test-key'
        app.dependency_overrides[get_session_scope_factory] = lambda: (lambda: _FakeSessionScope(fake_session))
        app.dependency_overrides[get_optimize_service] = lambda: fake_optimize_service
        app.dependency_overrides[get_strategy_library_service] = lambda: fake_strategy_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url='http://test') as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_canonical_optimize_router_covers_versions_advise_filter_and_candidate_creation(client: AsyncClient) -> None:
    versions = await client.get(
        '/api/ui/v1/optimize/versions',
        params={
            'trader_id': 'trader_a',
            'status': 'released',
            'version_type': 'manual',
            'date_from': '2026-05-09',
            'date_to': '2026-05-09',
            'skip': 0,
            'limit': 10,
        },
    )
    assert versions.status_code == 200
    assert versions.json()['count'] == 1
    assert versions.json()['items'][0]['version_id'] == 'trader_a_2026-05-09_released'

    detail = await client.get('/api/ui/v1/optimize/versions/trader_a_2026-05-09_released')
    assert detail.status_code == 200
    assert detail.json()['item']['recommendations'][0]['symbol'] == '000001.SZ'

    advise = await client.post(
        '/api/ui/v1/optimize/advise-rule-validations',
        json=[
            {
                'trader_id': 'trader_a',
                'strategy_version_id': 'sv-1',
                'rule_id': 'rule-1',
                'rule_text': 'price above moving average',
                'programmable': True,
                'validation_status': 'validated',
                'hit_count': 3,
                'sample_count': 5,
                'hit_rate': 0.6,
                'posterior_return_mean': 0.12,
                'posterior_return_median': 0.1,
                'notes': ['ok'],
            },
        ],
    )
    assert advise.status_code == 200
    assert advise.json()['count'] == 1

    filtered = await client.post(
        '/api/ui/v1/optimize/filter-active-traders',
        json={
            'backtest_results': [
                {
                    'trader_id': 'trader_a',
                    'date_from': '2026-05-01',
                    'date_to': '2026-05-09',
                    'summary': {
                        'total_days': 9,
                        'total_trades': 8,
                        'valid_trades': 6,
                        'skipped_trades': 2,
                        'win_rate': 0.5,
                        'avg_return_pct': 0.08,
                    },
                },
            ],
            'rule_validations': {
                'trader_a': [
                    {
                        'trader_id': 'trader_a',
                        'strategy_version_id': 'sv-1',
                        'rule_id': 'rule-1',
                        'rule_text': 'price above moving average',
                        'programmable': True,
                        'validation_status': 'validated',
                        'hit_count': 3,
                        'sample_count': 5,
                        'hit_rate': 0.6,
                        'notes': [],
                    },
                ],
            },
        },
    )
    assert filtered.status_code == 200
    assert filtered.json()['results'][0]['trader_id'] == 'trader_a'

    candidate = await client.post(
        '/api/ui/v1/optimize/create-candidate',
        json={
            'parent_version_id': 'trader_a_2026-05-09_released',
            'trader_id': 'trader_a',
            'strategy_date': '2026-05-09',
            'adjustments': [
                {
                    'trader_id': 'trader_a',
                    'rule_id': 'rule-1',
                    'current_status': 'hit_rate_too_low',
                    'suggestion': 'tighten threshold',
                    'confidence': 0.88,
                    'basis': 'hit_rate=0.60',
                },
            ],
            'recommendations': [
                {
                    'symbol': '000001.SZ',
                    'decision': 'buy',
                    'confidence': 0.91,
                    'entry_price': 10.0,
                    'target_price': 11.5,
                    'stop_loss_price': 9.2,
                    'volume': 100,
                    'rationale': 'trend confirmed',
                    'evidence_refs': ['evidence-1'],
                },
            ],
            'notes': 'keep the original recommendation and review later',
        },
    )
    assert candidate.status_code == 200
    assert candidate.json()['item']['version_type'] == 'candidate'
