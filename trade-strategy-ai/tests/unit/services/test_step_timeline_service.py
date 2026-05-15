from __future__ import annotations

from src.models.step_timeline import JobTimeline
from src.services.step_timeline_service import StepTimelineService


def test_normalize_audit_events_into_step_timeline() -> None:
    """StepTimelineService 应能把 Job audit events 归一化为结构化 timeline。"""
    service = StepTimelineService()
    timeline: JobTimeline = service.build_job_timeline(
        job={
            "id": "job-1",
            "status": "running",
            "started_at": "2026-05-15T00:00:00+00:00",
            "finished_at": None,
            "audit_events": [
                {
                    "operation": "create",
                    "actor": "web",
                    "event_at": "2026-05-15T00:00:00+00:00",
                    "payload": {"details": {"job_type": "pipeline-run"}},
                },
                {
                    "operation": "start",
                    "actor": "worker-1",
                    "event_at": "2026-05-15T00:01:00+00:00",
                    "payload": {"details": {"worker_id": "worker-1"}},
                },
            ],
        }
    )

    assert timeline.count == 2
    assert timeline.items[0].title == "Job 创建"
    assert timeline.items[0].status == "success"
    assert timeline.items[1].title == "Job 启动"
    assert timeline.items[1].status == "running"
