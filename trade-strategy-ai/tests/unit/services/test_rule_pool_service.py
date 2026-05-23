from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.services.rule_pool_service import RulePoolService


class _FakeScalarResult:
    def __init__(self, items: list[str]) -> None:
        self._items = items

    def scalars(self) -> _FakeScalarResult:
        return self

    def all(self) -> list[str]:
        return list(self._items)


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def execute(self, stmt):  # noqa: ANN001
        text = str(stmt)
        self.calls.append(text)
        if 'review_status' in text:
            return _FakeScalarResult(['approved', 'pending', 'rejected', 'pending'])
        if 'mapping_status' in text:
            return _FakeScalarResult(['mapped', 'unmapped', 'mapped'])
        if 'source_type' in text:
            return _FakeScalarResult(['standalone', 'derived', 'experience', 'derived'])
        if 'rule_type' in text:
            return _FakeScalarResult(['breakout', 'pullback', 'breakout'])
        if 'instrument_focus' in text:
            return _FakeScalarResult(['mixed', 'stock', 'mixed'])
        return _FakeScalarResult([])


@dataclass
class _FakeSessionScope:
    session: _FakeSession

    async def __aenter__(self) -> _FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False


@pytest.mark.asyncio
async def test_list_filter_options_uses_full_data_sources() -> None:
    session = _FakeSession()
    service = RulePoolService(session_scope_factory=lambda: _FakeSessionScope(session))

    result = await service.list_filter_options()

    assert result.status == 'ok'
    assert result.payload['review_statuses'] == ['pending', 'approved', 'rejected']
    assert result.payload['mapping_statuses'] == ['unmapped', 'pending', 'mapped', 'unmappable']
    assert result.payload['source_types'] == ['standalone', 'derived', 'experience']
    assert result.payload['rule_types'] == ['breakout', 'pullback']
    assert result.payload['instrument_focuses'] == ['mixed', 'stock']
