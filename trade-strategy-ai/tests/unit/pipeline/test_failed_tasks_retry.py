from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile

import pytest

from src.pipeline.tasks.process_tasks import (
    _cleanup_failed_tasks,
    _load_failed_with_metadata,
    _save_failed_with_metadata,
    MAX_RETRY_COUNT,
    FAILED_TTL_DAYS,
)


class TestCleanupFailedTasks:
    def test_retry_count_below_limit_preserved(self) -> None:
        now = datetime.now(timezone.utc)
        tasks = [
            {"task_id": "1", "failed_at": now.isoformat(), "retry_count": 2},
        ]
        alive, dead = _cleanup_failed_tasks(tasks)
        assert len(alive) == 1
        assert len(dead) == 0

    def test_retry_count_at_limit_moves_to_dead(self) -> None:
        now = datetime.now(timezone.utc)
        tasks = [
            {"task_id": "1", "failed_at": now.isoformat(), "retry_count": MAX_RETRY_COUNT},
        ]
        alive, dead = _cleanup_failed_tasks(tasks)
        assert len(alive) == 0
        assert len(dead) == 1

    def test_old_task_beyond_ttl_moves_to_dead(self) -> None:
        now = datetime.now(timezone.utc)
        old_date = now - timedelta(days=FAILED_TTL_DAYS + 1)
        tasks = [
            {"task_id": "1", "failed_at": old_date.isoformat(), "retry_count": 0},
        ]
        alive, dead = _cleanup_failed_tasks(tasks)
        assert len(alive) == 0
        assert len(dead) == 1

    def test_recent_task_below_ttl_preserved(self) -> None:
        now = datetime.now(timezone.utc)
        recent = now - timedelta(days=1)
        tasks = [
            {"task_id": "1", "failed_at": recent.isoformat(), "retry_count": 0},
        ]
        alive, dead = _cleanup_failed_tasks(tasks)
        assert len(alive) == 1
        assert len(dead) == 0


class TestLoadSaveFailedWithMetadata:
    def test_backward_compat_adds_defaults(self, tmp_path: Path) -> None:
        path = tmp_path / "test.jsonl"
        # Write old-format entry (no failed_at, no retry_count)
        with path.open("w") as f:
            f.write('{"task_id": "1", "type": "test"}\n')
        tasks = _load_failed_with_metadata(path)
        assert len(tasks) == 1
        assert tasks[0]["retry_count"] == 0
        assert "failed_at" in tasks[0]

    def test_roundtrip_preserves_metadata(self, tmp_path: Path) -> None:
        path = tmp_path / "test.jsonl"
        tasks = [
            {"task_id": "1", "failed_at": "2026-04-06T10:00:00Z", "retry_count": 2},
        ]
        _save_failed_with_metadata(path, tasks)
        loaded = _load_failed_with_metadata(path)
        assert len(loaded) == 1
        assert loaded[0]["retry_count"] == 2
        assert loaded[0]["failed_at"] == "2026-04-06T10:00:00Z"