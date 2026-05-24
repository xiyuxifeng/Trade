"""Strategy Studio UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Any, AsyncIterator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.dependencies import verify_api_key
from api.routers.ui.strategy_studio import (
    get_optimize_service,
    get_rule_pool_service,
    get_session_scope_factory,
    get_strategy_library_service,
)
from src.backtest.schemas import BacktestResult, BacktestSummary
from src.services.base import ServiceResult
from src.strategy_library.schemas import (
    StrategyAdjustment,
    StrategyRecommendation,
    StrategyVersion,
    StrategyVersionStatus,
    StrategyVersionType,
)


def _build_version_row(
    *,
    version_id: str,
    trader_id: str,
    strategy_date: date,
    status: str,
    version_type: str,
    parent_version_id: str | None,
    notes: str,
    rules_snapshot: list[dict[str, Any]],
) -> SimpleNamespace:
    return SimpleNamespace(
        version_name=version_id,
        trader_id=trader_id,
        strategy_date=strategy_date,
        status=status,
        version_type=version_type,
        released_at=datetime(2026, 5, 9, 10, 30, tzinfo=timezone.utc) if status == 'released' else None,
        source_article_ids=['article-1', 'article-2'],
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
            'rules_snapshot': rules_snapshot,
        },
        notes=notes,
        parent_version_id=parent_version_id,
    )


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
        id=UUID('11111111-1111-1111-1111-111111111111'),
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

    def scalar(self) -> Any | None:
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, version_rows: list[Any], rule_rows: list[Any]):
        self.version_rows = version_rows
        self.rule_rows = rule_rows
        self.commits = 0

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
        if 'rule_pool' in text:
            rule_id = self._criterion_value(stmt, 'rule_id')
            if rule_id:
                matched = [row for row in self.rule_rows if row.rule_id == rule_id]
                return _FakeResult(matched)
            return _FakeResult(self.rule_rows)
        return _FakeResult([])

    async def commit(self) -> None:
        self.commits += 1


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
    filtered: dict[str, BacktestResult] = field(default_factory=dict)

    def advise_rule_validations(self, rule_validations: list[Any]) -> ServiceResult:
        self.advised = list(rule_validations)
        return ServiceResult(
            status='ok',
            message='strategy advise completed',
            payload={'count': len(rule_validations), 'rule_ids': [item.rule_id for item in rule_validations]},
        )

    def filter_active_traders(
        self,
        *,
        backtest_results: dict[str, BacktestResult],
        config: Any | None = None,
        rule_validations: dict[str, list[Any]] | None = None,
    ) -> ServiceResult:
        self.filtered = backtest_results
        return ServiceResult(
            status='ok',
            message='active trader filter completed',
            payload={
                'config': config.__dict__ if config is not None else None,
                'results': [
                    {
                        'trader_id': trader_id,
                        'valid_trades': result.summary.valid_trades if result.summary else 0,
                        'rule_count': len(rule_validations.get(trader_id, [])) if rule_validations else 0,
                    }
                    for trader_id, result in backtest_results.items()
                ],
            },
        )


@dataclass
class _FakeStrategyService:
    versions: dict[str, StrategyVersion]
    create_calls: list[dict[str, Any]] = field(default_factory=list)

    async def get_version(self, session: Any, version_id: str) -> StrategyVersion | None:
        return self.versions.get(version_id)

    async def create_candidate_version(
        self,
        session: Any,
        trader_id: str,
        strategy_date: date,
        parent_version_id: str,
        adjustments: list[StrategyAdjustment],
        recommendations: list[StrategyRecommendation],
        notes: str | None = None,
    ) -> StrategyVersion:
        self.create_calls.append(
            {
                'trader_id': trader_id,
                'strategy_date': strategy_date,
                'parent_version_id': parent_version_id,
                'adjustments': adjustments,
                'recommendations': recommendations,
                'notes': notes,
            },
        )
        candidate = StrategyVersion(
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
        self.versions[candidate.version_id] = candidate
        return candidate


@dataclass
class _FakeRulePoolService:
    review_calls: list[tuple[str, str, bool, str]] = field(default_factory=list)
    review_batch_calls: list[tuple[str, str, int, bool, str]] = field(default_factory=list)

    async def review_rule(self, rule_id: str, *, decision: str, force: bool = False, reviewed_by: str = 'cli_user') -> ServiceResult:
        self.review_calls.append((rule_id, decision, force, reviewed_by))
        return ServiceResult(
            status='ok',
            message='rule reviewed',
            payload={
                'rule_id': rule_id,
                'review_status': decision,
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
        reviewed_by: str = 'cli_user',
    ) -> ServiceResult:
        self.review_batch_calls.append((decision, status, limit, force, reviewed_by))
        return ServiceResult(
            status='ok',
            message='rule batch reviewed',
            payload={
                'decision': decision,
                'filter_status': status,
                'updated_count': limit,
                'target_status': decision,
                'reviewed_by': reviewed_by,
            },
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
            parent_version_id=None,
            notes='released notes',
            rules_snapshot=[{'rule_id': 'r-1'}],
        ),
        _build_version_row(
            version_id='trader_a_2026-05-09_candidate_parent123',
            trader_id='trader_a',
            strategy_date=date(2026, 5, 9),
            status='draft',
            version_type='candidate',
            parent_version_id='parent123',
            notes='candidate notes',
            rules_snapshot=[],
        ),
    ]
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
    fake_session = _FakeSession(version_rows, rule_rows)
    fake_optimize_service = _FakeOptimizeService()
    fake_strategy_service = _FakeStrategyService(
        versions={row.version_name: StrategyVersion(
            version_id=row.version_name,
            trader_id=row.trader_id,
            strategy_date=row.strategy_date,
            status=StrategyVersionStatus(row.status),
            version_type=StrategyVersionType(row.version_type),
            parent_version_id=row.parent_version_id,
            recommendations=[],
            source_article_ids=[],
            evidence_refs=[],
            notes=row.notes,
            released_at=row.released_at,
            rules_snapshot=[],
        ) for row in version_rows},
    )
    fake_rule_pool_service = _FakeRulePoolService()

    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: 'test-key'
        app.dependency_overrides[get_session_scope_factory] = lambda: (lambda: _FakeSessionScope(fake_session))
        app.dependency_overrides[get_optimize_service] = lambda: fake_optimize_service
        app.dependency_overrides[get_strategy_library_service] = lambda: fake_strategy_service
        app.dependency_overrides[get_rule_pool_service] = lambda: fake_rule_pool_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url='http://test') as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_strategy_studio_endpoints_cover_versions_rules_and_candidate_creation(client: AsyncClient) -> None:
    """Strategy Studio BFF 应覆盖版本、优化和规则池链路。"""
    versions = await client.get(
        '/api/ui/v1/strategy-studio/versions',
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
    versions_body = versions.json()
    assert versions_body['count'] == 1
    assert versions_body['items'][0]['version_id'] == 'trader_a_2026-05-09_released'
    assert versions_body['items'][0]['has_rules_snapshot'] is True

    detail = await client.get('/api/ui/v1/strategy-studio/versions/trader_a_2026-05-09_released')
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body['item']['parent_version_id'] is None
    assert detail_body['item']['recommendations'][0]['symbol'] == '000001.SZ'
    assert detail_body['item']['rules_snapshot'][0]['rule_id'] == 'r-1'

    advise = await client.post(
        '/api/ui/v1/strategy-studio/optimize/advise-rule-validations',
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
        '/api/ui/v1/strategy-studio/optimize/filter-active-traders',
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
    assert filtered.json()['results'][0]['rule_count'] == 1

    candidate = await client.post(
        '/api/ui/v1/strategy-studio/optimize/create-candidate',
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
    candidate_body = candidate.json()
    assert candidate_body['item']['version_id'].startswith('trader_a_2026-05-09_candidate_')
    assert candidate_body['item']['notes'] == 'keep the original recommendation and review later'

    rules = await client.get(
        '/api/ui/v1/strategy-studio/rule-pool',
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
    rules_body = rules.json()
    assert rules_body['count'] == 1
    assert rules_body['items'][0]['rule_id'] == 'rule-1'
    assert rules_body['items'][0]['mapped'] is False

    rule_detail = await client.get('/api/ui/v1/strategy-studio/rule-pool/rule-2')
    assert rule_detail.status_code == 200
    assert rule_detail.json()['item']['mapped'] is True
    assert rule_detail.json()['item']['extraction_layer']['mapped_condition']['price'] == 'above_ma20'

    review = await client.post(
        '/api/ui/v1/strategy-studio/rule-pool/rule-1/review',
        json={'decision': 'approve', 'force': False, 'reviewed_by': 'web'},
    )
    assert review.status_code == 200
    assert review.json()['review_status'] == 'approve'

    batch = await client.post(
        '/api/ui/v1/strategy-studio/rule-pool/review-batch',
        json={'decision': 'reject', 'status': 'pending', 'limit': 25, 'force': True, 'reviewed_by': 'web'},
    )
    assert batch.status_code == 200
    assert batch.json()['filter_status'] == 'pending'

    canonical_versions = await client.get(
        '/api/ui/v1/optimize/versions',
        params={'trader_id': 'trader_a', 'status': 'released', 'version_type': 'manual', 'skip': 0, 'limit': 10},
    )
    assert canonical_versions.status_code == 200
    assert canonical_versions.json()['count'] == 1

    canonical_rule_review = await client.post(
        '/api/ui/v1/rule-pool/rule-1/review',
        json={'decision': 'approve', 'force': False, 'reviewed_by': 'web'},
    )
    assert canonical_rule_review.status_code == 200
    assert canonical_rule_review.json()['review_status'] == 'approve'
