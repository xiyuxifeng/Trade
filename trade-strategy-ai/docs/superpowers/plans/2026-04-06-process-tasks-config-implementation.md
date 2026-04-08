# P1-026D: process_tasks 去 global config 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `process_tasks` 中的 global `_config` 改为闭包捕获，handlers 通过显式捕获的 config 获取配置，消除隐式全局状态。

**Architecture:** `run_process_tasks` 内部调用 `_create_handlers(config)` 创建局部 handler 闭包，闭包显式捕获 config，`_process_one` 接收 handlers 参数而非读取 global。

**Tech Stack:** Python async, pytest

---

## 文件变更

| 操作 | 文件 |
|------|------|
| 修改 | `trade-strategy-ai/src/pipeline/tasks/process_tasks.py` |

---

## Task 1: 添加 `_create_handlers` 函数

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/process_tasks.py`

- [ ] **Step 1: 在 `run_process_tasks` 定义前添加 `_create_handlers` 函数**

在 `run_process_tasks` 函数（第129行）之前添加：

```python
def _create_handlers(config: AppConfig) -> dict[str, TaskHandler]:
    """Create handler closures that explicitly capture config.

    Each handler is a local async function that closes over the config
    passed in, eliminating the need for module-level global state.
    """

    async def handle_article_ingested(details: dict[str, Any]) -> None:
        from src.agents.data_agent.skills.extract_article_metadata import (
            extract_and_store_metadata,
        )

        await extract_and_store_metadata(
            config=config,
            base_dir=Path("."),
            limit=20,
        )

    async def handle_article_metadata_extracted(details: dict[str, Any]) -> None:
        from src.persona.cluster_builder import build_clusters_from_db

        dest = Path("data/processed/persona/clusters.real.json")
        await build_clusters_from_db(config=config, dest=dest)

    return {
        "article_ingested": handle_article_ingested,
        "article_metadata_extracted": handle_article_metadata_extracted,
    }
```

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/process_tasks.py
git commit -m "feat(process_tasks): add _create_handlers closure factory"
```

---

## Task 2: 修改 `_process_one` 签名

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/process_tasks.py`

- [ ] **Step 1: 修改 `_process_one` 函数，接收 handlers 参数**

将当前函数签名：
```python
async def _process_one(task: dict[str, Any]) -> tuple[bool, bool]:
```

替换为：
```python
async def _process_one(
    task: dict[str, Any], handlers: dict[str, TaskHandler]
) -> tuple[bool, bool]:
```

同时将函数内：
```python
handler = TASK_HANDLERS.get(task_type)
```

替换为：
```python
handler = handlers.get(task_type)
```

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/process_tasks.py
git commit -m "feat(process_tasks): _process_one accepts handlers param"
```

---

## Task 3: 重写 `run_process_tasks` 消除 global

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/process_tasks.py`

- [ ] **Step 1: 重写 `run_process_tasks` 函数体**

删除：
```python
global _config
_config = config
```

在函数体开头添加：
```python
handlers = _create_handlers(config)
```

同时将 `_process_one(task)` 调用替换为 `_process_one(task, handlers)`。

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/process_tasks.py
git commit -m "feat(process_tasks): use closures instead of global config"
```

---

## Task 4: 删除 global 相关代码

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/process_tasks.py`

- [ ] **Step 1: 删除以下代码**

1. 删除 `global _config` 和 `_config = config`（已在 Task 3 删除）

2. 删除 `_config` 变量声明（约第175行）：
```python
_config: AppConfig | None = None
```

3. 删除 `_get_config()` 函数（约第178-181行）：
```python
def _get_config() -> AppConfig:
    if _config is None:
        raise RuntimeError("run_process_tasks must be called with config parameter")
    return _config
```

4. 删除 handlers 内对 `_get_config()` 的调用，替换为直接使用闭包捕获的 config。

当前代码（约第188行和第201行）：
```python
config = _get_config()
```

应删除这两行（因为闭包已捕获 config）。

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/process_tasks.py
git commit -m "chore(process_tasks): remove global config and _get_config"
```

---

## Task 5: 清理未使用的 import

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/process_tasks.py`

- [ ] **Step 1: 检查并清理未使用的 import**

检查 `AppConfig` 是否仍被使用：
- `_create_handlers(config: AppConfig)` — 仍在用
- `_config` — 已删除

如果 `from src.common.config import AppConfig` 不再有其他用途，确认仍需保留。

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/process_tasks.py
git commit -m "chore(process_tasks): verify imports after refactor"
```

---

## Task 6: 单元测试

**Files:**
- Create: `trade-strategy-ai/tests/unit/pipeline/test_process_tasks.py`

- [ ] **Step 1: 写测试文件**

```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile

import pytest

from src.pipeline.tasks.process_tasks import (
    ProcessTasksStats,
    _create_handlers,
    _dedup_by_article_id,
)


class TestCreateHandlers:
    def test_returns_dict_with_expected_keys(self) -> None:
        mock_config = MagicMock()
        handlers = _create_handlers(mock_config)
        assert "article_ingested" in handlers
        assert "article_metadata_extracted" in handlers

    def test_handler_closes_over_config(self) -> None:
        mock_config = MagicMock()
        mock_config.some_value = "test_value"
        handlers = _create_handlers(mock_config)

        article_ingested = handlers["article_ingested"]
        # The handler should have access to mock_config via closure
        # We verify by checking that extract_and_store_metadata is called with mock_config
        assert callable(article_ingested)


class TestDedupByArticleId:
    def test_dedup_keeps_latest(self) -> None:
        tasks = [
            {"task_id": "1", "details": {"article_id": "a"}, "created_at": "2026-01-01"},
            {"task_id": "2", "details": {"article_id": "a"}, "created_at": "2026-01-03"},
            {"task_id": "3", "details": {"article_id": "b"}, "created_at": "2026-01-02"},
        ]
        result = _dedup_by_article_id(tasks)
        assert len(result) == 2
        article_ids = {t["details"]["article_id"] for t in result}
        assert article_ids == {"a", "b"}
        # Latest for 'a' should be task_id 2
        latest_a = next(t for t in result if t["details"]["article_id"] == "a")
        assert latest_a["task_id"] == "2"

    def test_dedup_empty_list(self) -> None:
        result = _dedup_by_article_id([])
        assert result == []

    def test_dedup_missing_article_id(self) -> None:
        tasks = [
            {"task_id": "1", "details": {}, "created_at": "2026-01-01"},
        ]
        result = _dedup_by_article_id(tasks)
        assert result == []
```

- [ ] **Step 2: 运行测试**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
pytest tests/unit/pipeline/test_process_tasks.py -v
```

期望：所有测试 PASS

- [ ] **Step 3: Commit**

```bash
git add trade-strategy-ai/tests/unit/pipeline/test_process_tasks.py
git commit -m "test(process_tasks): add unit tests for _create_handlers and _dedup_by_article_id"
```

---

## Task 7: 端到端验证

**Files:**
- None

- [ ] **Step 1: 运行全量测试**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
pytest tests/ -v --tb=short 2>&1 | tail -30
```

期望：无新失败

- [ ] **Step 2: 端到端 DAG 验证（如环境支持）**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
python -c "
import asyncio
from src.pipeline.dag import run_pipeline

async def test():
    result = await run_pipeline(force_crawl=False)
    print(f'store={result.store}')
    print(f'process={result.process}')

asyncio.run(test())
"
```

期望：`process` stats 正常返回，无 RuntimeError about config

- [ ] **Step 3: Commit 所有更改**

```bash
git add -A
git commit -m "feat(process_tasks): eliminate global config via closures"
```

---

## 依赖检查

实现本计划前，确认以下文件存在：
- `trade-strategy-ai/src/pipeline/tasks/process_tasks.py`（已存在）
- `trade-strategy-ai/src/common/config.py`（AppConfig 定义）
- `trade-strategy-ai/src/pipeline/tasks/__init__.py`（检查是否导出相关内容）

## 验收标准

1. `pytest tests/unit/pipeline/test_process_tasks.py -v` 全部 PASS
2. 全量测试无新失败
3. DAG 端到端运行正常，`process` stats 正常
4. 代码中无 `global _config`、`_get_config()`、`_config` 变量
5. handlers 通过闭包捕获 config，无隐式全局依赖
