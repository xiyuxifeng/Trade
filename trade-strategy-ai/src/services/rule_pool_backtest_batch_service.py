from __future__ import annotations

import hashlib
import json
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Callable
from uuid import uuid4

from src.db.repositories.rule_pool_backtest_batch_repository import RulePoolBacktestBatchRepository
from src.models.rule_pool_backtest_batch import RulePoolBacktestBatch, RulePoolBacktestBatchRun
from src.services.job_service import JobService


def _to_plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}
    if isinstance(value, (date,)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(_to_plain(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class RulePoolBacktestBatchService:
    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any] | None = None,
        repository: RulePoolBacktestBatchRepository | None = None,
        job_service: JobService | None = None,
    ) -> None:
        self._session_scope_factory = session_scope_factory
        self._repository = repository or RulePoolBacktestBatchRepository()
        self._job_service = job_service or JobService()

    def _ensure_session_scope(self) -> Callable[[], Any]:
        if self._session_scope_factory is not None:
            return self._session_scope_factory
        from src.db.session import get_session_factory

        session_factory = get_session_factory()

        @asynccontextmanager
        async def _session_scope():
            async with session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        self._session_scope_factory = _session_scope
        return _session_scope

    def _serialize_batch(self, batch: RulePoolBacktestBatch) -> dict[str, Any]:
        return {
            "batch_id": batch.batch_id,
            "batch_run_id": batch.batch_run_id,
            "batch_index": batch.batch_index,
            "rule_ids": list(batch.rule_ids_json or []),
            "rule_count": len(batch.rule_ids_json or []),
            "job_id": str(batch.job_id) if batch.job_id is not None else None,
            "status": batch.status,
            "result": _to_plain(batch.result_json),
            "result_artifact_id": batch.result_artifact_id,
            "error": _to_plain(batch.error_json),
            "started_at": batch.started_at.isoformat() if batch.started_at else None,
            "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
            "updated_at": batch.updated_at.isoformat() if batch.updated_at else None,
        }

    def _serialize_run(self, batch_run: RulePoolBacktestBatchRun, batches: list[RulePoolBacktestBatch] | None = None) -> dict[str, Any]:
        batch_items = batches if batches is not None else list(batch_run.batches or [])
        return {
            "batch_run_id": batch_run.batch_run_id,
            "status": batch_run.status,
            "start_date": batch_run.start_date.isoformat(),
            "end_date": batch_run.end_date.isoformat(),
            "min_confidence": float(batch_run.min_confidence),
            "market_regime_version": batch_run.market_regime_version,
            "profile_id": batch_run.profile_id,
            "selected_rule_count": batch_run.selected_rule_count,
            "batch_size": batch_run.batch_size,
            "created_by": batch_run.created_by,
            "merged_result_id": batch_run.merged_result_id,
            "config": _to_plain(batch_run.config_json or {}),
            "fingerprint": batch_run.fingerprint,
            "batches": [self._serialize_batch(batch) for batch in batch_items],
            "created_at": batch_run.created_at.isoformat() if batch_run.created_at else None,
            "updated_at": batch_run.updated_at.isoformat() if batch_run.updated_at else None,
        }

    async def create_batch_run(
        self,
        *,
        rule_ids: list[str],
        batch_size: int,
        start_date: date,
        end_date: date,
        min_confidence: float,
        market_regime_version: str | None,
        profile_id: str | None,
        created_by: str | None,
    ) -> dict[str, Any]:
        cleaned_rule_ids = [str(item).strip() for item in rule_ids if str(item).strip()]
        if not cleaned_rule_ids:
            raise ValueError("rule_ids must not be empty")
        if batch_size < 1 or batch_size > 500:
            raise ValueError("batch_size must be between 1 and 500")
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")

        batch_run_id = f"rpbt-{uuid4().hex}"
        config = {
            "source_surface": "/rules/backtests",
            "rule_ids": cleaned_rule_ids,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "min_confidence": min_confidence,
            "market_regime_version": market_regime_version,
            "profile_id": profile_id,
        }
        batch_run = RulePoolBacktestBatchRun(
            batch_run_id=batch_run_id,
            status="draft",
            start_date=start_date,
            end_date=end_date,
            min_confidence=min_confidence,
            market_regime_version=market_regime_version,
            profile_id=profile_id,
            selected_rule_count=len(cleaned_rule_ids),
            batch_size=batch_size,
            created_by=created_by,
            config_json=config,
            fingerprint=_fingerprint(config),
        )
        batches = [
            RulePoolBacktestBatch(
                batch_id=f"{batch_run_id}-{index:03d}",
                batch_run_id=batch_run_id,
                batch_index=index,
                rule_ids_json=cleaned_rule_ids[offset : offset + batch_size],
                status="pending",
            )
            for index, offset in enumerate(range(0, len(cleaned_rule_ids), batch_size), start=1)
        ]
        async with self._ensure_session_scope()() as session:
            saved = await self._repository.create_batch_run(session, batch_run=batch_run, batches=batches)
            return self._serialize_run(saved, batches)

    async def list_batch_runs(self, *, limit: int = 50, skip: int = 0) -> dict[str, Any]:
        async with self._ensure_session_scope()() as session:
            items = await self._repository.list_batch_runs(session, limit=limit, offset=skip)
            total = await self._repository.count_batch_runs(session)
            serialized = [self._serialize_run(item) for item in items]
            return {"items": serialized, "count": len(serialized), "total": total, "skip": skip, "limit": limit}

    async def get_batch_run(self, batch_run_id: str) -> dict[str, Any]:
        async with self._ensure_session_scope()() as session:
            batch_run = await self._repository.get_batch_run(session, batch_run_id)
            if batch_run is None:
                raise LookupError("batch run not found")
            return self._serialize_run(batch_run)

    async def start_batch(self, batch_run_id: str, *, batch_index: int, actor: str) -> dict[str, Any]:
        async with self._ensure_session_scope()() as session:
            batch_run = await self._repository.get_batch_run(session, batch_run_id)
            if batch_run is None:
                raise LookupError("batch run not found")
            batch = next((item for item in batch_run.batches if item.batch_index == batch_index), None)
            if batch is None:
                raise LookupError("batch not found")
            if batch.status not in {"pending", "failed", "cancelled"}:
                raise ValueError("only pending, failed or cancelled batches can be started")

            params = {
                "rule_ids": list(batch.rule_ids_json or []),
                "start_date": batch_run.start_date.isoformat(),
                "end_date": batch_run.end_date.isoformat(),
                "min_confidence": float(batch_run.min_confidence),
                "market_regime_version": batch_run.market_regime_version,
                "profile_id": batch_run.profile_id,
            }
            created = await self._job_service.create_job(
                job_type="rule-pool-backtest",
                params=params,
                created_by=actor,
                confirmed=True,
                idempotency_key=f"{batch_run_id}:{batch_index}:rule-pool-backtest",
            )
            if created.status != "ok":
                raise ValueError(created.message or "batch job creation failed")
            job = created.payload["job"]
            await self._repository.update_batch_status(
                session,
                batch_run_id=batch_run_id,
                batch_index=batch_index,
                status="running",
                job_id=job["id"],
            )
            refreshed = await self._repository.update_batch_run(session, batch_run_id=batch_run_id, status="running")
            if refreshed is None:
                raise LookupError("batch run not found")
            return self._serialize_run(refreshed)

    async def refresh_batch_status(self, batch_run_id: str) -> dict[str, Any]:
        async with self._ensure_session_scope()() as session:
            batch_run = await self._repository.get_batch_run(session, batch_run_id)
            if batch_run is None:
                raise LookupError("batch run not found")
            for batch in list(batch_run.batches or []):
                if batch.job_id is None:
                    continue
                job_result = await self._job_service.get_job(str(batch.job_id))
                if job_result.status != "ok":
                    continue
                job = job_result.payload.get("job", {})
                status_map = {"success": "completed", "failed": "failed", "cancelled": "cancelled", "paused": "paused", "running": "running", "pending": "running"}
                mapped_status = status_map.get(str(job.get("status")), batch.status)
                await self._repository.update_batch_status(
                    session,
                    batch_run_id=batch_run_id,
                    batch_index=batch.batch_index,
                    status=mapped_status,
                    result_json=job.get("result") if mapped_status == "completed" and isinstance(job.get("result"), dict) else None,
                    error_json=job.get("error") if mapped_status == "failed" and isinstance(job.get("error"), dict) else None,
                )
            refreshed = await self._repository.get_batch_run(session, batch_run_id)
            if refreshed is None:
                raise LookupError("batch run not found")
            statuses = {batch.status for batch in refreshed.batches}
            run_status = "completed" if statuses and statuses <= {"completed"} else "partial" if "failed" in statuses or "cancelled" in statuses else refreshed.status
            refreshed = await self._repository.update_batch_run(session, batch_run_id=batch_run_id, status=run_status)
            if refreshed is None:
                raise LookupError("batch run not found")
            return self._serialize_run(refreshed)

    def _validate_merge_request(self, batch_run: RulePoolBacktestBatchRun) -> None:
        batches = list(batch_run.batches or [])
        if not batches:
            raise ValueError("no batches to merge")
        incomplete = [batch.batch_index for batch in batches if batch.status != "completed"]
        if incomplete:
            raise ValueError(f"only completed batches can be merged; incomplete batches: {incomplete}")
        missing = [batch.batch_index for batch in batches if not isinstance(batch.result_json, dict)]
        if missing:
            raise ValueError(f"completed batches are missing result payloads: {missing}")
        expected = {
            "start_date": batch_run.start_date.isoformat(),
            "end_date": batch_run.end_date.isoformat(),
            "min_confidence": float(batch_run.min_confidence),
            "market_regime_version": batch_run.market_regime_version,
            "profile_id": batch_run.profile_id,
        }
        conflicts: list[int] = []
        for batch in batches:
            request = (batch.result_json or {}).get("request")
            if not isinstance(request, dict):
                conflicts.append(batch.batch_index)
                continue
            for key, expected_value in expected.items():
                if request.get(key) != expected_value:
                    conflicts.append(batch.batch_index)
                    break
        if conflicts:
            raise ValueError(f"batch result parameters conflict with the batch run: {conflicts}")

    def _build_merged_result(self, batch_run: RulePoolBacktestBatchRun) -> dict[str, Any]:
        total_days = total_trades = valid_trades = skipped_trades = 0
        records: list[dict[str, Any]] = []
        rule_results: list[dict[str, Any]] = []
        rule_regime_metrics: dict[str, Any] = {}
        for batch in list(batch_run.batches or []):
            payload = batch.result_json or {}
            result = payload.get("result") if isinstance(payload.get("result"), dict) else payload
            summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
            total_days = max(total_days, int(summary.get("total_days") or 0))
            total_trades += int(summary.get("total_trades") or 0)
            valid_trades += int(summary.get("valid_trades") or 0)
            skipped_trades += int(summary.get("skipped_trades") or 0)
            for record in list(result.get("records") or []):
                if isinstance(record, dict):
                    records.append({**record, "batch_id": batch.batch_id, "batch_run_id": batch.batch_run_id, "job_id": str(batch.job_id) if batch.job_id else None})
            raw_metrics = result.get("rule_regime_metrics")
            if isinstance(raw_metrics, dict):
                for rule_id, metrics in raw_metrics.items():
                    rule_regime_metrics[str(rule_id)] = metrics
                    rule_results.append(
                        {
                            "rule_id": str(rule_id),
                            "batch_id": batch.batch_id,
                            "batch_index": batch.batch_index,
                            "batch_run_id": batch.batch_run_id,
                            "job_id": str(batch.job_id) if batch.job_id else None,
                            "source_result_reference": batch.result_artifact_id or str(batch.job_id or ""),
                            "market_state_metrics": metrics,
                        }
                    )
        summary = {
            "total_days": total_days,
            "total_trades": total_trades,
            "valid_trades": valid_trades,
            "skipped_trades": skipped_trades,
        }
        return {
            "result_id": f"merged-{batch_run.batch_run_id}",
            "batch_run_id": batch_run.batch_run_id,
            "status": "merged",
            "summary": summary,
            "records": records,
            "rule_results": rule_results,
            "rule_regime_metrics": rule_regime_metrics,
            "provenance": {
                "source": "rule_pool_backtest_batch_merge",
                "batch_ids": [batch.batch_id for batch in batch_run.batches],
                "job_ids": [str(batch.job_id) for batch in batch_run.batches if batch.job_id is not None],
            },
        }

    async def merge_batch_results(self, batch_run_id: str) -> dict[str, Any]:
        async with self._ensure_session_scope()() as session:
            batch_run = await self._repository.get_batch_run(session, batch_run_id)
            if batch_run is None:
                raise LookupError("batch run not found")
            self._validate_merge_request(batch_run)
            merged_result = self._build_merged_result(batch_run)
            config = dict(batch_run.config_json or {})
            config["merged_result"] = merged_result
            saved = await self._repository.update_batch_run(
                session,
                batch_run_id=batch_run_id,
                status="merged",
                merged_result_id=merged_result["result_id"],
                config_json=config,
            )
            if saved is None:
                raise LookupError("batch run not found")
            payload = self._serialize_run(saved)
            payload["merged_result"] = merged_result
            return payload
