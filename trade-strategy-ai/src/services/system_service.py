from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from src.common.config import load_app_config
from src.health.db_checker import DatabaseHealthChecker
from src.health.service import HealthCheckService
from src.services.dashboard_service import DashboardService
from src.services.base import BaseService, ServiceResult
from src.services.job_service import JobService


def _to_plain(value: Any) -> Any:
    """把 dataclass / 枚举 / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if is_dataclass(value):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


class SystemService(BaseService):
    """系统与环境相关服务的占位基类。

    后续用于统一承载数据库检查、迁移、目录检查与调度状态查询。
    """

    service_name = "system"

    def __init__(
        self,
        db_checker: DatabaseHealthChecker | None = None,
        health_service: HealthCheckService | None = None,
        job_service: JobService | None = None,
        dashboard_service: DashboardService | None = None,
    ) -> None:
        self._db_checker = db_checker or DatabaseHealthChecker()
        self._health_service = health_service or HealthCheckService(db_checker=self._db_checker)
        self._job_service = job_service or JobService()
        self._dashboard_service = dashboard_service or DashboardService()

    async def check_database(self) -> ServiceResult:
        """检查数据库连接状态。"""
        check = await self._db_checker.check()
        ok = check.status.value == "ok"
        return ServiceResult(
            status="ok" if ok else "error",
            message="database ok" if ok else "database failed",
            payload={"database": asdict(check)},
        )

    def check_key_directories(self, config_path: str | Path) -> ServiceResult:
        """检查配置相关的关键目录是否存在。"""
        loaded = load_app_config(config_path)
        config_file = Path(config_path).expanduser().resolve()
        base_dir = config_file.parent.parent if config_file.parent.name == "config" else config_file.parent

        directory_specs: dict[str, Path] = {
            "data": base_dir / "data",
            "logs": base_dir / "logs",
            "storage.output_dir": base_dir / loaded.config.storage.output_dir,
            "data.market_data_cache_dir": base_dir / loaded.config.data.market_data_cache_dir,
            "data.market_universe_snapshot_dir": base_dir / loaded.config.data.market_universe_snapshot_dir,
        }

        directories: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        for name, directory in directory_specs.items():
            exists = directory.exists()
            directories[name] = {"path": str(directory), "exists": exists}
            if not exists:
                missing.append(name)

        status = "ok" if not missing else "partial"
        message = "directories ok" if not missing else "some directories are missing"
        return ServiceResult(
            status=status,
            message=message,
            payload={
                "base_dir": str(base_dir),
                "config_path": str(config_file),
                "directories": directories,
            },
            warnings=missing,
        )

    async def build_dashboard_summary(
        self,
        *,
        config_path: str | Path = Path("config/app.yaml"),
    ) -> ServiceResult:
        """构建运维 Dashboard 摘要。"""
        loaded = load_app_config(config_path)
        detailed = await self._health_service.check_detailed()
        failed_jobs_result = await self._job_service.list_jobs(status="failed", limit=10)
        running_jobs_result = await self._job_service.list_jobs(status="running", limit=10)
        success_jobs_result = await self._job_service.list_jobs(status="success", limit=20)
        dashboard_report_result = await self._dashboard_service.build_report(
            config_path=loaded.config_path,
            mode="cli",
        )

        failed_jobs = list(failed_jobs_result.payload.get("items", [])) if failed_jobs_result.status == "ok" else []
        running_jobs = list(running_jobs_result.payload.get("items", [])) if running_jobs_result.status == "ok" else []
        success_jobs = list(success_jobs_result.payload.get("items", [])) if success_jobs_result.status == "ok" else []
        report = dashboard_report_result.payload.get("report", {}) if dashboard_report_result.status == "ok" else {}

        failed_job_entries = [self._build_failed_job_entry(job) for job in failed_jobs]
        running_job_entry = self._build_worker_entry(running_jobs)
        duration_summary = self._build_duration_summary(success_jobs)
        freshness_summary = self._build_freshness_summary(report)
        alerts_summary = self._build_alert_summary(report)
        trace_entries = [entry for entry in (self._build_trace_entry(job) for job in failed_jobs) if entry is not None]

        overall_status = str(getattr(detailed.status, "value", detailed.status))
        status = "ok"
        if overall_status != "healthy" or failed_job_entries or alerts_summary["critical"] > 0:
            status = "partial"

        health_payload = {
            "overall": overall_status,
            "issues": list(detailed.issues),
        }
        health_payload.update({name: _to_plain(component) for name, component in detailed.components.items()})

        return ServiceResult(
            status=status,
            message="dashboard summary built",
            payload={
                "status": status,
                "generated_at": datetime.now(UTC).isoformat(),
                "config_path": str(loaded.config_path),
                "health": health_payload,
                "worker": running_job_entry,
                "failed_jobs": failed_job_entries,
                "duration_summary": duration_summary,
                "freshness": freshness_summary,
                "alerts": alerts_summary,
                "traces": trace_entries,
                "report": _to_plain(report),
            },
        )

    def _build_failed_job_entry(self, job: dict[str, Any]) -> dict[str, Any]:
        """把失败 Job 转成 Dashboard 展示结构。"""
        started_at = self._parse_dt(job.get("started_at"))
        finished_at = self._parse_dt(job.get("finished_at"))
        duration_seconds = None
        if started_at is not None and finished_at is not None:
            duration_seconds = round((finished_at - started_at).total_seconds(), 2)
        error_value = job.get("error")
        error_message = None
        if isinstance(error_value, dict):
            error_message = str(error_value.get("message") or error_value.get("error") or error_value)
        elif error_value is not None:
            error_message = str(error_value)

        return {
            "id": str(job.get("id")),
            "job_type": job.get("job_type"),
            "status": job.get("status"),
            "started_at": job.get("started_at"),
            "finished_at": job.get("finished_at"),
            "duration_seconds": duration_seconds,
            "error_message": error_message,
            "heartbeat_at": job.get("heartbeat_at"),
        }

    def _build_worker_entry(self, running_jobs: list[dict[str, Any]]) -> dict[str, Any]:
        """从运行中 Job 推断 Worker 心跳摘要。"""
        if not running_jobs:
            return {
                "status": "warning",
                "heartbeat_at": None,
                "heartbeat_age_minutes": None,
                "current_job_id": None,
            }

        current = running_jobs[0]
        heartbeat_at = self._parse_dt(current.get("heartbeat_at"))
        heartbeat_age_minutes = None
        if heartbeat_at is not None:
            heartbeat_age_minutes = round((datetime.now(UTC) - heartbeat_at).total_seconds() / 60.0, 2)
        status = "ok"
        if heartbeat_age_minutes is not None and heartbeat_age_minutes > 10:
            status = "warning"

        return {
            "status": status,
            "heartbeat_at": current.get("heartbeat_at"),
            "heartbeat_age_minutes": heartbeat_age_minutes,
            "current_job_id": current.get("id"),
        }

    def _build_duration_summary(self, success_jobs: list[dict[str, Any]]) -> dict[str, Any]:
        """汇总最近成功 Job 的耗时统计。"""
        recent_jobs: list[dict[str, Any]] = []
        durations: list[float] = []
        for job in success_jobs:
            started_at = self._parse_dt(job.get("started_at"))
            finished_at = self._parse_dt(job.get("finished_at"))
            duration_seconds = None
            if started_at is not None and finished_at is not None:
                duration_seconds = round((finished_at - started_at).total_seconds(), 2)
                durations.append(duration_seconds)
            recent_jobs.append(
                {
                    "id": str(job.get("id")),
                    "job_type": job.get("job_type"),
                    "duration_seconds": duration_seconds,
                }
            )

        durations.sort()
        average_seconds = round(sum(durations) / len(durations), 2) if durations else None
        p95_seconds = self._percentile(durations, 0.95) if durations else None
        return {
            "average_seconds": average_seconds,
            "p95_seconds": p95_seconds,
            "recent_jobs": recent_jobs,
        }

    def _build_freshness_summary(self, report: dict[str, Any]) -> dict[str, Any]:
        """汇总数据新鲜度信息。"""
        sources = report.get("source_freshness", []) if isinstance(report, dict) else []
        return {
            "sources": _to_plain(sources),
        }

    def _build_alert_summary(self, report: dict[str, Any]) -> dict[str, Any]:
        """汇总告警信息。"""
        alerts = list(report.get("alerts", [])) if isinstance(report, dict) else []
        critical = 0
        warning = 0
        latest: list[dict[str, Any]] = []
        for alert in alerts:
            plain_alert = _to_plain(alert)
            level = str(plain_alert.get("level") or "").lower()
            if level == "critical":
                critical += 1
            elif level == "warning":
                warning += 1
            latest.append(plain_alert)
        return {
            "critical": critical,
            "warning": warning,
            "latest": latest[:5],
        }

    def _build_trace_entry(self, job: dict[str, Any]) -> dict[str, Any] | None:
        """从 Job 审计记录中提取追踪线索。"""
        audit_events = list(job.get("audit_events", []))
        request_context = None
        if audit_events:
            payload = audit_events[-1].get("payload") if isinstance(audit_events[-1], dict) else None
            if isinstance(payload, dict):
                request_context = payload.get("request_context")
        if request_context is None:
            return None
        return {
            "job_id": str(job.get("id")),
            "request_context": _to_plain(request_context),
        }

    def _parse_dt(self, value: Any) -> datetime | None:
        """解析 ISO 日期时间。"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(normalized)
            except ValueError:
                return None
        return None

    def _percentile(self, values: list[float], quantile: float) -> float | None:
        """计算简单分位数。"""
        if not values:
            return None
        if quantile <= 0:
            return round(values[0], 2)
        if quantile >= 1:
            return round(values[-1], 2)
        index = max(0, min(len(values) - 1, int((len(values) * quantile + 0.999999)) - 1))
        return round(values[index], 2)
