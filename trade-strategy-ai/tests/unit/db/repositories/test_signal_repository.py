from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.strategy.types import PriceSpec, Signal as StrategySignal, SignalSide, SynthesisMode


class _FakeScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)


class _FakeSession:
    def __init__(self, items, count: int):
        self.items = items
        self.count = count
        self.scalars_calls = []
        self.scalar_calls = []
        self.added = []
        self.flush_calls = 0

    async def scalars(self, stmt):
        self.scalars_calls.append(stmt)
        return _FakeScalarResult(self.items)

    async def scalar(self, stmt):
        self.scalar_calls.append(stmt)
        return self.count

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flush_calls += 1


@pytest.mark.asyncio()
async def test_signal_repository_lists_signals() -> None:
    """SignalRepository 应支持按标的和时间过滤的查询。"""
    from src.db.repositories import SignalRepository
    from src.models.signal import Signal

    signal = Signal(
        signal_id="11111111-1111-1111-1111-111111111111",
        symbol="000001.SZ",
        side="BUY",
        confidence=0.91,
        triggered_rules=["rule_a"],
        synthesis_mode="priority",
        version="v1",
        trader_id="trader_a",
        strategy_version_id="sv-1",
        signal_metadata={
            "trader_id": "trader_a",
            "summary": "trend up",
            "context": {"trend": "up", "score": 0.91},
        },
        created_at=datetime(2026, 4, 23, 9, 30, tzinfo=UTC),
    )
    fake_session = _FakeSession([signal], 1)
    repo = SignalRepository()

    signals = await repo.list_signals(
        fake_session,
        symbol="000001.SZ",
        since=datetime(2026, 4, 22, tzinfo=UTC),
        limit=20,
    )
    count = await repo.count_signals(
        fake_session,
        symbol="000001.SZ",
        since=datetime(2026, 4, 22, tzinfo=UTC),
    )

    assert count == 1
    assert len(signals) == 1
    assert signals[0].symbol == "000001.SZ"
    assert signals[0].trader_id == "trader_a"
    assert fake_session.scalars_calls
    assert fake_session.scalar_calls


@pytest.mark.asyncio()
async def test_signal_repository_upserts_signal_and_reads_by_id() -> None:
    """SignalRepository 应支持写入。"""
    from src.db.repositories import SignalRepository

    repo = SignalRepository()
    fake_session = _FakeSession([], 0)
    signal = StrategySignal(
        signal_id="11111111-1111-1111-1111-111111111111",
        symbol="000001.SZ",
        side=SignalSide.BUY,
        confidence=0.91,
        timestamp=datetime(2026, 4, 23, 9, 30, tzinfo=UTC),
        triggered_rules=["rule_a"],
        synthesis_mode=SynthesisMode.PRIORITY,
        entry_price=PriceSpec(type="limit", value=10.2),
        metadata={"trader_id": "trader_a"},
    )

    saved = await repo.upsert_signal(fake_session, signal, context={"trend": "up"})

    assert fake_session.added
    assert fake_session.flush_calls == 1
    assert saved.signal_id == UUID("11111111-1111-1111-1111-111111111111")
    assert saved.signal_metadata["context"]["trend"] == "up"
