from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.domain.enums import TradingDayPlanState
from src.services.post_close_actuals_service import PostCloseActualsRepository


class _FakePlanRepository:
    def __init__(self, *, plan: object, signals: list[object]) -> None:
        self._plan = plan
        self._signals = signals

    async def get_plan_for_id(self, session: object, *, trading_day_plan_id: object) -> object | None:
        del session, trading_day_plan_id
        return self._plan

    async def list_signals_for_plan(self, session: object, *, trading_day_plan_id: object) -> list[object]:
        del session, trading_day_plan_id
        return list(self._signals)


class _FakeSession:
    def __init__(self, *, snapshot: object) -> None:
        self._snapshot = snapshot

    async def get(self, model: object, object_id: object) -> object | None:
        del model
        if object_id == self._snapshot.id:
            return self._snapshot
        return None


@pytest.mark.asyncio()
async def test_post_close_actuals_marks_late_snapshot_as_unavailable() -> None:
    plan_id = uuid4()
    snapshot_id = uuid4()
    plan = SimpleNamespace(
        trading_day_plan_id=plan_id,
        trade_date=date(2026, 6, 21),
        lifecycle_state=TradingDayPlanState.approved,
    )
    signals = [
        SimpleNamespace(signal_id=uuid4(), symbol="000001.SZ"),
        SimpleNamespace(signal_id=uuid4(), symbol="000002.SZ"),
    ]
    snapshot = SimpleNamespace(
        id=snapshot_id,
        snapshot_id="market-snapshot-2026-06-21-pm",
        trade_date=date(2026, 6, 21),
        available_at=datetime(2026, 6, 21, 10, 5, tzinfo=UTC),
        frozen_at=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        content_fingerprint="market-fingerprint-late",
    )
    repository = PostCloseActualsRepository(
        plan_repository=_FakePlanRepository(plan=plan, signals=signals),
    )

    result = await repository.get_actuals_for_signals(
        _FakeSession(snapshot=snapshot),
        trading_day_plan_id=plan_id,
        post_close_market_snapshot_id=snapshot_id,
    )

    assert result.coverage_state == "unavailable"
    assert result.reasons == ["post_close_snapshot_available_late"]
    assert result.market_snapshot_available_at == snapshot.available_at
    assert all(item.state == "unavailable" for item in result.signals)
    assert all(item.reasons == ["post_close_snapshot_available_late"] for item in result.signals)
