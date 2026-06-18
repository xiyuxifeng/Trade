from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from src.services.data_scheduling_service import (
    DataSchedulingService,
    DataSchedulingFacts,
    DataSchedulingOperationRecord,
    DataSchedulingRepairStep,
    DataSchedulingSnapshotFact,
)


def _dt(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _snapshot(
    *,
    trade_date: date | None,
    status: str,
    available_at: datetime | None,
) -> DataSchedulingSnapshotFact:
    return DataSchedulingSnapshotFact(
        trade_date=trade_date,
        status=status,
        available_at=available_at,
        detail="fixture",
    )


def _facts() -> DataSchedulingFacts:
    return DataSchedulingFacts(
        market="CN",
        timezone="Asia/Shanghai",
        latest_ohlcv_trade_date=date(2026, 6, 17),
        latest_ohlcv_available_at=_dt(2026, 6, 17, 9, 5),
        latest_indicator_trade_date=date(2026, 6, 17),
        latest_indicator_available_at=_dt(2026, 6, 17, 9, 12),
        latest_dataset_snapshot=_snapshot(
            trade_date=date(2026, 6, 17),
            status="ready",
            available_at=_dt(2026, 6, 17, 9, 8),
        ),
        latest_pre_market_snapshot=_snapshot(
            trade_date=date(2026, 6, 17),
            status="ready",
            available_at=_dt(2026, 6, 17, 1, 25),
        ),
        latest_post_close_snapshot=_snapshot(
            trade_date=date(2026, 6, 16),
            status="ready",
            available_at=_dt(2026, 6, 16, 9, 30),
        ),
        latest_market_state_snapshot=_snapshot(
            trade_date=date(2026, 6, 17),
            status="ready",
            available_at=_dt(2026, 6, 17, 1, 30),
        ),
        missing_coverages=[],
        unavailable_reasons=[],
    )


@pytest.mark.asyncio
async def test_readiness_uses_canonical_data_facts_not_job_success() -> None:
    service = DataSchedulingService()
    facts = replace(
        _facts(),
        latest_pre_market_snapshot=_snapshot(trade_date=date(2026, 6, 17), status="missing", available_at=None),
    )
    operations = [
        DataSchedulingOperationRecord(
            operation_id="op-1",
            action="update_now",
            label="立即更新",
            status="success",
            operation_date=date(2026, 6, 17),
            scheduled_kind="manual",
            created_at=_dt(2026, 6, 17, 1, 26),
            updated_at=_dt(2026, 6, 17, 1, 27),
        )
    ]

    readiness = service.evaluate_readiness(
        facts=facts,
        now_shanghai=datetime(2026, 6, 17, 9, 28),
        operations=operations,
    )

    assert readiness.status == "partial"
    assert readiness.repair_plan.status == "needs_repair"
    assert "盘前" in readiness.summary


@pytest.mark.asyncio
async def test_pre_market_readiness_never_consumes_same_day_post_close_data() -> None:
    service = DataSchedulingService()
    facts = replace(
        _facts(),
        latest_pre_market_snapshot=_snapshot(trade_date=date(2026, 6, 16), status="missing", available_at=None),
        latest_post_close_snapshot=_snapshot(
            trade_date=date(2026, 6, 17),
            status="ready",
            available_at=_dt(2026, 6, 17, 9, 30),
        ),
    )

    readiness = service.evaluate_readiness(
        facts=facts,
        now_shanghai=datetime(2026, 6, 17, 9, 24),
        operations=[],
    )

    assert readiness.status == "partial"
    assert readiness.repair_plan.steps[0].action == "refresh_pre_market_kaipan"
    assert all(step.action != "refresh_post_close_kaipan" for step in readiness.repair_plan.steps)


@pytest.mark.asyncio
async def test_repair_plan_selects_smallest_required_work() -> None:
    service = DataSchedulingService()
    facts = replace(
        _facts(),
        latest_market_state_snapshot=_snapshot(trade_date=date(2026, 6, 16), status="missing", available_at=None),
    )

    readiness = service.evaluate_readiness(
        facts=facts,
        now_shanghai=datetime(2026, 6, 17, 9, 40),
        operations=[],
    )

    assert [step.action for step in readiness.repair_plan.steps] == ["recompute_market_state"]


def test_schedule_uses_asia_shanghai_boundaries() -> None:
    service = DataSchedulingService()

    schedule = service.build_schedule()

    assert schedule.timezone == "Asia/Shanghai"
    assert [entry.window_start for entry in schedule.entries] == ["09:20", "17:00", "17:30", "22:00"]
    assert schedule.entries[0].window_end == "09:25"


def test_invalid_canonical_state_never_reports_ready() -> None:
    service = DataSchedulingService()
    facts = replace(
        _facts(),
        latest_dataset_snapshot=_snapshot(
            trade_date=date(2026, 6, 17),
            status="invalid",
            available_at=_dt(2026, 6, 17, 9, 8),
        ),
    )

    readiness = service.evaluate_readiness(
        facts=facts,
        now_shanghai=datetime(2026, 6, 17, 18, 10),
        operations=[],
    )

    assert readiness.status == "invalid"
    assert readiness.repair_plan.status == "needs_repair"


def test_conflict_state_remains_conflict() -> None:
    service = DataSchedulingService()
    facts = replace(
        _facts(),
        latest_post_close_snapshot=_snapshot(
            trade_date=date(2026, 6, 17),
            status="conflict",
            available_at=_dt(2026, 6, 17, 9, 30),
        ),
    )

    readiness = service.evaluate_readiness(
        facts=facts,
        now_shanghai=datetime(2026, 6, 17, 18, 10),
        operations=[],
    )

    assert readiness.status == "conflict"


def test_cancelled_operation_state_is_truthful_when_data_is_still_missing() -> None:
    service = DataSchedulingService()
    facts = replace(
        _facts(),
        latest_pre_market_snapshot=_snapshot(
            trade_date=date(2026, 6, 16),
            status="missing",
            available_at=None,
        ),
    )
    operations = [
        DataSchedulingOperationRecord(
            operation_id="op-cancelled",
            action="repair",
            label="补齐盘前市场数据",
            status="cancelled",
            operation_date=date(2026, 6, 17),
            scheduled_kind="manual",
            created_at=_dt(2026, 6, 17, 1, 23),
            updated_at=_dt(2026, 6, 17, 1, 24),
        )
    ]

    readiness = service.evaluate_readiness(
        facts=facts,
        now_shanghai=datetime(2026, 6, 17, 9, 24),
        operations=operations,
    )

    assert readiness.status == "cancelled"
    assert readiness.repair_plan.status == "needs_repair"


def test_operation_identity_deduplicates_manual_and_scheduled_same_scope() -> None:
    service = DataSchedulingService()
    steps = [
        DataSchedulingRepairStep(
            action="refresh_pre_market_kaipan",
            label="补齐盘前市场数据",
            reason="今天盘前可用数据仍未准备完成。",
            target_trade_date=date(2026, 6, 17),
        )
    ]

    manual_key = service.build_operation_key(
        action="repair",
        target_trade_date=date(2026, 6, 17),
        steps=steps,
        trigger_source="manual",
    )
    scheduled_key = service.build_operation_key(
        action="repair",
        target_trade_date=date(2026, 6, 17),
        steps=steps,
        trigger_source="scheduled",
    )

    assert manual_key == scheduled_key
