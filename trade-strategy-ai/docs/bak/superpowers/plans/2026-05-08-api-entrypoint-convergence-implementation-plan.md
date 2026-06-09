# API 入口收敛 Implementation Plan

> 注：这是一份历史实施计划。最终落地已经改为只保留 `api/main.py` 一个对外入口，`src/api/main.py` 已删除。下述步骤保留为迁移过程记录，不再作为当前执行目标。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `api/main.py` 与 `src/api/main.py` 收敛为同一套 FastAPI app 构建入口，并保留兼容层，避免后续路由继续分叉。

**Architecture:** 引入单一 app factory 作为唯一的应用构建来源，把旧的 `api/routers/*`、新的 `src/api/routes/*` 和 UI BFF 路由都挂到同一个工厂里。`api/main.py` 作为对外主入口，`src/api/main.py` 作为迁移期兼容层，两者都只导入同一个 `app`。完成后再用测试和文档锁定这一边界，最后再评估根目录 `src/` 的遗留清理。

**Tech Stack:** Python 3.11+, FastAPI, pytest

---

## 文件结构

```
src/api/
├── app.py                 # 新增：唯一的 FastAPI app factory
├── main.py                # 修改：迁移期兼容入口，导入共享 app
├── routes/               # 现有旧 API 路由集合
└── routers/ui/           # 现有 UI BFF 路由集合

api/
├── main.py                # 修改：对外主入口，导入共享 app
└── routers/ui/            # 迁移期兼容路由导出

tests/api/
└── test_api_entrypoints.py  # 新增：验证两个入口共享同一套关键路由
```

---

## Task 1: 建立单一 app factory

**Files:**
- Create: `src/api/app.py`
- Modify: `api/main.py`
- Modify: `src/api/main.py`
- Test: `tests/api/test_api_app_factory.py`

- [ ] **Step 1: 写 failing test**

```python
"""API app factory 测试。"""

from src.api.app import create_app


def test_create_app_registers_critical_routes() -> None:
    app = create_app()
    paths = set(app.openapi()["paths"])
    assert "/health" in paths
    assert "/run/pre_market" in paths
    assert "/reports/daily" in paths
    assert "/api/ui/v1/jobs/definitions" in paths
```

- [ ] **Step 2: 跑测试，确认失败**

Run:

```bash
python -m pytest tests/api/test_api_app_factory.py -q
```

Expected:

- `ModuleNotFoundError` 或 `ImportError`，因为 `src/api/app.py` 还不存在。

- [ ] **Step 3: 实现最小 app factory**

```python
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import alerts, backtest_results, rankings, reports, run, snapshots, strategy_versions
from api.routers.ui import jobs_router as ui_jobs_router
from src.api.routes import articles_router, market_router, trades_router
from src.health.routes import health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    config_path = Path("config/app.yaml")
    if config_path.exists():
        run.set_config_path(config_path)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Trade Strategy AI API",
        description="交易策略 AI 系统的 HTTP 接口层",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(run.router)
    app.include_router(reports.router)
    app.include_router(strategy_versions.router)
    app.include_router(snapshots.router)
    app.include_router(rankings.router)
    app.include_router(backtest_results.router)
    app.include_router(alerts.router)
    app.include_router(ui_jobs_router)
    app.include_router(articles_router)
    app.include_router(trades_router)
    app.include_router(market_router)
    app.include_router(health_router)
    return app


app = create_app()
```

`api/main.py` 与 `src/api/main.py` 都改成：

```python
from src.api.app import app

__all__ = ["app"]
```

- [ ] **Step 4: 跑测试验证通过**

Run:

```bash
python -m pytest tests/api/test_api_app_factory.py -q
```

Expected:

- `1 passed`

- [ ] **Step 5: 提交**

```bash
git add src/api/app.py api/main.py src/api/main.py tests/api/test_api_app_factory.py
git commit -m "feat(api): add shared app factory"
```

---

## Task 2: 收敛入口兼容层与路由导出

**Files:**
- Modify: `api/routers/ui/__init__.py`
- Modify: `api/routers/ui/jobs.py`
- Modify: `src/api/routers/ui/__init__.py`
- Modify: `src/api/routers/ui/jobs.py`
- Modify: `tests/api/test_api_entrypoints.py`

- [ ] **Step 1: 写 failing test**

```python
"""API 入口一致性测试。"""

from api.main import app as legacy_app
from src.api.main import app as src_app


def test_legacy_and_src_entrypoints_share_critical_paths() -> None:
    legacy_paths = set(legacy_app.openapi()["paths"])
    src_paths = set(src_app.openapi()["paths"])

    assert "/api/ui/v1/jobs/definitions" in legacy_paths
    assert "/api/ui/v1/jobs/definitions" in src_paths
    assert "/run/pre_market" in legacy_paths
    assert "/run/pre_market" in src_paths
```

- [ ] **Step 2: 跑测试，确认失败**

Run:

```bash
python -m pytest tests/api/test_api_entrypoints.py -q
```

Expected:

- 如果入口仍旧分叉，断言会失败。

- [ ] **Step 3: 修正兼容层**

```python
from src.api.app import app

__all__ = ["app"]
```

确保：

- `api/main.py` 只负责导出共享 `app`
- `src/api/main.py` 只负责导出共享 `app`
- `api/routers/ui/*` 和 `src/api/routers/ui/*` 的导出保持一致，避免入口层重复逻辑

- [ ] **Step 4: 跑测试验证通过**

Run:

```bash
python -m pytest tests/api/test_api_entrypoints.py -q
```

Expected:

- `1 passed`

- [ ] **Step 5: 提交**

```bash
git add api/routers/ui/__init__.py api/routers/ui/jobs.py src/api/routers/ui/__init__.py src/api/routers/ui/jobs.py tests/api/test_api_entrypoints.py
git commit -m "refactor(api): converge entrypoints"
```

---

## Task 3: 文档对齐与遗留目录边界

**Files:**
- Modify: `docs/web-plan.md`
- Modify: `docs/Web-TaskList.md`
- Modify: `docs/UserManual.md`

- [ ] **Step 1: 写 failing test / 检查项**

```text
检查项：
- `docs/web-plan.md` 必须说明单一 app factory 是源码真相。
- `docs/Web-TaskList.md` 必须明确 `api/main.py` 是 canonical entrypoint。
- `docs/UserManual.md` 中若还存在旧入口说明，必须标明兼容期，不得当成唯一实现。
```

- [ ] **Step 2: 更新文档内容**

在 `docs/web-plan.md` 的 API / BFF 章节补充：

- `src/api/app.py` 是唯一 app factory
- `api/main.py` 是主入口
- `src/api/main.py` 是迁移期兼容层
- 根目录 `src/` 目录暂不删除，先作为历史兼容层保留

在 `docs/Web-TaskList.md` 中新增后续清理任务或备注：

- API 收敛完成后，再做根目录 `src/` 的引用审计
- 清理目标必须等 `src.providers.kaipan_scheduler` 不再被文档、脚本和测试引用后才能启动

在 `docs/UserManual.md` 中对旧命令入口增加迁移说明：

- 旧 `python -m src.providers.kaipan_scheduler` 属于历史兼容入口
- 后续新入口优先以 Web API 和 `api/main.py` 为准

- [ ] **Step 3: 跑文档检查**

```bash
rg -n "src.api.main|api.main|src.providers.kaipan_scheduler" docs/UserManual.md docs/web-plan.md docs/Web-TaskList.md
```

Expected:

- 只保留清晰的迁移说明和兼容说明，不再出现“两个入口都同等推荐”的表述。

- [ ] **Step 4: 提交**

```bash
git add docs/web-plan.md docs/Web-TaskList.md docs/UserManual.md
git commit -m "docs(api): document entrypoint convergence"
```

---

## 非目标

- 本计划不删除根目录 `src/`。
- 本计划不改写 `src/providers/kaipan_scheduler.py` 的业务逻辑。
- 本计划不重构旧路由实现，只收敛应用装配层。

## 交付标准

完成本计划后：

- 代码上只有一套 app 组合逻辑。
- `api.main` 与 `src.api.main` 不再分别维护应用定义。
- 文档明确说明 canonical entrypoint、兼容层和遗留目录边界。
- 后续若要删除根目录 `src/`，只需做遗留引用清理，不需要再拆应用装配逻辑。
