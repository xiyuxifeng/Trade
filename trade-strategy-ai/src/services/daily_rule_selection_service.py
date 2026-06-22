from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
import json
from typing import Any, Callable, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.db.repositories.daily_rule_selection_repo import DailyRuleSelectionRepository
from src.db.session import get_session_factory
from src.domain.enums import DailyRuleSelectionState, FormalLifecycleState, QualityStatus
from src.models.stage2_canonical import DailyRuleSelection, DailyRuleSelectionItem
from src.services.pre_market_readiness_service import PreMarketReadinessService
from src.services.system_run_trace_service import build_stable_business_run_id


PRIORITY_LABELS = {
    "formal_rule_applicability": "正式规则适用性",
    "current_market_state": "当前市场状态",
    "formal_strategy": "当前正式策略",
    "data_quality": "数据质量",
    "author_validated_profile": "作者验证画像",
    "author_method_profile": "作者方法画像",
}
READY_STATES = {"ready", "ok", "verified", "complete", QualityStatus.verified.value, QualityStatus.complete.value}
DEGRADED_STATES = {"partial", "degraded", "insufficient_sample", "insufficient_coverage", "ambiguous", "unresolved"}
BLOCKED_STATES = {"blocked", "invalid", "conflict", "unavailable"}
ACTIVE_MEMBERSHIP_STATES = {"", "active", "enabled", "ready", "published"}


class DailyRuleDecisionView(BaseModel):
    rule_version_id: str
    strategy_rule_membership_id: str | None = None
    decision: Literal["selected", "reduced", "suspended"]
    controlling_priority_tier: str
    controlling_priority_label: str
    evidence_ids: list[str] = Field(default_factory=list)
    quality_states: list[str] = Field(default_factory=list)
    reason_tiers: list[str] = Field(default_factory=list)
    reason_list: list[str] = Field(default_factory=list)
    degraded_inputs: list[str] = Field(default_factory=list)
    unresolved_inputs: list[str] = Field(default_factory=list)


class DailyRuleSelectionTraceabilityView(BaseModel):
    trade_date: str
    strategy_version_id: str
    dataset_snapshot_id: str
    market_snapshot_id: str
    market_state_id: str
    rule_applicability_profile_ids: list[str] = Field(default_factory=list)
    author_method_profile_version_id: str | None = None
    author_rule_profile_version_id: str | None = None
    author_validated_profile_version_id: str | None = None
    data_quality_state: str
    readiness_status: str


class DailyRuleSelectionView(BaseModel):
    state: Literal["ready", "partial", "unavailable"]
    selection_status: Literal["ready", "degraded", "blocked"]
    generated: bool
    trade_date: str
    happened: str
    affected: str
    repair_guidance: str
    daily_rule_selection_id: str | None = None
    revision_no: int | None = None
    strategy_version_id: str
    quality_status: str
    readiness_status: str
    enabled_rules: list[DailyRuleDecisionView] = Field(default_factory=list)
    reduced_rules: list[DailyRuleDecisionView] = Field(default_factory=list)
    suspended_rules: list[DailyRuleDecisionView] = Field(default_factory=list)
    traceability: DailyRuleSelectionTraceabilityView
    degraded_inputs: list[str] = Field(default_factory=list)
    unresolved_inputs: list[str] = Field(default_factory=list)


class DailyRuleSelectionService:
    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any] | None = None,
        repository: DailyRuleSelectionRepository | None = None,
        readiness_service: PreMarketReadinessService | None = None,
    ) -> None:
        self._session_scope_factory = session_scope_factory or self._default_session_scope_factory
        self.repository = repository or DailyRuleSelectionRepository()
        self.readiness_service = readiness_service or PreMarketReadinessService(session_scope_factory=self._session_scope_factory)

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

    async def get_rule_selection(
        self,
        trade_date: str | date,
        *,
        actor_id: str,
        actor_role: str,
    ) -> DailyRuleSelectionView:
        if actor_role not in {"viewer", "operator", "admin"}:
            raise PermissionError("viewer permission is required to view daily rule selection")

        normalized_trade_date = trade_date if isinstance(trade_date, date) else date.fromisoformat(str(trade_date))
        readiness = await self.readiness_service.get_readiness(
            normalized_trade_date.isoformat(),
            actor_id=actor_id,
            actor_role=actor_role,
        )
        traceability = DailyRuleSelectionTraceabilityView(
            trade_date=readiness.traceability.trade_date,
            strategy_version_id=str(readiness.traceability.strategy_version_id),
            dataset_snapshot_id=str(readiness.traceability.dataset_snapshot_id),
            market_snapshot_id=str(readiness.traceability.market_snapshot_id),
            market_state_id=str(readiness.traceability.market_state_id),
            rule_applicability_profile_ids=list(readiness.traceability.rule_applicability_profile_ids),
            author_method_profile_version_id=readiness.traceability.author_method_profile_version_id,
            author_rule_profile_version_id=readiness.traceability.author_rule_profile_version_id,
            author_validated_profile_version_id=readiness.traceability.author_validated_profile_version_id,
            data_quality_state=readiness.traceability.data_quality_state,
            readiness_status=readiness.readiness_status,
        )
        degraded_inputs = [item.code for item in readiness.checks if item.status == "degraded"]
        unresolved_inputs = [item.code for item in readiness.checks if item.status == "blocked"]
        if not readiness.can_proceed:
            return DailyRuleSelectionView(
                state="unavailable",
                selection_status="blocked",
                generated=False,
                trade_date=normalized_trade_date.isoformat(),
                happened="正式盘前检查尚未通过，当前不能生成每日规则选择。",
                affected="如果继续生成，会把缺失或阻塞的正式输入误当成可用结果。",
                repair_guidance=readiness.repair_guidance,
                strategy_version_id=traceability.strategy_version_id,
                quality_status="blocked",
                readiness_status=readiness.readiness_status,
                traceability=traceability,
                degraded_inputs=degraded_inputs,
                unresolved_inputs=unresolved_inputs,
            )

        async with self._session_scope_factory() as session:
            strategy_version = await self.repository.get_strategy_version(session, UUID(traceability.strategy_version_id))
            if strategy_version is None or strategy_version.lifecycle_state != FormalLifecycleState.published:
                return DailyRuleSelectionView(
                    state="unavailable",
                    selection_status="blocked",
                    generated=False,
                    trade_date=normalized_trade_date.isoformat(),
                    happened="当前正式策略版本不可用，不能生成每日规则选择。",
                    affected="系统无法确认今天应该按哪一版正式策略挑选规则。",
                    repair_guidance="先确认当前正式策略版本已发布且绑定完整。",
                    strategy_version_id=traceability.strategy_version_id,
                    quality_status="blocked",
                    readiness_status=readiness.readiness_status,
                    traceability=traceability,
                    degraded_inputs=degraded_inputs,
                    unresolved_inputs=["current_formal_strategy"],
                )

            memberships = await self.repository.list_strategy_rule_memberships(
                session,
                strategy_version_id=strategy_version.strategy_version_id,
            )
            if not memberships:
                return DailyRuleSelectionView(
                    state="unavailable",
                    selection_status="blocked",
                    generated=False,
                    trade_date=normalized_trade_date.isoformat(),
                    happened="当前正式策略没有可用于今日盘前的正式规则。",
                    affected="系统无法生成每日规则选择结果。",
                    repair_guidance="先到策略中心补齐正式规则池后再重试。",
                    strategy_version_id=traceability.strategy_version_id,
                    quality_status="blocked",
                    readiness_status=readiness.readiness_status,
                    traceability=traceability,
                    degraded_inputs=degraded_inputs,
                    unresolved_inputs=["missing_strategy_rule_memberships"],
                )

            market_state = await self.repository.get_market_state(session, market_state_id=UUID(traceability.market_state_id))
            profile_ids = [
                UUID(value)
                for value in (
                    traceability.author_method_profile_version_id,
                    traceability.author_rule_profile_version_id,
                    traceability.author_validated_profile_version_id,
                )
                if value
            ]
            author_profiles = {
                str(item.author_profile_version_id): item
                for item in await self.repository.list_author_profile_versions(session, author_profile_version_ids=profile_ids)
            }
            applicability_profiles = await self.repository.list_published_rule_applicability_profiles(
                session,
                rule_version_ids=[item.rule_version_id for item in memberships],
                dataset_snapshot_id=UUID(traceability.dataset_snapshot_id),
            )
            profile_by_rule: dict[str, Any] = {}
            for item in sorted(applicability_profiles, key=self._applicability_profile_sort_key):
                if item.rule_version_id is not None:
                    profile_by_rule[str(item.rule_version_id)] = item

            decisions = self._evaluate_decisions(
                memberships=memberships,
                profile_by_rule=profile_by_rule,
                market_state=market_state,
                author_profiles=author_profiles,
                traceability=traceability,
                degraded_inputs=degraded_inputs,
            )
            input_signature = self._input_signature(traceability, decisions)
            latest = await self.repository.get_latest_selection(
                session,
                strategy_version_id=strategy_version.strategy_version_id,
                market_state_id=UUID(traceability.market_state_id),
                trade_date=normalized_trade_date,
            )
            if latest is not None and self._selection_context(latest).get("input_signature") == input_signature:
                items = await self.repository.list_selection_items(session, daily_rule_selection_id=latest.daily_rule_selection_id)
                return self._build_view_from_record(latest, items)

            selection_status = "degraded" if decisions["reduced"] or decisions["suspended"] or degraded_inputs else "ready"
            quality_status = QualityStatus.partial if selection_status == "degraded" else QualityStatus.verified
            revision_no = await self.repository.next_revision_no(
                session,
                strategy_version_id=strategy_version.strategy_version_id,
                market_state_id=UUID(traceability.market_state_id),
                trade_date=normalized_trade_date,
            )
            selection_context = {
                **traceability.model_dump(mode="json"),
                "input_signature": input_signature,
                "degraded_inputs": degraded_inputs,
                "unresolved_inputs": sorted({value for group in decisions.values() for item in group for value in item.unresolved_inputs}),
            }
            selection = DailyRuleSelection(
                daily_rule_selection_id=uuid4(),
                strategy_version_id=strategy_version.strategy_version_id,
                market_state_id=UUID(traceability.market_state_id),
                trade_date=normalized_trade_date,
                revision_no=revision_no,
                selected_rules_json=self._decision_bucket_payload("selected", decisions["selected"], selection_context),
                reduced_rules_json=self._decision_bucket_payload("reduced", decisions["reduced"], selection_context),
                blocked_rules_json=self._decision_bucket_payload("suspended", decisions["suspended"], selection_context),
                quality_status=quality_status,
                lifecycle_state=DailyRuleSelectionState.generated,
                source_run_id=build_stable_business_run_id(
                    object_type="daily-rule-selection",
                    object_id=f"{strategy_version.strategy_version_id}:{normalized_trade_date.isoformat()}:{revision_no}",
                ),
                created_by=actor_id,
                updated_by=actor_id,
            )
            items = [
                DailyRuleSelectionItem(
                    daily_rule_selection_item_id=uuid4(),
                    daily_rule_selection_id=selection.daily_rule_selection_id,
                    rule_version_id=UUID(item.rule_version_id),
                    decision=item.decision,
                    payload_json=item.model_dump(mode="json"),
                )
                for item in [*decisions["selected"], *decisions["reduced"], *decisions["suspended"]]
            ]
            persisted, persisted_items = await self.repository.create_selection(session, selection=selection, items=items)
            return self._build_view_from_record(persisted, persisted_items)

    def _evaluate_decisions(
        self,
        *,
        memberships: list[Any],
        profile_by_rule: dict[str, Any],
        market_state: Any,
        author_profiles: dict[str, Any],
        traceability: DailyRuleSelectionTraceabilityView,
        degraded_inputs: list[str],
    ) -> dict[str, list[DailyRuleDecisionView]]:
        sorted_memberships = sorted(
            memberships,
            key=lambda item: (
                -(float(item.base_weight) if item.base_weight is not None else -1.0),
                str(item.membership_id),
            ),
        )
        grouped = {"selected": [], "reduced": [], "suspended": []}
        for membership in sorted_memberships:
            decision = self._evaluate_rule(
                membership=membership,
                applicability_profile=profile_by_rule.get(str(membership.rule_version_id)),
                market_state=market_state,
                author_profiles=author_profiles,
                traceability=traceability,
                degraded_inputs=degraded_inputs,
            )
            grouped[decision.decision].append(decision)
        return grouped

    def _evaluate_rule(
        self,
        *,
        membership: Any,
        applicability_profile: Any | None,
        market_state: Any,
        author_profiles: dict[str, Any],
        traceability: DailyRuleSelectionTraceabilityView,
        degraded_inputs: list[str],
    ) -> DailyRuleDecisionView:
        reason_tiers: list[str] = []
        reason_list: list[str] = []
        evidence_ids: list[str] = []
        quality_states: list[str] = []
        unresolved_inputs: list[str] = []
        local_degraded_inputs = list(degraded_inputs)
        decision = "selected"
        controlling_tier = "formal_rule_applicability"

        if applicability_profile is None:
            decision = "suspended"
            controlling_tier = "formal_rule_applicability"
            reason_tiers.append(controlling_tier)
            reason_list.append("缺少正式规则适用性，今日暂停。")
            unresolved_inputs.append("missing_rule_applicability")
            quality_states.append("unavailable")
        else:
            evidence_ids.extend(
                [
                    str(applicability_profile.applicability_profile_id),
                    *[str(item) for item in applicability_profile.source_backtest_run_ids],
                    *[str(item) for item in applicability_profile.source_backtest_result_ids],
                ]
            )
            quality_states.extend(
                [
                    str(applicability_profile.quality_status),
                    str(applicability_profile.result_status),
                    str(applicability_profile.insufficient_sample_status),
                ]
            )
            if (
                str(applicability_profile.result_status) in BLOCKED_STATES
                or str(applicability_profile.recommendation_status) in BLOCKED_STATES
                or str(applicability_profile.quality_status) in BLOCKED_STATES
            ):
                decision = "suspended"
                controlling_tier = "formal_rule_applicability"
                reason_tiers.append(controlling_tier)
                reason_list.append("正式规则适用性结果不可用，今日暂停。")
                unresolved_inputs.append(str(applicability_profile.result_status))
            elif (
                str(applicability_profile.result_status) in DEGRADED_STATES
                or str(applicability_profile.quality_status) in DEGRADED_STATES
                or str(applicability_profile.insufficient_sample_status) not in {"sufficient", "ready", "ok"}
                or (applicability_profile.coverage is not None and float(applicability_profile.coverage) < 1.0)
            ):
                decision = "reduced"
                controlling_tier = "formal_rule_applicability"
                reason_tiers.append(controlling_tier)
                reason_list.append("样本不足，今日降权处理。")
                local_degraded_inputs.extend(
                    item
                    for item in (
                        str(applicability_profile.result_status),
                        str(applicability_profile.quality_status),
                        str(applicability_profile.insufficient_sample_status),
                    )
                    if item not in {"sufficient", "ready", "ok"} and item not in local_degraded_inputs
                )
            else:
                reason_tiers.append("formal_rule_applicability")
                reason_list.append("规则适用性已发布。")

        if applicability_profile is not None and decision == "selected":
            current_labels = {self._normalize(market_state.primary_label)}
            current_labels.update(self._normalize(item.get("label")) for item in getattr(market_state, "labels", []) if item.get("label"))
            blocked_labels = {self._normalize(item.get("regime_label")) for item in applicability_profile.blocked_regimes if item.get("regime_label")}
            neutral_labels = {self._normalize(item.get("regime_label")) for item in applicability_profile.neutral_regimes if item.get("regime_label")}
            applicable_labels = {self._normalize(item.get("regime_label")) for item in applicability_profile.applicable_regimes if item.get("regime_label")}
            evidence_ids.append(str(traceability.market_state_id))
            quality_states.append(str(market_state.quality_status))
            if blocked_labels and current_labels & blocked_labels:
                decision = "suspended"
                controlling_tier = "current_market_state"
                reason_tiers.append(controlling_tier)
                reason_list.append("当前市场状态与规则冲突，今日暂停。")
            elif neutral_labels and current_labels & neutral_labels:
                decision = "reduced"
                controlling_tier = "current_market_state"
                reason_tiers.append(controlling_tier)
                reason_list.append("当前市场状态仅部分支持该规则，今日降权。")
            elif applicable_labels and current_labels & applicable_labels:
                reason_tiers.append("current_market_state")
                reason_list.append("当前市场状态与规则适配。")
            elif applicable_labels or neutral_labels or blocked_labels:
                decision = "reduced"
                controlling_tier = "current_market_state"
                reason_tiers.append(controlling_tier)
                reason_list.append("当前市场状态缺少明确适配证据，今日降权。")

        membership_status = str(membership.status or "").strip().lower()
        base_weight = float(membership.base_weight) if membership.base_weight is not None else None
        if decision == "selected":
            if membership_status and membership_status not in ACTIVE_MEMBERSHIP_STATES:
                decision = "suspended"
                controlling_tier = "formal_strategy"
                reason_tiers.append(controlling_tier)
                reason_list.append("当前正式策略没有启用该规则。")
            elif base_weight is not None and base_weight <= 0:
                decision = "suspended"
                controlling_tier = "formal_strategy"
                reason_tiers.append(controlling_tier)
                reason_list.append("当前正式策略把该规则权重设为 0，今日暂停。")
            else:
                reason_tiers.append("formal_strategy")
                reason_list.append("当前正式策略仍保留该规则。")

        if decision == "selected" and (
            traceability.data_quality_state != "ready" or traceability.readiness_status == "degraded" or local_degraded_inputs
        ):
            decision = "reduced"
            controlling_tier = "data_quality"
            reason_tiers.append(controlling_tier)
            reason_list.append("存在降级输入，今日按降级模式保留该规则。")

        validated_profile = author_profiles.get(str(traceability.author_validated_profile_version_id)) if traceability.author_validated_profile_version_id else None
        method_profile = author_profiles.get(str(traceability.author_method_profile_version_id)) if traceability.author_method_profile_version_id else None
        if decision == "selected" and validated_profile is not None and not self._is_ready(str(validated_profile.quality_status)):
            decision = "reduced"
            controlling_tier = "author_validated_profile"
            reason_tiers.append(controlling_tier)
            reason_list.append("作者验证画像质量不是完全可用，今日降权。")
        if decision == "selected" and method_profile is not None and not self._is_ready(str(method_profile.quality_status)):
            decision = "reduced"
            controlling_tier = "author_method_profile"
            reason_tiers.append(controlling_tier)
            reason_list.append("作者方法画像质量不是完全可用，今日降权。")

        return DailyRuleDecisionView(
            rule_version_id=str(membership.rule_version_id),
            strategy_rule_membership_id=str(membership.membership_id),
            decision=decision,
            controlling_priority_tier=controlling_tier,
            controlling_priority_label=PRIORITY_LABELS[controlling_tier],
            evidence_ids=self._ordered_unique(evidence_ids),
            quality_states=self._ordered_unique(quality_states),
            reason_tiers=self._ordered_unique(reason_tiers),
            reason_list=reason_list,
            degraded_inputs=self._ordered_unique(local_degraded_inputs),
            unresolved_inputs=self._ordered_unique(unresolved_inputs),
        )

    def _decision_bucket_payload(
        self,
        bucket: str,
        items: list[DailyRuleDecisionView],
        selection_context: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "bucket": bucket,
            "selection_context": selection_context,
            "items": [
                {
                    "rule_version_id": item.rule_version_id,
                    "strategy_rule_membership_id": item.strategy_rule_membership_id,
                    "decision": item.decision,
                    "controlling_priority_tier": item.controlling_priority_tier,
                    "reason_tiers": item.reason_tiers,
                }
                for item in items
            ],
        }

    def _build_view_from_record(
        self,
        selection: DailyRuleSelection,
        items: list[DailyRuleSelectionItem],
    ) -> DailyRuleSelectionView:
        payloads = [DailyRuleDecisionView.model_validate(item.payload_json) for item in items]
        traceability = DailyRuleSelectionTraceabilityView.model_validate(self._selection_context(selection))
        reduced = [item for item in payloads if item.decision == "reduced"]
        suspended = [item for item in payloads if item.decision == "suspended"]
        selection_status = "degraded" if reduced or suspended or traceability.readiness_status == "degraded" else "ready"
        return DailyRuleSelectionView(
            state="partial" if selection_status == "degraded" else "ready",
            selection_status=selection_status,
            generated=True,
            trade_date=selection.trade_date.isoformat(),
            happened="已根据正式盘前输入生成每日规则选择。",
            affected="今日启用、降权和暂停规则已经固定，可继续后续盘前流程。",
            repair_guidance="如需减少降级影响，请先补齐缺失输入后重新生成。",
            daily_rule_selection_id=str(selection.daily_rule_selection_id),
            revision_no=selection.revision_no,
            strategy_version_id=str(selection.strategy_version_id),
            quality_status=selection.quality_status.value if hasattr(selection.quality_status, "value") else str(selection.quality_status),
            readiness_status=traceability.readiness_status,
            enabled_rules=[item for item in payloads if item.decision == "selected"],
            reduced_rules=reduced,
            suspended_rules=suspended,
            traceability=traceability,
            degraded_inputs=self._ordered_unique(self._selection_context(selection).get("degraded_inputs", [])),
            unresolved_inputs=self._ordered_unique(self._selection_context(selection).get("unresolved_inputs", [])),
        )

    def _selection_context(self, selection: DailyRuleSelection) -> dict[str, Any]:
        for bucket in (selection.selected_rules_json, selection.reduced_rules_json, selection.blocked_rules_json):
            if isinstance(bucket, dict) and isinstance(bucket.get("selection_context"), dict):
                return bucket["selection_context"]
        raise LookupError("daily rule selection context is missing")

    def _input_signature(
        self,
        traceability: DailyRuleSelectionTraceabilityView,
        decisions: dict[str, list[DailyRuleDecisionView]],
    ) -> str:
        raw = {
            "traceability": traceability.model_dump(mode="json"),
            "decisions": {
                key: [item.model_dump(mode="json") for item in value]
                for key, value in decisions.items()
            },
        }
        return sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize(value: str | None) -> str:
        return (value or "").strip().lower()

    @staticmethod
    def _ordered_unique(values: list[str]) -> list[str]:
        ordered: list[str] = []
        for item in values:
            if item and item not in ordered:
                ordered.append(item)
        return ordered

    @staticmethod
    def _is_ready(value: str) -> bool:
        return value in READY_STATES

    @staticmethod
    def _applicability_profile_sort_key(item: Any) -> tuple[datetime, datetime, str]:
        return (
            item.reviewed_at or datetime.min,
            item.created_at or datetime.min,
            str(item.applicability_profile_id),
        )
