# Web Non-Docker Local Deployment Design

> **For agentic workers:** this design targets the single-machine, non-Docker deployment path requested for local validation. Do not replace the Docker/Compose production flow; add a parallel local path that reuses the same API and worker logic.

**Goal:** 为 `trade-strategy-ai` 提供一条不依赖 Docker 的单机本机部署与构建路径，使用户可以在已安装 Python、Node 和 PostgreSQL 的机器上完成 `build -> migrate -> start api -> start worker -> open web` 的闭环验证。

**Architecture:** 保留现有 Docker/Compose 作为默认生产方案，同时新增一个本机部署 launcher 脚本和一个可选的 API 静态资源托管入口。本机模式下，后端 API 直接托管 `web/dist`，浏览器访问同一个 `http://localhost:8000` 即可同时看到 Web 页面和 `/api/ui/v1/*` 接口，避免额外反向代理和跨域配置。

**Tech Stack:** Python 3.11+, FastAPI, Typer, Uvicorn, PostgreSQL, Node.js 22+, Corepack/pnpm, pytest / pytest-asyncio.

---

## 1. 设计边界

- 只覆盖单机本机部署，不实现内网多机部署编排。
- 不替换现有 Docker/Compose 生产链路。
- 不新增独立运维面板，不做远程机器管理。
- 不引入新的消息队列或 Redis 依赖。
- 不把 `pnpm dev` 当作部署方案，必须支持 `pnpm build` 之后的本机启动。
- 不改变现有 API 路由语义，不重写 Job / Workflow / Settings 业务逻辑。

## 2. 目标能力

### 2.1 必须支持

- 一条命令构建 Web 前端产物。
- 一条命令执行数据库迁移。
- 一条命令启动 API。
- 一条命令启动 Job Worker。
- 一条命令启动本机联动模式，至少可同时拉起 API 和 Worker。
- API 在本机模式下可直接托管 `web/dist`，实现同源访问。
- 本机模式的启动说明必须写入 `README.md` 和 `docs/WebDeployment.md`。

### 2.2 暂不支持

- 自动安装系统级 PostgreSQL。
- 自动拉起反向代理或 Nginx。
- 多节点调度、水平扩展、分布式 Worker。
- 远程 SSH/堡垒机部署。
- Windows 专用批处理脚本。

## 3. 推荐方案

### 3.1 推荐方案：Python launcher + API 静态托管

新增 `scripts/web_local.py` 作为本机部署入口，提供以下子命令：

- `build`：执行前端构建。
- `migrate`：执行数据库迁移。
- `start-api`：启动 API，并在 `WEB_STATIC_DIR` 指向 `web/dist` 时托管前端静态资源。
- `start-worker`：启动数据库轮询式 Job Worker。
- `start`：按本机模式启动 API 和 Worker，必要时先校验前端产物是否存在。

推荐原因：

- 复用现有 Python CLI 和配置加载逻辑，不重复造一套 shell 编排。
- 跨平台性比 shell 脚本更好，后续更容易补测试。
- API 同源托管前端后，不需要额外解决本机 CORS 和路由刷新问题。

### 3.2 备选方案：纯 shell 脚本

用 `scripts/web-local.sh` 包装构建和启动命令。

优点：

- 文件更少，入门成本低。

缺点：

- 进程管理、错误处理和测试都更脆弱。
- 跨平台能力差。
- 后续扩展本机托管逻辑时容易变成碎片化脚本。

### 3.3 不推荐方案：继续依赖 Vite dev / preview

直接用 `pnpm dev` 或 `pnpm preview` 作为本机部署入口。

优点：

- 几乎不需要新增代码。

缺点：

- 不是部署方案，只是前端开发服务器。
- 与生产静态托管方式不一致。
- 需要额外处理跨域或代理配置，验收路径不稳定。

## 4. 详细设计

### 4.1 本机 launcher

`scripts/web_local.py` 负责协调本机部署动作，但不替代现有 `cli/main.py`。

建议的行为：

- `build` 只负责前端产物构建，不启动服务。
- `migrate` 只负责数据库迁移，不构建前端。
- `start-api` 启动 API 进程，并根据环境变量决定是否托管静态文件。
- `start-worker` 启动 Job Worker。
- `start` 负责联动启动 API 和 Worker，适合单机验证。
- `start` 默认不自动执行前端构建；若 `web/dist` 缺失，应提示先运行 `build`。

launcher 需要做的基础校验：

- `config/app.yaml` 是否存在。
- 数据库连接配置是否可用。
- `web/dist/index.html` 是否存在。
- 需要的外部命令是否可执行，例如 `corepack`、`pnpm`、`uvicorn`。

### 4.2 API 本机静态托管

在 API 启动逻辑里增加一个可选的静态资源托管入口：

- 当 `WEB_STATIC_DIR` 环境变量存在且目录有效时，API 同时托管前端静态资源。
- 前端静态资源从 `web/dist` 读取。
- 对 SPA 路由提供回退，让刷新 `/jobs`、`/reports` 这类前端路由时不会 404。
- 现有 `/api/*`、`/health`、`/docs` 路由保持优先级，不被静态回退覆盖。

这样本机模式下可以直接通过 `http://localhost:8000` 访问：

- 前端页面
- FastAPI 文档
- `/api/ui/v1/*`

### 4.3 启动顺序

本机推荐顺序：

1. 安装 Python 依赖和前端依赖。
2. 构建前端产物。
3. 准备 PostgreSQL。
4. 执行数据库迁移。
5. 启动 API。
6. 启动 Worker。
7. 打开浏览器访问 API 根路径。

### 4.4 错误处理

- 构建失败时，launcher 应以非零退出码退出，并打印失败命令。
- 迁移失败时，launcher 不应继续启动 API 或 Worker。
- 启动 API 失败时，应尽快结束整个联动进程。
- 启动 Worker 失败时，应把失败状态暴露到终端，不静默吞掉。
- `web/dist` 缺失时，`start` 应给出明确提示，避免用户误以为部署成功。
- `start` 不应隐式调用 `build`，避免把长耗时构建动作塞进启动命令。

## 5. 文件边界

- `scripts/web_local.py`
  - 本机部署 launcher，负责 build / migrate / start-api / start-worker / start。
- `api/app.py`
  - 可选的本机静态资源托管入口。
- `docs/WebDeployment.md`
  - 增加非 Docker 本机部署说明、命令顺序和前置条件。
- `README.md`
  - 增加本机启动入口摘要。
- `web/README.md`
  - 增加 `pnpm build` 之后的本机产物说明。
- `tests/unit/`
  - 补 launcher 入口和静态托管相关单测或 smoke test。
- `docs/Web-TaskList.md`
  - 为非 Docker 本机部署新增后续跟踪任务，待实现完成后更新状态。

## 6. 验收标准

- `python -m scripts.web_local build` 可以构建前端产物。
- `python -m scripts.web_local migrate` 可以执行数据库迁移。
- `python -m scripts.web_local start-api` 可以启动 API，并在配置本机静态托管时直接提供前端页面。
- `python -m scripts.web_local start-worker` 可以启动 Job Worker。
- `python -m scripts.web_local start` 可以在单机上同时拉起 API 和 Worker。
- 本机模式下，浏览器访问 `http://localhost:8000` 可以看到 Web 页面。
- 本机模式下，前端调用 `/api/ui/v1/*` 不需要 Docker，也不依赖独立反向代理。
- Docker/Compose 方案保持可用，且不受本任务影响。
- 对应测试和文档更新全部通过并可追溯。

## 7. 实施提示

- 这是一个单机本机部署增强，不是整体架构重写。
- 优先复用 `cli.main` 中已有的数据库迁移、Worker 和构建逻辑。
- 如果静态托管实现过于复杂，先保证 `start-api` + `start-worker` 闭环，再补 SPA 回退。
- 不要把本机模式写成与 Docker 并行的第二套生产标准，本文只定义“本机可验收”路径。
