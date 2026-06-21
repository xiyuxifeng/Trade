from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
import json
from typing import Any, Callable, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from src.common.stage2_writer_routing import canonical_write_scope
from src.db.repositories.daily_trading_plan_repo import DailyTradingPlanRepository
from src.db.session import get_session_factory
from src.domain.enums import DailyStrategyInstanceState, SignalState, TradingDayPlanState
from src.models.signal import Signal
from src.models.stage2_canonical import DailyStrategyInstance, TradingDayPlan
from src.services.daily_rule_selection_service import DailyRuleDecisionView, DailyRuleSelectionService


class TradingPlanFieldView(BaseModel):
    state: Literal["ready", "degraded", "unavailable"]
    summary: str
    details: list[str] = Field(default_factory=list)


class TradingPlanRuleDecisionView(DailyRuleDecisionView):
    rule_title: str | None = None


class TradingPlanCandidateView(BaseModel):
    symbol: str
    name: str | None = None
    rank: int | None = None
    score: float | None = None
    note: str | None = None
    state: Literal["ready", "degraded", "unavailable"] = "ready"


class TradingPlanSignalView(BaseModel):
    signal_id: str | None = None
    symbol: str
    name: str | None = None
    side: Literal["BUY", "SELL", "HOLD"]
    confidence: float | None = None
    confidence_label: str
    state: Literal["ready", "degraded", "unavailable"]
    entry_condition: str
    invalidation_condition: str
    stop_loss_take_profit: str
    suggested_position: str
    triggered_rule_version_ids: list[str] = Field(default_factory=list)
    degraded_inputs: list[str] = Field(default_factory=list)
    unresolved_inputs: list[str] = Field(default_factory=list)


class TradingDayPlanTraceabilityView(BaseModel):
    trade_date: str
    strategy_version_id: str
    daily_rule_selection_id: str
    dataset_snapshot_id: str
    market_snapshot_id: str
    market_state_id: str
    current_market_state_label: str | None = None
    rule_applicability_profile_ids: list[str] = Field(default_factory=list)
    author_method_profile_version_id: str | None = None
    author_rule_profile_version_id: str | None = None
    author_validated_profile_version_id: str | None = None
    data_quality_state: str
    readiness_status: str
    selected_rules: list[TradingPlanRuleDecisionView] = Field(default_factory=list)
    reduced_rules: list[TradingPlanRuleDecisionView] = Field(default_factory=list)
    suspended_rules: list[TradingPlanRuleDecisionView] = Field(default_factory=list)
    degraded_inputs: list[str] = Field(default_factory=list)
    unresolved_inputs: list[str] = Field(default_factory=list)


class TradingDayPlanReviewRequest(BaseModel):
    action: Literal["approve", "reject"]
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def _validate_reason(cls, value: str | None, info):
        action = info.data.get("action")
        if action == "reject" and not (value or "").strip():
            raise ValueError("驳回每日运行计划时必须填写原因。")
        return value.strip() if isinstance(value, str) else value


class TradingDayPlanView(BaseModel):
    state: Literal["ready", "partial", "unavailable"]
    plan_status: Literal["ready", "degraded", "blocked"]
    generated: bool
    trade_date: str
    happened: str
    affected: str
    repair_guidance: str
    daily_strategy_instance_id: str | None = None
    trading_day_plan_id: str | None = None
    daily_rule_selection_id: str | None = None
    revision_no: int | None = None
    strategy_version_id: str | None = None
    instance_lifecycle_state: str | None = None
    plan_lifecycle_state: str | None = None
    approval_state: Literal["pending", "approved", "rejected"]
    approved_by: str | None = None
    approved_at: str | None = None
    rejection_reason: str | None = None
    market_judgment: TradingPlanFieldView
    enabled_rules: list[TradingPlanRuleDecisionView] = Field(default_factory=list)
    reduced_rules: list[TradingPlanRuleDecisionView] = Field(default_factory=list)
    suspended_rules: list[TradingPlanRuleDecisionView] = Field(default_factory=list)
    candidate_symbols: list[TradingPlanCandidateView] = Field(default_factory=list)
    candidate_symbols_state: TradingPlanFieldView
    signals: list[TradingPlanSignalView] = Field(default_factory=list)
    entry_conditions: TradingPlanFieldView
    invalidation_conditions: TradingPlanFieldView
    stop_loss_take_profit: TradingPlanFieldView
    suggested_position: TradingPlanFieldView
    risk_warnings: TradingPlanFieldView
    confidence: TradingPlanFieldView
    traceability: TradingDayPlanTraceabilityView | None = None


class DailyTradingPlanService:
    service_name = "daily_trading_plan"

    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any] | None = None,
        repository: DailyTradingPlanRepository | None = None,
        daily_rule_selection_service: DailyRuleSelectionService | None = None,
    ) -> None:
        self._session_scope_factory = session_scope_factory or self._default_session_scope_factory
        self.repository = repository or DailyTradingPlanRepository()
        self.daily_rule_selection_service = daily_rule_selection_service or DailyRuleSelectionService(
            session_scope_factory=self._session_scope_factory
        )

    @staticmethod
    @asynccontextmanager
    async def _default_session_scope_factory():
        session_factory = get_session_factory()
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_trading_day_plan(
        self,
        trade_date: str | date,
        *,
        actor_id: str,
        actor_role: str,
    ) -> TradingDayPlanView:
        if actor_role not in {"viewer", "operator", "admin"}:
            raise PermissionError("viewer permission is required to view trading day plan")

        normalized_trade_date = trade_date if isinstance(trade_date, date) else date.fromisoformat(str(trade_date))
        selection = await self.daily_rule_selection_service.get_rule_selection(
            normalized_trade_date.isoformat(),
            actor_id=actor_id,
            actor_role=actor_role,
        )
        if not selection.generated or not selection.daily_rule_selection_id or selection.selection_status == "blocked":
            return self._blocked_view(normalized_trade_date, selection)

        async with self._session_scope_factory() as session:
            selection_record = await self.repository.get_daily_rule_selection(session, UUID(selection.daily_rule_selection_id))
            if selection_record is None:
                raise LookupError("daily rule selection record is missing")
            latest_instance = await self.repository.get_latest_instance(
                session,
                strategy_version_id=UUID(selection.strategy_version_id),
                trade_date=normalized_trade_date,
            )
            input_signature = self._input_signature(selection)
            if latest_instance is not None and self._payload_signature(latest_instance.payload) == input_signature:
                latest_plan = await self.repository.get_plan_for_instance(
                    session,
                    daily_strategy_instance_id=latest_instance.daily_strategy_instance_id,
                )
                if latest_plan is not None:
                    signals = await self.repository.list_signals_for_plan(
                        session,
                        trading_day_plan_id=latest_plan.trading_day_plan_id,
                    )
                    return self._build_view_from_records(latest_instance, latest_plan, signals)

            strategy_version = await self.repository.get_strategy_version(session, UUID(selection.strategy_version_id))
            if strategy_version is None:
                raise LookupError("strategy version is missing for trading day plan")
            market_snapshot = await self.repository.get_market_snapshot(session, UUID(selection.traceability.market_snapshot_id))
            if market_snapshot is None:
                raise LookupError("market snapshot is missing for trading day plan")
            market_state = await self.repository.get_market_state(session, UUID(selection.traceability.market_state_id))
            if market_state is None:
                raise LookupError("market state is missing for trading day plan")
            sections = await self.repository.list_market_snapshot_sections(session, snapshot_id=market_snapshot.snapshot_id)
            section_by_id = {item.section_id: item for item in sections}
            rule_ids = [
                UUID(item.rule_version_id)
                for item in [*selection.enabled_rules, *selection.reduced_rules, *selection.suspended_rules]
            ]
            rule_versions = {
                str(item.rule_version_id): item
                for item in await self.repository.list_rule_versions(session, rule_version_ids=rule_ids)
            }

            payload = self._build_payload(
                selection=selection,
                strategy_version=strategy_version,
                market_snapshot=market_snapshot,
                market_state=market_state,
                section_by_id=section_by_id,
                rule_versions=rule_versions,
                input_signature=input_signature,
            )
            revision_no = await self.repository.next_instance_revision_no(
                session,
                strategy_version_id=strategy_version.strategy_version_id,
                trade_date=normalized_trade_date,
            )
            instance = DailyStrategyInstance(
                daily_strategy_instance_id=uuid4(),
                strategy_version_id=strategy_version.strategy_version_id,
                daily_rule_selection_id=selection_record.daily_rule_selection_id,
                market_snapshot_id=market_snapshot.id,
                trade_date=normalized_trade_date,
                revision_no=revision_no,
                risk_multiplier=self._as_decimal(payload["runtime_summary"].get("risk_multiplier")),
                position_limit=self._as_decimal(payload["runtime_summary"].get("position_limit")),
                candidate_pool_snapshot_id=None,
                payload=payload,
                lifecycle_state=DailyStrategyInstanceState.generated,
                created_by=actor_id,
                updated_by=actor_id,
            )
            plan = TradingDayPlan(
                trading_day_plan_id=uuid4(),
                daily_strategy_instance_id=instance.daily_strategy_instance_id,
                trade_date=normalized_trade_date,
                revision_no=1,
                lifecycle_state=TradingDayPlanState.in_review,
                payload=payload,
                approved_by=None,
                approved_at=None,
                rejection_reason=None,
                source_run_id=None,
                created_by=actor_id,
                updated_by=actor_id,
            )
            signal_rows = self._build_signal_rows(
                payload=payload,
                strategy_version_id=strategy_version.strategy_version_id,
                trading_day_plan_id=plan.trading_day_plan_id,
                daily_strategy_instance_id=instance.daily_strategy_instance_id,
            )

            with canonical_write_scope("daily_strategy_instance", self.service_name):
                persisted_instance = await self.repository.create_instance(session, instance=instance)
            with canonical_write_scope("trading_day_plan", self.service_name):
                persisted_plan = await self.repository.create_plan(session, plan=plan)
            with canonical_write_scope("signal", self.service_name):
                persisted_signals = await self.repository.replace_signals_for_plan(
                    session,
                    trading_day_plan_id=persisted_plan.trading_day_plan_id,
                    daily_strategy_instance_id=persisted_instance.daily_strategy_instance_id,
                    signals=signal_rows,
                )
            return self._build_view_from_records(persisted_instance, persisted_plan, persisted_signals)

    async def review_trading_day_plan(
        self,
        trade_date: str | date,
        *,
        actor_id: str,
        actor_role: str,
        request: TradingDayPlanReviewRequest,
    ) -> TradingDayPlanView:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to review trading day plan")
        result = await self.get_trading_day_plan(trade_date, actor_id=actor_id, actor_role=actor_role)
        if not result.generated or not result.daily_strategy_instance_id or not result.trading_day_plan_id:
            return result

        async with self._session_scope_factory() as session:
            instance = await session.get(DailyStrategyInstance, UUID(result.daily_strategy_instance_id))
            plan = await session.get(TradingDayPlan, UUID(result.trading_day_plan_id))
            if instance is None or plan is None:
                raise LookupError("trading day plan is missing")
            signals = await self.repository.list_signals_for_plan(session, trading_day_plan_id=plan.trading_day_plan_id)
            now = datetime.now(UTC)
            if request.action == "approve":
                instance.lifecycle_state = DailyStrategyInstanceState.approved
                plan.lifecycle_state = TradingDayPlanState.approved
                plan.approved_by = actor_id
                plan.approved_at = now
                plan.rejection_reason = None
                for item in signals:
                    item.signal_state = SignalState.approved
                    item.rejected = False
                    item.rejection_reason = None
                    item.updated_at = now.replace(tzinfo=None)
            else:
                instance.lifecycle_state = DailyStrategyInstanceState.cancelled
                plan.lifecycle_state = TradingDayPlanState.rejected
                plan.approved_by = None
                plan.approved_at = None
                plan.rejection_reason = request.reason
                for item in signals:
                    item.signal_state = SignalState.rejected
                    item.rejected = True
                    item.rejection_reason = request.reason
                    item.updated_at = now.replace(tzinfo=None)
            plan.updated_by = actor_id
            instance.updated_by = actor_id
            review_state = {"action": request.action, "reason": request.reason, "actor_id": actor_id}
            plan.payload = {**plan.payload, "review_state": review_state}
            instance.payload = {**instance.payload, "review_state": review_state}
            with canonical_write_scope("daily_strategy_instance", self.service_name):
                await self.repository.update_instance(session, instance=instance)
            with canonical_write_scope("trading_day_plan", self.service_name):
                await self.repository.update_plan(session, plan=plan)
            with canonical_write_scope("signal", self.service_name):
                await self.repository.update_signals(session, signals=signals)
            return self._build_view_from_records(instance, plan, signals)

    def _blocked_view(self, trade_date: date, selection: Any) -> TradingDayPlanView:
        return TradingDayPlanView(
            state="unavailable",
            plan_status="blocked",
            generated=False,
            trade_date=trade_date.isoformat(),
            happened="每日规则选择尚未就绪，当前不能生成每日运行计划。",
            affected="系统不会在缺少正式规则选择的情况下生成看似成功的盘前计划。",
            repair_guidance=selection.repair_guidance,
            approval_state="pending",
            market_judgment=TradingPlanFieldView(state="unavailable", summary="今日市场判断暂不可用。"),
            candidate_symbols_state=TradingPlanFieldView(state="unavailable", summary="候选标的暂不可用。"),
            entry_conditions=TradingPlanFieldView(state="unavailable", summary="入场条件暂不可用。"),
            invalidation_conditions=TradingPlanFieldView(state="unavailable", summary="失效条件暂不可用。"),
            stop_loss_take_profit=TradingPlanFieldView(state="unavailable", summary="止盈止损暂不可用。"),
            suggested_position=TradingPlanFieldView(state="unavailable", summary="建议仓位暂不可用。"),
            risk_warnings=TradingPlanFieldView(
                state="unavailable",
                summary="请先修复前置依赖。",
                details=[selection.happened, selection.affected],
            ),
            confidence=TradingPlanFieldView(state="unavailable", summary="置信度暂不可用。"),
            traceability=None,
        )

    def _build_payload(
        self,
        *,
        selection: Any,
        strategy_version: Any,
        market_snapshot: Any,
        market_state: Any,
        section_by_id: dict[str, Any],
        rule_versions: dict[str, Any],
        input_signature: str,
    ) -> dict[str, Any]:
        enabled_rules = [self._rule_decision_view(item, rule_versions) for item in selection.enabled_rules]
        reduced_rules = [self._rule_decision_view(item, rule_versions) for item in selection.reduced_rules]
        suspended_rules = [self._rule_decision_view(item, rule_versions) for item in selection.suspended_rules]
        candidate_symbols, candidate_field = self._candidate_views(section_by_id.get("strong_symbols"))
        selected_rule_count = len(enabled_rules)
        reduced_rule_count = len(reduced_rules)
        total_rule_count = max(1, selected_rule_count + reduced_rule_count + len(suspended_rules))
        confidence_value = self._compute_confidence(
            market_confidence=getattr(market_state, "confidence", None),
            selected_rule_count=selected_rule_count,
            reduced_rule_count=reduced_rule_count,
            total_rule_count=total_rule_count,
            degraded_inputs=selection.degraded_inputs,
        )
        market_judgment = TradingPlanFieldView(
            state="degraded" if selection.degraded_inputs else "ready",
            summary=f"{market_state.primary_label}（置信度 {self._confidence_label(confidence_value)}）",
            details=[
                f"市场状态 ID：{selection.traceability.market_state_id}",
                f"数据质量：{selection.traceability.data_quality_state}",
            ],
        )
        entry_conditions = self._field_from_rule_text(
            title="入场条件",
            rule_versions=rule_versions,
            rule_ids=[item.rule_version_id for item in [*enabled_rules, *reduced_rules]],
            extractor=self._entry_condition_text,
            fallback="当前缺少可解释的入场条件，请先补齐规则条件描述。",
        )
        invalidation_conditions = TradingPlanFieldView(
            state="degraded" if selection.degraded_inputs or selection.unresolved_inputs else "ready",
            summary="若市场状态、规则适用性或关键数据质量发生变化，本计划即时失效。",
            details=[
                "若正式市场状态与当前判断不再一致，则停止执行。",
                "若关键规则适用性变为 unavailable / invalid / conflict，则停止执行。",
                "若盘前数据缺口扩大或仍有未解决输入，则停止执行。",
            ],
        )
        stop_loss_take_profit = self._risk_policy_field(strategy_version)
        suggested_position = self._position_field(strategy_version, selection)
        risk_warnings = TradingPlanFieldView(
            state="degraded" if selection.degraded_inputs or selection.unresolved_inputs else "ready",
            summary="执行前请先确认今日盘前依赖状态。",
            details=self._risk_warning_details(selection, candidate_field),
        )
        confidence_field = TradingPlanFieldView(
            state="degraded" if selection.degraded_inputs else "ready",
            summary=self._confidence_label(confidence_value),
            details=[
                f"市场判断置信度：{getattr(market_state, 'confidence', 0):.2f}",
                f"启用规则 {selected_rule_count} 条，降权规则 {reduced_rule_count} 条，暂停规则 {len(suspended_rules)} 条。",
            ],
        )
        signal_views = self._signal_payloads(
            candidates=candidate_symbols,
            enabled_rules=enabled_rules,
            reduced_rules=reduced_rules,
            suggested_position=suggested_position.summary,
            stop_loss_take_profit=stop_loss_take_profit.summary,
            confidence_value=confidence_value,
            degraded_inputs=selection.degraded_inputs,
            unresolved_inputs=selection.unresolved_inputs,
            rule_versions=rule_versions,
        )
        traceability = TradingDayPlanTraceabilityView(
            trade_date=selection.traceability.trade_date,
            strategy_version_id=selection.traceability.strategy_version_id,
            daily_rule_selection_id=str(selection.daily_rule_selection_id),
            dataset_snapshot_id=selection.traceability.dataset_snapshot_id,
            market_snapshot_id=selection.traceability.market_snapshot_id,
            market_state_id=selection.traceability.market_state_id,
            current_market_state_label=getattr(market_state, "primary_label", None),
            rule_applicability_profile_ids=list(selection.traceability.rule_applicability_profile_ids),
            author_method_profile_version_id=selection.traceability.author_method_profile_version_id,
            author_rule_profile_version_id=selection.traceability.author_rule_profile_version_id,
            author_validated_profile_version_id=selection.traceability.author_validated_profile_version_id,
            data_quality_state=selection.traceability.data_quality_state,
            readiness_status=selection.readiness_status,
            selected_rules=enabled_rules,
            reduced_rules=reduced_rules,
            suspended_rules=suspended_rules,
            degraded_inputs=list(selection.degraded_inputs),
            unresolved_inputs=list(selection.unresolved_inputs),
        )
        return {
            "input_signature": input_signature,
            "approval_state": "pending",
            "market_judgment": market_judgment.model_dump(mode="json"),
            "enabled_rules": [item.model_dump(mode="json") for item in enabled_rules],
            "reduced_rules": [item.model_dump(mode="json") for item in reduced_rules],
            "suspended_rules": [item.model_dump(mode="json") for item in suspended_rules],
            "candidate_symbols_state": candidate_field.model_dump(mode="json"),
            "candidate_symbols": [item.model_dump(mode="json") for item in candidate_symbols],
            "signals": [item.model_dump(mode="json") for item in signal_views],
            "entry_conditions": entry_conditions.model_dump(mode="json"),
            "invalidation_conditions": invalidation_conditions.model_dump(mode="json"),
            "stop_loss_take_profit": stop_loss_take_profit.model_dump(mode="json"),
            "suggested_position": suggested_position.model_dump(mode="json"),
            "risk_warnings": risk_warnings.model_dump(mode="json"),
            "confidence": confidence_field.model_dump(mode="json"),
            "traceability": traceability.model_dump(mode="json"),
            "runtime_summary": {
                "risk_multiplier": round(max(0.2, confidence_value), 4),
                "position_limit": self._position_limit_value(strategy_version, selection),
            },
        }

    def _build_view_from_records(
        self,
        instance: DailyStrategyInstance,
        plan: TradingDayPlan,
        signals: list[Signal],
    ) -> TradingDayPlanView:
        payload = plan.payload or {}
        plan_lifecycle_state = plan.lifecycle_state.value if hasattr(plan.lifecycle_state, "value") else str(plan.lifecycle_state)
        approval_state: Literal["pending", "approved", "rejected"]
        if plan_lifecycle_state == TradingDayPlanState.approved.value:
            approval_state = "approved"
        elif plan_lifecycle_state == TradingDayPlanState.rejected.value:
            approval_state = "rejected"
        else:
            approval_state = "pending"
        traceability = TradingDayPlanTraceabilityView.model_validate(payload["traceability"])
        plan_status: Literal["ready", "degraded", "blocked"] = "degraded" if (
            traceability.degraded_inputs or traceability.reduced_rules or traceability.suspended_rules
        ) else "ready"
        return TradingDayPlanView(
            state="partial" if plan_status == "degraded" else "ready",
            plan_status=plan_status,
            generated=True,
            trade_date=plan.trade_date.isoformat(),
            happened="已根据已接受的每日规则选择生成每日运行计划。",
            affected="今日盘前执行对象、信号和风险提示已经固定，可在批准后执行。",
            repair_guidance="若需降低风险，请先补齐降级输入后重新生成计划。",
            daily_strategy_instance_id=str(instance.daily_strategy_instance_id),
            trading_day_plan_id=str(plan.trading_day_plan_id),
            daily_rule_selection_id=traceability.daily_rule_selection_id,
            revision_no=instance.revision_no,
            strategy_version_id=str(instance.strategy_version_id),
            instance_lifecycle_state=instance.lifecycle_state.value if hasattr(instance.lifecycle_state, "value") else str(instance.lifecycle_state),
            plan_lifecycle_state=plan_lifecycle_state,
            approval_state=approval_state,
            approved_by=plan.approved_by,
            approved_at=plan.approved_at.isoformat() if plan.approved_at else None,
            rejection_reason=plan.rejection_reason,
            market_judgment=TradingPlanFieldView.model_validate(payload["market_judgment"]),
            enabled_rules=[TradingPlanRuleDecisionView.model_validate(item) for item in payload.get("enabled_rules", [])],
            reduced_rules=[TradingPlanRuleDecisionView.model_validate(item) for item in payload.get("reduced_rules", [])],
            suspended_rules=[TradingPlanRuleDecisionView.model_validate(item) for item in payload.get("suspended_rules", [])],
            candidate_symbols=[TradingPlanCandidateView.model_validate(item) for item in payload.get("candidate_symbols", [])],
            candidate_symbols_state=TradingPlanFieldView.model_validate(payload["candidate_symbols_state"]),
            signals=self._signal_views_from_rows(signals, payload),
            entry_conditions=TradingPlanFieldView.model_validate(payload["entry_conditions"]),
            invalidation_conditions=TradingPlanFieldView.model_validate(payload["invalidation_conditions"]),
            stop_loss_take_profit=TradingPlanFieldView.model_validate(payload["stop_loss_take_profit"]),
            suggested_position=TradingPlanFieldView.model_validate(payload["suggested_position"]),
            risk_warnings=TradingPlanFieldView.model_validate(payload["risk_warnings"]),
            confidence=TradingPlanFieldView.model_validate(payload["confidence"]),
            traceability=traceability,
        )

    def _signal_views_from_rows(self, signals: list[Signal], payload: dict[str, Any]) -> list[TradingPlanSignalView]:
        signal_payloads = payload.get("signals", [])
        by_symbol = {item.symbol: item for item in signals}
        views: list[TradingPlanSignalView] = []
        for item in signal_payloads:
            row = by_symbol.get(item.get("symbol"))
            merged = {**item}
            if row is not None:
                merged["signal_id"] = str(row.signal_id)
                merged["side"] = row.side
                merged["state"] = "degraded" if row.degraded else item.get("state", "ready")
            views.append(TradingPlanSignalView.model_validate(merged))
        return views

    def _signal_payloads(
        self,
        *,
        candidates: list[TradingPlanCandidateView],
        enabled_rules: list[TradingPlanRuleDecisionView],
        reduced_rules: list[TradingPlanRuleDecisionView],
        suggested_position: str,
        stop_loss_take_profit: str,
        confidence_value: float,
        degraded_inputs: list[str],
        unresolved_inputs: list[str],
        rule_versions: dict[str, Any],
    ) -> list[TradingPlanSignalView]:
        actionable_rules = enabled_rules or reduced_rules
        if not candidates:
            return []
        side = self._signal_side(actionable_rules, rule_versions)
        signals: list[TradingPlanSignalView] = []
        for index, candidate in enumerate(candidates[:3], start=1):
            symbol_confidence = max(0.05, round(confidence_value - (index - 1) * 0.08, 2))
            entry_condition = f"候选标的 {candidate.symbol} 需满足已启用规则的盘前条件后再执行。"
            signals.append(
                TradingPlanSignalView(
                    symbol=candidate.symbol,
                    name=candidate.name,
                    side=side,
                    confidence=symbol_confidence,
                    confidence_label=self._confidence_label(symbol_confidence),
                    state="degraded" if degraded_inputs else "ready",
                    entry_condition=entry_condition,
                    invalidation_condition="若竞价/盘前状态偏离当前市场判断或关键规则失效，则该信号失效。",
                    stop_loss_take_profit=stop_loss_take_profit,
                    suggested_position=suggested_position,
                    triggered_rule_version_ids=[item.rule_version_id for item in actionable_rules],
                    degraded_inputs=list(degraded_inputs),
                    unresolved_inputs=list(unresolved_inputs),
                )
            )
        return signals

    def _build_signal_rows(
        self,
        *,
        payload: dict[str, Any],
        strategy_version_id: UUID,
        trading_day_plan_id: UUID,
        daily_strategy_instance_id: UUID,
    ) -> list[Signal]:
        now = datetime.now(UTC).replace(tzinfo=None)
        rows: list[Signal] = []
        for item in payload.get("signals", []):
            rows.append(
                Signal(
                    signal_id=uuid4(),
                    symbol=item["symbol"],
                    side=item["side"],
                    confidence=item.get("confidence"),
                    triggered_rules=item.get("triggered_rule_version_ids", []),
                    synthesis_mode="priority",
                    entry_price={"type": "market"},
                    position_size={"type": "fixed_ratio", "value": self._extract_position_ratio(item.get("suggested_position"))},
                    stop_loss={"summary": item.get("stop_loss_take_profit")},
                    take_profit={"summary": item.get("stop_loss_take_profit")},
                    strategy_version_id=strategy_version_id,
                    trading_day_plan_id=trading_day_plan_id,
                    daily_strategy_instance_id=daily_strategy_instance_id,
                    rule_version_ids=[str(value) for value in item.get("triggered_rule_version_ids", []) if self._is_uuid(value)],
                    signal_state=SignalState.proposed,
                    generated_at=now,
                    available_at=now,
                    expires_at=None,
                    source_topic_ids=[],
                    evidence_refs={"daily_rule_selection_id": payload["traceability"]["daily_rule_selection_id"]},
                    decision_mode="stage9_pre_market",
                    rejected=False,
                    degraded=item.get("state") == "degraded",
                    degradation_reason="；".join(item.get("degraded_inputs", [])) if item.get("degraded_inputs") else None,
                    version="v1",
                    signal_metadata={
                        "entry_condition": item.get("entry_condition"),
                        "invalidation_condition": item.get("invalidation_condition"),
                        "suggested_position": item.get("suggested_position"),
                    },
                    created_at=now,
                    updated_at=now,
                )
            )
        return rows

    def _field_from_rule_text(
        self,
        *,
        title: str,
        rule_versions: dict[str, Any],
        rule_ids: list[str],
        extractor: Callable[[Any], str | None],
        fallback: str,
    ) -> TradingPlanFieldView:
        details = [text for text in (extractor(rule_versions.get(rule_id)) for rule_id in rule_ids) if text]
        if details:
            return TradingPlanFieldView(state="ready", summary=f"已整理 {title}。", details=details[:6])
        return TradingPlanFieldView(state="unavailable", summary=fallback, details=[])

    def _entry_condition_text(self, rule_version: Any | None) -> str | None:
        if rule_version is None:
            return None
        condition_json = getattr(rule_version, "condition_json", {}) or {}
        title = getattr(rule_version, "title", None) or str(getattr(rule_version, "rule_version_id", ""))
        if isinstance(condition_json, dict) and condition_json:
            if "summary" in condition_json:
                return f"{title}：{condition_json['summary']}"
            if "indicator" in condition_json:
                return f"{title}：关注 {condition_json['indicator']} 条件成立。"
        return f"{title}：按正式规则条件触发后执行。"

    def _risk_policy_field(self, strategy_version: Any) -> TradingPlanFieldView:
        risk_policy = getattr(strategy_version, "risk_policy_json", {}) or {}
        stop_loss = self._first_value(risk_policy, "stop_loss", "stop_loss_pct", "stopLoss", "max_loss")
        take_profit = self._first_value(risk_policy, "take_profit", "take_profit_pct", "takeProfit", "target_profit")
        if stop_loss is None and take_profit is None:
            return TradingPlanFieldView(
                state="unavailable",
                summary="止盈止损暂不可用：当前正式策略未提供结构化止盈止损参数。",
                details=[],
            )
        details = []
        if stop_loss is not None:
            details.append(f"止损：{stop_loss}")
        if take_profit is not None:
            details.append(f"止盈：{take_profit}")
        return TradingPlanFieldView(state="ready", summary="已绑定正式策略风险控制参数。", details=details)

    def _position_field(self, strategy_version: Any, selection: Any) -> TradingPlanFieldView:
        value = self._position_limit_value(strategy_version, selection)
        if value is None:
            return TradingPlanFieldView(
                state="unavailable",
                summary="建议仓位暂不可用：当前正式策略没有结构化仓位上限。",
                details=[],
            )
        state = "degraded" if selection.degraded_inputs else "ready"
        return TradingPlanFieldView(
            state=state,
            summary=f"建议单日总仓位不超过 {round(float(value) * 100, 1)}%。",
            details=["若存在降级输入，请优先控制在该上限以下执行。"] if state == "degraded" else [],
        )

    def _risk_warning_details(self, selection: Any, candidate_field: TradingPlanFieldView) -> list[str]:
        details = []
        if selection.degraded_inputs:
            details.append(f"降级输入：{'、'.join(selection.degraded_inputs)}")
        if selection.unresolved_inputs:
            details.append(f"未解决输入：{'、'.join(selection.unresolved_inputs)}")
        if candidate_field.state != "ready":
            details.append(candidate_field.summary)
        if not details:
            details.append("当前未发现需要阻止执行的额外风险提示。")
        return details

    def _position_limit_value(self, strategy_version: Any, selection: Any) -> float | None:
        risk_policy = getattr(strategy_version, "risk_policy_json", {}) or {}
        raw_value = self._first_value(
            risk_policy,
            "position_limit",
            "max_position",
            "max_position_ratio",
            "suggested_position_ratio",
        )
        if raw_value is None:
            return None
        value = float(raw_value)
        if selection.degraded_inputs:
            value = min(value, value * 0.7)
        return max(0.0, min(1.0, value))

    def _candidate_views(self, section: Any | None) -> tuple[list[TradingPlanCandidateView], TradingPlanFieldView]:
        if section is None:
            return [], TradingPlanFieldView(state="unavailable", summary="候选标的暂不可用：缺少正式强势标的快照。")
        payload = getattr(section, "payload_json", {}) or {}
        symbols = payload.get("symbols")
        if not isinstance(symbols, list) or not symbols:
            return [], TradingPlanFieldView(
                state="degraded",
                summary="候选标的为空：当前盘前强势标的 section 没有返回可用标的。",
            )
        items: list[TradingPlanCandidateView] = []
        for index, item in enumerate(symbols[:5], start=1):
            if isinstance(item, str):
                items.append(TradingPlanCandidateView(symbol=item, rank=index))
                continue
            symbol = str(item.get("symbol") or "").strip()
            if not symbol:
                continue
            items.append(
                TradingPlanCandidateView(
                    symbol=symbol,
                    name=item.get("name"),
                    rank=index,
                    score=self._as_float(item.get("score") or item.get("strength")),
                    note=item.get("reason") or item.get("summary"),
                    state="ready" if getattr(section, "quality_status", "") == "ok" else "degraded",
                )
            )
        state = "ready" if getattr(section, "quality_status", "") == "ok" else "degraded"
        return items, TradingPlanFieldView(state=state, summary="候选标的来自正式盘前市场快照 strong_symbols section。")

    def _rule_decision_view(self, item: Any, rule_versions: dict[str, Any]) -> TradingPlanRuleDecisionView:
        rule_version = rule_versions.get(item.rule_version_id)
        payload = item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
        payload["rule_title"] = getattr(rule_version, "title", None)
        return TradingPlanRuleDecisionView.model_validate(payload)

    def _compute_confidence(
        self,
        *,
        market_confidence: float | None,
        selected_rule_count: int,
        reduced_rule_count: int,
        total_rule_count: int,
        degraded_inputs: list[str],
    ) -> float:
        base = float(market_confidence or 0.5)
        rule_factor = (selected_rule_count + 0.5 * reduced_rule_count) / max(total_rule_count, 1)
        degraded_penalty = min(0.25, len(degraded_inputs) * 0.05)
        return round(max(0.05, min(0.95, base * 0.6 + rule_factor * 0.4 - degraded_penalty)), 2)

    def _confidence_label(self, value: float | None) -> str:
        if value is None:
            return "暂不可用"
        if value >= 0.8:
            return f"{round(value * 100)}%（较高）"
        if value >= 0.6:
            return f"{round(value * 100)}%（中等）"
        return f"{round(value * 100)}%（偏谨慎）"

    def _signal_side(self, rules: list[TradingPlanRuleDecisionView], rule_versions: dict[str, Any]) -> Literal["BUY", "SELL", "HOLD"]:
        votes = {"BUY": 0, "SELL": 0}
        for item in rules:
            action_json = getattr(rule_versions.get(item.rule_version_id), "action_json", {}) or {}
            raw_side = str(action_json.get("decision") or action_json.get("side") or "").upper()
            if raw_side in votes:
                votes[raw_side] += 1
        if votes["BUY"] > votes["SELL"]:
            return "BUY"
        if votes["SELL"] > votes["BUY"]:
            return "SELL"
        return "HOLD"

    def _payload_signature(self, payload: dict[str, Any] | None) -> str | None:
        if not isinstance(payload, dict):
            return None
        value = payload.get("input_signature")
        return str(value) if value else None

    def _input_signature(self, selection: Any) -> str:
        seed = json.dumps(
            {
                "daily_rule_selection_id": selection.daily_rule_selection_id,
                "strategy_version_id": selection.strategy_version_id,
                "trade_date": selection.trade_date,
                "traceability": selection.traceability.model_dump(mode="json"),
                "enabled_rules": [item.model_dump(mode="json") for item in selection.enabled_rules],
                "reduced_rules": [item.model_dump(mode="json") for item in selection.reduced_rules],
                "suspended_rules": [item.model_dump(mode="json") for item in selection.suspended_rules],
                "degraded_inputs": selection.degraded_inputs,
                "unresolved_inputs": selection.unresolved_inputs,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(seed.encode("utf-8")).hexdigest()

    def _extract_position_ratio(self, summary: str | None) -> float:
        if not summary:
            return 0.0
        for chunk in summary.replace("%", "").split():
            try:
                value = float(chunk)
            except ValueError:
                continue
            if value > 1:
                return round(value / 100, 4)
            return round(value, 4)
        return 0.0

    def _first_value(self, payload: dict[str, Any], *keys: str) -> Any | None:
        for key in keys:
            if key in payload and payload[key] not in (None, ""):
                return payload[key]
        return None

    def _as_decimal(self, value: float | None) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(round(float(value), 8)))

    def _as_float(self, value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _is_uuid(self, value: str) -> bool:
        try:
            UUID(str(value))
            return True
        except (TypeError, ValueError):
            return False
