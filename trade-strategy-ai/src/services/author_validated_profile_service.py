from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.author_profile_repository import AuthorProfileRepository
from src.db.session import get_session_factory
from src.domain.enums import AuthorProfileKind, QualityStatus
from src.models.blog_article import BlogArticle
from src.models.rule_applicability import RuleApplicabilityProfile
from src.models.stage2_canonical import (
    ArticleStructure,
    Authors,
    BacktestResult,
    BacktestRun,
    RuleCandidate,
    RuleVersion,
)
from src.services.author_profile_service import AuthorProfileDraftRequest, AuthorProfileService, AuthorProfileVersionView


AUTHOR_VALIDATED_PROFILE_SCHEMA_VERSION = "author-profile-v1"
AUTHOR_VALIDATED_PROFILE_AGGREGATION_VERSION = "author_validated_profile_summary_deterministic_v1"
AUTHOR_VALIDATED_PROFILE_LIMITATION = "画像来自正式回测与规则适用性证据，不代表作者真实实盘表现。"


class AuthorValidatedProfileGenerationRequest(BaseModel):
    author_id: UUID
    applicability_profile_ids: list[UUID] = Field(min_length=1, max_length=50)
    author_profile_id: UUID | None = None
    parent_version_id: UUID | None = None
    supersedes_version_id: UUID | None = None
    evidence_from: date | None = None
    evidence_to: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    reason: str | None = None
    source_surface: str = "/authors"

    @field_validator("applicability_profile_ids")
    @classmethod
    def _dedupe_profile_ids(cls, value: list[UUID]) -> list[UUID]:
        deduped = list(dict.fromkeys(value))
        if not deduped:
            raise ValueError("至少需要一个正式适用性画像。")
        return deduped

    @model_validator(mode="after")
    def _validate_periods(self) -> "AuthorValidatedProfileGenerationRequest":
        if self.evidence_from and self.evidence_to and self.evidence_to < self.evidence_from:
            raise ValueError("evidence_to must be on or after evidence_from")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


@dataclass(frozen=True)
class _RuleLineage:
    rule_version: RuleVersion
    candidate: RuleCandidate | None
    structure: ArticleStructure | None
    article: BlogArticle | None


@dataclass(frozen=True)
class _ValidatedBundle:
    profile: RuleApplicabilityProfile
    run: BacktestRun
    result: BacktestResult
    rule_lineages: list[_RuleLineage]


class AuthorValidatedProfileService:
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
        request: AuthorValidatedProfileGenerationRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> AuthorProfileVersionView:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to create an author validated profile draft")

        async with self._session_scope_factory() as session:
            author = await session.get(Authors, request.author_id)
            if author is None:
                raise LookupError("author not found")

            profile_map = await self._load_profiles(session, request.applicability_profile_ids)
            run_map = await self._load_runs(session, profile_map.values())
            result_map = await self._load_results(session, profile_map.values())
            rule_lineages = await self._load_rule_lineages(session, profile_map.values(), run_map.values())

            issues: list[dict[str, Any]] = []
            bundles: list[_ValidatedBundle] = []
            for profile_id in request.applicability_profile_ids:
                profile = profile_map.get(profile_id)
                if profile is None:
                    issues.append(
                        {
                            "lane": "backtest_validation",
                            "reason": "未找到正式适用性画像。",
                            "rule_applicability_profile_id": str(profile_id),
                        }
                    )
                    continue
                bundle, bundle_issues = self._resolve_bundle(
                    author=author,
                    profile=profile,
                    run_map=run_map,
                    result_map=result_map,
                    rule_lineages=rule_lineages,
                )
                issues.extend(bundle_issues)
                if bundle is not None:
                    bundles.append(bundle)

            if not bundles:
                draft_request = self._build_insufficient_request(request, issues)
                return await self._profile_service.create_draft(draft_request, actor_id=actor_id, actor_role=actor_role)

            draft_request = self._build_draft_request(request=request, bundles=bundles, issues=issues)
        return await self._profile_service.create_draft(draft_request, actor_id=actor_id, actor_role=actor_role)

    async def _load_profiles(
        self,
        session: AsyncSession,
        profile_ids: list[UUID],
    ) -> dict[UUID, RuleApplicabilityProfile]:
        stmt = select(RuleApplicabilityProfile).where(RuleApplicabilityProfile.profile_id.in_(profile_ids))
        rows = list((await session.execute(stmt)).scalars().all())
        return {row.profile_id: row for row in rows}

    async def _load_runs(
        self,
        session: AsyncSession,
        profiles: Any,
    ) -> dict[str, BacktestRun]:
        run_ids = [run_id for profile in profiles for run_id in self._string_list(profile.source_backtest_run_ids)]
        if not run_ids:
            return {}
        stmt = select(BacktestRun).where(BacktestRun.run_id.in_([UUID(value) for value in run_ids]))
        rows = list((await session.execute(stmt)).scalars().all())
        return {str(row.run_id): row for row in rows}

    async def _load_results(
        self,
        session: AsyncSession,
        profiles: Any,
    ) -> dict[str, BacktestResult]:
        result_ids = [result_id for profile in profiles for result_id in self._string_list(profile.source_backtest_result_ids)]
        if not result_ids:
            return {}
        stmt = select(BacktestResult).where(BacktestResult.result_id.in_([UUID(value) for value in result_ids]))
        rows = list((await session.execute(stmt)).scalars().all())
        return {str(row.result_id): row for row in rows}

    async def _load_rule_lineages(
        self,
        session: AsyncSession,
        profiles: Any,
        runs: Any,
    ) -> dict[str, _RuleLineage]:
        rule_version_ids = {
            str(rule_version_id)
            for profile in profiles
            for rule_version_id in (
                ([profile.rule_version_id] if profile.rule_version_id else [])
                + [UUID(value) for value in self._string_list(profile.frozen_rule_version_ids)]
            )
        }
        rule_version_ids.update(
            str(run.rule_version_id)
            for run in runs
            if run.rule_version_id is not None
        )
        if not rule_version_ids:
            return {}
        stmt = (
            select(RuleVersion, RuleCandidate, ArticleStructure, BlogArticle)
            .outerjoin(RuleCandidate, RuleCandidate.rule_candidate_id == RuleVersion.source_candidate_id)
            .outerjoin(ArticleStructure, ArticleStructure.article_structure_id == RuleCandidate.article_structure_id)
            .outerjoin(BlogArticle, BlogArticle.id == RuleCandidate.source_article_id)
            .where(RuleVersion.rule_version_id.in_([UUID(value) for value in sorted(rule_version_ids)]))
        )
        rows = (await session.execute(stmt)).all()
        return {
            str(rule_version.rule_version_id): _RuleLineage(
                rule_version=rule_version,
                candidate=candidate,
                structure=structure,
                article=article,
            )
            for rule_version, candidate, structure, article in rows
        }

    def _resolve_bundle(
        self,
        *,
        author: Authors,
        profile: RuleApplicabilityProfile,
        run_map: dict[str, BacktestRun],
        result_map: dict[str, BacktestResult],
        rule_lineages: dict[str, _RuleLineage],
    ) -> tuple[_ValidatedBundle | None, list[dict[str, Any]]]:
        issues: list[dict[str, Any]] = []
        run_ids = self._string_list(profile.source_backtest_run_ids)
        result_ids = self._string_list(profile.source_backtest_result_ids)
        result_fingerprints = set(self._string_list(profile.source_result_fingerprints))
        if len(run_ids) != 1 or len(result_ids) != 1:
            issues.append(
                {
                    "lane": "backtest_validation",
                    "reason": "正式适用性画像缺少唯一回测运行或结果绑定。",
                    "rule_applicability_profile_id": str(profile.profile_id),
                }
            )
            return None, issues
        run = run_map.get(run_ids[0])
        result = result_map.get(result_ids[0])
        if run is None or result is None:
            issues.append(
                {
                    "lane": "backtest_validation",
                    "reason": "正式回测运行或结果不存在，无法生成作者验证画像。",
                    "rule_applicability_profile_id": str(profile.profile_id),
                    "backtest_run_id": run_ids[0],
                    "backtest_result_id": result_ids[0],
                }
            )
            return None, issues
        if str(result.run_id) != str(run.run_id):
            issues.append(
                {
                    "lane": "backtest_validation",
                    "reason": "正式回测结果与运行绑定不一致。",
                    "rule_applicability_profile_id": str(profile.profile_id),
                }
            )
            return None, issues
        if profile.dataset_fingerprint and profile.dataset_fingerprint != run.dataset_fingerprint:
            issues.append(
                {
                    "lane": "backtest_validation",
                    "reason": "数据集指纹不一致，不能把证据写入正式作者验证画像。",
                    "rule_applicability_profile_id": str(profile.profile_id),
                }
            )
            return None, issues
        if result.result_fingerprint not in result_fingerprints:
            issues.append(
                {
                    "lane": "backtest_validation",
                    "reason": "回测结果指纹与正式适用性画像绑定不一致。",
                    "rule_applicability_profile_id": str(profile.profile_id),
                }
            )
            return None, issues
        if profile.level_policy_version and profile.level_policy_version != (result.level_policy_version or run.level_policy_version):
            issues.append(
                {
                    "lane": "backtest_validation",
                    "reason": "Level policy 版本不一致，当前证据不能进入正式作者验证画像。",
                    "rule_applicability_profile_id": str(profile.profile_id),
                }
            )
            return None, issues

        lineages = [
            lineage
            for rule_id in self._resolved_rule_version_ids(profile, run)
            if (lineage := rule_lineages.get(rule_id)) is not None
        ]
        if not lineages:
            issues.append(
                {
                    "lane": "backtest_validation",
                    "reason": "无法定位正式规则版本来源。",
                    "rule_applicability_profile_id": str(profile.profile_id),
                }
            )
            return None, issues
        if not all(self._is_author_aligned(author, lineage) for lineage in lineages):
            issues.append(
                {
                    "lane": "backtest_validation",
                    "reason": "部分正式适用性画像来源未对齐当前作者。",
                    "rule_applicability_profile_id": str(profile.profile_id),
                }
            )
            return None, issues

        return _ValidatedBundle(profile=profile, run=run, result=result, rule_lineages=lineages), issues

    def _build_draft_request(
        self,
        *,
        request: AuthorValidatedProfileGenerationRequest,
        bundles: list[_ValidatedBundle],
        issues: list[dict[str, Any]],
    ) -> AuthorProfileDraftRequest:
        strong_rule_types = self._aggregate_rule_types(bundles, recommendation_status="recommended")
        weak_rule_types = self._aggregate_rule_types(bundles, recommendation_status="not_recommended")
        strong_market_states = self._aggregate_market_states(bundles, lane="applicable")
        weak_market_states = self._aggregate_market_states(bundles, lane="blocked")
        common_failure_modes = self._aggregate_failure_modes(bundles)
        data_coverage = self._data_coverage(bundles)
        sample_count = self._sample_count(bundles)
        overall_confidence = self._overall_confidence(bundles)
        limitations = self._limit_list(bundles, issues)
        quality_status = self._quality_status(bundles, issues)
        conclusions = self._conclusions(
            strong_rule_types=strong_rule_types,
            weak_rule_types=weak_rule_types,
            strong_market_states=strong_market_states,
            weak_market_states=weak_market_states,
            overall_confidence=overall_confidence,
        )
        evidence = {
            "backtest_validation": {
                "rule_applicability_profiles": [self._profile_evidence(bundle) for bundle in bundles],
                "issues": issues,
            },
            "data_coverage": data_coverage,
            "limitations": limitations,
        }
        profile_payload = {
            "validated_profile": {
                "summary_mode": AUTHOR_VALIDATED_PROFILE_AGGREGATION_VERSION,
                "strong_rule_types": strong_rule_types,
                "weak_rule_types": weak_rule_types,
                "strong_market_states": strong_market_states,
                "weak_market_states": weak_market_states,
                "common_failure_modes": common_failure_modes,
                "data_coverage": data_coverage,
                "sample_count": sample_count,
                "confidence": {
                    "overall": overall_confidence,
                    "basis": [
                        f"validated_profiles={len(bundles)}",
                        f"insufficient_sample_profiles={sample_count['insufficient_sample_profiles']}",
                        f"kaipan_limitation_profiles={data_coverage['kaipan_limitation_profiles']}",
                    ],
                },
                "limitations": limitations,
                "evidence": evidence,
            },
            "quality": {
                "status": "complete" if quality_status == QualityStatus.complete else "partial",
                "warnings": limitations,
                "issues": issues,
            },
            "conclusions": conclusions,
            "limitations": limitations,
        }
        return AuthorProfileDraftRequest(
            author_id=request.author_id,
            author_profile_id=request.author_profile_id,
            parent_version_id=request.parent_version_id,
            supersedes_version_id=request.supersedes_version_id,
            profile_kind=AuthorProfileKind.validated,
            schema_version=AUTHOR_VALIDATED_PROFILE_SCHEMA_VERSION,
            payload=profile_payload,
            evidence=evidence,
            source_applicability_profile_ids={
                "requested_profile_ids": [str(profile_id) for profile_id in request.applicability_profile_ids],
                "resolved_profile_ids": [str(bundle.profile.profile_id) for bundle in bundles],
                "resolved_applicability_profile_ids": [str(bundle.profile.applicability_profile_id) for bundle in bundles],
                "result_fingerprints": [bundle.result.result_fingerprint for bundle in bundles],
            },
            source_backtest_run_ids={
                "resolved_run_ids": [str(bundle.run.run_id) for bundle in bundles],
                "dataset_fingerprints": [bundle.run.dataset_fingerprint for bundle in bundles],
                "market_snapshot_fingerprints": [fingerprint for bundle in bundles for fingerprint in (bundle.run.market_snapshot_fingerprints or [])],
            },
            source_backtest_result_ids={
                "resolved_result_ids": [str(bundle.result.result_id) for bundle in bundles],
                "result_fingerprints": [bundle.result.result_fingerprint for bundle in bundles],
            },
            source_versions={
                "aggregation_version": AUTHOR_VALIDATED_PROFILE_AGGREGATION_VERSION,
                "profile_schema_version": AUTHOR_VALIDATED_PROFILE_SCHEMA_VERSION,
                "level_policy_versions": sorted({bundle.profile.level_policy_version or bundle.run.level_policy_version for bundle in bundles}),
                "market_state_model_versions": sorted({bundle.profile.market_state_model_version or bundle.result.market_state_model_version for bundle in bundles if bundle.profile.market_state_model_version or bundle.result.market_state_model_version}),
                "market_state_source_versions": sorted({bundle.profile.market_state_source_version or bundle.result.market_state_source_version for bundle in bundles if bundle.profile.market_state_source_version or bundle.result.market_state_source_version}),
                "recommendation_policy_versions": sorted({bundle.profile.recommendation_policy_version for bundle in bundles if bundle.profile.recommendation_policy_version}),
            },
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
        request: AuthorValidatedProfileGenerationRequest,
        issues: list[dict[str, Any]],
    ) -> AuthorProfileDraftRequest:
        limitations = self._dedupe(
            [
                AUTHOR_VALIDATED_PROFILE_LIMITATION,
                "当前没有足够的正式验证证据，系统只保留待补充的草稿。",
                *[item["reason"] for item in issues if isinstance(item.get("reason"), str)],
            ]
        )
        return AuthorProfileDraftRequest(
            author_id=request.author_id,
            author_profile_id=request.author_profile_id,
            parent_version_id=request.parent_version_id,
            supersedes_version_id=request.supersedes_version_id,
            profile_kind=AuthorProfileKind.validated,
            schema_version=AUTHOR_VALIDATED_PROFILE_SCHEMA_VERSION,
            payload={
                "validated_profile": {
                    "summary_mode": AUTHOR_VALIDATED_PROFILE_AGGREGATION_VERSION,
                    "strong_rule_types": [],
                    "weak_rule_types": [],
                    "strong_market_states": [],
                    "weak_market_states": [],
                    "common_failure_modes": [],
                    "data_coverage": {"total_applicability_profiles": 0, "kaipan_limitation_profiles": 0},
                    "sample_count": {"total": 0, "eligible": 0, "evaluated": 0, "insufficient_sample_profiles": 0},
                    "confidence": {"overall": 0.0, "basis": ["insufficient_evidence"]},
                    "limitations": limitations,
                    "evidence": {"backtest_validation": {"issues": issues}},
                },
                "quality": {
                    "status": "insufficient_evidence",
                    "warnings": limitations,
                    "issues": issues,
                },
                "conclusions": [],
                "limitations": limitations,
            },
            evidence={"backtest_validation": {"issues": issues}},
            source_applicability_profile_ids={
                "requested_profile_ids": [str(profile_id) for profile_id in request.applicability_profile_ids],
                "resolved_profile_ids": [],
            },
            source_versions={
                "aggregation_version": AUTHOR_VALIDATED_PROFILE_AGGREGATION_VERSION,
                "status": "insufficient_evidence",
            },
            evidence_from=request.evidence_from,
            evidence_to=request.evidence_to,
            effective_from=request.effective_from,
            effective_to=request.effective_to,
            quality_status=QualityStatus.unresolved,
            reason=request.reason,
            source_surface=request.source_surface,
        )

    def _aggregate_rule_types(self, bundles: list[_ValidatedBundle], *, recommendation_status: str) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for bundle in bundles:
            if bundle.profile.recommendation_status != recommendation_status or bundle.profile.insufficient_sample_status != "sufficient":
                continue
            for lineage in bundle.rule_lineages:
                entry = grouped.setdefault(
                    lineage.rule_version.rule_type,
                    {
                        "rule_type": lineage.rule_version.rule_type,
                        "count": 0,
                        "sample_count": 0,
                        "confidence_total": 0.0,
                        "profile_ids": [],
                    },
                )
                entry["count"] += 1
                entry["sample_count"] += int(bundle.profile.sample_count or 0)
                entry["confidence_total"] += float(bundle.profile.confidence or 0.0)
                entry["profile_ids"].append(str(bundle.profile.profile_id))
        return [
            {
                "rule_type": key,
                "count": value["count"],
                "sample_count": value["sample_count"],
                "confidence": round(value["confidence_total"] / max(value["count"], 1), 2),
                "profile_ids": sorted(dict.fromkeys(value["profile_ids"])),
            }
            for key, value in sorted(grouped.items(), key=lambda item: (-item[1]["count"], item[0]))
        ]

    def _aggregate_market_states(self, bundles: list[_ValidatedBundle], *, lane: str) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for bundle in bundles:
            records = bundle.profile.applicable_regimes if lane == "applicable" else bundle.profile.blocked_regimes
            for record in records:
                if record.get("low_sample"):
                    continue
                label = str(record.get("regime_label") or "").strip()
                if not label:
                    continue
                entry = grouped.setdefault(
                    label,
                    {
                        "market_state": label,
                        "count": 0,
                        "sample_count": 0,
                        "confidence_total": 0.0,
                        "profile_ids": [],
                    },
                )
                entry["count"] += 1
                entry["sample_count"] += int(record.get("sample_count") or 0)
                entry["confidence_total"] += float(record.get("confidence") or 0.0)
                entry["profile_ids"].append(str(bundle.profile.profile_id))
        return [
            {
                "market_state": key,
                "count": value["count"],
                "sample_count": value["sample_count"],
                "confidence": round(value["confidence_total"] / max(value["count"], 1), 2),
                "profile_ids": sorted(dict.fromkeys(value["profile_ids"])),
            }
            for key, value in sorted(grouped.items(), key=lambda item: (-item[1]["count"], item[0]))
        ]

    def _aggregate_failure_modes(self, bundles: list[_ValidatedBundle]) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for bundle in bundles:
            reasons = [record.get("reason") for record in bundle.profile.blocked_regimes] + list(bundle.profile.warnings or [])
            for limitation in bundle.profile.limitations or []:
                if "Kaipan" in limitation or "样本" in limitation:
                    reasons.append(limitation)
            for reason in reasons:
                if not reason:
                    continue
                entry = grouped.setdefault(
                    str(reason),
                    {
                        "reason": str(reason),
                        "count": 0,
                        "profile_ids": [],
                    },
                )
                entry["count"] += 1
                entry["profile_ids"].append(str(bundle.profile.profile_id))
        return [
            {
                "reason": key,
                "count": value["count"],
                "profile_ids": sorted(dict.fromkeys(value["profile_ids"])),
            }
            for key, value in sorted(grouped.items(), key=lambda item: (-item[1]["count"], item[0]))
        ]

    def _data_coverage(self, bundles: list[_ValidatedBundle]) -> dict[str, Any]:
        return {
            "total_applicability_profiles": len(bundles),
            "complete_profiles": sum(1 for bundle in bundles if bundle.profile.quality_status == "complete"),
            "partial_profiles": sum(1 for bundle in bundles if bundle.profile.quality_status != "complete"),
            "kaipan_limitation_profiles": sum(1 for bundle in bundles if self._has_kaipan_limitation(bundle)),
            "market_state_limited_profiles": sum(
                1
                for bundle in bundles
                if ((bundle.result.coverage_json or {}).get("market_state") or {}).get("state") != "ready"
            ),
            "requested_levels": self._count_values(bundle.profile.requested_level for bundle in bundles),
            "effective_levels": self._count_values(bundle.profile.effective_level for bundle in bundles),
        }

    def _sample_count(self, bundles: list[_ValidatedBundle]) -> dict[str, Any]:
        return {
            "total": sum(int(bundle.profile.sample_count or 0) for bundle in bundles),
            "eligible": sum(int(bundle.profile.eligible_sample_count or 0) for bundle in bundles),
            "evaluated": sum(int(bundle.profile.evaluated_sample_count or 0) for bundle in bundles),
            "insufficient_sample_profiles": sum(
                1 for bundle in bundles if bundle.profile.insufficient_sample_status == "insufficient_sample"
            ),
        }

    def _overall_confidence(self, bundles: list[_ValidatedBundle]) -> float:
        total_weight = 0
        weighted_confidence = 0.0
        for bundle in bundles:
            weight = max(int(bundle.profile.sample_count or 0), 1)
            total_weight += weight
            weighted_confidence += float(bundle.profile.confidence or 0.0) * weight
        return round(weighted_confidence / max(total_weight, 1), 2)

    def _limit_list(self, bundles: list[_ValidatedBundle], issues: list[dict[str, Any]]) -> list[str]:
        limitations = [AUTHOR_VALIDATED_PROFILE_LIMITATION]
        limitations.extend(str(item["reason"]) for item in issues if item.get("reason"))
        for bundle in bundles:
            limitations.extend(list(bundle.profile.limitations or []))
            limitations.extend(list(bundle.profile.warnings or []))
        if any(bundle.profile.insufficient_sample_status == "insufficient_sample" for bundle in bundles):
            limitations.append("样本不足时只能保留 insufficient_sample 和低置信度结论，不能给出强结论。")
        if any(self._has_kaipan_limitation(bundle) for bundle in bundles):
            limitations.append("缺失 Kaipan 数据只会记为覆盖限制，不会被当成规则失败。")
        return self._dedupe(limitations)

    def _quality_status(self, bundles: list[_ValidatedBundle], issues: list[dict[str, Any]]) -> QualityStatus:
        if issues:
            return QualityStatus.partial
        if any(bundle.profile.quality_status != "complete" or bundle.profile.insufficient_sample_status != "sufficient" for bundle in bundles):
            return QualityStatus.partial
        return QualityStatus.complete

    def _conclusions(
        self,
        *,
        strong_rule_types: list[dict[str, Any]],
        weak_rule_types: list[dict[str, Any]],
        strong_market_states: list[dict[str, Any]],
        weak_market_states: list[dict[str, Any]],
        overall_confidence: float,
    ) -> list[dict[str, Any]]:
        conclusions: list[dict[str, Any]] = []
        if strong_rule_types:
            item = strong_rule_types[0]
            conclusions.append(
                self._conclusion(
                    text=f"验证观察显示 {item['rule_type']} 类规则更容易保持稳定。",
                    evidence=[{"lane": "backtest_validation", "rule_type": item["rule_type"], "profile_ids": item["profile_ids"]}],
                    confidence=overall_confidence,
                )
            )
        if weak_rule_types:
            item = weak_rule_types[0]
            conclusions.append(
                self._conclusion(
                    text=f"验证观察显示 {item['rule_type']} 类规则更容易出现失效。",
                    evidence=[{"lane": "backtest_validation", "rule_type": item["rule_type"], "profile_ids": item["profile_ids"]}],
                    confidence=overall_confidence,
                )
            )
        if strong_market_states:
            item = strong_market_states[0]
            conclusions.append(
                self._conclusion(
                    text=f"正式验证证据更支持在 {item['market_state']} 这类市场状态下使用相关规则。",
                    evidence=[{"lane": "backtest_validation", "market_state": item["market_state"], "profile_ids": item["profile_ids"]}],
                    confidence=overall_confidence,
                )
            )
        if weak_market_states:
            item = weak_market_states[0]
            conclusions.append(
                self._conclusion(
                    text=f"{item['market_state']} 这类市场状态下更容易出现验证限制或失效。",
                    evidence=[{"lane": "backtest_validation", "market_state": item["market_state"], "profile_ids": item["profile_ids"]}],
                    confidence=overall_confidence,
                )
            )
        return conclusions

    def _conclusion(self, *, text: str, evidence: list[dict[str, Any]], confidence: float) -> dict[str, Any]:
        return {
            "text": text,
            "evidence": evidence,
            "confidence": confidence,
            "provenance": {"lane": "backtest_validation"},
            "version_binding": {
                "schema_version": AUTHOR_VALIDATED_PROFILE_SCHEMA_VERSION,
                "aggregation_version": AUTHOR_VALIDATED_PROFILE_AGGREGATION_VERSION,
            },
        }

    def _profile_evidence(self, bundle: _ValidatedBundle) -> dict[str, Any]:
        return {
            "rule_applicability_profile_id": str(bundle.profile.profile_id),
            "applicability_profile_id": str(bundle.profile.applicability_profile_id),
            "backtest_run_id": str(bundle.run.run_id),
            "backtest_result_id": str(bundle.result.result_id),
            "result_fingerprint": bundle.result.result_fingerprint,
            "dataset_fingerprint": bundle.run.dataset_fingerprint,
            "market_snapshot_fingerprints": bundle.run.market_snapshot_fingerprints or [],
            "requested_level": bundle.profile.requested_level,
            "effective_level": bundle.profile.effective_level,
            "level_policy_version": bundle.profile.level_policy_version or bundle.run.level_policy_version,
            "market_state_model_version": bundle.profile.market_state_model_version or bundle.result.market_state_model_version,
            "market_state_source_version": bundle.profile.market_state_source_version or bundle.result.market_state_source_version,
            "recommendation_status": bundle.profile.recommendation_status,
            "confidence": bundle.profile.confidence,
            "sample_count": bundle.profile.sample_count,
            "coverage": bundle.profile.coverage,
        }

    def _resolved_rule_version_ids(self, profile: RuleApplicabilityProfile, run: BacktestRun) -> list[str]:
        rule_ids = self._string_list(profile.frozen_rule_version_ids)
        if profile.rule_version_id:
            rule_ids.append(str(profile.rule_version_id))
        if run.rule_version_id:
            rule_ids.append(str(run.rule_version_id))
        return list(dict.fromkeys(rule_ids))

    def _is_author_aligned(self, author: Authors, lineage: _RuleLineage) -> bool:
        if lineage.article is None or lineage.structure is None or lineage.candidate is None:
            return False
        article_matches = lineage.article.source == author.source and lineage.article.author_id == author.source_author_key
        structure_matches = (lineage.structure.payload or {}).get("author_id") == author.source_author_key
        return article_matches and structure_matches

    def _has_kaipan_limitation(self, bundle: _ValidatedBundle) -> bool:
        texts = [*list(bundle.profile.limitations or []), *list(bundle.profile.warnings or [])]
        coverage = bundle.result.coverage_json or {}
        kaipan_state = (coverage.get("kaipan") or {}).get("state")
        return kaipan_state == "insufficient_coverage" or any("Kaipan" in text for text in texts)

    def _count_values(self, values: Any) -> dict[str, int]:
        counted: dict[str, int] = {}
        for value in values:
            if not value:
                continue
            counted[str(value)] = counted.get(str(value), 0) + 1
        return counted

    def _dedupe(self, values: list[str]) -> list[str]:
        return [item for item in dict.fromkeys(values) if item]

    def _string_list(self, values: Any) -> list[str]:
        if not values:
            return []
        if isinstance(values, list):
            return [str(item) for item in values if item]
        return [str(values)]
