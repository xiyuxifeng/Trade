# Trade Strategy AI 重构迁移矩阵

## 1. 迁移信息

- Task ID：`RT-S0-002`
- 日期：`2026-06-10`
- 依据：`Refactor-Current-State-Audit.md` 和当前代码。

处置类型：

- **保留**：作为新架构基础继续使用。
- **改造**：保留实现主体，但调整契约、文案或职责。
- **合并**：多个入口或事实源合并为一个正式入口。
- **迁移**：数据或能力迁移到新领域对象。
- **兼容**：短期只读或转发，禁止继续扩展。
- **退役**：满足条件后删除入口或实现。

Stage 以 `Trade-Refactor-TaskList.md` 为准。

## 2. 能力迁移总表

| 现有能力 | 当前事实源 | 处置 | 目标事实源/新入口 | 保留到 | 退役条件 |
| --- | --- | --- | --- | --- | --- |
| Job 生命周期 | JobService、`jobs` | 保留、改造 | 系统内部统一运行记录；用户在业务页查看“本次运行详情” | 长期 | 不退役底座，只退役普通用户主入口。 |
| JobDefinition | job_registry | 保留、合并 | 唯一运行动作定义或由新 Runtime Contract 派生 | Stage 11 | 新运行契约覆盖参数、权限、风险、重试和并发。 |
| WorkflowDefinition | workflow_service | 兼容、合并 | 业务流程定义由应用服务/Runtime Contract 派生 | Stage 11 | 所有 Workflow 调用已映射到业务动作，兼容 API 无调用。 |
| PipelineSpec | `src/pipelines` | 改造、合并 | 后台步骤编排，不作为产品入口 | Stage 11 | 新运行契约和恢复语义覆盖现有步骤。 |
| WorkflowRun | `workflow_runs` | 保留、改造 | 统一业务 run_id 和步骤追踪 | 长期 | 不退役，字段按 Stage 11 扩展。 |
| ArtifactService | Artifact API、Job 文件 | 保留、改造 | 业务结果附件/导出，不是正式对象 | 长期 | 独立产品入口在 Stage 12 退役。 |
| ConfigProfile | `config_profiles` | 保留、改造 | 系统管理 → 配置 | 长期 | 文件 config_path 不再是 Web 正式引用。 |
| 文章原文 | `raw_articles`、`blog_articles` | 合并、迁移 | Article，数据库为事实源 | Stage 3 | 去重、来源和内容版本迁移完成。 |
| 文章提取结果 | `article_metadata` | 迁移 | ArticleStructure、PromptRun、RuleCandidate | Stage 3 | 新 Schema 回归通过，历史结果可读。 |
| 规则池 | `rule_pool` | 迁移、改造 | RuleCandidate、RuleVersion、RuleFamily | Stage 4 | 所有正式规则有版本、证据、审核和来源。 |
| 回测结果 | BacktestResultRun、RulePool JSON、Job/Artifact | 合并、迁移 | BacktestRun + DatasetSnapshot + RuleApplicabilityProfile | Stage 6 | 新查询只读数据库正式结果，文件仅导出。 |
| OHLCV | `ohlcv_bars`、indicators | 保留、改造 | DatasetSnapshot 下的基础数据 | 长期 | 不退役；补齐版本、缺口和时间语义。 |
| Kaipan | Provider、文件、市场快照表 | 保留、改造 | MarketSnapshot 和 DatasetSnapshot 覆盖记录 | 长期 | 技术入口在 Stage 12 退役。 |
| 市场快照 | `market_snapshots` 等 | 保留、改造 | MarketSnapshot | 长期 | 统一 available_at/captured_at/effective_at。 |
| 市场状态 | Persona MarketState、MarketRegime 表 | 合并、迁移 | MarketState + 模型版本 | Stage 6 | 旧分类无生产调用，API 完成 canonical 映射。 |
| Persona cluster | 文件和 Persona Schema | 兼容、迁移 | AuthorMethodProfile 辅助输入 | Stage 7 | 作者画像三层模型发布，旧文件只读。 |
| TraderProfile | `trader_profiles.json` | 迁移、退役 | AuthorMethodProfile/AuthorRuleProfile | Stage 7 | 数据迁移报告完成，策略不再读取文件。 |
| TraderMemory | `trader_memory` | 改造、迁移 | 作者证据、盘后证据或用户执行记录分表 | Stage 10 | 新对象完成数据分类和迁移。 |
| 策略版本 | TraderStrategyVersion | 迁移、改造 | 稳定 StrategyVersion | Stage 8 | 发布、当前使用、归档、回滚可追溯。 |
| 市场状态规则选择 | StrategyRegimeSelection | 迁移 | DailyRuleSelection | Stage 9 | 每日选择关联正式策略和市场状态。 |
| 盘前 Job/报告 | run-pre-market | 迁移 | DailyStrategyInstance + TradingDayPlan | Stage 9 | 页面可生成、批准和追溯正式对象。 |
| 盘后 Job/报告 | run-after-close、Postmortem | 迁移 | PostMarketReview + 三类 Proposal | Stage 10 | 结构化对象可审核，报告仅为展示。 |
| 旧 Prompt | 无版本文件 | 兼容、退役 | v1 Prompt 套件 | Stage 3 | 满足 Prompt 退役清单后删除。 |
| 新 Prompt 文件 | v1 文件 | 保留、接入 | Prompt Registry/版本化调用链 | 长期 | 接入前不得视为正式能力。 |

## 3. 前端旧入口迁移矩阵

| 旧入口 | 当前能力 | 处置 | 新入口 | 允许保留到 | 最终删除 | 退役条件 |
| --- | --- | --- | --- | --- | --- | --- |
| `/dashboard` | 工程概览 | 改造 | `/` 首页 | Stage 1 | 否，可重定向 | 首页具备今日状态、待办和下一步。 |
| `/jobs` | Job 中心 | 迁移、兼容 | 系统管理 → 任务运行；业务页“运行详情” | Stage 12 | 是，普通入口 | 所有业务页可直接查看和恢复运行。 |
| `/jobs/:jobId` | Job 详情 | 保留、改造 | 统一运行详情 | 长期 | 否 | 用户文案业务化，技术信息仅管理员展开。 |
| `/articles` | 文章入口目录 | 改造 | 研究中心 | Stage 1 | 否，可重定向 | 新研究中心路由上线。 |
| `/articles/run` | Pipeline/Step 表单 | 合并、迁移 | 研究中心 → 添加文章/批量处理 | Stage 3 | 是 | 导入、提取和修复由业务动作自动编排。 |
| `/articles/list` | 文章列表 | 保留、迁移 | 研究中心 → 文章库 | Stage 3 | 否，可重定向 | Article 新契约上线。 |
| `/articles/quality` | 文章质量 | 合并 | 研究中心质量摘要/系统管理批处理详情 | Stage 3 | 是独立页 | 质量指标嵌入新页面。 |
| `/articles/results` | ArticleMetadata 多版本 | 迁移 | 文章详情 → 提取结果/规则审核 | Stage 4 | 是 | 新 Schema 和审核工作台可用。 |
| `/rule-pool` | 规则审核 | 改造 | 规则与回测 → 候选规则/正式规则 | Stage 4 | 否，可重定向 | RuleVersion/RuleFamily 上线。 |
| `/rule-pool/:ruleId` | 规则详情 | 改造 | 规则与回测 → 规则详情 | Stage 4 | 否，可重定向 | 新规则 ID 映射和历史兼容完成。 |
| `/backtest` | 回测工作台 | 改造 | 规则与回测 → 回测实验 | Stage 6 | 否，可重定向 | DatasetSnapshot 和新结果契约上线。 |
| `/backtest/regime` | 分市场状态报告 | 合并 | 回测详情 → 分市场状态结果 | Stage 6 | 是独立页 | 结果页覆盖全周期和分状态。 |
| `/backtest/candidates` | 策略候选版本 | 迁移 | 策略中心 → 草稿与建议 | Stage 8 | 是 | StrategyVersion/Proposal 新契约上线。 |
| `/persona` | Persona 行为规则 | 迁移、退役 | 作者画像 | Stage 7 | 是 | 三层作者画像和历史数据迁移完成。 |
| `/strategies/pre-market` | 盘前 Job 表单 | 改造、迁移 | 每日交易 → 今日盘前 | Stage 9 | 否，可重定向 | TradingDayPlan 可生成、批准和追溯。 |
| `/strategies/after-close` | 盘后 Job/报告 | 改造、迁移 | 每日交易 → 今日盘后 | Stage 10 | 否，可重定向 | PostMarketReview 和 Proposal 可审核。 |
| `/strategies` | 当前重定向首页 | 迁移 | 策略中心 | Stage 8 | 否 | 策略中心正式上线。 |
| `/market` | 市场任务导航 | 合并、迁移 | 系统管理 → 数据与调度；业务页显示数据状态 | Stage 5 | 是旧聚合页 | 数据检查和修复入口已嵌入业务页。 |
| `/market/kaipan` | Kaipan 技术工作台 | 迁移、退役 | 系统管理 → 市场数据 | Stage 5 | 是 | 用户只看到整理盘前/盘后数据等业务动作。 |
| `/market/ohlcv` | OHLCV 技术工作台 | 迁移、退役 | 系统管理 → 历史行情 | Stage 5 | 是 | 历史回灌、增量、缺口和补抓统一。 |
| `/market/snapshots` | 快照浏览 | 迁移、兼容 | 系统管理高级详情/业务运行详情 | Stage 11 | 可选 | 新页面按业务引用打开快照。 |
| `/market/datasets` | 数据集浏览 | 迁移、兼容 | 系统管理高级详情/回测数据版本 | Stage 11 | 可选 | DatasetSnapshot 成为正式入口。 |
| `/artifacts` | 独立产物中心 | 合并、退役 | 业务结果附件、运行详情 | Stage 12 | 是 | 所有 Artifact 都有业务归属和反向链接。 |
| `/artifacts/:artifactId` | 产物详情 | 兼容 | 运行详情/业务结果附件 | Stage 12 | 可保留深链重定向 | 历史链接有映射且无主导航入口。 |
| `/workflows*` | 工程 Workflow | 兼容、退役 | 对应业务页面 | Stage 11 | 是 | Workflow API 无普通页面调用。 |
| `/profiles/*` | 运行配置 | 迁移 | 系统管理 → Profile 配置 | Stage 11 | 否，可重定向 | 普通业务页自动选择有效配置。 |
| `/alerts` | 告警中心 | 迁移 | 首页待办 + 系统管理失败与告警 | Stage 11 | 是独立主入口 | 告警可从影响业务直接修复。 |
| `/system/*` | 运维管理 | 保留、改造 | 系统管理 | 长期 | 否 | 文案和权限符合产品约束。 |
| `/admin*`、`/settings`、`/system/restore` | 旧重定向 | 兼容、退役 | `/system*` | Stage 12 | 是 | 外部链接观察期结束。 |

### 3.1 实际注册路由逐项映射

下表按 `web/src/app/router.tsx` 的实际注册项逐项记录，不使用通配符代替验收。

| 旧路由 | 新入口 | 数据迁移方式 | 允许保留到 | 最终处理 |
| --- | --- | --- | --- | --- |
| `/login` | 登录 | 用户和 Session 表原地保留 | 长期 | 保留 |
| `/` | 首页 | 无数据迁移，改默认重定向 | Stage 1 | 改为首页 |
| `/dashboard` | 首页 | Dashboard 查询改读今日业务状态 | Stage 1 | 兼容重定向 |
| `/jobs` | 系统管理 → 任务运行 | Job 数据原地保留 | Stage 12 | 删除普通入口 |
| `/jobs/:jobId` | 运行详情 | Job、timeline、artifact 引用原地保留 | 长期 | 保留深链 |
| `/profiles` | 系统管理 → Profile 配置 | ConfigProfile 原地保留 | Stage 11 | 兼容重定向 |
| `/profiles/import` | 系统管理 → 导入配置 | 导入记录关联 ConfigProfile | Stage 11 | 兼容重定向 |
| `/profiles/:profileId` | 系统管理 → 配置详情 | Profile ID 原地保留 | Stage 11 | 兼容重定向 |
| `/profiles/:profileId/edit` | 系统管理 → 配置编辑 | Profile ID 原地保留 | Stage 11 | 兼容重定向 |
| `/profiles/:profileId/snapshots/:snapshotId` | 系统管理 → 配置版本 | Snapshot ID 原地保留 | Stage 11 | 兼容重定向 |
| `/workflows` | 对应业务页面 | WorkflowRun 原地保留，定义转 Runtime Contract | Stage 11 | 删除 |
| `/workflows/pre-market` | 每日交易 → 今日盘前 | 历史 WorkflowRun 关联 TradingDayPlan | Stage 9 | 重定向后删除 |
| `/workflows/pre-market/run` | 每日交易 → 今日盘前 | 同上 | Stage 9 | 重定向后删除 |
| `/workflows/after-close` | 每日交易 → 今日盘后 | 历史 WorkflowRun 关联 PostMarketReview | Stage 10 | 重定向后删除 |
| `/workflows/after-close/run` | 每日交易 → 今日盘后 | 同上 | Stage 10 | 重定向后删除 |
| `/workflows/:workflowId/run` | 对应业务动作 | Workflow ID 建立业务动作映射 | Stage 11 | 删除 |
| `/articles` | 研究中心 | Article ID 原地保留 | Stage 1 | 兼容重定向 |
| `/articles/run` | 研究中心 → 添加文章/批量处理 | Job/PromptRun 关联 Article | Stage 3 | 删除 |
| `/articles/list` | 研究中心 → 文章库 | BlogArticle/RawArticle 合并映射 | Stage 3 | 兼容重定向 |
| `/articles/quality` | 研究中心质量摘要 | 质量统计改由 Article/PromptRun 聚合 | Stage 3 | 删除独立页 |
| `/articles/results` | 文章详情 → 提取结果 | ArticleMetadata 转 ArticleStructure/RuleCandidate | Stage 4 | 删除 |
| `/alerts` | 首页待办/系统管理告警 | AlertHistory 原地保留并增加业务引用 | Stage 11 | 删除独立主入口 |
| `/backtest` | 规则与回测 → 回测实验 | BacktestResultRun 转 BacktestRun | Stage 6 | 兼容重定向 |
| `/backtest/regime` | 回测详情 → 分市场状态 | regime metrics 原地迁移到结果明细 | Stage 6 | 删除独立页 |
| `/backtest/candidates` | 策略中心 → 草稿与建议 | candidate StrategyVersion 转 Proposal/草稿 | Stage 8 | 删除 |
| `/rule-pool` | 规则与回测 → 规则列表 | RulePool 转 RuleCandidate/RuleVersion | Stage 4 | 兼容重定向 |
| `/rule-pool/:ruleId` | 规则与回测 → 规则详情 | 旧 rule_id 建映射表 | Stage 4 | 兼容重定向 |
| `/artifacts` | 业务结果附件/运行详情 | Artifact 增加业务对象引用 | Stage 12 | 删除 |
| `/artifacts/:artifactId` | 业务结果附件 | Artifact ID 原地保留并建立反向链接 | Stage 12 | 保留深链重定向 |
| `/market` | 系统管理 → 数据与调度 | 市场数据原地保留 | Stage 5 | 删除旧聚合页 |
| `/market/snapshots` | 市场快照高级详情 | MarketSnapshot 原地保留 | Stage 11 | 业务深链或管理员入口 |
| `/market/datasets` | 回测数据版本/高级详情 | MarketDataset 迁移为 DatasetSnapshot 引用 | Stage 11 | 业务深链或管理员入口 |
| `/market/kaipan` | 系统管理 → 市场数据 | Kaipan 文件和表关联 MarketSnapshot | Stage 5 | 删除 |
| `/market/ohlcv` | 系统管理 → 历史行情 | OHLCVBar 原地保留并补 DatasetSnapshot | Stage 5 | 删除 |
| `/strategies` | 策略中心 | TraderStrategyVersion 迁移为 StrategyVersion | Stage 8 | 改为正式入口 |
| `/persona` | 作者画像 | Persona/TraderProfile/Memory 分类迁移 | Stage 7 | 删除 |
| `/strategies/pre-market` | 每日交易 → 今日盘前 | selection/Job 迁移为每日三对象 | Stage 9 | 兼容重定向 |
| `/strategies/after-close` | 每日交易 → 今日盘后 | 报告/Memory 迁移为 Review/Proposal | Stage 10 | 兼容重定向 |
| `/system` | 系统管理 | 系统数据原地保留 | 长期 | 保留 |
| `/system/audit` | 系统管理 → 权限与审计 | Audit 表原地保留 | 长期 | 保留 |
| `/system/users` | 系统管理 → 用户管理 | User/Session 原地保留 | 长期 | 保留 |
| `/system/health` | 系统管理 → 系统健康 | 无业务数据迁移 | 长期 | 保留 |
| `/system/db-migrate` | 系统管理高级操作 | 迁移日志关联审计记录 | 长期 | 保留管理员入口 |
| `/system/backup` | 系统管理 → 备份恢复 | 备份索引关联审计记录 | 长期 | 保留管理员入口 |
| `/admin` | `/system` | 无数据迁移 | Stage 12 | 删除重定向 |
| `/admin/audit` | `/system/audit` | 无数据迁移 | Stage 12 | 删除重定向 |
| `/system/restore` | `/system/backup` | 无数据迁移 | Stage 12 | 删除重定向 |
| `/settings` | 系统管理 → Profile 配置 | ConfigProfile 原地保留 | Stage 12 | 删除重定向 |
| `*` | 统一中文 404 | 无数据迁移 | Stage 1 | 保留通配能力并替换用户文案 |

### 3.2 前端逐项退役条件

上表每个入口按最终处理绑定以下门禁；没有满足对应门禁时不得删除或取消兼容：

| 入口范围 | 退役条件 |
| --- | --- |
| `/dashboard`、`/articles*` | 新首页/研究中心已接入真实 API；原路由重定向测试通过；导航、route registry 和外部链接无旧主入口。 |
| `/jobs`、`/jobs/:jobId`、`/artifacts*`、`/workflows*` | 每个业务动作均可在业务页创建、查看、恢复运行；历史 Job、Artifact、WorkflowRun 深链可解析；普通用户不再提交内部类型。 |
| `/profiles*`、`/settings` | 配置统一进入系统管理；现有 profile_id 和 snapshot_id 可解析；业务页可自动选择有效配置。 |
| `/rule-pool*`、`/backtest*` | RuleVersion、DatasetSnapshot、BacktestRun 和 ID 映射完成；历史结果可读；回测复现和迁移对账通过。 |
| `/market*` | 数据检查、修复、调度和 DatasetSnapshot 新入口可用；Kaipan/OHLCV 技术动作不再由普通用户直接调用。 |
| `/persona` | 三层作者画像已落库、审核和版本化；Persona/TraderProfile/Memory 迁移报告通过。 |
| `/strategies`、`/strategies/pre-market`、`/strategies/after-close` | 稳定 StrategyVersion、每日三对象、PostMarketReview 和三类 Proposal 分离完成；历史策略/报告有映射。 |
| `/alerts` | 告警已嵌入首页和受影响业务页，并能直接定位修复动作。 |
| `/admin*`、`/system/restore` | 新系统入口已稳定，旧深链观察期结束，访问日志无有效调用。 |
| `*` | 中文 404 覆盖未知路径，保留通配路由，不执行退役。 |

## 4. API 迁移矩阵

| 旧 API | 处置 | 目标 API/Service | 保留到 | 退役条件 |
| --- | --- | --- | --- | --- |
| `/api/ui/system/status` | 退役 | `/api/ui/v1/system/status` | Stage 1 | 前端和脚本无引用。 |
| `/api/ui/v1/jobs/*` | 保留、改造 | Runtime Application Service | 长期 | 不作为普通业务的直接参数 API。 |
| `/api/ui/v1/workflows/*` | 兼容、合并 | 业务 Application Service | Stage 11 | 业务动作不再直接调用 workflow_id。 |
| `/api/ui/v1/pipelines/*` | 兼容、合并 | 研究中心批处理 Service | Stage 3 | 文章页不再暴露 Pipeline/Step。 |
| `/api/ui/v1/artifacts/*` | 保留查询、退役独立入口 | 业务结果附件 API | Stage 12 | 所有产物可由业务对象查询。 |
| `/snapshots/*` | 合并 | `/api/ui/v1/market/snapshots/*` 或 DatasetSnapshot API | Stage 5 | 调用方全部迁移。 |
| `/strategy_versions/*` | 兼容、迁移 | StrategyVersion API | Stage 8 | 新策略模型完成历史读取。 |
| `/api/ui/v1/optimize/versions/*` | 合并 | Strategy Center API | Stage 8 | StrategyStudio 重复 API 删除。 |
| `/api/ui/v1/strategy-studio/*` | 退役 | Rule/Strategy/Proposal 独立 API | Stage 8 | 前端不再调用聚合重复端点。 |
| `/api/ui/v1/rule-pool/*` | 改造 | RuleCandidate/RuleVersion API | Stage 4 | 新规则 ID 和审核状态迁移完成。 |
| `/backtest_results/*` | 改造 | BacktestRun API | Stage 6 | 不再 fallback Job/文件。 |
| `/api/ui/v1/kaipan/*` | 合并 | 数据与调度业务动作 | Stage 5 | 用户动作不暴露 fetch/normalize。 |
| `/api/ui/v1/market/ohlcv/run|stop|status` | 合并 | 历史行情更新业务动作 | Stage 5 | 与通用 Job 使用同一应用服务。 |
| `/reports/*` | 兼容、迁移 | TradingDayPlan/PostMarketReview 查询 | Stage 10 | 报告不再是唯一正式结果。 |
| `/api/ui/v1/persona/*` | 退役、迁移 | AuthorProfile API | Stage 7 | 新画像三层对象上线。 |

### 4.1 注册 API 家族全量处置

下表覆盖 `api/app.py` 实际注册的所有 endpoint 模块；具体 163 条 method/path 以 FastAPI `app.routes` 为代码清单，不以历史文档为准。

| 注册 API 家族 | 处置 | 目标入口 | 保留到 | 退役条件 |
| --- | --- | --- | --- | --- |
| 根、OpenAPI、`/health*` | 保留、改造 | 系统健康与 API 基础设施 | 长期 | 不退役；用户错误文案需产品化。 |
| `/articles*` | 兼容、迁移 | Research/Article API | Stage 3 | Web 和脚本迁移，Article 合并映射完成。 |
| `/trades*` | 保留、改造 | 交易记录/盘后证据 API | Stage 10 | 新证据对象使用统一查询。 |
| `/market*` | 保留、改造 | MarketData/DatasetSnapshot API | Stage 5 | 时间语义和数据版本契约上线。 |
| `/reports*` | 兼容、迁移 | TradingDayPlan/PostMarketReview API | Stage 10 | 文件报告仅作导出。 |
| `/snapshots*`、`/api/ui/v1/snapshots*` | 合并 | MarketSnapshot/DatasetSnapshot API | Stage 5 | 两套查询调用方归一。 |
| `/strategy_versions*` | 兼容、迁移 | StrategyVersion API | Stage 8 | 历史版本映射、发布和回滚完成。 |
| `/backtest_results*` | 迁移 | BacktestRun API | Stage 6 | Job/文件 fallback 退役。 |
| `/rankings*` | 改造、迁移 | 盘后评估/作者验证结果 | Stage 10 | 排名业务归属和来源版本明确。 |
| `/alerts*` | 保留、改造 | 首页待办/系统告警 API | Stage 11 | 告警具备业务对象引用和修复动作。 |
| UI `auth` | 保留 | 认证与用户管理 | 长期 | 不退役。 |
| UI `system`、`ops`、`profiles`、`security` | 保留、改造 | 系统管理 API | 长期 | legacy system status 按原表退役。 |
| UI `data-audits`、`job-audits`、`data-health` | 保留、改造 | 系统管理审计与健康 | 长期 | 不作为普通主流程入口。 |
| UI `imports` | 迁移、合并 | 研究中心导入/系统数据迁移 | Stage 3/11 | 导入动作按业务域拆分，旧聚合端点无调用。 |
| UI `jobs` | 保留、改造 | Runtime Application Service | 长期 | 普通业务不直接提交 job_type。 |
| UI `workflows`、`pipelines` | 兼容、合并 | 业务 Application Service | Stage 11 | workflow_id/pipeline_id 不再暴露给普通用户。 |
| UI `artifacts` | 保留查询、退役独立入口 | 业务附件 API | Stage 12 | 所有 Artifact 有业务归属。 |
| UI `article-metadata` | 迁移 | ArticleStructure/PromptRun/Review API | Stage 4 | 新 Schema 与选择记录迁移完成。 |
| UI `market`、`kaipan` | 合并、改造 | 数据与调度业务动作 | Stage 5 | fetch/normalize/OHLCV 技术端点无普通调用。 |
| UI `rule-pool` | 迁移 | RuleCandidate/RuleVersion API | Stage 4 | 规则 ID、证据和审核状态对账完成。 |
| UI `optimize`、`strategy-studio` | 合并、退役重复 | Strategy/Proposal API | Stage 8/10 | 重复版本、规则池和优化端点无调用。 |
| UI `persona` | 迁移、退役 | AuthorProfile API | Stage 7 | 三层画像上线。 |
| UI `signals` | 改造、迁移 | DailyStrategyInstance/TradingDayPlan 明细 | Stage 9 | Signal 不再冒充正式计划。 |
| UI `traders` | 迁移 | Author/Strategy 主体查询 | Stage 7/8 | trader 与 author 身份映射明确。 |

### 4.2 未注册历史 Router

`api/routers/alignment.py`、`backtest.py`、`blog.py`、`health.py`、`market.py`、`run.py`、`signal.py`、`strategy.py`、`trade.py`、`api/routes/reports.py` 和 `api/routers/ui/settings.py` 当前未注册。

处置：全部标记为**兼容候选、禁止新增调用**。目标入口按 4.1 对应业务家族合并；只有代码引用、测试引用和部署入口均为零，且有用逻辑已迁移后才能删除。`api/dependencies.py` 与 `api/deps.py` 在 Stage 11 合并为单一依赖入口。

## 5. Schema 与事实源迁移

| 当前 Schema/事实源 | 处置 | 目标 | 数据迁移方式 | 验证 |
| --- | --- | --- | --- | --- |
| ArticleMetadata JSON | 迁移 | ArticleStructure + PromptRun + RuleCandidate | 按 article_id/schema_version 转换；无法映射字段标质量状态 | 固定文章样本回归。 |
| ArticleMetadataSelection | 保留、改造 | 结构化结果选择/批准记录 | 关联新 PromptRun 和审核记录 | 每篇文章最多一个当前选择。 |
| RulePool | 迁移 | RuleCandidate/RuleVersion/RuleFamily | 保留 rule_id 映射表；JSON 条件转 canonical Schema | 条数、来源、审核状态对账。 |
| RulePool.backtest_result | 退役 | BacktestRun/RuleApplicabilityProfile | 迁移可识别摘要，原 JSON 归档 | 迁移前后指标抽样比较。 |
| BacktestResultRun | 改造 | BacktestRun | 增加 DatasetSnapshot、RuleVersion、基准和代码版本引用 | 同输入 fingerprint 一致。 |
| Persona MarketState | 兼容 | MarketState | 建立旧枚举到 canonical label 映射 | 历史日期抽样比对。 |
| MarketRegimeFeature/Record | 保留、改造 | MarketState 模型与记录 | 保留表，补 canonical API 字段和时间语义 | 无未来数据泄漏检查。 |
| TraderProfile 文件 | 迁移、退役 | AuthorMethodProfile/AuthorRuleProfile | 按作者和证据来源导入草稿，推断字段不得直接发布 | 人工审核迁移报告。 |
| TraderMemory | 拆分、迁移 | 作者证据、盘后证据、执行记录 | 按 memory_type 分类；不确定项标 unresolved | 总数和引用完整性对账。 |
| TraderStrategyVersion | 迁移 | StrategyVersion | 将稳定规则池/风险配置迁移为草稿；日级 recommendation 迁移为历史实例 | 发布状态、父版本和日期对账。 |
| StrategyRegimeSelection | 迁移 | DailyRuleSelection | 保留 selection_id，关联正式策略和 MarketState | 每日选择明细对账。 |
| Job result/Artifact | 兼容 | 正式业务对象 + 附件 | 先建立业务对象引用，再降为附件 | 无孤立产物。 |

## 6. Prompt 迁移矩阵

| 当前 Prompt | 处置 | 新 Prompt | 保留到 | 退役条件 |
| --- | --- | --- | --- | --- |
| `concept_extraction.md` | 兼容、退役 | `article_analysis_v1` / `concept_extraction_v1` | Stage 3 | 新调用链、回归、历史读取和回滚通过。 |
| `rule_extraction.md` | 兼容、退役 | `article_analysis_v1` / `rule_extraction_v1` | Stage 3 | 同上。 |
| `precondition_extraction.md` | 兼容、退役 | `explicit_precondition_extraction_v1` | Stage 3 | `not_declared` 和证据规则通过回归。 |
| `llm_attribution.md` | 兼容、退役 | `llm_attribution_v1` | Stage 10 | 条件触发、Schema 校验和历史结果兼容完成。 |
| `llm_postmortem_notes.md` | 兼容、退役 | `llm_postmortem_notes_v1` | Stage 10 | 新盘后对象和用户说明链路完成。 |
| `src/article_classifier/prompts.py::CLASSIFICATION_PROMPT` | 迁移、退役硬编码 | 版本化 article classification Prompt | Stage 3 | 文件/Registry 接入、Schema 校验、固定样本回归和历史版本记录完成。 |
| 作者画像 v1 Prompt | 保留、接入 | 同名 v1 | Stage 7 | 接入三层画像草稿流程。 |
| `strategy_revision_proposal_v1` | 保留、接入 | 同名 v1 | Stage 10 | 只生成 Proposal，不改正式策略。 |

旧 Prompt 状态必须按：

```text
active
→ deprecated
→ compatibility_only
→ unused
→ deleted
```

## 7. 执行定义合并方案

| 当前定义 | 目标职责 | 处置 |
| --- | --- | --- |
| JobDefinition | 原子运行能力、权限、风险、重试和并发 | 保留为底座或由 Runtime Contract 生成。 |
| WorkflowDefinition | 用户业务动作的步骤视图 | 改为由应用服务契约派生，不单独维护参数。 |
| PipelineSpec | 后台可恢复编排 | 保留步骤依赖，删除重复权限/参数事实。 |
| Runtime Bridge | 统一读取接口 | 升级为唯一注册入口，禁止多处独立注册。 |
| 前端硬编码 job_type | 无 | 删除，改调业务动作 API。 |

### 7.1 JobDefinition 全量迁移

| Job 类型 | 处置 | 目标业务动作 | 退役条件 |
| --- | --- | --- | --- |
| `db-migrate`、`backup-data`、`restore-data` | 保留、改造 | 系统管理高风险操作 | 仅管理员可见，审计、确认、恢复测试通过。 |
| `init-project`、`seed-data`、`migrate-crawl-state`、`import-trade-logs` | 兼容、迁移 | 安装/数据迁移工具 | 初始化或迁移窗口结束，生产无调用后退役。 |
| `crawl`、`clean`、`validate`、`store`、`process` | 合并 | 研究中心文章导入与结构化处理 | 新业务动作自动编排，用户不再选 step。 |
| `pipeline-run`、`pipeline-step` | 兼容、合并 | Runtime Application Service | 所有 Pipeline 使用统一运行契约且无外部直接提交。 |
| `clusters-build`、`persona-init-sample` | 迁移、退役 | AuthorMethodProfile 构建/开发样本工具 | 作者画像正式链路上线，样本入口不在生产注册。 |
| `e2e-regression` | 迁移、退役生产 Job | CI/E2E 测试命令 | CI 接管且生产 API 不再暴露。 |
| `run-pre-market` | 迁移 | 生成 DailyRuleSelection、DailyStrategyInstance、TradingDayPlan | Stage 9 对象落库、批准和追溯通过。 |
| `run-after-close` | 迁移 | 生成 PostMarketReview 和三类 Proposal | Stage 10 对象落库、审核和追溯通过。 |
| `market-state-build` | 保留、改造 | 构建版本化市场状态 | 模型版本、时间语义和 DatasetSnapshot 关联完成。 |
| `snapshot-build` | 保留、改造 | 整理市场数据/固定数据版本 | DatasetSnapshot 成为正式引用。 |
| `strategy-build` | 迁移、改造 | 创建 StrategyVersion 草稿 | 不再按日生成正式策略，发布/回滚契约完成。 |
| `ohlcv-crawl` | 保留、改造 | 更新历史行情/补齐缺口 | 统一数据任务和调度入口上线。 |
| `backtest-run`、`backtest-validate-rules`、`backtest-reproducibility-check` | 保留、改造 | 开始回测/规则验真/复现验证 | BacktestRun 强制版本引用且无实时 Provider。 |
| `rule-pool-backtest` | 迁移、合并 | RuleVersion/RuleFamily 回测 | RulePool 不再是正式规则事实源。 |
| `optimize-create-candidate`、`candidate-review` | 迁移 | StrategyRevisionProposal 审核 | Proposal 与正式策略分离，旧 candidate 无写入。 |
| `rule-review` | 迁移 | RuleCandidate/RuleVersion 审核 | 新审核状态和证据契约上线。 |
| `kaipan-fetch`、`kaipan-normalize`、`kaipan-run` | 合并、改造 | 整理盘前/盘后市场数据 | 普通用户不见技术步骤，统一调度和数据版本可追溯。 |

### 7.2 Workflow、Pipeline 和调度全量迁移

| 当前入口 | 处置 | 目标 | 退役条件 |
| --- | --- | --- | --- |
| Workflow `ohlcv` | 合并 | 历史行情更新业务动作 | 页面/API 不再提交 workflow_id。 |
| Workflow `scheduler` | 合并、退役 | 系统管理 → 数据与调度 | Kaipan、OHLCV、市场状态、快照由统一调度计划管理。 |
| Pipeline `article_pipeline` | 保留、改造 | 研究中心后台编排 | 参数和权限只来自统一 Runtime Contract。 |
| Pipeline `backtest` | 保留、改造 | 回测后台编排 | 强制 DatasetSnapshot 和版本引用。 |
| Pipeline `optimize-rule-pool` | 迁移、合并 | Rule/Strategy Proposal 编排 | RulePool 与 candidate legacy 写入停止。 |
| Pipeline `strategy` | 迁移、改造 | 稳定策略与每日实例分离编排 | 不再混合正式策略和每日结果。 |
| Pipeline `market_data`（未注册） | 合并或退役 | 统一市场数据编排 | Stage 5 决定接入唯一 Registry 或删除；不得继续孤立维护。 |
| CLI `scheduler-start` | 兼容、退役 | 持久化统一调度服务 | 新服务接管盘前/盘后且 CLI 无生产守护进程。 |
| PipelineScheduler | 合并 | 统一调度服务 | 任务计划和运行状态已持久化。 |
| ArticlePipelineScheduleService | 合并 | 研究中心计划任务 | 统一调度可表达文章计划并完成幂等验证。 |
| RuleBacktestScheduler | 合并 | 回测计划任务 | 统一调度可表达规则回测计划。 |
| MarketService OHLCV scheduler | 合并 | 数据与调度 | 单一调度实例接管 OHLCV。 |
| KaipanService/provider scheduler | 合并 | 数据与调度 | 单一调度实例接管 Kaipan，旧进程入口无调用。 |

## 8. 退役门禁

任何旧入口只有同时满足以下条件才能删除：

1. 新入口已从主导航可达。
2. 新入口使用真实数据完成同等业务能力。
3. 历史 ID、深链和数据有映射或明确归档。
4. 前端、API、Job、Workflow、脚本和文档无生产引用。
5. 迁移可安全重跑，失败有恢复方案。
6. 受影响测试和 E2E 通过。
7. 观察期没有阻塞问题。
8. 实施记录已更新。

## 9. Stage 进入条件

本矩阵只定义迁移责任，不授权提前实现后续 Stage。

- Stage 0 的任务级出口已满足：未改核心行为、代码清单已审计、重复入口和事实源已列出、每类旧入口均有目标和退役门禁、实施记录已更新。
- Stage 1 只能开始信息架构、导航和页面框架，不得顺带重建 Stage 2-10 领域对象。
- Stage 2 必须先确定 ID、版本、审核和迁移契约。
- Stage 3 之前旧 Prompt 仍可兼容，但不得把 v1 文件存在视为已接入。
- Stage 8 前不得把现有按日 StrategyVersion 直接认定为正式策略。
- Stage 9/10 前不得用 Job/Artifact 冒充每日计划或盘后正式对象。

## 10. 迁移矩阵验收

- [x] 每类现有能力已标记保留、改造、合并、迁移、兼容或退役。
- [x] 49 条当前前端路由记录均已给出新入口、保留 Stage 和逐类退役条件。
- [x] 已覆盖 163 条注册 API 所属家族及未注册历史 Router。
- [x] 已覆盖 40 张 ORM 表、迁移遗留表、Schema、数据和 Prompt 事实源。
- [x] 已覆盖 33 个 Job、2 个 Workflow、4 个已注册 Pipeline、1 个孤立 Pipeline 和六类调度实现。
- [x] 已定义统一退役门禁。
- [x] 未开始 Stage 1。

结论：`RT-S0-001` 和 `RT-S0-002` 满足 Stage 0 任务级验收，可以进入 Stage 1，但本轮不执行 Stage 1。
