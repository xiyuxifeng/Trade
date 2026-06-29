from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Any, Callable, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.db.repositories.pre_market_readiness_repo import PreMarketReadinessRepository
from src.db.session import get_session_factory
from src.domain.enums import FormalLifecycleState, QualityStatus
from src.models.stage2_canonical import DatasetLifecycleState
from src.services.data_time_semantics import PRE_MARKET_DECISION_SLOT, slot_cutoff_at


PRE_MARKET_SLOT = PRE_MARKET_DECISION_SLOT
READY_QUALITY_STATES = {"ready", "ok", "verified", "complete", QualityStatus.verified.value, QualityStatus.complete.value}
DEGRADED_QUALITY_STATES = {"partial", "ambiguous", "unresolved", "insufficient_sample", "insufficient_coverage"}


class PreMarketRepairAction(BaseModel):
    label: str
    to: str


class PreMarketCheckView(BaseModel):
    code: str
    label: str
    status: Literal["ready", "degraded", "blocked"]
    happened: str
    affected: str
    repair_guidance: str
    can_proceed_in_degraded_mode: bool
    traceability: dict[str, Any] = Field(default_factory=dict)


class PreMarketTraceabilityView(BaseModel):
    trade_date: str
    strategy_version_id: str | None = None
    dataset_snapshot_id: str | None = None
    market_snapshot_id: str | None = None
    market_state_id: str | None = None
    rule_applicability_profile_ids: list[str] = Field(default_factory=list)
    author_method_profile_version_id: str | None = None
    author_rule_profile_version_id: str | None = None
    author_validated_profile_version_id: str | None = None
    data_quality_state: str = "unknown"


class PreMarketReadinessView(BaseModel):
    state: Literal["ready", "partial", "unavailable", "empty"]
    readiness_status: Literal["ready", "degraded", "blocked"]
    trade_date: str
    slot: str
    summary_title: str
    happened: str
    affected: str
    repair_guidance: str
    can_proceed: bool
    can_proceed_in_degraded_mode: bool
    checks: list[PreMarketCheckView]
    traceability: PreMarketTraceabilityView
    repair_actions: list[PreMarketRepairAction] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PreMarketReadinessService:
    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any] | None = None,
        repository: PreMarketReadinessRepository | None = None,
    ) -> None:
        self._session_scope_factory = session_scope_factory or self._default_session_scope_factory
        self.repository = repository or PreMarketReadinessRepository()

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

    async def get_readiness(
        self,
        trade_date: str | date,
        *,
        actor_id: str,
        actor_role: str,
    ) -> PreMarketReadinessView:
        if actor_role not in {"viewer", "operator", "admin"}:
            raise PermissionError("viewer permission is required to view daily pre-market readiness")

        normalized_trade_date = trade_date if isinstance(trade_date, date) else date.fromisoformat(str(trade_date))
        decision_cutoff_at = slot_cutoff_at(normalized_trade_date, PRE_MARKET_SLOT)
        traceability = PreMarketTraceabilityView(trade_date=normalized_trade_date.isoformat())
        checks: list[PreMarketCheckView] = []
        warnings: list[str] = []

        async with self._session_scope_factory() as session:
            current_strategies = await self.repository.list_current_strategies(session)
            strategy_check, strategy_version = await self._build_strategy_check(session, current_strategies, traceability)
            checks.append(strategy_check)

            dataset_snapshot = await self.repository.get_latest_dataset_snapshot(
                session,
                trade_date=normalized_trade_date,
                available_at_before=decision_cutoff_at,
            )
            latest_dataset_snapshot = dataset_snapshot or await self.repository.get_latest_dataset_snapshot(
                session,
                trade_date=normalized_trade_date,
            )
            ohlcv_check = self._build_ohlcv_check(
                dataset_snapshot,
                latest_dataset_snapshot=latest_dataset_snapshot,
                trade_date=normalized_trade_date,
                decision_cutoff_at=decision_cutoff_at,
                traceability=traceability,
            )
            checks.append(ohlcv_check)

            market_snapshot = await self.repository.get_market_snapshot_for_trade_date_and_slot(
                session,
                trade_date=normalized_trade_date,
                slot=PRE_MARKET_SLOT,
                available_at_before=decision_cutoff_at,
            )
            latest_market_snapshot = market_snapshot or await self.repository.get_market_snapshot_for_trade_date_and_slot(
                session,
                trade_date=normalized_trade_date,
                slot=PRE_MARKET_SLOT,
            )
            kaipan_check = self._build_kaipan_check(
                market_snapshot,
                latest_market_snapshot=latest_market_snapshot,
                decision_cutoff_at=decision_cutoff_at,
                traceability=traceability,
            )
            checks.append(kaipan_check)

            market_state = None
            if market_snapshot is not None:
                market_state = await self.repository.get_market_state_for_snapshot(
                    session,
                    market_snapshot_id=market_snapshot.id,
                    available_at_before=decision_cutoff_at,
                )
            latest_market_state = None
            if market_snapshot is not None and market_state is None:
                latest_market_state = await self.repository.get_market_state_for_snapshot(
                    session,
                    market_snapshot_id=market_snapshot.id,
                )
            market_state_check = self._build_market_state_check(
                market_state,
                latest_market_state=latest_market_state,
                decision_cutoff_at=decision_cutoff_at,
                traceability=traceability,
            )
            checks.append(market_state_check)

            author_profiles: dict[UUID, Any] = {}
            memberships: list[Any] = []
            if strategy_version is not None:
                memberships = await self.repository.list_strategy_rule_memberships(
                    session,
                    strategy_version_id=strategy_version.strategy_version_id,
                )
                author_profile_ids = [
                    strategy_version.author_method_profile_version_id,
                    strategy_version.author_rule_profile_version_id,
                    strategy_version.author_validated_profile_version_id,
                ]
                author_profiles = {
                    item.author_profile_version_id: item
                    for item in await self.repository.list_author_profile_versions(
                        session,
                        author_profile_version_ids=[item for item in author_profile_ids if item is not None],
                    )
                }
            author_check = self._build_author_profile_check(strategy_version, author_profiles, traceability)
            checks.append(author_check)

            applicability_profiles = []
            if memberships and dataset_snapshot is not None:
                applicability_profiles = await self.repository.list_published_rule_applicability_profiles(
                    session,
                    rule_version_ids=[item.rule_version_id for item in memberships],
                    dataset_snapshot_id=dataset_snapshot.dataset_snapshot_id,
                )
            rule_applicability_check = self._build_rule_applicability_check(
                memberships=memberships,
                market_snapshot=market_snapshot,
                applicability_profiles=applicability_profiles,
                traceability=traceability,
            )
            checks.append(rule_applicability_check)

        data_quality_check = self._build_data_quality_check(
            strategy_check=strategy_check,
            ohlcv_check=ohlcv_check,
            kaipan_check=kaipan_check,
            market_state_check=market_state_check,
            author_check=author_check,
            rule_applicability_check=rule_applicability_check,
            traceability=traceability,
        )
        checks.append(data_quality_check)

        overall_status = self._overall_status(checks)
        traceability.data_quality_state = overall_status
        if overall_status == "ready":
            state = "ready"
            summary_title = "已就绪"
            happened = "正式盘前所需的 canonical 输入已经齐备。"
            affected = "可以继续后续正式盘前流程。"
            repair_guidance = "当前无需修复，继续下一步即可。"
            can_proceed = True
            can_proceed_in_degraded_mode = False
        elif overall_status == "degraded":
            state = "partial"
            summary_title = "可降级继续"
            happened = self._first_message(checks, "degraded", "happened", "存在部分正式输入缺口。")
            affected = self._first_message(checks, "degraded", "affected", "后续流程会缺少一部分正式证据。")
            repair_guidance = self._first_message(checks, "degraded", "repair_guidance", "先补齐缺失输入，或按降级模式继续。")
            can_proceed = True
            can_proceed_in_degraded_mode = True
        else:
            state = "unavailable"
            summary_title = "已阻塞"
            happened = self._first_message(checks, "blocked", "happened", "正式盘前输入不足，当前无法继续。")
            affected = self._first_message(checks, "blocked", "affected", "今日正式盘前流程不能继续。")
            repair_guidance = self._first_message(checks, "blocked", "repair_guidance", "先补齐阻塞项后再继续。")
            can_proceed = False
            can_proceed_in_degraded_mode = False

        repair_actions = self._collect_repair_actions(checks)
        if actor_id:
            warnings.append(f"checked_by:{actor_id}")

        return PreMarketReadinessView(
            state=state,
            readiness_status=overall_status,
            trade_date=normalized_trade_date.isoformat(),
            slot=PRE_MARKET_SLOT,
            summary_title=summary_title,
            happened=happened,
            affected=affected,
            repair_guidance=repair_guidance,
            can_proceed=can_proceed,
            can_proceed_in_degraded_mode=can_proceed_in_degraded_mode,
            checks=checks,
            traceability=traceability,
            repair_actions=repair_actions,
            warnings=warnings,
        )

    async def _build_strategy_check(
        self,
        session: Any,
        current_strategies: list[Any],
        traceability: PreMarketTraceabilityView,
    ) -> tuple[PreMarketCheckView, Any | None]:
        if not current_strategies:
            return (
                PreMarketCheckView(
                    code="current_formal_strategy",
                    label="当前正式策略",
                    status="blocked",
                    happened="当前没有已发布的正式策略。",
                    affected="系统无法确认今天应该使用哪一版正式策略。",
                    repair_guidance="先到策略中心发布当前正式策略。",
                    can_proceed_in_degraded_mode=False,
                    traceability={"current_strategy_count": 0},
                ),
                None,
            )
        if len(current_strategies) > 1:
            return (
                PreMarketCheckView(
                    code="current_formal_strategy",
                    label="当前正式策略",
                    status="blocked",
                    happened="检测到多个当前正式策略。",
                    affected="系统无法确定今日盘前应该绑定哪一个正式策略版本。",
                    repair_guidance="先到策略中心清理重复的当前正式策略。",
                    can_proceed_in_degraded_mode=False,
                    traceability={"current_strategy_ids": [str(item.strategy_id) for item in current_strategies]},
                ),
                None,
            )

        strategy = current_strategies[0]
        if strategy.current_published_version_id is None:
            return (
                PreMarketCheckView(
                    code="current_formal_strategy",
                    label="当前正式策略",
                    status="blocked",
                    happened="当前正式策略没有绑定已发布版本。",
                    affected="系统无法读取今天的正式规则池。",
                    repair_guidance="先到策略中心发布正式版本。",
                    can_proceed_in_degraded_mode=False,
                    traceability={"strategy_id": str(strategy.strategy_id)},
                ),
                None,
            )

        strategy_version = await self.repository.get_strategy_version(session, strategy.current_published_version_id)
        if strategy_version is None:
            return (
                PreMarketCheckView(
                    code="current_formal_strategy",
                    label="当前正式策略",
                    status="blocked",
                    happened="当前正式策略版本不存在。",
                    affected="系统无法读取今天的正式规则池。",
                    repair_guidance="先检查正式策略版本绑定是否完整。",
                    can_proceed_in_degraded_mode=False,
                    traceability={"strategy_id": str(strategy.strategy_id), "strategy_version_id": str(strategy.current_published_version_id)},
                ),
                None,
            )

        traceability.strategy_version_id = str(strategy_version.strategy_version_id)
        traceability.author_method_profile_version_id = (
            str(strategy_version.author_method_profile_version_id) if strategy_version.author_method_profile_version_id else None
        )
        traceability.author_rule_profile_version_id = (
            str(strategy_version.author_rule_profile_version_id) if strategy_version.author_rule_profile_version_id else None
        )
        traceability.author_validated_profile_version_id = (
            str(strategy_version.author_validated_profile_version_id) if strategy_version.author_validated_profile_version_id else None
        )

        validation_state = (
            (strategy_version.evidence_json or {}).get("validation_summary") or {}
        ).get("state")
        if strategy_version.lifecycle_state != FormalLifecycleState.published or validation_state != "passed":
            return (
                PreMarketCheckView(
                    code="current_formal_strategy",
                    label="当前正式策略",
                    status="blocked",
                    happened="当前正式策略还没有通过正式验证或未处于已发布状态。",
                    affected="系统不会把未验证的策略当作今天的正式盘前输入。",
                    repair_guidance="先完成正式策略验证并确认当前版本已发布。",
                    can_proceed_in_degraded_mode=False,
                    traceability={
                        "strategy_id": str(strategy.strategy_id),
                        "strategy_version_id": str(strategy_version.strategy_version_id),
                        "validation_state": validation_state,
                        "lifecycle_state": strategy_version.lifecycle_state.value,
                    },
                ),
                None,
            )

        return (
            PreMarketCheckView(
                code="current_formal_strategy",
                label="当前正式策略",
                status="ready",
                happened="当前正式策略已发布，且验证状态通过。",
                affected="今天会按这版正式策略读取规则池和画像绑定。",
                repair_guidance="当前无需修复。",
                can_proceed_in_degraded_mode=False,
                traceability={
                    "strategy_id": str(strategy.strategy_id),
                    "strategy_version_id": str(strategy_version.strategy_version_id),
                    "validation_state": validation_state,
                },
            ),
            strategy_version,
        )

    def _build_ohlcv_check(
        self,
        dataset_snapshot: Any,
        *,
        latest_dataset_snapshot: Any,
        trade_date: date,
        decision_cutoff_at: datetime | None,
        traceability: PreMarketTraceabilityView,
    ) -> PreMarketCheckView:
        if dataset_snapshot is None and latest_dataset_snapshot is None:
            return PreMarketCheckView(
                code="latest_ohlcv",
                label="最新 OHLCV",
                status="blocked",
                happened="未找到今天之前可用的正式历史行情快照。",
                affected="系统无法确认今天能使用的最新历史行情范围。",
                repair_guidance="先到数据管理补齐 OHLCV 历史行情。",
                can_proceed_in_degraded_mode=False,
                traceability={
                    "trade_date": trade_date.isoformat(),
                    "decision_cutoff_at": decision_cutoff_at.isoformat() if decision_cutoff_at else None,
                },
            )

        if dataset_snapshot is None and latest_dataset_snapshot is not None:
            return PreMarketCheckView(
                code="latest_ohlcv",
                label="最新 OHLCV",
                status="blocked",
                happened="已找到较新的历史行情快照，但它在正式盘前决策时点之前并不可用。",
                affected="系统不能把盘前之后才补齐的数据当作今天盘前可用输入。",
                repair_guidance="请先冻结在盘前决策时点前可用的正式历史行情快照，或改期重试。",
                can_proceed_in_degraded_mode=False,
                traceability={
                    "dataset_snapshot_id": str(latest_dataset_snapshot.dataset_snapshot_id),
                    "dataset_trade_date": latest_dataset_snapshot.trade_date.isoformat() if latest_dataset_snapshot.trade_date else None,
                    "available_at": latest_dataset_snapshot.available_at.isoformat() if latest_dataset_snapshot.available_at else None,
                    "decision_cutoff_at": decision_cutoff_at.isoformat() if decision_cutoff_at else None,
                    "source": (latest_dataset_snapshot.storage_ref or {}).get("source") or latest_dataset_snapshot.dataset_type,
                    "slot": (latest_dataset_snapshot.storage_ref or {}).get("slot"),
                    "effective_at": latest_dataset_snapshot.frozen_at.isoformat() if latest_dataset_snapshot.frozen_at else None,
                },
            )

        traceability.dataset_snapshot_id = str(dataset_snapshot.dataset_snapshot_id)
        if dataset_snapshot.lifecycle_state != DatasetLifecycleState.ready:
            return PreMarketCheckView(
                code="latest_ohlcv",
                label="最新 OHLCV",
                status="blocked",
                happened="找到了历史行情快照，但状态不是可用。",
                affected="今天不能把这份历史行情当作正式盘前输入。",
                repair_guidance="先补齐或重建最新历史行情快照。",
                can_proceed_in_degraded_mode=False,
                traceability={
                    "dataset_snapshot_id": str(dataset_snapshot.dataset_snapshot_id),
                    "dataset_trade_date": dataset_snapshot.trade_date.isoformat() if dataset_snapshot.trade_date else None,
                    "lifecycle_state": dataset_snapshot.lifecycle_state.value,
                    "available_at": dataset_snapshot.available_at.isoformat() if dataset_snapshot.available_at else None,
                    "decision_cutoff_at": decision_cutoff_at.isoformat() if decision_cutoff_at else None,
                },
            )

        return PreMarketCheckView(
            code="latest_ohlcv",
            label="最新 OHLCV",
            status="ready",
            happened=f"已找到最新正式历史行情快照，覆盖到 {dataset_snapshot.trade_date.isoformat() if dataset_snapshot.trade_date else '未知日期'}。",
            affected="今天的盘前检查会绑定这份正式历史行情快照。",
            repair_guidance="当前无需修复。",
            can_proceed_in_degraded_mode=False,
            traceability={
                "dataset_snapshot_id": str(dataset_snapshot.dataset_snapshot_id),
                "dataset_trade_date": dataset_snapshot.trade_date.isoformat() if dataset_snapshot.trade_date else None,
                "content_fingerprint": dataset_snapshot.content_fingerprint,
                "available_at": dataset_snapshot.available_at.isoformat() if dataset_snapshot.available_at else None,
                "decision_cutoff_at": decision_cutoff_at.isoformat() if decision_cutoff_at else None,
                "source": (dataset_snapshot.storage_ref or {}).get("source") or dataset_snapshot.dataset_type,
                "slot": (dataset_snapshot.storage_ref or {}).get("slot"),
                "effective_at": dataset_snapshot.frozen_at.isoformat() if dataset_snapshot.frozen_at else None,
            },
        )

    def _build_kaipan_check(
        self,
        market_snapshot: Any,
        *,
        latest_market_snapshot: Any,
        decision_cutoff_at: datetime | None,
        traceability: PreMarketTraceabilityView,
    ) -> PreMarketCheckView:
        if market_snapshot is None and latest_market_snapshot is None:
            return PreMarketCheckView(
                code="kaipan_pre_market",
                label="Kaipan 盘前数据",
                status="blocked",
                happened="今日盘前市场快照缺失。",
                affected="系统无法确认盘前 Kaipan 数据，也不能继续正式盘前流程。",
                repair_guidance="先到数据管理补齐今日盘前市场数据。",
                can_proceed_in_degraded_mode=False,
                traceability={
                    "slot": PRE_MARKET_SLOT,
                    "market_snapshot_id": None,
                    "decision_cutoff_at": decision_cutoff_at.isoformat() if decision_cutoff_at else None,
                },
            )

        if market_snapshot is None and latest_market_snapshot is not None:
            return PreMarketCheckView(
                code="kaipan_pre_market",
                label="Kaipan 盘前数据",
                status="blocked",
                happened="今日盘前市场快照存在，但在正式盘前决策时点之前并不可用。",
                affected="系统不能把盘前之后才补齐的市场快照误当作正式盘前输入。",
                repair_guidance="请先补齐在 09-25 决策时点前可用的盘前市场快照。",
                can_proceed_in_degraded_mode=False,
                traceability={
                    "market_snapshot_id": str(latest_market_snapshot.id),
                    "snapshot_id": latest_market_snapshot.snapshot_id,
                    "slot": latest_market_snapshot.slot,
                    "available_at": latest_market_snapshot.available_at.isoformat() if latest_market_snapshot.available_at else None,
                    "captured_at": latest_market_snapshot.captured_at.isoformat() if latest_market_snapshot.captured_at else None,
                    "effective_at": latest_market_snapshot.effective_at.isoformat() if latest_market_snapshot.effective_at else None,
                    "decision_cutoff_at": decision_cutoff_at.isoformat() if decision_cutoff_at else None,
                    "source": list(latest_market_snapshot.provider_sources or []),
                },
            )

        if market_snapshot.slot != PRE_MARKET_SLOT:
            return PreMarketCheckView(
                code="kaipan_pre_market",
                label="Kaipan 盘前数据",
                status="blocked",
                happened="找到了市场快照，但不是盘前时段。",
                affected="系统不能把盘后快照误当作正式盘前输入。",
                repair_guidance="先补齐今天 09-25 的盘前市场快照。",
                can_proceed_in_degraded_mode=False,
                traceability={"market_snapshot_id": str(market_snapshot.id), "slot": market_snapshot.slot},
            )

        traceability.market_snapshot_id = str(market_snapshot.id)
        status = "ready" if self._is_ready_quality(market_snapshot.quality_status) else "degraded"
        happened = "今日盘前市场快照已就绪。" if status == "ready" else "今日盘前市场快照已生成，但质量状态不是完全可用。"
        affected = "系统会绑定这份盘前 Kaipan 快照。" if status == "ready" else "今天可以继续检查，但盘前市场信息存在缺口。"
        repair_guidance = "当前无需修复。" if status == "ready" else "先到数据管理补齐盘前市场快照缺口，或按降级模式继续。"
        return PreMarketCheckView(
            code="kaipan_pre_market",
            label="Kaipan 盘前数据",
            status=status,
            happened=happened,
            affected=affected,
            repair_guidance=repair_guidance,
            can_proceed_in_degraded_mode=status == "degraded",
            traceability={
                "market_snapshot_id": str(market_snapshot.id),
                "snapshot_id": market_snapshot.snapshot_id,
                "slot": market_snapshot.slot,
                "quality_status": market_snapshot.quality_status,
                "available_at": market_snapshot.available_at.isoformat() if market_snapshot.available_at else None,
                "captured_at": market_snapshot.captured_at.isoformat() if market_snapshot.captured_at else None,
                "effective_at": market_snapshot.effective_at.isoformat() if market_snapshot.effective_at else None,
                "decision_cutoff_at": decision_cutoff_at.isoformat() if decision_cutoff_at else None,
                "source": list(market_snapshot.provider_sources or []),
            },
        )

    def _build_market_state_check(
        self,
        market_state: Any,
        *,
        latest_market_state: Any,
        decision_cutoff_at: datetime | None,
        traceability: PreMarketTraceabilityView,
    ) -> PreMarketCheckView:
        if market_state is None and latest_market_state is None:
            return PreMarketCheckView(
                code="current_market_state",
                label="当前市场状态",
                status="blocked",
                happened="今日盘前市场状态缺失。",
                affected="系统无法确认今天应该按哪一种市场状态解释正式规则。",
                repair_guidance="先补齐盘前市场快照，并重新生成今天的市场状态。",
                can_proceed_in_degraded_mode=False,
                traceability={"market_state_id": None, "decision_cutoff_at": decision_cutoff_at.isoformat() if decision_cutoff_at else None},
            )

        if market_state is None and latest_market_state is not None:
            return PreMarketCheckView(
                code="current_market_state",
                label="当前市场状态",
                status="blocked",
                happened="今日盘前市场状态已生成，但在正式盘前决策时点之前并不可用。",
                affected="系统不能把盘前之后才补齐的市场状态当作今天的正式规则解释输入。",
                repair_guidance="请先补齐在盘前决策时点前可用的市场状态后再继续。",
                can_proceed_in_degraded_mode=False,
                traceability={
                    "market_state_id": str(latest_market_state.market_state_id),
                    "regime_id": latest_market_state.regime_id,
                    "regime_version": latest_market_state.regime_version,
                    "available_at": latest_market_state.available_at.isoformat() if latest_market_state.available_at else None,
                    "decision_cutoff_at": decision_cutoff_at.isoformat() if decision_cutoff_at else None,
                },
            )

        traceability.market_state_id = str(market_state.market_state_id)
        status = "ready" if self._is_ready_quality(market_state.quality_status) else "degraded"
        happened = "今日盘前市场状态已就绪。" if status == "ready" else "今日盘前市场状态已生成，但质量状态不是完全可用。"
        affected = "今天会按这份市场状态绑定正式规则适用性。" if status == "ready" else "后续规则解释会带着市场状态降级标记。"
        repair_guidance = "当前无需修复。" if status == "ready" else "先补齐市场状态输入，或按降级模式继续。"
        return PreMarketCheckView(
            code="current_market_state",
            label="当前市场状态",
            status=status,
            happened=happened,
            affected=affected,
            repair_guidance=repair_guidance,
            can_proceed_in_degraded_mode=status == "degraded",
            traceability={
                "market_state_id": str(market_state.market_state_id),
                "regime_id": market_state.regime_id,
                "regime_version": market_state.regime_version,
                "quality_status": market_state.quality_status,
                "available_at": market_state.available_at.isoformat() if market_state.available_at else None,
                "decision_cutoff_at": decision_cutoff_at.isoformat() if decision_cutoff_at else None,
            },
        )

    def _build_author_profile_check(
        self,
        strategy_version: Any,
        author_profiles: dict[UUID, Any],
        traceability: PreMarketTraceabilityView,
    ) -> PreMarketCheckView:
        if strategy_version is None or strategy_version.author_validated_profile_version_id is None:
            return PreMarketCheckView(
                code="author_validated_profile",
                label="作者验证画像",
                status="blocked",
                happened="当前正式策略没有绑定作者验证画像。",
                affected="系统无法确认今天要参考哪一版正式作者验证画像。",
                repair_guidance="先到策略中心重新绑定并发布正式策略。",
                can_proceed_in_degraded_mode=False,
                traceability={"author_validated_profile_version_id": None},
            )

        profile = author_profiles.get(strategy_version.author_validated_profile_version_id)
        if profile is None or profile.lifecycle_state != FormalLifecycleState.published:
            return PreMarketCheckView(
                code="author_validated_profile",
                label="作者验证画像",
                status="blocked",
                happened="当前正式策略绑定的作者验证画像不存在，或还没有发布。",
                affected="今天无法读取正式作者验证画像。",
                repair_guidance="先发布并绑定正式作者验证画像。",
                can_proceed_in_degraded_mode=False,
                traceability={"author_validated_profile_version_id": str(strategy_version.author_validated_profile_version_id)},
            )

        status = "ready" if self._is_ready_quality(profile.quality_status) else "degraded"
        return PreMarketCheckView(
            code="author_validated_profile",
            label="作者验证画像",
            status=status,
            happened="当前正式策略绑定的作者验证画像已发布。" if status == "ready" else "作者验证画像已发布，但质量状态不是完全可用。",
            affected="今天会读取这版正式作者验证画像。" if status == "ready" else "今天会带着画像质量降级标记继续。",
            repair_guidance="当前无需修复。" if status == "ready" else "先补齐作者验证画像证据，或按降级模式继续。",
            can_proceed_in_degraded_mode=status == "degraded",
            traceability={
                "author_validated_profile_version_id": str(profile.author_profile_version_id),
                "quality_status": profile.quality_status.value if hasattr(profile.quality_status, "value") else str(profile.quality_status),
            },
        )

    def _build_rule_applicability_check(
        self,
        *,
        memberships: list[Any],
        market_snapshot: Any,
        applicability_profiles: list[Any],
        traceability: PreMarketTraceabilityView,
    ) -> PreMarketCheckView:
        if not memberships:
            return PreMarketCheckView(
                code="rule_applicability",
                label="规则适用性",
                status="blocked",
                happened="当前正式策略没有规则成员。",
                affected="系统无法检查今天的正式规则适用性。",
                repair_guidance="先到策略中心确认正式策略规则池。",
                can_proceed_in_degraded_mode=False,
                traceability={"applicability_profile_ids": []},
            )
        if market_snapshot is None:
            return PreMarketCheckView(
                code="rule_applicability",
                label="规则适用性",
                status="blocked",
                happened="盘前市场快照缺失，无法筛选正式规则适用性画像。",
                affected="今天无法确认规则适用性。",
                repair_guidance="先补齐盘前市场快照，再重新检查规则适用性。",
                can_proceed_in_degraded_mode=False,
                traceability={"applicability_profile_ids": []},
            )

        selected: list[Any] = []
        missing_rule_version_ids: list[str] = []
        for membership in memberships:
            matched = [
                profile
                for profile in applicability_profiles
                if profile.rule_version_id == membership.rule_version_id
                and self._profile_matches_market_snapshot(profile, market_snapshot)
            ]
            matched.sort(key=self._applicability_profile_sort_key)
            if matched:
                selected.append(matched[-1])
            else:
                missing_rule_version_ids.append(str(membership.rule_version_id))

        traceability.rule_applicability_profile_ids = [str(item.applicability_profile_id) for item in selected]
        if not selected:
            return PreMarketCheckView(
                code="rule_applicability",
                label="规则适用性",
                status="blocked",
                happened="今天没有可用的正式规则适用性画像。",
                affected="系统无法确认今天哪些正式规则可以启用。",
                repair_guidance="先到规则回测页面补齐适用性画像。",
                can_proceed_in_degraded_mode=False,
                traceability={
                    "applicability_profile_ids": [],
                    "missing_rule_version_ids": missing_rule_version_ids,
                },
            )

        has_degraded_profile = any(not self._is_ready_quality(item.quality_status) or item.result_status != "ready" for item in selected)
        if missing_rule_version_ids or has_degraded_profile:
            return PreMarketCheckView(
                code="rule_applicability",
                label="规则适用性",
                status="degraded",
                happened="正式规则适用性覆盖不完整。",
                affected="今日规则选择会缺少一部分正式适用性证据。",
                repair_guidance="先补齐规则适用性画像，或在降级模式下继续。",
                can_proceed_in_degraded_mode=True,
                traceability={
                    "applicability_profile_ids": [str(item.applicability_profile_id) for item in selected],
                    "missing_rule_version_ids": missing_rule_version_ids,
                },
            )

        return PreMarketCheckView(
            code="rule_applicability",
            label="规则适用性",
            status="ready",
            happened="正式规则适用性画像已覆盖当前正式策略规则池。",
            affected="今天可以按正式规则适用性继续后续流程。",
            repair_guidance="当前无需修复。",
            can_proceed_in_degraded_mode=False,
            traceability={"applicability_profile_ids": [str(item.applicability_profile_id) for item in selected]},
        )

    @staticmethod
    def _profile_matches_market_snapshot(profile: Any, market_snapshot: Any) -> bool:
        snapshot_ids = [str(item) for item in (profile.market_snapshot_ids or [])]
        if snapshot_ids:
            return str(market_snapshot.id) in snapshot_ids
        return str(getattr(profile, "effective_level", "") or "") == "level_1"

    def _build_data_quality_check(
        self,
        *,
        strategy_check: PreMarketCheckView,
        ohlcv_check: PreMarketCheckView,
        kaipan_check: PreMarketCheckView,
        market_state_check: PreMarketCheckView,
        author_check: PreMarketCheckView,
        rule_applicability_check: PreMarketCheckView,
        traceability: PreMarketTraceabilityView,
    ) -> PreMarketCheckView:
        upstream_checks = [
            strategy_check,
            ohlcv_check,
            kaipan_check,
            market_state_check,
            author_check,
            rule_applicability_check,
        ]
        if any(item.status == "blocked" for item in upstream_checks):
            return PreMarketCheckView(
                code="data_quality",
                label="数据质量",
                status="blocked",
                happened="至少一个正式输入仍处于阻塞状态。",
                affected="今天的正式盘前流程不能把这些输入当作可用数据。",
                repair_guidance="先修复阻塞项，再重新检查数据质量。",
                can_proceed_in_degraded_mode=False,
                traceability={"data_quality_state": "blocked"},
            )
        if any(item.status == "degraded" for item in upstream_checks):
            return PreMarketCheckView(
                code="data_quality",
                label="数据质量",
                status="degraded",
                happened="正式输入可读，但其中至少一项带有降级标记。",
                affected="后续流程会携带数据质量降级标记继续。",
                repair_guidance="先补齐降级输入，或按降级模式继续。",
                can_proceed_in_degraded_mode=True,
                traceability={"data_quality_state": "degraded"},
            )
        return PreMarketCheckView(
            code="data_quality",
            label="数据质量",
            status="ready",
            happened="当前正式输入都处于可用状态。",
            affected="今天可以按正式质量状态继续后续流程。",
            repair_guidance="当前无需修复。",
            can_proceed_in_degraded_mode=False,
            traceability={"data_quality_state": "ready"},
        )

    def _overall_status(self, checks: list[PreMarketCheckView]) -> Literal["ready", "degraded", "blocked"]:
        if any(item.status == "blocked" for item in checks):
            return "blocked"
        if any(item.status == "degraded" for item in checks):
            return "degraded"
        return "ready"

    def _first_message(self, checks: list[PreMarketCheckView], status: str, field: str, fallback: str) -> str:
        for item in checks:
            if item.status == status:
                return getattr(item, field)
        return fallback

    def _collect_repair_actions(self, checks: list[PreMarketCheckView]) -> list[PreMarketRepairAction]:
        actions: list[PreMarketRepairAction] = []
        seen: set[str] = set()
        for item in checks:
            if item.code in {"kaipan_pre_market", "latest_ohlcv", "current_market_state", "data_quality"}:
                path = "/system/data"
                label = "补齐缺失数据" if item.status != "ready" else ""
            elif item.code == "rule_applicability":
                path = "/rules/backtests"
                label = "补齐规则适用性"
            else:
                path = "/strategies"
                label = "查看正式策略"
            if not label or path in seen:
                continue
            seen.add(path)
            actions.append(PreMarketRepairAction(label=label, to=path))
        return actions

    def _is_ready_quality(self, value: Any) -> bool:
        normalized = value.value if hasattr(value, "value") else str(value)
        return normalized in READY_QUALITY_STATES

    @staticmethod
    def _applicability_profile_sort_key(item: Any) -> tuple[datetime, datetime, str]:
        return (
            item.reviewed_at or datetime.min,
            item.created_at or datetime.min,
            str(item.applicability_profile_id),
        )
