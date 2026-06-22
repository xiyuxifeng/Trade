from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any, Callable, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.stage2_writer_routing import canonical_write_scope
from src.db.repositories.daily_trading_plan_repo import DailyTradingPlanRepository
from src.db.repositories.market_snapshot_item_repository import MarketSnapshotItemRepository
from src.db.repositories.market_snapshot_section_repository import MarketSnapshotSectionRepository
from src.db.repositories.post_market_review_repo import PostMarketReviewRepository
from src.db.repositories.strategy_repo import StrategyRepository
from src.db.session import get_session_factory
from src.domain.enums import (
    AuthorProfileKind,
    PostMarketReviewState,
    ProposalLifecycleState,
    ProposalType,
    QualityStatus,
    SignalState,
    TradingDayPlanState,
)
from src.domain.lifecycle import DomainLifecycleTransitionError, LifecycleTransitionValidator
from src.models.market_data_snapshot import MarketSnapshot
from src.models.market_data_snapshot_item import MarketSnapshotItem
from src.models.market_data_snapshot_section import MarketSnapshotSection
from src.models.signal import Signal
from src.models.stage2_canonical import (
    AuthorProfileVersion,
    DatasetSnapshot,
    OptimizationProposal,
    PostMarketReview,
    RuleVersion,
    Strategy,
    StrategyRuleMembership,
    StrategyVersion,
)
from src.services.strategy_center_service import StrategyCenterService, StrategyProposalAcceptRequest


POST_CLOSE_ACTUALS_SECTION_ID = "post_close_symbol_ohlcv_actuals"
POST_CLOSE_ACTUALS_CONTRACT_VERSION = "post-close-symbol-ohlcv-actuals-v1"
SIGNAL_OUTCOME_POLICY_VERSION = "stage10-signal-outcome-v1"
STRUCTURED_ATTRIBUTION_POLICY_VERSION = "stage10-structured-attribution-v1"
OPTIMIZATION_PROPOSAL_POLICY_VERSION = "stage10-optimization-proposal-v1"
CoverageState = Literal["ready", "partial", "unavailable", "conflict", "invalid", "insufficient_coverage", "degraded"]
AttributionCategory = Literal[
    "data issue",
    "market-state identification issue",
    "rule issue",
    "strategy-composition issue",
    "execution issue",
    "unattributable",
]
ProposalRecommendationState = Literal[
    "continue_observing",
    "create_draft_review_suggestion",
    "review_author_profile",
]

PROPOSAL_TYPE_LABELS = {
    ProposalType.rule_optimization: "规则优化建议",
    ProposalType.author_profile_revision: "作者画像修订建议",
    ProposalType.strategy_revision: "策略修订建议",
}
PROPOSAL_LIFECYCLE_LABELS = {
    ProposalLifecycleState.draft: "待处理",
    ProposalLifecycleState.in_review: "复核中",
    ProposalLifecycleState.accepted: "已生成草稿",
    ProposalLifecycleState.rejected: "已拒绝",
    ProposalLifecycleState.archived: "已归档",
    ProposalLifecycleState.superseded: "已被替代",
}
PROPOSAL_EVIDENCE_LABELS = {
    "ready": "证据完整",
    "partial": "证据不完整",
    "unavailable": "证据暂不可用",
    "conflict": "证据冲突",
    "invalid": "证据无效",
    "insufficient_coverage": "覆盖不足",
    "degraded": "证据降级",
}
PROPOSAL_RECOMMENDATION_LABELS = {
    "continue_observing": "继续观察",
    "create_draft_review_suggestion": "生成草稿复核建议",
    "review_author_profile": "进入画像复核",
}
AUTHOR_PROFILE_KIND_LABELS = {
    AuthorProfileKind.method: "作者方法画像",
    AuthorProfileKind.rule: "作者规则画像",
    AuthorProfileKind.validated: "作者验证画像",
}


def _json_fingerprint(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _ratio(numerator: Decimal, denominator: Decimal) -> float | None:
    if denominator == 0:
        return None
    return float(numerator / denominator)


def _state(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _entry_price_baseline(signal: Signal) -> tuple[Decimal | None, str | None, str | None]:
    entry_price = signal.entry_price or {}
    if not isinstance(entry_price, dict):
        return None, None, "signal_entry_price_invalid"
    value = entry_price.get("value", entry_price.get("price"))
    baseline = _decimal(value)
    if baseline is not None and baseline > 0:
        return baseline, "signal_entry_price", None
    baseline_policy = entry_price.get("baseline_policy")
    if baseline_policy in {"previous_close_daily_market_signal", "previous_close"}:
        return None, "previous_close_daily_market_signal", None
    if value is not None:
        return None, None, "signal_entry_price_invalid"
    return None, None, "signal_entry_price_missing"


class PostCloseActualRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    previous_close: Decimal | None = None
    volume: Decimal
    turnover: Decimal
    exchange: str | None = None
    asset_type: str | None = None
    frequency: Literal["1d", "daily"]
    adjustment_policy: Literal["none", "qfq", "hfq", "forward_adjusted", "backward_adjusted"]
    source: str
    source_time: datetime | None = None
    captured_at: datetime | None = None
    ingested_at: datetime | None = None
    available_at: datetime
    frozen_at: datetime
    dataset_snapshot_id: str
    dataset_content_fingerprint: str
    row_fingerprint: str
    section_raw_payload_fingerprint: str | None = None
    quality_state: Literal["ready", "available", "verified", "degraded"]
    availability_state: Literal["ready", "available"]
    evidence_window: Literal["daily_bar"]
    actuals_contract_version: str
    intraday_approximation: bool = False

    @field_validator("actuals_contract_version")
    @classmethod
    def _contract_version(cls, value: str) -> str:
        if value != POST_CLOSE_ACTUALS_CONTRACT_VERSION:
            raise ValueError("unexpected actuals contract version")
        return value


class SignalActualResult(BaseModel):
    signal_id: str
    symbol: str
    state: CoverageState
    row: PostCloseActualRow | None = None
    row_fingerprint: str | None = None
    reasons: list[str] = Field(default_factory=list)


class PostCloseActualsReadResult(BaseModel):
    trading_day_plan_id: str
    trade_date: date
    plan_lifecycle_state: str
    post_close_market_snapshot_id: str
    post_close_market_snapshot_snapshot_id: str
    market_snapshot_content_fingerprint: str
    market_snapshot_frozen_at: datetime | None = None
    market_snapshot_available_at: datetime | None = None
    dataset_snapshot_id: str | None = None
    dataset_content_fingerprint: str | None = None
    section_raw_payload_fingerprint: str | None = None
    coverage_state: CoverageState
    signals: list[SignalActualResult]
    missing_symbols: list[str] = Field(default_factory=list)
    conflict_symbols: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class SignalOutcomeEvaluationRequest(BaseModel):
    trading_day_plan_id: str
    post_close_market_snapshot_id: str
    post_close_market_state_id: str | None = None


class SignalOutcomeEvaluationResult(BaseModel):
    state: CoverageState
    post_market_review_id: str | None = None
    trading_day_plan_id: str
    trade_date: date
    post_close_market_snapshot_id: str
    signal_results: list[dict[str, Any]]
    evidence: dict[str, Any]
    happened: str
    affected: str
    repair_guidance: str


class PostMarketReviewView(BaseModel):
    state: CoverageState
    generated: bool
    post_market_review_id: str | None = None
    trading_day_plan_id: str
    trade_date: date
    revision_no: int | None = None
    lifecycle_state: str | None = None
    quality_status: str | None = None
    signal_outcome_state: CoverageState
    attribution_state: CoverageState
    post_close_market_snapshot_id: str | None = None
    post_close_market_state_id: str | None = None
    signal_results: list[dict[str, Any]] = Field(default_factory=list)
    attribution: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    happened: str
    affected: str
    repair_guidance: str


class SignalAttributionEvaluationRequest(BaseModel):
    trading_day_plan_id: str
    post_close_market_snapshot_id: str


class SignalAttributionEvaluationResult(BaseModel):
    state: CoverageState
    post_market_review_id: str
    trading_day_plan_id: str
    trade_date: date
    post_close_market_snapshot_id: str
    attribution: dict[str, Any]
    happened: str
    affected: str
    repair_guidance: str


class OptimizationProposalGenerationRequest(BaseModel):
    post_market_review_id: str


class OptimizationProposalReviewRequest(BaseModel):
    action: Literal["start_review", "continue_observing", "reject"]
    reason: str | None = None
    source_surface: str = "/daily/after-close"


class OptimizationProposalAcceptRequest(BaseModel):
    reason: str | None = None
    linked_draft_version_id: UUID | None = None
    source_surface: str = "/daily/after-close"


class OptimizationProposalTargetView(BaseModel):
    asset_type: str
    asset_id: str
    label: str
    strategy_membership_ids: list[str] = Field(default_factory=list)
    rule_version_ids: list[str] = Field(default_factory=list)
    author_profile_version_ids: list[str] = Field(default_factory=list)


class OptimizationProposalView(BaseModel):
    proposal_id: str
    proposal_type: str
    proposal_type_label: str
    lifecycle_state: str
    lifecycle_label: str
    revision_no: int
    confidence: float | None = None
    evidence_state: str
    evidence_label: str
    recommendation_state: str
    recommendation_label: str
    rationale: str
    target: OptimizationProposalTargetView
    review_binding: dict[str, Any] = Field(default_factory=dict)
    base_version_id: str | None = None
    accepted_draft_version_id: str | None = None
    proposed_changes: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
    available_actions: list[str] = Field(default_factory=list)
    partial_reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class OptimizationProposalCollectionResult(BaseModel):
    state: Literal["ready", "partial", "empty"]
    count: int
    items: list[OptimizationProposalView]
    happened: str
    affected: str
    repair_guidance: str


class PostCloseActualsRepository:
    """Read formal post-close actual rows from the canonical MarketSnapshot contract."""

    def __init__(
        self,
        *,
        plan_repository: DailyTradingPlanRepository | None = None,
        section_repository: MarketSnapshotSectionRepository | None = None,
        item_repository: MarketSnapshotItemRepository | None = None,
    ) -> None:
        self.plan_repository = plan_repository or DailyTradingPlanRepository()
        self.section_repository = section_repository or MarketSnapshotSectionRepository()
        self.item_repository = item_repository or MarketSnapshotItemRepository()

    async def get_actuals_for_signals(
        self,
        session: AsyncSession,
        *,
        trading_day_plan_id: UUID,
        post_close_market_snapshot_id: UUID,
    ) -> PostCloseActualsReadResult:
        plan = await self.plan_repository.get_plan_for_id(session, trading_day_plan_id=trading_day_plan_id)
        if plan is None:
            raise LookupError("trading day plan is missing")
        plan_state = plan.lifecycle_state.value if hasattr(plan.lifecycle_state, "value") else str(plan.lifecycle_state)
        signals = await self.plan_repository.list_signals_for_plan(session, trading_day_plan_id=trading_day_plan_id)
        snapshot = await session.get(MarketSnapshot, post_close_market_snapshot_id)
        if snapshot is None:
            raise LookupError("post-close market snapshot is missing")
        if snapshot.trade_date != plan.trade_date:
            return self._snapshot_level_result(
                plan=plan,
                plan_state=plan_state,
                signals=signals,
                snapshot=snapshot,
                coverage_state="invalid",
                reasons=["post_close_snapshot_trade_date_mismatch"],
            )
        if plan_state != TradingDayPlanState.approved.value:
            return self._snapshot_level_result(
                plan=plan,
                plan_state=plan_state,
                signals=signals,
                snapshot=snapshot,
                coverage_state="invalid",
                reasons=["trading_day_plan_not_approved"],
            )
        section = await self.section_repository.get_by_snapshot_and_section(
            session,
            snapshot.snapshot_id,
            POST_CLOSE_ACTUALS_SECTION_ID,
        )
        if section is None:
            return self._snapshot_level_result(
                plan=plan,
                plan_state=plan_state,
                signals=signals,
                snapshot=snapshot,
                coverage_state="unavailable",
                reasons=["post_close_actuals_section_missing"],
            )
        items = await self.item_repository.list_by_section(
            session,
            snapshot.snapshot_id,
            POST_CLOSE_ACTUALS_SECTION_ID,
        )
        dataset = await self._load_bound_dataset(session, section)
        return self._build_result(plan=plan, plan_state=plan_state, signals=signals, snapshot=snapshot, section=section, items=items, dataset=dataset)

    async def _load_bound_dataset(self, session: AsyncSession, section: MarketSnapshotSection) -> DatasetSnapshot | None:
        payload = section.payload_json or {}
        dataset_snapshot_id = payload.get("dataset_snapshot_id")
        if not dataset_snapshot_id:
            return None
        try:
            return await session.get(DatasetSnapshot, UUID(str(dataset_snapshot_id)))
        except ValueError:
            return None

    def _snapshot_level_result(
        self,
        *,
        plan: Any,
        plan_state: str,
        signals: list[Signal],
        snapshot: MarketSnapshot,
        coverage_state: CoverageState,
        reasons: list[str],
    ) -> PostCloseActualsReadResult:
        return PostCloseActualsReadResult(
            trading_day_plan_id=str(plan.trading_day_plan_id),
            trade_date=plan.trade_date,
            plan_lifecycle_state=plan_state,
            post_close_market_snapshot_id=str(snapshot.id),
            post_close_market_snapshot_snapshot_id=snapshot.snapshot_id,
            market_snapshot_content_fingerprint=snapshot.content_fingerprint,
            market_snapshot_frozen_at=snapshot.frozen_at,
            market_snapshot_available_at=snapshot.available_at,
            coverage_state=coverage_state,
            signals=[
                SignalActualResult(
                    signal_id=str(signal.signal_id),
                    symbol=signal.symbol,
                    state=coverage_state,
                    reasons=list(reasons),
                )
                for signal in signals
            ],
            missing_symbols=sorted({signal.symbol for signal in signals}),
            reasons=list(reasons),
        )

    def _build_result(
        self,
        *,
        plan: Any,
        plan_state: str,
        signals: list[Signal],
        snapshot: MarketSnapshot,
        section: MarketSnapshotSection,
        items: list[MarketSnapshotItem],
        dataset: DatasetSnapshot | None,
    ) -> PostCloseActualsReadResult:
        section_payload = section.payload_json or {}
        manifest_missing = set(section_payload.get("missing_symbols") or [])
        manifest_conflicts = set(section_payload.get("conflict_symbols") or [])
        section_reasons: list[str] = []
        if section_payload.get("actuals_contract_version") != POST_CLOSE_ACTUALS_CONTRACT_VERSION:
            section_reasons.append("actuals_contract_version_invalid")
        if not section.raw_payload_fingerprint:
            section_reasons.append("section_raw_payload_fingerprint_missing")
        dataset_snapshot_id = section_payload.get("dataset_snapshot_id")
        dataset_content_fingerprint = section_payload.get("dataset_content_fingerprint")
        if dataset is None:
            section_reasons.append("dataset_snapshot_binding_missing")
        elif str(dataset.dataset_snapshot_id) != str(dataset_snapshot_id) or dataset.content_fingerprint != dataset_content_fingerprint:
            section_reasons.append("dataset_snapshot_binding_mismatch")

        signal_symbols = [signal.symbol for signal in signals]
        by_symbol: dict[str, list[MarketSnapshotItem]] = {}
        for item in items:
            if item.symbol:
                by_symbol.setdefault(item.symbol, []).append(item)

        results: list[SignalActualResult] = []
        missing_symbols: set[str] = set()
        conflict_symbols: set[str] = set(manifest_conflicts)
        for signal in signals:
            item_candidates = by_symbol.get(signal.symbol, [])
            if signal.symbol in manifest_missing or not item_candidates:
                missing_symbols.add(signal.symbol)
                results.append(
                    SignalActualResult(
                        signal_id=str(signal.signal_id),
                        symbol=signal.symbol,
                        state="insufficient_coverage",
                        reasons=["post_close_actual_row_missing"],
                    )
                )
                continue
            if len(item_candidates) > 1 or signal.symbol in manifest_conflicts:
                conflict_symbols.add(signal.symbol)
                results.append(
                    SignalActualResult(
                        signal_id=str(signal.signal_id),
                        symbol=signal.symbol,
                        state="conflict",
                        reasons=["post_close_actual_row_conflict"],
                    )
                )
                continue
            item = item_candidates[0]
            state, row, reasons = self._validate_item(signal=signal, item=item, snapshot=snapshot, section=section)
            results.append(
                SignalActualResult(
                    signal_id=str(signal.signal_id),
                    symbol=signal.symbol,
                    state=state,
                    row=row,
                    row_fingerprint=row.row_fingerprint if row else None,
                    reasons=reasons,
                )
            )

        if section_reasons:
            coverage_state: CoverageState = "invalid"
        elif conflict_symbols:
            coverage_state = "conflict"
        elif missing_symbols:
            coverage_state = "insufficient_coverage" if len(missing_symbols) == len(set(signal_symbols)) else "partial"
        elif any(result.state in {"invalid", "unavailable"} for result in results):
            coverage_state = "invalid"
        elif any(result.state == "degraded" for result in results):
            coverage_state = "degraded"
        else:
            coverage_state = "ready"

        return PostCloseActualsReadResult(
            trading_day_plan_id=str(plan.trading_day_plan_id),
            trade_date=plan.trade_date,
            plan_lifecycle_state=plan_state,
            post_close_market_snapshot_id=str(snapshot.id),
            post_close_market_snapshot_snapshot_id=snapshot.snapshot_id,
            market_snapshot_content_fingerprint=snapshot.content_fingerprint,
            market_snapshot_frozen_at=snapshot.frozen_at,
            market_snapshot_available_at=snapshot.available_at,
            dataset_snapshot_id=str(dataset.dataset_snapshot_id) if dataset else str(dataset_snapshot_id) if dataset_snapshot_id else None,
            dataset_content_fingerprint=dataset.content_fingerprint if dataset else dataset_content_fingerprint,
            section_raw_payload_fingerprint=section.raw_payload_fingerprint,
            coverage_state=coverage_state,
            signals=results,
            missing_symbols=sorted(missing_symbols),
            conflict_symbols=sorted(conflict_symbols),
            reasons=section_reasons,
        )

    def _validate_item(
        self,
        *,
        signal: Signal,
        item: MarketSnapshotItem,
        snapshot: MarketSnapshot,
        section: MarketSnapshotSection,
    ) -> tuple[CoverageState, PostCloseActualRow | None, list[str]]:
        payload = dict(item.payload_json or {})
        reasons: list[str] = []
        if item.item_key != f"{POST_CLOSE_ACTUALS_SECTION_ID}:{signal.symbol}:{snapshot.trade_date.isoformat()}":
            reasons.append("actual_item_key_invalid")
        if payload.get("symbol") != signal.symbol:
            reasons.append("actual_symbol_mismatch")
        if payload.get("trade_date") != snapshot.trade_date.isoformat():
            reasons.append("actual_trade_date_mismatch")
        if payload.get("row_fingerprint") is None:
            reasons.append("row_fingerprint_missing")
        if item.quality_status not in {"ok", "ready", "complete", "verified", "degraded"}:
            reasons.append("item_quality_state_invalid")
        try:
            row = PostCloseActualRow.model_validate(payload)
        except Exception as exc:
            return "invalid", None, [*reasons, f"actual_payload_invalid:{type(exc).__name__}"]
        section_payload = section.payload_json or {}
        if item.dataset_id and item.dataset_id != row.dataset_snapshot_id:
            reasons.append("item_dataset_binding_mismatch")
        if row.dataset_snapshot_id != str(section_payload.get("dataset_snapshot_id")):
            reasons.append("row_dataset_snapshot_binding_mismatch")
        if row.dataset_content_fingerprint != section_payload.get("dataset_content_fingerprint"):
            reasons.append("row_dataset_content_fingerprint_mismatch")
        expected_row_fingerprint = (section_payload.get("row_fingerprints") or {}).get(signal.symbol)
        if expected_row_fingerprint and row.row_fingerprint != expected_row_fingerprint:
            reasons.append("row_fingerprint_manifest_mismatch")
        if section.raw_payload_fingerprint and payload.get("section_raw_payload_fingerprint") not in {None, section.raw_payload_fingerprint}:
            reasons.append("section_fingerprint_mismatch")
        if row.evidence_window == "daily_bar" and row.intraday_approximation is not True:
            reasons.append("daily_bar_approximation_flag_missing")
        state: CoverageState = "degraded" if row.quality_state == "degraded" or item.quality_status == "degraded" else "ready"
        if row.availability_state not in {"ready", "available"}:
            state = "unavailable"
            reasons.append("actual_row_not_available")
        if reasons:
            return "invalid", row, reasons
        return state, row, []


class PostMarketReviewService:
    service_name = "post_market_review"

    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any] | None = None,
        actuals_repository: PostCloseActualsRepository | None = None,
        review_repository: PostMarketReviewRepository | None = None,
        strategy_repository: StrategyRepository | None = None,
    ) -> None:
        self._session_scope_factory = session_scope_factory or self._default_session_scope_factory
        self.actuals_repository = actuals_repository or PostCloseActualsRepository()
        self.review_repository = review_repository or PostMarketReviewRepository()
        self.strategy_repository = strategy_repository or StrategyRepository()
        self._lifecycle_validator = LifecycleTransitionValidator()

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

    async def get_actuals_for_signals(
        self,
        *,
        trading_day_plan_id: str | UUID,
        post_close_market_snapshot_id: str | UUID,
        actor_id: str,
        actor_role: str,
    ) -> PostCloseActualsReadResult:
        if actor_role not in {"viewer", "operator", "admin"}:
            raise PermissionError("viewer permission is required to view post-close actuals")
        del actor_id
        async with self._session_scope_factory() as session:
            return await self.actuals_repository.get_actuals_for_signals(
                session,
                trading_day_plan_id=UUID(str(trading_day_plan_id)),
                post_close_market_snapshot_id=UUID(str(post_close_market_snapshot_id)),
            )

    async def evaluate_signal_outcomes(
        self,
        request: SignalOutcomeEvaluationRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> SignalOutcomeEvaluationResult:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to evaluate post-market signal results")
        async with self._session_scope_factory() as session:
            actuals = await self.actuals_repository.get_actuals_for_signals(
                session,
                trading_day_plan_id=UUID(request.trading_day_plan_id),
                post_close_market_snapshot_id=UUID(request.post_close_market_snapshot_id),
            )
            plan = await self.review_repository.get_plan(session, UUID(request.trading_day_plan_id))
            if plan is None:
                raise LookupError("trading day plan is missing")
            signals = await self.actuals_repository.plan_repository.list_signals_for_plan(
                session,
                trading_day_plan_id=plan.trading_day_plan_id,
            )
            instance = await self.review_repository.get_daily_strategy_instance(session, plan.daily_strategy_instance_id)
            if instance is None:
                raise LookupError("daily strategy instance is missing")
            selection = await self.review_repository.get_daily_rule_selection(session, instance.daily_rule_selection_id)
            if selection is None:
                raise LookupError("daily rule selection is missing")
            selection_items = await self.review_repository.list_selection_items(session, selection.daily_rule_selection_id)
            post_close_market_state_id = UUID(request.post_close_market_state_id) if request.post_close_market_state_id else None
            signal_results = [
                self._evaluate_one_signal(signal=signal, actual=actual, selection_items=selection_items, pre_market_state_id=selection.market_state_id, post_close_market_state_id=post_close_market_state_id)
                for signal, actual in zip(signals, actuals.signals, strict=False)
            ]
            evidence = self._evidence_payload(
                actuals=actuals,
                signals=signals,
                pre_market_state_id=selection.market_state_id,
                post_close_market_state_id=post_close_market_state_id,
            )
            attribution = self._build_attribution_payload(
                signal_results=signal_results,
                evidence=evidence,
            )
            review = await self._upsert_review(
                session,
                plan_id=plan.trading_day_plan_id,
                post_close_market_snapshot_id=UUID(request.post_close_market_snapshot_id),
                post_close_market_state_id=post_close_market_state_id,
                signal_results=signal_results,
                attribution=attribution,
                evidence=evidence,
                coverage_state=actuals.coverage_state,
                actor_id=actor_id,
            )
            return SignalOutcomeEvaluationResult(
                state=actuals.coverage_state,
                post_market_review_id=str(review.post_market_review_id),
                trading_day_plan_id=str(plan.trading_day_plan_id),
                trade_date=plan.trade_date,
                post_close_market_snapshot_id=request.post_close_market_snapshot_id,
                signal_results=signal_results,
                evidence=evidence,
                happened="已根据正式盘后行情快照评估盘前信号。" if actuals.coverage_state == "ready" else "盘后信号评估存在未满足的数据状态。",
                affected="页面会显示每个信号的实际结果、差异和不可用原因；不会把缺失值当作成功。",
                repair_guidance="补齐缺失的盘后标的行情快照或处理冲突后重新评估。" if actuals.coverage_state != "ready" else "可进入结构化归因任务，但本次未生成归因或优化建议。",
            )

    async def get_post_market_review(
        self,
        *,
        trading_day_plan_id: str | UUID,
        post_market_review_id: str | UUID | None = None,
        actor_id: str,
        actor_role: str,
    ) -> PostMarketReviewView:
        if actor_role not in {"viewer", "operator", "admin"}:
            raise PermissionError("viewer permission is required to view post-market review")
        del actor_id
        async with self._session_scope_factory() as session:
            plan = await self.review_repository.get_plan(session, UUID(str(trading_day_plan_id)))
            if plan is None:
                raise LookupError("trading day plan is missing")
            selected_review: PostMarketReview | None = None
            if post_market_review_id is not None:
                selected_review = await self.review_repository.get_review(session, UUID(str(post_market_review_id)))
                if selected_review is None or selected_review.trading_day_plan_id != plan.trading_day_plan_id:
                    raise LookupError("post-market review is missing")
            else:
                reviews = await self.review_repository.list_reviews_for_plan(session, plan.trading_day_plan_id)
                selected_review = reviews[-1] if reviews else None
            if selected_review is None:
                return PostMarketReviewView(
                    state="unavailable",
                    generated=False,
                    trading_day_plan_id=str(plan.trading_day_plan_id),
                    trade_date=plan.trade_date,
                    signal_outcome_state="unavailable",
                    attribution_state="unavailable",
                    happened="正式盘后复盘尚未生成。",
                    affected="当前只能查看盘前预测，实际结果、差异和建议操作暂不可用。",
                    repair_guidance="请先完成正式盘后结果评估；如果今天已经完成，请刷新页面后重试。",
                )
            signal_results_payload = selected_review.signal_results_json or {}
            signal_results = list(signal_results_payload.get("signals") or [])
            signal_outcome_state = self._signal_outcome_state_from_review(signal_results_payload)
            attribution = selected_review.attribution_json or {}
            attribution_state = self._review_payload_state(attribution)
            overall_state = self._aggregate_review_states([signal_outcome_state, attribution_state])
            return PostMarketReviewView(
                state=overall_state,
                generated=True,
                post_market_review_id=str(selected_review.post_market_review_id),
                trading_day_plan_id=str(plan.trading_day_plan_id),
                trade_date=plan.trade_date,
                revision_no=selected_review.revision_no,
                lifecycle_state=_state(selected_review.lifecycle_state),
                quality_status=_state(selected_review.quality_status),
                signal_outcome_state=signal_outcome_state,
                attribution_state=attribution_state,
                post_close_market_snapshot_id=str(selected_review.market_snapshot_id) if selected_review.market_snapshot_id else None,
                post_close_market_state_id=str(selected_review.market_state_id) if selected_review.market_state_id else None,
                signal_results=signal_results,
                attribution=attribution,
                evidence=selected_review.evidence_json or {},
                happened="已读取正式盘后复盘。" if overall_state == "ready" else "正式盘后复盘存在未满足的数据状态。",
                affected="页面会按正式证据展示盘前预测、实际结果、差异和建议操作；缺失值不会被当作成功。" if overall_state == "ready" else "页面只会展示当前已确认的盘后结果，并明确标注缺失、冲突或降级部分。",
                repair_guidance="可继续查看今日建议操作。" if overall_state == "ready" else "请先补齐缺失证据、处理冲突，或在正式状态允许时继续查看可用部分。",
            )

    async def evaluate_signal_attribution(
        self,
        request: SignalAttributionEvaluationRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> SignalAttributionEvaluationResult:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to evaluate structured attribution")
        async with self._session_scope_factory() as session:
            plan = await self.review_repository.get_plan(session, UUID(request.trading_day_plan_id))
            if plan is None:
                raise LookupError("trading day plan is missing")
            reviews = await self.review_repository.list_reviews_for_plan(session, plan.trading_day_plan_id)
            review = next(
                (
                    item
                    for item in reviews
                    if item.market_snapshot_id == UUID(request.post_close_market_snapshot_id)
                    and (item.signal_results_json or {}).get("policy_version") == SIGNAL_OUTCOME_POLICY_VERSION
                ),
                None,
            )
            if review is None:
                raise LookupError("post-market review is missing")
            attribution = self._build_attribution_payload(
                signal_results=list((review.signal_results_json or {}).get("signals") or []),
                evidence=review.evidence_json or {},
            )
            review.attribution_json = attribution
            review.prompt_run_id = None
            review.updated_by = actor_id
            with canonical_write_scope("post_market_review", self.service_name):
                review = await self.review_repository.save_review(session, review)
            return SignalAttributionEvaluationResult(
                state=attribution["state"],
                post_market_review_id=str(review.post_market_review_id),
                trading_day_plan_id=str(plan.trading_day_plan_id),
                trade_date=plan.trade_date,
                post_close_market_snapshot_id=request.post_close_market_snapshot_id,
                attribution=attribution,
                happened="已基于 RT-S10-001 正式盘后结果生成结构化归因。",
                affected="页面和后续 Stage 10 任务会读取结构化归因，而不是直接依赖自由文本说明。",
                repair_guidance="如需进一步解释，可在低置信度、证据冲突或重要信号时进入受限 LLM 校验；本次未调用 LLM。",
            )

    async def _upsert_review(
        self,
        session: AsyncSession,
        *,
        plan_id: UUID,
        post_close_market_snapshot_id: UUID,
        post_close_market_state_id: UUID | None,
        signal_results: list[dict[str, Any]],
        attribution: dict[str, Any],
        evidence: dict[str, Any],
        coverage_state: CoverageState,
        actor_id: str,
    ) -> PostMarketReview:
        existing_reviews = await self.review_repository.list_reviews_for_plan(session, plan_id)
        review = next(
            (
                item
                for item in existing_reviews
                if item.market_snapshot_id == post_close_market_snapshot_id
                and (item.evidence_json or {}).get("actuals", {}).get("post_close_market_snapshot_id") == str(post_close_market_snapshot_id)
            ),
            None,
        )
        if review is None:
            review = PostMarketReview(
                post_market_review_id=uuid4(),
                trading_day_plan_id=plan_id,
                revision_no=await self.review_repository.next_revision_no(session, plan_id),
                market_snapshot_id=post_close_market_snapshot_id,
                market_state_id=post_close_market_state_id,
                signal_results_json={"policy_version": SIGNAL_OUTCOME_POLICY_VERSION, "signals": signal_results},
                attribution_json=attribution,
                evidence_json=evidence,
                lifecycle_state=PostMarketReviewState.draft,
                quality_status=QualityStatus.complete if coverage_state == "ready" else QualityStatus.partial,
                prompt_run_id=None,
                created_by=actor_id,
                updated_by=actor_id,
            )
        else:
            review.market_state_id = post_close_market_state_id
            review.signal_results_json = {"policy_version": SIGNAL_OUTCOME_POLICY_VERSION, "signals": signal_results}
            review.attribution_json = attribution
            review.evidence_json = evidence
            review.quality_status = QualityStatus.complete if coverage_state == "ready" else QualityStatus.partial
            review.updated_by = actor_id
            review.prompt_run_id = None
        with canonical_write_scope("post_market_review", self.service_name):
            return await self.review_repository.save_review(session, review)

    def _evaluate_one_signal(
        self,
        *,
        signal: Signal,
        actual: SignalActualResult,
        selection_items: list[Any],
        pre_market_state_id: UUID,
        post_close_market_state_id: UUID | None,
    ) -> dict[str, Any]:
        triggered = self._triggered_state(signal)
        executed = {"state": "unavailable", "value": None, "reason": "approved_execution_supplement_missing"}
        matched_rules = self._matched_rules(signal, selection_items)
        market_state_change = self._market_state_change(pre_market_state_id, post_close_market_state_id)
        base = {
            "signal_id": str(signal.signal_id),
            "symbol": signal.symbol,
            "side": signal.side,
            "state": actual.state,
            "triggered": triggered,
            "executed": executed,
            "matched_rule": matched_rules,
            "market_state_change": market_state_change,
            "actual_result": {"state": actual.state, "value": None, "reason": None},
            "mfe": {"state": actual.state, "value": None, "reason": None},
            "mae": {"state": actual.state, "value": None, "reason": None},
            "return": {"state": actual.state, "value": None, "reason": None},
            "evidence": {
                "row_fingerprint": actual.row_fingerprint,
                "reasons": list(actual.reasons),
                "metric_policy_version": SIGNAL_OUTCOME_POLICY_VERSION,
            },
        }
        if actual.row is None:
            for field in ("actual_result", "mfe", "mae", "return"):
                base[field] = {"state": actual.state, "value": None, "reason": ",".join(actual.reasons) or "actual_row_unavailable"}
            return base
        row = actual.row
        base["evidence"]["evidence_window"] = row.evidence_window
        base["evidence"]["intraday_approximation"] = row.intraday_approximation
        baseline, baseline_policy, baseline_reason = _entry_price_baseline(signal)
        if baseline is None and baseline_policy == "previous_close_daily_market_signal":
            baseline = row.previous_close
            if baseline is None or baseline <= 0:
                baseline_reason = "baseline_previous_close_missing_or_invalid"
        if baseline is None or baseline <= 0 or baseline_policy is None:
            reason = baseline_reason or "baseline_unavailable"
            base["return"] = {"state": "unavailable", "value": None, "reason": reason}
            base["mfe"] = {"state": "unavailable", "value": None, "reason": reason}
            base["mae"] = {"state": "unavailable", "value": None, "reason": reason}
            base["actual_result"] = {"state": "unavailable", "value": None, "reason": reason}
            return base
        side = (signal.side or "").upper()
        if side == "BUY":
            ret = _ratio(row.close - baseline, baseline)
            mfe = _ratio(row.high - baseline, baseline)
            mae = _ratio(row.low - baseline, baseline)
            actual_result = "up" if row.close > baseline else "down" if row.close < baseline else "flat"
        elif side == "SELL":
            ret = _ratio(baseline - row.close, baseline)
            mfe = _ratio(baseline - row.low, baseline)
            mae = _ratio(baseline - row.high, baseline)
            actual_result = "down" if row.close < baseline else "up" if row.close > baseline else "flat"
        elif side == "HOLD":
            ret = _ratio(row.close - baseline, baseline)
            mfe = _ratio(row.high - baseline, baseline)
            mae = _ratio(row.low - baseline, baseline)
            actual_result = "flat" if row.close == baseline else "moved"
        else:
            base["actual_result"] = {"state": "invalid", "value": None, "reason": "signal_side_invalid"}
            return base
        base["actual_result"] = {"state": "ready", "value": actual_result, "baseline_policy": baseline_policy, "baseline": float(baseline), "close": float(row.close)}
        base["mfe"] = {"state": "ready", "value": mfe, "evidence_window": row.evidence_window, "intraday_approximation": row.intraday_approximation}
        base["mae"] = {"state": "ready", "value": mae, "evidence_window": row.evidence_window, "intraday_approximation": row.intraday_approximation}
        base["return"] = {"state": "ready", "value": ret, "baseline_policy": baseline_policy, "baseline": float(baseline)}
        return base

    def _triggered_state(self, signal: Signal) -> dict[str, Any]:
        state = signal.signal_state.value if hasattr(signal.signal_state, "value") else str(signal.signal_state)
        side = (signal.side or "").upper()
        if state in {SignalState.approved.value, SignalState.executed.value} and side in {"BUY", "SELL"}:
            return {"state": "ready", "value": True, "evidence": {"signal_state": state, "side": side}}
        if state in {SignalState.approved.value, SignalState.executed.value} and side == "HOLD":
            return {"state": "ready", "value": False, "evidence": {"signal_state": state, "side": side, "reason": "explicit_hold_signal"}}
        if state in {SignalState.rejected.value, SignalState.cancelled.value, SignalState.expired.value}:
            return {"state": "ready", "value": False, "evidence": {"signal_state": state}}
        return {"state": "invalid", "value": None, "reason": "signal_trigger_evidence_missing_or_contradictory", "evidence": {"signal_state": state, "side": side}}

    def _matched_rules(self, signal: Signal, selection_items: list[Any]) -> dict[str, Any]:
        signal_rules = [str(item) for item in (signal.rule_version_ids or [])]
        triggered_rules = [str(item) for item in (signal.triggered_rules or [])]
        selection_rule_ids = {str(item.rule_version_id): getattr(item, "decision", None) for item in selection_items}
        candidate_rules = list(dict.fromkeys([*signal_rules, *triggered_rules]))
        matched = [rule_id for rule_id in candidate_rules if rule_id in selection_rule_ids]
        return {
            "state": "ready" if matched else "unavailable",
            "rule_version_ids": matched,
            "signal_rule_version_ids": signal_rules,
            "triggered_rules": triggered_rules,
            "selection_decisions": {rule_id: selection_rule_ids.get(rule_id) for rule_id in matched},
            "reason": None if matched else "no_matching_daily_rule_selection_item",
        }

    def _market_state_change(self, pre_market_state_id: UUID, post_close_market_state_id: UUID | None) -> dict[str, Any]:
        if post_close_market_state_id is None:
            return {"state": "unavailable", "value": None, "reason": "post_close_market_state_missing", "pre_market_state_id": str(pre_market_state_id)}
        return {
            "state": "ready",
            "value": "unchanged" if pre_market_state_id == post_close_market_state_id else "changed",
            "pre_market_state_id": str(pre_market_state_id),
            "post_close_market_state_id": str(post_close_market_state_id),
        }

    def _evidence_payload(
        self,
        *,
        actuals: PostCloseActualsReadResult,
        signals: list[Signal],
        pre_market_state_id: UUID,
        post_close_market_state_id: UUID | None,
    ) -> dict[str, Any]:
        payload = {
            "policy_version": SIGNAL_OUTCOME_POLICY_VERSION,
            "actuals_contract_version": POST_CLOSE_ACTUALS_CONTRACT_VERSION,
            "plan": {"trading_day_plan_id": actuals.trading_day_plan_id, "trade_date": actuals.trade_date.isoformat()},
            "signals": [{"signal_id": str(signal.signal_id), "symbol": signal.symbol, "side": signal.side} for signal in signals],
            "actuals": {
                "post_close_market_snapshot_id": actuals.post_close_market_snapshot_id,
                "post_close_market_snapshot_snapshot_id": actuals.post_close_market_snapshot_snapshot_id,
                "market_snapshot_content_fingerprint": actuals.market_snapshot_content_fingerprint,
                "market_snapshot_frozen_at": actuals.market_snapshot_frozen_at.isoformat() if actuals.market_snapshot_frozen_at else None,
                "market_snapshot_available_at": actuals.market_snapshot_available_at.isoformat() if actuals.market_snapshot_available_at else None,
                "dataset_snapshot_id": actuals.dataset_snapshot_id,
                "dataset_content_fingerprint": actuals.dataset_content_fingerprint,
                "section_raw_payload_fingerprint": actuals.section_raw_payload_fingerprint,
                "row_fingerprints": {item.symbol: item.row_fingerprint for item in actuals.signals if item.row_fingerprint},
                "coverage_state": actuals.coverage_state,
                "missing_symbols": actuals.missing_symbols,
                "conflict_symbols": actuals.conflict_symbols,
                "reasons": actuals.reasons,
            },
            "market_state_change": {
                "pre_market_state_id": str(pre_market_state_id),
                "post_close_market_state_id": str(post_close_market_state_id) if post_close_market_state_id else None,
            },
            "unavailable_conflict_invalid_reasons": {
                item.symbol: item.reasons for item in actuals.signals if item.reasons
            },
            "attribution_state": "unavailable_RT-S10-002_not_started",
            "proposal_state": "unavailable_RT-S10-003_not_started",
        }
        payload["evidence_fingerprint"] = _json_fingerprint(payload)
        return payload

    def _build_attribution_payload(
        self,
        *,
        signal_results: list[dict[str, Any]],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        attributions = [self._classify_signal_attribution(signal_result) for signal_result in signal_results]
        counts_by_category: dict[str, int] = {}
        counts_by_state: dict[str, int] = {}
        llm_eligible_signal_ids: list[str] = []
        for item in attributions:
            counts_by_category[item["category"]] = counts_by_category.get(item["category"], 0) + 1
            counts_by_state[item["state"]] = counts_by_state.get(item["state"], 0) + 1
            if item["llm_validation"]["eligible"]:
                llm_eligible_signal_ids.append(item["signal_id"])
        overall_state = self._aggregate_attribution_state([item["state"] for item in attributions])
        primary_category = max(counts_by_category.items(), key=lambda pair: (pair[1], pair[0]))[0] if counts_by_category else "unattributable"
        payload = {
            "policy_version": STRUCTURED_ATTRIBUTION_POLICY_VERSION,
            "source": "RT-S10-001_program_facts",
            "state": overall_state,
            "primary_category": primary_category,
            "signals": attributions,
            "summary": {
                "signal_count": len(attributions),
                "counts_by_category": counts_by_category,
                "counts_by_state": counts_by_state,
            },
            "llm_validation": {
                "state": "not_requested",
                "eligible_signal_ids": llm_eligible_signal_ids,
                "reason": "deterministic_program_fact_first",
            },
            "review_evidence_fingerprint": evidence.get("evidence_fingerprint"),
            "proposal_state": "unavailable_RT-S10-003_not_started",
        }
        payload["attribution_fingerprint"] = _json_fingerprint(payload)
        return payload

    def _classify_signal_attribution(self, signal_result: dict[str, Any]) -> dict[str, Any]:
        state = self._signal_attribution_state(signal_result)
        triggered = signal_result.get("triggered") or {}
        executed = signal_result.get("executed") or {}
        matched_rule = signal_result.get("matched_rule") or {}
        market_state_change = signal_result.get("market_state_change") or {}
        actual_result = signal_result.get("actual_result") or {}
        return_fact = signal_result.get("return") or {}
        reasons = self._signal_attribution_reasons(signal_result)
        category: AttributionCategory
        candidates: list[AttributionCategory] = []
        if state in {"partial", "unavailable", "conflict", "invalid", "insufficient_coverage", "degraded"}:
            candidates.append("data issue")
        elif self._is_execution_issue(triggered=triggered, executed=executed):
            candidates.append("execution issue")
        else:
            unfavorable = self._is_unfavorable_signal(signal_result)
            if unfavorable:
                if self._is_market_state_issue(market_state_change):
                    candidates.append("market-state identification issue")
                if self._is_strategy_composition_issue(matched_rule):
                    candidates.append("strategy-composition issue")
                if self._is_rule_issue(matched_rule):
                    candidates.append("rule issue")
        category = candidates[0] if candidates else "unattributable"
        llm_reasons = self._llm_gate_reasons(
            signal_result=signal_result,
            category_candidates=candidates,
            state=state,
        )
        explanation = self._signal_explanation(
            category=category,
            state=state,
            signal_result=signal_result,
        )
        return {
            "signal_id": signal_result.get("signal_id"),
            "symbol": signal_result.get("symbol"),
            "state": state,
            "category": category,
            "confidence": "low" if "low_confidence_multiple_candidate_categories" in llm_reasons else "high",
            "reasons": reasons,
            "program_facts": {
                "signal_result_state": signal_result.get("state"),
                "triggered": {
                    "state": triggered.get("state"),
                    "value": triggered.get("value"),
                },
                "executed": {
                    "state": executed.get("state"),
                    "value": executed.get("value"),
                    "reason": executed.get("reason"),
                },
                "actual_result": {
                    "state": actual_result.get("state"),
                    "value": actual_result.get("value"),
                    "reason": actual_result.get("reason"),
                },
                "return": {
                    "state": return_fact.get("state"),
                    "value": return_fact.get("value"),
                    "reason": return_fact.get("reason"),
                },
                "matched_rule": {
                    "state": matched_rule.get("state"),
                    "rule_version_ids": matched_rule.get("rule_version_ids") or [],
                    "selection_decisions": matched_rule.get("selection_decisions") or {},
                },
                "market_state_change": {
                    "state": market_state_change.get("state"),
                    "value": market_state_change.get("value"),
                    "reason": market_state_change.get("reason"),
                },
            },
            "llm_validation": {
                "eligible": bool(llm_reasons),
                "requested": False,
                "state": "not_requested",
                "reasons": llm_reasons,
            },
            "user_explanation": explanation,
        }

    def _signal_attribution_state(self, signal_result: dict[str, Any]) -> CoverageState:
        signal_state = str(signal_result.get("state") or "ready")
        if signal_state in {"partial", "unavailable", "conflict", "invalid", "insufficient_coverage", "degraded"}:
            return signal_state  # type: ignore[return-value]
        for field_name in ("triggered", "actual_result", "mfe", "mae", "return"):
            field_state = str((signal_result.get(field_name) or {}).get("state") or "ready")
            if field_state in {"conflict", "invalid"}:
                return field_state  # type: ignore[return-value]
            if field_state in {"unavailable", "partial", "insufficient_coverage", "degraded"}:
                return field_state  # type: ignore[return-value]
        return "ready"

    def _review_payload_state(self, payload: dict[str, Any]) -> CoverageState:
        state = str(payload.get("state") or "unavailable")
        if state in {"ready", "partial", "unavailable", "conflict", "invalid", "insufficient_coverage", "degraded"}:
            return state  # type: ignore[return-value]
        return "invalid"

    def _signal_outcome_state_from_review(self, payload: dict[str, Any]) -> CoverageState:
        if payload.get("policy_version") != SIGNAL_OUTCOME_POLICY_VERSION:
            return "invalid"
        signals = list(payload.get("signals") or [])
        if not signals:
            return "unavailable"
        return self._aggregate_review_states([self._signal_attribution_state(item) for item in signals])

    def _aggregate_review_states(self, states: list[str]) -> CoverageState:
        if any(state == "conflict" for state in states):
            return "conflict"
        if any(state == "invalid" for state in states):
            return "invalid"
        if any(state == "insufficient_coverage" for state in states):
            return "insufficient_coverage"
        if any(state == "partial" for state in states):
            return "partial"
        if any(state == "unavailable" for state in states):
            return "unavailable"
        if any(state == "degraded" for state in states):
            return "degraded"
        return "ready"

    def _signal_attribution_reasons(self, signal_result: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        evidence = signal_result.get("evidence") or {}
        if isinstance(evidence.get("reasons"), list):
            reasons.extend(str(item) for item in evidence["reasons"])
        for field_name in ("actual_result", "mfe", "mae", "return"):
            reason = (signal_result.get(field_name) or {}).get("reason")
            if reason:
                reasons.append(str(reason))
        market_state_reason = (signal_result.get("market_state_change") or {}).get("reason")
        if market_state_reason:
            reasons.append(str(market_state_reason))
        return list(dict.fromkeys(reasons))

    def _is_execution_issue(self, *, triggered: dict[str, Any], executed: dict[str, Any]) -> bool:
        if executed.get("state") != "ready":
            return False
        if triggered.get("value") is not True:
            return False
        return executed.get("value") is False or bool(executed.get("reason"))

    def _is_market_state_issue(self, market_state_change: dict[str, Any]) -> bool:
        return market_state_change.get("state") == "ready" and market_state_change.get("value") == "changed"

    def _is_strategy_composition_issue(self, matched_rule: dict[str, Any]) -> bool:
        if matched_rule.get("state") != "ready":
            return False
        decisions = list((matched_rule.get("selection_decisions") or {}).values())
        rule_ids = list(matched_rule.get("rule_version_ids") or [])
        return any(decision not in {None, "selected"} for decision in decisions) or len(rule_ids) > 1

    def _is_rule_issue(self, matched_rule: dict[str, Any]) -> bool:
        if matched_rule.get("state") != "ready":
            return False
        decisions = list((matched_rule.get("selection_decisions") or {}).values())
        if any(decision not in {None, "selected"} for decision in decisions):
            return False
        return bool(matched_rule.get("rule_version_ids"))

    def _is_unfavorable_signal(self, signal_result: dict[str, Any]) -> bool:
        side = str(signal_result.get("side") or "").upper()
        return_fact = signal_result.get("return") or {}
        if return_fact.get("state") == "ready":
            value = return_fact.get("value")
            try:
                return float(value) < 0
            except (TypeError, ValueError):
                return False
        actual_result = signal_result.get("actual_result") or {}
        value = actual_result.get("value")
        if actual_result.get("state") != "ready":
            return False
        if side == "BUY":
            return value == "down"
        if side == "SELL":
            return value == "up"
        if side == "HOLD":
            return value == "moved"
        return False

    def _llm_gate_reasons(
        self,
        *,
        signal_result: dict[str, Any],
        category_candidates: list[AttributionCategory],
        state: CoverageState,
    ) -> list[str]:
        reasons: list[str] = []
        if len(category_candidates) > 1:
            reasons.append("low_confidence_multiple_candidate_categories")
        if state == "conflict":
            reasons.append("evidence_conflict")
        triggered = signal_result.get("triggered") or {}
        return_fact = signal_result.get("return") or {}
        if triggered.get("state") == "ready" and triggered.get("value") is True and return_fact.get("state") == "ready":
            try:
                if abs(float(return_fact.get("value"))) >= 0.05:
                    reasons.append("important_signal")
            except (TypeError, ValueError):
                pass
        return reasons

    def _signal_explanation(
        self,
        *,
        category: AttributionCategory,
        state: CoverageState,
        signal_result: dict[str, Any],
    ) -> str:
        symbol = signal_result.get("symbol") or "该信号"
        if category == "data issue":
            return f"{symbol} 的盘后证据存在缺失、冲突或降级，当前先归为数据问题。"
        if category == "market-state identification issue":
            return f"{symbol} 的盘前与盘后市场状态发生变化，且结果不利于原判断，当前更接近市场状态识别问题。"
        if category == "strategy-composition issue":
            return f"{symbol} 命中的规则存在混合决策或降权痕迹，当前更接近策略组合问题。"
        if category == "rule issue":
            return f"{symbol} 命中的正式规则已被选中，但盘后结果不支持该判断，当前更接近规则问题。"
        if category == "execution issue":
            return f"{symbol} 已存在明确执行证据，结果更接近执行层面的偏差。"
        if state != "ready":
            return f"{symbol} 当前证据不足以落入固定问题类别，先按暂不可归因处理。"
        return f"{symbol} 当前结果没有落入固定五类问题，按规则归为暂不可归因。"

    def _aggregate_attribution_state(self, states: list[str]) -> CoverageState:
        if any(state == "conflict" for state in states):
            return "conflict"
        if any(state == "invalid" for state in states):
            return "invalid"
        if any(state == "insufficient_coverage" for state in states):
            return "partial"
        if any(state == "partial" for state in states):
            return "partial"
        if any(state == "unavailable" for state in states):
            return "unavailable"
        if any(state == "degraded" for state in states):
            return "degraded"
        return "ready"

    async def generate_optimization_proposals(
        self,
        request: OptimizationProposalGenerationRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> OptimizationProposalCollectionResult:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to generate optimization proposals")
        async with self._session_scope_factory() as session:
            review, plan, instance, strategy_version, strategy, memberships = await self._load_proposal_context(
                session,
                post_market_review_id=UUID(request.post_market_review_id),
            )
            existing = await self.strategy_repository.list_proposals_for_review(
                session,
                post_market_review_id=review.post_market_review_id,
            )
            proposals = await self._generate_or_reuse_proposals(
                session,
                review=review,
                plan=plan,
                instance=instance,
                strategy_version=strategy_version,
                strategy=strategy,
                memberships=memberships,
                existing=existing,
                actor_id=actor_id,
            )
            items = [await self._to_optimization_proposal_view(session, proposal) for proposal in proposals]
            state = self._collection_state(items)
            return OptimizationProposalCollectionResult(
                state=state,
                count=len(items),
                items=items,
                happened="已基于正式盘后结果与结构化归因生成分离的规则、画像和策略建议。",
                affected="建议只会进入建议生命周期，不会直接改写正式规则、画像、策略或当前策略指针。",
                repair_guidance="如需继续处理，请先进入复核；只有策略修订建议允许在现有正式治理内生成草稿。",
            )

    async def list_optimization_proposals(
        self,
        *,
        actor_id: str,
        actor_role: str,
        post_market_review_id: str | None = None,
        proposal_type: str | None = None,
        limit: int = 50,
    ) -> OptimizationProposalCollectionResult:
        del actor_id
        if actor_role not in {"viewer", "operator", "admin"}:
            raise PermissionError("viewer permission is required to view optimization proposals")
        proposal_type_enum = self._parse_proposal_type(proposal_type) if proposal_type else None
        async with self._session_scope_factory() as session:
            if post_market_review_id is not None:
                proposals = await self.strategy_repository.list_proposals_for_review(
                    session,
                    post_market_review_id=UUID(post_market_review_id),
                    proposal_type=proposal_type_enum,
                    limit=limit,
                )
            else:
                proposals = await self.strategy_repository.list_proposals(
                    session,
                    proposal_type=proposal_type_enum,
                    limit=limit,
                )
            items = [await self._to_optimization_proposal_view(session, proposal) for proposal in proposals]
            state = self._collection_state(items)
            return OptimizationProposalCollectionResult(
                state=state,
                count=len(items),
                items=items,
                happened="已读取正式盘后优化建议列表。",
                affected="页面会按规则、画像、策略三条独立建议展示当前状态和可执行动作。",
                repair_guidance="如建议为空，请先完成盘后结果评估、结构化归因，并生成本次优化建议。",
            )

    async def get_optimization_proposal(
        self,
        proposal_id: str | UUID,
        *,
        actor_id: str,
        actor_role: str,
    ) -> OptimizationProposalView:
        del actor_id
        if actor_role not in {"viewer", "operator", "admin"}:
            raise PermissionError("viewer permission is required to view optimization proposals")
        async with self._session_scope_factory() as session:
            proposal = await self.strategy_repository.get_proposal(session, proposal_id)
            if proposal is None:
                raise LookupError("optimization proposal not found")
            return await self._to_optimization_proposal_view(session, proposal)

    async def review_optimization_proposal(
        self,
        proposal_id: str | UUID,
        request: OptimizationProposalReviewRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> OptimizationProposalView:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to review optimization proposals")
        async with self._session_scope_factory() as session:
            proposal = await self.strategy_repository.get_proposal(session, proposal_id)
            if proposal is None:
                raise LookupError("optimization proposal not found")
            before = self._proposal_audit_state(proposal)
            from_state = proposal.lifecycle_state
            to_state = from_state
            if request.action == "start_review":
                to_state = ProposalLifecycleState.in_review
                self._lifecycle_validator.validate(from_state, to_state)
            elif request.action == "continue_observing":
                if from_state is not ProposalLifecycleState.in_review:
                    raise ValueError("只有进入复核后的建议才能回到继续观察。")
                to_state = ProposalLifecycleState.draft
            elif request.action == "reject":
                to_state = ProposalLifecycleState.rejected
                self._lifecycle_validator.validate(from_state, to_state)
            proposal.lifecycle_state = to_state
            proposal.updated_at = datetime.now(UTC)
            proposal.updated_by = actor_id
            proposal.evidence_json = {
                **(proposal.evidence_json or {}),
                "last_review_action": request.action,
                "last_review_reason": request.reason,
            }
            with canonical_write_scope("strategy", "PostMarketReviewService.review_optimization_proposal"):
                await self.strategy_repository.record_lifecycle_event(
                    session,
                    object_id=proposal.optimization_proposal_id,
                    from_state=from_state.value,
                    to_state=to_state.value,
                    actor_id=actor_id,
                    actor_role=actor_role,
                    reason=request.reason,
                    before_state=before,
                    after_state=self._proposal_audit_state(proposal),
                    correlation_id=str(proposal.post_market_review_id),
                )
            return await self._to_optimization_proposal_view(session, proposal)

    async def accept_optimization_proposal_to_draft(
        self,
        proposal_id: str | UUID,
        request: OptimizationProposalAcceptRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> OptimizationProposalView:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to accept optimization proposals")
        async with self._session_scope_factory() as session:
            proposal = await self.strategy_repository.get_proposal(session, proposal_id)
            if proposal is None:
                raise LookupError("optimization proposal not found")
            if proposal.proposal_type is not ProposalType.strategy_revision:
                raise ValueError("当前建议类型没有安全的正式草稿通道，只能继续观察或拒绝。")
        strategy_service = StrategyCenterService(session_scope_factory=self._session_scope_factory)
        await strategy_service.accept_proposal_to_draft(
            proposal_id,
            StrategyProposalAcceptRequest(
                reason=request.reason,
                linked_draft_version_id=request.linked_draft_version_id,
            ),
            actor_id=actor_id,
            actor_role=actor_role,
        )
        async with self._session_scope_factory() as session:
            proposal = await self.strategy_repository.get_proposal(session, proposal_id)
            assert proposal is not None
            return await self._to_optimization_proposal_view(session, proposal)

    async def _load_proposal_context(
        self,
        session: AsyncSession,
        *,
        post_market_review_id: UUID,
    ) -> tuple[PostMarketReview, Any, Any, StrategyVersion, Strategy, list[StrategyRuleMembership]]:
        review = await self.review_repository.get_review(session, post_market_review_id)
        if review is None:
            raise LookupError("post-market review is missing")
        if (review.signal_results_json or {}).get("policy_version") != SIGNAL_OUTCOME_POLICY_VERSION:
            raise ValueError("post-market review is missing finalized RT-S10-001 evidence")
        if (review.attribution_json or {}).get("policy_version") != STRUCTURED_ATTRIBUTION_POLICY_VERSION:
            raise ValueError("post-market review is missing finalized RT-S10-002 evidence")
        plan = await self.review_repository.get_plan(session, review.trading_day_plan_id)
        if plan is None:
            raise LookupError("trading day plan is missing")
        instance = await self.review_repository.get_daily_strategy_instance(session, plan.daily_strategy_instance_id)
        if instance is None:
            raise LookupError("daily strategy instance is missing")
        strategy_version = await self.strategy_repository.get_version(session, instance.strategy_version_id)
        if strategy_version is None:
            raise LookupError("strategy version is missing")
        strategy = await self.strategy_repository.get_strategy(session, strategy_version.strategy_id)
        if strategy is None:
            raise LookupError("strategy is missing")
        memberships = await self.strategy_repository.list_rule_memberships(
            session,
            strategy_version_id=strategy_version.strategy_version_id,
        )
        return review, plan, instance, strategy_version, strategy, memberships

    async def _generate_or_reuse_proposals(
        self,
        session: AsyncSession,
        *,
        review: PostMarketReview,
        plan: Any,
        instance: Any,
        strategy_version: StrategyVersion,
        strategy: Strategy,
        memberships: list[StrategyRuleMembership],
        existing: list[OptimizationProposal],
        actor_id: str,
    ) -> list[OptimizationProposal]:
        signal_results = list((review.signal_results_json or {}).get("signals") or [])
        attributions = list((review.attribution_json or {}).get("signals") or [])
        attribution_by_signal_id = {str(item.get("signal_id")): item for item in attributions if item.get("signal_id")}
        membership_by_rule_id = {str(item.rule_version_id): item for item in memberships}
        all_rule_ids = sorted(
            {
                rule_id
                for signal in signal_results
                for rule_id in ((signal.get("matched_rule") or {}).get("rule_version_ids") or [])
                if rule_id
            }
        )
        rule_versions = {
            str(item.rule_version_id): item
            for item in await self.strategy_repository.list_rule_versions_by_ids(
                session,
                rule_version_ids=[UUID(rule_id) for rule_id in all_rule_ids],
            )
        }
        proposals: list[OptimizationProposal] = []
        for rule_id in all_rule_ids:
            candidate = self._build_rule_candidate(
                review=review,
                plan=plan,
                instance=instance,
                strategy_version=strategy_version,
                strategy=strategy,
                rule_version=rule_versions.get(rule_id),
                membership=membership_by_rule_id.get(rule_id),
                signal_results=signal_results,
                attribution_by_signal_id=attribution_by_signal_id,
            )
            proposals.append(
                await self._persist_or_reuse_candidate(
                    session,
                    candidate=candidate,
                    existing=existing,
                    actor_id=actor_id,
                )
            )
        author_candidate = await self._build_author_candidate(
            session,
            review=review,
            plan=plan,
            instance=instance,
            strategy_version=strategy_version,
            strategy=strategy,
            signal_results=signal_results,
            attribution_by_signal_id=attribution_by_signal_id,
        )
        proposals.append(
            await self._persist_or_reuse_candidate(
                session,
                candidate=author_candidate,
                existing=existing,
                actor_id=actor_id,
            )
        )
        strategy_candidate = self._build_strategy_candidate(
            review=review,
            plan=plan,
            instance=instance,
            strategy_version=strategy_version,
            strategy=strategy,
            memberships=memberships,
            signal_results=signal_results,
            attribution_by_signal_id=attribution_by_signal_id,
        )
        proposals.append(
            await self._persist_or_reuse_candidate(
                session,
                candidate=strategy_candidate,
                existing=existing,
                actor_id=actor_id,
            )
        )
        return proposals

    def _build_rule_candidate(
        self,
        *,
        review: PostMarketReview,
        plan: Any,
        instance: Any,
        strategy_version: StrategyVersion,
        strategy: Strategy,
        rule_version: RuleVersion | None,
        membership: StrategyRuleMembership | None,
        signal_results: list[dict[str, Any]],
        attribution_by_signal_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        rule_id = str(rule_version.rule_version_id if rule_version is not None else membership.rule_version_id)
        matched_signals = [
            signal
            for signal in signal_results
            if rule_id in ((signal.get("matched_rule") or {}).get("rule_version_ids") or [])
        ]
        attribution_items = [
            attribution_by_signal_id[str(signal.get("signal_id"))]
            for signal in matched_signals
            if str(signal.get("signal_id")) in attribution_by_signal_id
        ]
        evidence_state = self._proposal_evidence_state(review=review, signal_results=matched_signals, attributions=attribution_items)
        negative_ready_count = sum(1 for signal in matched_signals if self._is_negative_ready_signal(signal))
        categories = sorted({item.get("category") for item in attribution_items if item.get("category")})
        recommendation_state: ProposalRecommendationState = "continue_observing"
        if evidence_state == "ready" and "rule issue" in categories and negative_ready_count >= 2:
            recommendation_state = "create_draft_review_suggestion"
        reasons = [
            f"matched_signal_count={len(matched_signals)}",
            f"negative_ready_signal_count={negative_ready_count}",
            f"attribution_categories={','.join(categories) if categories else 'none'}",
        ]
        if membership is not None:
            reasons.append(f"strategy_membership_id={membership.membership_id}")
        rationale = (
            f"{rule_version.title if rule_version is not None and rule_version.title else rule_id} "
            f"当前仅基于单日盘后证据生成规则层建议，正式规则不会被直接改写。"
        )
        evidence = self._proposal_evidence_payload(
            proposal_type=ProposalType.rule_optimization,
            review=review,
            plan=plan,
            instance=instance,
            strategy_version=strategy_version,
            strategy=strategy,
            signal_results=matched_signals,
            attributions=attribution_items,
            recommendation_state=recommendation_state,
            deterministic_reason_list=reasons,
            target_asset_type="RuleVersion",
            target_asset_id=rule_id,
            relevant_rule_version_ids=[rule_id],
            relevant_author_profile_version_ids=self._strategy_author_profile_ids(strategy_version),
            relevant_strategy_membership_ids=[str(membership.membership_id)] if membership is not None else [],
        )
        return {
            "proposal_type": ProposalType.rule_optimization,
            "target_asset_type": "RuleVersion",
            "target_asset_id": UUID(rule_id),
            "base_version_id": UUID(rule_id),
            "proposed_changes": {
                "recommended_action": recommendation_state,
                "action_label": PROPOSAL_RECOMMENDATION_LABELS[recommendation_state],
                "rule_title": rule_version.title if rule_version is not None else None,
            },
            "evidence": {
                **evidence,
                "rationale": rationale,
                "evidence_state": evidence_state,
                "target": {
                    "asset_type": "RuleVersion",
                    "asset_id": rule_id,
                    "label": rule_version.title if rule_version is not None and rule_version.title else rule_id,
                    "strategy_membership_ids": [str(membership.membership_id)] if membership is not None else [],
                    "rule_version_ids": [rule_id],
                    "author_profile_version_ids": [],
                },
            },
            "confidence": self._confidence_value(evidence_state=evidence_state, negative_ready_count=negative_ready_count, bonus=0.05 if "rule issue" in categories else 0.0),
        }

    async def _build_author_candidate(
        self,
        session: AsyncSession,
        *,
        review: PostMarketReview,
        plan: Any,
        instance: Any,
        strategy_version: StrategyVersion,
        strategy: Strategy,
        signal_results: list[dict[str, Any]],
        attribution_by_signal_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        profile_id = (
            strategy_version.author_validated_profile_version_id
            or strategy_version.author_rule_profile_version_id
            or strategy_version.author_method_profile_version_id
        )
        if profile_id is None:
            raise ValueError("author profile target is missing for post-market optimization proposal")
        profile = await self.strategy_repository.get_author_profile_version(session, profile_id)
        if profile is None:
            raise LookupError("author profile version is missing")
        attributions = [
            attribution_by_signal_id[str(signal.get("signal_id"))]
            for signal in signal_results
            if str(signal.get("signal_id")) in attribution_by_signal_id
        ]
        evidence_state = self._proposal_evidence_state(review=review, signal_results=signal_results, attributions=attributions)
        negative_ready_count = sum(1 for signal in signal_results if self._is_negative_ready_signal(signal))
        categories = sorted({item.get("category") for item in attributions if item.get("category")})
        recommendation_state: ProposalRecommendationState = "continue_observing"
        if evidence_state == "ready" and negative_ready_count >= 2 and any(
            category in {"unattributable", "market-state identification issue"} for category in categories
        ):
            recommendation_state = "review_author_profile"
        reasons = [
            f"signal_count={len(signal_results)}",
            f"negative_ready_signal_count={negative_ready_count}",
            f"attribution_categories={','.join(categories) if categories else 'none'}",
            f"author_profile_kind={profile.profile_kind.value}",
        ]
        rationale = f"{AUTHOR_PROFILE_KIND_LABELS[profile.profile_kind]} 当前只接收单日证据形成复核建议，不会直接覆盖已发布画像。"
        evidence = self._proposal_evidence_payload(
            proposal_type=ProposalType.author_profile_revision,
            review=review,
            plan=plan,
            instance=instance,
            strategy_version=strategy_version,
            strategy=strategy,
            signal_results=signal_results,
            attributions=attributions,
            recommendation_state=recommendation_state,
            deterministic_reason_list=reasons,
            target_asset_type="AuthorProfileVersion",
            target_asset_id=str(profile.author_profile_version_id),
            relevant_rule_version_ids=sorted(
                {
                    rule_id
                    for signal in signal_results
                    for rule_id in ((signal.get("matched_rule") or {}).get("rule_version_ids") or [])
                    if rule_id
                }
            ),
            relevant_author_profile_version_ids=[str(profile.author_profile_version_id)],
            relevant_strategy_membership_ids=[],
        )
        return {
            "proposal_type": ProposalType.author_profile_revision,
            "target_asset_type": "AuthorProfileVersion",
            "target_asset_id": profile.author_profile_version_id,
            "base_version_id": profile.author_profile_version_id,
            "proposed_changes": {
                "recommended_action": recommendation_state,
                "action_label": PROPOSAL_RECOMMENDATION_LABELS[recommendation_state],
                "profile_kind": profile.profile_kind.value,
            },
            "evidence": {
                **evidence,
                "rationale": rationale,
                "evidence_state": evidence_state,
                "target": {
                    "asset_type": "AuthorProfileVersion",
                    "asset_id": str(profile.author_profile_version_id),
                    "label": f"{AUTHOR_PROFILE_KIND_LABELS[profile.profile_kind]} v{profile.version_no}",
                    "strategy_membership_ids": [],
                    "rule_version_ids": evidence["relevant_rule_version_ids"],
                    "author_profile_version_ids": [str(profile.author_profile_version_id)],
                },
            },
            "confidence": self._confidence_value(evidence_state=evidence_state, negative_ready_count=negative_ready_count, bonus=0.02),
        }

    def _build_strategy_candidate(
        self,
        *,
        review: PostMarketReview,
        plan: Any,
        instance: Any,
        strategy_version: StrategyVersion,
        strategy: Strategy,
        memberships: list[StrategyRuleMembership],
        signal_results: list[dict[str, Any]],
        attribution_by_signal_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        attributions = [
            attribution_by_signal_id[str(signal.get("signal_id"))]
            for signal in signal_results
            if str(signal.get("signal_id")) in attribution_by_signal_id
        ]
        evidence_state = self._proposal_evidence_state(review=review, signal_results=signal_results, attributions=attributions)
        negative_ready_count = sum(1 for signal in signal_results if self._is_negative_ready_signal(signal))
        categories = sorted({item.get("category") for item in attributions if item.get("category")})
        affected_rule_ids = sorted(
            {
                rule_id
                for signal in signal_results
                for rule_id in ((signal.get("matched_rule") or {}).get("rule_version_ids") or [])
                if rule_id
            }
        )
        strategy_issue_count = sum(
            1
            for item in attributions
            if item.get("category") in {"strategy-composition issue", "market-state identification issue"}
        )
        recommendation_state: ProposalRecommendationState = "continue_observing"
        proposed_weight_changes: list[dict[str, Any]] = []
        if evidence_state == "ready" and strategy_issue_count >= 1 and negative_ready_count >= 1:
            recommendation_state = "create_draft_review_suggestion"
            for membership in memberships:
                rule_id = str(membership.rule_version_id)
                if rule_id not in affected_rule_ids or membership.base_weight is None:
                    continue
                current_weight = float(membership.base_weight)
                proposed_weight_changes.append(
                    {
                        "rule_version_id": rule_id,
                        "base_weight": round(current_weight * 0.8, 6),
                    }
                )
        reasons = [
            f"signal_count={len(signal_results)}",
            f"negative_ready_signal_count={negative_ready_count}",
            f"strategy_issue_signal_count={strategy_issue_count}",
            f"attribution_categories={','.join(categories) if categories else 'none'}",
        ]
        rationale = "本次策略建议仅依据正式盘后单日证据生成，如被接受也只能生成草稿，不会发布或切换当前正式策略。"
        evidence = self._proposal_evidence_payload(
            proposal_type=ProposalType.strategy_revision,
            review=review,
            plan=plan,
            instance=instance,
            strategy_version=strategy_version,
            strategy=strategy,
            signal_results=signal_results,
            attributions=attributions,
            recommendation_state=recommendation_state,
            deterministic_reason_list=reasons,
            target_asset_type="StrategyVersion",
            target_asset_id=str(strategy_version.strategy_version_id),
            relevant_rule_version_ids=affected_rule_ids,
            relevant_author_profile_version_ids=self._strategy_author_profile_ids(strategy_version),
            relevant_strategy_membership_ids=[
                str(item.membership_id)
                for item in memberships
                if str(item.rule_version_id) in affected_rule_ids
            ],
        )
        proposed_changes: dict[str, Any] = {
            "recommended_action": recommendation_state,
            "action_label": PROPOSAL_RECOMMENDATION_LABELS[recommendation_state],
        }
        if proposed_weight_changes:
            proposed_changes["proposed_weight_changes"] = proposed_weight_changes
            proposed_changes["summary"] = "降低本次异常命中规则的基础权重，先生成草稿再进入正式复核。"
        return {
            "proposal_type": ProposalType.strategy_revision,
            "target_asset_type": "StrategyVersion",
            "target_asset_id": strategy_version.strategy_version_id,
            "base_version_id": strategy_version.strategy_version_id,
            "proposed_changes": proposed_changes,
            "evidence": {
                **evidence,
                "rationale": rationale,
                "evidence_state": evidence_state,
                "target": {
                    "asset_type": "StrategyVersion",
                    "asset_id": str(strategy_version.strategy_version_id),
                    "label": f"{strategy_version.title or strategy.business_key} v{strategy_version.version_no}",
                    "strategy_membership_ids": evidence["relevant_strategy_membership_ids"],
                    "rule_version_ids": affected_rule_ids,
                    "author_profile_version_ids": evidence["relevant_author_profile_version_ids"],
                },
            },
            "confidence": self._confidence_value(evidence_state=evidence_state, negative_ready_count=negative_ready_count, bonus=0.08 if proposed_weight_changes else 0.0),
        }

    async def _persist_or_reuse_candidate(
        self,
        session: AsyncSession,
        *,
        candidate: dict[str, Any],
        existing: list[OptimizationProposal],
        actor_id: str,
    ) -> OptimizationProposal:
        fingerprint = candidate["evidence"]["proposal_generation_fingerprint"]
        for proposal in existing:
            if (
                proposal.proposal_type == candidate["proposal_type"]
                and proposal.target_asset_id == candidate["target_asset_id"]
                and (proposal.evidence_json or {}).get("proposal_generation_fingerprint") == fingerprint
            ):
                return proposal
        proposal = OptimizationProposal(
            optimization_proposal_id=uuid4(),
            post_market_review_id=UUID(candidate["evidence"]["post_market_review_id"]),
            proposal_type=candidate["proposal_type"],
            target_asset_type=candidate["target_asset_type"],
            target_asset_id=candidate["target_asset_id"],
            revision_no=await self.strategy_repository.next_proposal_revision_no(
                session,
                post_market_review_id=UUID(candidate["evidence"]["post_market_review_id"]),
                target_asset_id=candidate["target_asset_id"],
                proposal_type=candidate["proposal_type"],
            ),
            base_version_id=candidate["base_version_id"],
            proposed_changes=candidate["proposed_changes"],
            evidence_json=candidate["evidence"],
            confidence=candidate["confidence"],
            lifecycle_state=ProposalLifecycleState.draft,
            accepted_draft_version_id=None,
            created_by=actor_id,
            updated_by=actor_id,
        )
        with canonical_write_scope("strategy", "PostMarketReviewService.generate_optimization_proposals"):
            await self.strategy_repository.add_proposal(session, proposal)
            await self.strategy_repository.record_lifecycle_event(
                session,
                object_id=proposal.optimization_proposal_id,
                from_state=None,
                to_state=ProposalLifecycleState.draft.value,
                actor_id=actor_id,
                actor_role="operator",
                reason=candidate["evidence"].get("rationale"),
                before_state=None,
                after_state=self._proposal_audit_state(proposal),
                correlation_id=str(proposal.post_market_review_id),
            )
        return proposal

    def _proposal_evidence_payload(
        self,
        *,
        proposal_type: ProposalType,
        review: PostMarketReview,
        plan: Any,
        instance: Any,
        strategy_version: StrategyVersion,
        strategy: Strategy,
        signal_results: list[dict[str, Any]],
        attributions: list[dict[str, Any]],
        recommendation_state: ProposalRecommendationState,
        deterministic_reason_list: list[str],
        target_asset_type: str,
        target_asset_id: str,
        relevant_rule_version_ids: list[str],
        relevant_author_profile_version_ids: list[str],
        relevant_strategy_membership_ids: list[str],
    ) -> dict[str, Any]:
        signal_ids = [str(item.get("signal_id")) for item in signal_results if item.get("signal_id")]
        attribution_categories = [str(item.get("category")) for item in attributions if item.get("category")]
        source_quality_states = {
            "review_quality_status": _state(review.quality_status),
            "signal_result_state": self._aggregate_signal_states(signal_results),
            "attribution_state": self._aggregate_attribution_state([str(item.get("state") or "ready") for item in attributions]) if attributions else "unavailable",
        }
        payload = {
            "policy_version": OPTIMIZATION_PROPOSAL_POLICY_VERSION,
            "proposal_type": proposal_type.value,
            "post_market_review_id": str(review.post_market_review_id),
            "trading_day_plan_id": str(plan.trading_day_plan_id),
            "daily_strategy_instance_id": str(instance.daily_strategy_instance_id),
            "strategy_id": str(strategy.strategy_id),
            "strategy_version_id": str(strategy_version.strategy_version_id),
            "signal_ids": signal_ids,
            "attribution_categories": attribution_categories,
            "outcome_metrics": [
                {
                    "signal_id": str(item.get("signal_id")),
                    "symbol": item.get("symbol"),
                    "state": item.get("state"),
                    "return_state": (item.get("return") or {}).get("state"),
                    "return_value": (item.get("return") or {}).get("value"),
                    "actual_result_state": (item.get("actual_result") or {}).get("state"),
                    "actual_result_value": (item.get("actual_result") or {}).get("value"),
                }
                for item in signal_results
            ],
            "relevant_rule_version_ids": relevant_rule_version_ids,
            "relevant_author_profile_version_ids": relevant_author_profile_version_ids,
            "relevant_strategy_membership_ids": relevant_strategy_membership_ids,
            "source_quality_states": source_quality_states,
            "deterministic_reason_list": deterministic_reason_list,
            "recommendation_state": recommendation_state,
            "target_asset_type": target_asset_type,
            "target_asset_id": target_asset_id,
            "current_strategy_version_id": str(strategy.current_published_version_id) if strategy.current_published_version_id else None,
        }
        payload["proposal_generation_fingerprint"] = _json_fingerprint(payload)
        return payload

    async def _to_optimization_proposal_view(
        self,
        session: AsyncSession,
        proposal: OptimizationProposal,
    ) -> OptimizationProposalView:
        evidence = proposal.evidence_json or {}
        target = await self._proposal_target_view(session, proposal, evidence)
        recommendation_state = str((proposal.proposed_changes or {}).get("recommended_action") or evidence.get("recommendation_state") or "continue_observing")
        evidence_state = str(evidence.get("evidence_state") or "unavailable")
        return OptimizationProposalView(
            proposal_id=str(proposal.optimization_proposal_id),
            proposal_type=proposal.proposal_type.value,
            proposal_type_label=PROPOSAL_TYPE_LABELS[proposal.proposal_type],
            lifecycle_state=proposal.lifecycle_state.value,
            lifecycle_label=PROPOSAL_LIFECYCLE_LABELS[proposal.lifecycle_state],
            revision_no=proposal.revision_no,
            confidence=float(proposal.confidence) if proposal.confidence is not None else None,
            evidence_state=evidence_state,
            evidence_label=PROPOSAL_EVIDENCE_LABELS.get(evidence_state, "证据暂不可用"),
            recommendation_state=recommendation_state,
            recommendation_label=PROPOSAL_RECOMMENDATION_LABELS.get(recommendation_state, "继续观察"),
            rationale=str(evidence.get("rationale") or "未提供"),
            target=target,
            review_binding={
                "post_market_review_id": evidence.get("post_market_review_id"),
                "trading_day_plan_id": evidence.get("trading_day_plan_id"),
                "daily_strategy_instance_id": evidence.get("daily_strategy_instance_id"),
                "strategy_version_id": evidence.get("strategy_version_id"),
            },
            base_version_id=str(proposal.base_version_id) if proposal.base_version_id else None,
            accepted_draft_version_id=str(proposal.accepted_draft_version_id) if proposal.accepted_draft_version_id else None,
            proposed_changes=proposal.proposed_changes or {},
            evidence=evidence,
            created_at=proposal.created_at.isoformat() if proposal.created_at else None,
            updated_at=proposal.updated_at.isoformat() if proposal.updated_at else None,
            available_actions=self._proposal_available_actions(proposal.proposal_type, proposal.lifecycle_state),
            partial_reasons=list(evidence.get("deterministic_reason_list") or []),
            limitations=list(evidence.get("limitations") or []),
        )

    async def _proposal_target_view(
        self,
        session: AsyncSession,
        proposal: OptimizationProposal,
        evidence: dict[str, Any],
    ) -> OptimizationProposalTargetView:
        target = evidence.get("target") or {}
        label = str(target.get("label") or proposal.target_asset_id)
        if proposal.proposal_type is ProposalType.rule_optimization:
            row = await self.strategy_repository.get_rule_version(session, proposal.target_asset_id)
            if row is not None and row.title:
                label = row.title
        elif proposal.proposal_type is ProposalType.author_profile_revision:
            row = await self.strategy_repository.get_author_profile_version(session, proposal.target_asset_id)
            if row is not None:
                label = f"{AUTHOR_PROFILE_KIND_LABELS[row.profile_kind]} v{row.version_no}"
        elif proposal.proposal_type is ProposalType.strategy_revision:
            row = await self.strategy_repository.get_version(session, proposal.target_asset_id)
            if row is not None:
                label = f"{row.title or '正式策略'} v{row.version_no}"
        return OptimizationProposalTargetView(
            asset_type=proposal.target_asset_type,
            asset_id=str(proposal.target_asset_id),
            label=label,
            strategy_membership_ids=list(target.get("strategy_membership_ids") or []),
            rule_version_ids=list(target.get("rule_version_ids") or []),
            author_profile_version_ids=list(target.get("author_profile_version_ids") or []),
        )

    def _proposal_available_actions(
        self,
        proposal_type: ProposalType,
        lifecycle_state: ProposalLifecycleState,
    ) -> list[str]:
        actions = {
            ProposalLifecycleState.draft: ["start_review", "reject"],
            ProposalLifecycleState.in_review: ["continue_observing", "reject"],
            ProposalLifecycleState.accepted: ["archive"],
            ProposalLifecycleState.rejected: ["archive"],
            ProposalLifecycleState.archived: [],
            ProposalLifecycleState.superseded: ["archive"],
        }
        allowed = list(actions[lifecycle_state])
        if proposal_type is ProposalType.strategy_revision and lifecycle_state is ProposalLifecycleState.in_review:
            allowed.insert(1, "accept_to_draft")
        return allowed

    def _proposal_audit_state(self, proposal: OptimizationProposal) -> dict[str, Any]:
        return {
            "proposal_id": str(proposal.optimization_proposal_id),
            "proposal_type": proposal.proposal_type.value,
            "target_asset_type": proposal.target_asset_type,
            "target_asset_id": str(proposal.target_asset_id),
            "base_version_id": str(proposal.base_version_id) if proposal.base_version_id else None,
            "accepted_draft_version_id": str(proposal.accepted_draft_version_id) if proposal.accepted_draft_version_id else None,
            "lifecycle_state": proposal.lifecycle_state.value,
            "revision_no": proposal.revision_no,
        }

    def _proposal_evidence_state(
        self,
        *,
        review: PostMarketReview,
        signal_results: list[dict[str, Any]],
        attributions: list[dict[str, Any]],
    ) -> CoverageState:
        states = [self._aggregate_signal_states(signal_results)]
        if attributions:
            states.append(self._aggregate_attribution_state([str(item.get("state") or "ready") for item in attributions]))
        if _state(review.quality_status) != QualityStatus.complete.value:
            states.append("partial")
        return self._aggregate_signal_states_from_values(states)

    def _aggregate_signal_states(self, signal_results: list[dict[str, Any]]) -> CoverageState:
        return self._aggregate_signal_states_from_values([str(item.get("state") or "ready") for item in signal_results])

    def _aggregate_signal_states_from_values(self, states: list[str]) -> CoverageState:
        if any(state == "conflict" for state in states):
            return "conflict"
        if any(state == "invalid" for state in states):
            return "invalid"
        if any(state == "unavailable" for state in states):
            return "unavailable"
        if any(state == "insufficient_coverage" for state in states):
            return "insufficient_coverage"
        if any(state == "degraded" for state in states):
            return "degraded"
        if any(state == "partial" for state in states):
            return "partial"
        return "ready"

    def _is_negative_ready_signal(self, signal_result: dict[str, Any]) -> bool:
        return_fact = signal_result.get("return") or {}
        if return_fact.get("state") != "ready":
            return False
        try:
            return float(return_fact.get("value")) < 0
        except (TypeError, ValueError):
            return False

    def _strategy_author_profile_ids(self, strategy_version: StrategyVersion) -> list[str]:
        return [
            str(item)
            for item in [
                strategy_version.author_method_profile_version_id,
                strategy_version.author_rule_profile_version_id,
                strategy_version.author_validated_profile_version_id,
            ]
            if item is not None
        ]

    def _confidence_value(
        self,
        *,
        evidence_state: CoverageState,
        negative_ready_count: int,
        bonus: float = 0.0,
    ) -> float:
        base = 0.35 if evidence_state != "ready" else 0.5
        return min(0.95, round(base + min(negative_ready_count, 3) * 0.08 + bonus, 2))

    def _parse_proposal_type(self, value: str) -> ProposalType:
        try:
            return ProposalType(value)
        except ValueError as exc:
            raise ValueError("proposal_type 无效。") from exc

    def _collection_state(self, items: list[OptimizationProposalView]) -> Literal["ready", "partial", "empty"]:
        if not items:
            return "empty"
        if any(item.evidence_state != "ready" for item in items):
            return "partial"
        return "ready"
