# Web 管理后台开发计划

> 本文档定义 `trade-strategy-ai` 从 CLI 项目升级为 Web 管理后台的总体方案。
> 目标是让用户不再依赖手工输入 CLI 命令，也能按 `docs/UserManual.md` 跑通全部项目操作、查看全部关键数据与产物。

---

## 1. 背景与目标

当前项目的主要操作入口是 `python -m cli.main ...`，功能已经覆盖配置、数据库、数据处理、盘前盘后、快照、OHLCV、策略版本、回测、优化、规则池、调度、报表和告警。

CLI 对开发者可用，但对普通使用者存在以下问题：

- 命令多，参数多，使用成本高。
- 操作流程依赖 `docs/UserManual.md`，用户需要理解命令顺序和前置条件。
- 长任务缺少统一的状态、日志、错误和产物查看入口。
- 报表、快照、回测、K 线、告警等结果分散在 API、数据库和文件目录中。
- 现有 CLI 逻辑部分直接写在命令函数中，不利于 Web/API 复用。

本计划的目标是：

1. 把 CLI 背后的业务逻辑抽成 Python service。
2. 保留 CLI，但让 CLI 与 Web API 共用同一套 service。
3. 新增 Web 管理后台，覆盖 `docs/UserManual.md` 的全部功能。
4. 提供清晰、低风险、可追踪的操作体验。
5. 让用户可以方便查看个股 K 线、报表、快照、回测、告警和任务产物。
6. 让用户可以通过 Web 查看、编辑、校验和保存主要设置项，而不是手工修改 `config/app.yaml`。

---

## 2. 设计原则

### 2.1 不做远程 shell

Web 后台禁止提供任意命令输入框，也不允许用户通过浏览器提交 shell 字符串执行。

所有 Web 操作必须通过受控 API 调用受控 service：

```text
Web UI -> FastAPI UI API -> Python Service -> 现有领域模块 / 数据库 / 文件产物
```

原因：

- 避免命令注入。
- 避免误删数据或破坏配置。
- 避免 cookie、API Key、数据库密码泄露。
- 让参数、权限、日志、错误和产物可结构化记录。

### 2.2 CLI 逻辑服务化

现有 CLI 不应该被废弃，而是逐步改为 service 的调用方。

目标结构：

```text
cli/main.py
  -> src/services/*

api/main.py
  -> api/routers/*
  -> src/services/*

web/*
  -> FastAPI API
```

这样可以保证：

- CLI 和 Web 行为一致。
- 核心逻辑可测试。
- 后续新增入口不会复制业务逻辑。

### 2.3 以 UserManual 流程组织 UI

Web 后台不是简单菜单集合，而是把 `docs/UserManual.md` 产品化。

用户应该能通过操作向导完成：

```text
安装检查 -> 配置检查 -> 数据库检查/迁移 -> 数据处理 -> 快照/OHLCV
-> 策略版本 -> 盘前日报 -> 盘后考核 -> 回测/规则验真 -> 优化/规则池 -> 查看结果
```

每一步都应显示：

- 当前步骤目标。
- 所需参数。
- 前置条件是否满足。
- 执行按钮。
- 执行状态。
- 日志。
- 产物链接。
- 下一步建议。

### 2.4 所有长任务进入 Job Center

以下操作必须通过 Job Center 执行和追踪：

- `pipeline-run`
- `pipeline-step`
- `crawl`
- `extract-articles`
- `clusters-build`
- `e2e-regression`
- `snapshot build`
- `ohlcv crawl`
- `strategy build`
- `run-pre-market`
- `run-after-close`
- `backtest run`
- `backtest validate-rules`
- `backtest rule-pool-run`
- `optimize filter`
- `optimize advise`
- `optimize create-candidate`
- `backup-data`
- `restore-data`
- `scheduler-start`

补充原则：

- Job 状态必须持久化到数据库，日志和产物可以落盘。
- v1 采用“数据库持久化 Job + 独立 Worker 进程 + 数据库轮询锁”的方案，暂不强制引入 Redis/RQ/Celery。
- Worker 必须支持心跳、任务锁、幂等键、超时、重试、取消请求、并发限制和服务重启后的状态恢复。
- 如果后续并发量或分布式部署需求上升，再评估 Redis/队列方案。

Job Center 需要记录：

- `job_id`
- 任务类型
- 参数快照
- 状态：`pending / running / success / failed / cancelled`
- 创建时间、开始时间、结束时间
- 日志
- 错误
- 产物路径
- 发起人或来源
- 幂等键
- 重试次数
- 超时时间
- Worker 标识
- 心跳时间

### 2.5 UserManual 覆盖矩阵作为验收入口

Web 交付必须维护一份 UserManual 覆盖矩阵，逐条映射：

- UserManual 命令/功能。
- Web 页面。
- UI API。
- Python service。
- Job 类型。
- 权限等级。
- 风险等级。
- 验收用例。

覆盖矩阵中存在未覆盖项时，不能进入最终交付验收。

---

## 3. 推荐技术栈

### 3.1 后端

- FastAPI：作为 Web 后台 API 和 BFF 层。
- Pydantic：定义请求、响应、Job、Workflow、产物模型。
- SQLAlchemy async：复用现有数据库访问方式。
- APScheduler：保留现有调度能力，Web 提供状态和配置查看。
- 独立 Job Worker：从数据库领取任务并执行，支持心跳、锁、重试、超时和恢复。
- pytest / pytest-asyncio：后端测试。

### 3.2 前端

- React + TypeScript + Vite：构建单页 Web 管理后台。
- TanStack Router：类型安全路由。
- TanStack Query：请求缓存、状态刷新、Job 轮询。
- Tailwind CSS + shadcn/ui：后台表格、表单、弹窗、侧边栏、状态组件。
- TradingView Lightweight Charts：个股 K 线。
- ECharts：回测曲线、ranking、告警统计、数据质量趋势。

### 3.3 部署方式

开发期：

```text
FastAPI: uvicorn api.main:app --reload
Web: vite dev server
```

本地/内网交付期：

```text
vite build -> web/dist
FastAPI static files -> 托管 web/dist
独立 Worker 进程 -> 执行持久化 Job
```

生产交付还必须包含：

- Docker/Compose 或等价部署脚本。
- 数据库迁移流程。
- API 和 Worker 健康检查。
- 配置和密钥注入说明。
- 日志目录和产物目录规划。
- 备份、恢复、发布和回滚文档。
- 反向代理、TLS、上传大小和超时配置建议。

---

## 4. 总体架构

```text
┌──────────────────────────────────────────┐
│ Web 管理后台 React SPA                    │
│ - 操作向导                                │
│ - Job Center                              │
│ - K 线 / 报表 / 快照 / 回测 / 告警          │
└───────────────────┬──────────────────────┘
                    │ HTTP JSON
┌───────────────────▼──────────────────────┐
│ FastAPI UI API / BFF                       │
│ - /api/ui/v1/jobs                          │
│ - /api/ui/v1/workflows                     │
│ - /api/ui/v1/system                        │
│ - /api/ui/v1/artifacts                     │
│ - /api/ui/v1/market                        │
└───────────────────┬──────────────────────┘
                    │ Python call
┌───────────────────▼──────────────────────┐
│ Service Layer                              │
│ - ConfigService                            │
│ - JobService                               │
│ - JobRunner                                │
│ - WorkflowService                          │
│ - PipelineService                          │
│ - MarketService                            │
│ - PersonaService                           │
│ - SignalService                            │
│ - KaipanService                            │
│ - DashboardService                         │
│ - BacktestService                          │
│ - RulePoolService                          │
│ - ArtifactService                          │
└───────────────────┬──────────────────────┘
                    │
┌───────────────────▼──────────────────────┐
│ Job Worker                                 │
│ - DB polling + lock                        │
│ - heartbeat / retry / timeout / cancel     │
└───────────────────┬──────────────────────┘
                    │
┌───────────────────▼──────────────────────┐
│ Existing Domain Modules                    │
│ CLI / ManagerAgent / Pipeline / Backtest   │
│ Snapshot / OHLCV / Alerting / Rule Pool    │
└──────────────────────────────────────────┘
```

---

## 5. 后端模块设计

### 5.1 Service Layer

新增 `src/services/`，作为 CLI 与 Web API 的共享业务层。

基础约定：

- `BaseService`：所有 Web/CLI 共享服务的基类，只承载公共约定，不依赖 Typer，也不直接输出终端文本。
- `ServiceResult`：服务层统一返回结构，包含 `status`、`message`、`payload` 和 `warnings`，由 CLI 和 Web API 再做各自渲染。
- 服务命名统一使用 `*Service`，例如 `ConfigService`、`SystemService`、`JobService`。
- 业务方法返回结构化对象，不返回拼接好的终端字符串。

建议模块：

- `config_service.py`：配置读取、原始 YAML 读取、配置脱敏、配置校验、配置状态检查。
- `setup_service.py`：封装 init-config、init-project、seed-data、import-trade-logs 和 migrate-crawl-state。
- `config_edit_service.py`：配置草稿、字段级校验、保存、备份、恢复和敏感项写入策略。
- `system_service.py`：Python 版本、依赖、数据库连通性、关键目录状态、API 健康检查。
- `run_service.py`：封装 run-pre-market、run-after-close 和 HTML 导出。
- `job_service.py`：Job 创建、执行、状态流转、日志和产物记录。
- `job_registry.py`：定义 Job 白名单、参数 schema、权限与风险等级，并供 UI 提交前校验。
- `workflow_service.py`：定义 UserManual 流程、步骤、前置条件和下一步建议。
- `pipeline_service.py`：封装 crawl、pipeline-run、pipeline-step、extract、clusters、e2e-regression。
- `snapshot_service.py`：封装 snapshot build、快照查询和删除。
- `market_service.py`：封装 OHLCV crawl、K 线查询、最新收盘价查询。
- `strategy_service.py`：封装 strategy build/list/detail/download。
- `backtest_service.py`：封装 backtest run/report/validate-rules/reproducibility-check/rule-pool-run。
- `optimize_service.py`：封装 optimize filter/advise/create-candidate。
- `rule_pool_service.py`：封装 rule-pool show/list/review/review-batch。
- `api/routers/ui/jobs.py`：提供 Job 定义查询与提交参数校验接口，禁止前端提交任意 job type。
- `artifact_service.py`：统一发现日报、考核、HTML、快照、回测、规则验真、backup 等产物，不包含 `config/backups` 这类敏感配置备份，配置备份由 Stage 7 Settings Center 处理。
- `scheduler_service.py`：封装调度状态、配置读取、启动提示和运行记录。

### 5.2 Job Center

Job 状态必须使用数据库持久化，便于查询、分页、审计和服务重启后的恢复。
`JobService` 负责状态流转和持久化，`JobRunner` 负责按白名单执行受控任务。

最小字段：

```text
id
type
status
params_json
result_json
artifact_refs_json
error_message
created_at
started_at
finished_at
created_by
idempotency_key
retry_count
max_retries
retry_backoff_seconds
timeout_seconds
worker_id
heartbeat_at
cancel_requested_at
```

日志可以先落文件，再由 `job_id` 关联：

```text
data/jobs/{job_id}/job.log
data/jobs/{job_id}/params.json
data/jobs/{job_id}/result.json
data/jobs/{job_id}/artifacts.json
```

目录约定：

- `job.log`：按行追加的运行日志
- `params.json`：创建 Job 时的参数快照
- `result.json`：Job 成功、失败或取消后的最终结果摘要
- `artifacts.json`：Job 绑定的产物引用列表

Worker 协议要求：
- `JobRunner` 只能领取白名单 `job_type`
- `claim_job()` 负责原子领取 Job
- `heartbeat_job()` 定期刷新运行中任务的心跳
- `cancel_job()` 对运行中任务只设置 `cancel_requested`
- `fail_job()` 和 `recover_stale_jobs()` 会根据 `retry_backoff_seconds` 生成下一次可领取时间

### 5.3 API 路由

新增 `api/routers/ui/` 或 `api/routers/ui.py`。

建议接口：

```text
GET  /api/ui/v1/system/status
GET  /api/ui/v1/settings
GET  /api/ui/v1/settings/schema
POST /api/ui/v1/settings/validate
POST /api/ui/v1/settings/save
GET  /api/ui/v1/settings/backups
POST /api/ui/v1/settings/restore
GET  /api/ui/v1/workflows
GET  /api/ui/v1/workflows/{workflow_id}
POST /api/ui/v1/workflows/{workflow_id}/run

POST /api/ui/v1/jobs
GET  /api/ui/v1/jobs
GET  /api/ui/v1/jobs/{job_id}
GET  /api/ui/v1/jobs/{job_id}/logs
POST /api/ui/v1/jobs/{job_id}/cancel

GET  /api/ui/v1/artifacts
GET  /api/ui/v1/artifacts/{artifact_id}
GET  /api/ui/v1/artifacts/{artifact_id}/download

GET  /api/ui/v1/market/ohlcv
GET  /api/ui/v1/market/symbols
```

所有 UI API 必须声明权限等级：

- `viewer`：只读查询和产物预览。
- `operator`：运行非破坏性任务。
- `admin`：配置保存、数据库迁移、恢复、批量审核、告警测试、调度启动等高风险操作。

### 5.4 API 入口收敛

当前项目存在：

- `api/main.py`

Web 管理后台以 `api/main.py` 作为唯一主入口，底层通过 `api/app.py` 统一构建 FastAPI app；仓库不再保留 `src/api/main.py` 这个运行入口。

Web 前端只能依赖版本化 UI API，不直接依赖内部领域 API。

---

## 6. 前端页面设计

### 6.1 总览 Dashboard

展示：

- API 健康状态。
- 数据库连接状态。
- 配置文件状态。
- 最近 Job。
- 最近日报/考核。
- 最近快照。
- 最近回测。
- 告警摘要。
- 下一步建议。

### 6.2 环境与配置中心

展示：

- Python 版本。
- 数据库连接状态。
- `config/app.yaml` 是否存在。
- 关键配置项脱敏展示。
- 数据目录是否存在。
- 依赖检查结果。

同时提供设置项编辑与保存能力：

- 基础设置：时区、运行模式、输出目录、日志级别。
- 数据库设置：连接串、连接池参数、echo 开关。
- API 设置：host、port、timeout、API Key 开关。
- 调度设置：是否启用、盘前时间、盘后时间。
- 数据设置：provider、market_data_cache_dir、mock_prices。
- 爬虫设置：sources、throttling、auth 引用。
- LLM 设置：provider、model、base URL、API Key 环境变量引用。
- Persona 设置：enable、clusters_path、top_k、market_state 配置。
- Kaipan 设置：data_dir、schema_dir、token/user_id 环境变量引用、限速和重试参数。
- Alerting 设置：告警通道、Webhook 环境变量引用、聚合规则。

保存规则：

- 默认保存到 `config/app.yaml`。
- 保存前必须做 schema 校验和业务校验。
- 保存前自动创建备份，例如 `config/backups/app.YYYYMMDD-HHMMSS.yaml`。
- Web 不直接展示或保存明文密钥，敏感项优先保存为环境变量引用，例如 `"${DASHSCOPE_API_KEY}"`。
- 保存成功后显示配置 diff、备份路径和下一步建议。
- 保存失败时不能覆盖原配置。
- 提供从最近备份恢复配置的入口，恢复操作必须二次确认。

禁止展示明文 cookie、API Key、数据库密码。

### 6.3 操作向导

按用户路径组织操作，而不是简单堆叠命令。

首次初始化路径：

1. 配置检查。
2. 数据库检查。
3. 数据库迁移。
4. 初始化数据。
5. 样例数据或最小真实数据导入。

日常运行路径：

1. 文章抓取与处理 pipeline。
2. 文章抽取与 persona clusters。
3. 市场状态构建。
4. 快照构建。
5. OHLCV 入库。
6. 策略版本构建。
7. 盘前日报。
8. 盘后考核。

复盘分析路径：

1. 报表和产物查看。
2. 回测。
3. 规则验真。
4. 优化建议与候选版本。
5. 规则池审核。

排障运维路径：

1. 任务失败查看。
2. 数据监控 Dashboard。
3. 配置检查。
4. 备份与恢复。
5. 调度器状态。

操作向导中涉及配置缺失时，应跳转到对应设置项，而不是只提示用户手工编辑 YAML。

### 6.4 Job 任务中心

提供：

- 任务列表。
- 状态过滤。
- 类型过滤。
- 任务详情。
- 实时或轮询日志。
- 参数快照。
- 错误详情。
- 产物跳转。
- 重跑入口。

### 6.5 数据 Pipeline

提供：

- `crawl`
- `pipeline-run`
- `pipeline-step`
- `extract-articles`
- `clusters-build`
- `e2e-regression`

每个操作使用表单填写参数，不让用户手写命令。

### 6.6 盘前/盘后

提供：

- 选择日期。
- `force` 开关。
- `export_html` 开关。
- 运行盘前。
- 运行盘后。
- 查看 JSON 报告。
- 查看 HTML 报告。
- 查看 Evidence Pack 和 ranking 入口。

### 6.7 市场数据与 K 线

提供：

- 个股代码搜索。
- 日期区间选择。
- K 线图。
- OHLCV 明细表。
- 数据导出。
- 最近同步状态。

K 线使用 TradingView Lightweight Charts。

### 6.8 快照中心

提供：

- 快照构建。
- 按日期、slot、type 查询。
- hot topics 查看。
- topic constituents 查看。
- strong symbols 查看。
- JSON 下载。

### 6.9 策略版本中心

提供：

- 构建策略版本。
- 按 trader/status 查询。
- 查看版本详情。
- 下载版本归档或 JSON。

### 6.10 回测与规则验真

提供：

- backtest run。
- backtest report。
- validate-rules。
- reproducibility-check。
- rule-pool-run。
- 回测结果列表。
- 回测详情。
- 指标图表。
- Markdown/JSON 报告查看。

### 6.11 优化与规则池

提供：

- optimize filter。
- optimize advise。
- optimize create-candidate。
- rule-pool show/list。
- rule-pool review。
- rule-pool review-batch。

批量审核必须二次确认。

### 6.12 告警中心

提供：

- 告警历史列表。
- 级别、状态、标签、日期过滤。
- 告警详情。
- 确认告警。
- 解决告警。
- 测试告警。

测试告警必须提示可能触发外部 Webhook。

### 6.13 调度中心

提供：

- 读取调度配置。
- 展示盘前/盘后时间。
- 展示 schedule.enable。
- 展示最近运行记录。
- 提供启动调度的说明或受控任务入口。

---

## 7. 安全与风险控制

### 7.1 高风险操作

以下操作必须二次确认：

- 保存配置。
- 从备份恢复配置。
- `restore-data`
- `db-migrate`
- `backup-data` 带覆盖目标时
- `pipeline-run --force`
- `snapshot build --force`
- `strategy build --force`
- `run-pre-market --force`
- `run-after-close --force`
- `rule-pool review-batch`
- `alerts/test`
- `scheduler-start`

确认内容必须包含：

- 操作名称。
- 参数摘要。
- 可能影响。
- 是否会覆盖文件或写数据库。

### 7.2 敏感信息保护

Web API 返回配置时必须脱敏：

- cookie
- token
- api_key
- password
- secret
- DATABASE_URL 密码段

Web 保存配置时必须区分普通设置和敏感设置：

- 普通设置可以直接写入 YAML。
- 敏感设置只允许写入环境变量引用或空值。
- 如果用户输入明文密钥，前端必须提示不推荐，后端必须拒绝直接写入仓库内 YAML，除非后续显式引入本地 secret store。
- 配置保存、恢复和校验必须记录 Job 或审计记录。

### 7.3 权限策略

生产交付必须包含最小角色权限模型。

v1 角色：

- 只读用户。
- 操作用户。
- 管理员。
- 审计日志。

权限规则：

- `viewer` 只能查看系统状态、任务、报表、快照、K 线、回测结果和告警历史。
- `operator` 可运行非破坏性任务，如 pipeline、盘前、盘后、快照、回测。
- `admin` 可执行配置保存、数据库迁移、恢复、批量审核、告警测试、调度启动等高风险操作。
- 权限必须由后端强制校验，前端隐藏按钮不能作为安全边界。

---

## 8. 实施顺序

推荐按以下顺序推进：

1. 文档与任务清单落地。
2. 建立 UserManual 覆盖矩阵。
3. 建立 service layer 基础结构。
4. 抽取 UserManual 覆盖所需 service。
5. 建立生产级 Job Center 和独立 Worker。
6. 新增版本化 UI API。
7. 搭建 Web 前端工程。
8. 实现 Dashboard、Job Center、操作向导最小闭环。
9. 实现 K 线、报表、快照、回测、告警、策略、优化、规则池页面。
10. 补齐 RBAC、安全、配置保存、文件上传和产物预览保护。
11. 补齐生产部署、健康检查、备份恢复和回滚。
12. 完成端到端验收与文档闭环。

---

## 9. 验收标准

整体完成后必须满足：

1. 用户无需手写 CLI，即可通过 Web 跑通 UserManual 主链路。
2. Web 能运行配置检查、数据库检查/迁移、pipeline、快照、OHLCV、策略版本、盘前、盘后、回测、优化、规则池、告警等操作。
3. Web 能查看个股 K 线、日报、考核、快照、策略版本、回测结果、规则验真、告警历史。
4. 所有长任务都进入 Job Center，并能查看状态、日志、参数、错误和产物。
5. 高风险操作有二次确认。
6. Web 能编辑、校验、保存和恢复主要配置项，且敏感信息不明文落库或落 YAML。
7. Web 不暴露任意 shell 执行能力。
8. CLI 仍可用，并逐步共用 service layer。
9. UI API 具备版本化、RBAC 和审计。
10. Job Center 具备持久化、独立 Worker、心跳、重试、超时、取消、幂等和恢复能力。
11. 具备生产部署、健康检查、备份恢复、发布和回滚文档。
12. 后端单元测试、API 测试、前端构建验证、契约测试和端到端验收通过。
13. 文档与 `docs/UserManual.md`、`docs/TaskList.md`、UserManual 覆盖矩阵保持一致。
