"""Pipeline 健康检查器。"""
from __future__ import annotations

from datetime import UTC, datetime

from src.common.logger import get_logger
from src.health.models import ComponentCheck, HealthStatus

logger = get_logger("health.pipeline")


# 全局变量：记录最近一次 pipeline 执行快照
_last_pipeline_snapshot: "PipelineHealthSnapshot | None" = None


def record_pipeline_snapshot(snapshot: "PipelineHealthSnapshot") -> None:
    """由 PipelineRunner 调用，记录最新执行快照。"""
    global _last_pipeline_snapshot
    _last_pipeline_snapshot = snapshot


class PipelineHealthChecker:
    """检查 Pipeline 最近执行状态。"""

    name: str = "pipeline"

    async def check(self) -> ComponentCheck:
        """返回最近一次 PipelineHealthSnapshot 的状态。"""
        global _last_pipeline_snapshot

        if _last_pipeline_snapshot is None:
            return ComponentCheck(
                name=self.name,
                status=HealthStatus.WARNING,
                details={
                    "last_run": None,
                    "total_runs_today": 0,
                },
                error="No pipeline run recorded yet",
            )

        snap = _last_pipeline_snapshot
        today = datetime.now(UTC).date()
        snap_date = snap.started_at.date() if snap.started_at else None
        is_today = snap_date == today if snap_date else False

        failed_nodes = getattr(snap, "failed_nodes", [])
        status = HealthStatus.OK if not failed_nodes else HealthStatus.ERROR

        return ComponentCheck(
            name=self.name,
            status=status,
            details={
                "last_run": snap.started_at.isoformat() if snap.started_at else None,
                "last_status": snap.status,
                "failed_nodes": list(failed_nodes),
                "total_runs_today": 1 if is_today else 0,
            },
            error=f"{len(failed_nodes)} node(s) failed: {failed_nodes}" if failed_nodes else None,
        )