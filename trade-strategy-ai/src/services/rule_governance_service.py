from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal, TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.rule_governance_repository import RuleGovernanceRepository
from src.models.stage2_canonical import RuleCandidate, RuleVersion

if TYPE_CHECKING:
    pass


FINGERPRINT_ALGORITHM_VERSION = "rule-fingerprint-v1"
RuleRelation = Literal["exact_duplicate", "parameter_variant", "conflict", "similar_rule", "distinct"]


class RuleGovernanceError(RuntimeError):
    pass


class RuleGovernanceGateError(RuleGovernanceError):
    pass


@dataclass(frozen=True)
class RuleFingerprint:
    algorithm_version: str
    exact_fingerprint: str
    family_fingerprint: str


@dataclass(frozen=True)
class RuleComparison:
    relation: RuleRelation
    parameter_differences: dict[str, dict[str, Any]] = field(default_factory=dict)
    conflict_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GovernanceMatch:
    relation: RuleRelation
    rule_version_id: str
    rule_id: str
    family_id: str | None
    title: str
    parameter_differences: dict[str, dict[str, Any]] = field(default_factory=dict)
    conflict_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateGovernanceAssessment:
    fingerprint: RuleFingerprint
    exact_duplicate_of_rule_version_id: str | None
    eligible_for_formal_version: bool
    eligible_for_backtest: bool
    family_key: str
    related_rules: list[GovernanceMatch] = field(default_factory=list)


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(payload: dict[str, Any]) -> str:
    source = {"algorithm_version": FINGERPRINT_ALGORITHM_VERSION, "payload": payload}
    return hashlib.sha256(_stable_json(source).encode("utf-8")).hexdigest()


def _normalize_rule_payload(payload: dict[str, Any]) -> dict[str, Any]:
    condition = payload.get("condition") or {}
    clauses = []
    for clause in condition.get("clauses") or []:
        clauses.append(
            {
                "field": clause.get("field"),
                "operator": clause.get("operator"),
                "value": clause.get("value"),
                "lookback": clause.get("lookback"),
                "unit": clause.get("unit"),
            }
        )
    clauses = sorted(clauses, key=lambda item: _stable_json(item))
    instrument_focus = sorted(str(item) for item in (payload.get("instrument_focus") or []))
    data_dependencies = sorted(str(item) for item in (payload.get("data_dependencies") or []))
    risk_controls = sorted(
        [
            {
                "type": item.get("type"),
                "operator": item.get("operator"),
                "value": item.get("value"),
            }
            if isinstance(item, dict)
            else item
            for item in (payload.get("risk_controls") or [])
        ],
        key=_stable_json,
    )
    market_state = payload.get("market_state_applicability") or {}
    explicit_market_state = sorted(
        [
            {
                "field": item.get("field"),
                "operator": item.get("operator"),
                "value": item.get("value"),
            }
            if isinstance(item, dict)
            else item
            for item in (market_state.get("explicit_conditions") or [])
        ],
        key=_stable_json,
    )
    action = payload.get("action") or {}
    return {
        "rule_type": payload.get("rule_type"),
        "instrument_focus": instrument_focus,
        "timeframe": payload.get("timeframe"),
        "holding_period": payload.get("holding_period"),
        "condition": {
            "logic": condition.get("logic"),
            "clauses": clauses,
        },
        "action": {
            "type": action.get("type"),
            "side": action.get("side"),
            "price_reference": action.get("price_reference"),
        },
        "risk_controls": risk_controls,
        "data_dependencies": data_dependencies,
        "market_state_applicability": {
            "status": market_state.get("status") or "not_declared",
            "explicit_conditions": explicit_market_state,
        },
    }


def _family_shape(normalized: dict[str, Any]) -> dict[str, Any]:
    clauses = []
    for clause in normalized["condition"]["clauses"]:
        clauses.append(
            {
                "field": clause.get("field"),
                "operator": clause.get("operator"),
                "value": "__param__",
                "lookback": "__param__" if clause.get("lookback") is not None else None,
                "unit": clause.get("unit"),
            }
        )
    risk_controls = []
    for item in normalized["risk_controls"]:
        if isinstance(item, dict):
            risk_controls.append(
                {
                    "type": item.get("type"),
                    "operator": item.get("operator"),
                    "value": "__param__" if item.get("value") is not None else None,
                }
            )
        else:
            risk_controls.append(item)
    return {
        **normalized,
        "timeframe": "__param__" if normalized.get("timeframe") is not None else None,
        "holding_period": "__param__" if normalized.get("holding_period") is not None else None,
        "condition": {
            "logic": normalized["condition"].get("logic"),
            "clauses": clauses,
        },
        "risk_controls": risk_controls,
    }


def fingerprint_rule_payload(payload: dict[str, Any]) -> RuleFingerprint:
    normalized = _normalize_rule_payload(payload)
    return RuleFingerprint(
        algorithm_version=FINGERPRINT_ALGORITHM_VERSION,
        exact_fingerprint=_digest(normalized),
        family_fingerprint=_digest(_family_shape(normalized)),
    )


def _parameter_differences(left: dict[str, Any], right: dict[str, Any]) -> dict[str, dict[str, Any]]:
    differences: dict[str, dict[str, Any]] = {}

    if left.get("timeframe") != right.get("timeframe"):
        differences["timeframe"] = {"left": left.get("timeframe"), "right": right.get("timeframe")}
    if left.get("holding_period") != right.get("holding_period"):
        differences["holding_period"] = {"left": left.get("holding_period"), "right": right.get("holding_period")}
    left_clauses = left.get("condition", {}).get("clauses") or []
    right_clauses = right.get("condition", {}).get("clauses") or []
    for index, (left_clause, right_clause) in enumerate(zip(left_clauses, right_clauses, strict=False)):
        if left_clause.get("value") != right_clause.get("value"):
            differences[f"condition.clauses[{index}].value"] = {
                "left": left_clause.get("value"),
                "right": right_clause.get("value"),
            }
        if left_clause.get("lookback") != right_clause.get("lookback"):
            differences[f"condition.clauses[{index}].lookback"] = {
                "left": left_clause.get("lookback"),
                "right": right_clause.get("lookback"),
            }
    return differences


def compare_rule_payloads(left_payload: dict[str, Any], right_payload: dict[str, Any]) -> RuleComparison:
    left_normalized = _normalize_rule_payload(left_payload)
    right_normalized = _normalize_rule_payload(right_payload)
    left_fp = fingerprint_rule_payload(left_payload)
    right_fp = fingerprint_rule_payload(right_payload)

    if left_fp.exact_fingerprint == right_fp.exact_fingerprint:
        return RuleComparison(relation="exact_duplicate")

    conflict_reasons: list[str] = []
    if (
        left_normalized.get("rule_type") == right_normalized.get("rule_type")
        and left_normalized.get("instrument_focus") == right_normalized.get("instrument_focus")
        and left_normalized.get("condition") == right_normalized.get("condition")
        and (left_normalized.get("action") or {}).get("type") == (right_normalized.get("action") or {}).get("type")
        and (left_normalized.get("action") or {}).get("side") != (right_normalized.get("action") or {}).get("side")
    ):
        conflict_reasons.append("action.side")
    if conflict_reasons:
        return RuleComparison(relation="conflict", conflict_reasons=conflict_reasons)

    if left_fp.family_fingerprint == right_fp.family_fingerprint:
        return RuleComparison(
            relation="parameter_variant",
            parameter_differences=_parameter_differences(left_normalized, right_normalized),
        )

    left_fields = {item.get("field") for item in left_normalized.get("condition", {}).get("clauses") or []}
    right_fields = {item.get("field") for item in right_normalized.get("condition", {}).get("clauses") or []}
    if left_fields and left_fields == right_fields and left_normalized.get("rule_type") == right_normalized.get("rule_type"):
        return RuleComparison(relation="similar_rule")

    return RuleComparison(relation="distinct")


class RuleGovernanceService:
    service_name = "rule-governance-service"

    def __init__(
        self,
        *,
        repository: RuleGovernanceRepository | None = None,
        regression_service: Any | None = None,
    ) -> None:
        self._repository = repository or RuleGovernanceRepository()
        self._regression_service = regression_service

    async def ensure_fixed_set_gate(self) -> Any:
        if self._regression_service is None:
            raise RuleGovernanceGateError("fixed-set gate service unavailable")
        result = await self._regression_service.run_fixed_set()
        if result.status != "passed":
            raise RuleGovernanceGateError(
                f"stage3 fixed-set gate failed: {result.semantic_failures or result.validation_failures or result.provider_failures or result.persistence_failures}"
            )
        return result

    async def assess_candidate(
        self,
        session: AsyncSession,
        *,
        candidate: RuleCandidate,
    ) -> CandidateGovernanceAssessment:
        payload = candidate.canonical_payload or {}
        fingerprint = fingerprint_rule_payload(payload)
        rule_versions = await self._repository.list_rule_versions(session)
        related_rules: list[GovernanceMatch] = []
        exact_duplicate_of_rule_version_id: str | None = None

        for rule_version in rule_versions:
            other_payload = {
                "rule_type": rule_version.rule_type,
                "instrument_focus": rule_version.instrument_scope.get("instrument_focus") or [],
                "timeframe": rule_version.parameter_json.get("timeframe"),
                "holding_period": rule_version.parameter_json.get("holding_period"),
                "condition": rule_version.condition_json,
                "action": rule_version.action_json,
                "risk_controls": rule_version.parameter_json.get("risk_controls") or [],
                "data_dependencies": rule_version.data_dependencies.get("required") or [],
                "market_state_applicability": rule_version.parameter_json.get("market_state_applicability") or payload.get("market_state_applicability") or {},
            }
            comparison = compare_rule_payloads(payload, other_payload)
            if comparison.relation == "distinct":
                continue
            family = await self._repository.get_rule_family_by_fingerprint(
                session,
                family_fingerprint=fingerprint.family_fingerprint,
            )
            related_rules.append(
                GovernanceMatch(
                    relation=comparison.relation,
                    rule_version_id=str(rule_version.rule_version_id),
                    rule_id=str(rule_version.rule_id),
                    family_id=str(family.rule_family_id) if family is not None else None,
                    title=rule_version.title,
                    parameter_differences=comparison.parameter_differences,
                    conflict_reasons=comparison.conflict_reasons,
                )
            )
            if comparison.relation == "exact_duplicate" and exact_duplicate_of_rule_version_id is None:
                exact_duplicate_of_rule_version_id = str(rule_version.rule_version_id)

        return CandidateGovernanceAssessment(
            fingerprint=fingerprint,
            exact_duplicate_of_rule_version_id=exact_duplicate_of_rule_version_id,
            eligible_for_formal_version=exact_duplicate_of_rule_version_id is None,
            eligible_for_backtest=exact_duplicate_of_rule_version_id is None,
            family_key=f"family:{fingerprint.family_fingerprint}",
            related_rules=related_rules,
        )

    async def approve_candidate(
        self,
        session: AsyncSession,
        *,
        candidate: RuleCandidate,
        actor_id: str,
        reason: str | None,
        correlation_id: str,
        title: str,
        description: str | None,
        schema_version: str,
        instrument_scope: dict[str, Any],
        condition_json: dict[str, Any],
        action_json: dict[str, Any],
        parameter_json: dict[str, Any],
        data_dependencies: dict[str, Any],
        evidence_json: dict[str, Any],
        after_review_snapshot: dict[str, Any],
    ) -> tuple[RuleVersion, CandidateGovernanceAssessment]:
        raise RuleGovernanceGateError(
            "legacy rule_candidates are read-only audit evidence; use strict executable extraction promotion"
        )
        assessment = await self.assess_candidate(session, candidate=candidate)

        if assessment.exact_duplicate_of_rule_version_id is not None:
            version = await self._repository.get_rule_version(
                session,
                rule_version_id=UUID(assessment.exact_duplicate_of_rule_version_id),
            )
            if version is None:
                raise RuleGovernanceError("duplicate target rule version not found")
            await self._repository.link_candidate_to_existing_rule_version(
                session,
                candidate=candidate,
                rule_version=version,
                actor_id=actor_id,
                reason=reason,
                correlation_id=correlation_id,
                after_review_snapshot={
                    **after_review_snapshot,
                    "governance_relation": "exact_duplicate",
                    "linked_rule_version_id": str(version.rule_version_id),
                },
            )
            family = await self._repository.ensure_family(
                session,
                family_fingerprint=assessment.fingerprint.family_fingerprint,
                family_key=assessment.family_key,
                name=title,
                actor_id=actor_id,
            )
            await self._repository.ensure_family_membership(
                session,
                family=family,
                rule_version=version,
                member_role="primary",
                parameter_distance=None,
                actor_id=actor_id,
            )
            return version, assessment

        version = await self._repository.create_formal_rule(
            session,
            candidate=candidate,
            actor_id=actor_id,
            reason=reason,
            exact_fingerprint=assessment.fingerprint.exact_fingerprint,
            business_key=f"rule:{assessment.fingerprint.exact_fingerprint}",
            title=title,
            description=description,
            schema_version=schema_version,
            instrument_scope=instrument_scope,
            condition_json=condition_json,
            action_json=action_json,
            parameter_json=parameter_json,
            data_dependencies=data_dependencies,
            evidence_json=evidence_json,
            correlation_id=correlation_id,
            after_review_snapshot={
                **after_review_snapshot,
                "governance_relation": "new_rule_version",
                "family_fingerprint": assessment.fingerprint.family_fingerprint,
            },
        )
        family = await self._repository.ensure_family(
            session,
            family_fingerprint=assessment.fingerprint.family_fingerprint,
            family_key=assessment.family_key,
            name=title,
            actor_id=actor_id,
        )
        member_role = "variant" if any(item.relation == "parameter_variant" for item in assessment.related_rules) else "primary"
        parameter_distance = next(
            (item.parameter_differences for item in assessment.related_rules if item.relation == "parameter_variant"),
            None,
        )
        await self._repository.ensure_family_membership(
            session,
            family=family,
            rule_version=version,
            member_role=member_role,
            parameter_distance=parameter_distance,
            actor_id=actor_id,
        )
        return version, assessment
