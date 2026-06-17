from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from src.common.stage2_writer_routing import canonical_write_scope
from src.domain.enums import CanonicalObjectType, FormalLifecycleState
from src.models.stage2_canonical import LifecycleEvent, Rule, RuleCandidate, RuleVersion
from src.services.rule_governance_service import RuleGovernanceGateError, RuleGovernanceService


class RuleLifecycleError(RuntimeError):
    pass


class RuleLifecycleConflictError(RuleLifecycleError):
    pass


class RuleLifecycleTransitionBlockedError(RuleLifecycleError):
    pass


class RuleLifecycleStaleWriteError(RuleLifecycleError):
    pass


@dataclass(frozen=True)
class LifecycleAction:
    key: str
    label: str
    requires_reason: bool = True
    requires_evidence: bool = False


@dataclass(frozen=True)
class LifecycleView:
    object_type: str
    object_id: str
    canonical_state: str
    display_state: str | None
    display_label: str | None
    status: str
    status_message: str | None
    restriction_message: str | None
    correlation_id: str | None
    updated_at: datetime
    allowed_next_actions: list[LifecycleAction] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class RuleLifecycleService:
    service_name = "rule-lifecycle-service"

    def __init__(
        self,
        *,
        session_scope_factory,
        regression_service: Any | None = None,
        governance_service: RuleGovernanceService | None = None,
    ) -> None:
        self._session_scope_factory = session_scope_factory
        self._governance_service = governance_service or RuleGovernanceService(
            regression_service=regression_service,
        )

    async def _ensure_gate(self) -> None:
        try:
            await self._governance_service.ensure_fixed_set_gate()
        except RuleGovernanceGateError as exc:
            raise RuleLifecycleTransitionBlockedError(str(exc)) from exc

    @staticmethod
    def _rule_lifecycle_payload(
        *,
        display_state: str,
        display_label: str,
        status: str = "ready",
        status_message: str | None = None,
        restriction_level: str = "none",
        restriction_message: str | None = None,
        evidence_refs: list[str] | None = None,
        entry_point: str,
    ) -> dict[str, Any]:
        return {
            "lifecycle": {
                "display_state": display_state,
                "display_label": display_label,
                "status": status,
                "status_message": status_message,
                "restriction_level": restriction_level,
                "restriction_message": restriction_message,
                "evidence_refs": evidence_refs or [],
                "entry_point": entry_point,
            }
        }

    @staticmethod
    def _event_metadata(event: LifecycleEvent | None) -> dict[str, Any]:
        if event is None or not isinstance(event.after_json, dict):
            return {}
        lifecycle = event.after_json.get("lifecycle")
        return lifecycle if isinstance(lifecycle, dict) else {}

    @staticmethod
    def _ensure_reason(reason: str | None) -> None:
        if not reason or not reason.strip():
            raise RuleLifecycleTransitionBlockedError("必须提供变更原因。")

    @staticmethod
    def _ensure_expected_timestamp(actual: datetime, expected: datetime | None) -> None:
        if expected is not None and actual != expected:
            raise RuleLifecycleStaleWriteError("对象状态已更新，请刷新后重试。")

    async def _get_candidate(self, session, *, candidate_id: UUID) -> RuleCandidate:
        candidate = await session.get(RuleCandidate, candidate_id)
        if candidate is None:
            raise RuleLifecycleError(f"rule candidate not found: {candidate_id}")
        return candidate

    async def _get_rule_version(self, session, *, rule_version_id: UUID) -> RuleVersion:
        rule_version = await session.get(RuleVersion, rule_version_id)
        if rule_version is None:
            raise RuleLifecycleError(f"rule version not found: {rule_version_id}")
        return rule_version

    async def _get_rule(self, session, *, rule_id: UUID) -> Rule | None:
        return await session.get(Rule, rule_id)

    async def _get_latest_event(self, session, *, object_type: str, object_id: UUID, correlation_id: str | None = None) -> LifecycleEvent | None:
        stmt = (
            select(LifecycleEvent)
            .where(LifecycleEvent.object_type == object_type)
            .where(LifecycleEvent.object_id == object_id)
            .order_by(LifecycleEvent.occurred_at.desc(), LifecycleEvent.event_id.desc())
            .limit(1)
        )
        if correlation_id is not None:
            stmt = (
                select(LifecycleEvent)
                .where(LifecycleEvent.object_type == object_type)
                .where(LifecycleEvent.object_id == object_id)
                .where(LifecycleEvent.correlation_id == correlation_id)
                .order_by(LifecycleEvent.occurred_at.desc(), LifecycleEvent.event_id.desc())
                .limit(1)
            )
        return (await session.execute(stmt)).scalars().first()

    async def _append_event(
        self,
        session,
        *,
        object_type: str,
        object_id: UUID,
        from_state: str | None,
        to_state: str,
        actor_type: str,
        actor_id: str,
        reason_code: str,
        reason_text: str | None,
        before_json: dict[str, Any] | None,
        after_json: dict[str, Any] | None,
        correlation_id: str,
    ) -> None:
        session.add(
            LifecycleEvent(
                event_id=uuid4(),
                object_type=object_type,
                object_id=object_id,
                from_state=from_state,
                to_state=to_state,
                actor_type=actor_type,
                actor_id=actor_id,
                reason_code=reason_code,
                reason_text=reason_text,
                before_json=before_json,
                after_json=after_json,
                occurred_at=datetime.now(UTC),
                correlation_id=correlation_id,
            )
        )
        await session.flush()

    @staticmethod
    def _candidate_actions(display_label: str | None) -> list[LifecycleAction]:
        if display_label == "候选":
            return [LifecycleAction(key="submit_for_review", label="提交审核")]
        return []

    @staticmethod
    def _rule_actions(display_label: str | None) -> list[LifecycleAction]:
        if display_label == "已批准":
            return [LifecycleAction(key="queue_backtest", label="进入待回测")]
        if display_label == "待回测":
            return [
                LifecycleAction(key="start_validation", label="开始验证"),
                LifecycleAction(key="retire", label="停用规则"),
            ]
        if display_label == "验证中":
            return [
                LifecycleAction(key="mark_usable", label="标记可用", requires_evidence=True),
                LifecycleAction(key="mark_limited", label="限定使用", requires_evidence=True),
                LifecycleAction(key="retire", label="停用规则"),
            ]
        if display_label == "可用":
            return [
                LifecycleAction(key="mark_limited", label="限定使用", requires_evidence=True),
                LifecycleAction(key="retire", label="停用规则"),
            ]
        if display_label == "限定使用":
            return [
                LifecycleAction(key="mark_usable", label="标记可用", requires_evidence=True),
                LifecycleAction(key="retire", label="停用规则"),
            ]
        return []

    def _build_candidate_view(self, *, candidate: RuleCandidate) -> LifecycleView:
        mapping = {
            "extracted": ("候选", "候选", "ready", None),
            "auto_review": ("待审核", "待审核", "ready", None),
            "manual_review": ("待审核", "待审核", "ready", None),
            "rejected": (None, None, "unavailable", "该候选规则已被拒绝，未进入正式生命周期。"),
            "superseded": (None, None, "compatibility_only", "该候选规则已被替代，当前仅保留历史记录。"),
        }
        display_state, display_label, status, status_message = mapping.get(
            str(candidate.review_state),
            (None, None, "unavailable", "无法证明候选规则状态。"),
        )
        return LifecycleView(
            object_type="rule_candidate",
            object_id=str(candidate.rule_candidate_id),
            canonical_state=str(candidate.review_state),
            display_state=display_state,
            display_label=display_label,
            status=status,
            status_message=status_message,
            restriction_message=None,
            correlation_id=None,
            updated_at=candidate.updated_at,
            allowed_next_actions=self._candidate_actions(display_label),
            metadata={},
        )

    def _build_rule_version_view(self, *, rule_version: RuleVersion, rule: Rule | None, latest_event: LifecycleEvent | None) -> LifecycleView:
        lifecycle_meta = {}
        if isinstance(rule_version.evidence_json, dict):
            lifecycle_meta = rule_version.evidence_json.get("lifecycle") or {}
        if not lifecycle_meta:
            lifecycle_meta = self._event_metadata(latest_event)
        canonical_state = str(rule_version.lifecycle_state)

        if canonical_state == FormalLifecycleState.draft.value:
            display_state = lifecycle_meta.get("display_state")
            display_label = lifecycle_meta.get("display_label")
            if display_label in {"已批准", "待回测"}:
                return LifecycleView(
                    object_type="rule_version",
                    object_id=str(rule_version.rule_version_id),
                    canonical_state=canonical_state,
                    display_state=display_label,
                    display_label=display_label,
                    status=str(lifecycle_meta.get("status") or "ready"),
                    status_message=lifecycle_meta.get("status_message"),
                    restriction_message=lifecycle_meta.get("restriction_message"),
                    correlation_id=latest_event.correlation_id if latest_event is not None else None,
                    updated_at=rule_version.updated_at,
                    allowed_next_actions=self._rule_actions(display_label),
                    metadata=lifecycle_meta,
                )
            return LifecycleView(
                object_type="rule_version",
                object_id=str(rule_version.rule_version_id),
                canonical_state=canonical_state,
                display_state=None,
                display_label=None,
                status="unavailable",
                status_message="缺少可证明的正式生命周期证据。",
                restriction_message=None,
                correlation_id=latest_event.correlation_id if latest_event is not None else None,
                updated_at=rule_version.updated_at,
                allowed_next_actions=[],
                metadata=lifecycle_meta if isinstance(lifecycle_meta, dict) else {},
            )

        if canonical_state == FormalLifecycleState.in_review.value:
            return LifecycleView(
                object_type="rule_version",
                object_id=str(rule_version.rule_version_id),
                canonical_state=canonical_state,
                display_state="验证中",
                display_label="验证中",
                status="ready",
                status_message=None,
                restriction_message=None,
                correlation_id=latest_event.correlation_id if latest_event is not None else None,
                updated_at=rule_version.updated_at,
                allowed_next_actions=self._rule_actions("验证中"),
                metadata=lifecycle_meta if isinstance(lifecycle_meta, dict) else {},
            )

        if canonical_state == FormalLifecycleState.published.value:
            restriction_level = str(lifecycle_meta.get("restriction_level") or "none")
            if restriction_level == "limited" or rule is None or rule.current_published_version_id != rule_version.rule_version_id:
                display_label = "限定使用"
                display_state = "限定使用"
            else:
                display_label = "可用"
                display_state = "可用"
            return LifecycleView(
                object_type="rule_version",
                object_id=str(rule_version.rule_version_id),
                canonical_state=canonical_state,
                display_state=display_state,
                display_label=display_label,
                status="ready",
                status_message=None,
                restriction_message=lifecycle_meta.get("restriction_message"),
                correlation_id=latest_event.correlation_id if latest_event is not None else None,
                updated_at=rule_version.updated_at,
                allowed_next_actions=self._rule_actions(display_label),
                metadata=lifecycle_meta if isinstance(lifecycle_meta, dict) else {},
            )

        if canonical_state in {
            FormalLifecycleState.archived.value,
            FormalLifecycleState.rejected.value,
            FormalLifecycleState.superseded.value,
        }:
            return LifecycleView(
                object_type="rule_version",
                object_id=str(rule_version.rule_version_id),
                canonical_state=canonical_state,
                display_state="已停用",
                display_label="已停用",
                status="ready",
                status_message=None,
                restriction_message=None,
                correlation_id=latest_event.correlation_id if latest_event is not None else None,
                updated_at=rule_version.updated_at,
                allowed_next_actions=[],
                metadata=lifecycle_meta if isinstance(lifecycle_meta, dict) else {},
            )

        return LifecycleView(
            object_type="rule_version",
            object_id=str(rule_version.rule_version_id),
            canonical_state=canonical_state,
            display_state=None,
            display_label=None,
            status="compatibility_only",
            status_message="当前 formal lifecycle state 无法在 Stage 4 中证明为正式用户状态。",
            restriction_message=None,
            correlation_id=latest_event.correlation_id if latest_event is not None else None,
            updated_at=rule_version.updated_at,
            allowed_next_actions=[],
            metadata=lifecycle_meta if isinstance(lifecycle_meta, dict) else {},
        )

    async def get_candidate_lifecycle(self, *, candidate_id: UUID) -> LifecycleView:
        async with self._session_scope_factory() as session:
            return await self.get_candidate_lifecycle_in_session(session, candidate_id=candidate_id)

    async def get_candidate_lifecycle_in_session(self, session, *, candidate_id: UUID) -> LifecycleView:
        candidate = await self._get_candidate(session, candidate_id=candidate_id)
        return self._build_candidate_view(candidate=candidate)

    async def get_rule_version_lifecycle_in_session(self, session, *, rule_version_id: str | UUID) -> LifecycleView:
        version_uuid = UUID(str(rule_version_id))
        rule_version = await self._get_rule_version(session, rule_version_id=version_uuid)
        rule = await self._get_rule(session, rule_id=rule_version.rule_id)
        latest_event = await self._get_latest_event(
            session,
            object_type=CanonicalObjectType.rule_version.value,
            object_id=version_uuid,
        )
        return self._build_rule_version_view(rule_version=rule_version, rule=rule, latest_event=latest_event)

    async def get_rule_version_lifecycle(self, *, rule_version_id: str | UUID) -> LifecycleView:
        async with self._session_scope_factory() as session:
            return await self.get_rule_version_lifecycle_in_session(session, rule_version_id=rule_version_id)

    async def list_rule_version_history(self, *, rule_version_id: str | UUID) -> list[dict[str, Any]]:
        async with self._session_scope_factory() as session:
            version_uuid = UUID(str(rule_version_id))
            events = (
                await session.execute(
                    select(LifecycleEvent)
                    .where(LifecycleEvent.object_type == CanonicalObjectType.rule_version.value)
                    .where(LifecycleEvent.object_id == version_uuid)
                    .order_by(LifecycleEvent.occurred_at.asc(), LifecycleEvent.event_id.asc())
                )
            ).scalars().all()
            items: list[dict[str, Any]] = []
            for event in events:
                meta = self._event_metadata(event)
                items.append(
                    {
                        "event_id": str(event.event_id),
                        "canonical_state": event.to_state,
                        "display_state": meta.get("display_state"),
                        "display_label": meta.get("display_label"),
                        "reason_code": event.reason_code,
                        "reason": event.reason_text,
                        "actor_type": event.actor_type,
                        "actor_id": event.actor_id,
                        "correlation_id": event.correlation_id,
                        "occurred_at": event.occurred_at.isoformat(),
                        "metadata": meta,
                    }
                )
            return items

    async def transition_candidate(
        self,
        *,
        candidate_id: UUID,
        target_state: str,
        actor_type: str,
        actor_id: str,
        reason: str | None,
        correlation_id: str,
    ) -> LifecycleView:
        self._ensure_reason(reason)
        if target_state != "待审核":
            raise RuleLifecycleTransitionBlockedError("当前阶段只支持把候选规则提交到待审核。")
        await self._ensure_gate()
        async with self._session_scope_factory() as session:
            return await self.transition_candidate_in_session(
                session,
                candidate_id=candidate_id,
                target_state=target_state,
                actor_type=actor_type,
                actor_id=actor_id,
                reason=reason,
                correlation_id=correlation_id,
            )

    async def transition_candidate_in_session(
        self,
        session,
        *,
        candidate_id: UUID,
        target_state: str,
        actor_type: str,
        actor_id: str,
        reason: str | None,
        correlation_id: str,
    ) -> LifecycleView:
        candidate = await self._get_candidate(session, candidate_id=candidate_id)
        existing = await self._get_latest_event(
            session,
            object_type=CanonicalObjectType.rule_candidate.value,
            object_id=candidate.rule_candidate_id,
            correlation_id=correlation_id,
        )
        if existing is not None:
            return self._build_candidate_view(candidate=candidate)
        if str(candidate.review_state) != "extracted":
            raise RuleLifecycleTransitionBlockedError("只有候选状态的规则才能进入待审核。")
        with canonical_write_scope("rule_version", self.service_name):
            candidate.review_state = "manual_review"
            candidate.updated_by = actor_id
            candidate.updated_at = datetime.now(UTC)
            await self._append_event(
                session,
                object_type=CanonicalObjectType.rule_candidate.value,
                object_id=candidate.rule_candidate_id,
                from_state="extracted",
                to_state="manual_review",
                actor_type=actor_type,
                actor_id=actor_id,
                reason_code="submitted_for_review",
                reason_text=reason,
                before_json={"review_state": "extracted"},
                after_json={
                    "review_state": "manual_review",
                    **self._rule_lifecycle_payload(
                        display_state="待审核",
                        display_label="待审核",
                        entry_point="rule_lifecycle.transition_candidate",
                    ),
                },
                correlation_id=correlation_id,
            )
            await session.refresh(candidate)
        return self._build_candidate_view(candidate=candidate)

    async def approve_candidate(
        self,
        *,
        candidate_id: UUID,
        actor_id: str,
        reason: str | None,
        correlation_id: str,
    ) -> LifecycleView:
        self._ensure_reason(reason)
        await self._ensure_gate()
        async with self._session_scope_factory() as session:
            return await self.approve_candidate_in_session(
                session,
                candidate_id=candidate_id,
                actor_id=actor_id,
                reason=reason,
                correlation_id=correlation_id,
            )

    async def approve_candidate_in_session(
        self,
        session,
        *,
        candidate_id: UUID,
        actor_id: str,
        reason: str | None,
        correlation_id: str,
    ) -> LifecycleView:
        candidate = await self._get_candidate(session, candidate_id=candidate_id)
        existing = await self._get_latest_event(
            session,
            object_type=CanonicalObjectType.rule_candidate.value,
            object_id=candidate.rule_candidate_id,
            correlation_id=correlation_id,
        )
        if existing is None:
            if str(candidate.review_state) not in {"manual_review", "auto_review"}:
                raise RuleLifecycleTransitionBlockedError("候选规则必须先进入待审核，不能跳过审核直接批准。")
            payload = candidate.canonical_payload or {}
            with canonical_write_scope("rule_version", self.service_name):
                await self._governance_service.approve_candidate(
                    session,
                    candidate=candidate,
                    actor_id=actor_id,
                    reason=reason,
                    correlation_id=correlation_id,
                    title=str(payload.get("title") or f"candidate-{candidate.candidate_index}"),
                    description=str(payload.get("description")) if payload.get("description") is not None else None,
                    schema_version="rule_v1",
                    instrument_scope={"instrument_focus": payload.get("instrument_focus") or []},
                    condition_json=payload.get("condition") or {},
                    action_json=payload.get("action") or {},
                    parameter_json={
                        "timeframe": payload.get("timeframe"),
                        "holding_period": payload.get("holding_period"),
                        "risk_controls": payload.get("risk_controls") or [],
                        "market_state_applicability": payload.get("market_state_applicability") or {},
                    },
                    data_dependencies=candidate.data_dependencies or {},
                    evidence_json=candidate.evidence_json or {},
                    after_review_snapshot={
                        "automatic_review_status": "needs_human_review",
                        "reason": reason,
                        "review_state": "approved",
                    },
                )
        linked = await self._governance_service._repository.get_linked_rule_version_by_candidate(  # noqa: SLF001
            session,
            candidate_id=candidate.rule_candidate_id,
        )
        if linked is None:
            raise RuleLifecycleError("approved candidate has no linked rule version")
        await session.refresh(linked)
        rule = await self._get_rule(session, rule_id=linked.rule_id)
        latest_event = await self._get_latest_event(
            session,
            object_type=CanonicalObjectType.rule_version.value,
            object_id=linked.rule_version_id,
        )
        return self._build_rule_version_view(rule_version=linked, rule=rule, latest_event=latest_event)

    async def reject_candidate(
        self,
        *,
        candidate_id: UUID,
        actor_type: str,
        actor_id: str,
        reason: str | None,
        correlation_id: str,
    ) -> LifecycleView:
        self._ensure_reason(reason)
        await self._ensure_gate()
        async with self._session_scope_factory() as session:
            return await self.reject_candidate_in_session(
                session,
                candidate_id=candidate_id,
                actor_type=actor_type,
                actor_id=actor_id,
                reason=reason,
                correlation_id=correlation_id,
            )

    async def reject_candidate_in_session(
        self,
        session,
        *,
        candidate_id: UUID,
        actor_type: str,
        actor_id: str,
        reason: str | None,
        correlation_id: str,
    ) -> LifecycleView:
        candidate = await self._get_candidate(session, candidate_id=candidate_id)
        existing = await self._get_latest_event(
            session,
            object_type=CanonicalObjectType.rule_candidate.value,
            object_id=candidate.rule_candidate_id,
            correlation_id=correlation_id,
        )
        if existing is not None:
            return self._build_candidate_view(candidate=candidate)
        if str(candidate.review_state) not in {"manual_review", "auto_review"}:
            raise RuleLifecycleTransitionBlockedError("只有待审核的候选规则才能驳回。")
        with canonical_write_scope("rule_version", self.service_name):
            candidate.review_state = "rejected"
            candidate.updated_by = actor_id
            candidate.updated_at = datetime.now(UTC)
            await self._append_event(
                session,
                object_type=CanonicalObjectType.rule_candidate.value,
                object_id=candidate.rule_candidate_id,
                from_state="manual_review",
                to_state="rejected",
                actor_type=actor_type,
                actor_id=actor_id,
                reason_code="human_rejected",
                reason_text=reason,
                before_json={"review_state": "manual_review"},
                after_json={"review_state": "rejected"},
                correlation_id=correlation_id,
            )
            await session.refresh(candidate)
        return self._build_candidate_view(candidate=candidate)

    async def transition_rule_version(
        self,
        *,
        rule_version_id: str | UUID,
        target_state: str,
        actor_type: str,
        actor_id: str,
        reason: str | None,
        correlation_id: str,
        expected_updated_at: datetime | None = None,
        evidence_refs: list[str] | None = None,
    ) -> LifecycleView:
        self._ensure_reason(reason)
        await self._ensure_gate()
        async with self._session_scope_factory() as session:
            return await self.transition_rule_version_in_session(
                session,
                rule_version_id=rule_version_id,
                target_state=target_state,
                actor_type=actor_type,
                actor_id=actor_id,
                reason=reason,
                correlation_id=correlation_id,
                expected_updated_at=expected_updated_at,
                evidence_refs=evidence_refs,
            )

    async def transition_rule_version_in_session(
        self,
        session,
        *,
        rule_version_id: str | UUID,
        target_state: str,
        actor_type: str,
        actor_id: str,
        reason: str | None,
        correlation_id: str,
        expected_updated_at: datetime | None = None,
        evidence_refs: list[str] | None = None,
    ) -> LifecycleView:
        version_uuid = UUID(str(rule_version_id))
        rule_version = await self._get_rule_version(session, rule_version_id=version_uuid)
        rule = await self._get_rule(session, rule_id=rule_version.rule_id)
        existing = await self._get_latest_event(
            session,
            object_type=CanonicalObjectType.rule_version.value,
            object_id=rule_version.rule_version_id,
            correlation_id=correlation_id,
        )
        if existing is not None:
            latest_event = await self._get_latest_event(
                session,
                object_type=CanonicalObjectType.rule_version.value,
                object_id=rule_version.rule_version_id,
            )
            return self._build_rule_version_view(rule_version=rule_version, rule=rule, latest_event=latest_event)
        self._ensure_expected_timestamp(rule_version.updated_at, expected_updated_at)

        latest_event = await self._get_latest_event(
            session,
            object_type=CanonicalObjectType.rule_version.value,
            object_id=rule_version.rule_version_id,
        )
        current_view = self._build_rule_version_view(rule_version=rule_version, rule=rule, latest_event=latest_event)

        with canonical_write_scope("rule_version", self.service_name):
            if target_state == "待回测":
                if current_view.display_label != "已批准" or str(rule_version.lifecycle_state) != FormalLifecycleState.draft.value:
                    raise RuleLifecycleTransitionBlockedError("只有已批准的规则才能进入待回测。")
                lifecycle_payload = self._rule_lifecycle_payload(
                    display_state="待回测",
                    display_label="待回测",
                    evidence_refs=evidence_refs,
                    entry_point="rule_lifecycle.transition_rule_version",
                )
                rule_version.evidence_json = {**(rule_version.evidence_json or {}), **lifecycle_payload}
                rule_version.updated_by = actor_id
                rule_version.updated_at = datetime.now(UTC)
                await self._append_event(
                    session,
                    object_type=CanonicalObjectType.rule_version.value,
                    object_id=rule_version.rule_version_id,
                    from_state=FormalLifecycleState.draft.value,
                    to_state=FormalLifecycleState.draft.value,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    reason_code="queued_for_backtest",
                    reason_text=reason,
                    before_json={"lifecycle_state": FormalLifecycleState.draft.value},
                    after_json={"lifecycle_state": FormalLifecycleState.draft.value, **lifecycle_payload},
                    correlation_id=correlation_id,
                )
            elif target_state == "验证中":
                if current_view.display_label != "待回测" or str(rule_version.lifecycle_state) != FormalLifecycleState.draft.value:
                    raise RuleLifecycleTransitionBlockedError("只有待回测的规则才能进入验证中。")
                lifecycle_payload = self._rule_lifecycle_payload(
                    display_state="验证中",
                    display_label="验证中",
                    evidence_refs=evidence_refs,
                    entry_point="rule_lifecycle.transition_rule_version",
                )
                rule_version.lifecycle_state = FormalLifecycleState.in_review
                rule_version.evidence_json = {**(rule_version.evidence_json or {}), **lifecycle_payload}
                rule_version.updated_by = actor_id
                rule_version.updated_at = datetime.now(UTC)
                await self._append_event(
                    session,
                    object_type=CanonicalObjectType.rule_version.value,
                    object_id=rule_version.rule_version_id,
                    from_state=FormalLifecycleState.draft.value,
                    to_state=FormalLifecycleState.in_review.value,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    reason_code="started_validation",
                    reason_text=reason,
                    before_json={"lifecycle_state": FormalLifecycleState.draft.value},
                    after_json={"lifecycle_state": FormalLifecycleState.in_review.value, **lifecycle_payload},
                    correlation_id=correlation_id,
                )
            elif target_state in {"可用", "限定使用"}:
                if current_view.display_label not in {"验证中", "限定使用", "可用"}:
                    raise RuleLifecycleTransitionBlockedError("只有验证中的规则才能变更为可用或限定使用。")
                if not evidence_refs:
                    raise RuleLifecycleTransitionBlockedError("缺少回测或人工验证证据，不能进入正式可用状态。")
                restriction_level = "limited" if target_state == "限定使用" else "none"
                restriction_message = reason if target_state == "限定使用" else None
                lifecycle_payload = self._rule_lifecycle_payload(
                    display_state=target_state,
                    display_label=target_state,
                    restriction_level=restriction_level,
                    restriction_message=restriction_message,
                    evidence_refs=evidence_refs,
                    entry_point="rule_lifecycle.transition_rule_version",
                )
                prior_state = str(rule_version.lifecycle_state)
                rule_version.lifecycle_state = FormalLifecycleState.published
                rule_version.evidence_json = {**(rule_version.evidence_json or {}), **lifecycle_payload}
                rule_version.updated_by = actor_id
                rule_version.updated_at = datetime.now(UTC)
                if rule is not None:
                    rule.current_published_version_id = None if target_state == "限定使用" else rule_version.rule_version_id
                    rule.updated_by = actor_id
                    rule.updated_at = datetime.now(UTC)
                await self._append_event(
                    session,
                    object_type=CanonicalObjectType.rule_version.value,
                    object_id=rule_version.rule_version_id,
                    from_state=prior_state,
                    to_state=FormalLifecycleState.published.value,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    reason_code="marked_limited_use" if target_state == "限定使用" else "marked_usable",
                    reason_text=reason,
                    before_json={"lifecycle_state": prior_state},
                    after_json={"lifecycle_state": FormalLifecycleState.published.value, **lifecycle_payload},
                    correlation_id=correlation_id,
                )
            elif target_state == "已停用":
                if current_view.display_label not in {"已批准", "待回测", "验证中", "可用", "限定使用"}:
                    raise RuleLifecycleTransitionBlockedError("当前状态不支持停用。")
                lifecycle_payload = self._rule_lifecycle_payload(
                    display_state="已停用",
                    display_label="已停用",
                    evidence_refs=evidence_refs,
                    entry_point="rule_lifecycle.transition_rule_version",
                )
                prior_state = str(rule_version.lifecycle_state)
                rule_version.lifecycle_state = FormalLifecycleState.archived
                rule_version.evidence_json = {**(rule_version.evidence_json or {}), **lifecycle_payload}
                rule_version.updated_by = actor_id
                rule_version.updated_at = datetime.now(UTC)
                rule_version.superseded_at = datetime.now(UTC)
                if rule is not None and rule.current_published_version_id == rule_version.rule_version_id:
                    rule.current_published_version_id = None
                    rule.updated_by = actor_id
                    rule.updated_at = datetime.now(UTC)
                await self._append_event(
                    session,
                    object_type=CanonicalObjectType.rule_version.value,
                    object_id=rule_version.rule_version_id,
                    from_state=prior_state,
                    to_state=FormalLifecycleState.archived.value,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    reason_code="archived_by_operator",
                    reason_text=reason,
                    before_json={"lifecycle_state": prior_state},
                    after_json={"lifecycle_state": FormalLifecycleState.archived.value, **lifecycle_payload},
                    correlation_id=correlation_id,
                )
            else:
                raise RuleLifecycleTransitionBlockedError(f"不支持的目标状态：{target_state}")

        await session.refresh(rule_version)
        latest_event = await self._get_latest_event(
            session,
            object_type=CanonicalObjectType.rule_version.value,
            object_id=rule_version.rule_version_id,
        )
        return self._build_rule_version_view(rule_version=rule_version, rule=rule, latest_event=latest_event)
