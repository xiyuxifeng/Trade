# Web-TaskList

> 本文件是 `trade-strategy-ai` Web 管理后台建设任务清单。
> 目标不是替代 `docs/TaskList.md`，而是在主项目任务之外，单独追踪 Web 化改造：服务化 CLI、建设 Web API、实现 Web 管理后台，并覆盖 `docs/UserManual.md` 全部功能。

---

## 1. 文档用途

本清单承担 4 个作用：

1. 定义 Web 管理后台最终交付目标。
2. 定义 CLI 项目到 Web 后台的差距。
3. 定义从当前状态到 Web 可用的唯一任务路径。
4. 定义每个任务的输入、输出、前置依赖、验收标准与并行边界。

---

## 2. 使用说明

### 2.1 接手规则

新的执行者在没有历史上下文时，必须按以下顺序接手：

1. 阅读 `docs/web-plan.md`，理解 Web 管理后台总体方案。
2. 阅读 `docs/UserManual.md`，理解需要 Web 化的全部功能。
3. 阅读 `docs/TaskList.md`，确认主项目当前阶段与主链路状态。
4. 阅读本文件，确认 Web 当前 Stage、未完成任务、依赖关系和验收标准。
5. 只从“未完成且前置依赖已满足”的任务开始执行。

### 2.2 任务状态规则

- `[ ]` 未开始
- `[-]` 进行中
- `[x]` 已完成
- `[!]` 阻塞

### 2.3 任务完成规则

一个任务只有同时满足以下条件，才能标记为完成：

1. 目标已经实现。
2. 输出物已经落地到明确路径。
3. 验收标准已经满足。
4. 相关测试、样例验证或手工验证已经完成。
5. 文档或配置更新已补齐。

### 2.4 任务字段说明

每个任务都使用相同字段：

- `目标`：这项任务要解决什么问题。
- `输入`：开始执行前必须已经具备的内容。
- `输出`：任务完成后必须新增或修改的产物。
- `修改范围`：需要改动的文件或模块。
- `前置依赖`：必须先完成的任务。
- `可并行`：哪些任务可以和它同时做。
- `验收标准`：做到什么程度才算完成。
- `完成情况`：记录完成的内容和结果。
- `备注`：其他需要注意的事项。

### 2.5 执行原则

- Web 不执行任意 shell 字符串。
- CLI 逻辑必须逐步抽到 Python service。
- CLI 和 Web API 必须共用 service，避免行为分叉。
- 所有长任务必须进入生产级 Job Center，支持持久化、恢复、幂等、取消、重试、超时和并发控制。
- 所有高风险操作必须有二次确认。
- 所有配置展示必须脱敏。
- 设置项保存前必须校验并自动备份，敏感项不得明文写入仓库内 YAML。
- Web 交付必须具备权限分级、审计、部署、运维、备份恢复和端到端验收，不以 Demo 标准验收。
- Web 功能优先按 `docs/UserManual.md` 的用户操作流程组织。

---

## 3. 最终交付目标

Web 管理后台完成后，必须达到以下状态：

1. 用户可以通过浏览器完成 `docs/UserManual.md` 中的全部常用操作。
2. 用户可以通过操作向导跑通抓取、处理、盘前、盘后、回测、优化的主链路。
3. 用户可以方便查看个股 K 线、OHLCV 明细、日报、考核、快照、策略版本、回测结果、规则验真、告警历史。
4. 所有长任务都有统一状态、日志、错误和产物追踪。
5. 高风险操作具备明确的参数摘要和二次确认。
6. CLI 保持可用，并与 Web API 共用 service layer。
7. Web 后台具备最小权限保护和敏感信息脱敏。
8. Web 后台支持主要设置项的查看、编辑、校验、保存、备份和恢复。
9. Web 后台具备生产部署、健康检查、日志、监控、备份恢复和回滚能力。
10. 后端、前端、文档和测试达到可维护状态。

---

## 4. 当前代码现状与主要缺口

### 4.1 已有基础

- 项目已有 Typer CLI，入口在 `cli/main.py` 和多个 `cli/*.py` 子模块。
- 项目已有 FastAPI，入口通过 `src/api/app.py` 收敛，`api/main.py` 作为唯一对外入口。
- 已有部分管理 API：盘前/盘后、报表、快照、策略版本、ranking、回测结果、告警。
- 已有部分查询 API：文章、交易、市场数据、报表。
- 已有 OHLCV 数据模型，可支持 K 线数据查询。
- 已有 `docs/UserManual.md`，完整描述用户操作流程。
- 已有 `docs/APIReference.md`，描述现有 API。

### 4.2 关键缺口

- CLI 背后部分逻辑仍直接写在命令函数中，缺少统一 service layer。
- Web 不能直接复用所有 CLI 操作。
- 长任务缺少统一 Job Center。
- 现有 FastAPI 入口已经收敛为单一 app 构建源，后续重点是维护版本化 UI API。
- 缺少 Web 前端工程。
- 缺少操作向导。
- 缺少统一产物中心。
- 缺少 K 线页面、回测可视化、快照可视化和告警管理页面。
- 缺少 Web 侧权限、脱敏和高风险操作保护。
- 缺少设置项编辑、保存、备份、恢复和敏感配置写入策略。
- 缺少 UserManual 命令到 Web 功能的逐项覆盖矩阵。
- 缺少生产级 Job 执行器、Worker 心跳、重试、超时、并发控制和服务重启恢复设计。
- 缺少生产部署、运维监控、发布回滚和备份恢复演练任务。

### 4.3 唯一主线

Web 化改造主线是：

```text
CLI 逻辑服务化 -> 生产级 Job Center -> UI API -> Web 前端 -> UserManual 操作向导 -> 数据和产物可视化 -> 生产部署与运维验收
```

---

## 5. 优先级定义

- `P0`：Web 主链路必需，不完成无法继续推进。
- `P1`：核心可用能力，完成后 Web 可覆盖主要用户操作。
- `P2`：增强能力，提升体验、可视化和管理效率。

---

## 6. Stage 0：文档与架构基线（P0）

### Stage 目标

- 明确 Web 建设范围。
- 明确技术栈、架构和任务拆分。
- 建立后续执行的唯一 Web 任务入口。

### 阶段交付物

- `docs/web-plan.md`
- `docs/Web-TaskList.md`
- `docs/Web-UserManual-Coverage.md`

### 任务清单

- [x] `WEB-S0-001` `P0`
  目标：新增 Web 管理后台总体计划。
  输入：`docs/UserManual.md`、`docs/TaskList.md`、当前 CLI/API 代码。
  输出：`docs/web-plan.md`。
  修改范围：`docs/web-plan.md`。
  前置依赖：无。
  可并行：`WEB-S0-002`。
  验收标准：文档说明目标、架构、技术栈、模块设计、实施顺序、安全策略和验收标准。
  完成情况：已完成 `docs/web-plan.md`，并补充了 Web 不做远程 shell、CLI 服务化、Job Center、UserManual 覆盖矩阵、生产部署与验收要求。
  备注：不得写成临时 demo 方案，必须以长期维护为目标。

- [x] `WEB-S0-002` `P0`
  目标：新增 Web 专项任务清单。
  输入：`docs/web-plan.md`、`docs/TaskList.md`。
  输出：`docs/Web-TaskList.md`。
  修改范围：`docs/Web-TaskList.md`。
  前置依赖：无。
  可并行：`WEB-S0-001`。
  验收标准：任务拆分清晰，有优先级、执行顺序、前置依赖和验收标准。
  完成情况：已完成 `docs/Web-TaskList.md`，按 Stage/P0-P2 拆分 Web 化改造主线，并整理了任务依赖与验收标准。
  备注：本文件只管理 Web 化改造，不替代主 `TaskList.md`。

- [x] `WEB-S0-003` `P0`
  目标：建立 UserManual 到 Web 功能的覆盖矩阵。
  输入：`docs/UserManual.md`、`docs/APIReference.md`、当前 CLI/API 代码。
  输出：`docs/Web-UserManual-Coverage.md`。
  修改范围：`docs/Web-UserManual-Coverage.md`、`docs/Web-TaskList.md`。
  前置依赖：`WEB-S0-001`、`WEB-S0-002`。
  可并行：无。
  验收标准：逐条列出 UserManual 中每个命令/功能对应的 Web 页面、API、Service、Job 类型、权限级别、风险等级和验收用例；未覆盖项必须标记为阻塞，不能进入最终验收。
  完成情况：已完成 `docs/Web-UserManual-Coverage.md`，覆盖配置、数据库、Pipeline、盘前盘后、快照、策略、行情、回测、优化、规则池、KaipanScheduler 和 Dashboard。
  备注：必须覆盖 `init-config`、`db-check`、`db-migrate`、`init-project`、`seed-data`、`backup-data`、`restore-data`、`scheduler-start`、`crawl`、`import-trade-logs`、`pipeline-run`、`pipeline-step`、`migrate-crawl-state`、`extract-articles`、`clusters-build`、`e2e-regression`、`run-pre-market`、`run-after-close`、`list-signals`、`persona-init-sample`、`market-state-build`、`snapshot build`、`strategy build/list`、`ohlcv crawl`、`backtest`、`optimize`、`rule-pool`、KaipanScheduler、数据监控 Dashboard。

---

## 7. Stage 1：CLI 逻辑服务化（P0）

### Stage 目标

- 将 CLI 背后的核心逻辑抽成 Python service。
- 保证 CLI 和 Web API 共用同一套业务逻辑。

### 阶段交付物

- `src/services/` 基础结构。
- 配置、系统状态、盘前盘后、pipeline、快照、OHLCV、策略、回测、优化、规则池等 service。
- CLI 调用 service 的重构。

### 任务清单

- [x] `WEB-S1-001` `P0`
  目标：建立 service layer 目录与基础约定。
  输入：现有 `cli/main.py`、`api/main.py`。
  输出：`src/services/__init__.py`、service 命名和返回模型约定。
  修改范围：`src/services/`、`docs/web-plan.md`。
  前置依赖：`WEB-S0-001`。
  可并行：无。
  验收标准：新增 service 目录；明确 service 不依赖 Typer，不直接输出终端文本。
  完成情况：已完成 `src/services/` 基础骨架，定义 `BaseService`、`ServiceResult`、`ConfigService`、`SystemService`，并在 `docs/web-plan.md` 补充了服务层约定。
  备注：service 应返回结构化结果，CLI 负责把结果渲染成终端输出。

- [x] `WEB-S1-002` `P0`
  目标：抽取配置与系统状态 service。
  输入：`config/settings.py`、`src/common/config.py`、`cli/main.py` 中配置和数据库命令。
  输出：`ConfigService`、`SystemService`。
  修改范围：`src/services/config_service.py`、`src/services/system_service.py`、相关测试。
  前置依赖：`WEB-S1-001`。
  可并行：`WEB-S1-003`。
  验收标准：能读取配置、脱敏配置、检查配置文件、检查数据库连接、检查关键目录；配置写入能力只在 `WEB-S7-005` 后开放。
  完成情况：已完成 `ConfigService` 与 `SystemService` 的最小实现，支持配置加载、原始 YAML 读取、递归脱敏、配置文件检查、数据库连通性检查和关键目录检查。
  备注：任何 cookie、token、api_key、password、secret 必须脱敏。

- [x] `WEB-S1-003` `P0`
  目标：抽取盘前/盘后 service。
  输入：`api/routers/run.py`、`src/host/handler.py`、`ManagerAgent`。
  输出：`RunService`。
  修改范围：`src/services/run_service.py`、`api/routers/run.py`、相关测试。
  前置依赖：`WEB-S1-001`。
  可并行：`WEB-S1-002`。
  验收标准：service 支持 `run_pre_market`、`run_after_close`、`export_html`，API 与 CLI 可复用。
  完成情况：已完成 `RunService`，支持盘前/盘后调用、可选 HTML 导出，并补充了对应单测。
  备注：原有 `/run/pre_market`、`/run/after_close` 行为不能回退。

- [x] `WEB-S1-004` `P0`
  目标：抽取 pipeline service。
  输入：`cli/main.py` 中 `crawl`、`pipeline-run`、`pipeline-step`、`extract-articles`、`clusters-build`、`e2e-regression`。
  输出：`PipelineService`。
  修改范围：`src/services/pipeline_service.py`、`cli/main.py`、相关测试。
  前置依赖：`WEB-S1-001`。
  可并行：`WEB-S1-005`、`WEB-S1-006`。
  验收标准：UserManual 中数据处理相关操作均可通过 service 调用；CLI 行为保持一致。
  完成情况：已完成 `PipelineService`，覆盖 crawl、pipeline-run、pipeline-step、extract-articles、clusters-build 和 e2e-regression 的共享业务封装，并补充了单测。
  备注：长任务执行本身由 Job Center 调度，service 只负责业务执行。

- [x] `WEB-S1-005` `P0`
  目标：抽取快照与 OHLCV service。
  输入：`cli/snapshot.py`、`cli/ohlcv.py`、`src/api/routes/market.py`、`api/routers/snapshots.py`。
  输出：`SnapshotOperationService`、`MarketService`。
  修改范围：`src/services/snapshot_service.py`、`src/services/market_service.py`、相关测试。
  前置依赖：`WEB-S1-001`。
  可并行：`WEB-S1-004`。
  验收标准：支持快照构建、快照查询、OHLCV 抓取、K 线数据查询。
  完成情况：已完成 `SnapshotService` 和 `MarketService`，支持快照构建/查询/删除、OHLCV 抓取、最新收盘价、bars 和 DataFrame 查询，并补充了单测。
  备注：K 线接口必须按 symbol 和日期范围查询，返回前端图表友好的数据结构。

- [x] `WEB-S1-006` `P1`
  目标：抽取策略版本 service。
  输入：`cli/strategy.py`、`api/routers/strategy_versions.py`。
  输出：`StrategyOperationService`。
  修改范围：`src/services/strategy_service.py`、相关 CLI/API 和测试。
  前置依赖：`WEB-S1-001`。
  可并行：`WEB-S1-004`、`WEB-S1-005`。
  验收标准：支持策略版本构建、列表、详情和下载信息查询。
  完成情况：已完成 `StrategyService`，支持构建、列表、详情和 JSON 下载准备，并补充了单测。
  备注：保留 trader/status/date 过滤能力。

- [x] `WEB-S1-007` `P1`
  目标：抽取回测与规则验真 service。
  输入：`cli/backtest.py`、`api/routers/backtest_results.py`。
  输出：`BacktestService`。
  修改范围：`src/services/backtest_service.py`、相关 CLI/API 和测试。
  前置依赖：`WEB-S1-001`。
  可并行：`WEB-S1-008`。
  验收标准：支持 backtest run、report、validate-rules、reproducibility-check、rule-pool-run。
  完成情况：已完成 `BacktestService`，支持回测执行、结果报告加载与渲染、规则验真、复现检查和规则池回测；`cli/backtest.py` 已切换为复用 service，补充了单测并通过回归验证。
  备注：回测结果必须可记录为 Job 产物。

- [x] `WEB-S1-008` `P1`
  目标：抽取优化和规则池 service。
  输入：`cli/optimize.py`、`cli/main.py` 中 rule-pool 命令。
  输出：`OptimizeService`、`RulePoolService`。
  修改范围：`src/services/optimize_service.py`、`src/services/rule_pool_service.py`、相关测试。
  前置依赖：`WEB-S1-001`。
  可并行：`WEB-S1-007`。
  验收标准：支持 optimize filter/advise/create-candidate 和 rule-pool show/list/review/review-batch。
  完成情况：已完成 `OptimizeService` 与 `RulePoolService`，覆盖活跃 trader 筛选、策略调整建议、候选版本生成、规则列表/详情/审核/批量审核，并补充了单测。
  备注：批量审核必须暴露风险信息，供 Web 二次确认。

- [x] `WEB-S1-009` `P0`
  目标：补齐 UserManual 中未纳入前述 service 的命令服务化。
  输入：`docs/UserManual.md`、`WEB-S0-003` 覆盖矩阵、当前 CLI/API 代码。
  输出：配置/初始化/导入/迁移/信号/persona/market-state/Kaipan/Dashboard 等补充 service。
  修改范围：`src/services/config_service.py`、`src/services/setup_service.py`、`src/services/signal_service.py`、`src/services/persona_service.py`、`src/services/kaipan_service.py`、`src/services/dashboard_service.py`、`src/services/pipeline_service.py`、`src/services/run_service.py`、相关 CLI/API 和测试。
  前置依赖：`WEB-S0-003`、`WEB-S1-001`。
  可并行：`WEB-S1-004`、`WEB-S1-005`。
  验收标准：`init-config`、`init-project`、`seed-data`、`import-trade-logs`、`migrate-crawl-state`、`list-signals`、`persona-init-sample`、`market-state-build`、KaipanScheduler `fetch/normalize/status/run`、`src.pipeline.dashboard` 均可通过 service 调用；CLI 行为保持一致。
  完成情况：A/B/C 子任务已完成，新增 `ConfigService.write_default_template()`、`SetupService`、`SignalService`、`PersonaService`、`KaipanService`、`DashboardService`，已接入 `init-config`、`init-project`、`seed-data`、`import-trade-logs`、`migrate-crawl-state`、`list-signals`、`persona-init-sample`、`market-state-build`、KaipanScheduler `fetch/normalize/status/run`、`src.pipeline.dashboard` 的 service 化与回归测试。
  备注：KaipanScheduler 和数据监控 Dashboard 是独立入口，不能因不在 `cli.main` 中而遗漏。

---

## 8. Stage 2：Job Center 与运行审计（P0）

### Stage 目标

- 为所有长任务提供统一执行、状态、日志、错误和产物追踪。

### 阶段交付物

- Job 数据模型。
- JobService。
- Job 日志和产物目录。
- Job API。

### 任务清单

- [x] `WEB-S2-001` `P0`
  目标：定义 Job 数据模型和存储方案。
  输入：长任务列表、现有数据库迁移体系。
  输出：Job 模型和迁移。
  修改范围：`src/models/`、`src/db/migrations/`、相关测试。
  前置依赖：`WEB-S1-001`。
  可并行：无。
  验收标准：Job 可持久化保存任务类型、状态、参数、结果、错误、产物、幂等键、重试次数、超时时间、取消标记、Worker 标识和时间字段。
  完成情况：已完成 `Job` ORM 模型与 Alembic migration，新增 `jobs` 表并补充了模型注册与单测；表字段覆盖任务类型、状态、参数、结果、错误、产物、幂等键、重试次数、超时时间、取消标记、Worker 标识、锁与时间字段。
  备注：生产交付必须使用持久化存储；文件存储只能作为日志和产物目录，不能作为唯一任务状态来源。

- [x] `WEB-S2-002` `P0`
  目标：实现 JobService。
  输入：Job 模型、service layer。
  输出：`src/services/job_service.py`。
  修改范围：`src/services/job_service.py`、相关测试。
  前置依赖：`WEB-S2-001`。
  可并行：无。
  验收标准：支持创建、启动、完成、失败、取消、查询、分页、日志追加、产物绑定、幂等创建、任务锁、超时标记、重试计数和状态恢复。
  完成情况：已完成 `JobService`，支持创建、查询、分页、启动、完成、失败、取消、日志追加、产物绑定、幂等创建、任务锁、超时标记、重试计数和状态恢复；新增了对应单测并通过验证。
  备注：失败状态必须保留异常摘要和可读错误信息。

- [x] `WEB-S2-003` `P0`
  目标：接入生产级长任务执行器。
  输入：JobService、已抽取 service。
  输出：受控任务执行入口。
  修改范围：`src/services/job_runner.py`、相关测试。
  前置依赖：`WEB-S2-002`、`WEB-S1-003`。
  可并行：无。
  验收标准：至少支持盘前、盘后、pipeline-run 三类任务通过 Job 执行；服务重启后 running 任务可恢复为 failed/retryable；同一幂等键不能重复创建破坏性任务；任务执行超时后状态可追踪。
  完成情况：已完成 `JobRunner`，支持 `run-pre-market`、`run-after-close`、`pipeline-run` 白名单执行；执行结果会写入 `data/jobs/{job_id}/result.json` 并绑定产物；补充了受控执行、pending 轮询和 stale 恢复可重试信息的单测并通过验证。
  备注：生产交付不得只依赖 FastAPI 进程内 background task；如暂不引入外部队列，必须实现数据库轮询 Worker、心跳和锁。

- [ ] `WEB-S2-004` `P1`
  目标：统一任务日志与产物目录。
  输入：JobService、ArtifactService 设计。
  输出：`data/jobs/{job_id}/` 目录规范。
  修改范围：`src/services/job_service.py`、`docs/web-plan.md`。
  前置依赖：`WEB-S2-002`。
  可并行：`WEB-S3-001`。
  验收标准：每个 Job 可查看日志、参数快照、结果 JSON 和产物引用。
  完成情况：未完成。
  备注：日志中不得输出敏感配置。

- [x] `WEB-S2-005` `P0`
  目标：实现 Job Worker 心跳、并发控制、重试和取消协议。
  输入：JobService、JobRunner、数据库会话。
  输出：生产级 Job Worker 协议。
  修改范围：`src/services/job_runner.py`、`src/services/job_service.py`、Job 模型/迁移、相关测试。
  前置依赖：`WEB-S2-001`、`WEB-S2-002`、`WEB-S2-003`。
  可并行：无。
  验收标准：Worker 定期写入心跳；超过心跳阈值的任务可恢复；支持按任务类型限制并发；支持可配置最大重试次数和退避；取消请求能阻止未开始任务并标记运行中任务为 cancel_requested。
  完成情况：已完成 `JobRunner` Worker 协议增强；支持 `claim_job` 原子领取、`heartbeat_job` 定期刷新心跳、按 job type 限制并发、`retry_backoff_seconds` 退避重试、运行中任务取消请求保留 `cancel_requested` 标记；补充了服务层与 worker 协议单测并通过验证。
  备注：对不能安全中断的任务，取消语义必须明确为“请求取消”，并在 UI 中说明。

- [x] `WEB-S2-006` `P0`
  目标：补齐所有 UserManual 长任务的 Job 类型白名单。
  输入：`WEB-S0-003` 覆盖矩阵、各 service。
  输出：Job 类型注册表。
  修改范围：`src/services/job_registry.py`、`src/services/job_runner.py`、`api/routers/ui/jobs.py`、相关测试。
  前置依赖：`WEB-S0-003`、`WEB-S1-009`、`WEB-S2-003`。
  可并行：无。
  验收标准：覆盖矩阵中所有需要执行的命令都有明确 job type、参数 schema、权限等级、风险等级、是否可重试、是否可并发、是否需要二次确认。
  完成情况：已完成 Job 类型注册表、参数 schema 和 UI 校验入口；白名单仅保留 `pipeline-run`、`pipeline-step`、`run-pre-market`、`run-after-close` 四个可执行 job type，其余长任务仅注册不直接进入 JobRunner。
  备注：不允许前端提交任意 job type 或任意 shell 字符串。

---

## 9. Stage 3：FastAPI UI API / BFF（P0）

### Stage 目标

- 为 Web 前端提供稳定、聚合、面向页面的 API。
- 收敛现有两套 API 入口。

### 阶段交付物

- `/api/ui/*` 路由。
- system/workflows/jobs/artifacts/market API。
- API 测试。

### 任务清单

- [ ] `WEB-S3-001` `P0`
  目标：新增 UI API 路由骨架。
  输入：`api/main.py`、`src/api/app.py`。
  输出：`api/routers/ui/` 或 `api/routers/ui.py`。
  修改范围：`src/api/app.py`、`api/main.py`、`api/routers/ui/`。
  前置依赖：`WEB-S1-002`。
  可并行：`WEB-S2-004`。
  验收标准：`/api/ui/system/status` 可返回系统状态。
  完成情况：未完成。
  备注：优先挂载到 `src/api/app.py`，`api/main.py` 作为唯一主入口。

- [ ] `WEB-S3-002` `P0`
  目标：实现 Job API。
  输入：JobService。
  输出：`/api/ui/jobs` 系列接口。
  修改范围：`api/routers/ui/jobs.py`、相关测试。
  前置依赖：`WEB-S2-002`。
  可并行：`WEB-S3-003`。
  验收标准：支持创建任务、列表、详情、日志、取消。
  完成情况：未完成。
  备注：创建任务只能使用白名单任务类型。

- [ ] `WEB-S3-003` `P0`
  目标：实现 Workflow API。
  输入：`docs/UserManual.md`、WorkflowService。
  输出：`/api/ui/workflows` 系列接口。
  修改范围：`src/services/workflow_service.py`、`api/routers/ui/workflows.py`。
  前置依赖：`WEB-S2-003`。
  可并行：`WEB-S3-002`。
  验收标准：能列出 UserManual 主流程步骤，并能为每一步创建 Job。
  完成情况：未完成。
  备注：每个步骤必须包含说明、参数 schema、前置条件和下一步建议。

- [ ] `WEB-S3-004` `P1`
  目标：实现 Artifact API。
  输入：日报、考核、快照、回测、规则验真、backup 等产物目录。
  输出：`ArtifactService` 和 `/api/ui/artifacts`。
  修改范围：`src/services/artifact_service.py`、`api/routers/ui/artifacts.py`。
  前置依赖：`WEB-S2-004`。
  可并行：`WEB-S3-005`。
  验收标准：能统一查询、预览、下载主要产物。
  完成情况：未完成。
  备注：产物必须区分 JSON、HTML、Markdown、CSV、Parquet、tar.gz。

- [ ] `WEB-S3-005` `P1`
  目标：实现 Market UI API。
  输入：OHLCV 数据模型和 MarketService。
  输出：`/api/ui/market/ohlcv`、`/api/ui/market/symbols`。
  修改范围：`api/routers/ui/market.py`、相关测试。
  前置依赖：`WEB-S1-005`。
  可并行：`WEB-S3-004`。
  验收标准：能按 symbol 和日期范围返回 K 线数据。
  完成情况：未完成。
  备注：返回字段应包含 time/open/high/low/close/volume。

- [ ] `WEB-S3-006` `P1`
  目标：将 API 入口最终收敛为单一入口，删除另一个入口，并确保文档和代码都只指向同一个主入口, 同时将`src/api/`下的代码和文件迁移到`api/`下, 保证项目结构清晰。
  输入：`api/main.py`、`src/api/main.py`、`src/api/app.py`、`docs/APIReference.md`、`docs/UserManual.md`。
  输出：单一 API 入口说明、旧入口删除说明、迁移完成后的文档收口。
  修改范围：`api/main.py`、`src/api/main.py`、`src/api/app.py`、`docs/APIReference.md`、`docs/UserManual.md`、`docs/web-plan.md`、相关测试。
  前置依赖：`WEB-S3-001`。
  可并行：无。
  验收标准：仓库只保留一个对外 API 启动入口；`src/api/main.py` 已删除；`src/api/`下的代码和文件已迁移到`api/`下；所有文档、测试和部署说明都已切换到唯一主入口；旧入口不再作为运行时契约出现。
  完成情况：未完成。
  备注：以 `api/main.py` 作为唯一主入口，迁移期兼容层在任务完成时一并清理。

- [ ] `WEB-S3-007` `P0`
  目标：制定并实现 API versioning 与兼容策略。
  输入：`api/main.py`、`docs/APIReference.md`、Web UI API 设计。
  输出：`/api/ui/v1` 或等价版本化入口、旧 API 兼容说明。
  修改范围：`api/main.py`、`api/routers/ui/`、`docs/APIReference.md`、相关测试。
  前置依赖：`WEB-S3-001`、`WEB-S3-006`。
  可并行：`WEB-S7-008`。
  验收标准：Web 仅依赖版本化 UI API；旧 API 路由不被破坏；新增/废弃 API 有兼容策略；OpenAPI 文档能区分管理接口、查询接口和 UI BFF 接口。
  完成情况：未完成。
  备注：避免前端直接依赖内部领域 API，降低后续重构成本。

---

## 10. Stage 4：Web 前端工程与设计系统（P0）

### Stage 目标

- 建立 React Web 前端工程。
- 实现基础布局、路由、API client 和设计系统。

### 阶段交付物

- `web/` 前端工程。
- Dashboard 初版。
- 通用页面布局、表格、表单、状态组件。

### 任务清单

- [ ] `WEB-S4-001` `P0`
  目标：初始化前端工程。
  输入：技术栈决策。
  输出：`web/`。
  修改范围：`web/package.json`、`web/src/`、`web/vite.config.ts`。
  前置依赖：`WEB-S0-001`。
  可并行：`WEB-S3-001`。
  验收标准：React + TypeScript + Vite 可启动、可构建。
  完成情况：未完成。
  备注：不要把前端文件散落到后端目录。

- [ ] `WEB-S4-002` `P0`
  目标：接入 Tailwind CSS 和 shadcn/ui。
  输入：前端工程。
  输出：基础设计系统。
  修改范围：`web/src/styles/`、`web/components.json`、`web/src/components/`。
  前置依赖：`WEB-S4-001`。
  可并行：`WEB-S4-003`。
  验收标准：可使用按钮、表格、表单、弹窗、侧边栏、toast。
  完成情况：未完成。
  备注：视觉方向采用数据密集型金融分析后台。

- [ ] `WEB-S4-003` `P0`
  目标：实现前端路由和 API client。
  输入：UI API 设计。
  输出：路由结构和请求封装。
  修改范围：`web/src/routes/`、`web/src/lib/api/`。
  前置依赖：`WEB-S4-001`、`WEB-S3-001`。
  可并行：`WEB-S4-002`。
  验收标准：前端能调用 `/api/ui/system/status` 并显示结果。
  完成情况：未完成。
  备注：请求错误必须有统一展示。

- [ ] `WEB-S4-004` `P1`
  目标：实现基础布局和导航。
  输入：页面模块设计。
  输出：Dashboard shell。
  修改范围：`web/src/components/layout/`、`web/src/routes/`。
  前置依赖：`WEB-S4-002`、`WEB-S4-003`。
  可并行：无。
  验收标准：有侧边栏、顶部栏、主内容区和移动端基础适配。
  完成情况：未完成。
  备注：导航必须按用户任务组织，不按代码模块堆叠。

---

## 11. Stage 5：UserManual 操作向导（P0）

### Stage 目标

- 把 `docs/UserManual.md` 的操作流程转为可点击、可校验、可追踪的 Web 向导。

### 阶段交付物

- Workflow 页面。
- 步骤详情页。
- 参数表单。
- Job 创建和跳转。

### 任务清单

- [ ] `WEB-S5-001` `P0`
  目标：定义 UserManual Workflow 数据结构。
  输入：`docs/UserManual.md`。
  输出：Workflow definitions。
  修改范围：`src/services/workflow_service.py`、相关测试。
  前置依赖：`WEB-S3-003`。
  可并行：无。
  验收标准：覆盖安装检查、配置、数据库、pipeline、盘前盘后、快照、OHLCV、策略、回测、优化、规则池、调度、报表。
  完成情况：未完成。
  备注：每个 workflow step 必须有参数 schema。

- [ ] `WEB-S5-002` `P0`
  目标：实现操作向导页面。
  输入：Workflow API。
  输出：`web/src/features/workflows/`。
  修改范围：`web/src/features/workflows/`、`web/src/routes/`。
  前置依赖：`WEB-S4-004`、`WEB-S5-001`。
  可并行：`WEB-S5-003`。
  验收标准：用户能看到完整流程、当前步骤说明、前置条件和运行入口。
  完成情况：未完成。
  备注：不要让用户手写 CLI 命令。

- [ ] `WEB-S5-003` `P0`
  目标：实现参数表单与高风险确认。
  输入：Workflow step schema。
  输出：动态表单和确认弹窗。
  修改范围：`web/src/features/workflows/`、`web/src/components/forms/`。
  前置依赖：`WEB-S4-002`、`WEB-S5-001`。
  可并行：`WEB-S5-002`。
  验收标准：日期、trader、limit、force、export_html、mode 等参数可填写；高风险操作必须二次确认。
  完成情况：未完成。
  备注：确认弹窗必须展示参数摘要和影响说明。

- [ ] `WEB-S5-004` `P0`
  目标：操作向导接入 Job Center。
  输入：Job API、Workflow 页面。
  输出：运行后创建 Job 并跳转任务详情。
  修改范围：`web/src/features/workflows/`、`web/src/features/jobs/`。
  前置依赖：`WEB-S3-002`、`WEB-S5-002`。
  可并行：无。
  验收标准：从向导运行任一任务后可在 Job Center 查看状态、日志和产物。
  完成情况：未完成。
  备注：失败时必须展示可读错误和下一步建议。

---

## 12. Stage 6：数据查看与可视化（P1）

### Stage 目标

- 实现用户最关心的数据查看能力：K 线、报表、快照、回测、告警。

### 阶段交付物

- 市场数据页。
- 报表中心。
- 快照中心。
- 回测中心。
- 告警中心。

### 任务清单

- [ ] `WEB-S6-001` `P1`
  目标：实现 Job 任务中心页面。
  输入：Job API。
  输出：`web/src/features/jobs/`。
  修改范围：`web/src/features/jobs/`、`web/src/routes/`。
  前置依赖：`WEB-S3-002`、`WEB-S4-004`。
  可并行：`WEB-S6-002`。
  验收标准：支持任务列表、过滤、详情、日志、产物、重跑入口。
  完成情况：未完成。
  备注：长任务轮询间隔应可控，避免过度请求。

- [ ] `WEB-S6-002` `P1`
  目标：实现市场数据与个股 K 线页面。
  输入：Market UI API。
  输出：`web/src/features/market/`。
  修改范围：`web/src/features/market/`、`web/src/routes/`。
  前置依赖：`WEB-S3-005`、`WEB-S4-004`。
  可并行：`WEB-S6-001`。
  验收标准：可搜索 symbol，选择日期范围，展示 K 线和 OHLCV 表格。
  完成情况：未完成。
  备注：K 线图使用 TradingView Lightweight Charts。

- [ ] `WEB-S6-003` `P1`
  目标：实现报表中心。
  输入：现有 reports API、Artifact API。
  输出：`web/src/features/reports/`。
  修改范围：`web/src/features/reports/`、`web/src/routes/`。
  前置依赖：`WEB-S3-004`、`WEB-S4-004`。
  可并行：`WEB-S6-004`。
  验收标准：可查看盘前日报、盘后考核、HTML 报表和 JSON 详情。
  完成情况：未完成。
  备注：HTML 报表可用 iframe 或安全预览方式展示。

- [ ] `WEB-S6-004` `P1`
  目标：实现快照中心。
  输入：快照 API。
  输出：`web/src/features/snapshots/`。
  修改范围：`web/src/features/snapshots/`、`web/src/routes/`。
  前置依赖：`WEB-S1-005`、`WEB-S4-004`。
  可并行：`WEB-S6-003`。
  验收标准：可构建快照、查询快照、查看 hot topics、topic constituents、strong symbols。
  完成情况：未完成。
  备注：快照构建必须走 Job。

- [ ] `WEB-S6-005` `P0`
  目标：实现回测中心。
  输入：BacktestOperationService、backtest_results API。
  输出：`web/src/features/backtest/`。
  修改范围：`web/src/features/backtest/`、`web/src/routes/`。
  前置依赖：`WEB-S1-007`、`WEB-S3-004`、`WEB-S4-004`。
  可并行：`WEB-S6-006`。
  验收标准：可运行回测、查看结果列表、详情、报告、规则验真和关键指标图表。
  完成情况：未完成。
  备注：回测运行必须走 Job。

- [ ] `WEB-S6-006` `P0`
  目标：实现告警中心。
  输入：现有 alerts API。
  输出：`web/src/features/alerts/`。
  修改范围：`web/src/features/alerts/`、`web/src/routes/`。
  前置依赖：`WEB-S4-004`。
  可并行：`WEB-S6-005`。
  验收标准：可查看告警历史、过滤、确认、解决、发送测试告警。
  完成情况：未完成。
  备注：发送测试告警必须二次确认。

- [ ] `WEB-S6-007` `P0`
  目标：实现策略版本、优化和规则池页面。
  输入：StrategyOperationService、OptimizeService、RulePoolService。
  输出：`web/src/features/strategy/`、`web/src/features/optimize/`、`web/src/features/rule-pool/`。
  修改范围：相关前端 feature 目录。
  前置依赖：`WEB-S1-006`、`WEB-S1-008`、`WEB-S4-004`。
  可并行：无。
  验收标准：可构建/查看策略版本，运行优化，查看和审核规则池。
  完成情况：未完成。
  备注：批量规则审核必须二次确认。

- [ ] `WEB-S6-008` `P0`
  目标：实现数据导入、信号、Persona、MarketState、Kaipan 和数据监控页面。
  输入：`WEB-S1-009`、`WEB-S0-003` 覆盖矩阵。
  输出：补充功能页面。
  修改范围：`web/src/features/imports/`、`web/src/features/signals/`、`web/src/features/persona/`、`web/src/features/kaipan/`、`web/src/features/data-health/`、`web/src/routes/`。
  前置依赖：`WEB-S1-009`、`WEB-S2-006`、`WEB-S4-004`。
  可并行：`WEB-S6-005`、`WEB-S6-006`。
  验收标准：Web 支持交易记录导入、crawl state 迁移、信号列表、persona 样例生成、market-state 构建、Kaipan fetch/normalize/status/run、数据监控 Dashboard 生成与查看。
  完成情况：未完成。
  备注：文件上传和导入操作必须限制文件类型、大小和存储目录，并记录审计。

- [ ] `WEB-S6-009` `P1`
  目标：实现报表和 HTML 产物安全预览。
  输入：Artifact API、报表中心、HTML/Markdown 产物。
  输出：安全预览组件和策略。
  修改范围：`web/src/features/reports/`、`web/src/components/artifacts/`、`api/routers/ui/artifacts.py`、相关测试。
  前置依赖：`WEB-S3-004`、`WEB-S6-003`。
  可并行：无。
  验收标准：HTML 预览使用 sandbox 或服务端安全响应头；禁止执行不可信脚本；Markdown 渲染经过安全过滤；下载接口限制在允许的产物目录内。
  完成情况：未完成。
  备注：LLM 或外部数据生成的 HTML/Markdown 不能按可信内容处理。

---

## 13. Stage 7：权限、安全与操作保护（P0）

### Stage 目标

- 保护敏感信息。
- 降低误操作风险。
- 为本地/内网使用提供最小权限控制。

### 阶段交付物

- 登录/session 或 API Key 保护。
- 角色权限控制。
- 配置脱敏。
- 设置项编辑、保存、备份和恢复。
- 高风险操作确认机制。
- 审计记录。

### 任务清单

- [ ] `WEB-S7-001` `P0`
  目标：实现 Web API 生产级鉴权基线。
  输入：现有 API Key 机制。
  输出：UI API 鉴权与会话/API Key 保护。
  修改范围：`api/deps.py`、`api/routers/ui/`、前端 API client。
  前置依赖：`WEB-S3-001`。
  可并行：`WEB-S7-002`。
  验收标准：UI API 可按配置启用 API Key 或登录会话；未授权请求被拒绝；鉴权失败有统一错误；本地开发关闭鉴权必须显式配置。
  完成情况：未完成。
  备注：本地开发可配置关闭鉴权。

- [ ] `WEB-S7-002` `P0`
  目标：实现配置脱敏和敏感字段保护。
  输入：ConfigService。
  输出：脱敏规则和测试。
  修改范围：`src/services/config_service.py`、相关测试。
  前置依赖：`WEB-S1-002`。
  可并行：`WEB-S7-001`。
  验收标准：cookie、token、api_key、password、secret、DATABASE_URL 密码不明文返回。
  完成情况：未完成。
  备注：日志中也不得输出敏感信息。

- [ ] `WEB-S7-003` `P0`
  目标：实现高风险操作确认协议。
  输入：WorkflowService、Job API。
  输出：后端确认字段校验和前端确认弹窗。
  修改范围：`src/services/workflow_service.py`、`api/routers/ui/jobs.py`、`web/src/features/workflows/`。
  前置依赖：`WEB-S5-003`。
  可并行：无。
  验收标准：未提供确认字段时，高风险任务不能创建。
  完成情况：未完成。
  备注：不能只做前端确认，后端也必须校验。

- [ ] `WEB-S7-004` `P0`
  目标：实现操作审计。
  输入：Job Center、用户来源信息。
  输出：审计记录。
  修改范围：Job 模型、JobService、相关测试。
  前置依赖：`WEB-S2-002`、`WEB-S7-001`。
  可并行：无。
  验收标准：记录谁在什么时候发起了什么操作，参数摘要是什么。
  完成情况：未完成。
  备注：审计参数同样必须脱敏。

- [ ] `WEB-S7-005` `P0`
  目标：实现设置项读取、编辑校验、保存、备份和恢复 service。
  输入：`config/app.yaml`、`src/common/config.py`、`config/settings.py`、ConfigService。
  输出：`ConfigEditService`。
  修改范围：`src/services/config_edit_service.py`、`tests/services/test_config_edit_service.py`。
  前置依赖：`WEB-S1-002`、`WEB-S7-002`。
  可并行：`WEB-S7-006`。
  验收标准：支持读取当前配置、生成可编辑配置 schema、校验配置草稿、保存到 `config/app.yaml`、保存前写入 `config/backups/app.YYYYMMDD-HHMMSS.yaml`、从备份恢复；保存失败不能覆盖原配置。
  完成情况：未完成。
  备注：敏感项只允许保存为空值或环境变量引用，例如 `"${DASHSCOPE_API_KEY}"`，不得把明文密钥写入 YAML。

- [ ] `WEB-S7-006` `P0`
  目标：实现设置项 API。
  输入：`ConfigEditService`。
  输出：`/api/ui/settings` 系列接口。
  修改范围：`api/routers/ui/settings.py`、`api/main.py`、`tests/api/test_ui_settings.py`。
  前置依赖：`WEB-S7-005`。
  可并行：`WEB-S7-007`。
  验收标准：支持获取脱敏配置、获取编辑 schema、校验配置草稿、保存配置、列出备份、恢复备份；保存和恢复必须要求二次确认字段。
  完成情况：未完成。
  备注：API 返回的 diff 必须脱敏，不能包含密钥明文。

- [ ] `WEB-S7-007` `P0`
  目标：实现 Web 设置中心页面。
  输入：Settings API、配置字段分组。
  输出：`web/src/features/settings/`。
  修改范围：`web/src/features/settings/`、`web/src/routes/`。
  前置依赖：`WEB-S4-004`、`WEB-S7-006`。
  可并行：无。
  验收标准：用户可以在 Web 中编辑基础设置、数据库、API、调度、数据源、爬虫、LLM、Persona、Kaipan、告警等主要设置项；保存前显示校验结果和 diff；保存成功显示备份路径；恢复备份必须二次确认。
  完成情况：未完成。
  备注：敏感字段输入框必须提示推荐使用环境变量引用，不回显已保存密钥。

- [ ] `WEB-S7-008` `P0`
  目标：实现角色权限模型。
  输入：Web 功能清单、Job 类型注册表、Settings API。
  输出：`viewer / operator / admin` 最小角色模型。
  修改范围：`api/deps.py`、`api/routers/ui/`、`src/services/job_registry.py`、`web/src/lib/auth/`、相关测试。
  前置依赖：`WEB-S7-001`、`WEB-S2-006`。
  可并行：`WEB-S3-007`。
  验收标准：viewer 只能查看；operator 可运行非破坏性任务；admin 可执行配置保存、数据库迁移、恢复、批量审核、告警测试、调度启动等高风险操作；后端强制校验权限，不能只依赖前端隐藏按钮。
  完成情况：未完成。
  备注：权限等级必须写入 `WEB-S0-003` 覆盖矩阵。

- [ ] `WEB-S7-009` `P0`
  目标：补齐配置编辑的生产级并发与回滚保护。
  输入：`ConfigEditService`、Settings API、配置文件路径。
  输出：配置编辑锁、原子写入、保存后验证和恢复演练。
  修改范围：`src/services/config_edit_service.py`、`api/routers/ui/settings.py`、相关测试。
  前置依赖：`WEB-S7-005`、`WEB-S7-006`。
  可并行：`WEB-S7-008`。
  验收标准：同一时间只允许一个配置保存事务；写入采用临时文件+原子替换；保存后自动重新加载并校验配置；失败自动保留原配置；恢复备份后记录审计并提示需要重启或重载的服务。
  完成情况：未完成。
  备注：必须明确哪些配置支持热加载，哪些配置需要重启 API/Worker。

- [ ] `WEB-S7-010` `P1`
  目标：实现文件上传与导入安全策略。
  输入：交易记录导入、备份恢复、Artifact 下载需求。
  输出：上传/下载安全限制。
  修改范围：`api/routers/ui/`、`src/services/artifact_service.py`、`src/services/pipeline_service.py`、相关测试。
  前置依赖：`WEB-S6-008`、`WEB-S7-008`。
  可并行：无。
  验收标准：上传文件限制后缀、MIME、大小和保存目录；路径必须规范化并禁止目录穿越；导入前支持 dry-run；下载只能访问白名单产物目录。
  完成情况：未完成。
  备注：`import-trade-logs` 支持多种文件格式，Web 必须显式限制输入边界。

---

## 14. Stage 8：测试、验收与文档闭环（P0）

### Stage 目标

- 确保 Web 后台可用、稳定、可维护。
- 确保文档和真实功能一致。

### 阶段交付物

- 后端测试。
- 前端测试或构建验证。
- Web 使用说明。
- UserManual 更新。

### 任务清单

- [ ] `WEB-S8-001` `P0`
  目标：补齐 service 单元测试。
  输入：Stage 1 service。
  输出：pytest 测试。
  修改范围：`tests/services/`。
  前置依赖：`WEB-S1-003`、`WEB-S1-004`、`WEB-S1-005`。
  可并行：`WEB-S8-002`。
  验收标准：关键 service 有正常路径、参数错误、缺失前置数据、失败路径测试。
  完成情况：未完成。
  备注：测试不依赖真实外网数据。

- [ ] `WEB-S8-002` `P0`
  目标：补齐 UI API 测试。
  输入：Stage 3 API。
  输出：API 测试。
  修改范围：`tests/api/`。
  前置依赖：`WEB-S3-002`、`WEB-S3-003`、`WEB-S3-004`。
  可并行：`WEB-S8-001`。
  验收标准：system、workflow、job、artifact、market API 均有测试。
  完成情况：未完成。
  备注：必须覆盖未授权和高风险确认失败场景。

- [ ] `WEB-S8-003` `P1`
  目标：补齐前端构建和基础交互验证。
  输入：Web 前端工程。
  输出：前端验证命令和结果。
  修改范围：`web/`、`package.json` 脚本。
  前置依赖：`WEB-S4-004`、`WEB-S6-001`。
  可并行：`WEB-S8-001`。
  验收标准：`typecheck`、`lint`、`build` 通过；关键页面可访问；至少覆盖 workflow、job、settings、auth、artifact 预览的基础交互测试。
  完成情况：未完成。
  备注：如果引入前端测试框架，优先覆盖 workflow 和 job 页面。

- [ ] `WEB-S8-004` `P0`
  目标：完成 UserManual 全功能 Web 验收。
  输入：Web 后台、UserManual。
  输出：验收记录。
  修改范围：`docs/UserManual.md`、`docs/web-plan.md`、`docs/Web-TaskList.md`。
  前置依赖：`WEB-S0-003`、`WEB-S5-004`、`WEB-S6-002`、`WEB-S6-003`、`WEB-S6-004`、`WEB-S6-005`、`WEB-S6-006`、`WEB-S6-007`、`WEB-S6-008`、`WEB-S7-007`、`WEB-S7-008`。
  可并行：无。
  验收标准：UserManual 中每个功能都有对应 Web 页面或 Web 操作入口。
  完成情况：未完成。
  备注：不能只验收 happy path，必须包含失败提示和空状态。

- [ ] `WEB-S8-005` `P1`
  目标：更新 Web 使用说明。
  输入：最终 Web 功能。
  输出：Web 使用文档。
  修改范围：`docs/UserManual.md` 或新增 `docs/WebUserManual.md`。
  前置依赖：`WEB-S8-004`。
  可并行：无。
  验收标准：用户可以按文档启动 API、启动 Web、完成主流程。
  完成情况：未完成。
  备注：文档必须说明敏感配置和高风险操作。

- [ ] `WEB-S8-006` `P0`
  目标：补齐生产级端到端验收测试。
  输入：Web 后台、Job Center、权限模型、UserManual 覆盖矩阵。
  输出：端到端验收测试和验收记录。
  修改范围：`tests/e2e/`、`web/` 测试目录、`docs/Web-TaskList.md`。
  前置依赖：`WEB-S8-001`、`WEB-S8-002`、`WEB-S8-003`、`WEB-S8-004`。
  可并行：无。
  验收标准：覆盖完整主链路、任务失败恢复、服务重启后 Job 状态恢复、权限拒绝、高风险确认失败、配置保存回滚、Artifact 安全预览、K 线空数据/大数据、告警测试二次确认。
  完成情况：未完成。
  备注：端到端测试应优先使用 mock/snapshot 数据，避免依赖真实外网。

- [ ] `WEB-S8-007` `P1`
  目标：建立前后端契约测试。
  输入：OpenAPI schema、前端 API client、UI API。
  输出：契约验证。
  修改范围：`tests/api/`、`web/src/lib/api/`、构建脚本。
  前置依赖：`WEB-S3-007`、`WEB-S4-003`。
  可并行：`WEB-S8-003`。
  验收标准：后端 OpenAPI schema 变化能被前端类型生成或契约测试捕获；前端不调用未定义接口；破坏性 API 变更会导致 CI/本地验证失败。
  完成情况：未完成。
  备注：可先使用生成的 TypeScript 类型或轻量 schema 校验，不必一开始引入复杂平台。

---

## 15. Stage 9：生产部署、运维与发布回滚（P0）

### Stage 目标

- 让 Web 管理后台具备生产交付能力，而不是只停留在本地 Demo。
- 明确部署、健康检查、日志、监控、备份恢复、发布和回滚流程。

### 阶段交付物

- 生产部署方案。
- Docker/Compose 或等价部署脚本。
- 健康检查与可观测性。
- 备份恢复演练。
- 发布和回滚文档。

### 任务清单

- [ ] `WEB-S9-001` `P0`
  目标：制定生产部署拓扑。
  输入：FastAPI、Web 前端、PostgreSQL、Redis/队列候选、Job Worker。
  输出：生产部署说明。
  修改范围：`docs/WebDeployment.md`、`docs/web-plan.md`、`docs/Web-TaskList.md`。
  前置依赖：`WEB-S2-005`、`WEB-S3-007`、`WEB-S4-001`。
  可并行：`WEB-S9-002`。
  验收标准：明确 API、静态前端、Worker、数据库、文件产物目录、日志目录、配置和密钥注入方式；明确单机本地部署与内网部署两种模式。
  完成情况：未完成。
  备注：如果暂不引入 Redis/外部队列，必须说明数据库轮询 Worker 的运行方式和限制。

- [ ] `WEB-S9-002` `P0`
  目标：实现生产构建和启动脚本。
  输入：后端 API、前端工程、Job Worker。
  输出：构建和启动命令。
  修改范围：`docker-compose.yml`、`Dockerfile` 或等价脚本、`README.md`/部署文档、前端构建脚本。
  前置依赖：`WEB-S4-001`、`WEB-S2-005`。
  可并行：`WEB-S9-001`。
  验收标准：一条文档化流程可完成依赖安装、前端构建、数据库迁移、API 启动、Worker 启动和健康检查；生产启动不使用 `--reload`。
  完成情况：未完成。
  备注：不得把本地开发命令当作生产部署方案。

- [ ] `WEB-S9-003` `P0`
  目标：实现健康检查、日志和监控指标。
  输入：SystemService、JobService、数据库连接、产物目录。
  输出：健康检查和可观测性接口。
  修改范围：`api/routers/ui/system.py`、`src/services/system_service.py`、日志配置、相关测试。
  前置依赖：`WEB-S3-001`、`WEB-S2-005`。
  可并行：`WEB-S9-004`。
  验收标准：健康检查覆盖 API、数据库、Job Worker 心跳、产物目录读写、配置加载；Dashboard 展示最近失败任务、任务耗时、数据新鲜度、告警摘要；日志可按 request/job 关联追踪。
  完成情况：未完成。
  备注：至少提供机器可读 JSON 健康检查，便于反向代理或监控系统探测。

- [ ] `WEB-S9-004` `P0`
  目标：实现备份恢复和回滚演练。
  输入：backup/restore service、配置备份、数据库迁移、Job/Artifact 存储。
  输出：备份恢复演练文档和验证任务。
  修改范围：`docs/WebDeployment.md`、`tests/e2e/`、相关 service 测试。
  前置依赖：`WEB-S1-009`、`WEB-S7-009`。
  可并行：`WEB-S9-003`。
  验收标准：可备份数据库、配置、关键产物和 Job 元数据；可在测试环境恢复；恢复操作有二次确认和审计；发布失败时有明确回滚步骤。
  完成情况：未完成。
  备注：恢复是破坏性操作，必须要求 admin 权限。

- [ ] `WEB-S9-005` `P1`
  目标：补齐 TLS、反向代理和静态资源缓存建议。
  输入：生产部署拓扑、前端构建产物。
  输出：反向代理和缓存配置建议。
  修改范围：`docs/WebDeployment.md`。
  前置依赖：`WEB-S9-001`、`WEB-S9-002`。
  可并行：无。
  验收标准：文档说明 Nginx/Caddy 或等价反向代理、HTTPS 终止、API 路径转发、静态资源缓存、上传大小限制和超时设置。
  完成情况：未完成。
  备注：本地单机使用可不强制 TLS，但内网/多人使用必须提供建议配置。

---

## 16. 执行顺序总览

推荐执行顺序：

1. `WEB-S0-001` 至 `WEB-S0-003`
2. `WEB-S1-001` 至 `WEB-S1-005`
3. `WEB-S1-006` 至 `WEB-S1-009`
4. `WEB-S2-001` 至 `WEB-S2-006`
5. `WEB-S3-001` 至 `WEB-S3-007`
6. `WEB-S4-001` 至 `WEB-S4-004`
7. `WEB-S5-001` 至 `WEB-S5-004`
8. `WEB-S6-001` 至 `WEB-S6-009`
9. `WEB-S7-001` 至 `WEB-S7-010`
10. `WEB-S8-001` 至 `WEB-S8-007`
11. `WEB-S9-001` 至 `WEB-S9-005`

设置项编辑与保存属于 Web 最小可用能力，`WEB-S7-005` 至 `WEB-S7-007` 应在 `WEB-S8-004` 之前完成。

---

## 17. 最小可用版本定义

Web 后台最小可用版本必须完成：

- `WEB-S0-003`
- `WEB-S1-001` 至 `WEB-S1-009`
- `WEB-S2-001` 至 `WEB-S2-006`
- `WEB-S3-001` 至 `WEB-S3-003`
- `WEB-S3-007`
- `WEB-S4-001` 至 `WEB-S4-004`
- `WEB-S5-001` 至 `WEB-S5-004`
- `WEB-S6-001` 至 `WEB-S6-008`
- `WEB-S7-001` 至 `WEB-S7-009`
- `WEB-S8-001` 至 `WEB-S8-006`
- `WEB-S9-001` 至 `WEB-S9-004`

达到最小可用版本后，用户应能：

1. 通过 Web 查看系统状态。
2. 通过 Web 跑配置检查和数据库检查。
3. 通过 Web 编辑、校验、保存和恢复主要设置项。
4. 通过 Web 跑 pipeline、快照、OHLCV、盘前、盘后。
5. 通过 Web 查看任务状态、日志和产物。
6. 通过 Web 查看 K 线、日报、考核、快照、回测、告警、策略版本、优化结果和规则池。
7. 通过 Web 覆盖 UserManual 中全部常用命令和独立入口。
8. 通过生产级 Job Center 在服务重启、任务失败、权限拒绝、高风险确认失败场景下保持可追踪。
9. 具备生产部署、健康检查、备份恢复和发布回滚文档。
10. 不需要手写 CLI 命令即可完成主链路。
