from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Awaitable

from src.schemas.contracts import AgentTask


@dataclass
class ProcessTasksStats:
    processed: int = 0
    skipped_dedup: int = 0
    retried: int = 0
    failed: int = 0
    duration_ms: int = 0


TaskHandler = Callable[[dict[str, Any]], Awaitable[None]]

TASK_HANDLERS: dict[str, TaskHandler] = {}


def register_handler(task_type: str, handler: TaskHandler) -> None:
    TASK_HANDLERS[task_type] = handler


def _load_tasks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    tasks = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            tasks.append(json.loads(line))
    return tasks


def _save_tasks(path: Path, tasks: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")
