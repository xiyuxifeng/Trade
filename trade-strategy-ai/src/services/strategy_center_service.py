from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.stage2_writer_routing import canonical_write_scope
from src.db.repositories.strategy_repo import StrategyRepository
from src.db.session import get_session_factory
from src.domain.enums import AuthorProfileKind, FormalLifecycleState, QualityStatus
from src.models.stage2_canonical import Strategy, StrategyRuleMembership, StrategyVersion


STATE_LABELS = {
    FormalLifecycleState.draft: "草稿",
    FormalLifecycleState.pending_review: "待审核",
    FormalLifecycleState.in_review: "审核中",
    FormalLifecycleState.approved: "已审核",
    FormalLifecycleState.published: "已发布",
    FormalLifecycleState.archived: "已归档",
    FormalLifecycleState.rejected: "已驳回",
    FormalLifecycleState.superseded: "已被替代",
}


class StrategyRuleMembershipInput(BaseModel):
    rule_version_id: UUID
    base_weight: float | None = None
    status: str | None = "active"
    configuration_json: dict[str, Any] = Field(default_factory=dict)


class StrategyDraftRequest(BaseModel):
    strategy_id: UUID | None = None
    business_key: str
    schema_version: str
    title: str
    summary: str | None = None
    rule_memberships: list[StrategyRuleMembershipInput]
    author_method_profile_version_id: UUID
    author_rule_profile_version_id: UUID
    author_validated_profile_version_id: UUID
    risk_policy_json: dict[str, Any] = Field(default_factory=dict)
    selection_policy_json: dict[str, Any] = Field(default_factory=dict)
    universe_json: dict[str, Any] = Field(default_factory=dict)
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    quality_status: QualityStatus = QualityStatus.verified
    reason: str | None = None
    source_surface: str = "/strategies"

    @field_validator("rule_memberships")
    @classmethod
    def _validate_rule_memberships(cls, memberships: list[StrategyRuleMembershipInput]) -> list[StrategyRuleMembershipInput]:
        if not memberships:
            raise ValueError("至少选择一条正式规则后才能保存策略草稿。")
        return memberships


class StrategyTransitionRequest(BaseModel):
    reason: str | None = None
    source_surface: str = "/strategies"


class StrategyCurrentStatusView(BaseModel):
    is_current: bool
    current_version_id: str | None = None
    previous_current_version_id: str | None = None


class StrategyEvidenceView(BaseModel):
    dataset_snapshot_id: str | None = None
    market_snapshot_ids: list[str] = Field(default_factory=list)
    rule_applicability_profile_ids: list[str] = Field(default_factory=list)
    backtest_run_ids: list[str] = Field(default_factory=list)
    backtest_result_ids: list[str] = Field(default_factory=list)
    evidence_fingerprint: str | None = None


class StrategyVersionView(BaseModel):
    strategy_version_id: str
    strategy_id: str
    business_key: str
    title: str
    summary: str | None = None
    version_no: int
    lifecycle_state: str
    lifecycle_label: str
    review_status: str
    status_state: str
    schema_version: str
    quality_status: str
    rule_pool: list[dict[str, Any]] = Field(default_factory=list)
    profiles: dict[str, Any] = Field(default_factory=dict)
    policies: dict[str, Any] = Field(default_factory=dict)
    evidence: StrategyEvidenceView
    current_status: StrategyCurrentStatusView
    published_at: str | None = None
    partial_reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


def _now() -> datetime:
    return datetime.now(UTC)


def _state(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


class StrategyCenterService:
    def __init__(self, *, repository: StrategyRepository | None = None, session_scope_factory: Any | None = None) -> None:
        self.repository = repository or StrategyRepository()
        self._session_scope_factory = session_scope_factory or self._default_session_scope_factory

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

    async def create_draft(self, request: StrategyDraftRequest, *, actor_id: str, actor_role: str) -> StrategyVersionView:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to create a strategy draft")
        async with self._session_scope_factory() as session:
            return await self._create_draft_in_session(session, request, actor_id=actor_id, actor_role=actor_role)

    async def _create_draft_in_session(
        self,
        session: AsyncSession,
        request: StrategyDraftRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> StrategyVersionView:
        strategy = await self._resolve_strategy(session, request=request, actor_id=actor_id)
        await self._validate_canonical_dependencies(session, request)
        version = StrategyVersion(
            strategy_version_id=uuid4(),
            strategy_id=strategy.strategy_id,
            version_no=await self.repository.next_version_no(session, strategy_id=strategy.strategy_id),
            schema_version=request.schema_version,
            lifecycle_state=FormalLifecycleState.draft,
            title=request.title,
            summary=request.summary,
            risk_policy_json=request.risk_policy_json,
            selection_policy_json=request.selection_policy_json,
            universe_json=request.universe_json,
            author_method_profile_version_id=request.author_method_profile_version_id,
            author_rule_profile_version_id=request.author_rule_profile_version_id,
            author_validated_profile_version_id=request.author_validated_profile_version_id,
            evidence_json={**request.evidence_json, "evidence_fingerprint": _fingerprint(request.evidence_json)},
            quality_status=request.quality_status,
            review_status="draft",
            created_by=actor_id,
            updated_by=actor_id,
        )
        memberships = [
            StrategyRuleMembership(
                membership_id=uuid4(),
                strategy_version_id=version.strategy_version_id,
                rule_version_id=item.rule_version_id,
                base_weight=item.base_weight,
                status=item.status,
                configuration_json=item.configuration_json,
            )
            for item in request.rule_memberships
        ]
        with canonical_write_scope("strategy", "StrategyCenterService.create_draft"):
            await self.repository.add_version(session, version)
            await self.repository.replace_rule_memberships(
                session,
                strategy_version_id=version.strategy_version_id,
                memberships=memberships,
            )
            await self.repository.record_audit(
                session,
                version=version,
                transition="created_draft",
                actor_id=actor_id,
                actor_role=actor_role,
                reason=request.reason,
                source_surface=request.source_surface,
                before_state=None,
                after_state=self._audit_state(version, strategy.current_published_version_id),
            )
        return await self._to_view(session, version, strategy)

    async def list_versions(self, *, actor_id: str, actor_role: str, limit: int = 50) -> dict[str, Any]:
        del actor_id
        if actor_role not in {"viewer", "operator", "admin"}:
            raise PermissionError("viewer permission is required to view strategies")
        async with self._session_scope_factory() as session:
            versions = await self.repository.list_versions(session, limit=limit)
            items: list[dict[str, Any]] = []
            current_strategy: dict[str, Any] | None = None
            for version in versions:
                strategy = await self.repository.get_strategy(session, version.strategy_id)
                assert strategy is not None
                items.append((await self._to_view(session, version, strategy)).model_dump(mode="json"))
                if strategy.current_published_version_id:
                    current_strategy = {
                        "business_key": strategy.business_key,
                        "current_version_id": str(strategy.current_published_version_id),
                    }
            return {
                "state": "empty" if not items else "ready",
                "current_strategy": current_strategy,
                "items": items,
                "count": len(items),
            }

    async def get_version(self, version_id: str | UUID, *, actor_id: str, actor_role: str) -> StrategyVersionView:
        del actor_id
        if actor_role not in {"viewer", "operator", "admin"}:
            raise PermissionError("viewer permission is required to view strategies")
        async with self._session_scope_factory() as session:
            version = await self.repository.get_version(session, version_id)
            if version is None:
                raise LookupError("strategy version not found")
            strategy = await self.repository.get_strategy(session, version.strategy_id)
            assert strategy is not None
            return await self._to_view(session, version, strategy)

    async def submit_for_review(
        self,
        version_id: str | UUID,
        request: StrategyTransitionRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> StrategyVersionView:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to submit a strategy for review")
        return await self._transition(
            version_id,
            from_states={FormalLifecycleState.draft},
            to_state=FormalLifecycleState.pending_review,
            review_status="pending_review",
            transition="submitted_for_review",
            request=request,
            actor_id=actor_id,
            actor_role=actor_role,
        )

    async def publish(
        self,
        version_id: str | UUID,
        request: StrategyTransitionRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> StrategyVersionView:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to publish a strategy")
        async with self._session_scope_factory() as session:
            version = await self.repository.get_version(session, version_id)
            if version is None:
                raise LookupError("strategy version not found")
            if version.lifecycle_state not in {FormalLifecycleState.pending_review, FormalLifecycleState.in_review, FormalLifecycleState.approved}:
                raise ValueError("只有待审核或已审核的策略版本可以发布。")
            strategy = await self.repository.get_strategy(session, version.strategy_id)
            assert strategy is not None
            previous_current = strategy.current_published_version_id
            before = self._audit_state(version, previous_current)
            now = _now()
            version.lifecycle_state = FormalLifecycleState.published
            version.review_status = "published"
            version.review_reason = request.reason
            version.reviewed_by = actor_id
            version.reviewed_at = now
            version.published_by = actor_id
            version.published_at = now
            version.updated_by = actor_id
            with canonical_write_scope("strategy", "StrategyCenterService.publish"):
                await self.repository.set_current_published_version(
                    session,
                    strategy=strategy,
                    version_id=version.strategy_version_id,
                    actor_id=actor_id,
                    updated_at=now,
                )
                await self.repository.record_audit(
                    session,
                    version=version,
                    transition="published",
                    actor_id=actor_id,
                    actor_role=actor_role,
                    reason=request.reason,
                    source_surface=request.source_surface,
                    before_state=before,
                    after_state=self._audit_state(version, strategy.current_published_version_id, previous_current),
                )
            return await self._to_view(session, version, strategy, previous_current=previous_current)

    async def get_draft_options(self, *, actor_id: str, actor_role: str) -> dict[str, Any]:
        del actor_id
        if actor_role not in {"viewer", "operator", "admin"}:
            raise PermissionError("viewer permission is required to view strategy draft options")
        async with self._session_scope_factory() as session:
            rules = await self.repository.list_published_rule_versions(session)
            method_profiles = await self.repository.list_published_author_profiles(session, profile_kind=AuthorProfileKind.method)
            rule_profiles = await self.repository.list_published_author_profiles(session, profile_kind=AuthorProfileKind.rule)
            validated_profiles = await self.repository.list_published_author_profiles(session, profile_kind=AuthorProfileKind.validated)
            datasets = await self.repository.list_ready_dataset_snapshots(session)
            snapshots = await self.repository.list_market_snapshots(session)
            applicability = await self.repository.list_published_rule_applicability_profiles(session)
            return {
                "rule_options": [
                    {
                        "rule_version_id": str(rule.rule_version_id),
                        "title": rule.title,
                        "rule_type": rule.rule_type,
                        "canonical_fingerprint": rule.canonical_fingerprint,
                    }
                    for rule in rules
                ],
                "author_profile_options": {
                    "method": [self._profile_option(profile, "作者方法画像") for profile in method_profiles],
                    "rule": [self._profile_option(profile, "作者规则画像") for profile in rule_profiles],
                    "validated": [self._profile_option(profile, "作者验证画像") for profile in validated_profiles],
                },
                "dataset_options": [
                    {
                        "dataset_snapshot_id": str(item.dataset_snapshot_id),
                        "label": f"{item.dataset_type or '数据集'} {item.trade_date.isoformat() if item.trade_date else ''}".strip(),
                        "content_fingerprint": item.content_fingerprint,
                    }
                    for item in datasets
                ],
                "market_snapshot_options": [
                    {
                        "market_snapshot_id": str(item.id),
                        "label": f"{item.trade_date.isoformat()} {item.slot} 市场快照",
                        "content_fingerprint": item.content_fingerprint,
                    }
                    for item in snapshots
                ],
                "rule_applicability_options": [
                    {
                        "applicability_profile_id": str(item.applicability_profile_id),
                        "label": f"{item.rule_id} 适用性画像",
                        "dataset_snapshot_id": str(item.dataset_snapshot_id) if item.dataset_snapshot_id else None,
                    }
                    for item in applicability
                ],
            }

    async def _resolve_strategy(self, session: AsyncSession, *, request: StrategyDraftRequest, actor_id: str) -> Strategy:
        strategy: Strategy | None = None
        if request.strategy_id is not None:
            strategy = await self.repository.get_strategy(session, request.strategy_id)
            if strategy is None:
                raise LookupError("strategy not found")
            if strategy.business_key != request.business_key:
                raise ValueError("strategy_id 与 business_key 不一致，不能写入第二套正式策略事实。")
        else:
            strategy = await self.repository.get_strategy_by_business_key(session, business_key=request.business_key)
        if strategy is not None:
            return strategy
        now = _now()
        strategy = Strategy(
            strategy_id=uuid4(),
            business_key=request.business_key,
            current_published_version_id=None,
            created_at=now,
            created_by=actor_id,
            updated_at=now,
            updated_by=actor_id,
        )
        with canonical_write_scope("strategy", "StrategyCenterService.create_draft"):
            await self.repository.add_strategy(session, strategy)
        return strategy

    async def _validate_canonical_dependencies(self, session: AsyncSession, request: StrategyDraftRequest) -> None:
        published_rules = {str(item.rule_version_id) for item in await self.repository.list_published_rule_versions(session)}
        if any(str(item.rule_version_id) not in published_rules for item in request.rule_memberships):
            raise ValueError("策略草稿只能使用已发布的正式规则版本。")

        method_profiles = {str(item.author_profile_version_id) for item in await self.repository.list_published_author_profiles(session, profile_kind=AuthorProfileKind.method)}
        rule_profiles = {str(item.author_profile_version_id) for item in await self.repository.list_published_author_profiles(session, profile_kind=AuthorProfileKind.rule)}
        validated_profiles = {str(item.author_profile_version_id) for item in await self.repository.list_published_author_profiles(session, profile_kind=AuthorProfileKind.validated)}
        if str(request.author_method_profile_version_id) not in method_profiles:
            raise ValueError("作者方法画像版本不可用。")
        if str(request.author_rule_profile_version_id) not in rule_profiles:
            raise ValueError("作者规则画像版本不可用。")
        if str(request.author_validated_profile_version_id) not in validated_profiles:
            raise ValueError("作者验证画像版本不可用。")

        evidence = request.evidence_json
        dataset_snapshot_id = evidence.get("dataset_snapshot_id")
        if dataset_snapshot_id is not None:
            dataset_ids = {str(item.dataset_snapshot_id) for item in await self.repository.list_ready_dataset_snapshots(session)}
            if str(dataset_snapshot_id) not in dataset_ids:
                raise ValueError("正式数据集快照不可用。")

        snapshot_ids = {str(item.id) for item in await self.repository.list_market_snapshots(session)}
        if any(str(snapshot_id) not in snapshot_ids for snapshot_id in evidence.get("market_snapshot_ids", [])):
            raise ValueError("正式市场快照不可用。")

        applicability_ids = {str(item.applicability_profile_id) for item in await self.repository.list_published_rule_applicability_profiles(session)}
        if any(str(profile_id) not in applicability_ids for profile_id in evidence.get("rule_applicability_profile_ids", [])):
            raise ValueError("正式规则适用性画像不可用。")

    async def _transition(
        self,
        version_id: str | UUID,
        *,
        from_states: set[FormalLifecycleState],
        to_state: FormalLifecycleState,
        review_status: str,
        transition: str,
        request: StrategyTransitionRequest,
        actor_id: str,
        actor_role: str,
    ) -> StrategyVersionView:
        async with self._session_scope_factory() as session:
            version = await self.repository.get_version(session, version_id)
            if version is None:
                raise LookupError("strategy version not found")
            if version.lifecycle_state not in from_states:
                raise ValueError("策略状态未改变，请先确认当前版本状态。")
            strategy = await self.repository.get_strategy(session, version.strategy_id)
            assert strategy is not None
            before = self._audit_state(version, strategy.current_published_version_id)
            version.lifecycle_state = to_state
            version.review_status = review_status
            version.review_reason = request.reason
            version.reviewed_by = actor_id
            version.reviewed_at = _now()
            version.updated_by = actor_id
            with canonical_write_scope("strategy", f"StrategyCenterService.{transition}"):
                await self.repository.record_audit(
                    session,
                    version=version,
                    transition=transition,
                    actor_id=actor_id,
                    actor_role=actor_role,
                    reason=request.reason,
                    source_surface=request.source_surface,
                    before_state=before,
                    after_state=self._audit_state(version, strategy.current_published_version_id),
                )
            return await self._to_view(session, version, strategy)

    async def _to_view(
        self,
        session: AsyncSession,
        version: StrategyVersion,
        strategy: Strategy,
        *,
        previous_current: UUID | None = None,
    ) -> StrategyVersionView:
        memberships = await self.repository.list_rule_memberships(session, strategy_version_id=version.strategy_version_id)
        evidence = version.evidence_json or {}
        rule_pool = [
            {
                "rule_version_id": str(item.rule_version_id),
                "title": None,
                "base_weight": float(item.base_weight) if item.base_weight is not None else None,
                "status": item.status,
                "configuration_json": item.configuration_json,
            }
            for item in memberships
        ]
        return StrategyVersionView(
            strategy_version_id=str(version.strategy_version_id),
            strategy_id=str(version.strategy_id),
            business_key=strategy.business_key,
            title=version.title or strategy.business_key,
            summary=version.summary,
            version_no=version.version_no,
            lifecycle_state=_state(version.lifecycle_state),
            lifecycle_label=STATE_LABELS.get(version.lifecycle_state, _state(version.lifecycle_state)),
            review_status=version.review_status,
            status_state="published" if strategy.current_published_version_id == version.strategy_version_id else _state(version.lifecycle_state),
            schema_version=version.schema_version,
            quality_status=_state(version.quality_status),
            rule_pool=rule_pool,
            profiles={
                "author_method_profile_version_id": str(version.author_method_profile_version_id) if version.author_method_profile_version_id else None,
                "author_rule_profile_version_id": str(version.author_rule_profile_version_id) if version.author_rule_profile_version_id else None,
                "author_validated_profile_version_id": str(version.author_validated_profile_version_id) if version.author_validated_profile_version_id else None,
            },
            policies={
                "risk_policy_json": version.risk_policy_json,
                "selection_policy_json": version.selection_policy_json,
                "universe_json": version.universe_json,
            },
            evidence=StrategyEvidenceView(
                dataset_snapshot_id=str(evidence.get("dataset_snapshot_id")) if evidence.get("dataset_snapshot_id") else None,
                market_snapshot_ids=[str(item) for item in evidence.get("market_snapshot_ids", [])],
                rule_applicability_profile_ids=[str(item) for item in evidence.get("rule_applicability_profile_ids", [])],
                backtest_run_ids=[str(item) for item in evidence.get("backtest_run_ids", [])],
                backtest_result_ids=[str(item) for item in evidence.get("backtest_result_ids", [])],
                evidence_fingerprint=evidence.get("evidence_fingerprint"),
            ),
            current_status=StrategyCurrentStatusView(
                is_current=strategy.current_published_version_id == version.strategy_version_id,
                current_version_id=str(strategy.current_published_version_id) if strategy.current_published_version_id else None,
                previous_current_version_id=str(previous_current) if previous_current else None,
            ),
            published_at=version.published_at.isoformat() if version.published_at else None,
            partial_reasons=[],
            limitations=[],
        )

    def _profile_option(self, profile: Any, label_prefix: str) -> dict[str, Any]:
        return {
            "author_profile_version_id": str(profile.author_profile_version_id),
            "label": f"{label_prefix} v{profile.version_no}",
            "author_id": str(profile.author_id),
        }

    def _audit_state(
        self,
        version: StrategyVersion,
        current_version_id: UUID | None,
        previous_current: UUID | None = None,
    ) -> dict[str, Any]:
        return {
            "strategy_version_id": str(version.strategy_version_id),
            "strategy_id": str(version.strategy_id),
            "lifecycle_state": _state(version.lifecycle_state),
            "review_status": version.review_status,
            "current_version_id": str(current_version_id) if current_version_id else None,
            "previous_current_version_id": str(previous_current) if previous_current else None,
        }
