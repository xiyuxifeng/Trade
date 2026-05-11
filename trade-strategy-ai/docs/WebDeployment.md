# Web 部署拓扑

本文定义 `trade-strategy-ai` Web 管理后台的生产部署边界、运行时组件、目录约定和启动顺序。

目标是让部署说明和当前仓库实现保持一致，避免把开发命令当作生产方案，也避免把尚未落地的 Redis/队列方案写成默认依赖。

## 1. 目标和范围

本部署拓扑适用于两种场景：

1. 单机本地部署
2. 内网部署

本文只描述当前默认可行的生产拓扑，不强制引入外部队列系统。

默认生产拓扑由以下四部分组成：

- FastAPI API
- Web 静态前端
- Job Worker
- PostgreSQL

Redis 只作为后续并发或分布式扩展的候选，不作为默认必需依赖。

## 2. 运行时组件

### 2.1 FastAPI API

FastAPI 负责：

- 提供 `/api/ui/v1/*` UI BFF
- 提供健康检查和系统状态
- 代理到 service 层执行业务逻辑
- 返回 Job、Workflow、Artifact、Settings、Market、Report 相关数据

推荐启动命令：

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

生产环境不要使用 `--reload`。

### 2.2 Web 静态前端

Web 前端在 `web/` 下构建，生产时以静态资源形式部署。

构建后产物默认位于：

```text
web/dist
```

前端通过 `/api/ui/v1/*` 调用后端 API。

### 2.3 Job Worker

Job Worker 是独立进程，负责：

- 从数据库轮询领取 Job
- 刷新心跳
- 执行重试
- 处理超时和取消请求
- 在服务重启后恢复任务状态

Worker 不直接依赖浏览器，不承担页面职责。

### 2.4 PostgreSQL

PostgreSQL 是默认持久化存储，保存：

- Job 状态和参数快照
- 审计信息
- 配置备份元数据
- 业务结果元数据
- 运行时检查状态

### 2.5 运维 Dashboard

`/data-health` 页面现在同时承担两类职责：

- 展示运维 Dashboard 摘要，包含最近失败任务、任务耗时、数据新鲜度、告警摘要和追踪线索
- 展示 `dashboard report` 及其 HTML 产物路径，便于确认数据健康报告是否生成成功

对应的后端接口也分成两层：

- `/api/ui/v1/system/status`：机器可读健康检查，偏向探测和反向代理监控
- `/api/ui/v1/system/dashboard`：人工运维摘要，偏向问题定位和追踪

## 3. 部署模式

### 3.1 单机本地部署

推荐用于：

- 开发完成后的本机验证
- 单用户调试
- 小范围联调

典型结构：

```text
Browser -> FastAPI API -> Service Layer -> PostgreSQL
Browser -> Web 静态文件
Worker -> PostgreSQL
```

单机模式下，API、Worker 和 PostgreSQL 可以部署在同一台机器上，但进程必须分离。

建议启动顺序：

1. 启动 PostgreSQL
2. 执行数据库迁移
3. 启动 FastAPI API
4. 启动 Job Worker
5. 启动或托管 Web 静态资源

### 3.2 内网部署

推荐用于：

- 团队共享访问
- 多人协作联调
- 内网交付

典型结构：

```text
Browser -> Reverse Proxy -> Web 静态资源
Browser -> Reverse Proxy -> FastAPI API -> Service Layer -> PostgreSQL
Worker -> PostgreSQL
```

内网部署应额外考虑：

- HTTPS 终止
- 反向代理转发
- 上传大小限制
- 超时配置
- 日志保留策略

## 4. 配置与密钥注入

推荐使用以下方式注入配置：

- 环境变量
- `.env`
- `config/app.yaml`

敏感信息不要直接提交到 Git：

- 数据库密码
- Cookie
- API key
- Webhook secret
- 其它密钥类配置

Web 设置页只展示脱敏值，保存时由服务端负责校验和写回。

## 5. 文件目录约定

部署和运行时应保持这些目录约定：

- `config/`：应用配置
- `data/`：业务数据根目录
- `data/backups/`：配置备份
- `data/artifacts/`：产物目录
- `logs/`：服务日志
- `web/dist/`：前端构建产物

目录职责要固定，避免不同进程争用同一输出位置。

## 6. 日志与产物

建议将日志拆成两类：

- API 日志
- Worker 日志

Job 相关产物建议按 Job ID 或业务日期归档，确保：

- 能回溯任务参数
- 能定位错误日志
- 能找到最终产物
- 能与审计记录对应

## 7. Worker 运行方式

默认 Worker 使用数据库轮询模式。

它的职责是：

- 领取待执行 Job
- 更新任务状态
- 写入日志和产物路径
- 支持心跳、锁、超时、重试、取消

它的限制是：

- 在高并发或多实例场景下扩展性有限
- 如果未来需要更高吞吐量，可以再评估 Redis/队列方案

## 8. 暂不引入 Redis 的说明

当前仓库的默认生产方案不依赖 Redis。

原因：

- 任务调度和状态追踪已经可以由数据库轮询 Worker 完成
- 先把单机与内网部署闭环做实，比先引入额外队列更重要
- 后续若有并发和分布式需求，再把 Redis 作为候选队列组件评估

仓库中的 `docker-compose.yml` 目前只提供 PostgreSQL，Redis 只是可选 profile，不应被理解为默认必需组件。

## 9. 迁移和启动顺序

推荐的生产启动顺序：

1. 配好 `DATABASE_URL`、`CONFIG_PATH`、`X-API-Key` 相关注入
2. 启动 PostgreSQL
3. 执行数据库迁移
4. 构建 Web 前端
5. 启动 FastAPI API
6. 启动 Job Worker
7. 部署或托管 Web 静态资源
8. 检查健康状态与日志

生产启动流程必须避免以下做法：

- 直接使用开发模式 `--reload`
- 把临时目录当作正式产物目录
- 把敏感值明文写入仓库
- 把浏览器调试命令当作生产部署命令

## 10. 推荐启动命令

如果使用 Docker Compose，推荐的最小生产启动流程是：

```bash
docker compose up -d db
docker compose run --rm api python -m cli.main db-migrate --config config/app.yaml
docker compose up -d api worker web
```

对应的本地非 Docker 启动命令是：

```bash
python -m cli.main db-migrate --config config/app.yaml
uvicorn api.main:app --host 0.0.0.0 --port 8000
python -m cli.main job-worker-start --config config/app.yaml
corepack pnpm build
```

其中：

- `api` 负责 HTTP 接口和 UI BFF
- `worker` 负责数据库轮询执行 Job
- `web` 负责构建后的静态资源和 `/api/` 反向代理

## 11. 本机非 Docker 部署

如果只需要单机本机验证，不走 Docker / Compose，可以直接使用仓库内的 launcher 脚本：

```bash
python -m scripts.web_local build
python -m scripts.web_local migrate
python -m scripts.web_local start
```

对应的单独命令也可分别使用：

```bash
python -m scripts.web_local build
python -m scripts.web_local migrate
python -m scripts.web_local start-api
python -m scripts.web_local start-worker
```

本机模式的约定：

- `build` 在 `web/` 下执行 `corepack pnpm build`
- `start-api` 和 `start` 会要求 `web/dist/index.html` 已存在
- API 在 `WEB_STATIC_DIR=web/dist` 时直接托管前端静态页面
- 浏览器访问 `http://localhost:8000` 即可同时使用 Web 页面和 `/api/ui/v1/*`
- 这个路径只面向单机验证，不替代 Docker/Compose 的默认生产流程
