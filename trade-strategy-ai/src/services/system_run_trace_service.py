from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import select

from src.db.session import get_session_factory
from src.models.market_data_snapshot import MarketSnapshot
from src.models.job import Job
from src.models.stage2_canonical import (
    BacktestResult,
    BacktestRun,
    DailyRuleSelection,
    PostMarketReview,
    PromptRun,
    TradingDayPlan,
    DatasetSnapshot,
)
from src.services.base import BaseService, ServiceResult


def build_stable_business_run_id(*, object_type: str, object_id: str, stored_run_id: str | None = None) -> str:
    normalized = (stored_run_id or "").strip()
    if normalized:
        return normalized
    return f"{object_type}:{object_id}"


class SystemRunTraceService(BaseService):
    service_name = "system-run-trace"

    def __init__(self, *, session_scope_factory: Callable[[], Any] | None = None) -> None:
        self._session_scope_factory = session_scope_factory or self._default_session_scope_factory

    @staticmethod
    @asynccontextmanager
    async def _default_session_scope_factory():
        session_factory = get_session_factory()
        async with session_factory() as session:
            yield session

    async def list_run_traces(self, *, actor_role: str, limit: int = 20) -> ServiceResult:
        async with self._session_scope_factory() as session:
            prompt_runs = list(
                (
                    await session.execute(
                        select(PromptRun).order_by(PromptRun.created_at.desc()).limit(limit)
                    )
                )
                .scalars()
                .all()
            )
            backtest_runs = list(
                (
                    await session.execute(
                        select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(limit)
                    )
                )
                .scalars()
                .all()
            )
            daily_rule_selections = list(
                (
                    await session.execute(
                        select(DailyRuleSelection).order_by(DailyRuleSelection.created_at.desc()).limit(limit)
                    )
                )
                .scalars()
                .all()
            )
            trading_day_plans = list(
                (
                    await session.execute(
                        select(TradingDayPlan).order_by(TradingDayPlan.created_at.desc()).limit(limit)
                    )
                )
                .scalars()
                .all()
            )
            post_market_reviews = list(
                (
                    await session.execute(
                        select(PostMarketReview).order_by(PostMarketReview.created_at.desc()).limit(limit)
                    )
                )
                .scalars()
                .all()
            )
            system_jobs = list(
                (
                    await session.execute(
                        select(Job)
                        .where(Job.job_type.in_(["system-data-operation", "stage3-article-batch"]))
                        .order_by(Job.created_at.desc())
                        .limit(limit)
                    )
                )
                .scalars()
                .all()
            )

            dataset_ids: set[UUID] = set()
            market_ids: set[UUID] = set()
            backtest_ids = [run.run_id for run in backtest_runs]
            prompt_ids = [run.prompt_run_id for run in prompt_runs]
            for selection in daily_rule_selections:
                context = self._extract_selection_context(selection)
                dataset_id = self._parse_uuid(context.get("dataset_snapshot_id"))
                market_id = self._parse_uuid(context.get("market_snapshot_id"))
                if dataset_id is not None:
                    dataset_ids.add(dataset_id)
                if market_id is not None:
                    market_ids.add(market_id)
            for plan in trading_day_plans:
                traceability = self._extract_plan_traceability(plan)
                dataset_id = self._parse_uuid(traceability.get("dataset_snapshot_id"))
                market_id = self._parse_uuid(traceability.get("market_snapshot_id"))
                if dataset_id is not None:
                    dataset_ids.add(dataset_id)
                if market_id is not None:
                    market_ids.add(market_id)
            for run in backtest_runs:
                dataset_ids.add(run.dataset_snapshot_id)
                for raw_market_id in run.market_snapshot_ids or []:
                    market_id = self._parse_uuid(raw_market_id)
                    if market_id is not None:
                        market_ids.add(market_id)
            for review in post_market_reviews:
                if review.market_snapshot_id is not None:
                    market_ids.add(review.market_snapshot_id)

            datasets = await self._load_datasets(session, dataset_ids)
            markets = await self._load_market_snapshots(session, market_ids)
            backtest_results = await self._load_backtest_results(session, backtest_ids)
            prompt_by_id = {str(run.prompt_run_id): run for run in prompt_runs}

        traces: list[dict[str, Any]] = []
        traces.extend(self._build_prompt_trace(run, actor_role=actor_role) for run in prompt_runs)
        traces.extend(
            self._build_backtest_trace(
                run,
                actor_role=actor_role,
                dataset=datasets.get(str(run.dataset_snapshot_id)),
                market_snapshots=[markets[item] for item in run.market_snapshot_ids if item in markets],
                result=backtest_results.get(str(run.run_id)),
            )
            for run in backtest_runs
        )
        traces.extend(
            self._build_daily_rule_selection_trace(
                selection,
                actor_role=actor_role,
                dataset=datasets.get(self._extract_selection_context(selection).get("dataset_snapshot_id")),
                market_snapshot=markets.get(self._extract_selection_context(selection).get("market_snapshot_id")),
            )
            for selection in daily_rule_selections
        )
        traces.extend(
            self._build_trading_plan_trace(
                plan,
                actor_role=actor_role,
                dataset=datasets.get(self._extract_plan_traceability(plan).get("dataset_snapshot_id")),
                market_snapshot=markets.get(self._extract_plan_traceability(plan).get("market_snapshot_id")),
            )
            for plan in trading_day_plans
        )
        traces.extend(
            self._build_post_market_review_trace(
                review,
                actor_role=actor_role,
                market_snapshot=markets.get(str(review.market_snapshot_id)) if review.market_snapshot_id is not None else None,
                prompt_run=prompt_by_id.get(str(review.prompt_run_id)) if review.prompt_run_id is not None else None,
            )
            for review in post_market_reviews
        )
        traces.extend(
            self._build_system_job_trace(job, actor_role=actor_role)
            for job in system_jobs
        )
        traces.sort(key=lambda item: item.get("started_at") or item.get("finished_at") or "", reverse=True)
        return ServiceResult(
            status="ok",
            message="system run traces listed",
            payload={"count": min(len(traces), limit), "items": traces[:limit]},
        )

    async def _load_datasets(self, session: Any, dataset_ids: set[UUID]) -> dict[str, DatasetSnapshot]:
        if not dataset_ids:
            return {}
        items = list((await session.execute(select(DatasetSnapshot).where(DatasetSnapshot.dataset_snapshot_id.in_(dataset_ids)))).scalars().all())
        return {str(item.dataset_snapshot_id): item for item in items}

    async def _load_market_snapshots(self, session: Any, market_ids: set[UUID]) -> dict[str, MarketSnapshot]:
        if not market_ids:
            return {}
        items = list((await session.execute(select(MarketSnapshot).where(MarketSnapshot.id.in_(market_ids)))).scalars().all())
        return {str(item.id): item for item in items}

    async def _load_backtest_results(self, session: Any, run_ids: list[UUID]) -> dict[str, BacktestResult]:
        if not run_ids:
            return {}
        items = list((await session.execute(select(BacktestResult).where(BacktestResult.run_id.in_(run_ids)))).scalars().all())
        return {str(item.run_id): item for item in items}

    def _build_prompt_trace(self, run: PromptRun, *, actor_role: str) -> dict[str, Any]:
        run_id = build_stable_business_run_id(
            object_type="prompt",
            object_id=str(run.prompt_run_id),
            stored_run_id=run.run_id,
        )
        prompt_call = self._build_prompt_call_view(run)
        step = {
            "step_id": f"prompt-{run.prompt_name}",
            "business_label": self._prompt_business_label(run),
            "status": self._prompt_status(run.validation_state),
            "started_at": self._iso(run.started_at or run.created_at),
            "finished_at": self._iso(run.completed_at or run.updated_at),
            "duration_seconds": self._duration_seconds(run.started_at or run.created_at, run.completed_at or run.updated_at),
            "error": None if self._prompt_status(run.validation_state) == "ready" else "输出未通过正式校验。",
            "retry_count": run.retry_count,
            "input_references": [
                {
                    "type": run.input_object_type,
                    "id": run.input_object_id or run.input_version_id or "unavailable",
                    "label": run.input_object_type,
                }
            ],
            "output_references": [
                {
                    "type": "prompt_run",
                    "id": str(run.prompt_run_id),
                    "label": run.prompt_name,
                }
            ],
            "repair_guidance": self._prompt_repair_guidance(run.validation_state),
        }
        return self._assemble_trace(
            run_id=run_id,
            business_label=self._prompt_business_label(run),
            status=self._prompt_status(run.validation_state),
            started_at=run.started_at or run.created_at,
            finished_at=run.completed_at or run.updated_at,
            happened=f"{self._prompt_business_label(run)}已记录 Prompt 调用信息。",
            affected="普通用户可以理解当前业务结果是否可用；管理员可继续查看模型、版本和校验详情。",
            repair_guidance=self._prompt_repair_guidance(run.validation_state),
            next_action={"label": "查看研究中心", "target_path": "/research"},
            attempt=self._build_attempt_view(run_id=run_id, retry_count=run.retry_count, attempt_id=str(run.prompt_run_id)),
            steps=[step],
            prompt_calls=[prompt_call],
            data_fetches=[],
            backtests=[],
            linked_records=[{"type": "prompt_run", "id": str(run.prompt_run_id), "label": run.prompt_name}],
            admin_diagnostics={
                "technical_status": self._prompt_status(run.validation_state),
                "linked_ids": {"prompt_run_ids": [str(run.prompt_run_id)]},
                "payload_fingerprints": {"input_hash": run.input_hash},
                "raw_metadata": {"schema_name": run.schema_name},
            } if actor_role in {"operator", "admin"} else None,
        )

    def _build_backtest_trace(
        self,
        run: BacktestRun,
        *,
        actor_role: str,
        dataset: DatasetSnapshot | None,
        market_snapshots: list[MarketSnapshot],
        result: BacktestResult | None,
    ) -> dict[str, Any]:
        run_id = str(run.run_id)
        step = {
            "step_id": "formal-backtest",
            "business_label": "执行正式回测",
            "status": self._map_status(run.status),
            "started_at": self._iso(run.created_at),
            "finished_at": self._iso(result.updated_at if result is not None else run.updated_at),
            "duration_seconds": self._duration_seconds(run.created_at, result.updated_at if result is not None else run.updated_at),
            "error": None if self._map_status(run.status) == "ready" else run.downgrade_reason,
            "retry_count": 0,
            "input_references": self._backtest_input_refs(run),
            "output_references": [{"type": "backtest_run", "id": run_id, "label": "正式回测"}],
            "repair_guidance": "先检查数据覆盖、回测限制和降级原因，再决定是否重新执行。",
        }
        return self._assemble_trace(
            run_id=run_id,
            business_label="执行正式回测",
            status=self._map_status(run.status),
            started_at=run.created_at,
            finished_at=result.updated_at if result is not None else run.updated_at,
            happened="正式回测已记录数据版本、规则版本和复现实证。",
            affected="回测结果会影响规则验证、策略验证和后续正式判断。",
            repair_guidance="如果结果受限，请先补齐缺失数据或重新冻结数据快照后再执行。",
            next_action={"label": "查看规则与回测", "target_path": "/rules"},
            attempt=self._build_attempt_view(run_id=run_id, retry_count=0, attempt_id=run_id),
            steps=[step],
            prompt_calls=[],
            data_fetches=[self._build_dataset_fetch_view(dataset)] + [self._build_market_fetch_view(item) for item in market_snapshots],
            backtests=[self._build_backtest_view(run, result)],
            linked_records=[{"type": "backtest_run", "id": run_id, "label": "正式回测"}],
            admin_diagnostics={
                "technical_status": self._map_status(run.status),
                "linked_ids": {"backtest_run_ids": [run_id]},
                "payload_fingerprints": {
                    "request_fingerprint": run.request_fingerprint,
                    "reproducibility_fingerprint": run.reproducibility_fingerprint,
                },
                "raw_metadata": {"audit_json": run.audit_json},
            } if actor_role in {"operator", "admin"} else None,
        )

    def _build_daily_rule_selection_trace(
        self,
        selection: DailyRuleSelection,
        *,
        actor_role: str,
        dataset: DatasetSnapshot | None,
        market_snapshot: MarketSnapshot | None,
    ) -> dict[str, Any]:
        context = self._extract_selection_context(selection)
        run_id = build_stable_business_run_id(
            object_type="daily-rule-selection",
            object_id=str(selection.daily_rule_selection_id),
            stored_run_id=selection.source_run_id,
        )
        derived = not bool((selection.source_run_id or "").strip())
        status = "partial" if derived else "ready"
        return self._assemble_trace(
            run_id=run_id,
            business_label="生成每日规则选择",
            status=status,
            started_at=selection.created_at,
            finished_at=selection.updated_at,
            happened="每日规则选择已写入正式对象。",
            affected="今日启用、降权和暂停规则已经固定，可继续盘前流程。",
            repair_guidance="如果需要更稳定的运行链路，请重新生成本次规则选择，系统会写入正式运行标识。",
            next_action={"label": "查看今日盘前", "target_path": "/daily/pre-market"},
            attempt=self._build_attempt_view(run_id=run_id, retry_count=0, attempt_id=str(selection.daily_rule_selection_id) if not derived else None),
            steps=[
                {
                    "step_id": "daily-rule-selection",
                    "business_label": "生成每日规则选择",
                    "status": status,
                    "started_at": self._iso(selection.created_at),
                    "finished_at": self._iso(selection.updated_at),
                    "duration_seconds": self._duration_seconds(selection.created_at, selection.updated_at),
                    "error": None,
                    "retry_count": 0,
                    "input_references": self._traceability_refs(context),
                    "output_references": [{"type": "daily_rule_selection", "id": str(selection.daily_rule_selection_id), "label": "每日规则选择"}],
                    "repair_guidance": "如需减少降级影响，请先补齐缺失输入后重新生成。",
                }
            ],
            prompt_calls=[],
            data_fetches=[self._build_dataset_fetch_view(dataset), self._build_market_fetch_view(market_snapshot)],
            backtests=[],
            linked_records=[{"type": "daily_rule_selection", "id": str(selection.daily_rule_selection_id), "label": "每日规则选择"}],
            admin_diagnostics={
                "technical_status": status,
                "linked_ids": {"daily_rule_selection_ids": [str(selection.daily_rule_selection_id)]},
                "payload_fingerprints": {"source_run_mode": "derived" if derived else "stored"},
                "raw_metadata": {"selection_context": context},
            } if actor_role in {"operator", "admin"} else None,
        )

    def _build_trading_plan_trace(
        self,
        plan: TradingDayPlan,
        *,
        actor_role: str,
        dataset: DatasetSnapshot | None,
        market_snapshot: MarketSnapshot | None,
    ) -> dict[str, Any]:
        traceability = self._extract_plan_traceability(plan)
        run_id = build_stable_business_run_id(
            object_type="trading-day-plan",
            object_id=str(plan.trading_day_plan_id),
            stored_run_id=plan.source_run_id,
        )
        derived = not bool((plan.source_run_id or "").strip())
        status = "partial" if derived else "ready"
        return self._assemble_trace(
            run_id=run_id,
            business_label="生成今日交易计划",
            status=status,
            started_at=plan.created_at,
            finished_at=plan.updated_at,
            happened="今日交易计划已生成。",
            affected="普通用户可以查看今日计划与风险提示；管理员可继续追踪技术链路。",
            repair_guidance="如果要补齐正式运行追踪，请重新生成本次交易计划。",
            next_action={"label": "查看今日计划", "target_path": "/daily/pre-market"},
            attempt=self._build_attempt_view(run_id=run_id, retry_count=0, attempt_id=str(plan.trading_day_plan_id) if not derived else None),
            steps=[
                {
                    "step_id": "trading-day-plan",
                    "business_label": "生成今日交易计划",
                    "status": status,
                    "started_at": self._iso(plan.created_at),
                    "finished_at": self._iso(plan.updated_at),
                    "duration_seconds": self._duration_seconds(plan.created_at, plan.updated_at),
                    "error": None,
                    "retry_count": 0,
                    "input_references": self._traceability_refs(traceability),
                    "output_references": [{"type": "trading_day_plan", "id": str(plan.trading_day_plan_id), "label": "今日交易计划"}],
                    "repair_guidance": "若需降低风险，请先补齐降级输入后重新生成计划。",
                }
            ],
            prompt_calls=[],
            data_fetches=[self._build_dataset_fetch_view(dataset), self._build_market_fetch_view(market_snapshot)],
            backtests=[],
            linked_records=[{"type": "trading_day_plan", "id": str(plan.trading_day_plan_id), "label": "今日交易计划"}],
            admin_diagnostics={
                "technical_status": status,
                "linked_ids": {"trading_day_plan_ids": [str(plan.trading_day_plan_id)]},
                "payload_fingerprints": {"source_run_mode": "derived" if derived else "stored"},
                "raw_metadata": {"traceability": traceability},
            } if actor_role in {"operator", "admin"} else None,
        )

    def _build_post_market_review_trace(
        self,
        review: PostMarketReview,
        *,
        actor_role: str,
        market_snapshot: MarketSnapshot | None,
        prompt_run: PromptRun | None,
    ) -> dict[str, Any]:
        run_id = build_stable_business_run_id(
            object_type="post-market-review",
            object_id=str(review.post_market_review_id),
        )
        prompt_calls = [self._build_prompt_call_view(prompt_run)] if prompt_run is not None else []
        status = "partial" if prompt_run is None else "ready"
        return self._assemble_trace(
            run_id=run_id,
            business_label="生成正式盘后复盘",
            status=status,
            started_at=review.created_at,
            finished_at=review.updated_at,
            happened="正式盘后复盘已生成。",
            affected="用户可以查看盘后结果、差异和建议动作；诊断信息仅对管理员开放。",
            repair_guidance="如果需要更多诊断细节，请补充运行链路证据后重新生成正式盘后复盘。",
            next_action={"label": "查看正式盘后", "target_path": "/daily/after-close"},
            attempt=self._build_attempt_view(run_id=run_id, retry_count=0, attempt_id=None),
            steps=[
                {
                    "step_id": "post-market-review",
                    "business_label": "生成正式盘后复盘",
                    "status": status,
                    "started_at": self._iso(review.created_at),
                    "finished_at": self._iso(review.updated_at),
                    "duration_seconds": self._duration_seconds(review.created_at, review.updated_at),
                    "error": None,
                    "retry_count": 0,
                    "input_references": [
                        {"type": "trading_day_plan", "id": str(review.trading_day_plan_id), "label": "盘前计划"},
                    ],
                    "output_references": [{"type": "post_market_review", "id": str(review.post_market_review_id), "label": "正式盘后复盘"}],
                    "repair_guidance": "若需补充解释，请在允许的正式流程中重新执行盘后复盘。",
                }
            ],
            prompt_calls=prompt_calls,
            data_fetches=[self._build_market_fetch_view(market_snapshot)],
            backtests=[],
            linked_records=[{"type": "post_market_review", "id": str(review.post_market_review_id), "label": "正式盘后复盘"}],
            admin_diagnostics={
                "technical_status": status,
                "linked_ids": {"post_market_review_ids": [str(review.post_market_review_id)]},
                "payload_fingerprints": {"prompt_run_linked": bool(prompt_run)},
                "raw_metadata": {"evidence_keys": sorted((review.evidence_json or {}).keys())},
            } if actor_role in {"operator", "admin"} else None,
        )

    def _build_system_job_trace(self, job: Any, *, actor_role: str) -> dict[str, Any]:
        params = job.params if isinstance(job.params, dict) else {}
        runtime_state = job.runtime_state if isinstance(job.runtime_state, dict) else {}
        checkpoint = runtime_state.get("checkpoint") if isinstance(runtime_state.get("checkpoint"), dict) else {}
        completed_steps = checkpoint.get("completed_steps") if isinstance(checkpoint.get("completed_steps"), list) else []
        planned_steps = params.get("steps") if isinstance(params.get("steps"), list) else checkpoint.get("planned_steps") if isinstance(checkpoint.get("planned_steps"), list) else []
        if str(getattr(job, "job_type", "system-data-operation")) == "stage3-article-batch":
            return self._build_stage3_batch_trace(job, actor_role=actor_role)
        action = str(params.get("action") or "")
        business_label = self._system_data_business_label(action)
        status = self._map_status((job.result or {}).get("status") if isinstance(job.result, dict) and (job.result or {}).get("status") else job.status)
        steps = []
        for index, step in enumerate(planned_steps, start=1):
            completed = any(
                item.get("action") == step.get("action") and item.get("target_trade_date") == step.get("target_trade_date")
                for item in completed_steps
            )
            steps.append(
                {
                    "step_id": f"system-data-step-{index}",
                    "business_label": str(step.get("label") or step.get("action") or f"步骤 {index}"),
                    "status": "ready" if completed else status,
                    "started_at": self._iso(job.started_at),
                    "finished_at": self._iso(job.finished_at) if completed else None,
                    "duration_seconds": self._duration_seconds(job.started_at, job.finished_at) if completed else None,
                    "error": (job.error or {}).get("message") if isinstance(job.error, dict) and not completed else None,
                    "retry_count": job.retry_count,
                    "input_references": [],
                    "output_references": [],
                    "repair_guidance": str(step.get("reason") or "请先检查上游数据是否真实可用。"),
                }
            )
        return self._assemble_trace(
            run_id=f"system-data-operation:{job.id}",
            business_label=business_label,
            status=status,
            started_at=job.started_at or job.created_at,
            finished_at=job.finished_at or job.updated_at,
            happened=f"{business_label}已记录正式处理状态。",
            affected="普通用户可以看到当前处理是否阻断业务；管理员可继续查看重试策略、失败证据和检查点。",
            repair_guidance=self._system_data_repair_guidance(action=action, status=status),
            next_action={"label": "查看数据与调度", "target_path": "/system/data"},
            attempt=self._build_attempt_view(
                run_id=f"system-data-operation:{job.id}",
                retry_count=job.retry_count,
                attempt_id=f"{job.id}:attempt-{job.retry_count}",
            ),
            steps=steps,
            prompt_calls=[],
            data_fetches=[],
            backtests=[],
            linked_records=[{"type": "job", "id": str(job.id), "label": business_label}],
            admin_diagnostics={
                "technical_status": status,
                "linked_ids": {"job_ids": [str(job.id)]},
                "payload_fingerprints": {"idempotency_key": job.idempotency_key},
                "raw_metadata": {
                    "retry_policy": {
                        "retry_count": int(job.retry_count or 0),
                        "max_retries": int(job.max_retries or 0),
                        "backoff_seconds": int(job.retry_backoff_seconds or 0),
                        "retry_after_max_requires_admin": True,
                    },
                    "failure_evidence": runtime_state.get("last_failure_evidence") or job.error,
                    "action_level": params.get("action_level") or ("admin_approval_required" if action == "backfill" else "notify_only"),
                    "checkpoint": checkpoint,
                },
            } if actor_role in {"operator", "admin"} else None,
        )

    def _build_stage3_batch_trace(self, job: Any, *, actor_role: str) -> dict[str, Any]:
        params = job.params if isinstance(job.params, dict) else {}
        progress = job.progress if isinstance(job.progress, dict) else {}
        quality_stats = progress.get("quality_stats") if isinstance(progress.get("quality_stats"), dict) else {}
        prompt_version = params.get("prompt_version") or "article_analysis_v1"
        schema_version = params.get("schema_version") or "article_analysis_v1"
        status = self._map_status(job.status)
        return self._assemble_trace(
            run_id=f"stage3-batch:{job.id}",
            business_label="LLM 批处理恢复",
            status=status,
            started_at=job.started_at or job.created_at,
            finished_at=job.finished_at or job.updated_at,
            happened="批处理运行状态已记录，可用于恢复结构化文章与规则提取任务。",
            affected="普通用户不会看到技术缓存细节；管理员可查看模型、版本、缓存和重试状态。",
            repair_guidance="如需批量恢复，请先确认 prompt/schema/model 与输入哈希保持一致，再由管理员继续处理。",
            next_action={"label": "查看运行与告警", "target_path": "/system/runs"},
            attempt=self._build_attempt_view(
                run_id=f"stage3-batch:{job.id}",
                retry_count=job.retry_count,
                attempt_id=f"{job.id}:attempt-{job.retry_count}",
            ),
            steps=[],
            prompt_calls=[],
            data_fetches=[],
            backtests=[],
            linked_records=[{"type": "job", "id": str(job.id), "label": "stage3-batch"}],
            admin_diagnostics={
                "technical_status": status,
                "linked_ids": {"job_ids": [str(job.id)]},
                "payload_fingerprints": {"idempotency_key": job.idempotency_key},
                "raw_metadata": {
                    "prompt_version": prompt_version,
                    "schema_version": schema_version,
                    "model": params.get("model"),
                    "retry_count": int(job.retry_count or 0),
                    "cache_state": {
                        "cached_count": progress.get("cached_count"),
                        "quality_stats": quality_stats,
                        "stale_cache_visible": status != "ready",
                    },
                    "action_level": "admin_approval_required",
                },
            } if actor_role in {"operator", "admin"} else None,
        )

    def _assemble_trace(
        self,
        *,
        run_id: str,
        business_label: str,
        status: str,
        started_at: datetime | None,
        finished_at: datetime | None,
        happened: str,
        affected: str,
        repair_guidance: str,
        next_action: dict[str, str],
        attempt: dict[str, Any],
        steps: list[dict[str, Any]],
        prompt_calls: list[dict[str, Any]],
        data_fetches: list[dict[str, Any] | None],
        backtests: list[dict[str, Any]],
        linked_records: list[dict[str, Any]],
        admin_diagnostics: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "business_label": business_label,
            "status": status,
            "started_at": self._iso(started_at),
            "finished_at": self._iso(finished_at),
            "duration_seconds": self._duration_seconds(started_at, finished_at),
            "happened": happened,
            "affected": affected,
            "repair_guidance": repair_guidance,
            "next_action": next_action,
            "attempt": attempt,
            "steps": steps,
            "prompt_calls": prompt_calls,
            "data_fetches": [item for item in data_fetches if item is not None],
            "backtests": backtests,
            "linked_records": linked_records,
            "admin_diagnostics": admin_diagnostics,
        }

    def _build_prompt_call_view(self, run: Any) -> dict[str, Any]:
        return {
            "run_id": (run.run_id or "").strip() or str(run.prompt_run_id),
            "provider": run.provider,
            "model": run.model,
            "prompt_version": run.prompt_version,
            "schema_version": run.schema_version,
            "input_hash": run.input_hash,
            "validation_state": str(run.validation_state),
            "retry_count": run.retry_count,
            "tokens": dict(run.token_usage or {}),
            "cost": {
                "amount": float(run.cost_amount) if isinstance(run.cost_amount, Decimal) else run.cost_amount,
                "currency": run.cost_currency,
            },
            "started_at": self._iso(run.started_at),
            "completed_at": self._iso(run.completed_at),
            "linked_business_object": {
                "object_type": run.input_object_type,
                "object_id": run.input_object_id,
                "version_id": run.input_version_id,
            },
        }

    def _build_attempt_view(self, *, run_id: str, retry_count: int | None, attempt_id: str | None) -> dict[str, Any]:
        return {
            "attempt_id": attempt_id or f"{run_id}:attempt-unknown",
            "retry_count": retry_count,
            "state": "ready" if attempt_id is not None and retry_count is not None else "unavailable",
        }

    def _build_dataset_fetch_view(self, dataset: DatasetSnapshot | None) -> dict[str, Any] | None:
        if dataset is None:
            return None
        coverage = dataset.ohlcv_manifest.get("coverage") if isinstance(dataset.ohlcv_manifest, dict) else None
        return {
            "source": (dataset.storage_ref or {}).get("source") or dataset.dataset_type or "dataset_snapshot",
            "provider": (dataset.storage_ref or {}).get("provider"),
            "snapshot_id": (dataset.storage_ref or {}).get("snapshot_id"),
            "content_fingerprint": dataset.content_fingerprint,
            "date_range": {
                "date_from": dataset.date_from.isoformat() if isinstance(dataset.date_from, date) else dataset.date_from,
                "date_to": dataset.date_to.isoformat() if isinstance(dataset.date_to, date) else dataset.date_to,
            },
            "trade_date": dataset.trade_date.isoformat() if isinstance(dataset.trade_date, date) else dataset.trade_date,
            "slot": (dataset.storage_ref or {}).get("slot"),
            "coverage": coverage,
            "captured_at": None,
            "available_at": self._iso(dataset.available_at),
            "effective_at": self._iso(dataset.frozen_at),
            "quality_status": str(dataset.lifecycle_state),
            "missing_ranges": (dataset.ohlcv_manifest or {}).get("missing_ranges", []),
            "repair_guidance": "如数据覆盖不足，请先重新冻结正式数据快照。",
        }

    def _build_market_fetch_view(self, snapshot: MarketSnapshot | None) -> dict[str, Any] | None:
        if snapshot is None:
            return None
        return {
            "source": snapshot.snapshot_id,
            "provider": ",".join(snapshot.provider_sources or []) or None,
            "snapshot_id": snapshot.snapshot_id,
            "content_fingerprint": snapshot.content_fingerprint,
            "date_range": {
                "date_from": snapshot.trade_date.isoformat(),
                "date_to": snapshot.trade_date.isoformat(),
            },
            "trade_date": snapshot.trade_date.isoformat(),
            "slot": snapshot.slot,
            "coverage": {
                "available_sections": snapshot.available_section_count,
                "partial_sections": snapshot.partial_section_count,
                "missing_sections": snapshot.missing_section_count,
            },
            "captured_at": self._iso(snapshot.captured_at),
            "available_at": self._iso(snapshot.available_at),
            "effective_at": self._iso(snapshot.effective_at),
            "quality_status": snapshot.quality_status,
            "missing_ranges": snapshot.data_quality.get("missing_ranges", []) if isinstance(snapshot.data_quality, dict) else [],
            "repair_guidance": "如市场数据缺失，请先到系统管理中的数据与调度补齐对应时段。",
        }

    def _build_backtest_view(self, run: BacktestRun, result: BacktestResult | None) -> dict[str, Any]:
        return {
            "dataset_snapshot_id": str(run.dataset_snapshot_id),
            "data_fingerprints": {
                "dataset": run.dataset_fingerprint,
                "market_snapshots": list(run.market_snapshot_fingerprints or []),
            },
            "rule_version": {
                "rule_version_id": str(run.rule_version_id) if run.rule_version_id is not None else None,
                "rule_version_no": run.rule_version_no,
                "rule_version_fingerprint": run.rule_version_fingerprint or run.rule_family_fingerprint,
            },
            "market_state_model_version": run.market_state_model_version,
            "code_version": run.engine_version,
            "decision_time_policy": run.decision_time_policy,
            "reproducibility_fingerprint": result.reproducibility_fingerprint if result is not None else run.reproducibility_fingerprint,
            "coverage": result.coverage_json if result is not None else {"coverage_state": run.coverage_state},
            "limitations": result.limitations if result is not None else list(run.limitations or []),
        }

    def _extract_selection_context(self, selection: DailyRuleSelection) -> dict[str, Any]:
        for bucket in (selection.selected_rules_json, selection.reduced_rules_json, selection.blocked_rules_json):
            if isinstance(bucket, dict) and isinstance(bucket.get("selection_context"), dict):
                return dict(bucket["selection_context"])
        return {}

    def _extract_plan_traceability(self, plan: TradingDayPlan) -> dict[str, Any]:
        payload = plan.payload or {}
        traceability = payload.get("traceability")
        return dict(traceability) if isinstance(traceability, dict) else {}

    def _traceability_refs(self, traceability: dict[str, Any]) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for key in ("strategy_version_id", "dataset_snapshot_id", "market_snapshot_id", "market_state_id", "daily_rule_selection_id"):
            value = traceability.get(key)
            if value:
                refs.append({"type": key.removesuffix("_id"), "id": str(value), "label": key})
        return refs

    def _backtest_input_refs(self, run: BacktestRun) -> list[dict[str, Any]]:
        refs = [{"type": "dataset_snapshot", "id": str(run.dataset_snapshot_id), "label": "正式数据快照"}]
        if run.rule_version_id is not None:
            refs.append({"type": "rule_version", "id": str(run.rule_version_id), "label": "规则版本"})
        if run.rule_family_id is not None:
            refs.append({"type": "rule_family", "id": str(run.rule_family_id), "label": "规则族"})
        return refs

    def _prompt_business_label(self, run: PromptRun) -> str:
        mapping = {
            "article_revision": "结构化文章与规则提取",
            "author_profile_version": "生成作者画像草稿",
        }
        return mapping.get(run.input_object_type, "执行正式 Prompt 调用")

    def _system_data_business_label(self, action: str) -> str:
        mapping = {
            "repair": "补齐缺失数据",
            "update_now": "立即更新数据",
            "backfill": "回灌历史数据",
            "recompute_indicators": "重算指标",
            "recompute_market_state": "重算市场状态",
            "run_schedule_window": "执行定时窗口",
        }
        return mapping.get(action, "数据与调度操作")

    def _system_data_repair_guidance(self, *, action: str, status: str) -> str:
        if action == "backfill":
            return "历史回灌必须先经管理员批准，且不得重写历史 available_at / captured_at。"
        if status in {"error", "unavailable"}:
            return "请先检查失败证据、幂等键和最近尝试记录，再决定重试或继续执行。"
        return "如需继续处理，请先确认上游数据已经真实可用。"

    def _prompt_status(self, validation_state: Any) -> str:
        normalized = str(validation_state)
        if normalized in {"valid", "repaired"}:
            return "ready"
        if normalized in {"invalid", "failed"}:
            return "error"
        return "partial"

    def _prompt_repair_guidance(self, validation_state: Any) -> str:
        normalized = str(validation_state)
        if normalized in {"valid", "repaired"}:
            return "当前无需修复。"
        return "请先检查输入证据、Prompt 版本和输出校验错误，再重新执行。"

    def _map_status(self, value: Any) -> str:
        normalized = str(value)
        if normalized in {"success", "completed", "ready", "valid", "repaired"}:
            return "ready"
        if normalized in {"failed", "error", "invalid"}:
            return "error"
        if normalized in {"cancelled", "blocked", "conflict", "unavailable"}:
            return "unavailable"
        return "partial"

    def _parse_uuid(self, value: Any) -> UUID | None:
        if value in {None, ""}:
            return None
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None

    def _iso(self, value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    def _duration_seconds(self, started_at: datetime | None, finished_at: datetime | None) -> float | None:
        if started_at is None or finished_at is None:
            return None
        return round(max(0.0, (finished_at - started_at).total_seconds()), 2)
