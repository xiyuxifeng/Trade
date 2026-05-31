# trade-strategy-ai Web 部署与运维手册

> 适用范围：`trade-strategy-ai` Web 管理后台的部署、配置、监控、备份与故障排查责任人。
>
> 目标：给出可执行的部署顺序、运行时拓扑、配置说明、健康检查与排障路径。用户操作说明见 [`web-user-manual.md`](web-user-manual.md)。

---

## 1. 系统架构

### 1.1 运行时组件

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
| **FastAPI API** | UI BFF、健康检查、业务 API | 8000 |
| **Web 前端** | 静态 SPA（React + Vite） | 3000（Docker）或 API 托管 |
| **Job Worker** | 数据库轮询执行长任务 | 无 HTTP 端口 |
| **PostgreSQL** | Job 状态、审计、业务元数据 | 5432 |

**重要**：API 与 Worker **必须分离进程**。Worker 不依赖浏览器，不承担页面职责。

### 1.2 关键目录

所有相对路径默认以 `trade-strategy-ai` 项目根目录解析：

| 目录 | 用途 |
|------|------|
| `config/` | 应用配置（`app.yaml` 等） |
| `data/` | 业务数据根目录 |
| `data/backups/` | 配置备份与项目快照 |
| `data/artifacts/` | Job 产物 |
| `data/processed/` | 处理后数据（备份可选包含） |
| `logs/` | API 与 Worker 日志 |
| `web/dist/` | 前端构建产物 |
| `.pids/` | 本机 launcher 的 PID 文件 |

### 1.3 暂不依赖 Redis

当前默认方案 **不依赖 Redis**。任务调度与状态追踪由数据库轮询 Worker 完成。`docker-compose.yml` 中 Redis 仅在 `profiles: ["redis"]` 下可选启用，非默认必需。

---

## 2. 环境要求

### 2.1 软件依赖

| 依赖 | 版本要求 |
|------|----------|
| Python | 3.11+ |
| Node.js | 18+（前端构建，推荐 corepack + pnpm） |
| PostgreSQL | 15（推荐） |
| Docker / Compose | 可选，用于容器化部署 |

### 2.2 Python 环境

在 workspace 根目录创建虚拟环境并安装：

```bash
cd ..
python -m venv .venv
source .venv/bin/activate

cd trade-strategy-ai
pip install -e ".[dev]"
```

### 2.3 数据库准备

**macOS Homebrew 示例**：

```bash
brew install postgresql@15
brew services start postgresql@15
```

**创建数据库与用户**：

```bash
psql postgres -c "CREATE ROLE trade WITH LOGIN PASSWORD 'trade';"
createdb -O trade trade_strategy_ai
```

**连通性校验**：

```bash
python -m cli.main db-check --config config/app.yaml
```

---

## 3. 配置与密钥

### 3.1 配置来源

配置通过以下方式注入（优先级由应用解析逻辑决定）：

- 环境变量
- `.env` 文件（不要提交到 Git）
- `config/app.yaml`

### 3.2 关键环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 异步连接串 | `postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai` |
| `DATABASE_ECHO` | SQL 日志 | `false` |
| `LOG_LEVEL` | 应用日志级别（API / Worker 共用，部署时设置即可） | `INFO` / `WARNING` / `ERROR` / `DEBUG` |
| `WEB_STATIC_DIR` | API 托管前端时指定 dist 目录 | `web/dist` |
| `CONFIG_PATH` | 默认配置文件 | `config/app.yaml` |

Docker Compose 中 API 与 Worker 共享：

```yaml
DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/trade_strategy_ai
LOG_LEVEL: WARNING
```

### 3.3 敏感信息

**禁止** 将以下内容提交到 Git：

- 数据库密码
- Cookie / Token
- API Key
- Webhook Secret

Web 配置页只展示 **脱敏值**；保存时由服务端校验并写回。

### 3.4 应用配置键（节选）

`config/app.yaml` 中与业务相关的主要键：

| 键 | 含义 |
|----|------|
| `schedule.enable` | 是否启用定时调度 |
| `schedule.pre_market_time` | 盘前定时 |
| `schedule.after_close_time` | 盘后定时 |
| `alerting.enabled` | 是否启用告警系统；关闭后告警中心仍可查看历史，但不会发送外部通知 |
| `alerting.channel` | 告警通道（`dingtalk` / `feishu` / `wecom` / `generic`） |
| `alerting.console_output` | 是否输出到本地日志；仅本地输出不等于外部通知已开通 |
| `alerting.aggregation.window_minutes` | 告警聚合时间窗口 |
| `alerting.aggregation.max_count` | 聚合达到多少条后分段发送 |
| `alerting.<channel>.webhook_url` | 对应通道的 Webhook；没有它就只能本地输出，无法发外部消息 |
| `evaluation.min_expected_return` | 最低预期收益 |
| `evaluation.loss_trigger` | 亏损触发阈值 |
| `data.market_universe_snapshot_dir` | 候选池快照文件目录（当前仍是文件存储） |

> 说明：`data.market_data_cache_dir` 已不作为交付模板必填项暴露；它仅保留为运行时兼容缓存目录，不建议作为交付配置入口。
>
> 说明：告警系统的交付配置以 `alerting.enabled` 为总开关。启用后，管理员可在 Web 的 **告警中心**（`/alerts`）查看历史、确认/解决告警，并通过 **发送测试告警** 验证 Webhook 是否可用。
>
> 说明：日志级别不需要写入 `config/app.yaml`。部署时通过环境变量 `LOG_LEVEL` 设置即可，API 和 Worker 会读取同一值。Docker Compose 可在 `environment` 中设置，手动启动可直接在命令前加 `LOG_LEVEL=WARNING` 之类的前缀。

### 3.5 配置边界与生效顺序

为了避免把“部署配置”和“业务运行配置”混在一起，建议按下面理解：

| 配置层 | 位置 | 影响范围 | 说明 |
|------|------|----------|------|
| 部署配置 | 环境变量 / `.env` / `config/app.yaml` | API、Worker、数据库、定时默认值 | 由运维维护，重启后生效 |
| 运行配置 | Web `/profiles` | 文章、市场数据、策略、回测的运行上下文 | 由 admin 在页面导入和维护 |
| 任务参数 | 各业务页面表单 | 单次 Job 的执行行为 | 例如 `force`、日期、标的、回测区间等 |

**优先级**：

1. 页面任务参数优先于默认值
2. Profile 优先于旧的路径入口
3. `config/app.yaml` 提供全局默认值

**结论**：

- 运维负责把系统启动起来，并保证默认配置正确。
- admin 在 Web 里通过 `/profiles` 和各业务页面完成日常操作。
- Web 日常用户只需要选择当前 Profile，页面会自动绑定运行态，不需要手工编辑 `config_path`。
- `config/app.yaml` 和 `config/app.template.yaml` 只作为导入源和 CLI 调试入口，不应作为 Web 主流程的正式事实源；其中已包含 `strategy` 和 `risk` 配置段，用户不需要再单独维护独立的策略/风控配置文件。
- 如果 `/api/ui/v1/system/status` 里仍显示 `default` 且没有绑定 snapshot，这只是兜底启动态，不代表正式配置已经导入；应优先进入 `/profiles/import` 生成正式 Profile。
- `config/rules/behavior_rules.yaml` 仍是行为标签规则的只读配置源；Web 的 `/persona` 页面只提供预览与解释，不提供在线编辑入口。
- `/api/ui/v1/system/status` 里的 `Profile 上下文` 只表示环境变量注入的显式绑定，默认不会从 `config_path` 推断；没有注入时显示 `unset` / `未绑定`，这是为了避免把运行环境和业务 Profile 混为一谈。

---

## 4. 部署方式

### 4.1 方式 A：Docker Compose（推荐生产）

**适用**：团队共享、内网交付、生产环境。

#### 启动顺序

```bash
# 1. 构建镜像
docker compose build

# 2. 启动数据库
docker compose up -d db

# 3. 执行数据库迁移
docker compose run --rm api python -m cli.main db-migrate --config config/app.yaml

# 4. 创建默认管理员（首次）
docker compose run --rm api python -m cli.main seed-admin --username Dev --password <your-password>

# 5. 启动 API、Worker、Web
docker compose up -d api worker web
```

#### 服务说明

| 服务 | 镜像 | 端口 | 命令 |
|------|------|------|------|
| `db` | postgres:15 | 5432 | — |
| `api` | trade-strategy-ai-api:local | 8000 | uvicorn |
| `worker` | trade-strategy-ai-api:local | — | job-worker-start |
| `web` | trade-strategy-ai-web:local | 3000→80 | Nginx 托管 dist |

Worker 默认参数：`--limit 10 --interval-seconds 5 --stale-after-minutes 15`。

#### 健康检查

```bash
curl http://localhost:8000/health
curl http://localhost:3000/
```

---

### 4.2 方式 B：本机非 Docker（单机验证）

**适用**：开发完成后的本机验证、单用户调试。

使用仓库内 launcher 脚本：

```bash
export LOG_LEVEL=WARNING
python -m scripts.web_local build
python -m scripts.web_local migrate
python -m scripts.web_local seed-admin
python -m scripts.web_local start
```

**分步启动**：

```bash
export LOG_LEVEL=WARNING
python -m scripts.web_local build
python -m scripts.web_local migrate
python -m scripts.web_local seed-admin
python -m scripts.web_local start-api    # 终端 1
python -m scripts.web_local start-worker # 终端 2
```

**本机模式约定**：

- `build`：在 `web/` 下执行 `corepack pnpm build`
- `migrate`：执行 Alembic 迁移
- `seed-admin`：创建默认管理员（默认 Dev/wanghui，可通过参数修改）
- `start-api` / `start`：要求 `web/dist/index.html` 已存在
- 设置 `WEB_STATIC_DIR=web/dist` 时，API 直接托管前端
- `LOG_LEVEL`：在启动前通过环境变量设置，例如 `export LOG_LEVEL=WARNING`；`scripts.web_local` 启动的 API / Worker 会继承该值
- 浏览器访问 **`http://localhost:8000`** 即可同时使用页面与 API
- PID 文件写入 `.pids/api.pid`、`.pids/worker.pid`

**停止本机服务**：

```bash
python -m scripts.web_local stop
```

---

### 4.3 方式 C：手动非 Docker 启动

如果需要临时调整日志级别，可以在命令前直接加环境变量，例如：

```bash
LOG_LEVEL=WARNING uvicorn api.main:app --host 0.0.0.0 --port 8000
LOG_LEVEL=WARNING python -m cli.main job-worker-start --config config/app.yaml
```

```bash
python -m cli.main db-migrate --config config/app.yaml
python -m cli.main seed-admin --username Dev --password <your-password>

# 终端 1：API
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 终端 2：Worker
python -m cli.main job-worker-start --config config/app.yaml

# 前端（需先构建）
cd web && corepack pnpm build
# 单独部署 dist，或设置 WEB_STATIC_DIR 由 API 托管
```

**注意**：生产环境 **不要** 使用 `--reload`。

---

### 4.4 方式 D：内网反向代理部署

**适用**：团队内网、HTTPS 终止、多用户访问。

```text
Browser → Reverse Proxy (Nginx/Caddy)
            ├─ /          → web/dist 静态资源
            └─ /api/      → FastAPI :8000
Worker → PostgreSQL
```

**代理配置原则**：

1. TLS 在代理层终止
2. `/` 直接返回 `web/dist` 静态文件
3. `/api/` 转发到 FastAPI 后端
4. `/health` 与 `/api/ui/v1/system/status` 保持可探测
5. 带内容哈希的静态资源：`Cache-Control: public, max-age=31536000, immutable`
6. `index.html`：**不要** 长缓存
7. API 响应：默认不缓存
8. 上传大小与超时按实际任务规模单独配置

**最小 Nginx 示意**（需按实际路径调整）：

```nginx
server {
    listen 443 ssl;
    server_name trade.example.com;

    root /path/to/trade-strategy-ai/web/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_read_timeout 600s;
        client_max_body_size 50m;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

---

## 5. 首次部署清单

按顺序完成：

- [ ] 安装 Python 3.11+、Node.js、PostgreSQL
- [ ] 创建虚拟环境并 `pip install -e ".[dev]"`
- [ ] 配置 `DATABASE_URL` 或 `.env`
- [ ] 确认 `config/app.yaml` 存在
- [ ] 启动 PostgreSQL
- [ ] 执行 `db-migrate`
- [ ] 执行 `seed-admin` 创建管理员
- [ ] 构建 Web 前端（`pnpm build`）
- [ ] 启动 API
- [ ] 启动 Worker
- [ ] 部署/托管 Web 静态资源
- [ ] 访问 `/health` 确认 API 正常
- [ ] 登录 Web，导入 Profile
- [ ] 提交测试 Job，确认 Worker 能领取执行

---

## 6. 启动与健康检查

### 6.1 推荐启动顺序

```text
1. PostgreSQL
2. db-migrate（版本升级时）
3. FastAPI API
4. Job Worker
5. Web 静态资源
6. 检查 Dashboard / System Health / Jobs
```

### 6.2 健康检查端点

| 端点 | 用途 |
|------|------|
| `GET /health` | 服务存活探测（适合负载均衡/Compose healthcheck） |
| `GET /api/ui/v1/system/status` | 机器可读：API、DB、目录状态 |
| `GET /api/ui/v1/system/dashboard` | 人工运维摘要：失败任务、数据新鲜度、告警 |
| Web `/system/health` | 页面化健康检查（admin） |
| Web `/dashboard` | 运维总览 |

**建议**：这三处有错误时，先处理基础设施，再处理业务页面。

### 6.3 Worker 运行方式

Worker 使用 **数据库轮询模式**：

- 领取 `pending` Job
- 更新状态、写入日志与产物路径
- 支持心跳、锁、超时、重试、取消
- 服务重启后可恢复任务状态

**限制**：高并发或多实例场景扩展性有限；未来可按需评估 Redis/队列方案。

### 6.4 日志

建议拆分：

- **API 日志**：HTTP 请求、鉴权、BFF 错误
- **Worker 日志**：Job 执行、handler 异常

Job 产物按 Job ID 或业务日期归档，确保可回溯参数、日志与最终结果。

---

## 7. 用户与鉴权

### 7.1 创建管理员

**CLI**：

```bash
python -m cli.main seed-admin --username <name> --password <password>
```

**Web**（admin）：`/system/users` 添加用户并设置角色。

### 7.2 角色与 API Key

Web 使用 **API Key** 鉴权。角色层级：

```text
anonymous < viewer < operator < admin
```

- 提交 Job：至少 **operator**
- 系统管理、备份恢复、Kaipan：至少 **admin**

### 7.3 用户管理（Web）

在 `/system/users` 可：

- 添加用户（username、display_name、role、password）
- 修改角色与密码
- 禁用/删除用户

---

## 8. 备份与恢复

恢复能力分 **两层**，不可混用：

| 层级 | 入口 | 范围 |
|------|------|------|
| **配置恢复** | 配置管理 `/profiles` | `config/app.yaml` 及受管配置 |
| **项目级备份** | 系统管理 `/system/backup` | 数据库 + Job 元数据 + artifacts + 可选 processed |

### 8.1 创建项目备份

在 `/system/backup` 提交 **`backup-data`** Job：

| 参数 | 含义 |
|------|------|
| `profile_id` | 关联 Profile |
| `backup_dir_id` | 备份目录 ID |
| `include_processed` | 是否包含 `data/processed` |

备份写入 `data/backups/<timestamp>/`，至少包含：

- `manifest.json`
- `db/*.json`
- `artifacts/`
- `processed/`（若启用）

### 8.2 恢复项目备份

提交 **`restore-data`** Job（**admin**，需二次确认）：

| 参数 | 含义 |
|------|------|
| `backup_id` | 快照 ID |
| `include_processed` | 是否恢复 processed |
| `force` | 强制覆盖 |

**恢复后检查**：

- `/jobs` 能否正常领取任务
- `/dashboard` 或 `/system/health` 是否正常
- 相关产物是否可访问

### 8.3 回滚演练（推荐）

```text
1. 在 /system/backup 创建当前状态快照
2. 在测试环境恢复一份已知快照
3. 验证 DB、Job 列表、产物路径
4. 发布失败时，恢复上一份已验证快照
5. 若仅配置问题，在 /profiles 恢复配置备份
```

---

## 9. 数据库迁移

### 9.1 CLI 迁移

```bash
python -m cli.main db-migrate --config config/app.yaml
```

### 9.2 Web 触发（admin）

`/system/db-migrate` 提交 **`db-migrate`** Job（高风险，需确认）。

**注意**：迁移前建议先创建项目备份。

---

## 10. 监控与日常运维

### 10.1 关注页面

| 页面 | 关注内容 |
|------|----------|
| `/dashboard` | 系统健康、失败任务、告警 |
| `/alerts` | 告警启用状态、历史记录、确认/解决、测试告警 |
| `/jobs` | 任务状态、耗时异常 |
| `/system/health` | API、DB、Worker、存储 |
| `/system/audit` | 高风险操作、权限拒绝 |

### 10.2 关注信号

- 最近失败任务增多
- 任务耗时明显变长
- 数据新鲜度异常
- Worker 心跳丢失（任务长期 pending）
- 磁盘空间不足（`data/`、`logs/`）

### 10.3 追踪顺序

```text
1. Dashboard / System Health
2. 对应 Job 详情与日志
3. 关联 Artifacts
4. Profile / 配置是否正确
5. System Audit 是否有异常操作
```

---

## 11. 常见故障与处理

### 11.1 页面打不开

| 检查项 | 命令/方法 |
|--------|-----------|
| API 是否启动 | `curl http://localhost:8000/health` |
| 前端是否构建 | 确认 `web/dist/index.html` 存在 |
| API Key 是否正确 | 重新登录 |
| 反向代理配置 | 检查 `/` 与 `/api/` 转发 |
| 端口占用 | `lsof -i :8000` / `:3000` |

### 11.2 任务一直 pending

| 原因 | 处理 |
|------|------|
| Worker 未启动 | 启动 Worker |
| Worker 崩溃 | 查看 Worker 日志，重启 |
| 数据库不可连 | 检查 `DATABASE_URL`、PostgreSQL 状态 |
| Job 被锁 | 检查 stale 任务，必要时手动处理 |

```bash
# Docker
docker compose logs worker

# 本机
python -m scripts.web_local start-worker
```

### 11.3 任务执行失败

1. 打开 `/jobs/:jobId` 查看错误日志
2. 核对 Job 参数（profile_id、日期、symbols 等）
3. 确认数据库可写、产物目录可写
4. 检查 Profile validation 状态
5. 对支持重试的 Job 点击重试

### 11.4 API 返回 401/403

- 401：API Key 无效或过期 → 重新登录
- 403：角色不足 → 确认用户 role（提交 Job 需 operator+）

### 11.5 数据库连接失败

```bash
python -m cli.main db-check --config config/app.yaml
```

检查：

- PostgreSQL 是否运行
- `DATABASE_URL` 用户名/密码/库名
- 防火墙/端口（5432）
- Docker 网络（Compose 内用 `db` 主机名）

### 11.6 前端版本不更新

- `index.html` 被浏览器或 CDN 缓存 → 禁用长缓存
- 未重新 build → `pnpm build` 后重新部署 dist

### 11.7 恢复后数据不对

- 是否恢复了正确的快照目录
- `manifest.json` 是否存在
- `processed/` 是否在备份中包含
- 恢复后是否有新写入覆盖

### 11.8 磁盘空间不足

清理优先级（**先备份再清理**）：

- 旧 Job 日志（保留策略按合规要求）
- `data/processed/` 中间文件
- 过期 backups（保留最近 N 份）

---

## 12. 升级与发布

### 12.1 推荐发布流程

```text
1. 在测试环境验证新版本
2. 创建项目备份（/system/backup）
3. 拉取代码 / 构建新镜像
4. db-migrate（如有 schema 变更）
5. 构建前端 pnpm build
6. 滚动重启：先 Worker，再 API，最后 Web
7. 检查 /health、/dashboard
8. 提交 smoke test Job
```

### 12.2 Docker 升级

```bash
docker compose build
docker compose run --rm api python -m cli.main db-migrate --config config/app.yaml
docker compose up -d api worker web
```

### 12.3 生产禁止事项

- 使用 `uvicorn --reload`
- 把临时目录当作正式产物目录
- 敏感值明文写入 Git
- 跳过 db-migrate 直接启动
- 未备份直接 restore-data

---

## 13. 责任边界

| 模块 | 职责 |
|------|------|
| **配置管理 `/profiles`** | Profile 与配置文件 |
| **告警中心 `/alerts`** | 告警历史、确认/解决、测试验证 |
| **系统管理 `/system/backup`** | 项目快照与回滚 |
| **Dashboard / System Health** | 运维摘要与探测 |
| **任务中心 `/jobs`** | 长任务执行与日志 |
| **产物中心 `/artifacts`** | 输出文件索引与下载 |

不要在错误页面执行不属于该模块的高风险操作。

---

## 14. 快速命令参考

```bash
# 数据库
python -m cli.main db-check --config config/app.yaml
python -m cli.main db-migrate --config config/app.yaml

# 用户
python -m cli.main seed-admin --username Dev --password <pwd>

# Worker
python -m cli.main job-worker-start --config config/app.yaml

# 本机一键
python -m scripts.web_local build
python -m scripts.web_local migrate
python -m scripts.web_local seed-admin
python -m scripts.web_local start
python -m scripts.web_local stop

# Docker
docker compose up -d db
docker compose run --rm api python -m cli.main db-migrate --config config/app.yaml
docker compose up -d api worker web
docker compose logs -f worker

# 健康检查
curl http://localhost:8000/health
curl http://localhost:8000/api/ui/v1/system/status
```

---

## 15. 相关文档

| 文档 | 内容 |
|------|------|
| [`web-user-manual.md`](web-user-manual.md) | 用户操作手册（admin） |
| [`../README.md`](../README.md) | 项目总览与快速开始 |
| [`New-Web-UI-Information-Architecture.md`](New-Web-UI-Information-Architecture.md) | Web 信息架构 |

---

*文档版本：与当前 Docker Compose 与本机 launcher 实现一致。*
