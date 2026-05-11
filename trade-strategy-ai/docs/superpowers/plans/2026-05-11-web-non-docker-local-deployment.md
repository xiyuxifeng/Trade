# Web Non-Docker Local Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `trade-strategy-ai` 增加一条不依赖 Docker 的单机本机部署与构建路径，让用户可以在已安装 Python、Node 和 PostgreSQL 的机器上完成前端构建、数据库迁移、API 启动、Worker 启动和 Web 访问的闭环验证。

**Architecture:** 保留现有 Docker/Compose 作为默认生产方案，同时新增一个本机 launcher 脚本和一个可选的 API 静态资源托管入口。本机模式下由 Python launcher 负责协调命令执行，API 通过 `WEB_STATIC_DIR` 托管 `web/dist`，浏览器可以直接访问同源的 `http://localhost:8000`，不需要额外 Nginx 或反向代理。

**Tech Stack:** Python 3.11+, FastAPI, Typer, Uvicorn, PostgreSQL, Node.js 22+, Corepack/pnpm, pytest, pytest-asyncio.

---

### Task 1: 本机 launcher 脚本

**Files:**
- Create: `scripts/web_local.py`
- Create: `tests/unit/scripts/test_web_local.py`

- [ ] **Step 1: 写失败测试**

先写一个只验证命令编排的测试，确保脚本从仓库根目录出发时会切到正确工作目录，并且每个子命令调用了正确的外部命令。

```python
from pathlib import Path
from types import SimpleNamespace

def test_build_runs_pnpm_in_web_dir(monkeypatch):
    calls = []

    def fake_run(cmd, cwd=None, check=None, env=None):
        calls.append((tuple(cmd), Path(cwd) if cwd else None))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("scripts.web_local.subprocess.run", fake_run)
    build()

    assert calls == [(
        ("corepack", "pnpm", "build"),
        Path("/Users/wanghui/Documents/Claude/trade-strategy-ai/web"),
    )]
```

再补两个命令测试：

```python
def test_migrate_runs_cli_command_in_repo_root(monkeypatch):
    calls = []

    def fake_run(cmd, cwd=None, check=None, env=None):
        calls.append((tuple(cmd), Path(cwd) if cwd else None))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("scripts.web_local.subprocess.run", fake_run)
    migrate()

    assert calls == [(
        ("python", "-m", "cli.main", "db-migrate", "--config", "config/app.yaml"),
        Path("/Users/wanghui/Documents/Claude/trade-strategy-ai"),
    )]

def test_start_supervises_api_and_worker(monkeypatch):
    spawned = []

    class FakeProcess:
        def __init__(self, cmd):
            self.cmd = tuple(cmd)
            self._polls = 0
            self.returncode = None

        def poll(self):
            self._polls += 1
            if self._polls < 2:
                return None
            self.returncode = 0
            return self.returncode

        def terminate(self):
            self.returncode = 0

        def wait(self, timeout=None):
            self.returncode = 0
            return 0

    def fake_popen(cmd, cwd=None, env=None):
        spawned.append((tuple(cmd), Path(cwd) if cwd else None))
        return FakeProcess(cmd)

    monkeypatch.setattr("scripts.web_local.subprocess.Popen", fake_popen)
    monkeypatch.setattr("scripts.web_local.time.sleep", lambda _: None)
    monkeypatch.setattr("scripts.web_local._require_web_dist", lambda *_: None)

    start()

    assert spawned == [
        (
            ("uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"),
            Path("/Users/wanghui/Documents/Claude/trade-strategy-ai"),
        ),
        (
            ("python", "-m", "cli.main", "job-worker-start", "--config", "config/app.yaml"),
            Path("/Users/wanghui/Documents/Claude/trade-strategy-ai"),
        ),
    ]
```

- [ ] **Step 2: 先跑测试确认失败**

Run:

```bash
pytest -q tests/unit/scripts/test_web_local.py
```

Expected: fail，因为 `scripts/web_local.py` 还不存在。

- [ ] **Step 3: 实现最小功能**

实现 `scripts/web_local.py` 的命令集合：

- `build`：在 `web/` 目录执行 `corepack pnpm build`
- `migrate`：在仓库根目录执行 `python -m cli.main db-migrate --config config/app.yaml`
- `start-api`：启动 `uvicorn api.main:app --host 0.0.0.0 --port 8000`
- `start-worker`：启动 `python -m cli.main job-worker-start --config config/app.yaml`
- `start`：先检查 `web/dist/index.html`，再用子进程同时拉起 API 和 Worker，任一子进程退出就让父进程以非零状态退出

建议用 `subprocess.run()` 处理一次性命令，用 `subprocess.Popen()` 处理长驻进程，并把 `cwd` 和环境变量显式传给子进程。

- [ ] **Step 4: 跑测试确认通过**

Run:

```bash
pytest -q tests/unit/scripts/test_web_local.py
```

Expected: PASS。

- [ ] **Step 5: 记录实现边界**

补中文注释，说明 launcher 只负责本机单机验证，不替代 Docker/Compose。

---

### Task 2: API 本机静态托管

**Files:**
- Modify: `api/app.py`
- Create: `tests/api/test_web_static_local.py`

- [ ] **Step 1: 写失败测试**

写一个测试，覆盖 `WEB_STATIC_DIR` 存在时的本机静态资源托管行为。

```python
from pathlib import Path
from fastapi.testclient import TestClient

def test_web_static_root_and_spa_fallback(monkeypatch, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>web</body></html>", encoding="utf-8")
    monkeypatch.setenv("WEB_STATIC_DIR", str(dist))

    from api.app import create_app

    client = TestClient(create_app())
    assert client.get("/").status_code == 200
    assert client.get("/jobs").status_code == 200
    assert "web" in client.get("/jobs").text
    assert client.get("/health").json() == {"status": "ok"}
```

再补一个测试，确认 `/api/ui/v1/*` 路由不被静态回退覆盖：

```python
def test_api_routes_keep_priority(monkeypatch, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>web</body></html>", encoding="utf-8")
    monkeypatch.setenv("WEB_STATIC_DIR", str(dist))

    from api.app import create_app

    client = TestClient(create_app())
    assert client.get("/api/ui/v1/system/status").status_code in {200, 401, 403}
```

- [ ] **Step 2: 先跑测试确认失败**

Run:

```bash
pytest -q tests/api/test_web_static_local.py
```

Expected: fail，因为 `WEB_STATIC_DIR` 逻辑还没接入。

- [ ] **Step 3: 实现最小功能**

在 `api/app.py` 里增加一个本机静态资源托管辅助函数：

- 从 `WEB_STATIC_DIR` 读取前端构建目录
- 如果目录有效，注册静态文件服务
- 对 SPA 路由做 fallback，返回 `index.html`
- 避免 `/api/*`、`/health`、`/docs`、`/openapi.json`、`/redoc` 被静态路由吞掉

保持当前 API 路由语义不变，只在本机模式下额外提供页面入口。

- [ ] **Step 4: 跑测试确认通过**

Run:

```bash
pytest -q tests/api/test_web_static_local.py
```

Expected: PASS。

- [ ] **Step 5: 复跑相关 API 测试**

Run:

```bash
pytest -q tests/api/routers/test_system_status.py tests/api/routers/test_jobs_api.py tests/api/routers/test_workflows.py
```

Expected: PASS，确认新增静态托管没有破坏现有 UI API。

---

### Task 3: 文档和任务清单对齐

**Files:**
- Modify: `docs/WebDeployment.md`
- Modify: `README.md`
- Modify: `web/README.md`
- Modify: `docs/Web-TaskList.md`
- Modify: `docs/web-plan.md` if the local-only deployment path needs a cross-reference

- [ ] **Step 1: 补文档**

在 `docs/WebDeployment.md` 中新增一个“本机非 Docker 部署”小节，明确下面这条顺序：

```bash
python -m scripts.web_local build
python -m scripts.web_local migrate
python -m scripts.web_local start
```

在 `README.md` 里补一段本机部署入口摘要，在 `web/README.md` 里说明 `pnpm build` 之后的本机托管方式。

- [ ] **Step 2: 补任务清单**

在 `docs/Web-TaskList.md` 的 Stage 9 中新增一条任务，建议编号为 `WEB-S9-007`，描述为“实现非 Docker 本机构建与启动脚本”。

建议验收标准写成：

- 本机可用 `scripts/web_local.py` 完成构建、迁移和启动
- API 可在本机模式下托管 `web/dist`
- 任务状态、文档和实现保持一致

实现完成后，把该任务标记为 `[x]`。

- [ ] **Step 3: 复核文档和任务清单一致性**

Run:

```bash
rg -n "web_local|WEB_STATIC_DIR|start-worker|start-api|WEB-S9-007|本机部署" docs README.md web/README.md
```

Expected: 命中所有新增入口，且没有遗漏。

- [ ] **Step 4: 跑格式检查**

Run:

```bash
git diff --check
```

Expected: 无空格和换行错误。

---

### Task 4: 本机端到端收口验证

**Files:**
- Modify: none

- [ ] **Step 1: 跑 launcher 帮助和单测**

Run:

```bash
python -m scripts.web_local --help
pytest -q tests/unit/scripts/test_web_local.py tests/api/test_web_static_local.py
```

Expected: help 输出包含 `build`、`migrate`、`start-api`、`start-worker`、`start`，测试通过。

- [ ] **Step 2: 跑现有 Web 验证**

Run:

```bash
pytest -q tests/api/routers/test_system_status.py tests/api/routers/test_workflows.py tests/api/routers/test_jobs_api.py
```

Expected: PASS。

- [ ] **Step 3: 收口任务状态**

把 `WEB-S9-007` 标记为完成，确保 `Web-TaskList`、`WebDeployment.md`、`README.md`、`web/README.md` 和代码行为一致。
