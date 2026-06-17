from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from src.common.stage2_writer_routing import canonical_write_scope
from src.db.repositories.rule_review_repository import RuleReviewBundle, RuleReviewRepository
from src.domain.enums import CanonicalObjectType
from src.models.stage2_canonical import LifecycleEvent
from src.services.rule_governance_service import CandidateGovernanceAssessment, RuleGovernanceGateError, RuleGovernanceService
from src.services.rule_lifecycle_service import (
    LifecycleView,
    RuleLifecycleError,
    RuleLifecycleService,
    RuleLifecycleTransitionBlockedError,
)
from src.services.stage3_single_article_service import (
    build_article_structure_provenance,
    resolve_summary_provenance,
)


AutomaticReviewStatus = Literal["auto_pass", "recommend_pass", "manual_review", "not_backtestable", "recommend_reject"]
ReviewActionKey = Literal["edit", "approve", "approve_after_edit", "merge", "hold", "reject"]
BatchActionKey = Literal["approve_low_risk", "reject_invalid"]


class RuleReviewError(RuntimeError):
    pass


class RuleReviewTransitionBlockedError(RuleReviewError):
    pass


@dataclass(frozen=True)
class AutomaticReviewDecision:
    status: AutomaticReviewStatus
    label: str
    risk_level: str
    reasons: list[str]
    requires_human_review: bool
    blocked_reason: str | None = None


@dataclass(frozen=True)
class ReviewCandidateListItem:
    candidate_id: str
    title: str
    source_article_title: str
    automatic_review: AutomaticReviewDecision
    current_review_state: str
    lifecycle_state: str
    allowed_actions: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ReviewActionResult:
    candidate_id: str
    current_review_state: str
    current_lifecycle_state: str | None
    rule_version_id: str | None
    last_action: str
    allowed_actions: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ReviewBatchResult:
    processed_count: int
    skipped_count: int
    items: list[dict[str, Any]] = field(default_factory=list)


class RuleReviewService:
    service_name = "rule-review-service"

    def __init__(
        self,
        *,
        session_scope_factory,
        repository: RuleReviewRepository | None = None,
        regression_service: Any | None = None,
        governance_service: RuleGovernanceService | None = None,
        lifecycle_service: RuleLifecycleService | None = None,
    ) -> None:
        self._session_scope_factory = session_scope_factory
        self._repository = repository or RuleReviewRepository()
        self._governance_service = governance_service or RuleGovernanceService(
            regression_service=regression_service,
        )
        self._lifecycle_service = lifecycle_service or RuleLifecycleService(
            session_scope_factory=session_scope_factory,
            regression_service=regression_service,
            governance_service=self._governance_service,
        )

    async def _ensure_gate(self) -> None:
        try:
            await self._governance_service.ensure_fixed_set_gate()
        except RuleGovernanceGateError as exc:
            raise RuleReviewTransitionBlockedError(str(exc)) from exc

    @staticmethod
    def _merge_workbench_metadata(candidate, *, actor_id: str, patch: dict[str, Any]) -> None:
        evidence_json = candidate.evidence_json if isinstance(candidate.evidence_json, dict) else {}
        workbench = evidence_json.get("review_workbench") if isinstance(evidence_json.get("review_workbench"), dict) else {}
        updated = {
            **evidence_json,
            "review_workbench": {
                **workbench,
                **patch,
                "updated_at": datetime.now(UTC).isoformat(),
                "updated_by": actor_id,
            },
        }
        candidate.evidence_json = updated

    @staticmethod
    def _current_candidate_label(review_state: str) -> str:
        mapping = {
            "extracted": "候选",
            "auto_review": "待审核",
            "manual_review": "待审核",
            "approved": "已批准",
            "rejected": "已拒绝",
            "superseded": "已替代",
        }
        return mapping.get(review_state, review_state)

    @staticmethod
    def _bool_contains_kaipan(values: Any) -> bool:
        if isinstance(values, str):
            return "kaipan" in values.lower()
        if isinstance(values, list):
            return any(RuleReviewService._bool_contains_kaipan(item) for item in values)
        if isinstance(values, dict):
            return any(RuleReviewService._bool_contains_kaipan(item) for item in values.values())
        return False

    @staticmethod
    def _collect_allowed_actions(assessment: CandidateGovernanceAssessment, automatic_review: AutomaticReviewDecision) -> list[dict[str, str]]:
        actions: list[dict[str, str]] = [{"key": "edit", "label": "编辑"}, {"key": "hold", "label": "搁置"}, {"key": "reject", "label": "驳回"}]
        if assessment.exact_duplicate_of_rule_version_id is not None:
            actions.append({"key": "merge", "label": "合并"})
            return actions
        if automatic_review.status in {"auto_pass", "recommend_pass", "manual_review"}:
            actions.append({"key": "approve", "label": "批准"})
            actions.append({"key": "approve_after_edit", "label": "编辑后批准"})
        return actions

    def _classify_candidate(
        self,
        *,
        candidate,
        assessment: CandidateGovernanceAssessment,
    ) -> AutomaticReviewDecision:
        payload = candidate.canonical_payload or {}
        quantification = payload.get("quantification") or {}
        condition = payload.get("condition") or {}
        action = payload.get("action") or {}
        evidence = payload.get("evidence") or []
        market_state = payload.get("market_state_applicability") or {}
        workbench = (candidate.evidence_json or {}).get("review_workbench") if isinstance(candidate.evidence_json, dict) else {}

        missing_reasons: list[str] = []
        if not evidence:
            missing_reasons.append("缺少原文证据")
        if not condition:
            missing_reasons.append("缺少规则条件")
        if not action:
            missing_reasons.append("缺少规则动作")
        if missing_reasons:
            return AutomaticReviewDecision(
                status="recommend_reject",
                label="建议驳回",
                risk_level="high",
                reasons=missing_reasons,
                requires_human_review=True,
            )

        if str(candidate.backtestability_status) != "executable":
            reasons = ["当前规则还不能进入固定历史回测。"]
            if quantification.get("missing_fields"):
                reasons.append("量化字段仍不完整")
            return AutomaticReviewDecision(
                status="not_backtestable",
                label="不可回测",
                risk_level="high",
                reasons=reasons,
                requires_human_review=True,
                blocked_reason="backtestability_unavailable",
            )

        manual_reasons: list[str] = []
        if quantification.get("manual_review_required"):
            manual_reasons.append("量化条件仍需人工确认")
        if quantification.get("ambiguous_terms"):
            manual_reasons.append("存在模糊词")
        if candidate.missing_fields:
            manual_reasons.append("仍有缺失字段")
        if candidate.inferred_fields:
            manual_reasons.append("包含推断内容")
        if self._bool_contains_kaipan(candidate.data_dependencies or {}):
            manual_reasons.append("依赖盘前增强数据")
        if (market_state.get("inferred_hypotheses") or []):
            manual_reasons.append("市场状态仍带推断")
        if isinstance(workbench, dict) and workbench.get("edited"):
            manual_reasons.append("已发生人工编辑")
        for related in assessment.related_rules:
            if related.relation == "conflict":
                manual_reasons.append("发现冲突规则")
            elif related.relation in {"parameter_variant", "similar_rule"}:
                manual_reasons.append("发现相近规则，需人工确认")
        if manual_reasons:
            return AutomaticReviewDecision(
                status="manual_review",
                label="需要人工确认",
                risk_level="high" if "发现冲突规则" in manual_reasons else "medium",
                reasons=list(dict.fromkeys(manual_reasons)),
                requires_human_review=True,
            )

        if assessment.exact_duplicate_of_rule_version_id is not None:
            return AutomaticReviewDecision(
                status="recommend_pass",
                label="建议通过",
                risk_level="low",
                reasons=["与既有正式规则完全重复，可复用同一正式生命周期。"],
                requires_human_review=False,
            )

        rule_type = str(payload.get("rule_type") or candidate.rule_type or "")
        action_type = str((payload.get("action") or {}).get("type") or "")
        if rule_type == "entry" or action_type == "enter":
            return AutomaticReviewDecision(
                status="recommend_pass",
                label="建议通过",
                risk_level="low",
                reasons=["证据和量化条件完整，但入场规则仍需人工确认。"],
                requires_human_review=False,
            )

        return AutomaticReviewDecision(
            status="auto_pass",
            label="自动通过",
            risk_level="low",
            reasons=["证据和量化条件完整，可进入待回测边界。"],
            requires_human_review=False,
        )

    async def _get_bundle_and_assessment(self, *, candidate_id: UUID) -> tuple[RuleReviewBundle, CandidateGovernanceAssessment]:
        async with self._session_scope_factory() as session:
            return await self._get_bundle_and_assessment_in_session(session, candidate_id=candidate_id)

    async def _get_bundle_and_assessment_in_session(self, session, *, candidate_id: UUID) -> tuple[RuleReviewBundle, CandidateGovernanceAssessment]:
        bundle = await self._repository.build_bundle(session, candidate_id=candidate_id)
        if bundle is None:
            raise RuleReviewError(f"rule candidate not found: {candidate_id}")
        assessment = await self._governance_service.assess_candidate(session, candidate=bundle.candidate)
        return bundle, assessment

    async def list_candidates(
        self,
        *,
        require_human_review_only: bool = False,
        automatic_review_status: str | None = None,
    ) -> list[ReviewCandidateListItem]:
        async with self._session_scope_factory() as session:
            candidates = await self._repository.list_candidates(session)
            items: list[ReviewCandidateListItem] = []
            for candidate in candidates:
                bundle = await self._repository.build_bundle(session, candidate_id=candidate.rule_candidate_id)
                if bundle is None:
                    continue
                assessment = await self._governance_service.assess_candidate(session, candidate=candidate)
                automatic_review = self._classify_candidate(candidate=candidate, assessment=assessment)
                if require_human_review_only and automatic_review.status != "manual_review":
                    continue
                if automatic_review_status and automatic_review.status != automatic_review_status:
                    continue
                lifecycle = await self._lifecycle_service.get_candidate_lifecycle_in_session(session, candidate_id=candidate.rule_candidate_id)
                items.append(
                    ReviewCandidateListItem(
                        candidate_id=str(candidate.rule_candidate_id),
                        title=str((candidate.canonical_payload or {}).get("title") or f"candidate-{candidate.candidate_index}"),
                        source_article_title=bundle.article.title,
                        automatic_review=automatic_review,
                        current_review_state=self._current_candidate_label(str(candidate.review_state)),
                        lifecycle_state=lifecycle.display_label or lifecycle.display_state or lifecycle.canonical_state,
                        allowed_actions=self._collect_allowed_actions(assessment, automatic_review),
                    )
                )
            return items

    async def get_candidate_detail(self, *, candidate_id: UUID | str) -> dict[str, Any]:
        candidate_uuid = UUID(str(candidate_id))
        async with self._session_scope_factory() as session:
            bundle, assessment = await self._get_bundle_and_assessment_in_session(session, candidate_id=candidate_uuid)
            automatic_review = self._classify_candidate(candidate=bundle.candidate, assessment=assessment)
            summary = resolve_summary_provenance(article=bundle.article, revision=bundle.revision)
            candidate_lifecycle = await self._lifecycle_service.get_candidate_lifecycle_in_session(session, candidate_id=candidate_uuid)
            version_lifecycle: LifecycleView | None = None
            if bundle.rule_version is not None:
                version_lifecycle = await self._lifecycle_service.get_rule_version_lifecycle_in_session(session, rule_version_id=bundle.rule_version.rule_version_id)
            history = []
            for event in await self._repository.list_candidate_events(session, candidate_id=candidate_uuid):
                history.append(
                    {
                        "event_id": str(event.event_id),
                        "reason_code": event.reason_code,
                        "reason_text": event.reason_text,
                        "actor_type": event.actor_type,
                        "actor_id": event.actor_id,
                        "correlation_id": event.correlation_id,
                        "from_state": event.from_state,
                        "to_state": event.to_state,
                        "occurred_at": event.occurred_at.isoformat(),
                    }
                )
            if bundle.rule_version is not None:
                for event in await self._repository.list_rule_version_events(session, rule_version_id=bundle.rule_version.rule_version_id):
                    history.append(
                        {
                            "event_id": str(event.event_id),
                            "reason_code": event.reason_code,
                            "reason_text": event.reason_text,
                            "actor_type": event.actor_type,
                            "actor_id": event.actor_id,
                            "correlation_id": event.correlation_id,
                            "from_state": event.from_state,
                            "to_state": event.to_state,
                            "occurred_at": event.occurred_at.isoformat(),
                        }
                    )
            history.sort(key=lambda item: item["occurred_at"])
            return {
                "candidate_id": str(bundle.candidate.rule_candidate_id),
                "title": str((bundle.candidate.canonical_payload or {}).get("title") or f"candidate-{bundle.candidate.candidate_index}"),
                "source_article": {
                    "article_id": str(bundle.article.id),
                    "title": bundle.article.title,
                    "source_url": bundle.article.source_url,
                    "summary": summary.summary,
                    "summary_status": "ready" if summary.available else "unavailable",
                    "summary_reason": summary.reason,
                    "published_at": bundle.article.published_at.isoformat() if bundle.article.published_at is not None else None,
                    "article_revision_id": str(bundle.revision.article_revision_id),
                },
                "article_structure_provenance": asdict(
                    build_article_structure_provenance(structure=bundle.structure, prompt_run=bundle.prompt_run)
                ),
                "automatic_review": asdict(automatic_review),
                "current_review_state": self._current_candidate_label(str(bundle.candidate.review_state)),
                "current_lifecycle_state": (
                    version_lifecycle.display_label
                    if version_lifecycle is not None
                    else candidate_lifecycle.display_label or candidate_lifecycle.display_state or candidate_lifecycle.canonical_state
                ),
                "missing_fields": list((bundle.candidate.missing_fields or {}).keys()),
                "data_dependencies": list((bundle.candidate.data_dependencies or {}).get("required") or []),
                "evidence": bundle.candidate.evidence_json or {},
                "governance": {
                    "fingerprint": {
                        "algorithm_version": assessment.fingerprint.algorithm_version,
                        "exact_fingerprint": assessment.fingerprint.exact_fingerprint,
                        "family_fingerprint": assessment.fingerprint.family_fingerprint,
                        "family_key": assessment.family_key,
                    },
                    "exact_duplicate_of_rule_version_id": assessment.exact_duplicate_of_rule_version_id,
                    "eligible_for_formal_version": assessment.eligible_for_formal_version,
                    "eligible_for_backtest": assessment.eligible_for_backtest,
                    "related_rules": [
                        {
                            "relation": item.relation,
                            "rule_version_id": item.rule_version_id,
                            "rule_id": item.rule_id,
                            "family_id": item.family_id,
                            "title": item.title,
                            "parameter_differences": item.parameter_differences,
                            "conflict_reasons": item.conflict_reasons,
                        }
                        for item in assessment.related_rules
                    ],
                },
                "lifecycle": {
                    "candidate": {
                        "display_label": candidate_lifecycle.display_label,
                        "canonical_state": candidate_lifecycle.canonical_state,
                    },
                    "formal": None
                    if version_lifecycle is None
                    else {
                        "display_label": version_lifecycle.display_label,
                        "canonical_state": version_lifecycle.canonical_state,
                        "allowed_next_actions": [
                            {"key": item.key, "label": item.label}
                            for item in version_lifecycle.allowed_next_actions
                        ],
                    },
                },
                "rule_version_id": str(bundle.rule_version.rule_version_id) if bundle.rule_version is not None else None,
                "history": history,
                "allowed_actions": self._collect_allowed_actions(assessment, automatic_review),
            }

    async def _append_candidate_event(
        self,
        *,
        session,
        candidate,
        from_state: str,
        to_state: str,
        actor_type: str,
        actor_id: str,
        reason_code: str,
        reason_text: str,
        before_json: dict[str, Any] | None,
        after_json: dict[str, Any] | None,
        correlation_id: str,
    ) -> None:
        session.add(
            LifecycleEvent(
                object_type=CanonicalObjectType.rule_candidate.value,
                object_id=candidate.rule_candidate_id,
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

    async def _ensure_under_review(self, *, candidate_id: UUID, actor_type: str, actor_id: str, reason: str, correlation_id: str, session=None) -> None:
        if session is None:
            lifecycle = await self._lifecycle_service.get_candidate_lifecycle(candidate_id=candidate_id)
        else:
            lifecycle = await self._lifecycle_service.get_candidate_lifecycle_in_session(session, candidate_id=candidate_id)
        if lifecycle.display_label == "候选":
            if session is None:
                await self._lifecycle_service.transition_candidate(
                    candidate_id=candidate_id,
                    target_state="待审核",
                    actor_type=actor_type,
                    actor_id=actor_id,
                    reason=reason,
                    correlation_id=f"{correlation_id}:prepare",
                )
            else:
                await self._lifecycle_service.transition_candidate_in_session(
                    session,
                    candidate_id=candidate_id,
                    target_state="待审核",
                    actor_type=actor_type,
                    actor_id=actor_id,
                    reason=reason,
                    correlation_id=f"{correlation_id}:prepare",
                )

    async def apply_action(
        self,
        *,
        candidate_id: UUID | str,
        action: ReviewActionKey,
        actor_type: str,
        actor_id: str,
        reason: str,
        correlation_id: str,
        edits: dict[str, Any] | None = None,
    ) -> ReviewActionResult:
        if not reason.strip():
            raise RuleReviewTransitionBlockedError("必须提供审核原因。")
        await self._ensure_gate()
        candidate_uuid = UUID(str(candidate_id))
        async with self._session_scope_factory() as session:
            result = await self._apply_action_in_session(
                session,
                candidate_id=candidate_uuid,
                action=action,
                actor_type=actor_type,
                actor_id=actor_id,
                reason=reason,
                correlation_id=correlation_id,
                edits=edits or {},
            )
        detail = await self.get_candidate_detail(candidate_id=candidate_uuid)
        return ReviewActionResult(
            candidate_id=result.candidate_id,
            current_review_state=detail["current_review_state"],
            current_lifecycle_state=detail["current_lifecycle_state"],
            rule_version_id=detail["rule_version_id"],
            last_action=result.last_action,
            allowed_actions=detail["allowed_actions"],
        )

    async def _apply_action_in_session(
        self,
        session,
        *,
        candidate_id: UUID,
        action: ReviewActionKey,
        actor_type: str,
        actor_id: str,
        reason: str,
        correlation_id: str,
        edits: dict[str, Any],
    ) -> ReviewActionResult:
        if action in {"approve", "approve_after_edit", "merge", "reject"}:
            await self._ensure_under_review(
                candidate_id=candidate_id,
                actor_type=actor_type,
                actor_id=actor_id,
                reason=reason,
                correlation_id=correlation_id,
                session=session,
            )

        if action == "edit":
            await self._apply_edit_in_session(
                session,
                candidate_id=candidate_id,
                actor_type=actor_type,
                actor_id=actor_id,
                reason=reason,
                correlation_id=correlation_id,
                edits=edits,
            )
            return ReviewActionResult(
                candidate_id=str(candidate_id),
                current_review_state="待审核",
                current_lifecycle_state="待审核",
                rule_version_id=None,
                last_action="edit",
            )

        if action == "approve_after_edit":
            await self._apply_edit_in_session(
                session,
                candidate_id=candidate_id,
                actor_type=actor_type,
                actor_id=actor_id,
                reason=reason,
                correlation_id=f"{correlation_id}:edit",
                edits=edits,
            )
            action = "approve"

        if action == "hold":
            bundle = await self._repository.build_bundle(session, candidate_id=candidate_id)
            if bundle is None:
                raise RuleReviewError(f"rule candidate not found: {candidate_id}")
            with canonical_write_scope("rule_version", self.service_name):
                self._merge_workbench_metadata(
                    bundle.candidate,
                    actor_id=actor_id,
                    patch={"hold": True, "hold_reason": reason},
                )
                bundle.candidate.updated_by = actor_id
                bundle.candidate.updated_at = datetime.now(UTC)
                await self._append_candidate_event(
                    session=session,
                    candidate=bundle.candidate,
                    from_state=str(bundle.candidate.review_state),
                    to_state=str(bundle.candidate.review_state),
                    actor_type=actor_type,
                    actor_id=actor_id,
                    reason_code="human_hold",
                    reason_text=reason,
                    before_json={"review_state": str(bundle.candidate.review_state)},
                    after_json={"review_state": str(bundle.candidate.review_state), "hold": True},
                    correlation_id=correlation_id,
                )
            return ReviewActionResult(
                candidate_id=str(candidate_id),
                current_review_state=self._current_candidate_label(str(bundle.candidate.review_state)),
                current_lifecycle_state=(await self._lifecycle_service.get_candidate_lifecycle_in_session(session, candidate_id=candidate_id)).display_label,
                rule_version_id=str(bundle.rule_version.rule_version_id) if bundle.rule_version is not None else None,
                last_action="hold",
            )

        if action == "reject":
            try:
                view = await self._lifecycle_service.reject_candidate_in_session(
                    session,
                    candidate_id=candidate_id,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    reason=reason,
                    correlation_id=correlation_id,
                )
            except RuleLifecycleTransitionBlockedError as exc:
                raise RuleReviewTransitionBlockedError(str(exc)) from exc
            return ReviewActionResult(
                candidate_id=str(candidate_id),
                current_review_state="已拒绝",
                current_lifecycle_state=view.display_label,
                rule_version_id=None,
                last_action="reject",
            )

        bundle, assessment = await self._get_bundle_and_assessment_in_session(session, candidate_id=candidate_id)
        result_action = action
        if action == "merge":
            if assessment.exact_duplicate_of_rule_version_id is None:
                raise RuleReviewTransitionBlockedError("只有完全重复的候选规则才能执行合并。")
            with canonical_write_scope("rule_version", self.service_name):
                await self._append_candidate_event(
                    session=session,
                    candidate=bundle.candidate,
                    from_state=str(bundle.candidate.review_state),
                    to_state=str(bundle.candidate.review_state),
                    actor_type=actor_type,
                    actor_id=actor_id,
                    reason_code="human_merge",
                    reason_text=reason,
                    before_json={"review_state": str(bundle.candidate.review_state)},
                    after_json={"review_state": str(bundle.candidate.review_state), "merge_target_rule_version_id": assessment.exact_duplicate_of_rule_version_id},
                    correlation_id=f"{correlation_id}:merge",
                )
            action = "approve"
            result_action = "merge"

        if action == "approve":
            try:
                view = await self._lifecycle_service.approve_candidate_in_session(
                    session,
                    candidate_id=candidate_id,
                    actor_id=actor_id,
                    reason=reason,
                    correlation_id=correlation_id,
                )
            except RuleLifecycleTransitionBlockedError as exc:
                raise RuleReviewTransitionBlockedError(str(exc)) from exc
            return ReviewActionResult(
                candidate_id=str(candidate_id),
                current_review_state="已批准",
                current_lifecycle_state=view.display_label,
                rule_version_id=view.object_id,
                last_action=result_action,
            )

        raise RuleReviewTransitionBlockedError(f"unsupported action: {action}")

    async def _apply_edit(
        self,
        *,
        candidate_id: UUID,
        actor_type: str,
        actor_id: str,
        reason: str,
        correlation_id: str,
        edits: dict[str, Any],
    ) -> None:
        async with self._session_scope_factory() as session:
            await self._apply_edit_in_session(
                session,
                candidate_id=candidate_id,
                actor_type=actor_type,
                actor_id=actor_id,
                reason=reason,
                correlation_id=correlation_id,
                edits=edits,
            )

    async def _apply_edit_in_session(
        self,
        session,
        *,
        candidate_id: UUID,
        actor_type: str,
        actor_id: str,
        reason: str,
        correlation_id: str,
        edits: dict[str, Any],
    ) -> None:
        bundle = await self._repository.build_bundle(session, candidate_id=candidate_id)
        if bundle is None:
            raise RuleReviewError(f"rule candidate not found: {candidate_id}")
        if not edits:
            raise RuleReviewTransitionBlockedError("编辑后批准必须提供修改内容。")
        before_json = {
            "canonical_payload": bundle.candidate.canonical_payload,
            "evidence_json": bundle.candidate.evidence_json,
            "data_dependencies": bundle.candidate.data_dependencies,
        }
        with canonical_write_scope("rule_version", self.service_name):
            if "canonical_payload" in edits:
                bundle.candidate.canonical_payload = edits["canonical_payload"]
            if "data_dependencies" in edits:
                bundle.candidate.data_dependencies = edits["data_dependencies"]
            if "explicit_fields" in edits:
                bundle.candidate.explicit_fields = edits["explicit_fields"]
            if "missing_fields" in edits:
                bundle.candidate.missing_fields = edits["missing_fields"]
            self._merge_workbench_metadata(
                bundle.candidate,
                actor_id=actor_id,
                patch={"edited": True},
            )
            bundle.candidate.updated_by = actor_id
            bundle.candidate.updated_at = datetime.now(UTC)
            await self._append_candidate_event(
                session=session,
                candidate=bundle.candidate,
                from_state=str(bundle.candidate.review_state),
                to_state=str(bundle.candidate.review_state),
                actor_type=actor_type,
                actor_id=actor_id,
                reason_code="human_edited",
                reason_text=reason,
                before_json=before_json,
                after_json={
                    "canonical_payload": bundle.candidate.canonical_payload,
                    "evidence_json": bundle.candidate.evidence_json,
                    "data_dependencies": bundle.candidate.data_dependencies,
                },
                correlation_id=correlation_id,
            )

    async def _after_batch_item_processed(self, **_kwargs: Any) -> None:
        return None

    async def apply_batch_action(
        self,
        *,
        action: BatchActionKey,
        actor_type: str,
        actor_id: str,
        reason: str,
        correlation_id: str,
        candidate_ids: list[UUID | str],
    ) -> ReviewBatchResult:
        await self._ensure_gate()
        if not candidate_ids:
            raise RuleReviewTransitionBlockedError("必须提供候选规则列表。")
        async with self._session_scope_factory() as session:
            prechecked: list[UUID] = []
            for candidate_id in candidate_ids:
                candidate_uuid = UUID(str(candidate_id))
                bundle, assessment = await self._get_bundle_and_assessment_in_session(session, candidate_id=candidate_uuid)
                status = self._classify_candidate(candidate=bundle.candidate, assessment=assessment).status
                if action == "approve_low_risk":
                    if status not in {"auto_pass", "recommend_pass"}:
                        raise RuleReviewTransitionBlockedError("批量通过只允许处理低风险候选规则。")
                elif status not in {"recommend_reject", "not_backtestable"}:
                    raise RuleReviewTransitionBlockedError("批量驳回只允许处理明显无效或不可回测的候选规则。")
                prechecked.append(candidate_uuid)

            items: list[dict[str, Any]] = []
            for index, candidate_uuid in enumerate(prechecked):
                _bundle, current_assessment = await self._get_bundle_and_assessment_in_session(session, candidate_id=candidate_uuid)
                current_status = self._classify_candidate(candidate=_bundle.candidate, assessment=current_assessment).status
                if action == "approve_low_risk" and current_status not in {"auto_pass", "recommend_pass"}:
                    raise RuleReviewTransitionBlockedError("候选规则状态已变化，请刷新后重试批量通过。")
                if action == "reject_invalid" and current_status not in {"recommend_reject", "not_backtestable"}:
                    raise RuleReviewTransitionBlockedError("候选规则状态已变化，请刷新后重试批量驳回。")

                if action == "approve_low_risk":
                    result = await self._apply_action_in_session(
                        session,
                        candidate_id=candidate_uuid,
                        action="approve",
                        actor_type=actor_type,
                        actor_id=actor_id,
                        reason=reason,
                        correlation_id=f"{correlation_id}:{index}",
                        edits={},
                    )
                    if current_assessment.eligible_for_backtest and result.rule_version_id is not None:
                        queued = await self._lifecycle_service.transition_rule_version_in_session(
                            session,
                            rule_version_id=result.rule_version_id,
                            target_state="待回测",
                            actor_type=actor_type,
                            actor_id=actor_id,
                            reason=reason,
                            correlation_id=f"{correlation_id}:{index}:queue-backtest",
                        )
                        result = ReviewActionResult(
                            candidate_id=result.candidate_id,
                            current_review_state=result.current_review_state,
                            current_lifecycle_state=queued.display_label or queued.display_state,
                            rule_version_id=result.rule_version_id,
                            last_action=result.last_action,
                            allowed_actions=[{"key": item.key, "label": item.label} for item in queued.allowed_next_actions],
                        )
                else:
                    result = await self._apply_action_in_session(
                        session,
                        candidate_id=candidate_uuid,
                        action="reject",
                        actor_type=actor_type,
                        actor_id=actor_id,
                        reason=reason,
                        correlation_id=f"{correlation_id}:{index}",
                        edits={},
                    )
                items.append(
                    {
                        "candidate_id": result.candidate_id,
                        "status": "processed",
                        "current_review_state": result.current_review_state,
                        "rule_version_id": result.rule_version_id,
                    }
                )
                await self._after_batch_item_processed(
                    session=session,
                    index=index,
                    result=result,
                    action=action,
                    correlation_id=correlation_id,
                )
        return ReviewBatchResult(
            processed_count=len(items),
            skipped_count=0,
            items=items,
        )
