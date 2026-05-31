from __future__ import annotations

import asyncio
import json
import os
import socket
from dataclasses import asdict, is_dataclass
from contextlib import suppress
from contextvars import ContextVar
from datetime import UTC, date, datetime
from collections import defaultdict
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import UUID, uuid4

from src.agents.manager_agent.agent import ManagerAgent
from src.services.ops_service import OpsRecoveryService
from src.services.backtest_service import BacktestService
from src.common.config import load_app_config
from src.services.base import BaseService, ServiceResult
from src.services.config_profile_service import ConfigProfileService
from src.services.kaipan_service import KaipanService
from src.pipeline.dag import discover_crawl_jsonl_paths
from src.pipeline.tasks.clean_task import run_clean_from_db_task, run_clean_task
from src.pipeline.tasks.process_tasks import run_process_tasks
from src.pipeline.tasks.validate_task import run_validate_task
from src.agents.data_agent.skills.store_db import default_pending_tasks_path, store_articles_jsonl_to_db
from src.services.job_registry import (
    get_job_definition,
    get_job_type_limits,
    get_runnable_job_types,
    validate_job_submission,
)
from src.services.job_service import JobService
from src.services.pipeline_service import PipelineService
from src.services.market_service import MarketService
from src.services.optimize_service import OptimizeService
from src.services.persona_service import PersonaService
from src.services.run_service import RunService
from src.services.snapshot_service import SnapshotService
from src.services.strategy_service import StrategyService
from src.services.job_control import JobControlInterrupted, JobControlState
from src.models.job import JobStatus
from src.common.logger import bind_log_context, get_logger


logger = get_logger(__name__)


_KAIPAN_PROGRESS_REPORTER: ContextVar[Callable[[dict[str, Any]], None] | None] = ContextVar(
    "kaipan_progress_reporter",
    default=None,
)


def _to_plain(value: Any) -> Any:
    """把服务返回值转成可写入 JSON 的结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if is_dataclass(value):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


_SENSITIVE_RESULT_PATH_KEYS = {
    "html_path",
    "market_state_path",
    "quality_report_path",
    "result_path",
    "snapshot_path",
    "snapshot_summary_path",
}


def _sanitize_result_payload_for_output(payload: dict[str, Any]) -> dict[str, Any]:
    """把对外写入的 job result 脱敏，避免暴露绝对路径。"""

    def _sanitize(value: Any, key: str | None = None) -> Any:
        if isinstance(value, dict):
            return {item_key: _sanitize(item_value, item_key) for item_key, item_value in value.items()}
        if isinstance(value, list):
            return [_sanitize(item) for item in value]
        if key in _SENSITIVE_RESULT_PATH_KEYS and isinstance(value, (str, Path)):
            return Path(value).name
        return value

    return _sanitize(_to_plain(payload))


def _strip_keys_recursive(value: Any, keys: set[str]) -> Any:
    """递归删除字典结构中的指定键。"""
    if isinstance(value, dict):
        return {item_key: _strip_keys_recursive(item_value, keys) for item_key, item_value in value.items() if item_key not in keys}
    if isinstance(value, list):
        return [_strip_keys_recursive(item, keys) for item in value]
    return value


def _parse_date(value: Any) -> date:
    """将字符串或 date 统一解析为 date。"""
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    return date.today()


def _parse_optional_date(value: Any) -> date | None:
    """将可选日期参数归一化为 date。"""
    if value in {None, ""}:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"invalid date value: {value}")


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
        backtest_service_factory: Callable[[], BacktestService] = BacktestService,
        config_loader: Callable[[str | Path], Any] = load_app_config,
        worker_id: str | None = None,
        heartbeat_interval_seconds: float = 5.0,
        job_type_limits: dict[str, int] | None = None,
        handlers: dict[str, Callable[[dict[str, Any]], Awaitable[ServiceResult]]] | None = None,
    ) -> None:
        self._job_service = job_service or JobService()
        self._manager_factory = manager_factory
        self._pipeline_service_factory = pipeline_service_factory
        self._backtest_service_factory = backtest_service_factory
        self._config_loader = config_loader
        self._worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}"
        self._heartbeat_interval_seconds = max(0.1, float(heartbeat_interval_seconds))
        self._job_type_limits = {**get_job_type_limits(), **(job_type_limits or {})}
        self._handlers = handlers or {}

    def _create_progress_tracker(
        self,
        *,
        job_id: str | UUID,
    ) -> tuple[Callable[[dict[str, Any]], None], Callable[[], Awaitable[None]]]:
        """创建按顺序写入 Job progress 的回调与收尾器。"""
        progress_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        update_failed = False

        async def _drain() -> None:
            nonlocal update_failed
            while True:
                item = await progress_queue.get()
                try:
                    if item is None:
                        return
                    if update_failed:
                        continue
                    result = await self._job_service.update_job_progress(job_id=job_id, progress=item)
                    if result.status != "ok":
                        update_failed = True
                except Exception:
                    update_failed = True
                finally:
                    progress_queue.task_done()

        consumer_task = asyncio.create_task(_drain())

        def _report(progress: dict[str, Any]) -> None:
            if not update_failed:
                progress_queue.put_nowait(progress)

        async def _finish() -> None:
            progress_queue.put_nowait(None)
            await progress_queue.join()
            with suppress(Exception):
                await consumer_task

        return _report, _finish

    async def _resolve_job_control_action(self, job_id: str | UUID) -> str | None:
        """读取当前 Job 的控制态，判断是否应暂停或取消。"""
        result = await self._job_service.get_job(job_id)
        if result.status != "ok":
            return None
        job = result.payload.get("job") if isinstance(result.payload, dict) else None
        if not isinstance(job, dict):
            return None
        runtime_state = JobControlState.from_runtime_state(job.get("runtime_state"))
        status = str(job.get("status") or "")
        if status == JobStatus.paused.value or runtime_state.paused:
            return "pause"
        if status == JobStatus.cancelled.value or runtime_state.cancel_requested or bool(job.get("cancel_requested")):
            return "cancel"
        return None

    def supported_job_types(self) -> list[str]:
        """返回当前 Runner 支持的 job type 白名单。"""
        return get_runnable_job_types()

    def _build_manager(self, *, config_path: str | Path) -> tuple[ManagerAgent, Path]:
        """按 config_path 构建 ManagerAgent。"""
        loaded = self._config_loader(config_path)
        base_dir = _project_base_dir(Path(loaded.config_path))
        manager = self._manager_factory(config=loaded.config, base_dir=base_dir)
        return manager, base_dir

    async def _resolve_profile_config_path(self, params: dict[str, Any]) -> str | Path | None:
        """优先按 Profile 解析配置路径，兼容旧的 config_path 入口。"""
        profile_id = str(params.get("profile_id") or "").strip()
        if profile_id:
            resolved = await ConfigProfileService().resolve_profile_config_path(profile_id)
            if resolved is None:
                raise ValueError(f"profile not found: {profile_id}")
            return resolved

        config_path = params.get("config_path")
        if config_path:
            return config_path
        return None

    def _build_default_handlers(self) -> dict[str, Callable[[dict[str, Any]], Awaitable[ServiceResult]]]:
        """构建默认的 Job 处理器集合。"""

        async def _crawl(params: dict[str, Any]) -> ServiceResult:
            service = self._pipeline_service_factory()
            profile_id = str(params.get("profile_id") or "").strip() or None
            config_path = await self._resolve_profile_config_path(params) if profile_id is None else None
            if profile_id is None and config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            return await service.crawl(
                profile_id=profile_id,
                config_path=config_path,
                max_articles=params.get("max_articles"),
                force=_parse_bool(params.get("force"), default=False),
            )

        async def _article_pipeline_context(params: dict[str, Any]) -> tuple[Any, Path, Path]:
            """按 Profile 或 config_path 解析 article pipeline 的运行上下文。"""
            profile_id = str(params.get("profile_id") or "").strip()
            if profile_id:
                runtime = await ConfigProfileService().load_profile_runtime_config(profile_id)
                return runtime.config, runtime.base_dir, Path(f"profile:{profile_id}")
            config_path = await self._resolve_profile_config_path(params)
            if config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            loaded = load_app_config(config_path)
            base_dir = _project_base_dir(Path(loaded.config_path))
            return loaded.config, base_dir, Path(loaded.config_path)

        def _raise_missing_step(step_name: str) -> None:
            raise ValueError(f"请先执行 {step_name}")

        def _check_required_files(paths: list[Path], *, missing_step: str) -> None:
            if not paths or not all(path.exists() for path in paths):
                _raise_missing_step(missing_step)

        async def _clean(params: dict[str, Any]) -> ServiceResult:
            config, base_dir, _loaded_path = await _article_pipeline_context(params)
            force = _parse_bool(params.get("force"), default=False)
            use_db = _parse_bool(params.get("use_db"), default=False)
            max_articles = params.get("max_articles")
            progress_callback = _KAIPAN_PROGRESS_REPORTER.get()
            if use_db:
                result = await run_clean_from_db_task(
                    base_dir=base_dir,
                    force=force,
                    max_articles=max_articles if isinstance(max_articles, int) else None,
                    progress_callback=progress_callback,
                )
            else:
                crawl_paths = discover_crawl_jsonl_paths(base_dir=base_dir, config=config)
                _check_required_files(crawl_paths, missing_step="crawl")
                result = run_clean_task(
                    base_dir=base_dir,
                    input_paths=crawl_paths,
                    force=force,
                    max_articles=max_articles if isinstance(max_articles, int) else None,
                    progress_callback=progress_callback,
                )
            return ServiceResult(status="ok", message="clean completed", payload={"result": _to_plain(result)})

        async def _validate(params: dict[str, Any]) -> ServiceResult:
            _config, base_dir, _loaded_path = await _article_pipeline_context(params)
            force = _parse_bool(params.get("force"), default=False)
            max_articles = params.get("max_articles")
            validate_dir = base_dir / "data" / "processed" / "pipeline" / "validate"
            clean_dir = base_dir / "data" / "processed" / "pipeline" / "clean"
            clean_paths = sorted(clean_dir.glob("*.articles.cleaned.jsonl"))
            _check_required_files(clean_paths, missing_step="clean")
            result = run_validate_task(
                base_dir=base_dir,
                input_paths=clean_paths,
                force=force,
                max_articles=max_articles if isinstance(max_articles, int) else None,
                progress_callback=_KAIPAN_PROGRESS_REPORTER.get(),
            )
            return ServiceResult(status="ok", message="validate completed", payload={"result": _to_plain(result), "validate_dir": str(validate_dir)})

        async def _store(params: dict[str, Any]) -> ServiceResult:
            _config, base_dir, _loaded_path = await _article_pipeline_context(params)
            force = _parse_bool(params.get("force"), default=False)
            validate_dir = base_dir / "data" / "processed" / "pipeline" / "validate"
            validated_paths = sorted(validate_dir.glob("*.validated.jsonl"))
            _check_required_files(validated_paths, missing_step="validate")
            result = await store_articles_jsonl_to_db(
                base_dir=base_dir,
                jsonl_paths=validated_paths,
                pending_tasks_path=default_pending_tasks_path(base_dir=base_dir),
                force=force,
                progress_callback=_KAIPAN_PROGRESS_REPORTER.get(),
            )
            return ServiceResult(status="ok", message="store completed", payload={"result": _to_plain(result)})

        async def _process(params: dict[str, Any]) -> ServiceResult:
            config, base_dir, _loaded_path = await _article_pipeline_context(params)
            force = _parse_bool(params.get("force"), default=False)
            retry_failed = _parse_bool(params.get("retry_failed"), default=False)
            version = str(params.get("new_version") or "v1")
            if force:
                pipeline_dir = base_dir / "data" / "processed" / "pipeline"
                for relative in [
                    "pending_tasks.jsonl",
                    "failed_tasks.jsonl",
                    "dead_tasks.jsonl",
                    "llm_checkpoint.jsonl",
                ]:
                    target = pipeline_dir / relative
                    if target.exists():
                        target.unlink()
            pending_path = default_pending_tasks_path(base_dir=base_dir)
            if not pending_path.exists() and not force:
                _raise_missing_step("store")
            result = await run_process_tasks(
                config=config,
                force=force,
                retry_failed=retry_failed,
                version=version,
                progress_callback=_KAIPAN_PROGRESS_REPORTER.get(),
            )
            return ServiceResult(status="ok", message="process completed", payload={"result": _to_plain(result)})

        async def _kaipan_fetch(params: dict[str, Any]) -> ServiceResult:
            service = KaipanService()
            config_path = await self._resolve_profile_config_path(params)
            if config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            return service.fetch(
                config_path=config_path,
                trade_date=params.get("trade_date"),
                start_date=params.get("start_date"),
                end_date=params.get("end_date"),
                slot=params.get("slot", "all"),
                runtime_state=params.get("__job_runtime_state__"),
                progress_callback=_KAIPAN_PROGRESS_REPORTER.get(),
            )

        async def _kaipan_normalize(params: dict[str, Any]) -> ServiceResult:
            service = KaipanService()
            config_path = await self._resolve_profile_config_path(params)
            if config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            return service.normalize(
                config_path=config_path,
                trade_date=params.get("trade_date"),
                start_date=params.get("start_date"),
                end_date=params.get("end_date"),
                slot=params.get("slot", "all"),
                runtime_state=params.get("__job_runtime_state__"),
                progress_callback=_KAIPAN_PROGRESS_REPORTER.get(),
            )

        async def _kaipan_run(params: dict[str, Any]) -> ServiceResult:
            service = KaipanService()
            config_path = await self._resolve_profile_config_path(params)
            if config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            return service.run(
                config_path=config_path,
                start_scheduler=_parse_bool(params.get("start_scheduler"), default=False),
                block=_parse_bool(params.get("block"), default=False),
            )

        async def _ohlcv_crawl(params: dict[str, Any]) -> ServiceResult:
            service = MarketService()
            profile_id = str(params.get("profile_id") or "").strip() or None
            config_path = await self._resolve_profile_config_path(params) if profile_id is None else None
            if profile_id is None and config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            raw_limit = params.get("limit")
            limit = None if raw_limit in {None, ""} else int(raw_limit)
            return await service.crawl_ohlcv(
                profile_id=profile_id,
                config_path=config_path,
                mode=str(params.get("mode") or "incremental"),
                symbols=params.get("symbols"),
                start_date=_parse_optional_date(params.get("start_date")),
                end_date=_parse_optional_date(params.get("end_date")),
                limit=limit,
                runtime_state=params.get("__job_runtime_state__"),
                progress_callback=_KAIPAN_PROGRESS_REPORTER.get(),
            )

        async def _market_state_build(params: dict[str, Any]) -> ServiceResult:
            service = PersonaService()
            benchmark_symbol = params.get("benchmark_symbol")
            if not benchmark_symbol:
                raise ValueError("missing required param: benchmark_symbol")
            profile_id = str(params.get("profile_id") or "").strip() or None
            config_path = await self._resolve_profile_config_path(params) if profile_id is None else None
            if profile_id is None and config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            return service.build_market_state(
                profile_id=profile_id,
                config_path=config_path,
                benchmark_symbol=benchmark_symbol,
                as_of=params.get("as_of"),
                dest=params.get("dest", "data/processed/persona/market_state.json"),
                from_akshare=_parse_bool(params.get("from_akshare"), default=False),
                cache_csv=_parse_bool(params.get("cache_csv"), default=True),
            )

        async def _snapshot_build(params: dict[str, Any]) -> ServiceResult:
            service = SnapshotService()
            profile_id = str(params.get("profile_id") or "").strip() or None
            config_path = await self._resolve_profile_config_path(params) if profile_id is None else None
            if profile_id is None and config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            return await service.build_snapshot(
                profile_id=profile_id,
                config_path=config_path,
                benchmark_symbol=params.get("benchmark_symbol"),
                date=str(params.get("date") or params.get("trade_date") or date.today().isoformat()) if params.get("start_date") is None else None,
                start_date=str(params.get("start_date")) if params.get("start_date") else None,
                end_date=str(params.get("end_date")) if params.get("end_date") else None,
                slot=str(params.get("slot") or "17-30"),
                force=_parse_bool(params.get("force"), default=False),
                offline=_parse_bool(params.get("offline"), default=False),
                snapshot_type=str(params.get("snapshot_type") or "all"),
                runtime_state=params.get("__job_runtime_state__"),
                progress_callback=_KAIPAN_PROGRESS_REPORTER.get(),
            )

        async def _strategy_build(params: dict[str, Any]) -> ServiceResult:
            service = StrategyService()
            return await service.build_strategy_version(
                config_path=params.get("config_path"),
                profile_id=params.get("profile_id"),
                trader_id=str(params.get("trader_id") or ""),
                strategy_date=str(params.get("strategy_date") or date.today().isoformat()),
                force=_parse_bool(params.get("force"), default=False),
                regime_selection=params.get("regime_selection"),
                snapshot_id=params.get("snapshot_id"),
                market_regime_version=params.get("market_regime_version"),
                source_feature_version=params.get("source_feature_version"),
                applicability_profile_version=params.get("applicability_profile_version"),
                selected_by=params.get("selected_by"),
            )

        async def _backtest_run(params: dict[str, Any]) -> ServiceResult:
            service = self._backtest_service_factory()
            profile_id = str(params.get("profile_id") or "").strip() or None
            benchmark_symbol = params.get("benchmark_symbol")
            config_path = await self._resolve_profile_config_path(params) if profile_id is None else None
            if profile_id is None and config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            if profile_id is not None:
                return await service.run_backtest_profile(
                    profile_id=profile_id,
                    trader_id=str(params.get("trader_id") or ""),
                    date_from=_parse_date(params.get("date_from")),
                    date_to=_parse_date(params.get("date_to")),
                    strategy_version_id=params.get("strategy_version_id"),
                    symbols=params.get("symbols") or [],
                    benchmark_symbol=benchmark_symbol,
                    mode=str(params.get("mode") or "full"),
                    use_snapshot_only=_parse_bool(params.get("use_snapshot_only"), default=True),
                    scoring_profile=str(params.get("scoring_profile") or "stage5"),
                    runtime_state=params.get("__job_runtime_state__"),
                    progress_callback=_KAIPAN_PROGRESS_REPORTER.get(),
                )
            return service.run_backtest(
                trader_id=str(params.get("trader_id") or ""),
                date_from=_parse_date(params.get("date_from")),
                date_to=_parse_date(params.get("date_to")),
                strategy_version_id=params.get("strategy_version_id"),
                symbols=params.get("symbols") or [],
                benchmark_symbol=benchmark_symbol,
                mode=str(params.get("mode") or "full"),
                config_path=config_path,
                use_snapshot_only=_parse_bool(params.get("use_snapshot_only"), default=True),
                scoring_profile=str(params.get("scoring_profile") or "stage5"),
                runtime_state=params.get("__job_runtime_state__"),
                progress_callback=_KAIPAN_PROGRESS_REPORTER.get(),
            )

        async def _backtest_validate_rules(params: dict[str, Any]) -> ServiceResult:
            service = self._backtest_service_factory()
            benchmark_symbol = params.get("benchmark_symbol")
            profile_id = str(params.get("profile_id") or "").strip() or None
            config_path = await self._resolve_profile_config_path(params) if profile_id is None else None
            if profile_id is None and config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            if profile_id is not None:
                return await service.validate_rules(
                    profile_id=profile_id,
                    trader_id=str(params.get("trader_id") or ""),
                    date_from=_parse_date(params.get("date_from")),
                    date_to=_parse_date(params.get("date_to")),
                    strategy_version_id=params.get("strategy_version_id"),
                    symbols=params.get("symbols") or [],
                    benchmark_symbol=benchmark_symbol,
                    mode=str(params.get("mode") or "rule_validation"),
                    use_snapshot_only=_parse_bool(params.get("use_snapshot_only"), default=True),
                    scoring_profile=str(params.get("scoring_profile") or "stage5"),
                    runtime_state=params.get("__job_runtime_state__"),
                    progress_callback=_KAIPAN_PROGRESS_REPORTER.get(),
                )
            return await service.validate_rules(
                trader_id=str(params.get("trader_id") or ""),
                date_from=_parse_date(params.get("date_from")),
                date_to=_parse_date(params.get("date_to")),
                strategy_version_id=params.get("strategy_version_id"),
                symbols=params.get("symbols") or [],
                benchmark_symbol=benchmark_symbol,
                mode=str(params.get("mode") or "rule_validation"),
                config_path=config_path,
                use_snapshot_only=_parse_bool(params.get("use_snapshot_only"), default=True),
                scoring_profile=str(params.get("scoring_profile") or "stage5"),
                runtime_state=params.get("__job_runtime_state__"),
                progress_callback=_KAIPAN_PROGRESS_REPORTER.get(),
            )

        async def _backtest_reproducibility_check(params: dict[str, Any]) -> ServiceResult:
            service = self._backtest_service_factory()
            benchmark_symbol = params.get("benchmark_symbol")
            profile_id = str(params.get("profile_id") or "").strip() or None
            config_path = await self._resolve_profile_config_path(params) if profile_id is None else None
            if profile_id is None and config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            if profile_id is not None:
                return await service.reproducibility_check_profile(
                    profile_id=profile_id,
                    trader_id=str(params.get("trader_id") or ""),
                    date_from=_parse_date(params.get("date_from")),
                    date_to=_parse_date(params.get("date_to")),
                    strategy_version_id=params.get("strategy_version_id"),
                    symbols=params.get("symbols") or [],
                    benchmark_symbol=benchmark_symbol,
                    mode=str(params.get("mode") or "full"),
                    use_snapshot_only=_parse_bool(params.get("use_snapshot_only"), default=True),
                    scoring_profile=str(params.get("scoring_profile") or "stage5"),
                )
            return service.reproducibility_check(
                trader_id=str(params.get("trader_id") or ""),
                date_from=_parse_date(params.get("date_from")),
                date_to=_parse_date(params.get("date_to")),
                strategy_version_id=params.get("strategy_version_id"),
                symbols=params.get("symbols") or [],
                benchmark_symbol=benchmark_symbol,
                mode=str(params.get("mode") or "full"),
                config_path=config_path,
                use_snapshot_only=_parse_bool(params.get("use_snapshot_only"), default=True),
                scoring_profile=str(params.get("scoring_profile") or "stage5"),
            )

        async def _candidate_review(params: dict[str, Any]) -> ServiceResult:
            service = OptimizeService()
            return await service.review_candidate(
                candidate_version_id=str(params.get("candidate_version_id") or ""),
                decision=str(params.get("decision") or "pending"),
                reviewed_by=str(params.get("reviewed_by") or "web"),
                force=_parse_bool(params.get("force"), default=False),
            )

        async def _rule_pool_backtest(params: dict[str, Any]) -> ServiceResult:
            service = self._backtest_service_factory()
            rule_id = str(params.get("rule_id") or "").strip()
            rule_ids = [rule_id] if rule_id else None
            start_date = _parse_optional_date(params.get("start_date"))
            end_date = _parse_optional_date(params.get("end_date"))
            if start_date is None or end_date is None:
                raise ValueError("missing required param: start_date/end_date")
            profile_id = str(params.get("profile_id") or "").strip() or None
            config_path = await self._resolve_profile_config_path(params) if profile_id is None else None
            if profile_id is None and config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            return await service.run_rule_pool_backtest(
                start_date=start_date,
                end_date=end_date,
                rule_ids=rule_ids,
                min_confidence=float(params.get("min_confidence") or 0.5),
                market_regime_version=params.get("market_regime_version") or "market-regime-v3",
                profile_id=profile_id,
                config_path=config_path,
                runtime_state=params.get("__job_runtime_state__"),
                progress_callback=_KAIPAN_PROGRESS_REPORTER.get(),
            )

        async def _run_pre_market(params: dict[str, Any]) -> ServiceResult:
            config_path = await self._resolve_profile_config_path(params)
            if config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            manager, _ = self._build_manager(config_path=config_path)
            service = RunService(manager)
            return await service.run_pre_market(
                as_of_date=_parse_date(params.get("as_of_date")),
                force=_parse_bool(params.get("force"), default=False),
                export_html=_parse_bool(params.get("export_html"), default=False),
            )

        async def _run_after_close(params: dict[str, Any]) -> ServiceResult:
            config_path = await self._resolve_profile_config_path(params)
            if config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            manager, _ = self._build_manager(config_path=config_path)
            service = RunService(manager)
            return await service.run_after_close(
                as_of_date=_parse_date(params.get("as_of_date")),
                force=_parse_bool(params.get("force"), default=False),
                export_html=_parse_bool(params.get("export_html"), default=False),
            )

        async def _pipeline_run(params: dict[str, Any]) -> ServiceResult:
            service = self._pipeline_service_factory()
            profile_id = str(params.get("profile_id") or "").strip() or None
            config_path = await self._resolve_profile_config_path(params) if profile_id is None else None
            if profile_id is None and config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            return await service.run_pipeline(
                profile_id=profile_id,
                config_path=config_path,
                max_articles=params.get("max_articles"),
                force=_parse_bool(params.get("force"), default=False),
                skip_crawl=_parse_bool(params.get("skip_crawl"), default=False),
                from_step=params.get("from_step"),
                use_db=_parse_bool(params.get("use_db"), default=False),
                retry_failed=_parse_bool(params.get("retry_failed"), default=False),
                new_version=params.get("new_version"),
                progress_callback=_KAIPAN_PROGRESS_REPORTER.get(),
            )

        async def _pipeline_step(params: dict[str, Any]) -> ServiceResult:
            service = self._pipeline_service_factory()
            profile_id = str(params.get("profile_id") or "").strip() or None
            config_path = await self._resolve_profile_config_path(params) if profile_id is None else None
            if profile_id is None and config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            return await service.run_pipeline_step(
                step=params.get("step", "crawl"),
                profile_id=profile_id,
                config_path=config_path,
                max_articles=params.get("max_articles"),
                force=_parse_bool(params.get("force"), default=False),
                use_db=_parse_bool(params.get("use_db"), default=False),
                retry_failed=_parse_bool(params.get("retry_failed"), default=False),
                new_version=params.get("new_version"),
                progress_callback=_KAIPAN_PROGRESS_REPORTER.get(),
            )

        async def _backup_data(params: dict[str, Any]) -> ServiceResult:
            service = OpsRecoveryService()
            profile_id = str(params.get("profile_id") or "").strip()
            if not profile_id:
                raise ValueError("missing required param: profile_id")
            return await service.create_backup(
                profile_id=profile_id,
                include_processed=_parse_bool(params.get("include_processed"), default=True),
                backup_dir=params.get("backup_dir"),
                backup_dir_id=params.get("backup_dir_id"),
            )

        async def _restore_data(params: dict[str, Any]) -> ServiceResult:
            service = OpsRecoveryService()
            profile_id = str(params.get("profile_id") or "").strip()
            if not profile_id:
                raise ValueError("missing required param: profile_id")
            backup_id = str(params.get("backup_id") or "").strip() or None
            backup_dir = params.get("backup_dir")
            if backup_id is None and not backup_dir:
                raise ValueError("missing required param: backup_id/backup_dir")
            return await service.restore_backup(
                profile_id=profile_id,
                backup_id=backup_id,
                backup_path=backup_dir,
                include_processed=_parse_bool(params.get("include_processed"), default=True),
                confirmed=_parse_bool(params.get("force"), default=False),
            )

        return {
            "crawl": _crawl,
            "clean": _clean,
            "validate": _validate,
            "store": _store,
            "process": _process,
            "run-pre-market": _run_pre_market,
            "run-after-close": _run_after_close,
            "pipeline-run": _pipeline_run,
            "pipeline-step": _pipeline_step,
            "backup-data": _backup_data,
            "restore-data": _restore_data,
            "kaipan-fetch": _kaipan_fetch,
            "kaipan-normalize": _kaipan_normalize,
            "kaipan-run": _kaipan_run,
            "ohlcv-crawl": _ohlcv_crawl,
            "market-state-build": _market_state_build,
            "snapshot-build": _snapshot_build,
            "strategy-build": _strategy_build,
            "backtest-run": _backtest_run,
            "backtest-validate-rules": _backtest_validate_rules,
            "backtest-reproducibility-check": _backtest_reproducibility_check,
            "rule-pool-backtest": _rule_pool_backtest,
            "candidate-review": _candidate_review,
        }

    def _classify_error(self, *, job_type: str, message: str, payload: dict[str, Any] | None = None) -> tuple[str, str | None, bool]:
        """把 handler 失败原因收敛为可展示的错误分类。"""
        text = " ".join(
            [
                job_type.lower(),
                message.lower(),
                str(_to_plain(payload or {})).lower(),
            ]
        )
        if any(token in text for token in ("permission denied", "unauthorized", "forbidden")):
            return "permission", "permission_denied", False
        if any(token in text for token in ("provider unavailable", "akshare", "network", "timeout", "connection", "http", "fetch failed")):
            return "external_dependency", "provider_unavailable", True
        if any(token in text for token in ("config", "missing required param", "not set", "invalid slot", "invalid date", "must be provided", "must be")):
            return "user_error", "config_missing", False
        if any(token in text for token in ("empty", "invalid", "malformed", "parse", "format")):
            return "user_error", "data_invalid", False
        return "system_error", "system_error", True

    async def _bind_result_artifacts(
        self,
        *,
        job_id: str | UUID,
        job_dir: Path,
        job_type: str,
        result_payload: dict[str, Any],
    ) -> None:
        """把 handler 返回中的文件路径自动收敛为 Job artifact。"""
        payload = result_payload.get("payload")
        if not isinstance(payload, dict):
            return

        artifact_specs: list[tuple[str, str, Any]] = []
        if payload.get("html_path"):
            artifact_specs.append(("html", "HTML 报告", payload["html_path"]))
        if payload.get("market_state_path"):
            artifact_specs.append(("market-state-json", "市场状态 JSON", payload["market_state_path"]))
        if payload.get("snapshot_path"):
            artifact_specs.append(("snapshot-json", "市场快照 JSON", payload["snapshot_path"]))
        if payload.get("snapshot_summary_path"):
            artifact_specs.append(("snapshot-summary-json", "市场快照摘要 JSON", payload["snapshot_summary_path"]))
        if payload.get("quality_report_path"):
            artifact_specs.append(("snapshot-quality-json", "市场快照质量报告 JSON", payload["quality_report_path"]))
        snapshot_paths = payload.get("snapshot_paths")
        if isinstance(snapshot_paths, list):
            artifact_specs.extend(("snapshot-json", "市场快照 JSON", item) for item in snapshot_paths if item)

        if job_type in {"backtest-run", "rule-pool-backtest"} and "result" in payload:
            backtest_service = self._backtest_service_factory()
            report_content = backtest_service.render_backtest_report(payload["result"], format="markdown").payload["content"]
            csv_content = backtest_service.render_backtest_report(payload["result"], format="csv").payload["content"]
            report_path = job_dir / "backtest_report.md"
            csv_path = job_dir / "backtest_records.csv"
            report_path.write_text(report_content, encoding="utf-8")
            csv_path.write_text(csv_content, encoding="utf-8")
            artifact_specs.append(("report-markdown", "回测报告", report_path))
            artifact_specs.append(("records-csv", "回测交易记录", csv_path))
        elif job_type == "backtest-validate-rules" and "report" in payload:
            report_path = job_dir / "backtest_validation_report.md"
            report_path.write_text(str(payload["report"]), encoding="utf-8")
            artifact_specs.append(("validation-report-markdown", "规则验真报告", report_path))
        if job_type == "candidate-review" and "report" in payload:
            report_path = job_dir / "candidate_review_report.md"
            report_path.write_text(str(payload["report"]), encoding="utf-8")
            artifact_specs.append(("review-report-markdown", "候选审核报告", report_path))
        if job_type == "candidate-review" and "audit_log" in payload:
            audit_path = job_dir / "candidate_review_audit.json"
            audit_path.write_text(json.dumps(payload["audit_log"], ensure_ascii=False, indent=2), encoding="utf-8")
            artifact_specs.append(("audit-log-json", "候选审核审计", audit_path))

        for kind, title, path in artifact_specs:
            await self._job_service.bind_artifact(
                job_id=job_id,
                kind=kind,
                path=path,
                title=title,
                metadata={"job_type": job_type, "source": "job_result"},
            )

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
        params["__job_runtime_state__"] = job_payload.get("runtime_state")
        progress_reporter: Callable[[dict[str, Any]], None] | None = None
        progress_finish: Callable[[], Awaitable[None]] | None = None
        progress_token = None
        control_event = asyncio.Event()
        control_state: dict[str, str | None] = {"action": None}
        control_poll_interval = max(0.5, min(self._heartbeat_interval_seconds, 2.0))
        if job_payload["job_type"] in {
            "kaipan-fetch",
            "kaipan-normalize",
            "ohlcv-crawl",
            "snapshot-build",
            "clean",
            "validate",
            "store",
            "process",
            "pipeline-run",
            "pipeline-step",
            "backtest-run",
            "backtest-validate-rules",
            "rule-pool-backtest",
        }:
            progress_reporter, progress_finish = self._create_progress_tracker(job_id=job_id)

        async def _finish_progress() -> None:
            if progress_finish is not None:
                await progress_finish()

        async def _resolve_and_handle_control(action: str) -> ServiceResult:
            await _finish_progress()
            current = await self._job_service.get_job(job_id)
            if action == "cancel":
                if current.status == "ok" and isinstance(current.payload, dict):
                    current_job = current.payload.get("job")
                    if isinstance(current_job, dict) and current_job.get("status") == JobStatus.cancelled.value:
                        logger.info("job control resolved action=cancel status=cancelled")
                        return ServiceResult(status="ok", message="job cancelled", payload={"job": current_job})
                completed = await self._job_service.complete_job(job_id=job_id, result={})
                logger.info("job control resolved action=cancel status=cancelled")
                return ServiceResult(status="ok", message="job cancelled", payload={"job": completed.payload.get("job")})
            if current.status == "ok" and isinstance(current.payload, dict) and isinstance(current.payload.get("job"), dict):
                logger.info("job control resolved action=%s status=paused", action)
                return ServiceResult(status="ok", message="job paused", payload={"job": current.payload["job"]})
            logger.info("job control resolved action=%s status=paused", action)
            return ServiceResult(status="ok", message="job paused", payload={"job": job_payload})

        async def _monitor_control_state() -> None:
            try:
                while True:
                    await asyncio.sleep(control_poll_interval)
                    action = await self._resolve_job_control_action(job_id)
                    if action is not None:
                        control_state["action"] = action
                        control_event.set()
                        return
            except asyncio.CancelledError:
                raise

        control_task = asyncio.create_task(_monitor_control_state())

        def _report_progress(progress: dict[str, Any]) -> None:
            if control_event.is_set():
                raise JobControlInterrupted(control_state["action"] or "pause")
            if progress_reporter is not None:
                progress_reporter(progress)

        if progress_reporter is not None:
            progress_token = _KAIPAN_PROGRESS_REPORTER.set(_report_progress)

        with bind_log_context(
            job_id=str(job_id),
            job_type=str(job_payload.get("job_type") or "-"),
            profile_id=str(params.get("profile_id")) if params.get("profile_id") else None,
            config_path=str(params.get("config_path")) if params.get("config_path") else None,
        ):
            try:
                logger.info("job execution started")
                initial_control_action = await self._resolve_job_control_action(job_id)
                if initial_control_action is not None:
                    return await _resolve_and_handle_control(initial_control_action)
                result = await handler(params)
                current_control_action = await self._resolve_job_control_action(job_id)
                if current_control_action is not None:
                    return await _resolve_and_handle_control(current_control_action)
                await _finish_progress()
                result_payload = _to_plain(result.model_dump(mode="json"))
                if job_payload["job_type"] in {"crawl", "clean", "validate", "store", "process", "pipeline-run", "pipeline-step"}:
                    has_profile_context = bool(params.get("profile_id")) and not bool(params.get("config_path"))
                    if has_profile_context:
                        result_payload = _strip_keys_recursive(result_payload, {"config_path"})
                public_result_payload = _sanitize_result_payload_for_output(result_payload)
                result_path = await self._write_result_file(job_dir=job_dir, payload=public_result_payload)
                await self._job_service.bind_artifact(
                    job_id=job_id,
                    kind="result-json",
                    path=result_path,
                    metadata={"job_type": job_payload["job_type"]},
                )
                await self._bind_result_artifacts(
                    job_id=job_id,
                    job_dir=job_dir,
                    job_type=job_payload["job_type"],
                    result_payload=result_payload,
                )
                if result.status == "error":
                    error_type, error_code, retryable = self._classify_error(
                        job_type=job_payload["job_type"],
                        message=result.message or "job handler returned error",
                        payload=result_payload,
                    )
                    failed = await self._job_service.fail_job(
                        job_id=job_id,
                        error={
                            "type": error_type,
                            "message": result.message or "job handler returned error",
                            "code": error_code,
                            "retryable": retryable,
                            "result": result_payload,
                        },
                    )
                    return ServiceResult(
                        status="error",
                        message="job execution failed",
                        payload={"job": failed.payload.get("job"), "result": public_result_payload, "result_path": result_path.name},
                    )

                completed = await self._job_service.complete_job(job_id=job_id, result=result_payload)
                await self._job_service.append_log(
                    job_id=job_id,
                    line=f"[runner] completed job_type={job_payload['job_type']} status={result.status}",
                )
                logger.info("job execution completed status=%s", result.status)
                return ServiceResult(
                    status="ok",
                    message="job executed",
                    payload={
                        "job": completed.payload["job"],
                        "result": public_result_payload,
                        "result_path": result_path.name,
                    },
                )
            except JobControlInterrupted as exc:
                logger.info("job execution interrupted control_action=%s", exc.control_action)
                return await _resolve_and_handle_control(exc.control_action)
            except Exception as exc:  # noqa: BLE001
                with suppress(Exception):
                    await _finish_progress()
                logger.exception(
                    "job execution failed job_type=%s error=%s",
                    job_payload["job_type"],
                    exc,
                )
                await self._job_service.append_log(job_id=job_id, line=f"[runner] failed: {exc}")
                error_type, error_code, retryable = self._classify_error(
                    job_type=job_payload["job_type"],
                    message=str(exc),
                )
                failed = await self._job_service.fail_job(
                    job_id=job_id,
                    error={"type": error_type, "message": str(exc), "code": error_code, "retryable": retryable},
                )
                return ServiceResult(
                    status="error",
                    message="job execution failed",
                    payload={"job": failed.payload.get("job"), "error": str(exc)},
                )
            finally:
                if progress_token is not None:
                    _KAIPAN_PROGRESS_REPORTER.reset(progress_token)
                control_task.cancel()
                with suppress(asyncio.CancelledError):
                    await control_task
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
        confirmed: bool = False,
    ) -> ServiceResult:
        """创建并立即执行 Job。"""
        validated = validate_job_submission(job_type=job_type, params=params or {}, created_by=created_by, confirmed=confirmed)
        if validated.status != "ok":
            return validated
        created = await self._job_service.create_job(
            job_type=job_type,
            params=validated.payload["params"],
            created_by=created_by,
            idempotency_key=idempotency_key,
            confirmed=confirmed,
        )
        job_payload = created.payload.get("job") if isinstance(created.payload, dict) else None
        if not isinstance(job_payload, dict):
            return created
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

    async def recover_stale_jobs(
        self,
        *,
        stale_before: datetime,
        actor: str | None = None,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """回收 stale 的 running Job，并标记哪些任务仍然可重试。"""
        recovered = await self._job_service.recover_stale_jobs(stale_before=stale_before, actor=actor, audit_source=audit_source)
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
