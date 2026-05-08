from __future__ import annotations

import asyncio
import json
import os
import socket
from contextlib import suppress
from datetime import UTC, date, datetime
from collections import defaultdict
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import UUID, uuid4

from src.agents.manager_agent.agent import ManagerAgent
from src.common.config import load_app_config
from src.services.base import BaseService, ServiceResult
from src.services.job_registry import (
    get_job_definition,
    get_job_type_limits,
    get_runnable_job_types,
    validate_job_submission,
)
from src.services.job_service import JobService
from src.services.pipeline_service import PipelineService
from src.services.run_service import RunService


def _to_plain(value: Any) -> Any:
    """把服务返回值转成可写入 JSON 的结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _parse_date(value: Any) -> date:
    """将字符串或 date 统一解析为 date。"""
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    return date.today()


def _parse_bool(value: Any, default: bool = False) -> bool:
    """将前端参数中的布尔值统一归一化。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _project_base_dir(config_path: Path) -> Path:
    """根据配置文件路径推导项目根目录。"""
    if config_path.parent.name == "config":
        return config_path.parent.parent
    return config_path.parent


class JobRunner(BaseService):
    """受控 Job 执行入口。

    该类只负责白名单 Job 的执行编排，不接受任意 shell 命令。
    """

    service_name = "job-runner"

    def __init__(
        self,
        *,
        job_service: JobService | None = None,
        manager_factory: Callable[..., ManagerAgent] = ManagerAgent,
        pipeline_service_factory: Callable[[], PipelineService] = PipelineService,
        config_loader: Callable[[str | Path], Any] = load_app_config,
        worker_id: str | None = None,
        heartbeat_interval_seconds: float = 5.0,
        job_type_limits: dict[str, int] | None = None,
        handlers: dict[str, Callable[[dict[str, Any]], Awaitable[ServiceResult]]] | None = None,
    ) -> None:
        self._job_service = job_service or JobService()
        self._manager_factory = manager_factory
        self._pipeline_service_factory = pipeline_service_factory
        self._config_loader = config_loader
        self._worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}"
        self._heartbeat_interval_seconds = max(0.1, float(heartbeat_interval_seconds))
        self._job_type_limits = {**get_job_type_limits(), **(job_type_limits or {})}
        self._handlers = handlers or {}

    def supported_job_types(self) -> list[str]:
        """返回当前 Runner 支持的 job type 白名单。"""
        return get_runnable_job_types()

    def _build_manager(self, *, config_path: str | Path) -> tuple[ManagerAgent, Path]:
        """按 config_path 构建 ManagerAgent。"""
        loaded = self._config_loader(config_path)
        base_dir = _project_base_dir(Path(loaded.config_path))
        manager = self._manager_factory(config=loaded.config, base_dir=base_dir)
        return manager, base_dir

    def _build_default_handlers(self) -> dict[str, Callable[[dict[str, Any]], Awaitable[ServiceResult]]]:
        """构建默认的 Job 处理器集合。"""

        async def _run_pre_market(params: dict[str, Any]) -> ServiceResult:
            manager, _ = self._build_manager(config_path=params.get("config_path", "config/app.yaml"))
            service = RunService(manager)
            return await service.run_pre_market(
                as_of_date=_parse_date(params.get("as_of_date")),
                force=_parse_bool(params.get("force"), default=False),
                export_html=_parse_bool(params.get("export_html"), default=False),
            )

        async def _run_after_close(params: dict[str, Any]) -> ServiceResult:
            manager, _ = self._build_manager(config_path=params.get("config_path", "config/app.yaml"))
            service = RunService(manager)
            return await service.run_after_close(
                as_of_date=_parse_date(params.get("as_of_date")),
                force=_parse_bool(params.get("force"), default=False),
                export_html=_parse_bool(params.get("export_html"), default=False),
            )

        async def _pipeline_run(params: dict[str, Any]) -> ServiceResult:
            service = self._pipeline_service_factory()
            return await service.run_pipeline(
                config_path=params.get("config_path", "config/app.yaml"),
                max_articles=params.get("max_articles"),
                force=_parse_bool(params.get("force"), default=False),
                skip_crawl=_parse_bool(params.get("skip_crawl"), default=False),
                from_step=params.get("from_step"),
                use_db=_parse_bool(params.get("use_db"), default=False),
                new_version=params.get("new_version"),
            )

        async def _pipeline_step(params: dict[str, Any]) -> ServiceResult:
            service = self._pipeline_service_factory()
            return await service.run_pipeline_step(
                step=params.get("step", "crawl"),
                config_path=params.get("config_path", "config/app.yaml"),
                max_articles=params.get("max_articles"),
                force=_parse_bool(params.get("force"), default=False),
                use_db=_parse_bool(params.get("use_db"), default=False),
                new_version=params.get("new_version"),
            )

        return {
            "run-pre-market": _run_pre_market,
            "run-after-close": _run_after_close,
            "pipeline-run": _pipeline_run,
            "pipeline-step": _pipeline_step,
        }

    def _handler_for(self, job_type: str) -> Callable[[dict[str, Any]], Awaitable[ServiceResult]] | None:
        """获取某个 job type 的处理器。"""
        definition = get_job_definition(job_type)
        if definition is None or not definition.runnable:
            return None
        if job_type in self._handlers:
            return self._handlers[job_type]
        return self._build_default_handlers().get(job_type)

    def _limit_for_job_type(self, job_type: str) -> int:
        """返回某个 job type 的并发限制。"""
        return max(1, int(self._job_type_limits.get(job_type, 1)))

    async def _heartbeat_loop(self, *, job_id: str | UUID, worker_id: str, lock_token: str) -> None:
        """后台定期刷新心跳，直到任务结束。"""
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval_seconds)
                await self._job_service.heartbeat_job(job_id=job_id, worker_id=worker_id, lock_token=lock_token)
        except asyncio.CancelledError:
            raise

    async def _write_result_file(self, *, job_dir: Path, payload: dict[str, Any]) -> Path:
        """把执行结果写入 result.json。"""
        job_dir.mkdir(parents=True, exist_ok=True)
        result_path = job_dir / "result.json"
        result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return result_path

    async def execute_job(
        self,
        *,
        job_id: str | UUID,
        worker_id: str | None = None,
        lock_token: str | None = None,
    ) -> ServiceResult:
        """执行一个已入库的 Job。"""
        claim = await self._job_service.claim_job(
            job_id=job_id,
            worker_id=worker_id or self._worker_id,
            lock_token=lock_token or uuid4().hex,
        )
        if claim.status != "ok":
            return claim

        job_payload = claim.payload["job"]
        job_dir = Path(claim.payload["job_dir"])
        handler = self._handler_for(job_payload["job_type"])
        if handler is None:
            return await self._job_service.fail_job(
                job_id=job_id,
                error={"type": "unsupported_job_type", "message": f"unsupported job type: {job_payload['job_type']}"},
            )

        await self._job_service.append_log(
            job_id=job_id,
            line=f"[runner] started job_type={job_payload['job_type']}",
        )

        heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(
                job_id=job_id,
                worker_id=worker_id or self._worker_id,
                lock_token=lock_token or job_payload.get("lock_token") or "",
            )
        )

        params = dict(job_payload.get("params") or {})
        try:
            result = await handler(params)
            result_payload = _to_plain(result.model_dump())
            result_path = await self._write_result_file(job_dir=job_dir, payload=result_payload)
            await self._job_service.bind_artifact(
                job_id=job_id,
                kind="result-json",
                path=result_path,
                metadata={"job_type": job_payload["job_type"]},
            )
            if result_payload.get("payload", {}).get("html_path"):
                await self._job_service.bind_artifact(
                    job_id=job_id,
                    kind="html",
                    path=result_payload["payload"]["html_path"],
                    metadata={"job_type": job_payload["job_type"]},
                )
            if result.status == "error":
                failed = await self._job_service.fail_job(
                    job_id=job_id,
                    error={
                        "type": "handler_error",
                        "message": result.message or "job handler returned error",
                        "result": result_payload,
                    },
                )
                return ServiceResult(
                    status="error",
                    message="job execution failed",
                    payload={"job": failed.payload.get("job"), "result": result_payload, "result_path": str(result_path)},
                )

            completed = await self._job_service.complete_job(job_id=job_id, result=result_payload)
            await self._job_service.append_log(
                job_id=job_id,
                line=f"[runner] completed job_type={job_payload['job_type']} status={result.status}",
            )
            return ServiceResult(
                status="ok",
                message="job executed",
                payload={
                    "job": completed.payload["job"],
                    "result": result_payload,
                    "result_path": str(result_path),
                },
            )
        except Exception as exc:  # noqa: BLE001
            await self._job_service.append_log(job_id=job_id, line=f"[runner] failed: {exc}")
            failed = await self._job_service.fail_job(
                job_id=job_id,
                error={"type": "runner_error", "message": str(exc)},
            )
            return ServiceResult(
                status="error",
                message="job execution failed",
                payload={"job": failed.payload.get("job"), "error": str(exc)},
            )
        finally:
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task

    async def submit_job(
        self,
        *,
        job_type: str,
        params: dict[str, Any] | None = None,
        created_by: str | None = None,
        idempotency_key: str | None = None,
        worker_id: str | None = None,
        lock_token: str | None = None,
    ) -> ServiceResult:
        """创建并立即执行 Job。"""
        validated = validate_job_submission(job_type=job_type, params=params or {}, created_by=created_by)
        if validated.status != "ok":
            return validated
        created = await self._job_service.create_job(
            job_type=job_type,
            params=validated.payload["params"],
            created_by=created_by,
            idempotency_key=idempotency_key,
        )
        job_payload = created.payload["job"]
        if created.payload.get("created") is False and job_payload.get("status") != "pending":
            return created
        execution = await self.execute_job(
            job_id=job_payload["id"],
            worker_id=worker_id,
            lock_token=lock_token,
        )
        return ServiceResult(
            status=execution.status,
            message=execution.message,
            payload={
                "created": created.payload,
                "execution": execution.payload,
            },
            warnings=execution.warnings,
        )

    async def run_worker_once(self, *, limit: int = 10) -> ServiceResult:
        """拉取一批可执行 Job，并受并发限制执行。"""
        ready = await self._job_service.list_ready_jobs(limit=limit)
        if ready.status != "ok":
            return ready

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in ready.payload.get("items", []):
            grouped[item["job_type"]].append(item)

        executed: list[dict[str, Any]] = []
        tasks: list[asyncio.Task[ServiceResult]] = []
        pending_meta: list[dict[str, Any]] = []
        for job_type, items in grouped.items():
            running = await self._job_service.count_jobs(status="running", job_type=job_type)
            running_count = int(running.payload.get("count", 0)) if running.status == "ok" else 0
            slots = max(0, self._limit_for_job_type(job_type) - running_count)
            for item in items[:slots]:
                tasks.append(asyncio.create_task(self.execute_job(job_id=item["id"])))
                pending_meta.append({"job_id": item["id"], "job_type": job_type})

        if tasks:
            results = await asyncio.gather(*tasks)
            for meta, result in zip(pending_meta, results, strict=True):
                executed.append({"job_id": meta["job_id"], "job_type": meta["job_type"], "status": result.status, "message": result.message})
        return ServiceResult(
            status="ok",
            message="ready jobs processed",
            payload={
                "count": len(executed),
                "items": executed,
                "listed": ready.payload,
            },
        )

    async def run_pending_jobs_once(self, *, limit: int = 10) -> ServiceResult:
        """兼容旧入口：执行当前可领取的 Job。"""
        return await self.run_worker_once(limit=limit)

    async def recover_stale_jobs(self, *, stale_before: datetime) -> ServiceResult:
        """回收 stale 的 running Job，并标记哪些任务仍然可重试。"""
        recovered = await self._job_service.recover_stale_jobs(stale_before=stale_before)
        retryable_job_ids: list[str] = []
        for job_id in recovered.payload.get("job_ids", []):
            loaded = await self._job_service.get_job(job_id)
            if loaded.status != "ok":
                continue
            job = loaded.payload["job"]
            if int(job.get("retry_count", 0)) < int(job.get("max_retries", 0)):
                retryable_job_ids.append(job_id)
        payload = dict(recovered.payload)
        payload["retryable_job_ids"] = retryable_job_ids
        return ServiceResult(
            status=recovered.status,
            message=recovered.message,
            payload=payload,
            warnings=recovered.warnings,
        )
