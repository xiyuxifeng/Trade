from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
import hashlib
import json
from typing import Any, Callable
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.author_profile_repository import AuthorProfileRepository
from src.db.session import get_session_factory
from src.domain.enums import AuthorProfileKind, FormalLifecycleState, QualityStatus
from src.models.blog_article import BlogArticle
from src.models.stage2_canonical import (
    ArticleStructure,
    Authors,
    RuleCandidate,
    RuleFamily,
    RuleFamilyMembership,
    RuleVersion,
)
from src.services.author_profile_service import AuthorProfileDraftRequest, AuthorProfileService, AuthorProfileVersionView
from src.services.rule_governance_service import compare_rule_payloads


AUTHOR_RULE_PROFILE_SCHEMA_VERSION = "author-profile-v1"
AUTHOR_RULE_PROFILE_AGGREGATION_VERSION = "author_rule_profile_summary_deterministic_v1"
AUTHOR_RULE_PROFILE_LIMITATION = "画像来自已审核的规则与规则族证据，不代表作者真实实盘表现。"
REVIEWED_RULE_STATES = {
    FormalLifecycleState.approved,
    FormalLifecycleState.published,
    FormalLifecycleState.archived,
    FormalLifecycleState.superseded,
}


class AuthorRuleProfileGenerationRequest(BaseModel):
    author_id: UUID
    rule_version_ids: list[UUID] = Field(min_length=1, max_length=50)
    rule_family_ids: list[UUID] = Field(default_factory=list, max_length=50)
    author_profile_id: UUID | None = None
    parent_version_id: UUID | None = None
    supersedes_version_id: UUID | None = None
    evidence_from: date | None = None
    evidence_to: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    reason: str | None = None
    source_surface: str = "/authors"

    @field_validator("rule_version_ids")
    @classmethod
    def _dedupe_rule_version_ids(cls, value: list[UUID]) -> list[UUID]:
        deduped = list(dict.fromkeys(value))
        if not deduped:
            raise ValueError("至少需要一个已审核规则版本。")
        return deduped

    @field_validator("rule_family_ids")
    @classmethod
    def _dedupe_rule_family_ids(cls, value: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(value))


@dataclass(frozen=True)
class _RuleEvidenceBundle:
    rule_version: RuleVersion
    candidate: RuleCandidate | None
    article: BlogArticle | None
    structure: ArticleStructure | None


@dataclass(frozen=True)
class _RuleSnapshot:
    bundle: _RuleEvidenceBundle
    families: list[RuleFamily]
    memberships: list[RuleFamilyMembership]
    rule_payload: dict[str, Any]
    quantification: dict[str, Any]
    data_dependencies: list[str]


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(_jsonable(payload), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _extract_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, tuple):
        return [str(item) for item in value if item is not None]
    if isinstance(value, set):
        return [str(item) for item in sorted(value, key=str)]
    return [str(value)]


def _rule_payload(version: RuleVersion) -> dict[str, Any]:
    parameter_json = version.parameter_json or {}
    quantification = parameter_json.get("quantification") or (version.evidence_json or {}).get("quantification") or {}
    market_state = parameter_json.get("market_state_applicability") or {}
    return {
        "title": version.title,
        "description": version.description,
        "rule_type": version.rule_type,
        "instrument_focus": _extract_list((version.instrument_scope or {}).get("instrument_focus")),
        "timeframe": parameter_json.get("timeframe"),
        "holding_period": parameter_json.get("holding_period"),
        "condition": version.condition_json or {},
        "action": version.action_json or {},
        "risk_controls": parameter_json.get("risk_controls") or [],
        "data_dependencies": _extract_list((version.data_dependencies or {}).get("required") or version.data_dependencies),
        "market_state_applicability": {
            "status": market_state.get("status") or "not_declared",
            "explicit_conditions": market_state.get("explicit_conditions") or [],
            "inferred_hypotheses": market_state.get("inferred_hypotheses") or [],
        },
        "quantification": {
            "status": quantification.get("status") or "unknown",
            "missing_fields": _extract_list(quantification.get("missing_fields")),
            "ambiguous_terms": _extract_list(quantification.get("ambiguous_terms")),
            "manual_review_required": bool(quantification.get("manual_review_required")),
        },
    }


def _quantification_bucket(version: RuleVersion) -> dict[str, Any]:
    quantification = _rule_payload(version)["quantification"]
    source_status = str(quantification["status"])
    missing_fields = list(quantification["missing_fields"])
    ambiguous_terms = list(quantification["ambiguous_terms"])
    manual_review_required = bool(quantification["manual_review_required"])
    if source_status == "executable" and not missing_fields and not ambiguous_terms and not manual_review_required:
        status = "quantifiable"
        label = "可量化"
    elif source_status in {"partially_executable", "executable"} or missing_fields or ambiguous_terms or manual_review_required:
        status = "partial"
        label = "部分可量化"
    else:
        status = "insufficient"
        label = "量化信息不足"
    return {
        "status": status,
        "label": label,
        "source_status": source_status,
        "missing_fields": missing_fields,
        "ambiguous_terms": ambiguous_terms,
        "manual_review_required": manual_review_required,
    }


def _confidence_score(
    *,
    reviewed_count: int,
    requested_count: int,
    family_count: int,
    conflict_pair_count: int,
    partial_quant_count: int,
    issue_count: int,
) -> float:
    if reviewed_count == 0:
        return 0.18
    score = 0.55
    score += min(reviewed_count, 8) * 0.03
    score += min(family_count, 6) * 0.02
    if requested_count:
        score += reviewed_count / requested_count * 0.06
    score -= conflict_pair_count * 0.05
    score -= partial_quant_count * 0.02
    score -= issue_count * 0.03
    return round(max(0.1, min(score, 0.95)), 2)


class AuthorRuleProfileService:
    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any] | None = None,
        profile_repository: AuthorProfileRepository | None = None,
        profile_service: AuthorProfileService | None = None,
    ) -> None:
        self._session_scope_factory = session_scope_factory or self._default_session_scope_factory
        self._profile_repository = profile_repository or AuthorProfileRepository()
        self._profile_service = profile_service or AuthorProfileService(
            repository=self._profile_repository,
            session_scope_factory=self._session_scope_factory,
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

    async def generate_draft(
        self,
        request: AuthorRuleProfileGenerationRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> AuthorProfileVersionView:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to create an author rule profile draft")

        async with self._session_scope_factory() as session:
            author = await session.get(Authors, request.author_id)
            if author is None:
                raise LookupError("author not found")

            bundles = await self._load_rule_bundles(session, request.rule_version_ids)
            bundle_by_id = {bundle.rule_version.rule_version_id: bundle for bundle in bundles}
            memberships = await self._load_memberships(session, request.rule_version_ids)
            family_by_id = await self._load_families(session, request.rule_family_ids, memberships)

            issues: list[dict[str, Any]] = []
            missing_rule_ids = [rule_version_id for rule_version_id in request.rule_version_ids if rule_version_id not in bundle_by_id]
            if missing_rule_ids:
                issues.append(
                    {
                        "lane": "rule_governance",
                        "reason": "部分规则版本未找到。",
                        "rule_version_ids": [str(rule_version_id) for rule_version_id in missing_rule_ids],
                    }
                )

            reviewed_bundles: list[_RuleEvidenceBundle] = []
            unreviewed_rule_ids: list[str] = []
            unaligned_rule_ids: list[str] = []
            for rule_version_id in request.rule_version_ids:
                bundle = bundle_by_id.get(rule_version_id)
                if bundle is None:
                    continue
                if bundle.rule_version.lifecycle_state not in REVIEWED_RULE_STATES:
                    unreviewed_rule_ids.append(str(bundle.rule_version.rule_version_id))
                    continue
                if not self._is_author_aligned(author, bundle):
                    unaligned_rule_ids.append(str(bundle.rule_version.rule_version_id))
                    continue
                reviewed_bundles.append(bundle)

            if unreviewed_rule_ids:
                issues.append(
                    {
                        "lane": "rule_governance",
                        "reason": "部分规则版本尚未进入已审核状态。",
                        "rule_version_ids": unreviewed_rule_ids,
                    }
                )
            if unaligned_rule_ids:
                issues.append(
                    {
                        "lane": "rule_governance",
                        "reason": "部分规则版本来源未对齐当前作者。",
                        "rule_version_ids": unaligned_rule_ids,
                    }
                )

            membership_by_rule: dict[UUID, list[RuleFamilyMembership]] = {}
            for membership in memberships:
                membership_by_rule.setdefault(membership.rule_version_id, []).append(membership)

            snapshots = [
                _RuleSnapshot(
                    bundle=bundle,
                    families=[
                        family_by_id[membership.rule_family_id]
                        for membership in membership_by_rule.get(bundle.rule_version.rule_version_id, [])
                        if membership.rule_family_id in family_by_id
                    ],
                    memberships=membership_by_rule.get(bundle.rule_version.rule_version_id, []),
                    rule_payload=_rule_payload(bundle.rule_version),
                    quantification=_quantification_bucket(bundle.rule_version),
                    data_dependencies=_extract_list(
                        (bundle.rule_version.data_dependencies or {}).get("required") or bundle.rule_version.data_dependencies
                    ),
                )
                for bundle in reviewed_bundles
            ]

            if not snapshots:
                draft_request = self._build_insufficient_request(request, issues, family_by_id, memberships)
                return await self._profile_service.create_draft(draft_request, actor_id=actor_id, actor_role=actor_role)

            draft_request = self._build_draft_request(
                request=request,
                author=author,
                snapshots=snapshots,
                issues=issues,
                missing_rule_ids=missing_rule_ids,
                unreviewed_rule_ids=unreviewed_rule_ids,
                unaligned_rule_ids=unaligned_rule_ids,
            )
            return await self._profile_service.create_draft(draft_request, actor_id=actor_id, actor_role=actor_role)

    async def _load_rule_bundles(self, session: AsyncSession, rule_version_ids: list[UUID]) -> list[_RuleEvidenceBundle]:
        stmt = (
            select(RuleVersion, RuleCandidate, ArticleStructure, BlogArticle)
            .outerjoin(RuleCandidate, RuleCandidate.rule_candidate_id == RuleVersion.source_candidate_id)
            .outerjoin(ArticleStructure, ArticleStructure.article_structure_id == RuleCandidate.article_structure_id)
            .outerjoin(BlogArticle, BlogArticle.id == RuleCandidate.source_article_id)
            .where(RuleVersion.rule_version_id.in_(rule_version_ids))
        )
        rows = (await session.execute(stmt)).all()
        bundles = [
            _RuleEvidenceBundle(rule_version=rule_version, candidate=candidate, structure=structure, article=article)
            for rule_version, candidate, structure, article in rows
        ]
        by_id = {bundle.rule_version.rule_version_id: bundle for bundle in bundles}
        return [by_id[rule_version_id] for rule_version_id in rule_version_ids if rule_version_id in by_id]

    async def _load_memberships(self, session: AsyncSession, rule_version_ids: list[UUID]) -> list[RuleFamilyMembership]:
        if not rule_version_ids:
            return []
        stmt = select(RuleFamilyMembership).where(RuleFamilyMembership.rule_version_id.in_(rule_version_ids))
        return list((await session.execute(stmt)).scalars().all())

    async def _load_families(
        self,
        session: AsyncSession,
        requested_family_ids: list[UUID],
        memberships: list[RuleFamilyMembership],
    ) -> dict[UUID, RuleFamily]:
        family_ids = list(dict.fromkeys([*requested_family_ids, *[membership.rule_family_id for membership in memberships]]))
        if not family_ids:
            return {}
        stmt = select(RuleFamily).where(RuleFamily.rule_family_id.in_(family_ids))
        return {row.rule_family_id: row for row in (await session.execute(stmt)).scalars().all()}

    def _is_author_aligned(self, author: Authors, bundle: _RuleEvidenceBundle) -> bool:
        if bundle.article is None or bundle.candidate is None or bundle.structure is None:
            return False
        article_matches = bundle.article.source == author.source and bundle.article.author_id == author.source_author_key
        structure_matches = (bundle.structure.payload or {}).get("author_id") == author.source_author_key
        return article_matches and structure_matches

    def _build_draft_request(
        self,
        *,
        request: AuthorRuleProfileGenerationRequest,
        author: Authors,
        snapshots: list[_RuleSnapshot],
        issues: list[dict[str, Any]],
        missing_rule_ids: list[UUID],
        unreviewed_rule_ids: list[str],
        unaligned_rule_ids: list[str],
    ) -> AuthorProfileDraftRequest:
        rule_type_distribution = self._build_rule_type_distribution(snapshots)
        family_summaries = self._build_family_summaries(snapshots)
        quantifiability = self._build_quantifiability_summary(snapshots)
        data_dependencies = self._build_data_dependency_summary(snapshots)
        repeat_conflict_summary = self._build_repeat_conflict_summary(snapshots)
        representative_rules = self._build_representative_rules(snapshots, family_summaries)
        partial_quant_count = len([snapshot for snapshot in snapshots if snapshot.quantification["status"] != "quantifiable"])
        confidence = _confidence_score(
            reviewed_count=len(snapshots),
            requested_count=len(request.rule_version_ids),
            family_count=len([item for item in family_summaries if item["rule_family_id"] is not None]),
            conflict_pair_count=repeat_conflict_summary["conflict_pair_count"],
            partial_quant_count=partial_quant_count,
            issue_count=len(issues),
        )
        limitations = self._build_limitations(issues, partial_quant_count, repeat_conflict_summary)
        quality_status = QualityStatus.complete if not issues and partial_quant_count == 0 else QualityStatus.partial
        quality = {
            "status": "complete" if quality_status == QualityStatus.complete else "partial",
            "warnings": limitations,
        }
        if issues:
            quality["issues"] = issues

        evidence = {
            "rule_statistics": {
                "rule_type_distribution": rule_type_distribution,
                "quantifiability": quantifiability,
                "data_dependencies": data_dependencies,
                "repeat_conflict_summary": repeat_conflict_summary,
            },
            "rule_governance": {
                "reviewed_rule_versions": [
                    {
                        "rule_version_id": str(snapshot.bundle.rule_version.rule_version_id),
                        "title": snapshot.bundle.rule_version.title,
                        "rule_type": snapshot.bundle.rule_version.rule_type,
                        "lifecycle_state": snapshot.bundle.rule_version.lifecycle_state.value,
                        "canonical_fingerprint": snapshot.bundle.rule_version.canonical_fingerprint,
                    }
                    for snapshot in snapshots
                ],
                "rule_families": family_summaries,
                "membership_snapshot": [
                    {
                        "rule_family_id": str(membership.rule_family_id),
                        "rule_version_id": str(membership.rule_version_id),
                        "member_role": membership.member_role,
                        "parameter_distance": membership.parameter_distance,
                    }
                    for snapshot in snapshots
                    for membership in snapshot.memberships
                ],
                "issues": issues,
            },
        }
        conclusions = self._build_conclusions(
            author_id=author.author_id,
            snapshots=snapshots,
            rule_type_distribution=rule_type_distribution,
            quantifiability=quantifiability,
            repeat_conflict_summary=repeat_conflict_summary,
            family_summaries=family_summaries,
            confidence=confidence,
        )
        profile_payload = {
            "rule_profile": {
                "summary_mode": AUTHOR_RULE_PROFILE_AGGREGATION_VERSION,
                "rule_type_distribution": rule_type_distribution,
                "rule_families": family_summaries,
                "quantifiability": quantifiability,
                "data_dependencies": data_dependencies,
                "repeat_conflict_summary": repeat_conflict_summary,
                "representative_rules": representative_rules,
                "confidence": {
                    "overall": confidence,
                    "basis": [
                        f"reviewed_rule_versions={len(snapshots)}",
                        f"rule_families={len([item for item in family_summaries if item['rule_family_id'] is not None])}",
                        f"issues={len(issues)}",
                    ],
                },
                "limitations": limitations,
                "evidence": evidence,
            },
            "quality": quality,
            "conclusions": conclusions,
            "limitations": limitations,
        }
        source_rule_version_ids = {
            "requested_rule_version_ids": [str(rule_version_id) for rule_version_id in request.rule_version_ids],
            "reviewed_rule_version_ids": [str(snapshot.bundle.rule_version.rule_version_id) for snapshot in snapshots],
            "reviewed_rule_version_fingerprints": [snapshot.bundle.rule_version.canonical_fingerprint for snapshot in snapshots],
            "missing_rule_version_ids": [str(rule_version_id) for rule_version_id in missing_rule_ids],
            "unreviewed_rule_version_ids": unreviewed_rule_ids,
            "unaligned_rule_version_ids": unaligned_rule_ids,
        }
        source_rule_family_ids = {
            "requested_rule_family_ids": [str(rule_family_id) for rule_family_id in request.rule_family_ids],
            "reviewed_rule_family_ids": [
                item["rule_family_id"]
                for item in family_summaries
                if item["rule_family_id"] is not None
            ],
            "reviewed_rule_family_fingerprints": [
                item["canonical_fingerprint"]
                for item in family_summaries
                if item["canonical_fingerprint"] is not None
            ],
            "membership_snapshot": evidence["rule_governance"]["membership_snapshot"],
        }
        source_versions = {
            "aggregation_version": AUTHOR_RULE_PROFILE_AGGREGATION_VERSION,
            "profile_schema_version": AUTHOR_RULE_PROFILE_SCHEMA_VERSION,
            "reviewed_rule_states": sorted({snapshot.bundle.rule_version.lifecycle_state.value for snapshot in snapshots}),
            "reviewed_rule_count": len(snapshots),
            "reviewed_rule_family_count": len([item for item in family_summaries if item["rule_family_id"] is not None]),
            "reviewed_rule_version_fingerprints": [snapshot.bundle.rule_version.canonical_fingerprint for snapshot in snapshots],
            "reviewed_rule_family_fingerprints": [
                item["canonical_fingerprint"]
                for item in family_summaries
                if item["canonical_fingerprint"] is not None
            ],
        }
        return AuthorProfileDraftRequest(
            author_id=request.author_id,
            author_profile_id=request.author_profile_id,
            parent_version_id=request.parent_version_id,
            supersedes_version_id=request.supersedes_version_id,
            profile_kind=AuthorProfileKind.rule,
            schema_version=AUTHOR_RULE_PROFILE_SCHEMA_VERSION,
            payload=profile_payload,
            evidence=evidence,
            source_rule_version_ids=source_rule_version_ids,
            source_rule_family_ids=source_rule_family_ids,
            source_versions=source_versions,
            evidence_from=request.evidence_from,
            evidence_to=request.evidence_to,
            effective_from=request.effective_from,
            effective_to=request.effective_to,
            quality_status=quality_status,
            reason=request.reason,
            source_surface=request.source_surface,
        )

    def _build_insufficient_request(
        self,
        request: AuthorRuleProfileGenerationRequest,
        issues: list[dict[str, Any]],
        family_by_id: dict[UUID, RuleFamily],
        memberships: list[RuleFamilyMembership],
    ) -> AuthorProfileDraftRequest:
        unresolved_issues = issues or [{"lane": "rule_governance", "reason": "当前证据不足，无法生成完整规则画像。"}]
        return AuthorProfileDraftRequest(
            author_id=request.author_id,
            author_profile_id=request.author_profile_id,
            parent_version_id=request.parent_version_id,
            supersedes_version_id=request.supersedes_version_id,
            profile_kind=AuthorProfileKind.rule,
            schema_version=AUTHOR_RULE_PROFILE_SCHEMA_VERSION,
            payload={
                "rule_profile": {
                    "summary_mode": AUTHOR_RULE_PROFILE_AGGREGATION_VERSION,
                    "rule_type_distribution": [],
                    "rule_families": [],
                    "quantifiability": {
                        "label": "证据不足",
                        "status_counts": {},
                        "rules": [],
                    },
                    "data_dependencies": [],
                    "repeat_conflict_summary": {
                        "pair_count": 0,
                        "exact_duplicate_pair_count": 0,
                        "parameter_variant_pair_count": 0,
                        "conflict_pair_count": 0,
                        "exact_duplicate_groups": [],
                        "conflict_pairs": [],
                    },
                    "representative_rules": [],
                    "confidence": {"overall": 0.18, "basis": ["insufficient_evidence"]},
                    "limitations": [AUTHOR_RULE_PROFILE_LIMITATION, "当前证据不足，无法生成完整规则画像。"],
                    "evidence": {"rule_governance": {"issues": unresolved_issues}},
                },
                "quality": {
                    "status": "insufficient_evidence",
                    "warnings": ["当前证据不足，无法生成完整规则画像。"],
                    "issues": unresolved_issues,
                },
                "conclusions": [],
                "limitations": [AUTHOR_RULE_PROFILE_LIMITATION, "当前证据不足，无法生成完整规则画像。"],
            },
            evidence={
                "rule_governance": {
                    "issues": unresolved_issues,
                    "membership_snapshot": [
                        {
                            "rule_family_id": str(membership.rule_family_id),
                            "rule_version_id": str(membership.rule_version_id),
                            "member_role": membership.member_role,
                        }
                        for membership in memberships
                    ],
                }
            },
            source_rule_version_ids={
                "requested_rule_version_ids": [str(rule_version_id) for rule_version_id in request.rule_version_ids],
                "reviewed_rule_version_ids": [],
            },
            source_rule_family_ids={
                "requested_rule_family_ids": [str(rule_family_id) for rule_family_id in request.rule_family_ids],
                "resolved_rule_family_ids": [str(rule_family_id) for rule_family_id in family_by_id],
            },
            source_versions={
                "aggregation_version": AUTHOR_RULE_PROFILE_AGGREGATION_VERSION,
                "status": "insufficient_evidence",
                "issues": unresolved_issues,
            },
            evidence_from=request.evidence_from,
            evidence_to=request.evidence_to,
            effective_from=request.effective_from,
            effective_to=request.effective_to,
            quality_status=QualityStatus.unresolved,
            reason=request.reason,
            source_surface=request.source_surface,
        )

    def _build_rule_type_distribution(self, snapshots: list[_RuleSnapshot]) -> list[dict[str, Any]]:
        counts: dict[str, list[str]] = {}
        for snapshot in snapshots:
            counts.setdefault(snapshot.bundle.rule_version.rule_type, []).append(str(snapshot.bundle.rule_version.rule_version_id))
        total = sum(len(items) for items in counts.values()) or 1
        return [
            {
                "rule_type": rule_type,
                "count": len(rule_version_ids),
                "share": round(len(rule_version_ids) / total, 4),
                "rule_version_ids": rule_version_ids,
            }
            for rule_type, rule_version_ids in sorted(counts.items())
        ]

    def _build_family_summaries(self, snapshots: list[_RuleSnapshot]) -> list[dict[str, Any]]:
        by_family: dict[str, dict[str, Any]] = {}
        unassigned: list[_RuleSnapshot] = []
        for snapshot in snapshots:
            if not snapshot.families:
                unassigned.append(snapshot)
                continue
            for family in snapshot.families:
                entry = by_family.setdefault(
                    str(family.rule_family_id),
                    {
                        "rule_family_id": str(family.rule_family_id),
                        "family_key": family.family_key,
                        "name": family.name,
                        "canonical_fingerprint": family.canonical_fingerprint,
                        "lifecycle_state": family.lifecycle_state.value,
                        "member_rule_version_ids": [],
                        "member_rule_version_fingerprints": [],
                        "member_rule_types": set(),
                        "member_roles": [],
                    },
                )
                entry["member_rule_version_ids"].append(str(snapshot.bundle.rule_version.rule_version_id))
                entry["member_rule_version_fingerprints"].append(snapshot.bundle.rule_version.canonical_fingerprint)
                entry["member_rule_types"].add(snapshot.bundle.rule_version.rule_type)
                entry["member_roles"].extend([membership.member_role for membership in snapshot.memberships if membership.member_role])
        summaries = []
        for entry in by_family.values():
            member_rule_ids = sorted(dict.fromkeys(entry["member_rule_version_ids"]))
            summaries.append(
                {
                    "rule_family_id": entry["rule_family_id"],
                    "family_key": entry["family_key"],
                    "name": entry["name"],
                    "canonical_fingerprint": entry["canonical_fingerprint"],
                    "lifecycle_state": entry["lifecycle_state"],
                    "member_rule_version_ids": member_rule_ids,
                    "member_rule_version_fingerprints": sorted(dict.fromkeys(entry["member_rule_version_fingerprints"])),
                    "member_count": len(member_rule_ids),
                    "member_rule_types": sorted(entry["member_rule_types"]),
                    "representative_rule_version_id": member_rule_ids[0] if member_rule_ids else None,
                    "member_roles": sorted(dict.fromkeys(entry["member_roles"])),
                }
            )
        if unassigned:
            summaries.append(
                {
                    "rule_family_id": None,
                    "family_key": "unassigned",
                    "name": "未绑定规则族",
                    "canonical_fingerprint": None,
                    "lifecycle_state": "partial",
                    "member_rule_version_ids": [str(snapshot.bundle.rule_version.rule_version_id) for snapshot in unassigned],
                    "member_rule_version_fingerprints": [snapshot.bundle.rule_version.canonical_fingerprint for snapshot in unassigned],
                    "member_count": len(unassigned),
                    "member_rule_types": sorted({snapshot.bundle.rule_version.rule_type for snapshot in unassigned}),
                    "representative_rule_version_id": str(unassigned[0].bundle.rule_version.rule_version_id),
                    "member_roles": [],
                }
            )
        return sorted(summaries, key=lambda item: (item["rule_family_id"] is None, item["name"] or ""))

    def _build_quantifiability_summary(self, snapshots: list[_RuleSnapshot]) -> dict[str, Any]:
        rules = [
            {
                "rule_version_id": str(snapshot.bundle.rule_version.rule_version_id),
                "title": snapshot.bundle.rule_version.title,
                "status": snapshot.quantification["status"],
                "label": snapshot.quantification["label"],
                "source_status": snapshot.quantification["source_status"],
                "missing_fields": snapshot.quantification["missing_fields"],
                "ambiguous_terms": snapshot.quantification["ambiguous_terms"],
                "manual_review_required": snapshot.quantification["manual_review_required"],
                "data_dependencies": snapshot.data_dependencies,
            }
            for snapshot in snapshots
        ]
        status_counts: dict[str, int] = {}
        for rule in rules:
            status_counts[rule["status"]] = status_counts.get(rule["status"], 0) + 1
        if status_counts.get("quantifiable", 0) == len(rules):
            label = "全部可量化"
        elif status_counts.get("quantifiable", 0) + status_counts.get("partial", 0) == len(rules):
            label = "部分可量化"
        else:
            label = "量化信息不足"
        return {
            "label": label,
            "status_counts": dict(sorted(status_counts.items())),
            "rules": rules,
        }

    def _build_data_dependency_summary(self, snapshots: list[_RuleSnapshot]) -> list[dict[str, Any]]:
        dependencies: dict[str, dict[str, Any]] = {}
        for snapshot in snapshots:
            for dependency in snapshot.data_dependencies:
                entry = dependencies.setdefault(
                    dependency,
                    {
                        "name": dependency,
                        "count": 0,
                        "rule_version_ids": [],
                        "rule_family_ids": [],
                    },
                )
                entry["count"] += 1
                entry["rule_version_ids"].append(str(snapshot.bundle.rule_version.rule_version_id))
                entry["rule_family_ids"].extend([str(family.rule_family_id) for family in snapshot.families])
        return sorted(
            [
                {
                    **entry,
                    "rule_version_ids": sorted(dict.fromkeys(entry["rule_version_ids"])),
                    "rule_family_ids": sorted(dict.fromkeys(entry["rule_family_ids"])),
                }
                for entry in dependencies.values()
            ],
            key=lambda item: (-item["count"], item["name"]),
        )

    def _build_repeat_conflict_summary(self, snapshots: list[_RuleSnapshot]) -> dict[str, Any]:
        duplicate_groups: dict[str, list[_RuleSnapshot]] = {}
        pair_count = 0
        parameter_variant_pair_count = 0
        conflict_pairs: list[dict[str, Any]] = []

        for index, left in enumerate(snapshots):
            duplicate_groups.setdefault(left.bundle.rule_version.canonical_fingerprint, []).append(left)
            for right in snapshots[index + 1 :]:
                pair_count += 1
                comparison = compare_rule_payloads(left.rule_payload, right.rule_payload)
                if comparison.relation == "parameter_variant":
                    parameter_variant_pair_count += 1
                elif comparison.relation == "conflict":
                    conflict_pairs.append(
                        {
                            "left_rule_version_id": str(left.bundle.rule_version.rule_version_id),
                            "right_rule_version_id": str(right.bundle.rule_version.rule_version_id),
                            "conflict_reasons": comparison.conflict_reasons,
                        }
                    )

        exact_duplicate_groups = [
            {
                "canonical_fingerprint": fingerprint,
                "rule_version_ids": [str(snapshot.bundle.rule_version.rule_version_id) for snapshot in group],
                "titles": [snapshot.bundle.rule_version.title for snapshot in group],
            }
            for fingerprint, group in duplicate_groups.items()
            if len(group) > 1
        ]
        return {
            "pair_count": pair_count,
            "exact_duplicate_pair_count": sum(len(group) * (len(group) - 1) // 2 for group in duplicate_groups.values() if len(group) > 1),
            "parameter_variant_pair_count": parameter_variant_pair_count,
            "conflict_pair_count": len(conflict_pairs),
            "exact_duplicate_groups": exact_duplicate_groups,
            "conflict_pairs": conflict_pairs,
        }

    def _build_representative_rules(
        self,
        snapshots: list[_RuleSnapshot],
        family_summaries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        snapshot_by_id = {str(snapshot.bundle.rule_version.rule_version_id): snapshot for snapshot in snapshots}
        representatives: list[dict[str, Any]] = []
        used_rule_ids: set[str] = set()
        for family in family_summaries:
            representative_id = family["representative_rule_version_id"]
            if representative_id is None:
                continue
            snapshot = snapshot_by_id.get(representative_id)
            if snapshot is None:
                continue
            used_rule_ids.add(representative_id)
            representatives.append(
                {
                    "rule_version_id": representative_id,
                    "title": snapshot.bundle.rule_version.title,
                    "rule_type": snapshot.bundle.rule_version.rule_type,
                    "canonical_fingerprint": snapshot.bundle.rule_version.canonical_fingerprint,
                    "rule_family_ids": [family["rule_family_id"]] if family["rule_family_id"] is not None else [],
                    "quantifiability": snapshot.quantification,
                    "data_dependencies": snapshot.data_dependencies,
                    "reason": "代表对应规则族的首个已审核版本。",
                }
            )
        for snapshot in snapshots:
            rule_version_id = str(snapshot.bundle.rule_version.rule_version_id)
            if rule_version_id in used_rule_ids:
                continue
            representatives.append(
                {
                    "rule_version_id": rule_version_id,
                    "title": snapshot.bundle.rule_version.title,
                    "rule_type": snapshot.bundle.rule_version.rule_type,
                    "canonical_fingerprint": snapshot.bundle.rule_version.canonical_fingerprint,
                    "rule_family_ids": [str(family.rule_family_id) for family in snapshot.families],
                    "quantifiability": snapshot.quantification,
                    "data_dependencies": snapshot.data_dependencies,
                    "reason": "补充未被规则族覆盖的代表性样本。",
                }
            )
            break
        return representatives

    def _build_limitations(
        self,
        issues: list[dict[str, Any]],
        partial_quant_count: int,
        repeat_conflict_summary: dict[str, Any],
    ) -> list[str]:
        limitations = [AUTHOR_RULE_PROFILE_LIMITATION]
        for issue in issues:
            limitations.append(issue["reason"])
        if partial_quant_count:
            limitations.append("量化信息并非全部完整，需人工查看原始规则证据。")
        if repeat_conflict_summary["conflict_pair_count"]:
            limitations.append("存在冲突规则，需要人工复核后才能作为正式结论。")
        if repeat_conflict_summary["exact_duplicate_pair_count"]:
            limitations.append("存在完全重复的规则版本，代表性结论应优先引用已审核版本。")
        return list(dict.fromkeys(limitations))

    def _build_conclusions(
        self,
        *,
        author_id: UUID,
        snapshots: list[_RuleSnapshot],
        rule_type_distribution: list[dict[str, Any]],
        quantifiability: dict[str, Any],
        repeat_conflict_summary: dict[str, Any],
        family_summaries: list[dict[str, Any]],
        confidence: float,
    ) -> list[dict[str, Any]]:
        rule_version_ids = [str(snapshot.bundle.rule_version.rule_version_id) for snapshot in snapshots]
        family_ids = [item["rule_family_id"] for item in family_summaries if item["rule_family_id"] is not None]
        return [
            {
                "text": self._dominant_rule_type_text(rule_type_distribution),
                "evidence": [{"lane": "rule_statistics", "source": "rule_type_distribution", "rule_version_ids": rule_version_ids}],
                "confidence": confidence,
                "provenance": {
                    "lane": "rule_statistics",
                    "author_id": str(author_id),
                    "profile_kind": AuthorProfileKind.rule.value,
                },
                "version_binding": {
                    "schema_version": AUTHOR_RULE_PROFILE_SCHEMA_VERSION,
                    "aggregation_version": AUTHOR_RULE_PROFILE_AGGREGATION_VERSION,
                    "source_fingerprint": _fingerprint({"rule_type_distribution": rule_type_distribution}),
                },
            },
            {
                "text": self._quantifiability_text(quantifiability),
                "evidence": [{"lane": "rule_statistics", "source": "quantifiability_summary", "rule_version_ids": rule_version_ids}],
                "confidence": confidence,
                "provenance": {
                    "lane": "rule_statistics",
                    "author_id": str(author_id),
                    "profile_kind": AuthorProfileKind.rule.value,
                },
                "version_binding": {
                    "schema_version": AUTHOR_RULE_PROFILE_SCHEMA_VERSION,
                    "aggregation_version": AUTHOR_RULE_PROFILE_AGGREGATION_VERSION,
                    "source_fingerprint": _fingerprint({"quantifiability": quantifiability}),
                },
            },
            {
                "text": self._repeat_conflict_text(repeat_conflict_summary, family_ids),
                "evidence": [{"lane": "rule_statistics", "source": "repeat_conflict_summary", "rule_version_ids": rule_version_ids}],
                "confidence": confidence,
                "provenance": {
                    "lane": "rule_statistics",
                    "author_id": str(author_id),
                    "profile_kind": AuthorProfileKind.rule.value,
                    "source_rule_family_ids": family_ids,
                },
                "version_binding": {
                    "schema_version": AUTHOR_RULE_PROFILE_SCHEMA_VERSION,
                    "aggregation_version": AUTHOR_RULE_PROFILE_AGGREGATION_VERSION,
                    "source_fingerprint": _fingerprint({"repeat_conflict_summary": repeat_conflict_summary}),
                },
            },
        ]

    def _dominant_rule_type_text(self, distribution: list[dict[str, Any]]) -> str:
        if not distribution:
            return "当前没有可用的已审核规则版本。"
        dominant = distribution[0]
        return f"规则类型主要集中在 {dominant['rule_type']}，共 {dominant['count']} 条已审核规则。"

    def _quantifiability_text(self, quantifiability: dict[str, Any]) -> str:
        counts = quantifiability["status_counts"]
        return (
            f"规则量化状态以{quantifiability['label']}为主："
            f"可量化 {counts.get('quantifiable', 0)} 条，"
            f"部分可量化 {counts.get('partial', 0)} 条，"
            f"量化信息不足 {counts.get('insufficient', 0)} 条。"
        )

    def _repeat_conflict_text(self, repeat_conflict_summary: dict[str, Any], family_ids: list[str]) -> str:
        if repeat_conflict_summary["conflict_pair_count"]:
            return f"发现 {repeat_conflict_summary['conflict_pair_count']} 组冲突规则，需要人工复核。"
        if repeat_conflict_summary["exact_duplicate_pair_count"]:
            return f"发现 {repeat_conflict_summary['exact_duplicate_pair_count']} 组完全重复规则，建议优先引用已审核版本。"
        if family_ids:
            return f"规则族共覆盖 {len(family_ids)} 个正式分组，当前未发现明显冲突。"
        return "当前规则证据尚未形成稳定规则族分组。"
