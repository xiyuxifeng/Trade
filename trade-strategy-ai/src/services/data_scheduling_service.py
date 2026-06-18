from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from src.backtest.engine import is_trade_date, iter_trade_dates

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

    _TRUTHFUL_STATUS_PRIORITY = (
        "conflict",
        "invalid",
        "insufficient_coverage",
        "unavailable",
    )
    FORMAL_JOB_TYPE = "system-data-operation"
    DEFAULT_BENCHMARK_SYMBOL = "000300.SH"

    def __init__(
        self,
        *,
        session_factory: Callable[[], Any] | None = None,
        job_service: Any | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._job_service = job_service

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

    async def build_schedule_summary(self) -> dict[str, Any]:
        schedule = self.build_schedule()
        return {
            "timezone": schedule.timezone,
            "entries": [
                {
                    "key": entry.key,
                    "label": entry.label,
                    "window_start": entry.window_start,
                    "window_end": entry.window_end,
                    "dependency_order": list(entry.dependency_order),
                }
                for entry in schedule.entries
            ],
        }

    async def get_readiness(
        self,
        *,
        profile_id: str | None = None,
        now_shanghai: datetime | None = None,
    ) -> dict[str, Any]:
        facts = await self._collect_facts()
        operations = await self._list_operation_records(limit=20, offset=0)
        readiness = self.evaluate_readiness(
            facts=facts,
            now_shanghai=now_shanghai or datetime.now(SHANGHAI),
            operations=operations,
        )
        return {
            "profile_id": profile_id,
            "market": facts.market,
            "timezone": facts.timezone,
            "status": readiness.status,
            "summary": readiness.summary,
            "phase": readiness.phase,
            "target_trade_date": readiness.target_trade_date.isoformat(),
            "latest_update_at": readiness.latest_update_at.isoformat() if readiness.latest_update_at else None,
            "latest_successful_update_at": readiness.latest_update_at.isoformat() if readiness.latest_update_at else None,
            "repair_available": bool(readiness.repair_plan.steps),
            "repair_plan": {
                "status": readiness.repair_plan.status,
                "steps": [
                    {
                        "action": step.action,
                        "label": step.label,
                        "reason": step.reason,
                        "target_trade_date": step.target_trade_date.isoformat(),
                    }
                    for step in readiness.repair_plan.steps
                ],
            },
            "facts": {
                "latest_ohlcv_trade_date": facts.latest_ohlcv_trade_date.isoformat() if facts.latest_ohlcv_trade_date else None,
                "latest_indicator_trade_date": facts.latest_indicator_trade_date.isoformat() if facts.latest_indicator_trade_date else None,
                "dataset_snapshot_status": facts.latest_dataset_snapshot.status,
                "pre_market_snapshot_status": facts.latest_pre_market_snapshot.status,
                "post_close_snapshot_status": facts.latest_post_close_snapshot.status,
                "market_state_status": facts.latest_market_state_snapshot.status,
                "missing_coverages": list(facts.missing_coverages),
                "unavailable_reasons": list(facts.unavailable_reasons),
            },
        }

    async def list_operations(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        job_service = self._get_job_service()
        result = await job_service.list_jobs(job_type=self.FORMAL_JOB_TYPE, skip=offset, limit=limit)
        items = result.payload.get("items", []) if result.status == "ok" and isinstance(result.payload, dict) else []
        return {
            "count": len(items),
            "items": [self._job_to_operation(item) for item in items],
        }

    async def submit_operation(
        self,
        *,
        action: str,
        principal: Any,
        profile_id: str | None = None,
        target_trade_date: str | date | None = None,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        schedule_key: str | None = None,
        trigger_source: str = "manual",
        audit_source: dict[str, Any] | None = None,
        now_shanghai: datetime | None = None,
    ) -> Any:
        resolved_target_trade_date = self._coerce_optional_date(target_trade_date)
        resolved_start_date = self._coerce_optional_date(start_date)
        resolved_end_date = self._coerce_optional_date(end_date)
        now = now_shanghai or datetime.now(SHANGHAI)
        facts = await self._collect_facts()
        operations = await self._list_operation_records(limit=20, offset=0)
        readiness = self.evaluate_readiness(facts=facts, now_shanghai=now, operations=operations)
        planned_steps = self._plan_formal_operation(
            action=action,
            readiness=readiness,
            now_shanghai=now,
            target_trade_date=resolved_target_trade_date,
            schedule_key=schedule_key,
        )
        effective_target_date = resolved_target_trade_date or readiness.target_trade_date
        if action == "repair" and not planned_steps:
            from src.services.base import ServiceResult

            return ServiceResult(
                status="partial",
                message="no repair needed",
                payload={
                    "created": False,
                    "operation": {
                        "operation_id": None,
                        "label": "当前无需补齐数据",
                        "action": action,
                        "status": "ready",
                    },
                },
            )

        idempotency_key = self.build_operation_key(
            action=action,
            target_trade_date=effective_target_date,
            steps=planned_steps,
            trigger_source=trigger_source,
            start_date=resolved_start_date,
            end_date=resolved_end_date,
            schedule_key=schedule_key,
        )
        job_service = self._get_job_service()
        created_by = f"system-data:{getattr(principal, 'api_key_label', None) or getattr(principal, 'role', 'operator')}"
        result = await job_service.create_job(
            job_type=self.FORMAL_JOB_TYPE,
            params={
                "action": action,
                "profile_id": profile_id,
                "target_trade_date": effective_target_date.isoformat() if effective_target_date else None,
                "start_date": resolved_start_date.isoformat() if resolved_start_date else None,
                "end_date": resolved_end_date.isoformat() if resolved_end_date else None,
                "schedule_key": schedule_key,
                "trigger_source": trigger_source,
                "steps": [
                    {
                        "action": step.action,
                        "label": step.label,
                        "reason": step.reason,
                        "target_trade_date": step.target_trade_date.isoformat(),
                    }
                    for step in planned_steps
                ],
            },
            created_by=created_by,
            idempotency_key=idempotency_key,
            audit_source=audit_source,
        )
        if result.status != "ok":
            return result
        return self._wrap_job_result_as_operation(result)

    async def cancel_operation(self, *, operation_id: str, reason: str | None = None, audit_source: dict[str, Any] | None = None) -> Any:
        return await self._get_job_service().cancel_job(job_id=operation_id, reason=reason, audit_source=audit_source)

    async def retry_operation(self, *, operation_id: str, actor: str, audit_source: dict[str, Any] | None = None) -> Any:
        return await self._get_job_service().retry_job(job_id=operation_id, actor=actor, audit_source=audit_source)

    async def resume_operation(self, *, operation_id: str, actor: str, audit_source: dict[str, Any] | None = None) -> Any:
        return await self._get_job_service().resume_job(job_id=operation_id, actor=actor, audit_source=audit_source)

    async def execute_operation(
        self,
        *,
        params: dict[str, Any],
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> Any:
        from src.services.base import ServiceResult

        action = str(params.get("action") or "").strip()
        now = datetime.now(SHANGHAI)
        facts = await self._collect_facts()
        readiness = self.evaluate_readiness(facts=facts, now_shanghai=now, operations=[])
        target_trade_date = self._coerce_optional_date(params.get("target_trade_date")) or readiness.target_trade_date
        planned_steps = self._plan_formal_operation(
            action=action,
            readiness=readiness,
            now_shanghai=now,
            target_trade_date=target_trade_date,
            schedule_key=params.get("schedule_key"),
        )
        if action == "backfill":
            step_payload = await self._execute_backfill(
                profile_id=str(params.get("profile_id") or "").strip() or None,
                start_date=self._coerce_optional_date(params.get("start_date")),
                end_date=self._coerce_optional_date(params.get("end_date")),
                progress_callback=progress_callback,
            )
            return ServiceResult(status="ok", message="system data operation completed", payload=step_payload)

        if not planned_steps:
            return ServiceResult(
                status="ok",
                message="system data operation completed",
                payload={"action": action, "executed_steps": [], "status": "ready"},
            )

        executed_steps: list[dict[str, Any]] = []
        overall_status = "ok"
        step_context: dict[str, Any] = {}
        total = len(planned_steps)
        for index, step in enumerate(planned_steps, start=1):
            if progress_callback is not None:
                progress_callback(
                    {
                        "job_type": self.FORMAL_JOB_TYPE,
                        "stage": "system-data",
                        "current": index,
                        "total": total,
                        "percent": round((index / total) * 100, 2),
                        "current_step": step.action,
                        "current_trade_date": step.target_trade_date.isoformat(),
                        "status": "running",
                    }
                )
            step_result = await self._execute_step(
                action=step.action,
                profile_id=str(params.get("profile_id") or "").strip() or None,
                target_trade_date=step.target_trade_date,
                step_context=step_context,
            )
            executed_steps.append(step_result)
            if step_result.get("status") not in {"ok", "ready"}:
                overall_status = "partial" if step_result.get("status") == "partial" else "error"
                break
        return ServiceResult(
            status=overall_status,
            message="system data operation completed" if overall_status == "ok" else "system data operation completed with partial coverage",
            payload={
                "action": action,
                "executed_steps": executed_steps,
                "status": "ready" if overall_status == "ok" else "partial",
            },
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
        latest_operation = max(operations, key=lambda item: item.updated_at, default=None)
        truthful_fact_status = self._truthful_fact_status(facts)

        if running_operation is not None:
            status = "running"
            summary = f"{running_operation.label}正在执行，系统暂未就绪。"
        elif truthful_fact_status is not None:
            status = truthful_fact_status
            summary = self._summary_for_truthful_status(truthful_fact_status, phase=phase)
        elif latest_operation is not None and latest_operation.status in {"cancelled", "failed"} and (repair_steps or facts.missing_coverages):
            status = latest_operation.status
            summary = self._summary_for_operation_status(latest_operation.status)
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

    def build_operation_key(
        self,
        *,
        action: str,
        target_trade_date: date | None,
        steps: list[DataSchedulingRepairStep],
        trigger_source: str,
        start_date: date | None = None,
        end_date: date | None = None,
        schedule_key: str | None = None,
    ) -> str:
        del trigger_source
        payload = {
            "action": action,
            "target_trade_date": target_trade_date.isoformat() if target_trade_date else None,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "schedule_key": schedule_key,
            "steps": [
                {
                    "action": step.action,
                    "target_trade_date": step.target_trade_date.isoformat(),
                }
                for step in steps
            ],
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        return f"system-data-operation:{digest}"

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

    def _truthful_fact_status(self, facts: DataSchedulingFacts) -> str | None:
        statuses = (
            facts.latest_dataset_snapshot.status,
            facts.latest_pre_market_snapshot.status,
            facts.latest_post_close_snapshot.status,
            facts.latest_market_state_snapshot.status,
        )
        for status in self._TRUTHFUL_STATUS_PRIORITY:
            if status in statuses:
                return status
        return None

    def _summary_for_truthful_status(self, status: str, *, phase: str) -> str:
        if status == "conflict":
            return "正式数据存在冲突，当前不能判定为已就绪。"
        if status == "invalid":
            return "正式数据存在无效状态，当前不能判定为已就绪。"
        if status == "insufficient_coverage":
            return "正式数据覆盖不足，当前不能判定为已就绪。"
        if status == "unavailable":
            return "部分正式数据当前不可用，系统无法宣告已就绪。"
        return self._summary_for_phase(phase)

    def _summary_for_operation_status(self, status: str) -> str:
        if status == "cancelled":
            return "最近一次数据操作已取消，当前仍未达到正式就绪条件。"
        if status == "failed":
            return "最近一次数据操作失败，当前仍未达到正式就绪条件。"
        return "当前数据操作状态需要进一步处理。"

    def _get_session_factory(self) -> Callable[[], Any]:
        if self._session_factory is not None:
            return self._session_factory
        from src.db.session import session_scope

        self._session_factory = session_scope
        return self._session_factory

    def _get_job_service(self) -> Any:
        if self._job_service is not None:
            return self._job_service
        from src.services.job_service import JobService

        self._job_service = JobService()
        return self._job_service

    def _coerce_optional_date(self, value: str | date | None) -> date | None:
        if value in {None, ""}:
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    async def _collect_facts(self) -> DataSchedulingFacts:
        from src.models.indicator import Indicator
        from src.models.market_data_snapshot import MarketSnapshot as MarketSnapshotRecord
        from src.models.market_regime_record import MarketRegimeRecord
        from src.models.ohlcv_bar import OHLCVBar
        from src.models.stage2_canonical import DatasetSnapshot

        session_factory = self._get_session_factory()
        async with session_factory() as session:
            latest_ohlcv = await session.scalar(
                select(OHLCVBar).order_by(OHLCVBar.trade_date.desc(), OHLCVBar.available_at.desc()).limit(1)
            )
            latest_indicator = await session.scalar(
                select(Indicator).order_by(Indicator.trade_date.desc(), Indicator.computed_at.desc()).limit(1)
            )
            latest_dataset = await session.scalar(
                select(DatasetSnapshot).order_by(DatasetSnapshot.trade_date.desc(), DatasetSnapshot.created_at.desc()).limit(1)
            )
            latest_pre_market = await session.scalar(
                select(MarketSnapshotRecord)
                .where(MarketSnapshotRecord.slot == "09-25")
                .order_by(MarketSnapshotRecord.trade_date.desc(), MarketSnapshotRecord.created_at.desc())
                .limit(1)
            )
            latest_post_close = await session.scalar(
                select(MarketSnapshotRecord)
                .where(MarketSnapshotRecord.slot == "17-30")
                .order_by(MarketSnapshotRecord.trade_date.desc(), MarketSnapshotRecord.created_at.desc())
                .limit(1)
            )
            latest_market_state = await session.scalar(
                select(MarketRegimeRecord).order_by(MarketRegimeRecord.trade_date.desc(), MarketRegimeRecord.updated_at.desc()).limit(1)
            )

        return DataSchedulingFacts(
            market="CN",
            timezone="Asia/Shanghai",
            latest_ohlcv_trade_date=getattr(latest_ohlcv, "trade_date", None),
            latest_ohlcv_available_at=getattr(latest_ohlcv, "available_at", None),
            latest_indicator_trade_date=getattr(latest_indicator, "trade_date", None),
            latest_indicator_available_at=getattr(latest_indicator, "computed_at", None),
            latest_dataset_snapshot=self._dataset_snapshot_fact(latest_dataset),
            latest_pre_market_snapshot=self._market_snapshot_fact(latest_pre_market),
            latest_post_close_snapshot=self._market_snapshot_fact(latest_post_close),
            latest_market_state_snapshot=self._market_state_fact(latest_market_state),
            missing_coverages=[],
            unavailable_reasons=[],
        )

    def _dataset_snapshot_fact(self, snapshot: Any | None) -> DataSchedulingSnapshotFact:
        if snapshot is None:
            return DataSchedulingSnapshotFact(trade_date=None, status="missing", available_at=None, detail="dataset snapshot missing")
        status = getattr(getattr(snapshot, "lifecycle_state", None), "value", getattr(snapshot, "lifecycle_state", "missing"))
        return DataSchedulingSnapshotFact(
            trade_date=getattr(snapshot, "trade_date", None),
            status=str(status or "missing"),
            available_at=getattr(snapshot, "available_at", None),
            detail=str(getattr(snapshot, "dataset_type", None) or "dataset snapshot"),
        )

    def _market_snapshot_fact(self, snapshot: Any | None) -> DataSchedulingSnapshotFact:
        if snapshot is None:
            return DataSchedulingSnapshotFact(trade_date=None, status="missing", available_at=None, detail="market snapshot missing")
        raw_status = str(getattr(snapshot, "quality_status", "missing") or "missing")
        status = "ready" if raw_status == "ok" else raw_status
        return DataSchedulingSnapshotFact(
            trade_date=getattr(snapshot, "trade_date", None),
            status=status,
            available_at=getattr(snapshot, "available_at", None),
            detail=str(getattr(snapshot, "slot", None) or "market snapshot"),
        )

    def _market_state_fact(self, state: Any | None) -> DataSchedulingSnapshotFact:
        if state is None:
            return DataSchedulingSnapshotFact(trade_date=None, status="missing", available_at=None, detail="market state missing")
        raw_status = str(getattr(state, "quality_status", "missing") or "missing")
        status = "ready" if raw_status == "ok" else raw_status
        return DataSchedulingSnapshotFact(
            trade_date=getattr(state, "trade_date", None),
            status=status,
            available_at=getattr(state, "available_at", None),
            detail=str(getattr(state, "regime_version", None) or "market state"),
        )

    async def _list_operation_records(self, *, limit: int, offset: int) -> list[DataSchedulingOperationRecord]:
        result = await self._get_job_service().list_jobs(job_type=self.FORMAL_JOB_TYPE, skip=offset, limit=limit)
        items = result.payload.get("items", []) if result.status == "ok" and isinstance(result.payload, dict) else []
        records: list[DataSchedulingOperationRecord] = []
        for item in items:
            params = item.get("params") if isinstance(item.get("params"), dict) else {}
            records.append(
                DataSchedulingOperationRecord(
                    operation_id=str(item.get("id")),
                    action=str(params.get("action") or ""),
                    label=self._label_for_operation(params),
                    status=str(item.get("status") or "pending"),
                    operation_date=self._coerce_optional_date(params.get("target_trade_date")),
                    scheduled_kind=str(params.get("trigger_source") or "manual"),
                    created_at=datetime.fromisoformat(item["created_at"]) if item.get("created_at") else datetime.now(),
                    updated_at=datetime.fromisoformat(item["updated_at"]) if item.get("updated_at") else datetime.now(),
                    detail=None,
                )
            )
        return records

    def _label_for_operation(self, params: dict[str, Any]) -> str:
        action = str(params.get("action") or "")
        labels = {
            "repair": "补齐缺失数据",
            "update_now": "立即更新数据",
            "backfill": "回灌历史数据",
            "recompute_indicators": "重算指标",
            "recompute_market_state": "重算市场状态",
            "run_schedule_window": "执行定时窗口",
        }
        return labels.get(action, "数据与调度操作")

    def _job_to_operation(self, item: dict[str, Any]) -> dict[str, Any]:
        params = item.get("params") if isinstance(item.get("params"), dict) else {}
        return {
            "operation_id": str(item.get("id")),
            "label": self._label_for_operation(params),
            "action": params.get("action"),
            "status": item.get("status"),
            "target_trade_date": params.get("target_trade_date"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "cancel_requested": bool(item.get("cancel_requested")),
        }

    def _wrap_job_result_as_operation(self, result: Any) -> Any:
        payload = result.payload if isinstance(result.payload, dict) else {}
        job = payload.get("job") if isinstance(payload.get("job"), dict) else {}
        from src.services.base import ServiceResult

        return ServiceResult(
            status=result.status,
            message=result.message,
            payload={
                "created": bool(payload.get("created", True)),
                "operation": self._job_to_operation(job),
            },
        )

    def _plan_formal_operation(
        self,
        *,
        action: str,
        readiness: DataSchedulingReadiness,
        now_shanghai: datetime,
        target_trade_date: date | None,
        schedule_key: str | None,
    ) -> list[DataSchedulingRepairStep]:
        effective_date = target_trade_date or readiness.target_trade_date
        if action == "repair":
            return list(readiness.repair_plan.steps)
        if action == "recompute_indicators":
            return [DataSchedulingRepairStep(action="recompute_indicators", label="重算指标", reason="操作员手动触发重算。", target_trade_date=effective_date)]
        if action == "recompute_market_state":
            return [DataSchedulingRepairStep(action="recompute_market_state", label="重算市场状态", reason="操作员手动触发重算。", target_trade_date=effective_date)]
        if action == "run_schedule_window":
            return self._schedule_steps_for_window(schedule_key=schedule_key, target_trade_date=effective_date)
        if action == "update_now":
            schedule_key = self._schedule_key_for_phase(self._phase_for(now_shanghai))
            return self._schedule_steps_for_window(schedule_key=schedule_key, target_trade_date=effective_date)
        return []

    def _schedule_key_for_phase(self, phase: str) -> str:
        if phase in {"before_pre_market", "pre_market", "trading"}:
            return "pre_market_kaipan"
        if phase == "close_processing":
            return "close_data_refresh"
        return "post_close_kaipan"

    def _schedule_steps_for_window(self, *, schedule_key: str | None, target_trade_date: date) -> list[DataSchedulingRepairStep]:
        if schedule_key == "pre_market_kaipan":
            return [
                DataSchedulingRepairStep(action="refresh_pre_market_kaipan", label="补齐盘前市场数据", reason="执行盘前数据窗口。", target_trade_date=target_trade_date),
                DataSchedulingRepairStep(action="recompute_market_state", label="重算市场状态", reason="盘前数据刷新后重算市场状态。", target_trade_date=target_trade_date),
            ]
        if schedule_key == "close_data_refresh":
            return [
                DataSchedulingRepairStep(action="refresh_ohlcv_close", label="更新收盘后行情", reason="执行收盘后行情窗口。", target_trade_date=target_trade_date),
                DataSchedulingRepairStep(action="recompute_indicators", label="重算指标", reason="收盘后行情更新后重算指标。", target_trade_date=target_trade_date),
                DataSchedulingRepairStep(action="recompute_market_state", label="重算市场状态", reason="在上游准备完成后重算市场状态。", target_trade_date=target_trade_date),
            ]
        if schedule_key == "post_close_kaipan":
            return [
                DataSchedulingRepairStep(action="refresh_post_close_kaipan", label="补齐盘后市场数据", reason="执行盘后数据窗口。", target_trade_date=target_trade_date),
                DataSchedulingRepairStep(action="recompute_market_state", label="重算市场状态", reason="盘后数据刷新后重算市场状态。", target_trade_date=target_trade_date),
            ]
        if schedule_key == "overnight_repair":
            return [DataSchedulingRepairStep(action="repair", label="夜间健康修复", reason="执行夜间健康检查与修复。", target_trade_date=target_trade_date)]
        return []

    async def _execute_backfill(
        self,
        *,
        profile_id: str | None,
        start_date: date | None,
        end_date: date | None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        effective_start = start_date or date.today()
        effective_end = end_date or effective_start
        market_service = self._get_market_service()
        result = await market_service.crawl_ohlcv(
            profile_id=profile_id,
            mode="full",
            symbols=await self._load_symbols(),
            start_date=effective_start,
            end_date=effective_end,
            progress_callback=progress_callback,
        )
        indicators = await self._recompute_indicators_for_range(start_date=effective_start, end_date=effective_end)
        return {
            "action": "backfill",
            "ohlcv": result.payload if isinstance(result.payload, dict) else {},
            "indicators": indicators,
        }

    async def _execute_step(
        self,
        *,
        action: str,
        profile_id: str | None,
        target_trade_date: date,
        step_context: dict[str, Any],
    ) -> dict[str, Any]:
        if action == "refresh_ohlcv_close":
            market_service = self._get_market_service()
            result = await market_service.crawl_ohlcv(
                profile_id=profile_id,
                mode="incremental",
                symbols=await self._load_symbols(),
                start_date=target_trade_date,
                end_date=target_trade_date,
            )
            return {"action": action, "status": result.status, "payload": result.payload}
        if action == "recompute_indicators":
            indicators = await self._recompute_indicators_for_range(start_date=target_trade_date, end_date=target_trade_date)
            return {"action": action, "status": "ok", "payload": indicators}
        if action in {"refresh_pre_market_kaipan", "refresh_post_close_kaipan"}:
            slot = "09-25" if action == "refresh_pre_market_kaipan" else "17-30"
            result = await self._refresh_kaipan_slot(profile_id=profile_id, target_trade_date=target_trade_date, slot=slot)
            snapshot_id = None
            if isinstance(result.get("payload"), dict):
                snapshot_id = result["payload"].get("snapshot_id")
            if snapshot_id:
                step_context["snapshot_id"] = snapshot_id
            return {"action": action, "status": result.get("status", "partial"), "payload": result.get("payload")}
        if action == "recompute_market_state":
            result = await self._recompute_market_state(profile_id=profile_id, target_trade_date=target_trade_date, snapshot_id=step_context.get("snapshot_id"))
            return {"action": action, "status": result.status, "payload": result.payload}
        if action == "repair":
            return {"action": action, "status": "partial", "payload": {"message": "repair should expand into concrete steps before execution"}}
        return {"action": action, "status": "partial", "payload": {"message": "unsupported action"}}

    async def _load_symbols(self) -> list[str]:
        from src.models.stock_info import StockInfo

        session_factory = self._get_session_factory()
        async with session_factory() as session:
            result = await session.scalars(
                select(StockInfo.symbol)
                .where(StockInfo.security_type.in_(["stock", "index", "etf"]))
                .order_by(StockInfo.symbol.asc())
            )
            return list(result.all())

    def _get_market_service(self) -> Any:
        from src.services.market_service import MarketService

        return MarketService()

    async def _recompute_indicators_for_range(self, *, start_date: date, end_date: date) -> dict[str, Any]:
        from src.indicators.indicator_service import IndicatorService
        from src.db.session import get_session_factory

        symbols = await self._load_symbols()
        indicator_service = IndicatorService(session_factory=get_session_factory())
        computed_dates: list[str] = []
        for trade_date in iter_trade_dates(start_date, end_date):
            await indicator_service.get_for_date(symbols, trade_date)
            computed_dates.append(trade_date.isoformat())
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "computed_trade_dates": computed_dates,
            "symbol_count": len(symbols),
        }

    async def _refresh_kaipan_slot(self, *, profile_id: str | None, target_trade_date: date, slot: str) -> dict[str, Any]:
        from src.services.config_profile_service import ConfigProfileService
        from src.services.kaipan_service import KaipanService
        from src.services.market_snapshot_service import MarketSnapshotService

        runtime_profile_id = profile_id or ConfigProfileService().resolve_runtime_profile_id()
        config_path = await ConfigProfileService().resolve_profile_config_path(runtime_profile_id)
        kaipan_service = KaipanService()
        fetch_result = await asyncio.to_thread(kaipan_service.fetch, profile_id=runtime_profile_id, trade_date=target_trade_date, slot=slot)
        if fetch_result.status not in {"ok", "partial"}:
            return {"status": fetch_result.status, "payload": fetch_result.payload}
        normalize_result = await asyncio.to_thread(kaipan_service.normalize, profile_id=runtime_profile_id, trade_date=target_trade_date, slot=slot)
        if normalize_result.status not in {"ok", "partial"}:
            return {"status": normalize_result.status, "payload": normalize_result.payload}
        snapshot_service = MarketSnapshotService()
        snapshot_result = await snapshot_service.build_market_snapshot(
            config_path=config_path or Path("config/app.yaml"),
            benchmark_symbol=self.DEFAULT_BENCHMARK_SYMBOL,
            trade_date=target_trade_date.isoformat(),
            slot=slot,
            profile_id=runtime_profile_id,
        )
        return {"status": snapshot_result.status, "payload": snapshot_result.payload}

    async def _recompute_market_state(self, *, profile_id: str | None, target_trade_date: date, snapshot_id: str | None) -> Any:
        from src.models.market_data_snapshot import MarketSnapshot as MarketSnapshotRecord
        from src.services.base import ServiceResult
        from src.services.market_regime_service import MarketRegimeService

        del profile_id
        resolved_snapshot_id = snapshot_id
        if resolved_snapshot_id is None:
            session_factory = self._get_session_factory()
            async with session_factory() as session:
                result = await session.scalars(
                    select(MarketSnapshotRecord)
                    .where(MarketSnapshotRecord.trade_date == target_trade_date)
                    .order_by(MarketSnapshotRecord.created_at.desc())
                )
                snapshots = list(result.all())
            ready_snapshots = [item for item in snapshots if str(getattr(item, "quality_status", "missing")) == "ok"]
            slot_preference = {"17-30": 0, "09-25": 1}
            ready_snapshots.sort(
                key=lambda item: (
                    slot_preference.get(str(getattr(item, "slot", "")), 9),
                    -int(getattr(item, "created_at").timestamp()) if getattr(item, "created_at", None) is not None else 0,
                )
            )
            snapshot = ready_snapshots[0] if ready_snapshots else None
            if snapshot is None:
                available_slots = [str(getattr(item, "slot", "")) for item in snapshots]
                return ServiceResult(
                    status="partial",
                    message="market snapshot missing",
                    payload={
                        "trade_date": target_trade_date.isoformat(),
                        "slots": available_slots,
                    },
                )
            if str(getattr(snapshot, "quality_status", "missing")) != "ok":
                return ServiceResult(
                    status="partial",
                    message="market snapshot not ready",
                    payload={
                        "trade_date": target_trade_date.isoformat(),
                        "slot": getattr(snapshot, "slot", None),
                        "quality_status": getattr(snapshot, "quality_status", "missing"),
                    },
                )
            resolved_snapshot_id = snapshot.snapshot_id
        regime_service = MarketRegimeService()
        return await regime_service.build_market_regime(snapshot_id=resolved_snapshot_id)
