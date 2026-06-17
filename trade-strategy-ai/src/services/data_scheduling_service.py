from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from src.backtest.engine import is_trade_date

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _latest_trade_date_for(value: date) -> date:
    current = value
    while not is_trade_date(current):
        current -= timedelta(days=1)
    return current


@dataclass(frozen=True)
class DataSchedulingSnapshotFact:
    trade_date: date | None
    status: str
    available_at: datetime | None
    detail: str | None = None


@dataclass(frozen=True)
class DataSchedulingFacts:
    market: str
    timezone: str
    latest_ohlcv_trade_date: date | None
    latest_ohlcv_available_at: datetime | None
    latest_indicator_trade_date: date | None
    latest_indicator_available_at: datetime | None
    latest_dataset_snapshot: DataSchedulingSnapshotFact
    latest_pre_market_snapshot: DataSchedulingSnapshotFact
    latest_post_close_snapshot: DataSchedulingSnapshotFact
    latest_market_state_snapshot: DataSchedulingSnapshotFact
    missing_coverages: list[str] = field(default_factory=list)
    unavailable_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DataSchedulingOperationRecord:
    operation_id: str
    action: str
    label: str
    status: str
    operation_date: date | None
    scheduled_kind: str
    created_at: datetime
    updated_at: datetime
    detail: str | None = None


@dataclass(frozen=True)
class DataSchedulingRepairStep:
    action: str
    label: str
    reason: str
    target_trade_date: date


@dataclass(frozen=True)
class DataSchedulingRepairPlan:
    status: str
    steps: list[DataSchedulingRepairStep]


@dataclass(frozen=True)
class DataSchedulingReadiness:
    status: str
    summary: str
    target_trade_date: date
    phase: str
    latest_update_at: datetime | None
    repair_plan: DataSchedulingRepairPlan


@dataclass(frozen=True)
class DataSchedulingScheduleEntry:
    key: str
    label: str
    window_start: str
    window_end: str
    dependency_order: list[str]


@dataclass(frozen=True)
class DataSchedulingSchedule:
    timezone: str
    entries: list[DataSchedulingScheduleEntry]


class DataSchedulingService:
    """Thin orchestration contract for Stage 5 data readiness and scheduling."""

    def build_schedule(self) -> DataSchedulingSchedule:
        return DataSchedulingSchedule(
            timezone="Asia/Shanghai",
            entries=[
                DataSchedulingScheduleEntry(
                    key="pre_market_kaipan",
                    label="盘前 Kaipan 更新",
                    window_start="09:20",
                    window_end="09:25",
                    dependency_order=["refresh_pre_market_kaipan", "recompute_market_state"],
                ),
                DataSchedulingScheduleEntry(
                    key="close_data_refresh",
                    label="收盘后行情更新",
                    window_start="17:00",
                    window_end="17:00",
                    dependency_order=["refresh_ohlcv_close", "recompute_indicators", "recompute_market_state"],
                ),
                DataSchedulingScheduleEntry(
                    key="post_close_kaipan",
                    label="盘后 Kaipan 更新",
                    window_start="17:30",
                    window_end="17:30",
                    dependency_order=["refresh_post_close_kaipan", "recompute_market_state"],
                ),
                DataSchedulingScheduleEntry(
                    key="overnight_repair",
                    label="夜间健康检查与修复",
                    window_start="22:00",
                    window_end="23:59",
                    dependency_order=["health_check_and_repair"],
                ),
            ],
        )

    def evaluate_readiness(
        self,
        *,
        facts: DataSchedulingFacts,
        now_shanghai: datetime,
        operations: list[DataSchedulingOperationRecord],
    ) -> DataSchedulingReadiness:
        if now_shanghai.tzinfo is None:
            now_shanghai = now_shanghai.replace(tzinfo=SHANGHAI)
        else:
            now_shanghai = now_shanghai.astimezone(SHANGHAI)

        target_trade_date = _latest_trade_date_for(now_shanghai.date())
        phase = self._phase_for(now_shanghai)
        repair_steps = self._build_repair_steps(facts=facts, phase=phase, target_trade_date=target_trade_date)
        running_operation = next((item for item in operations if item.status in {"pending", "running"}), None)

        if running_operation is not None:
            status = "running"
            summary = f"{running_operation.label}正在执行，系统暂未就绪。"
        elif facts.unavailable_reasons:
            status = "unavailable"
            summary = "部分正式数据当前不可用，系统无法宣告已就绪。"
        elif repair_steps or facts.missing_coverages:
            status = "partial"
            summary = self._summary_for_phase(phase)
        else:
            status = "ready"
            summary = "所需正式数据已按当前时段就绪。"

        latest_candidates = [
            item
            for item in (
                facts.latest_ohlcv_available_at,
                facts.latest_indicator_available_at,
                facts.latest_dataset_snapshot.available_at,
                facts.latest_pre_market_snapshot.available_at,
                facts.latest_post_close_snapshot.available_at,
                facts.latest_market_state_snapshot.available_at,
            )
            if item is not None
        ]
        latest_update_at = max(latest_candidates) if latest_candidates else None

        return DataSchedulingReadiness(
            status=status,
            summary=summary,
            target_trade_date=target_trade_date,
            phase=phase,
            latest_update_at=latest_update_at,
            repair_plan=DataSchedulingRepairPlan(
                status="needs_repair" if repair_steps else "not_needed",
                steps=repair_steps,
            ),
        )

    def _phase_for(self, now_shanghai: datetime) -> str:
        current = now_shanghai.hour * 60 + now_shanghai.minute
        if current < 9 * 60 + 20:
            return "before_pre_market"
        if current <= 9 * 60 + 25:
            return "pre_market"
        if current < 17 * 60:
            return "trading"
        if current < 17 * 60 + 30:
            return "close_processing"
        return "post_close"

    def _build_repair_steps(
        self,
        *,
        facts: DataSchedulingFacts,
        phase: str,
        target_trade_date: date,
    ) -> list[DataSchedulingRepairStep]:
        steps: list[DataSchedulingRepairStep] = []
        if phase in {"before_pre_market", "pre_market", "trading"}:
            if facts.latest_pre_market_snapshot.trade_date != target_trade_date or facts.latest_pre_market_snapshot.status != "ready":
                steps.append(
                    DataSchedulingRepairStep(
                        action="refresh_pre_market_kaipan",
                        label="补齐盘前市场数据",
                        reason="今天盘前可用数据仍未准备完成。",
                        target_trade_date=target_trade_date,
                    )
                )
            if (
                facts.latest_pre_market_snapshot.trade_date == target_trade_date
                and facts.latest_pre_market_snapshot.status == "ready"
                and (facts.latest_market_state_snapshot.trade_date != target_trade_date or facts.latest_market_state_snapshot.status != "ready")
            ):
                steps.append(
                    DataSchedulingRepairStep(
                        action="recompute_market_state",
                        label="重算市场状态",
                        reason="盘前快照已就绪，但市场状态结果缺失或非 ready。",
                        target_trade_date=target_trade_date,
                    )
                )
            return steps

        if facts.latest_ohlcv_trade_date != target_trade_date:
            steps.append(
                DataSchedulingRepairStep(
                    action="refresh_ohlcv_close",
                    label="更新收盘后行情",
                    reason="今日收盘后 OHLCV 尚未完成正式更新。",
                    target_trade_date=target_trade_date,
                )
            )
        if facts.latest_indicator_trade_date != target_trade_date:
            steps.append(
                DataSchedulingRepairStep(
                    action="recompute_indicators",
                    label="重算指标",
                    reason="今日指标尚未与最新 OHLCV 对齐。",
                    target_trade_date=target_trade_date,
                )
            )
        if facts.latest_post_close_snapshot.trade_date != target_trade_date or facts.latest_post_close_snapshot.status != "ready":
            steps.append(
                DataSchedulingRepairStep(
                    action="refresh_post_close_kaipan",
                    label="补齐盘后市场数据",
                    reason="今日盘后 Kaipan 快照缺失或非 ready。",
                    target_trade_date=target_trade_date,
                )
            )
        if (
            not steps
            and (facts.latest_market_state_snapshot.trade_date != target_trade_date or facts.latest_market_state_snapshot.status != "ready")
        ):
            steps.append(
                DataSchedulingRepairStep(
                    action="recompute_market_state",
                    label="重算市场状态",
                    reason="上游数据已就绪，但市场状态结果缺失或非 ready。",
                    target_trade_date=target_trade_date,
                )
            )
        return steps

    def _summary_for_phase(self, phase: str) -> str:
        if phase in {"before_pre_market", "pre_market", "trading"}:
            return "盘前数据尚未完整到位，当前只能判定为部分就绪。"
        return "收盘后数据链路尚未全部完成，当前只能判定为部分就绪。"
