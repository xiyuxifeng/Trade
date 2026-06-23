from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import select

from src.db.session import get_session_factory
from src.domain.enums import FormalLifecycleState
from src.models.stage2_canonical import AuthorProfileVersion, BacktestResult, BacktestRun, PromptRun
from src.services.base import BaseService, ServiceResult

PROMPT_COST_WARNING_THRESHOLD_USD = Decimal("10")
STAGE3_BATCH_CONCURRENCY_LIMIT = 2
STAGE3_BATCH_RETRY_CAP = 1
SYSTEM_DATA_RETRY_CAP = 2
FORMAL_BACKTEST_RETRY_CAP = 0
METRIC_CALCULATION_VERSION = "stage6-market-state-metric-v1"


class SystemCostControlService(BaseService):
    service_name = "system-cost-control"

    def __init__(self, *, session_scope_factory: Callable[[], Any] | None = None) -> None:
        self._session_scope_factory = session_scope_factory or self._default_session_scope_factory

    @staticmethod
    @asynccontextmanager
    async def _default_session_scope_factory():
        session_factory = get_session_factory()
        async with session_factory() as session:
            yield session

    async def get_summary(self, *, actor_role: str) -> ServiceResult:
        async with self._session_scope_factory() as session:
            prompt_runs = list(
                (
                    await session.execute(
                        select(PromptRun).order_by(PromptRun.created_at.desc()).limit(20)
                    )
                )
                .scalars()
                .all()
            )
            backtest_rows = list(
                (
                    await session.execute(
                        select(BacktestRun, BacktestResult)
                        .join(BacktestResult, BacktestResult.run_id == BacktestRun.run_id)
                        .order_by(BacktestResult.created_at.desc())
                        .limit(20)
                    )
                )
                .all()
            )
            profile_rows = list(
                (
                    await session.execute(
                        select(AuthorProfileVersion)
                        .order_by(AuthorProfileVersion.updated_at.desc(), AuthorProfileVersion.created_at.desc())
                        .limit(20)
                    )
                )
                .scalars()
                .all()
            )

        total_cost = Decimal("0")
        total_tokens = 0
        currency: str | None = None
        prompt_run_count = 0
        for run in prompt_runs:
            if run.cost_amount is not None:
                total_cost += run.cost_amount if isinstance(run.cost_amount, Decimal) else Decimal(str(run.cost_amount))
                currency = currency or run.cost_currency or "USD"
            tokens = run.token_usage or {}
            total_tokens += int(tokens.get("total_tokens") or 0)
            prompt_run_count += 1

        budget_warning = {
            "status": "warning" if total_cost >= PROMPT_COST_WARNING_THRESHOLD_USD else "ok",
            "message": (
                "最近 7 天的 LLM 成本已接近预算上限。"
                if total_cost >= PROMPT_COST_WARNING_THRESHOLD_USD
                else "当前 LLM 成本仍在预算提醒阈值内。"
            ),
            "enforcement": "notify_only",
            "affected_flows": ["文章结构化", "作者方法画像", "作者规则画像", "作者验证画像"],
        }

        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "llm_cost_summary": {
                "currency": currency or "USD",
                "total_cost": float(total_cost),
                "prompt_run_count": prompt_run_count,
                "total_tokens": total_tokens,
            },
            "budget_warning": budget_warning,
            "concurrency_limits": [
                {"task_type": "stage3_article_batch", "label": "文章批处理", "limit": STAGE3_BATCH_CONCURRENCY_LIMIT},
                {"task_type": "formal_backtest_execution", "label": "正式回测", "limit": 1},
                {"task_type": "system_data_operation", "label": "数据与调度操作", "limit": 1},
            ],
            "retry_caps": [
                {"task_type": "stage3_article_batch", "label": "文章批处理", "max_retries": STAGE3_BATCH_RETRY_CAP},
                {"task_type": "formal_backtest_execution", "label": "正式回测", "max_retries": FORMAL_BACKTEST_RETRY_CAP},
                {"task_type": "system_data_operation", "label": "数据与调度操作", "max_retries": SYSTEM_DATA_RETRY_CAP},
            ],
            "prompt_cache_samples": [self._build_prompt_cache_sample(run) for run in prompt_runs[:5]],
            "backtest_reuse_samples": [
                self._build_backtest_reuse_sample(run, result) for run, result in backtest_rows[:5]
            ],
            "incremental_profile_samples": [self._build_incremental_profile_sample(row) for row in profile_rows[:5]],
        }
        if actor_role not in {"operator", "admin"}:
            payload.update(
                {
                    "concurrency_limits": [],
                    "retry_caps": [],
                    "prompt_cache_samples": [],
                    "backtest_reuse_samples": [],
                    "incremental_profile_samples": [],
                }
            )
        return ServiceResult(status="ok", message="cost control summary listed", payload=payload)

    def _build_prompt_cache_sample(self, run: PromptRun) -> dict[str, Any]:
        invalidation_reasons: list[str] = []
        cache_status = "ready"
        if not run.input_hash:
            cache_status = "unavailable"
            invalidation_reasons.append("input_hash_missing")
        if not run.prompt_version:
            cache_status = "unavailable"
            invalidation_reasons.append("prompt_version_missing")
        if not run.schema_version:
            cache_status = "unavailable"
            invalidation_reasons.append("schema_version_missing")
        if str(run.validation_state) not in {"valid", "repaired", "PromptValidationState.valid", "PromptValidationState.repaired"}:
            cache_status = "stale"
            invalidation_reasons.append("validation_state_invalid")

        request_json = run.request_json if isinstance(run.request_json, dict) else {}
        content_hash = request_json.get("content_hash")
        content_hash_status = "ready" if content_hash else "unavailable"
        if not content_hash:
            invalidation_reasons.append("content_hash_evidence_unavailable")
            if cache_status == "ready":
                cache_status = "unavailable"

        return {
            "prompt_name": run.prompt_name,
            "prompt_version": run.prompt_version,
            "schema_version": run.schema_version,
            "model": run.model,
            "input_hash": run.input_hash,
            "retry_count": int(run.retry_count or 0),
            "cache_status": cache_status,
            "invalidation_reasons": invalidation_reasons,
            "content_hash_status": content_hash_status,
            "article_revision_id": run.input_version_id if run.input_object_type == "article_revision" else None,
            "content_hash": content_hash,
        }

    def _build_backtest_reuse_sample(self, run: BacktestRun, result: BacktestResult) -> dict[str, Any]:
        audit = result.audit_json if isinstance(result.audit_json, dict) else {}
        reuse_contract = audit.get("reuse_contract") if isinstance(audit.get("reuse_contract"), dict) else {}
        metric_cache = audit.get("metric_cache") if isinstance(audit.get("metric_cache"), dict) else {}
        invalidation_reasons = reuse_contract.get("invalidation_reasons")
        if not isinstance(invalidation_reasons, list):
            invalidation_reasons = []
        return {
            "run_id": str(run.run_id),
            "reuse_status": reuse_contract.get("status") or "fresh",
            "invalidation_reasons": invalidation_reasons,
            "metric_cache_status": metric_cache.get("status") or ("ready" if result.input_fingerprint and result.result_fingerprint else "unavailable"),
            "calculation_version": metric_cache.get("calculation_version") or METRIC_CALCULATION_VERSION,
        }

    def _build_incremental_profile_sample(self, row: AuthorProfileVersion) -> dict[str, Any]:
        source_versions = row.source_versions if isinstance(row.source_versions, dict) else {}
        source_article_ids = row.source_article_ids if isinstance(row.source_article_ids, dict) else {}
        invalidation_reasons = source_versions.get("invalidation_reasons")
        if not isinstance(invalidation_reasons, list):
            invalidation_reasons = []
        update_scope = source_versions.get("incremental_update_scope")
        if not update_scope:
            update_scope = "changed_article_revision_group" if source_article_ids.get("article_revision_ids") else "evidence_group_unavailable"
        status = "draft_only"
        if row.lifecycle_state == FormalLifecycleState.published:
            status = "published_version_read_only"
        return {
            "profile_kind": row.profile_kind.value if hasattr(row.profile_kind, "value") else str(row.profile_kind),
            "author_id": str(row.author_id),
            "update_scope": update_scope,
            "status": status,
            "invalidation_reasons": invalidation_reasons,
        }
