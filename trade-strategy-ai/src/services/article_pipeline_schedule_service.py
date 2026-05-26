from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.services.base import BaseService, ServiceResult
from src.services.config_profile_service import ConfigProfileService
from src.services.job_service import JobService
from src.services.pipeline_application_service import ARTICLE_PIPELINE_ID, PipelineApplicationService, make_pipeline_application_service


def _to_plain(value: Any) -> Any:
    """把 dataclass / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


@dataclass(frozen=True)
class ArticlePipelineScheduleSnapshot:
    """文章 Pipeline 调度状态快照。"""

    scheduler_started: bool
    schedule_time: str | None
    force: bool
    profile_id: str | None
    config_path: str | None


class ArticlePipelineScheduleService(BaseService):
    """文章工作台的全量日程调度服务。"""

    service_name = "article-pipeline-schedule"
    _scheduler_lock = Lock()
    _scheduler: BackgroundScheduler | None = None
    _schedule_time: str | None = None
    _profile_id: str | None = None
    _config_path: Path | None = None
    _force: bool = False

    def __init__(
        self,
        *,
        job_service: JobService | None = None,
        pipeline_application_service: PipelineApplicationService | None = None,
    ) -> None:
        self._job_service = job_service or JobService()
        self._pipeline_application_service = pipeline_application_service or make_pipeline_application_service(job_service=self._job_service)

    @classmethod
    def _snapshot(cls) -> ArticlePipelineScheduleSnapshot:
        """读取当前 scheduler 的内存状态。"""
        with cls._scheduler_lock:
            scheduler = cls._scheduler
            started = scheduler is not None
            if not started and scheduler is not None:
                cls._scheduler = None
                cls._schedule_time = None
                cls._config_path = None
                cls._force = False
            return ArticlePipelineScheduleSnapshot(
                scheduler_started=started,
                schedule_time=cls._schedule_time,
                force=cls._force,
                profile_id=cls._profile_id,
                config_path=str(cls._config_path) if cls._config_path is not None else None,
            )

    @classmethod
    def _clear_scheduler(cls) -> None:
        """停止并清理当前 scheduler。"""
        with cls._scheduler_lock:
            scheduler = cls._scheduler
            cls._scheduler = None
            cls._schedule_time = None
            cls._force = False
        if scheduler is not None:
            scheduler.shutdown(wait=False)

    @staticmethod
    def _parse_schedule_time(schedule_time: str) -> tuple[int, int]:
        """解析 HH:MM 形式的调度时间。"""
        try:
            hour_str, minute_str = schedule_time.split(":", 1)
            hour = int(hour_str)
            minute = int(minute_str)
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError("schedule_time must be HH:MM") from exc
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError("schedule_time must be HH:MM")
        return hour, minute

    async def _has_completed_today(self, *, schedule_date: date) -> bool:
        """检查当天是否已经有成功的 article pipeline 全量任务。"""
        skip = 0
        page_size = 200
        while True:
            result = await self._job_service.list_jobs(status="success", job_type="pipeline-run", skip=skip, limit=page_size)
            if result.status != "ok":
                return False

            items = result.payload.get("items", []) if isinstance(result.payload, dict) else []
            if not items:
                return False

            for item in items:
                created_at = str(item.get("created_at") or "")
                if not created_at:
                    continue
                try:
                    created_day = datetime.fromisoformat(created_at).date()
                except ValueError:
                    continue
                if created_day == schedule_date:
                    return True

            if len(items) < page_size:
                return False
            skip += page_size
        return False

    async def run_scheduled_pipeline(
        self,
        *,
        profile_id: str | None = None,
        config_path: str | Path | None = None,
        force: bool = False,
        schedule_date: date | str | None = None,
    ) -> ServiceResult:
        """执行当天的 article_pipeline 全量任务。"""
        if schedule_date is None:
            target_date = date.today()
        elif isinstance(schedule_date, date):
            target_date = schedule_date
        else:
            target_date = date.fromisoformat(schedule_date)

        if await self._has_completed_today(schedule_date=target_date) and not force:
            return ServiceResult(
                status="ok",
                message="already completed",
                payload={
                    "message": "already completed",
                    "schedule_date": target_date.isoformat(),
                    "profile_id": profile_id,
                    "config_path": str(config_path) if config_path is not None else None,
                    "force": force,
                    "pipeline_id": ARTICLE_PIPELINE_ID,
                },
            )

        params: dict[str, Any] = {"force": force}
        if profile_id:
            params["profile_id"] = profile_id
        elif config_path is not None:
            params["config_path"] = str(config_path)
        else:
            params["config_path"] = "config/app.yaml"

        result = await self._pipeline_application_service.run_pipeline(
            pipeline_id=ARTICLE_PIPELINE_ID,
            params=params,
            created_by="article-schedule",
            confirmed=False,
            audit_source={"channel": "scheduler", "schedule_date": target_date.isoformat()},
        )
        payload = dict(result.payload)
        payload["schedule_date"] = target_date.isoformat()
        payload["profile_id"] = profile_id
        if config_path is not None:
            payload["config_path"] = str(config_path)
        payload["force"] = force
        return ServiceResult(status=result.status, message=result.message, payload=payload, warnings=result.warnings)

    async def start(
        self,
        *,
        profile_id: str | None = None,
        config_path: str | Path | None = None,
        schedule_time: str,
        force: bool = False,
    ) -> ServiceResult:
        """启动每日调度器。"""
        hour, minute = self._parse_schedule_time(schedule_time)

        if profile_id:
            resolved = await ConfigProfileService().resolve_profile_config_path(profile_id)
            if resolved is None:
                raise ValueError(f"profile not found: {profile_id}")
            config_path = resolved
        elif config_path is None:
            config_path = "config/app.yaml"

        self._clear_scheduler()

        scheduler = BackgroundScheduler()

        def _run_job() -> None:
            import asyncio

            asyncio.run(self.run_scheduled_pipeline(profile_id=profile_id, config_path=config_path, force=force))

        scheduler.add_job(
            _run_job,
            CronTrigger(hour=hour, minute=minute, second=0),
            id="article_pipeline_daily",
            replace_existing=True,
        )
        scheduler.start()

        with self._scheduler_lock:
            cls = type(self)
            cls._scheduler = scheduler
            cls._schedule_time = schedule_time
            cls._profile_id = profile_id
            cls._config_path = Path(config_path) if config_path is not None else None
            cls._force = force

        return ServiceResult(
            status="ok",
            message="scheduler started",
            payload=_to_plain(
                {
                    "scheduler_started": True,
                    "schedule_time": schedule_time,
                    "profile_id": profile_id,
                    "config_path": str(config_path),
                    "force": force,
                }
            ),
        )

    async def stop(self, *, profile_id: str | None = None, config_path: str | Path | None = None) -> ServiceResult:
        """停止调度器。"""
        snapshot = self._snapshot()
        current_config_path = snapshot.config_path or (str(config_path) if config_path is not None else None)
        current_profile_id = snapshot.profile_id or profile_id
        if not snapshot.scheduler_started:
            return ServiceResult(
                status="ok",
                message="scheduler stopped",
                payload=_to_plain(
                    {
                        "scheduler_started": False,
                        "schedule_time": snapshot.schedule_time,
                        "profile_id": current_profile_id,
                        "config_path": current_config_path,
                        "force": snapshot.force,
                    }
                ),
            )

        self._clear_scheduler()
        return ServiceResult(
            status="ok",
            message="scheduler stopped",
            payload=_to_plain(
                {
                    "scheduler_started": False,
                    "schedule_time": snapshot.schedule_time,
                    "profile_id": current_profile_id,
                    "config_path": current_config_path,
                    "force": snapshot.force,
                }
            ),
        )

    async def status(self, *, profile_id: str | None = None, config_path: str | Path | None = None) -> ServiceResult:
        """查询调度器状态。"""
        snapshot = self._snapshot()
        current_config_path = snapshot.config_path or (str(config_path) if config_path is not None else None)
        current_profile_id = snapshot.profile_id or profile_id
        payload = _to_plain(
            {
                "scheduler_started": snapshot.scheduler_started,
                "schedule_time": snapshot.schedule_time,
                "profile_id": current_profile_id,
                "config_path": current_config_path,
                "force": snapshot.force,
            }
        )
        return ServiceResult(status="ok", message="scheduler status", payload=payload)


def make_article_pipeline_schedule_service(
    *,
    job_service: JobService | None = None,
    pipeline_application_service: PipelineApplicationService | None = None,
) -> ArticlePipelineScheduleService:
    """工厂函数，方便 API 依赖注入。"""
    return ArticlePipelineScheduleService(job_service=job_service, pipeline_application_service=pipeline_application_service)
