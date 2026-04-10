# FastAPI 异步嵌套修复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 FastAPI 路由中 `asyncio.run()` 嵌套事件循环问题，通过新增异步版本的 `handle_command_async` 实现职责分离。

**Architecture:** `handle_command` 保持同步供 CLI 等场景使用，新增 `handle_command_async` 供 FastAPI 直接 await，职责边界清晰。

**Tech Stack:** Python asyncio, FastAPI, uvicorn

---

## 文件变更概览

| 文件 | 操作 |
|------|------|
| `src/host/handler.py` | 新增 `handle_command_async`，`handle_command` 标记 `@deprecated` |
| `src/host/__init__.py` | 导出 `handle_command_async` |
| `src/api/main.py` | 三个路由改用 `handle_command_async` |

---

## Task 1: 新增 `handle_command_async` 到 `handler.py`

**Files:**
- Modify: `src/host/handler.py`

- [ ] **Step 1: 在 `handle_command` 上方添加 `@deprecated` 装饰器**

在 `src/host/handler.py` 的 `handle_command` 函数定义前添加：

```python
import warnings

def handle_command(command: dict[str, Any]) -> dict[str, Any]:
    """Handle a thin-shell JSON command.

    .. deprecated::
        Use :func:`handle_command_async` instead. This synchronous version
        will be removed once all callers migrate to the async interface.
    """
    warnings.warn(
        "handle_command is deprecated, use handle_command_async instead",
        DeprecationWarning,
        stacklevel=2,
    )
```

- [ ] **Step 2: 在文件顶部添加 Future 导入**

在 `src/host/handler.py` 顶部的 `from __future__ import annotations` 后添加：

```python
from __future__ import annotations

import asyncio
import warnings
from datetime import date
from pathlib import Path
from typing import Any
```

- [ ] **Step 3: 在 `handle_command` 函数下方新增 `handle_command_async`**

在 `handle_command` 函数之后、`_project_base_dir` 之前添加：

```python
async def handle_command_async(command: dict[str, Any]) -> dict[str, Any]:
    """Async handler for FastAPI integration.

    This is the preferred entry point for FastAPI routes.
    """
    cmd = HostCommand.model_validate(command)
    loaded = load_app_config(cmd.config_path)
    base_dir = _project_base_dir(loaded.config_path)
    mgr = ManagerAgent(config=loaded.config, base_dir=base_dir)
    as_of = cmd.as_of_date or date.today()

    try:
        if cmd.type == "run_pre_market":
            report = await mgr.run_pre_market(as_of_date=as_of, force=cmd.force)
            return HostResponse(type=cmd.type, payload=report.model_dump()).model_dump()
        if cmd.type == "run_after_close":
            result = await mgr.run_after_close(as_of_date=as_of, force=cmd.force)
            return HostResponse(type=cmd.type, payload=result.model_dump()).model_dump()
        if cmd.type == "persona_init_sample":
            trader_ids = [t.trader_id for t in loaded.config.traders]
            clusters = build_sample_clusters_file(trader_ids=trader_ids)
            dest = cmd.args.get("dest") or (
                loaded.config.persona.clusters_path
                or "data/processed/persona/clusters.sample.json"
            )
            path = write_persona_clusters_file(
                path=base_dir / dest if not Path(str(dest)).is_absolute() else dest,
                data=clusters,
            )
            return HostResponse(type=cmd.type, payload={"clusters_path": str(path)}).model_dump()
        return HostResponse(
            ok=False, type=cmd.type, errors=[f"Unknown command type: {cmd.type}"]
        ).model_dump()
    except Exception as exc:
        return HostResponse(ok=False, type=cmd.type, errors=[str(exc)]).model_dump()
```

- [ ] **Step 4: 验证文件结构**

确认 `handler.py` 函数顺序为：
1. `_project_base_dir` (helper)
2. `handle_command_async` (新增)
3. `handle_command` (deprecated)

---

## Task 2: 更新 `__init__.py` 导出

**Files:**
- Modify: `src/host/__init__.py`

- [ ] **Step 1: 更新导出列表**

将 `src/host/__init__.py` 内容改为：

```python
from .handler import handle_command, handle_command_async

__all__ = ["handle_command", "handle_command_async"]
```

---

## Task 3: 修改 FastAPI 路由使用异步版本

**Files:**
- Modify: `src/api/main.py`

- [ ] **Step 1: 修改 `trigger_pre_market` 路由**

将 `src/api/main.py:77` 的 `result = handle_command(command)` 改为：

```python
    from src.host.handler import handle_command_async

    command = {
        "type": "run_pre_market",
        "config_path": request.config_path,
        "as_of_date": request.as_of_date.isoformat() if request.as_of_date else None,
        "force": request.force,
        "args": request.args,
    }
    result = await handle_command_async(command)
    return result
```

- [ ] **Step 2: 修改 `trigger_after_close` 路由**

将 `src/api/main.py:96` 的 `result = handle_command(command)` 改为：

```python
    from src.host.handler import handle_command_async

    command = {
        "type": "run_after_close",
        "config_path": request.config_path,
        "as_of_date": request.as_of_date.isoformat() if request.as_of_date else None,
        "force": request.force,
        "args": request.args,
    }
    result = await handle_command_async(command)
    return result
```

- [ ] **Step 3: 修改 `host_command` 路由**

将 `src/api/main.py:128` 的 `result = handle_command(command)` 改为：

```python
    from src.host.handler import handle_command_async

    command = {
        "type": request.type,
        "config_path": request.config_path,
        "as_of_date": request.as_of_date.isoformat() if request.as_of_date else None,
        "force": request.force,
        "args": request.args,
    }
    result = await handle_command_async(command)
    return result
```

---

## Task 4: 验证

- [ ] **Step 1: 运行 Python 语法检查**

Run: `cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai && python -m py_compile src/host/handler.py src/host/__init__.py src/api/main.py`
Expected: 无输出（编译成功）

- [ ] **Step 2: 检查导入是否正常**

Run: `cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai && python -c "from src.host.handler import handle_command_async, handle_command; print('import ok')"`
Expected: `import ok`

- [ ] **Step 3: 确认没有遗留的 `asyncio.run()` 调用**

Run: `grep -n "asyncio.run" src/host/handler.py src/api/main.py`
Expected: 无输出（迁移完成）

---

## 完成后

- 设计文档：`docs/superpowers/specs/2026-04-09-fix-async-nesting-design.md`
- 计划文档：`docs/superpowers/plans/2026-04-09-fix-async-nesting-plan.md`
