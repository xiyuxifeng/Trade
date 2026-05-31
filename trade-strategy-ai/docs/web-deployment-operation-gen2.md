# trade-strategy-ai Web 部署与运维手册

> 适用范围：`trade-strategy-ai` Web 管理后台的部署、配置、监控、备份与故障排查责任人。  
> 目标：给出可执行的部署顺序、运行时拓扑、配置说明、健康检查与排障路径。用户操作说明见 [`web-user-manual.md`](web-user-manual.md)。

---

## 1. 系统架构

默认生产拓扑由 **四个独立进程/服务** 组成（Redis 非必需）：

```text
Browser
  ├─→ Web 静态资源（web/dist 或 Nginx）
  └─→ FastAPI API（/api/ui/v1/*）
         └─→ Service Layer
               └─→ PostgreSQL

Job Worker（独立进程）
  └─→ PostgreSQL（轮询领取 Job）
```

| 组件 | 职责 | 默认端口 |
|------|------|----------|
| FastAPI API | UI BFF、健康检查、业务 API | 8000 |
| Web 前端 | 静态 SPA（React + Vite） | 3000（Docker）或 API 托管 |
| Job Worker | 数据库轮询执行长任务 | 无 HTTP 端口 |
| PostgreSQL | Job 状态、审计、业务元数据 | 5432 |

**重要**：API 与 Worker 必须分离进程。Worker 不依赖浏览器，不承担页面职责。

---

## 2. 环境要求

| 依赖 | 版本要求 |
|------|----------|
| Python | 3.11+ |
| Node.js | 18+（推荐 corepack + pnpm） |
| PostgreSQL | 15 推荐 |
| Docker / Compose | 可选，用于容器化部署 |

### Python 环境

建议在 workspace 根目录或项目根目录创建虚拟环境。不要依赖 `cd ..` 这类隐式路径。

```bash
cd <workspace>
python -m venv .venv
source .venv/bin/activate

cd trade-strategy-ai
pip install -e ".[dev]"
```

### 数据库准备

```bash
brew install postgresql@15
brew services start postgresql@15
psql postgres -c "CREATE ROLE trade WITH LOGIN PASSWORD '<strong-password>';"
createdb -O trade trade_strategy_ai
```

连通性校验：

```bash
python -m cli.main db-check --config config/app.yaml
```

---

## 3. 配置与密钥

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 异步连接串 | `postgresql+asyncpg://trade:<pwd>@localhost:5432/trade_strategy_ai` |
| `DATABASE_ECHO` | SQL 日志 | `false` |
| `LOG_LEVEL` | 应用日志级别 | `INFO` / `WARNING` / `ERROR` / `DEBUG` |
| `WEB_STATIC_DIR` | API 托管前端时指定 dist 目录 | `web/dist` |
| `CONFIG_PATH` | 默认配置文件 | `config/app.yaml` |

禁止将以下内容提交到 Git：数据库密码、Cookie、Token、API Key、Webhook Secret。

### 配置边界

| 配置层 | 位置 | 影响范围 | 说明 |
|------|------|----------|------|
| 部署配置 | 环境变量 / `.env` / `config/app.yaml` | API、Worker、数据库、定时默认值 | 运维维护，重启后生效 |
| 运行配置 | Web `/profiles` | 文章、市场数据、策略、回测上下文 | admin 在页面导入和维护 |
| 任务参数 | 各业务页面表单 | 单次 Job 的执行行为 | 如 `force`、日期、标的、回测区间 |

结论：Web 日常操作优先使用 Profile。`config/app.yaml` 和 `config/app.template.yaml` 只作为导入源；它们已包含 `strategy` 和 `risk` 配置段。`config_path` 仅作为 CLI/debug/历史兼容字段，不建议交付用户手动填写。
补充：如果 `/api/ui/v1/system/status` 仍显示 `default` 且没有 snapshot，这表示当前只是兜底启动，用户应优先通过 `/profiles/import` 导入正式 Profile，而不是继续把 fallback 当正式运行态。
补充：`config/rules/behavior_rules.yaml` 是 Persona 行为标签的只读规则源，Web `/persona` 只提供预览与解释，不提供编辑入口。
补充：`/api/ui/v1/system/status` 展示的 `Profile 上下文` 只读取启动环境显式注入的 `PROFILE_ID` / `PROFILE_SNAPSHOT_ID`，不从 `config_path` 反推；如果没有注入，界面会显示 `未绑定`，这是正常情况。

---

## 4. 部署方式

### 4.1 Docker Compose（推荐生产）

> 使用前请先确认 compose 文件中的服务名确实为 `db`、`api`、`worker`、`web`。

```bash
# 1. 构建镜像
docker compose build

# 2. 启动数据库
docker compose up -d db

# 3. 执行数据库迁移
docker compose run --rm api python -m cli.main db-migrate --config config/app.yaml

# 4. 创建管理员（首次）
docker compose run --rm api python -m cli.main seed-admin --username <admin-name> --password <strong-password>

# 5. 启动 API、Worker、Web
docker compose up -d api worker web
```

健康检查：

```bash
curl http://localhost:8000/health
curl http://localhost:3000/
```

### 4.2 本机非 Docker（单机验证）

```bash
export LOG_LEVEL=WARNING
python -m scripts.web_local build
python -m scripts.web_local migrate
python -m scripts.web_local seed-admin --username <admin-name> --password <strong-password>
python -m scripts.web_local start
```

分步启动：

```bash
export LOG_LEVEL=WARNING
python -m scripts.web_local build
python -m scripts.web_local migrate
python -m scripts.web_local seed-admin --username <admin-name> --password <strong-password>
python -m scripts.web_local start-api    # 终端 1
python -m scripts.web_local start-worker # 终端 2
```

本机模式约定：

- `build`：在 `web/` 下执行 `corepack pnpm build`
- `migrate`：执行 Alembic 迁移
- `seed-admin`：创建管理员；交付/生产环境必须显式传入用户名和强密码
- `start-api` / `start`：要求 `web/dist/index.html` 已存在
- 设置 `WEB_STATIC_DIR=web/dist` 时，API 直接托管前端
- `scripts.web_local` 会自动读取项目根目录 `.env`，并优先保留当前 shell 已设置的环境变量；本机调试时可直接把 `TGB_COOKIE`、`DATABASE_URL` 等写入 `.env`
- Profile 里的敏感字段会在运行时从环境变量回填，例如 `crawl.auth.tgb.cn.cookie` 会从 `TGB_COOKIE` 注入；如果对应环境变量缺失，运行时会直接报错，不会静默兜底；看到 `***` 不代表运行时没有可用值。
- `alerting` 和 `Kaipan` 相关环境变量会在实际使用对应功能时再校验；缺失时会返回配置提示，不会让 Web 启动阶段直接 500。
- 启动 `scripts.web_local` 时，脚本会在终端输出一段“本机脚本已读取到以下关键配置”的摘要，方便确认当前生效的是哪一组配置；敏感值会脱敏显示
- 浏览器访问 `http://localhost:8000`

停止：

```bash
python -m scripts.web_local stop
```

### 4.3 手动非 Docker 启动

```bash
python -m cli.main db-migrate --config config/app.yaml
python -m cli.main seed-admin --username <admin-name> --password <strong-password>

# 终端 1：API
LOG_LEVEL=WARNING uvicorn api.main:app --host 0.0.0.0 --port 8000

# 终端 2：Worker
LOG_LEVEL=WARNING python -m cli.main job-worker-start --config config/app.yaml

# 前端（需先构建）
cd web && corepack pnpm build
```

生产环境不要使用 `uvicorn --reload`。

### 4.4 访问地址口径

| 部署方式 | 用户访问地址 | API 地址 |
|---|---|---|
| Docker Compose | `http://<host>:3000` | `http://<host>:8000` |
| 本机 API 托管前端 | `http://localhost:8000` | 同地址 `/api/...` |
| Nginx/Caddy 反向代理 | `https://<your-domain>` | 由 `/api/` 反代到 `:8000` |

---

## 5. 首次部署清单

- [ ] 安装 Python 3.11+、Node.js、PostgreSQL 或 Docker
- [ ] 创建虚拟环境并安装依赖
- [ ] 配置 `DATABASE_URL` 或 `.env`
- [ ] 确认 `config/app.yaml` 存在
- [ ] 启动 PostgreSQL
- [ ] 执行 `db-migrate`
- [ ] 执行 `seed-admin` 创建管理员，使用强密码
- [ ] 构建 Web 前端
- [ ] 启动 API
- [ ] 启动 Worker
- [ ] 部署/托管 Web 静态资源
- [ ] 访问 `/health` 确认 API 正常
- [ ] 登录 Web，导入 Profile
- [ ] 提交测试 Job，确认 Worker 能从 `pending` 变为 `running/succeeded`
- [ ] 在 `/artifacts` 确认产物可访问

---

## 6. 健康检查与 Smoke Test

### 健康检查端点

| 端点 | 用途 |
|------|------|
| `GET /health` | 服务存活探测 |
| `GET /api/ui/v1/system/status` | API、DB、目录状态 |
| `GET /api/ui/v1/system/dashboard` | 失败任务、数据新鲜度、告警 |
| Web `/system/health` | 页面化健康检查（admin） |
| Web `/dashboard` | 运维总览 |

### Smoke Test

```text
1. curl /health 返回正常
2. Web 登录成功
3. /profiles 可导入或看到 validated Profile
4. 提交一个低风险测试 Job
5. /jobs 中看到 pending → running → succeeded 或明确失败日志
6. /artifacts 中能查看关联产物
7. /alerts 中能看到告警配置状态，必要时发送测试告警
```

---

## 7. 用户与鉴权

### 创建管理员

```bash
python -m cli.main seed-admin --username <name> --password <strong-password>
```

交付/生产环境不得使用默认用户名密码。首次交付时，运维必须明确告知：

- 登录页使用 API Key，还是使用 username/password。
- API Key 如何创建、轮换、禁用。
- admin、operator、viewer 三类角色分别给谁使用。

### 角色

```text
anonymous < viewer < operator < admin
```

- 提交 Job：至少 operator
- 系统管理、备份恢复、Kaipan：至少 admin

---

## 8. 备份与恢复

恢复能力分两层，不可混用：

| 层级 | 入口 | 范围 |
|------|------|------|
| 配置恢复 | 配置管理 `/profiles` | `config/app.yaml` 及受管配置 |
| 项目级备份 | 系统管理 `/system/backup` | 数据库 + Job 元数据 + artifacts + 可选 processed |

> 重要：项目级备份是应用级回滚手段，不替代 PostgreSQL 物理备份、云数据库快照或异地灾备。

创建项目备份：在 `/system/backup` 提交 `backup-data`。  
恢复项目备份：提交 `restore-data`，admin 权限，需二次确认。

恢复后检查：

- `/jobs` 能否正常领取任务
- `/dashboard` 或 `/system/health` 是否正常
- 相关产物是否可访问

---

## 9. 数据库迁移

```bash
python -m cli.main db-migrate --config config/app.yaml
```

Web 触发：`/system/db-migrate` 提交 `db-migrate` Job。迁移前建议先创建项目备份。

---

## 10. 监控与日常运维

| 页面 | 关注内容 |
|------|----------|
| `/dashboard` | 系统健康、失败任务、告警 |
| `/alerts` | 告警启用状态、历史记录、确认/解决、测试告警 |
| `/jobs` | 任务状态、耗时异常 |
| `/system/health` | API、DB、Worker、存储 |
| `/system/audit` | 高风险操作、权限拒绝 |

关注信号：失败任务增多、任务耗时变长、数据新鲜度异常、Worker 心跳丢失、磁盘空间不足。

---

## 11. 常见故障与处理

| 现象 | 检查/处理 |
|------|-----------|
| 页面打不开 | `curl http://localhost:8000/health`、检查前端构建、反向代理、端口占用 |
| 任务一直 pending | 启动/重启 Worker，检查数据库连接和 Worker 日志 |
| 任务执行失败 | 查看 `/jobs/:jobId` 日志，核对 Profile、日期、symbols、目录权限 |
| API 返回 401 | API Key 或登录状态无效，重新登录或重新发放 API Key |
| API 返回 403 | 角色不足，确认是否 operator/admin |
| 数据库连接失败 | 检查 `DATABASE_URL`、PostgreSQL 状态、防火墙、Docker 网络 |
| 前端版本不更新 | 重新 build，确保 `index.html` 不长缓存 |
| 恢复后数据不对 | 检查快照目录、`manifest.json`、processed 是否包含、恢复后是否被覆盖 |

Worker 日志：

```bash
# Docker
docker compose logs -f worker

# 本机
python -m scripts.web_local start-worker
```

---

## 12. 升级与发布

推荐流程：

```text
1. 在测试环境验证新版本
2. 创建项目备份
3. 拉取代码 / 构建新镜像
4. 如有 schema 变更，执行 db-migrate
5. 构建前端
6. 滚动重启：先 Worker，再 API，最后 Web
7. 检查 /health、/dashboard
8. 提交 smoke test Job
```

生产禁止事项：

- 使用 `uvicorn --reload`
- 把临时目录当作正式产物目录
- 敏感值明文写入 Git
- 跳过 db-migrate 直接启动
- 未备份直接 restore-data
- 使用默认管理员密码

---

## 13. 相关文档

| 文档 | 内容 |
|------|------|
| `web-user-manual.md` | 用户操作手册（admin） |
| `../README.md` | 项目总览与快速开始 |
| `New-Web-UI-Information-Architecture.md` | Web 信息架构 |

---

*文档版本：修订交付版。重点移除默认密码风险、统一 Profile 口径、补充 smoke test、访问地址与备份边界。*
