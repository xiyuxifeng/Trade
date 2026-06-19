from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
import hashlib
import inspect
import json
import statistics
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, model_validator

from src.db.repositories.backtest_run_repository import BacktestRunRepository
from src.db.session import get_session_factory


BUSINESS_STATE_LABELS = {
    "runnable": "可运行",
    "downgradeable": "可降级",
    "repair_required": "需修复",
    "not_runnable": "不可运行",
    "unavailable": "数据不可用",
    "insufficient_coverage": "覆盖不足",
    "conflict": "冲突",
    "permission_denied": "无权限",
    "invalid": "不可运行",
}

LEVEL_ORDER = {"level_1": 1, "level_2": 2, "level_3": 3}
FORMAL_BACKTEST_ENGINE_VERSION = "stage6-foundation-v1"
FORMAL_INDICATOR_VERSION = "dataset-bound-v1"
FORMAL_EXECUTION_POLICY_VERSION = "stage6-snapshot-only-v1"
FORMAL_DECISION_TIME_POLICY = "cn-a-share-close-plus-availability-v1"
FORMAL_MARKET_STATE_RESULT_VERSION = "stage6-market-state-result-v1"
CN_TZ = ZoneInfo("Asia/Shanghai")
SAMPLE_STATES = (
    "eligible",
    "evaluated_true",
    "evaluated_false",
    "condition_unavailable",
    "data_missing",
    "unsupported",
    "invalid",
    "skipped",
    "conflict",
    "market_state_unavailable",
)


class BacktestSelection(BaseModel):
    rule_version_id: UUID | None = None
    rule_family_id: UUID | None = None
    date_from: date
    date_to: date
    universe: dict[str, Any] = Field(default_factory=dict)
    benchmark_symbol: str
    mode: str = "full"
    requested_level: str = "level_1"
    profile_id: str | None = None

    @model_validator(mode="after")
    def _validate_selection(self) -> "BacktestSelection":
        if (self.rule_version_id is None) == (self.rule_family_id is None):
            raise ValueError("exactly one of rule_version_id or rule_family_id is required")
        if self.date_to < self.date_from:
            raise ValueError("date_to must be on or after date_from")
        return self

    @field_validator("requested_level")
    @classmethod
    def _validate_level(cls, value: str) -> str:
        if value not in LEVEL_ORDER:
            raise ValueError("requested_level must be one of level_1, level_2, level_3")
        return value


class BacktestDependencyResult(BaseModel):
    business_state: str
    canonical_state: str
    can_create_run: bool
    requested_level: str
    effective_level: str
    selection: dict[str, Any]
    coverage: dict[str, Any] = Field(default_factory=dict)
    unavailable_reasons: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    canonical_ids: dict[str, Any] = Field(default_factory=dict)
    fingerprints: dict[str, Any] = Field(default_factory=dict)


class BacktestRunCreateRequest(BaseModel):
    selection: BacktestSelection
    actor_id: str
    actor_role: str
    reason: str | None = None
    source_surface: str = "/rules/backtests"


class BacktestRunView(BaseModel):
    run_id: str
    status: str
    business_status: str
    rule_version_id: str | None = None
    rule_family_id: str | None = None
    frozen_rule_version_ids: list[str] = Field(default_factory=list)
    dataset_snapshot_id: str
    request_fingerprint: str
    reproducibility_fingerprint: str
    snapshot_only: bool
    progress: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class MarketStateMetricView(BaseModel):
    market_state_label: str
    market_state_model_version: str | None = None
    market_state_source_version: str | None = None
    eligible_sample_count: int = 0
    evaluated_sample_count: int = 0
    unavailable_sample_count: int = 0
    invalid_sample_count: int = 0
    conflict_sample_count: int = 0
    hit_trade_count: int = 0
    avg_return: float | None = None
    total_return: float | None = None
    win_rate: float | None = None
    max_drawdown: float | None = None
    coverage: float | None = None
    warnings: list[str] = Field(default_factory=list)
    result_fingerprint: str | None = None


class BacktestResultView(BaseModel):
    result_id: str
    run_id: str
    status: str
    requested_level: str
    effective_level: str
    market_state_model_version: str | None = None
    market_state_source_version: str | None = None
    market_state_result_version: str
    overall_metrics: dict[str, Any] = Field(default_factory=dict)
    per_market_state_metrics: list[MarketStateMetricView] = Field(default_factory=list)
    sample_state_counts: dict[str, int] = Field(default_factory=dict)
    coverage: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    result_fingerprint: str
    reproducibility_fingerprint: str


def _fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def _value(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    return value


def _id(value: Any) -> str | None:
    return str(value) if value is not None else None


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _business_state(canonical_state: str) -> str:
    return BUSINESS_STATE_LABELS.get(canonical_state, "不可运行")


async def _repo_call(repository: Any, method_name: str, session: Any, **kwargs: Any) -> Any:
    method = getattr(repository, method_name)
    signature = inspect.signature(method)
    parameters = list(signature.parameters)
    if parameters and parameters[0] == "session":
        return await method(session, **kwargs)
    return await method(**kwargs)


class BacktestApplicationService:
    def __init__(self, *, repository: Any | None = None, session_scope_factory: Any | None = None) -> None:
        self.repository = repository or BacktestRunRepository()
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

    async def _resolve_rules(self, session: Any, selection: BacktestSelection) -> tuple[Any | None, Any | None, list[Any], list[dict[str, Any]]]:
        reasons: list[dict[str, Any]] = []
        if selection.rule_version_id:
            rule_version = await _repo_call(
                self.repository,
                "get_rule_version",
                session,
                rule_version_id=selection.rule_version_id,
            )
            if rule_version is None:
                reasons.append({"code": "rule_version_unavailable", "message": "所选规则版本不存在或不可用。"})
                return None, None, [], reasons
            return rule_version, None, [rule_version], reasons

        rule_family = await _repo_call(
            self.repository,
            "get_rule_family_with_members",
            session,
            rule_family_id=selection.rule_family_id,
        )
        members = list(getattr(rule_family, "members", []) if rule_family is not None else [])
        if rule_family is None:
            reasons.append({"code": "rule_family_unavailable", "message": "所选规则族不存在或不可用。"})
        elif not members:
            reasons.append({"code": "rule_family_empty", "message": "所选规则族没有可冻结的规则版本。"})
        return None, rule_family, members, reasons

    async def _dependency_result(self, session: Any, selection: BacktestSelection) -> BacktestDependencyResult:
        rule_version, rule_family, rule_members, reasons = await self._resolve_rules(session, selection)
        coverage: dict[str, Any] = {}
        limitations: list[str] = []
        next_actions: list[str] = []
        canonical_ids: dict[str, Any] = {}
        fingerprints: dict[str, Any] = {}

        if rule_version is not None:
            canonical_ids["rule_version_id"] = _id(getattr(rule_version, "rule_version_id", None))
            fingerprints["rule_version"] = getattr(rule_version, "canonical_fingerprint", None)
        if rule_family is not None:
            canonical_ids["rule_family_id"] = _id(getattr(rule_family, "rule_family_id", None))
            canonical_ids["frozen_rule_version_ids"] = [
                _id(getattr(member, "rule_version_id", None)) for member in rule_members
            ]
            fingerprints["rule_family"] = getattr(rule_family, "canonical_fingerprint", None)
            fingerprints["frozen_rule_versions"] = [
                getattr(member, "canonical_fingerprint", None) for member in rule_members
            ]

        dataset = None
        if not reasons:
            dataset = await _repo_call(
                self.repository,
                "find_dataset_snapshot",
                session,
                date_from=selection.date_from,
                date_to=selection.date_to,
                benchmark_symbol=selection.benchmark_symbol,
                universe=selection.universe,
            )
        if dataset is None:
            reasons.append({"code": "dataset_snapshot_unavailable", "message": "没有覆盖本次区间和基准的正式历史行情快照。"})
            coverage["ohlcv"] = {"state": "unavailable", "available": None, "impact": "无法创建正式回测。"}
        else:
            dataset_state = _value(getattr(dataset, "lifecycle_state", None))
            date_from = getattr(dataset, "date_from", None)
            date_to = getattr(dataset, "date_to", None)
            if dataset_state != "ready":
                reasons.append({"code": "dataset_snapshot_invalid", "message": "历史行情快照当前不可用。"})
                coverage["ohlcv"] = {"state": "invalid", "available": False, "impact": "需要重新冻结数据快照。"}
            elif date_from and date_to and (date_from > selection.date_from or date_to < selection.date_to):
                reasons.append({"code": "dataset_snapshot_insufficient_coverage", "message": "历史行情快照没有完整覆盖回测区间。"})
                coverage["ohlcv"] = {"state": "insufficient_coverage", "available": None, "impact": "需要补齐历史行情。"}
            else:
                coverage["ohlcv"] = {
                    "state": "ready",
                    "available": True,
                    "dataset_snapshot_id": _id(getattr(dataset, "dataset_snapshot_id", None)),
                    "fingerprint": getattr(dataset, "content_fingerprint", None),
                }
                canonical_ids["dataset_snapshot_id"] = _id(getattr(dataset, "dataset_snapshot_id", None))
                fingerprints["dataset_snapshot"] = getattr(dataset, "content_fingerprint", None)

        market_snapshots: list[Any] = []
        if selection.requested_level in {"level_2", "level_3"} and dataset is not None:
            market_snapshots = await _repo_call(
                self.repository,
                "list_market_snapshots",
                session,
                date_from=selection.date_from,
                date_to=selection.date_to,
                market="CN",
            )
            if not market_snapshots:
                reasons.append({"code": "market_state_insufficient_coverage", "message": "没有覆盖本次区间的正式市场状态快照。"})
                coverage["market_state"] = {"state": "insufficient_coverage", "available": None, "impact": "需要补齐市场状态数据。"}
            else:
                decision_times = self._decision_times(selection.date_from, selection.date_to)
                market_snapshot_ids: list[str] = []
                market_snapshot_fingerprints: list[str] = []
                future_snapshot_dates: list[str] = []
                for snapshot in market_snapshots:
                    trade_date = _get(snapshot, "trade_date")
                    available_at = self._aware(_get(snapshot, "available_at"))
                    decision_time = decision_times.get(trade_date)
                    if available_at is None or decision_time is None or available_at > decision_time:
                        future_snapshot_dates.append(str(trade_date))
                        continue
                    market_snapshot_ids.append(str(_get(snapshot, "id", _get(snapshot, "snapshot_id"))))
                    market_snapshot_fingerprints.append(_get(snapshot, "content_fingerprint"))

                definition_version = _get(dataset, "market_state_definition_version") or "market-state-v1"
                states = []
                if market_snapshot_ids:
                    states = await _repo_call(
                        self.repository,
                        "list_market_states_for_run",
                        session,
                        date_from=selection.date_from,
                        date_to=selection.date_to,
                        market="CN",
                        definition_version=definition_version,
                        decision_times=decision_times,
                        market_snapshot_ids=market_snapshot_ids,
                    )
                source_versions = sorted(
                    {
                        str(_get(state, "source_feature_version"))
                        for state in states
                        if _get(state, "source_feature_version")
                    }
                )
                state_dates = {_get(state, "trade_date") for state in states}
                missing_dates = sorted(str(item) for item in (set(decision_times) - state_dates))
                if future_snapshot_dates:
                    reasons.append({
                        "code": "market_state_future_snapshot",
                        "message": "存在晚于模拟决策时间才可用的市场状态快照，不能用于正式回测。",
                    })
                if missing_dates:
                    reasons.append({
                        "code": "market_state_insufficient_coverage",
                        "message": "没有覆盖本次区间且可证明当时可用的正式市场状态。",
                    })
                if len(source_versions) > 1:
                    reasons.append({
                        "code": "market_state_source_conflict",
                        "message": "本次区间存在多个市场状态来源版本，不能混合作为正式结果。",
                    })

                if any(reason["code"].startswith("market_state_") for reason in reasons):
                    coverage["market_state"] = {
                        "state": "insufficient_coverage",
                        "available": None,
                        "snapshot_count": len(market_snapshots),
                        "point_in_time_state_count": len(states),
                        "impact": "无法创建 Level 2 分市场状态正式回测。",
                    }
                else:
                    coverage["market_state"] = {
                        "state": "ready",
                        "available": True,
                        "snapshot_count": len(market_snapshots),
                        "point_in_time_state_count": len(states),
                        "market_state_model_version": definition_version,
                        "market_state_source_version": source_versions[0] if source_versions else None,
                    }
                    canonical_ids["market_snapshot_ids"] = market_snapshot_ids
                    fingerprints["market_snapshots"] = market_snapshot_fingerprints
                    fingerprints["market_state_model_version"] = definition_version
                    fingerprints["market_state_source_version"] = source_versions[0] if source_versions else None
        elif selection.requested_level == "level_1":
            coverage["market_state"] = {"state": "not_required", "available": None}

        if selection.requested_level == "level_3":
            limitations.append("Level 3 的完整 Kaipan 强制校验将在后续任务中收口；本次基础仅记录请求等级。")

        if not reasons:
            canonical_state = "runnable"
            next_actions.append("提交正式回测")
        elif any(reason["code"].endswith("insufficient_coverage") for reason in reasons):
            canonical_state = "insufficient_coverage"
            next_actions.append("补齐缺失数据")
        elif any(reason["code"].endswith("invalid") for reason in reasons):
            canonical_state = "invalid"
            next_actions.append("重新冻结可用数据")
        else:
            canonical_state = "unavailable"
            next_actions.append("选择其他规则或数据区间")

        can_create_run = canonical_state == "runnable"
        return BacktestDependencyResult(
            business_state=_business_state(canonical_state if canonical_state != "insufficient_coverage" else "repair_required"),
            canonical_state=canonical_state,
            can_create_run=can_create_run,
            requested_level=selection.requested_level,
            effective_level=selection.requested_level if can_create_run else "unavailable",
            selection=selection.model_dump(mode="json"),
            coverage=coverage,
            unavailable_reasons=reasons,
            limitations=limitations,
            next_actions=next_actions,
            canonical_ids=canonical_ids,
            fingerprints=fingerprints,
        )

    async def check_dependencies(self, selection: BacktestSelection, *, actor_id: str, actor_role: str) -> BacktestDependencyResult:
        del actor_id, actor_role
        async with self._session_scope_factory() as session:
            return await self._dependency_result(session, selection)

    async def create_run(self, request: BacktestRunCreateRequest) -> BacktestRunView:
        if request.actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to create a formal backtest run")

        async with self._session_scope_factory() as session:
            dependency = await self._dependency_result(session, request.selection)
            if not dependency.can_create_run:
                raise ValueError(dependency.business_state)

            ids = dependency.canonical_ids
            fps = dependency.fingerprints
            request_identity = {
                "selection": request.selection.model_dump(mode="json"),
                "canonical_ids": ids,
                "fingerprints": fps,
                "snapshot_only": True,
                "engine_version": FORMAL_BACKTEST_ENGINE_VERSION,
                "execution_policy_version": FORMAL_EXECUTION_POLICY_VERSION,
                "decision_time_policy": FORMAL_DECISION_TIME_POLICY,
            }
            request_fingerprint = _fingerprint(request_identity)
            run_id = uuid4()
            reproducibility_fingerprint = _fingerprint({**request_identity, "run_id": str(run_id)})
            audit = {
                "actor_id": request.actor_id,
                "actor_role": request.actor_role,
                "time": datetime.now(UTC).isoformat(),
                "reason": request.reason,
                "source_surface": request.source_surface,
                "run_id": str(run_id),
                "before_state": None,
                "after_state": "dependency_checked",
            }
            payload = {
                "run_id": run_id,
                "rule_version_id": request.selection.rule_version_id,
                "rule_version_fingerprint": fps.get("rule_version"),
                "rule_version_no": None,
                "rule_family_id": request.selection.rule_family_id,
                "rule_family_fingerprint": fps.get("rule_family"),
                "frozen_rule_version_ids": ids.get("frozen_rule_version_ids") or (
                    [str(request.selection.rule_version_id)] if request.selection.rule_version_id else []
                ),
                "frozen_rule_version_fingerprints": fps.get("frozen_rule_versions") or (
                    [fps["rule_version"]] if fps.get("rule_version") else []
                ),
                "date_from": request.selection.date_from,
                "date_to": request.selection.date_to,
                "universe_json": request.selection.universe,
                "benchmark_symbol": request.selection.benchmark_symbol,
                "mode": request.selection.mode,
                "requested_level": request.selection.requested_level,
                "effective_level": dependency.effective_level,
                "dataset_snapshot_id": UUID(ids["dataset_snapshot_id"]),
                "dataset_fingerprint": fps["dataset_snapshot"],
                "market_snapshot_ids": ids.get("market_snapshot_ids") or [],
                "market_snapshot_fingerprints": fps.get("market_snapshots") or [],
                "market_state_model_version": fps.get("market_state_model_version"),
                "indicator_version": FORMAL_INDICATOR_VERSION,
                "engine_version": FORMAL_BACKTEST_ENGINE_VERSION,
                "execution_policy_version": FORMAL_EXECUTION_POLICY_VERSION,
                "recommendation_policy_version": None,
                "decision_time_policy": FORMAL_DECISION_TIME_POLICY,
                "request_fingerprint": request_fingerprint,
                "reproducibility_fingerprint": reproducibility_fingerprint,
                "snapshot_only": True,
                "status": "dependency_checked",
                "coverage_state": dependency.canonical_state,
                "quality_state": "not_executed",
                "unavailable_reasons": dependency.unavailable_reasons,
                "limitations": dependency.limitations,
                "progress_json": {"current_step": "已完成数据依赖检查", "percent": 0},
                "audit_json": audit,
                "actor_id": request.actor_id,
                "actor_role": request.actor_role,
                "reason": request.reason,
                "source_surface": request.source_surface,
                "before_state_json": None,
                "after_state_json": {"status": "dependency_checked"},
            }
            created = await _repo_call(self.repository, "create_backtest_run", session, payload=payload)
            return self._run_view(created)

    async def get_run(self, run_id: str, *, actor_id: str, actor_role: str) -> BacktestRunView:
        del actor_id, actor_role
        async with self._session_scope_factory() as session:
            run = await _repo_call(self.repository, "get_backtest_run", session, run_id=UUID(run_id))
            if run is None:
                raise LookupError("backtest run not found")
            return self._run_view(run)

    async def execute_run(self, run_id: str, *, actor_id: str, actor_role: str) -> BacktestResultView:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to execute a formal backtest run")
        async with self._session_scope_factory() as session:
            existing = await _repo_call(self.repository, "get_backtest_result_by_run", session, run_id=UUID(run_id))
            if existing is not None:
                return self._result_view(existing)
            run = await _repo_call(self.repository, "get_backtest_run", session, run_id=UUID(run_id))
            if run is None:
                raise LookupError("backtest run not found")
            payload = await self._execute_run_payload(session, run, actor_id=actor_id, actor_role=actor_role)
            created = await _repo_call(self.repository, "create_backtest_result", session, payload=payload)
            return self._result_view(created)

    async def get_result(self, run_id: str, *, actor_id: str, actor_role: str) -> BacktestResultView:
        del actor_id, actor_role
        async with self._session_scope_factory() as session:
            result = await _repo_call(self.repository, "get_backtest_result_by_run", session, run_id=UUID(run_id))
            if result is None:
                raise LookupError("backtest result not found")
            return self._result_view(result)

    async def _execute_run_payload(self, session: Any, run: Any, *, actor_id: str, actor_role: str) -> dict[str, Any]:
        if not bool(_get(run, "snapshot_only", True)):
            raise ValueError("正式回测只能使用固定快照执行。")
        date_from = _get(run, "date_from")
        date_to = _get(run, "date_to")
        effective_level = str(_get(run, "effective_level"))
        decision_times = self._decision_times(date_from, date_to)
        samples = await _repo_call(self.repository, "list_formal_samples_for_run", session, run=run)
        sample_state_counts = {state: 0 for state in SAMPLE_STATES}
        coverage = {
            "market_state": {"state": "not_required" if effective_level == "level_1" else "insufficient_coverage", "available": None},
            "samples": {"state": "ready" if samples else "insufficient_coverage", "count": len(samples)},
        }
        warnings: list[str] = []
        limitations = list(_get(run, "limitations", []) or [])
        states_by_date: dict[date, Any] = {}
        source_versions: set[str] = set()
        model_version = _get(run, "market_state_model_version")

        if effective_level != "level_1":
            states = await _repo_call(
                self.repository,
                "list_market_states_for_run",
                session,
                date_from=date_from,
                date_to=date_to,
                market="CN",
                definition_version=model_version,
                decision_times=decision_times,
                market_snapshot_ids=list(_get(run, "market_snapshot_ids", []) or []),
            )
            for state in states:
                trade_date = _get(state, "trade_date")
                available_at = self._aware(_get(state, "available_at"))
                decision_time = decision_times.get(trade_date)
                if available_at is None or decision_time is None or available_at > decision_time:
                    continue
                states_by_date.setdefault(trade_date, state)
                if _get(state, "source_feature_version"):
                    source_versions.add(str(_get(state, "source_feature_version")))
            missing_trade_dates = sorted(str(item) for item in (set(decision_times) - set(states_by_date)))
            market_state_ready = bool(states_by_date) and not missing_trade_dates
            coverage["market_state"] = {
                "state": "ready" if market_state_ready else "insufficient_coverage",
                "available": True if market_state_ready else None,
                "point_in_time_state_count": len(states_by_date),
                "required_trade_date_count": len(decision_times),
                "missing_trade_dates": missing_trade_dates,
            }
            if not states_by_date:
                warnings.append("缺少可证明当时可用的市场状态，样本不会计入亏损或胜率分母。")
            elif missing_trade_dates:
                warnings.append("部分交易日缺少可证明当时可用的市场状态，缺失日期样本不会计入亏损或胜率分母。")
            if len(source_versions) > 1:
                warnings.append("市场状态来源版本不一致，本次结果标记为无效。")

        buckets: dict[str, dict[str, Any]] = {}
        all_return_values: list[float] = []
        for sample in samples:
            sample_state = str(_get(sample, "sample_state", "invalid"))
            trade_date = _get(sample, "trade_date")
            if effective_level != "level_1" and trade_date not in states_by_date:
                sample_state_counts["market_state_unavailable"] += 1
                continue
            if sample_state not in sample_state_counts:
                sample_state = "invalid"
            sample_state_counts[sample_state] += 1
            if sample_state == "eligible":
                condition_result = _get(sample, "condition_result")
                sample_state_counts["evaluated_true" if condition_result is True else "evaluated_false"] += 1
            if sample_state != "eligible":
                continue
            state = states_by_date.get(trade_date)
            label = "全周期" if effective_level == "level_1" else str(_get(state, "primary_label"))
            bucket = buckets.setdefault(
                label,
                {
                    "market_state_label": label,
                    "market_state_model_version": model_version,
                    "market_state_source_version": _get(state, "source_feature_version") if state is not None else None,
                    "eligible_sample_count": 0,
                    "evaluated_sample_count": 0,
                    "unavailable_sample_count": 0,
                    "invalid_sample_count": 0,
                    "conflict_sample_count": 0,
                    "hit_trade_count": 0,
                    "warnings": [],
                    "returns": [],
                },
            )
            bucket["eligible_sample_count"] += 1
            bucket["evaluated_sample_count"] += 1
            return_pct = _get(sample, "return_pct")
            if _get(sample, "condition_result") is True and return_pct is not None:
                value = float(return_pct)
                bucket["returns"].append(value)
                bucket["hit_trade_count"] += 1
                all_return_values.append(value)

        per_market_metrics = [self._build_market_metric(bucket) for bucket in buckets.values()]
        overall_metrics = {
            "eligible_sample_count": sum(item["eligible_sample_count"] for item in per_market_metrics),
            "evaluated_sample_count": sum(item["evaluated_sample_count"] for item in per_market_metrics),
            "hit_trade_count": sum(item["hit_trade_count"] for item in per_market_metrics),
            "avg_return": statistics.mean(all_return_values) if all_return_values else None,
            "total_return": sum(all_return_values) if all_return_values else None,
        }
        status = "completed_valid"
        market_state_incomplete = (
            effective_level != "level_1"
            and set(decision_times) != set(states_by_date)
        )
        if not samples or market_state_incomplete or (effective_level != "level_1" and len(source_versions) > 1):
            status = "completed_invalid"
        if not samples:
            warnings.append("没有可执行的固定样本，结果仅记录覆盖状态。")
        identity = {
            "run_id": _id(_get(run, "run_id")),
            "request_fingerprint": _get(run, "request_fingerprint"),
            "dataset_fingerprint": _get(run, "dataset_fingerprint"),
            "market_snapshot_fingerprints": _get(run, "market_snapshot_fingerprints", []) or [],
            "market_state_model_version": model_version,
            "market_state_source_version": sorted(source_versions),
            "market_state_result_version": FORMAL_MARKET_STATE_RESULT_VERSION,
            "decision_time_policy": _get(run, "decision_time_policy"),
            "sample_state_counts": sample_state_counts,
            "per_market_state_metrics": per_market_metrics,
        }
        result_fingerprint = _fingerprint(identity)
        source_version_text = ",".join(sorted(source_versions)) or "unavailable"
        reproducibility_fingerprint = f"{model_version or 'market-state-unbound'}:{source_version_text}:{result_fingerprint}"
        audit = {
            "actor_id": actor_id,
            "actor_role": actor_role,
            "time": datetime.now(UTC).isoformat(),
            "source_surface": "/rules/backtests",
            "run_id": _id(_get(run, "run_id")),
            "before_state": _value(_get(run, "status")),
            "after_state": status,
        }
        return {
            "result_id": uuid4(),
            "run_id": _get(run, "run_id"),
            "input_fingerprint": str(_get(run, "request_fingerprint")),
            "result_fingerprint": result_fingerprint,
            "reproducibility_fingerprint": reproducibility_fingerprint,
            "status": status,
            "requested_level": str(_get(run, "requested_level")),
            "effective_level": effective_level,
            "market_state_model_version": model_version,
            "market_state_source_version": sorted(source_versions)[0] if len(source_versions) == 1 else None,
            "market_state_result_version": FORMAL_MARKET_STATE_RESULT_VERSION,
            "decision_time_policy": str(_get(run, "decision_time_policy")),
            "overall_metrics": overall_metrics,
            "per_market_state_metrics": per_market_metrics,
            "per_rule_metrics": [],
            "sample_state_counts": sample_state_counts,
            "coverage_json": coverage,
            "warnings": warnings,
            "limitations": limitations,
            "provenance_json": identity,
            "audit_json": audit,
        }

    def _build_market_metric(self, bucket: dict[str, Any]) -> dict[str, Any]:
        returns = list(bucket.pop("returns"))
        wins = [value for value in returns if value > 0]
        metric = {
            **bucket,
            "avg_return": statistics.mean(returns) if returns else None,
            "total_return": sum(returns) if returns else None,
            "win_rate": len(wins) / len(returns) if returns else None,
            "max_drawdown": self._max_drawdown(returns) if returns else None,
            "coverage": bucket["evaluated_sample_count"] / bucket["eligible_sample_count"] if bucket["eligible_sample_count"] else None,
        }
        metric["result_fingerprint"] = _fingerprint(metric)
        return metric

    @staticmethod
    def _max_drawdown(returns: list[float]) -> float | None:
        if not returns:
            return None
        equity = 1.0
        peak = 1.0
        max_drawdown = 0.0
        for value in returns:
            equity *= 1 + value
            peak = max(peak, equity)
            max_drawdown = min(max_drawdown, equity / peak - 1)
        return max_drawdown

    @staticmethod
    def _aware(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    @classmethod
    def _decision_times(cls, date_from: date, date_to: date) -> dict[date, datetime]:
        current = date_from
        result: dict[date, datetime] = {}
        while current <= date_to:
            result[current] = datetime(current.year, current.month, current.day, 9, 30, tzinfo=CN_TZ)
            current = date.fromordinal(current.toordinal() + 1)
        return result

    def _run_view(self, run: Any) -> BacktestRunView:
        if isinstance(run, dict):
            get = run.get
        else:
            get = lambda key, default=None: getattr(run, key, default)
        status = _value(get("status"))
        return BacktestRunView(
            run_id=str(get("run_id")),
            status=status,
            business_status="已创建" if status == "dependency_checked" else status,
            rule_version_id=_id(get("rule_version_id")),
            rule_family_id=_id(get("rule_family_id")),
            frozen_rule_version_ids=[str(item) for item in (get("frozen_rule_version_ids", []) or [])],
            dataset_snapshot_id=str(get("dataset_snapshot_id")),
            request_fingerprint=str(get("request_fingerprint")),
            reproducibility_fingerprint=str(get("reproducibility_fingerprint")),
            snapshot_only=bool(get("snapshot_only", True)),
            progress=get("progress_json", {}) or {},
            limitations=get("limitations", []) or [],
            next_actions=["查看运行进度", "查看数据覆盖和限制", "查看可复现证据"],
        )

    def _result_view(self, result: Any) -> BacktestResultView:
        return BacktestResultView(
            result_id=str(_get(result, "result_id")),
            run_id=str(_get(result, "run_id")),
            status=str(_get(result, "status")),
            requested_level=str(_get(result, "requested_level")),
            effective_level=str(_get(result, "effective_level")),
            market_state_model_version=_get(result, "market_state_model_version"),
            market_state_source_version=_get(result, "market_state_source_version"),
            market_state_result_version=str(_get(result, "market_state_result_version")),
            overall_metrics=_get(result, "overall_metrics", {}) or {},
            per_market_state_metrics=[
                MarketStateMetricView.model_validate(item)
                for item in (_get(result, "per_market_state_metrics", []) or [])
            ],
            sample_state_counts={key: int(value) for key, value in (_get(result, "sample_state_counts", {}) or {}).items()},
            coverage=_get(result, "coverage_json", _get(result, "coverage", {})) or {},
            warnings=_get(result, "warnings", []) or [],
            limitations=_get(result, "limitations", []) or [],
            result_fingerprint=str(_get(result, "result_fingerprint")),
            reproducibility_fingerprint=str(_get(result, "reproducibility_fingerprint")),
        )
