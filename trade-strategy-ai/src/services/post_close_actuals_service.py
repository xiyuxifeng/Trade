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
from src.db.session import get_session_factory
from src.domain.enums import PostMarketReviewState, QualityStatus, SignalState, TradingDayPlanState
from src.models.market_data_snapshot import MarketSnapshot
from src.models.market_data_snapshot_item import MarketSnapshotItem
from src.models.market_data_snapshot_section import MarketSnapshotSection
from src.models.signal import Signal
from src.models.stage2_canonical import DatasetSnapshot, PostMarketReview


POST_CLOSE_ACTUALS_SECTION_ID = "post_close_symbol_ohlcv_actuals"
POST_CLOSE_ACTUALS_CONTRACT_VERSION = "post-close-symbol-ohlcv-actuals-v1"
SIGNAL_OUTCOME_POLICY_VERSION = "stage10-signal-outcome-v1"
STRUCTURED_ATTRIBUTION_POLICY_VERSION = "stage10-structured-attribution-v1"
CoverageState = Literal["ready", "partial", "unavailable", "conflict", "invalid", "insufficient_coverage", "degraded"]
AttributionCategory = Literal[
    "data issue",
    "market-state identification issue",
    "rule issue",
    "strategy-composition issue",
    "execution issue",
    "unattributable",
]


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
    ) -> None:
        self._session_scope_factory = session_scope_factory or self._default_session_scope_factory
        self.actuals_repository = actuals_repository or PostCloseActualsRepository()
        self.review_repository = review_repository or PostMarketReviewRepository()

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
