# P1-026E: failed_tasks.jsonl 自动重试 + TTL 清理实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 failed_tasks.jsonl 增加重试计数器（3次上限）和 TTL 清理（7天），超过上限移入 dead_tasks.jsonl。

**Architecture:** 在 `run_process_tasks` 内部集成 TTL 清理和重试计数逻辑，新增 `_load_failed_with_metadata`、`_save_failed_with_metadata`、`_cleanup_failed_tasks` 等辅助函数。

**Tech Stack:** Python async, pytest

---

## 文件变更

| 操作 | 文件 |
|------|------|
| 修改 | `trade-strategy-ai/src/pipeline/tasks/process_tasks.py` |

---

## Task 1: 添加常量 + ProcessTasksStats 新字段

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/process_tasks.py`

- [ ] **Step 1: 添加常量和修改 ProcessTasksStats**

在 `_MAX_RETRIES = 3` 后添加：

```python
MAX_RETRY_COUNT = 3   # 超过此值移入 dead_tasks
FAILED_TTL_DAYS = 7   # 超过此天数的失败记录清理

DEAD_TASKS_PATH = Path("data/processed/pipeline/dead_tasks.jsonl")
```

修改 `ProcessTasksStats` dataclass，添加 `dead: int = 0` 字段。

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/process_tasks.py
git commit -m "feat(process_tasks): add MAX_RETRY_COUNT, FAILED_TTL_DAYS, DEAD_TASKS_PATH, dead stat"
```

---

## Task 2: 实现 `_load_failed_with_metadata`

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/process_tasks.py`

- [ ] **Step 1: 在 `_load_tasks` 后添加 `_load_failed_with_metadata` 函数**

```python
def _load_failed_with_metadata(path: Path) -> list[dict[str, Any]]:
    """Load failed tasks with retry metadata.

    Returns list of dicts with 'failed_at' (ISO8601) and 'retry_count' (int) fields.
    Backward compatible: tasks without these fields get default values.
    """
    if not path.exists():
        return []
    tasks = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            task = json.loads(line)
            # Backward compat: add defaults for old-format entries
            if "failed_at" not in task:
                task["failed_at"] = datetime.now(UTC).isoformat()
            if "retry_count" not in task:
                task["retry_count"] = 0
            tasks.append(task)
    return tasks
```

注意：需要 `from datetime import datetime, timezone as TZ` 或 `from datetime import UTC`（如未导入）。

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/process_tasks.py
git commit -m "feat(process_tasks): add _load_failed_with_metadata"
```

---

## Task 3: 实现 `_save_failed_with_metadata`

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/process_tasks.py`

- [ ] **Step 1: 在 `_load_failed_with_metadata` 后添加 `_save_failed_with_metadata` 函数**

```python
def _save_failed_with_metadata(path: Path, tasks: list[dict[str, Any]]) -> None:
    """Save failed tasks with retry metadata to JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")
```

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/process_tasks.py
git commit -m "feat(process_tasks): add _save_failed_with_metadata"
```

---

## Task 4: 实现 `_cleanup_failed_tasks`

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/process_tasks.py`

- [ ] **Step 1: 添加 `_cleanup_failed_tasks` 函数**

```python
def _cleanup_failed_tasks(
    tasks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separate alive tasks from dead tasks based on retry count and TTL.

    Returns: (alive_tasks, dead_tasks)
    - alive: retry_count < MAX_RETRY_COUNT AND failed_at within FAILED_TTL_DAYS
    - dead: retry_count >= MAX_RETRY_COUNT OR failed_at > FAILED_TTL_DAYS ago
    """
    from datetime import timedelta

    now = datetime.now(TZ)
    ttl_cutoff = now - timedelta(days=FAILED_TTL_DAYS)

    alive: list[dict[str, Any]] = []
    dead: list[dict[str, Any]] = []

    for task in tasks:
        retry_count = task.get("retry_count", 0)
        failed_at_str = task.get("failed_at")
        if failed_at_str:
            try:
                failed_at = datetime.fromisoformat(failed_at_str.replace("Z", "+00:00"))
                # Handle naive datetime
                if failed_at.tzinfo is None:
                    failed_at = failed_at.replace(tzinfo=TZ)
            except (ValueError, TypeError):
                failed_at = now
        else:
            failed_at = now

        is_dead = (
            retry_count >= MAX_RETRY_COUNT
            or failed_at < ttl_cutoff
        )
        if is_dead:
            dead.append(task)
        else:
            alive.append(task)

    return alive, dead
```

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/process_tasks.py
git commit -m "feat(process_tasks): add _cleanup_failed_tasks"
```

---

## Task 5: 修改 `run_process_tasks` 集成重试 + TTL 逻辑

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/process_tasks.py`

- [ ] **Step 1: 重写 `run_process_tasks` 函数体**

变更点：
1. `failed_tasks = _load_tasks(f_path)` → `failed_tasks = _load_failed_with_metadata(f_path)`
2. 函数开头添加 TTL 清理：`_cleanup_failed_tasks` 分离 alive/dead
3. 任务失败时：找到 `task_id` 匹配的失败记录 → `retry_count += 1` → 判断是否 >= MAX_RETRY_COUNT → 移入 dead_tasks 或写回 failed_tasks
4. `_save_tasks(f_path, failed_tasks)` → `_save_failed_with_metadata(f_path, failed_tasks)`
5. 新增写 dead_tasks：`dead_path` 参数或默认 DEAD_TASKS_PATH，追加 dead_tasks
6. 统计 `dead` 数

**关键逻辑**：处理 task 失败时的更新逻辑：
```python
# 找到匹配的失败记录
matching = [t for t in failed_tasks if t.get("task_id") == task_id]
if matching:
    existing = matching[0]
    existing["retry_count"] = existing.get("retry_count", 0) + 1
    if existing["retry_count"] >= MAX_RETRY_COUNT:
        dead_tasks.append(existing)
        failed_tasks.remove(existing)
        stats.dead += 1
    # else: keep in failed_tasks for retry
```

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/process_tasks.py
git commit -m "feat(process_tasks): integrate retry + TTL into run_process_tasks"
```

---

## Task 6: 单元测试

**Files:**
- Create: `trade-strategy-ai/tests/unit/pipeline/test_failed_tasks_retry.py`

- [ ] **Step 1: 写测试文件**

```python
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
```

- [ ] **Step 2: 运行测试**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
pytest tests/unit/pipeline/test_failed_tasks_retry.py -v
```

期望：所有测试 PASS

- [ ] **Step 3: Commit**

```bash
git add trade-strategy-ai/tests/unit/pipeline/test_failed_tasks_retry.py
git commit -m "test(process_tasks): add unit tests for retry + TTL cleanup"
```

---

## Task 7: 端到端验证

**Files:**
- None

- [ ] **Step 1: 运行全量测试**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
pytest tests/ -v --tb=short 2>&1 | tail -40
```

期望：无新失败

- [ ] **Step 2: 验证逻辑**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
python -c "
from src.pipeline.tasks.process_tasks import _cleanup_failed_tasks, MAX_RETRY_COUNT, FAILED_TTL_DAYS
from datetime import datetime, timezone, timedelta

# Test: retry_count >= 3 → dead
now = datetime.now(timezone.utc)
tasks = [{'task_id': '1', 'failed_at': now.isoformat(), 'retry_count': 3}]
alive, dead = _cleanup_failed_tasks(tasks)
print(f'alive={len(alive)}, dead={len(dead)} (expect 0, 1)')
assert len(dead) == 1

# Test: retry_count < 3 + recent → alive
tasks = [{'task_id': '2', 'failed_at': now.isoformat(), 'retry_count': 2}]
alive, dead = _cleanup_failed_tasks(tasks)
print(f'alive={len(alive)}, dead={len(dead)} (expect 1, 0)')
assert len(alive) == 1
print('All checks passed')
"
```

期望：输出正确

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "feat(process_tasks): implement retry + TTL for failed tasks"
```

---

## 依赖检查

实现本计划前，确认以下文件存在：
- `trade-strategy-ai/src/pipeline/tasks/process_tasks.py`（已存在）
- `trade-strategy-ai/tests/unit/pipeline/` 目录存在

## 验收标准

1. `pytest tests/unit/pipeline/test_failed_tasks_retry.py -v` 全部 PASS
2. `pytest tests/ -v` 无新失败
3. `_cleanup_failed_tasks` 正确分类 alive/dead
4. 旧格式 `failed_tasks.jsonl` 兼容（自动补全 `failed_at`/`retry_count`）
5. `ProcessTasksStats.dead` 字段存在
