# WEB-S6-008 Data Ops Center Design

> 目标：把 `WEB-S6-008` 拆成统一的 Web 数据运维中心设计，覆盖数据导入、信号、Persona、MarketState、Kaipan 和数据监控六类能力，并为后续三份实施计划提供统一边界。

## 1. 设计目标

### 1.1 核心目标

- 把 `docs/Web-UserManual-Coverage.md` 中与数据导入、信号、Persona、MarketState、Kaipan 和数据监控相关的能力，落成可用的 Web 页面。
- 前端只调用版本化 UI BFF，不直接调用 service 内部方法，也不直接依赖文件路径、脚本入口或 shell 命令。
- 复用现有 `SetupService`、`SignalService`、`PersonaService`、`KaipanService`、`DashboardService` 和对应 job/type 约束，不重建一套平行数据体系。
- 把高风险写入操作、长任务执行和运维入口统一纳入 Job Center、权限和审计体系。

### 1.2 设计原则

- 先复用现有 service，再补 UI BFF，再做页面。
- 长任务一律走 Job Center，不在页面中直连执行器。
- 文件上传、导入、迁移、调度等写入动作必须显式确认，并保留审计字段。
- 查询类页面尽量只读，支持筛选、详情、预览和产物跳转。
- 页面结构沿用当前控制台风格：`PageHeader` + 数据面板 + 局部空态 / 错误态。

### 1.3 不做的事

- 不在 `WEB-S6-008` 中改造底层业务算法。
- 不在本阶段引入新的数据模型或新的调度框架。
- 不把 `signal`、`persona`、`kaipan` 再拆成新的独立产品线。
- 不把设置编辑、权限、备份恢复这类 Stage 7/8 能力提前塞进本任务。

## 2. 范围划分

### 2.1 本任务必须覆盖

- 交易记录导入
- crawl state 迁移
- 信号列表
- persona 示例数据生成
- MarketState 构建与查看
- Kaipan fetch / normalize / status / run
- 数据监控 Dashboard 查看

### 2.2 本任务分成 3 个实施包

1. `WEB-S6-008A` 数据分析工作台
   - 信号中心
   - Persona 工作台
   - MarketState 工作台

2. `WEB-S6-008B` 数据导入工作台
   - 交易记录导入
   - crawl state 迁移
   - 导入结果预览与审计

3. `WEB-S6-008C` 运维与监控工作台
   - Kaipan 调度
   - Kaipan 状态
   - 数据监控 Dashboard

这样拆分的原因是：

- `A` 以读取和生成结果为主，适合先打通页面模式和 UI BFF 约定。
- `B` 是写入型能力，风险最高，需要独立确认和独立验证。
- `C` 覆盖调度和监控，依赖最广，适合作为收口阶段。

## 3. 现有能力基线

### 3.1 已存在的后端 service

- `SetupService`
  - 支持 `init-config`、`init-project`、`seed-data`、`import-trade-logs`、`migrate-crawl-state`
- `SignalService`
  - 支持信号列表查询
- `PersonaService`
  - 支持样例 clusters 生成和 MarketState 构建
- `KaipanService`
  - 支持 fetch、normalize、status、run
- `DashboardService`
  - 支持 CLI / HTML / both 三种输出模式

### 3.2 已存在的 UI 约束

- 当前 Web 统一使用 `/api/ui/v1/*` 前缀。
- Jobs、Workflows、Artifacts、Market、Snapshots、Strategy Studio 等页面已形成统一控制台风格。
- 长任务创建、状态查询和日志查看已有 Job Center 模式可复用。

### 3.3 已识别的对接入口

- `list-signals` 对应 `SignalService.list_signals()`
- `persona-init-sample` 对应 `PersonaService.build_sample_clusters()`
- `market-state-build` 对应 `PersonaService.build_market_state()`
- `import-trade-logs` 对应 `SetupService.import_trade_logs()`
- `migrate-crawl-state` 对应 `SetupService.migrate_crawl_state()`
- `KaipanScheduler fetch / normalize / status / run` 对应 `KaipanService`
- `dashboard --mode cli/html/both` 对应 `DashboardService.build_report()`

## 4. UI BFF 设计

### 4.1 总体约定

新增或补齐的 UI BFF 必须满足：

- 只做参数整理、权限判断、结果标准化和错误映射。
- 不把文件系统路径暴露给前端。
- 不让前端拼接 shell 命令或直接选择内部函数名。
- 对写入型接口返回可审计的摘要、产物路径和 Job 信息。

### 4.2 建议路由分组

#### 4.2.1 Signals

- `GET /api/ui/v1/signals`

返回字段建议包括：

- `signal_id`
- `symbol`
- `side`
- `confidence`
- `timestamp`
- `trader_id`
- `strategy_version_id`
- `context_summary`

#### 4.2.2 Persona

- `POST /api/ui/v1/persona/sample`
- `POST /api/ui/v1/persona/market-state/build`

返回字段建议包括：

- `clusters_path`
- `market_state_path`
- `source`
- `trader_count`
- `clusters_count`
- `market_state`

#### 4.2.3 Imports

- `POST /api/ui/v1/imports/trade-logs`
- `POST /api/ui/v1/imports/crawl-state/migrate`

返回字段建议包括：

- `job_id` 或 `result`
- `dry_run`
- `file_kind`
- `rows_seen`
- `parsed_count`
- `stored_count`
- `issues`

#### 4.2.4 Kaipan

- `POST /api/ui/v1/kaipan/fetch`
- `POST /api/ui/v1/kaipan/normalize`
- `GET /api/ui/v1/kaipan/status`
- `POST /api/ui/v1/kaipan/run`

返回字段建议包括：

- `trade_date`
- `slot`
- `slots`
- `slot_results`
- `normalize_results`
- `latest_slot`

#### 4.2.5 Data Health

- `GET /api/ui/v1/data-health/dashboard`

返回字段建议包括：

- `report`
- `html_path`
- `critical_alerts`
- `exit_code`

### 4.3 路由拆分建议

- `api/routers/ui/signals.py`
- `api/routers/ui/persona.py`
- `api/routers/ui/imports.py`
- `api/routers/ui/kaipan.py`
- `api/routers/ui/data_health.py`

如果后续发现 `persona` 与 `market-state` 的契约共用太多，也可以先合并成一个 `persona.py`，但 UI 上仍建议拆成两个页面区域。

## 5. 页面架构

### 5.1 总体布局

`WEB-S6-008` 不采用单页超级工作台，而采用一个主导航下的 5 个页面：

- `Signals`
- `Persona`
- `Market State`
- `Imports`
- `Kaipan`
- `Data Health`

其中：

- `Signals / Persona / Market State` 属于分析工作台
- `Imports` 属于写入工作台
- `Kaipan / Data Health` 属于运维与监控工作台

### 5.2 分页策略

- 列表页优先提供最近数据和常用筛选。
- 详情页优先展示结构化字段、来源、时间、路径和产物跳转。
- 写入页优先提供参数表单、风险摘要、确认按钮和 Job 结果区。

### 5.3 页面风格

- 延续控制台风格，使用深色数据密度布局。
- 每个页面保留清晰的状态条、主操作区和结果区。
- 长结果默认折叠，避免初始加载过重。

## 6. 子任务设计

### 6.1 `WEB-S6-008A` 数据分析工作台

#### 6.1.1 目标

- 让用户查看信号列表、生成 Persona 示例、构建 MarketState，并在一个分析上下文内完成联动。

#### 6.1.2 页面组成

- `signals`
- `persona`
- `market-state`

#### 6.1.3 交互规则

- 信号列表支持 trader、symbol、日期筛选。
- Persona 页面支持生成 sample clusters，并展示输出路径。
- MarketState 页面支持按日期构建，并展示来源类型 `csv / cache / akshare`。

#### 6.1.4 验收标准

- 可查看信号列表和详情。
- 可生成 persona 示例 clusters。
- 可生成并查看 MarketState JSON。

### 6.2 `WEB-S6-008B` 数据导入工作台

#### 6.2.1 目标

- 让用户通过 Web 完成交易记录导入与 crawl state 迁移，并能看到导入结果和审计摘要。

#### 6.2.2 页面组成

- `trade-log import`
- `crawl-state migrate`

#### 6.2.3 风险控制

- 文件上传必须限制类型、大小和数量。
- 导入前必须提供文件摘要、目标来源和 dry-run 选项。
- 导入后必须展示行数、异常、重复项和存储结果。
- crawl state 迁移必须显示影响范围并提供明确确认。

#### 6.2.4 验收标准

- 可上传并解析支持的交易记录文件。
- 可执行 dry-run 和真实导入。
- 可迁移 crawl state 并返回迁移摘要。

### 6.3 `WEB-S6-008C` 运维与监控工作台

#### 6.3.1 目标

- 让用户从 Web 侧查看和触发 Kaipan 调度流程，并查看数据健康 Dashboard。

#### 6.3.2 页面组成

- `kaipan`
- `data-health`

#### 6.3.3 交互规则

- Kaipan 页面提供 fetch、normalize、status、run 四种操作。
- `fetch`、`normalize`、`run` 走 Job 或受控执行入口。
- `status` 只读，默认展示最新批次和最近目录。
- Dashboard 页面默认展示 HTML 产物与关键告警摘要。

#### 6.3.4 验收标准

- 可按日期和 slot 触发 Kaipan 相关操作。
- 可查看最新状态与最近批次。
- 可查看 Dashboard HTML 或结构化摘要。

## 7. 错误与审计

### 7.1 统一错误处理

- BFF 返回前统一把异常转成页面可读的错误摘要。
- 写入失败要带可追踪的参数摘要和 Job / 产物引用。
- 只读查询失败要返回可理解的空态或错误态，不允许把底层堆栈直接暴露到 UI。

### 7.2 审计要求

- 文件导入要记录文件类型、大小、dry-run、来源和存储结果。
- crawl state 迁移要记录输入路径、迁移摘要和影响条目数。
- Kaipan 调度要记录日期、slot、执行结果和失败 dataset 列表。
- Dashboard 生成要记录输出模式和 HTML 产物路径。

### 7.3 安全要求

- 所有敏感配置与路径信息都必须脱敏或收口到服务端。
- 上传文件必须限制到允许目录之外不可写。
- HTML 产物预览应沿用现有安全策略，不在 `WEB-S6-008` 中新增不受控渲染。

## 8. 测试策略

### 8.1 后端测试

- 新增 UI BFF 的路由测试。
- 新增 service 级单测或参数适配测试。
- 覆盖错误分支、空结果分支和权限校验分支。

### 8.2 前端测试

- 每个新页面至少补 1 组渲染测试和 1 组主要交互测试。
- API client 必须补类型测试或参数/响应断言。
- 对文件导入和高风险操作增加确认分支测试。

### 8.3 端到端验证

- 分别验证 A / B / C 三个实施包。
- 验证页面能调用预期 UI BFF。
- 验证结果与现有 Job、Artifact、Dashboard 行为一致。

## 9. 交付边界与验收

### 9.1 交付物

- `api/routers/ui/signals.py`
- `api/routers/ui/persona.py`
- `api/routers/ui/imports.py`
- `api/routers/ui/kaipan.py`
- `api/routers/ui/data_health.py`
- `web/src/features/signals/`
- `web/src/features/persona/`
- `web/src/features/market-state/`
- `web/src/features/imports/`
- `web/src/features/kaipan/`
- `web/src/features/data-health/`

### 9.2 验收标准

- `WEB-S6-008A` 完成后，能查看信号、生成 Persona 样例、构建 MarketState。
- `WEB-S6-008B` 完成后，能通过 Web 导入交易记录并迁移 crawl state。
- `WEB-S6-008C` 完成后，能通过 Web 触发和查看 Kaipan 流程以及 Dashboard。
- 所有页面都能在 `docs/Web-TaskList.md` 中找到对应验收点。

### 9.3 与既有任务的关系

- `WEB-S6-008` 依赖 `WEB-S1-009`、`WEB-S2-006`、`WEB-S4-004`。
- `WEB-S6-008` 的实现不得破坏 `WEB-S6-007` 已完成的策略工作台。
- 如果某个子任务无法一次做完，应按 A/B/C 三个实施包独立标记进度，不把未完成内容写成已完成。

## 10. 风险

- `persona` 与 `market-state` 虽然都属于分析工作台，但数据来源不同，若 UI 设计过度合并，容易让页面职责混乱。
- `import-trade-logs` 和 `migrate-crawl-state` 都属于写入能力，必须提前定义上传、确认和回滚的最低边界。
- `KaipanService` 涉及调度与批量抓取，若前端直接暴露参数过多，可能诱发误操作。
- Dashboard 的 HTML 预览必须沿用现有安全策略，不能为了方便而放开任意脚本执行。

