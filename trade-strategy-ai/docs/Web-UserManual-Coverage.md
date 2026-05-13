# Web UserManual 覆盖矩阵

> 目标：把 `docs/UserManual.md` 中的常用 CLI / 独立 CLI 功能逐条映射到 Web 管理后台的页面、API、Service、Job 类型、权限与验收方式。
>
> 结论：`docs/UserManual.md` 中已识别的常用功能均已纳入 Web 化范围；其中长任务统一进入 Job Center，查询类能力走只读 API，配置/运维类能力走受控管理页。

### 当前已实现的 UI BFF

目前仓库里已经落地并可直接调用的 Web UI 入口是：

- `/api/ui/v1/system/status`
- `/api/ui/v1/jobs*`
- `/api/ui/v1/workflows*`
- `/api/ui/v1/artifacts*`
- `/api/ui/v1/market*`

其余覆盖矩阵条目仍属于后续阶段的目标设计，前端在 Stage 4 及之后接入时，应优先以以上已实现入口为准，避免把规划项误认为已经上线。

## 1. 约定

- Web API 统一使用 `/api/ui/v1/*` 前缀。
- 长任务统一使用 `POST /api/ui/v1/jobs` 创建 Job，再通过 `GET /api/ui/v1/jobs/{job_id}` 查看状态、日志和产物。
- 操作权限分为 `viewer / operator / admin`。
- 风险分级分为 `low / medium / high / critical`。
- 下表是 Web 目标设计的覆盖矩阵，不表示当前所有实现已完成。

## 2. 当前已实现

### 2.1 Stage 3 UI BFF

| 能力 | 已实现入口 | 状态 | 说明 |
| --- | --- | --- | --- |
| 系统状态 | `GET /api/ui/v1/system/status` | 已上线 | 返回配置路径、运行模式、数据库状态和关键目录状态；`/api/ui/system/status` 保留兼容别名。 |
| Job Center | `GET/POST /api/ui/v1/jobs*` | 已上线 | 支持白名单定义、创建、列表、详情、日志、取消和参数校验。 |
| Workflow 向导 | `GET/POST /api/ui/v1/workflows*` | 已上线 | 支持列表、详情、运行，并复用 Job 白名单校验。 |
| Artifact 中心 | `GET /api/ui/v1/artifacts*` | 已上线 | 支持主要产物的统一查询、预览和下载。 |
| 市场数据 | `GET /api/ui/v1/market*` | 已上线 | 支持 symbol 列表与按日期区间查询 OHLCV。 |

### 2.2 当前实现约束

- 已实现的 UI API 统一使用 `/api/ui/v1/*` 前缀。
- `config/backups` 不纳入 Artifact 中心默认索引，配置备份由 Stage 7 Settings Center 负责。
- `jobs`、`workflows`、`artifacts`、`market` 均依赖 `api/app.py` 挂载的版本化 router。

## 3. 覆盖矩阵

### 3.1 配置、数据库与初始化

| UserManual 功能 | Web 页面 / 入口 | UI API | Service | Job / 执行形态 | 权限 | 风险 | 验收要点 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `init-config` | 系统设置 / 配置模板 | `GET /api/ui/v1/system/config/template` | `ConfigService` | 无 | admin | low | 可生成默认配置模板并提示关键字段含义。 |
| `db-check` | 系统诊断 / 数据库检查 | `POST /api/ui/v1/system/db/check` | `SystemService` | 无 | operator / admin | low | 能显示数据库连通性、错误摘要和修复建议。 |
| `db-migrate` | 系统维护 / 数据库迁移 | `POST /api/ui/v1/system/db/migrate` | `SystemService` | `db-migrate` Job | admin | high | 执行前有摘要与确认，执行后可查看迁移结果。 |
| `init-project` | 初始化向导 | `POST /api/ui/v1/setup/init-project` | `SetupService` | `init-project` Job | admin | high | 可完成迁移与本地 seed，并给出完成状态。 |
| `seed-data` | 初始化向导 / 数据种子 | `POST /api/ui/v1/setup/seed-data` | `SetupService` | `seed-data` Job | admin | medium | 可导入样例数据并显示导入清单。 |
| `backup-data` | 运维 / 备份中心 | `POST /api/ui/v1/ops/backup` | `OpsRecoveryService` | 页面直调 | admin | high | 备份目录、表范围、产物路径和审计记录可追踪。 |
| `restore-data` | 运维 / 恢复中心 | `POST /api/ui/v1/ops/restore` | `OpsRecoveryService` | 页面直调 | admin | critical | 恢复前二次确认，且默认要求 `confirmed`。 |
| `scheduler-start` | 运维 / 调度状态 | `POST /api/ui/v1/system/scheduler/start` | `SchedulerService` | 常驻进程 / 状态控制 | admin | medium | 能查看调度状态、启停配置和下一次触发时间。 |

### 3.2 抓取与数据处理 Pipeline

| UserManual 功能 | Web 页面 / 入口 | UI API | Service | Job / 执行形态 | 权限 | 风险 | 验收要点 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `crawl` | 数据管道 / 抓取任务 | `POST /api/ui/v1/jobs` | `PipelineService` | `crawl` Job | operator / admin | medium | 支持参数预览、任务排队和日志查看。 |
| `import-trade-logs` | 数据导入 / 交易记录 | `POST /api/ui/v1/jobs` | `SetupService` | `import-trade-logs` Job | operator / admin | medium | 支持文件上传、格式校验和 dry-run。 |
| `pipeline-run` | 数据管道 / 一键执行 | `POST /api/ui/v1/jobs` | `PipelineService` | `pipeline-run` Job | operator / admin | medium | 可展示各步骤状态、失败步骤和重跑入口。 |
| `pipeline-step` | 数据管道 / 单步执行 | `POST /api/ui/v1/jobs` | `PipelineService` | `pipeline-step` Job | operator / admin | medium | 可按 step 逐步执行并显示前置依赖。`process` 步骤已整合原 `extract-articles` 的文章抽取功能。 |
| `migrate-crawl-state` | 数据迁移 / 爬虫状态 | `POST /api/ui/v1/jobs` | `SetupService` | `migrate-crawl-state` Job | admin | medium | 能把本地 state 迁移到数据库并输出迁移摘要。 |
| `clusters-build` | 画像 / 聚类构建 | `POST /api/ui/v1/jobs` | `PersonaService` | `clusters-build` Job | operator / admin | medium | 可生成 clusters 文件并查看版本与路径。 |
| `e2e-regression` | 验证 / 端到端回归 | `POST /api/ui/v1/jobs` | `RegressionService` | `e2e-regression` Job | admin | medium | 一键跑通主链路并输出回归报告。 |

### 3.3 盘前、盘后与信号

| UserManual 功能 | Web 页面 / 入口 | UI API | Service | Job / 执行形态 | 权限 | 风险 | 验收要点 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `run-pre-market` | 盘前工作台 | `POST /api/ui/v1/workflows/pre-market/run` | `RunService` | `run-pre-market` Job | operator / admin | medium | 可按日期触发，支持 HTML 导出与结果预览。 |
| `run-after-close` | 盘后工作台 | `POST /api/ui/v1/workflows/after-close/run` | `RunService` | `run-after-close` Job | operator / admin | medium | 可按日期触发，显示评估数量、结果与 HTML 链接。 |
| `list-signals` | 信号中心 | `GET /api/ui/v1/signals` | `SignalService` | 无 | viewer / operator / admin | low | 可按标的、日期过滤并查看信号详情。 |
| `persona-init-sample` | 画像 / 示例数据 | `POST /api/ui/v1/persona/sample` | `PersonaService` | `persona-init-sample` Job | admin | low | 可生成示例 clusters 文件用于联调。 |
| `market-state-build` | 市场状态 / 构建器 | `POST /api/ui/v1/market/state/build` | `PersonaService` | `market-state-build` Job | operator / admin | medium | 可生成 market state JSON 并查看来源。 |

### 3.4 快照、策略与行情

| UserManual 功能 | Web 页面 / 入口 | UI API | Service | Job / 执行形态 | 权限 | 风险 | 验收要点 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `snapshot build` | 快照中心 | `POST /api/ui/v1/snapshots` | `SnapshotService` | `snapshot-build` Job | operator / admin | medium | 支持单日和区间构建，并可重建已有快照。 |
| `strategy build` | 策略版本 / 构建 | `POST /api/ui/v1/strategies/build` | `StrategyService` | `strategy-build` Job | operator / admin | medium | 可按交易员和日期生成版本并显示状态。 |
| `strategy list` | 策略版本 / 列表 | `GET /api/ui/v1/strategies` | `StrategyService` | 无 | viewer / operator / admin | low | 可按 trader、状态、日期过滤查看版本。 |
| `ohlcv crawl` | 行情数据 / OHLCV 入库 | `POST /api/ui/v1/jobs` | `MarketService` | `ohlcv-crawl` Job | operator / admin | medium | 支持全量/增量、日期区间和限速提示。 |

### 3.5 回测与优化

| UserManual 功能 | Web 页面 / 入口 | UI API | Service | Job / 执行形态 | 权限 | 风险 | 验收要点 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `backtest run` | 回测中心 | `POST /api/ui/v1/backtests` | `BacktestService` | `backtest-run` Job | operator / admin | medium | 可按 trader 和日期区间回测并导出结果。 |
| `backtest report` | 回测中心 / 报告查看 | `GET /api/ui/v1/backtests/{result_id}` | `BacktestService` | 无 | viewer / operator / admin | low | 可从结果文件生成可读报告。 |
| `backtest validate-rules` | 规则验真中心 | `POST /api/ui/v1/backtests/validate-rules` | `BacktestService` | `backtest-validate-rules` Job | operator / admin | medium | 可输出规则命中验证报告。 |
| `backtest reproducibility-check` | 回测验证 / 可复现性 | `POST /api/ui/v1/backtests/reproducibility-check` | `BacktestService` | `backtest-reproducibility-check` Job | admin | medium | 可对同一请求重复执行并比对结果。 |
| `backtest rule-pool-run` | 规则池回测 | `POST /api/ui/v1/rule-pool/backtest` | `RulePoolService` | `rule-pool-backtest` Job | admin | high | 回测结果会回写规则池并更新置信度。 |
| `optimize filter` | 优化中心 / 筛选 | `POST /api/ui/v1/optimize/filter` | `OptimizeService` | 无 | operator / admin | low | 可基于回测结果筛选活跃 trader。 |
| `optimize advise` | 优化中心 / 建议 | `POST /api/ui/v1/optimize/advise` | `OptimizeService` | 无 | operator / admin | low | 可基于规则验真结果输出调整建议。 |
| `optimize create-candidate` | 优化中心 / 候选版本 | `POST /api/ui/v1/optimize/candidate` | `OptimizeService` | `optimize-create-candidate` Job | operator / admin | medium | 可生成文件链路或 DB 链路的候选版本。 |

### 3.6 规则池、调度与监控

| UserManual 功能 | Web 页面 / 入口 | UI API | Service | Job / 执行形态 | 权限 | 风险 | 验收要点 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `rule-pool show` | 规则池 / 详情 | `GET /api/ui/v1/rule-pool/{rule_id}` | `RulePoolService` | 无 | viewer / operator / admin | low | 可查看规则、回测、审核与映射条件。 |
| `rule-pool list` | 规则池 / 列表 | `GET /api/ui/v1/rule-pool` | `RulePoolService` | 无 | viewer / operator / admin | low | 支持状态、类型、映射条件等过滤。 |
| `rule-pool review` | 规则池 / 审核 | `POST /api/ui/v1/rule-pool/{rule_id}/review` | `RulePoolService` | 无 | operator / admin | medium | 审核前需展示摘要并支持强制覆盖。 |
| `rule-pool review-batch` | 规则池 / 批量审核 | `POST /api/ui/v1/rule-pool/review-batch` | `RulePoolService` | 无 | admin | medium | 批量审核前需确认影响范围。 |
| `KaipanScheduler fetch` | 运维 / Kaipan 调度 | `POST /api/ui/v1/kaipan/fetch` | `KaipanService` | `kaipan-fetch` Job | admin | medium | 可按日期和 slot 拉取 raw 数据。 |
| `KaipanScheduler normalize` | 运维 / Kaipan 调度 | `POST /api/ui/v1/kaipan/normalize` | `KaipanService` | `kaipan-normalize` Job | admin | medium | 可把 raw 转为规范化资产。 |
| `KaipanScheduler status` | 运维 / Kaipan 状态 | `GET /api/ui/v1/kaipan/status` | `KaipanService` | 无 | viewer / operator / admin | low | 可查看抓取/归一化进度与最近批次。 |
| `KaipanScheduler run` | 运维 / Kaipan 一键运行 | `POST /api/ui/v1/kaipan/run` | `KaipanService` | `kaipan-run` Job | admin | medium | 可串联 fetch 与 normalize 并输出批次结果。 |
| `dashboard --mode cli/html/both` | 监控中心 / Dashboard | `GET /api/ui/v1/dashboard` | `DashboardService` | 无 | viewer / operator / admin | low | 可查看阈值、趋势、告警与 HTML 产物。 |

## 4. 未覆盖项与约束

- 当前矩阵已覆盖 `docs/UserManual.md` 中识别到的常用命令与独立 CLI 功能。
- 后续如果 `UserManual` 新增命令，需要同步补充这一矩阵，再进入 Web 任务清单。
- 任何被标记为 `critical` 或 `high` 的操作，在 Web 上都必须保留摘要、确认、审计和产物追踪。
- 长任务必须走 Job Center，不能退化为浏览器直连执行。
