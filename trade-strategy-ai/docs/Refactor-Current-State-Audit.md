# Trade Strategy AI 重构现状审计

## 1. 审计信息

- Task ID：`RT-S0-001`
- 审计日期：`2026-06-10`
- 审计边界：只分析现有实现，不修改核心业务代码。
- 事实优先级：以当前代码注册关系、ORM 声明、迁移、Prompt 加载和前端调用为准。`docs/bak` 不作为结论依据；其中任何线索都必须回到代码重新确认。

本次实际核对：

- 前端导航、Sidebar、路由、页面和 API Client。
- FastAPI 应用实际注册的 API。
- Service、Job、Workflow、Pipeline、Worker 映射。
- ORM 模型、Alembic 迁移和文件型存储。
- Prompt 文件、生产加载点和测试引用。
- OHLCV、Kaipan、市场状态、规则、回测、画像、策略、盘前和盘后链路。

## 2. 总体结论

当前项目不是空壳，已经具备文章处理、规则池、任务运行、市场数据、市场状态、回测、规则适用性、策略版本、盘前和盘后等基础能力。但实现仍以工程任务和历史阶段对象组织，尚未形成 TaskList 要求的单一用户闭环。

关键结论：

1. 前端实际有 49 条路由记录：1 条登录、1 条根重定向、46 条 Dashboard 子路由和 1 条通配 404；`route-registry.ts` 只登记 37 条，形成第二套路由事实源。主导航仍直接展示“任务中心”和“产物中心”，Sidebar 品牌文案仍是 `Web control console`。
2. FastAPI 当前注册 163 个路由，存在业务 API、UI BFF、legacy API 和重复聚合 API 并存。
3. 执行层当前有 33 个 JobDefinition、2 个 WorkflowDefinition、4 个已注册 PipelineSpec，另有 1 个未注册 PipelineSpec。Job、Workflow、Pipeline 都在描述相近能力，Runtime Bridge 只是汇总，不是唯一写入源。
4. 源码实际声明 40 张 SQLAlchemy ORM 表：`src/models` 36 张、`src/rule_pool/models.py` 3 张、`src/alerting/db.py` 1 张。Alembic 为单一 head `2026_06_03_0001`，但迁移环境没有导入全部 ORM，且仍有无 ORM 的历史表。
5. 当前有 19 个 Prompt 文件，另有 `src/article_classifier/prompts.py` 的硬编码分类 Prompt。正式文章提取和盘后服务仍加载旧 Prompt；新 Prompt 目前不是生产事实源。
6. OHLCV、Kaipan、市场快照、市场状态和规则适用性已有可复用实现，但 DatasetSnapshot、数据时间语义和统一缺失数据契约不完整。
7. 策略版本当前按 `trader_id + strategy_date` 建模并支持每日构建，与“正式策略稳定、每日只生成运行实例”的目标冲突。
8. 当前“画像”混合了 Persona、TraderProfile、TraderMemory 和文件型 profile，尚无 AuthorMethodProfile、AuthorRuleProfile、AuthorValidatedProfile。

## 3. 前端现状

### 3.1 主导航与 Sidebar

当前主导航：

| 分组 | 当前入口 | 结论 |
| --- | --- | --- |
| 正式入口 | 概览、任务中心 | “任务中心”不应继续作为普通用户正式入口。 |
| 主流程 | 文章与规则、市场上下文、回测与画像、盘前分析、盘后复盘 | 已有业务方向，但信息架构与目标导航不一致。 |
| 辅助入口 | 产物中心、配置与管理、系统管理 | 产物和 Profile 仍暴露为产品入口。 |

Sidebar 仍展示：

- 产品名 `trade-strategy-ai`。
- 英文说明 `Web control console`。
- Job、Artifact、Profile 等工程化入口。

### 3.2 当前路由和页面

| 当前路由 | 当前页面职责 | 实际状态 |
| --- | --- | --- |
| `/dashboard` | 系统状态、最近任务、最近产物、告警 | 工程控制台首页，不是“今天下一步”首页。 |
| `/jobs`、`/jobs/:jobId` | Job 列表、日志、时间线、产物和控制 | 能力完整，可下沉为运行详情和管理员入口。 |
| `/articles` | 四个文章子入口目录 | 可复用外壳，但仍按 Pipeline/Step/Job 操作。 |
| `/articles/run` | 文章 Pipeline 与调度 | 用户直接选择 step、force、pipeline-run。 |
| `/articles/list` | 文章列表 | 可复用。 |
| `/articles/quality` | 文章质量汇总 | 可复用。 |
| `/articles/results` | 多版本 ArticleMetadata 查看和选择 | 可迁移为文章详情与提取结果审核。 |
| `/market` | 抓取、快照、数据集和基础信息流程 | 仍要求用户理解数据任务和 Artifact。 |
| `/market/kaipan` | Kaipan 运行工作台 | 暴露抓取、归一化和调度术语。 |
| `/market/ohlcv` | OHLCV 运行工作台 | 可迁移到系统管理的数据与调度。 |
| `/market/snapshots` | 市场快照浏览 | 可保留为高级详情。 |
| `/market/datasets` | 市场数据集浏览 | 可保留为高级详情。 |
| `/backtest` | 回测、规则验真、复现检查、结果浏览 | 可复用核心能力，入口仍围绕 Job 参数。 |
| `/backtest/regime` | 分市场状态回测报告 | 可合并到回测详情。 |
| `/backtest/candidates` | 策略候选版本列表 | 命名和业务域错误，应迁移到策略中心。 |
| `/rule-pool` | 规则列表、审核、适用性画像 | 可作为规则与回测工作台基础。 |
| `/persona` | Persona 行为规则查看 | 不是 TaskList 定义的作者画像。 |
| `/strategies/pre-market` | 提交 snapshot-build 和 run-pre-market Job | 尚无 DailyRuleSelection、DailyStrategyInstance、TradingDayPlan。 |
| `/strategies/after-close` | 提交 run-after-close Job 并查看报告/产物 | 尚无正式 PostMarketReview 和三类 Proposal。 |
| `/artifacts`、`/artifacts/:artifactId` | 独立产物中心 | 应改为业务结果内嵌详情并最终退役独立入口。 |
| `/profiles/*` | Profile 配置、导入、快照 | 应迁移到系统管理，不能代表作者画像。 |
| `/workflows*` | 兼容工作流目录和运行页 | 已标 compat，但仍可直接执行工程 Workflow。 |
| `/system/*` | 用户、审计、健康、迁移、备份 | 可保留并扩展为系统管理。 |

未注册但仍存在的前端实现：

- `features/backtests/backtests-center.tsx`
- `features/strategy-studio/strategy-studio.tsx`
- `features/reports/report-center.tsx`
- `features/signals/signals-center.tsx`
- `features/imports/import-center.tsx`
- `pages/admin/*`

这些文件构成未退役 legacy 或孤立实现，不能视为正式入口。

### 3.3 前端重复事实源

1. `navigation.ts`、`router.tsx`、`route-registry.ts` 分别维护导航、实际路由和路由说明。
2. 市场能力同时存在 MarketPage、MarketWorkspace、Kaipan 页面、OHLCV 页面、快照浏览和数据集浏览。
3. 回测同时存在 `features/backtest` 和 `features/backtests`。
4. 策略同时存在 StrategyWorkspace、StrategyStudio、StrategyRegimeSelection 和候选版本页。
5. 运行结果同时通过业务页面、Job 详情和 Artifact 中心展示。

## 4. API 与执行层现状

### 4.1 API

当前 API 分为四组：

| API 组 | 示例 | 结论 |
| --- | --- | --- |
| 业务查询 API | `/articles`、`/market/latest`、`/trades`、`/reports/*` | 部分仍直接读取文件或旧模型。 |
| UI BFF | `/api/ui/v1/*` | 当前 Web 的主要 API，可作为迁移承载层。 |
| legacy UI API | `/api/ui/system/status` | 已有明确 legacy 前缀，待退役。 |
| 重复聚合 API | `/api/ui/v1/optimize/*` 与 `/api/ui/v1/strategy-studio/optimize/*` | 同一 Service 被两套入口暴露。 |

明确重复：

- `/snapshots/*` 与 `/api/ui/v1/snapshots/*`。
- `/strategy_versions/*`、`/api/ui/v1/optimize/versions/*`、`/api/ui/v1/strategy-studio/versions/*`。
- `/api/ui/v1/rule-pool/*` 与 `/api/ui/v1/strategy-studio/rule-pool/*`。
- `/api/ui/v1/kaipan/*` 与通用 `/api/ui/v1/jobs` 的 Kaipan Job。
- `/api/ui/v1/market/ohlcv/run|stop|status` 与通用 OHLCV Job。
- `/reports/*` 的结果文件读取与 Job/Artifact 结果读取。

### 4.2 Job、Workflow、Pipeline

当前注册：

- 33 个 JobDefinition，其中 24 个 runnable，9 个只注册未开放运行。
- 2 个 WorkflowDefinition：`ohlcv`、`scheduler`。
- Runtime Bridge 注册 4 个 PipelineSpec：`article_pipeline`、`backtest`、`optimize-rule-pool`、`strategy`；另有未注册的 `market_data` PipelineSpec。

重复与不一致：

1. Job Registry 是参数、权限、风险和 handler 的主要事实源。
2. Workflow 从 Job 派生参数，但只注册 OHLCV 和 scheduler，不覆盖四个 PipelineSpec。
3. PipelineSpec 再次声明 workflow_id、job_types、步骤、权限和错误模式。
4. `market_data_pipeline_spec.py` 存在，但 Runtime Bridge 没有注册它。
5. Workflow 和 Pipeline 都能作为 UI 目录，业务页面又直接创建 Job。
6. `pipeline-run` 与独立 `crawl/clean/validate/store/process` 同时存在。

保留价值：

- JobService 的持久化、控制、审计、重试、时间线和产物绑定。
- JobDefinition 的参数 Schema、权限、风险和并发定义。
- WorkflowRun/WorkflowRunStep 的运行记录。
- PipelineSpec 的步骤依赖和业务聚合信息。

必须改造：

- 建立唯一运行契约，其他定义只能派生。
- Job/Workflow/Pipeline 退出普通用户导航，只作为业务动作底座。
- 业务页面不得继续让用户选择内部 job_type。

## 5. 数据库与存储现状

### 5.1 ORM 和迁移

当前源码声明 40 张 ORM 表，主要分组：

| 领域 | 当前表 |
| --- | --- |
| 文章 | `raw_articles`、`blog_articles`、`article_metadata`、`article_metadata_selections`、`article_classification` |
| 规则 | `rule_pool`、`trade_sample`、`rule_applicability_profiles` |
| 数据 | `ohlcv_bars`、`indicators`、`stock_info`、`market_snapshots`、`market_snapshot_sections`、`market_snapshot_items`、`market_datasets`、`market_data_quality_reports` |
| 市场状态 | `market_regime_features`、`market_regimes` |
| 策略与选择 | `trader_strategy_versions`、`strategy_regime_selections`、`regime_rule_selections` |
| 盘前盘后辅助 | `signals`、`trade_logs`、`evidence_packs`、`ranking_entries`、`alert_history`、`hot_topics_snapshots`、`strong_symbols_snapshots`、`topic_constituents_snapshots` |
| 运行与系统 | `jobs`、`job_audit_events`、`workflow_runs`、`workflow_run_steps`、`data_audit_events`、`config_profiles`、`users`、`user_sessions` |
| 画像与记忆 | `trader_memory` |

Alembic 当前只有一个 head：`2026_06_03_0001`。

40 张 ORM 表逐项清单：

```text
alert_history
article_classification
article_metadata
article_metadata_selections
backtest_result_runs
blog_articles
config_profiles
crawl_state
data_audit_events
evidence_packs
hot_topics_snapshots
indicators
job_audit_events
jobs
market_data_quality_reports
market_datasets
market_regime_features
market_regimes
market_snapshot_items
market_snapshot_sections
market_snapshots
ohlcv_bars
ranking_entries
raw_articles
regime_rule_selections
rule_applicability_profiles
rule_pool
signals
stock_info
strategy_regime_selections
strong_symbols_snapshots
topic_constituents_snapshots
trade_logs
trade_sample
trader_memory
trader_strategy_versions
user_sessions
users
workflow_run_steps
workflow_runs
```

模型装配存在额外风险：

- `src/db/migrations/env.py` 没有导入全部已声明 ORM，自动生成迁移时可能漏检。
- `rule_pool`、`trade_sample`、`article_classification` 定义在 `src/rule_pool/models.py`，不在 `src/models`。
- `alert_history` 定义在 `src/alerting/db.py`，不在 `src/models`。
- 迁移中仍有 `topic_mapping` 和旧 `market_data` 等没有当前 ORM 的历史表，必须在 Stage 2 连接实际数据库后确认是否仍存在、是否有数据和如何退役。

### 5.2 尚未实现的目标对象

以下对象在当前业务代码和 ORM 中没有正式实现：

- `ArticleStructure`
- `RuleCandidate`
- `RuleVersion`
- `RuleFamily`
- `DatasetSnapshot`
- `AuthorMethodProfile`
- `AuthorRuleProfile`
- `AuthorValidatedProfile`
- `StrategyVersion` 的稳定发布/回滚领域契约
- `DailyRuleSelection`
- `DailyStrategyInstance`
- `TradingDayPlan`
- `PostMarketReview`
- `RuleOptimizationProposal`
- `AuthorProfileRevisionProposal`
- `StrategyRevisionProposal`

### 5.3 文件型事实源

当前仍有正式流程依赖文件：

- TraderProfile 写入 `trader_profiles.json`。
- Persona cluster 写入 `data/processed/persona/*.json`。
- 部分日报、评估、persona route 和策略产物按文件读取。
- Backtest、市场状态、规则选择虽有数据库摘要，仍保留 `storage_ref`、`artifact_ref` 和文件 fallback。
- Job 同时维护数据库记录和 `data/jobs/<id>` 文件目录。

文件可以保留为导出、缓存和兼容层，但不能继续作为正式业务对象的唯一引用。

## 6. Prompt 与 LLM 现状

### 6.1 文件清单

当前共有 19 个 Prompt 文件：

- 14 个 v1 文件。
- 5 个明确旧版文件：`concept_extraction.md`、`rule_extraction.md`、`precondition_extraction.md`、`llm_attribution.md`、`llm_postmortem_notes.md`。
- 另有一个未文件化、未版本化的生产 Prompt：`src/article_classifier/prompts.py` 中的 `CLASSIFICATION_PROMPT`。

### 6.2 正式调用链

当前生产文章提取：

```text
concept_extraction.md
+ rule_extraction.md
+ precondition_extraction.md
→ 拼成一个 system prompt
→ LLM complete_json
```

当前生产盘后：

- `PostmortemService` 加载 `llm_attribution.md`。
- `PostmortemService` 加载 `llm_postmortem_notes.md`。

未发现新版 `article_analysis_v1`、作者画像 v1 Prompt 和策略修订 v1 Prompt 接入正式业务调用链。

### 6.3 Schema 风险

1. `ArticleMetadata.strategy_rules`、`preconditions` 和 `raw_llm_output` 使用开放 JSON。
2. 旧提取代码手写输出字段说明，未由单一 Pydantic/JSON Schema 生成。
3. Prompt 文件、Persona Schema、RulePool Schema、前端 TypeScript 类型并非同一事实源。
4. `ArticleMetadata.version` 实际映射数据库列 `schema_version`，同时还有 `extraction_version`，版本语义重叠。
5. 尚无统一 Prompt 调用记录表保存 prompt_version、schema_version、input_hash、token 和 cost。
6. 文章分类 Prompt 硬编码在 Python，形成 Prompt 文件之外的第二事实源。

## 7. 数据链路现状

### 7.1 OHLCV

已实现：

- `ohlcv_bars` 与 `indicators` 表。
- AkShare/Provider、抓取 Service、CLI 和 `ohlcv-crawl` Job。
- 前端状态、运行和停止入口。
- 回测引擎存在 snapshot-only 路径和相关检查，但本次代码审计不能证明所有调用分支都强制拒绝实时 Provider；该项必须在 Stage 6 通过调用链测试和 Provider mock 断言验证。

缺口：

- 没有正式 DatasetSnapshot 领域对象。
- 回测摘要没有强制 `dataset_snapshot_id`。
- 缺口检查、补抓、数据版本和回测数据冻结尚未统一成一个产品契约。
- OHLCV 运行入口在 Job、Workflow、市场页和 API 中重复。

### 7.2 Kaipan

已实现：

- Provider、Normalizer、Scheduler、Schema YAML。
- `kaipan-fetch`、`kaipan-normalize`、`kaipan-run` Job。
- 盘前/盘后 slot、市场快照和多个主题/强势股快照表。

缺口：

- 用户仍直接看到 Kaipan 技术名和内部步骤。
- 抓取、归一化、一键运行和 scheduler 控制混在同一能力域。
- 历史覆盖率、当时可用时间和回测可用性没有统一 DatasetSnapshot 契约。

### 7.3 市场状态

已实现：

- Persona 目录中的旧 MarketState 分类。
- `market_regime_features` 和 `market_regimes` 两层数据库模型。
- 市场状态构建 Service、查询 API 和前端展示。
- 分市场状态回测与规则选择。

重复事实源：

- `src/persona/market_state.py` 的旧分类。
- `MarketRegimeFeature`。
- `MarketRegimeRecord`。
- 多处 `market_state`、`market_regime`、`regime` 字段并存。

面向用户的部分页面已替换为“市场状态”，但代码、API 类型和旧页面仍大量使用 Regime。

## 8. 规则、回测、画像与策略现状

### 8.1 规则

已实现：

- ArticleMetadata 内嵌规则。
- `rule_pool` 独立规则表。
- 自动写入规则池。
- 人工审核、批量审核、DSL 映射、规则池回测。
- RuleApplicabilityProfile。

缺口：

- ArticleMetadata 内嵌规则和 RulePool 同时可被消费。
- 没有 RuleCandidate、RuleVersion、RuleFamily。
- RulePool 直接保存 `backtest_result`，同时又有 BacktestResultRun 和 RuleApplicabilityProfile。
- 生命周期状态与 TaskList 不一致。
- 自动审核结果没有统一的五级状态契约。

### 8.2 回测

已实现：

- `backtest-run`、规则验真、复现检查和规则池回测。
- snapshot-only 加载倾向。
- BacktestResultRun 数据库摘要。
- 分市场状态指标、fingerprint 和报告。

缺口：

- 没有强制 DatasetSnapshot 引用。
- 结果详情仍可从 Job/Artifact fallback。
- 回测入口按 trader/strategy version 组织，不是按 RuleVersion/RuleFamily。
- `insufficient_sample` 没有成为统一结果状态。
- BacktestResultRun、RulePool.backtest_result 和文件报告形成三套结果表达。

### 8.3 画像

当前至少存在四套概念：

- Persona cluster 和行为规则。
- TraderProfile 文件。
- TraderMemory 数据库。
- 前端 `/persona` 行为规则页。

它们都不是目标作者画像三层模型。现有 TraderProfile 还会根据文章规则推断风险风格、仓位倾向，并由策略构建器用于估算止损，这与“不编造作者真实仓位、风险纪律、止损”的约束冲突，必须重构。

### 8.4 策略

已实现：

- TraderStrategyVersion ORM。
- StrategyVersion dataclass、Repository、Service、Builder。
- manual/candidate、draft/released/archived。
- rules_snapshot、regime_selection 和 candidate review。

主要冲突：

- 唯一键包含 `strategy_date`，Builder 按日生成版本。
- StrategyBuilder 根据文章 sentiment 和画像偏好生成 buy/sell/hold。
- StrategyBuilder 根据风险风格估算止损。
- 当前策略对象混合正式策略、每日建议和标的 recommendation。
- 缺少稳定 StrategyVersion 与 DailyStrategyInstance 的分离。
- 没有完整发布、当前使用、回滚和差异审计契约。

## 9. 盘前与盘后现状

### 9.1 盘前

当前链路：

```text
用户选择 Profile、日期等参数
→ 可手动运行 snapshot-build
→ 手动提交 run-pre-market Job
→ 查看 Job 和 Artifact
```

已有市场状态规则选择摘要，但没有正式：

- DailyRuleSelection
- DailyStrategyInstance
- TradingDayPlan
- 用户批准状态
- 对全部输入版本的完整外键追溯

### 9.2 盘后

当前链路：

```text
用户提交 run-after-close Job
→ 程序计算 MFE/MAE/收益
→ 自动归因
→ 可选 LLM 校验/笔记
→ 报告、Job、Artifact、TraderMemory
```

缺口：

- 没有 PostMarketReview 正式对象。
- 没有分别建模三类优化 Proposal。
- 旧 LLM Prompt 仍在使用。
- 盘后结果仍偏报告和 Job 产物，不是可审核的结构化业务对象。

## 10. 重复入口、Schema 和事实源清单

| 类别 | 重复项 | 风险 |
| --- | --- | --- |
| 页面入口 | Jobs、Workflows、Artifacts 与各业务页面均可发起/查看同一运行 | 用户需要理解内部架构。 |
| 路由事实源 | navigation、router、route-registry | 路由和文案可漂移。 |
| 市场入口 | MarketPage、MarketWorkspace、Kaipan、OHLCV、Snapshots、Datasets | 同一数据能力分散。 |
| 回测入口 | backtest、backtests、regime report、candidate page | 页面职责重叠。 |
| 策略入口 | StrategyWorkspace、StrategyStudio、Optimize、StrategyVersion API | 策略事实源不唯一。 |
| 规则 Schema | ArticleMetadata.strategy_rules、Persona ArticleStrategyRule、RulePool ExtractionLayer、前端类型 | 无统一 RuleVersion Schema。 |
| 画像 Schema | Persona、TraderProfile、TraderMemory、profile 文件 | 与作者画像目标不一致。 |
| 市场状态 Schema | MarketState、MarketRegimeFeature、MarketRegimeRecord、API/TS 类型 | 字段和版本语义分散。 |
| 策略 Schema | StrategyVersion dataclass、TraderStrategyVersion JSON payload、API/TS 类型 | 正式策略与每日建议混合。 |
| 回测结果 | BacktestResultRun、RulePool.backtest_result、Job result、Artifact/report | 结果读取存在 fallback 和分叉。 |
| Prompt | 新 v1 文件、旧文件、代码内手写输出说明 | 新 Prompt 不是生产事实源。 |
| 数据引用 | 数据库记录、storage_ref、artifact_ref、直接文件路径 | 正式对象不能稳定追溯。 |

## 11. 复用与重构边界

### 11.1 建议保留

- JobService、Job 表、Job 审计和控制能力。
- ConfigProfile、权限、用户、备份和健康检查。
- BlogArticle、RawArticle 和文章查询。
- OHLCVBar、Indicator 和基础抓取 Service。
- MarketSnapshot、MarketDataset、MarketRegimeFeature、MarketRegimeRecord。
- BacktestEngine 的 snapshot-only 原则、fingerprint 和分市场状态统计。
- RuleApplicabilityProfile 的独立建模方向。
- WorkflowRun/WorkflowRunStep 的运行追踪。

### 11.2 建议改造或迁移

- ArticleMetadata 迁移到 ArticleStructure、PromptRun 和 RuleCandidate。
- RulePool 迁移到 RuleCandidate、RuleVersion、RuleFamily。
- TraderProfile/Persona/TraderMemory 迁移到三层 AuthorProfile。
- TraderStrategyVersion 迁移到稳定 StrategyVersion 和每日实例。
- StrategyRegimeSelection 迁移为 DailyRuleSelection。
- 盘前/盘后 Job 产物迁移为正式业务对象。
- Job/Workflow/Pipeline 定义收敛为单一运行契约。

### 11.3 建议退役

- 普通用户 Jobs、Workflows、Artifacts 独立主入口。
- `/api/ui/system/status` legacy API。
- StrategyStudio 重复 API。
- 旧 Prompt 生产调用。
- Persona 示例和文件型 profile 作为正式业务事实源。
- 未注册且无迁移责任人的孤立前端实现。

## 12. 严格 Review 补充清单

### 12.1 API 注册与历史模块

163 条 FastAPI 路由按实际 endpoint 模块归为以下注册家族，均已纳入迁移矩阵：

| 注册家族 | 当前职责 |
| --- | --- |
| 根与健康 | `/`、`/health`、`/health/*`、OpenAPI 文档 |
| 旧业务 API | `/articles*`、`/trades*`、`/market*`、`/reports*`、`/snapshots*`、`/strategy_versions*`、`/backtest_results*`、`/rankings*`、`/alerts*` |
| UI 系统与安全 | `auth`、`system`、`ops`、`profiles`、`security`、`data-audits`、`job-audits`、`data-health`、`imports` |
| UI 运行层 | `jobs`、`workflows`、`pipelines`、`artifacts` |
| UI 业务层 | `article-metadata`、`market`、`kaipan`、`rule-pool`、`optimize`、`strategy-studio`、`persona`、`signals`、`snapshots`、`traders` |

源码中存在但 `api/app.py` 未注册的历史 Router：

- `api/routers/alignment.py`
- `api/routers/backtest.py`
- `api/routers/blog.py`
- `api/routers/health.py`
- `api/routers/market.py`
- `api/routers/run.py`
- `api/routers/signal.py`
- `api/routers/strategy.py`
- `api/routers/trade.py`
- `api/routes/reports.py`
- `api/routers/ui/settings.py`

这些模块不能视为当前 API 能力，但仍是 legacy 代码和潜在误注册风险。`api/dependencies.py` 与 `api/deps.py` 也构成依赖入口重复。

### 12.2 Job、Workflow、Pipeline 和调度

33 个 JobDefinition 已逐项核对：

```text
db-migrate, init-project, seed-data, backup-data, restore-data,
crawl, clean, validate, store, process, import-trade-logs,
pipeline-run, pipeline-step, migrate-crawl-state, clusters-build,
e2e-regression, run-pre-market, run-after-close, persona-init-sample,
market-state-build, snapshot-build, strategy-build, ohlcv-crawl,
backtest-run, backtest-validate-rules, backtest-reproducibility-check,
rule-pool-backtest, optimize-create-candidate, candidate-review,
rule-review, kaipan-fetch, kaipan-normalize, kaipan-run
```

其中 24 个 `runnable=true`，9 个仅注册不可直接运行。两个 Workflow 为 `ohlcv` 和 `scheduler`。

源码实际有 5 个 PipelineSpec：

- Runtime Bridge 已注册：`article_pipeline`、`backtest`、`optimize-rule-pool`、`strategy`。
- 已定义但未注册：`market_data`。

当前至少有六套调度路径：

1. `cli/main.py scheduler-start` 的盘前/盘后 BlockingScheduler。
2. `src/pipeline/scheduler.py` 的 PipelineScheduler。
3. `ArticlePipelineScheduleService` 的文章每日调度。
4. `RuleBacktestScheduler` 的规则回测调度。
5. `MarketService` 的 OHLCV 调度。
6. `KaipanService` 和 `src/providers/kaipan_scheduler.py` 的 Kaipan 调度。

这些调度器主要使用进程内状态，状态查询和生命周期并非统一持久化事实源。

### 12.3 前端孤立实现

原审计把部分已接入实现误标为未注册，Review 后修正：

- `features/data-health/*` 已由 `/system/health` 使用。
- `features/market-workspace/*` 已由 `/market/kaipan` 和 `/market/ohlcv` 使用。

确认仍未被 `router.tsx` 页面链路使用的主要实现：

- `features/backtests/backtests-center.tsx`
- `features/strategy-studio/strategy-studio.tsx`
- `features/reports/report-center.tsx`
- `features/signals/signals-center.tsx`
- `features/imports/import-center.tsx`
- `pages/admin/*`

### 12.4 第二套或多套事实源

| 领域 | 当前并存事实源 | Review 结论 |
| --- | --- | --- |
| 规则 | `ArticleMetadata.strategy_rules`、`rule_pool`、`StrategyVersion.rules_snapshot`、`config/rules/behavior_rules.yaml`、`data/patterns/*` | 不止两套；用途虽不同，但当前消费边界不清，必须建立 canonical RuleVersion 和只读派生关系。 |
| 策略 | `TraderStrategyVersion` ORM、`StrategyVersion` dataclass、JSON `strategy_payload/rules_snapshot`、候选优化输出、日报文件 | ORM 与 JSON payload 混合，正式策略和每日实例未分离。 |
| 画像 | Persona cluster 文件、TraderProfile 文件、TraderMemory 表、行为规则 YAML、前端 Persona | 没有作者画像 canonical 对象。 |
| 市场数据 | OHLCV/快照数据库、Provider 实时返回、Kaipan 原始/归一化文件、`storage_ref` 文件 | 回测与日常运行的可用边界未统一。 |
| 市场状态 | Persona MarketState 文件/计算、`market_regime_features`、`market_regimes`、artifact | 分类、特征、记录和文件并存。 |
| 回测 | BacktestResultRun、RulePool.backtest_result、Job result、Artifact/report | 查询存在 fallback，结果事实源不唯一。 |
| Prompt | 19 个文件 Prompt、硬编码分类 Prompt、提取代码手写输出约束 | Prompt Registry 尚未成为唯一事实源。 |

### 12.5 代码证据边界

本审计的结论来自 `router.tsx`、`navigation.ts`、`route-registry.ts`、`api/app.py` 的实际注册、FastAPI `app.routes`、`__tablename__` 声明、Alembic 迁移、Job/Workflow/Pipeline 注册常量和 Prompt 加载调用。以下内容没有被当作已确认事实：

- `docs/bak` 中描述但代码未注册的功能。
- 仅存在设计文档、Prompt 文件或 Schema 名称而没有生产调用的目标能力。
- 未连接实际数据库时的表数据量、脏数据比例和部署数据库当前对象。
- 未通过运行测试证明的“所有回测路径绝不调用实时 Provider”。

## 13. 审计验收结论

- [x] 未修改核心业务行为。
- [x] 已检查前端、API、Service、Job、Workflow、Pipeline、模型、Prompt 和主要业务链路。
- [x] 已识别重复入口、重复 Schema、重复事实源和 legacy 实现。
- [x] 已明确可复用基础与必须重构的边界。
- [x] 已区分注册运行时、未注册历史源码和迁移遗留对象。
- [x] 所有结论均有代码证据或明确标记为待 Stage 2/6 验证。
- [x] 未开始 Stage 1。

运行时生产数据库中的实际数据量、脏数据比例和部署版本不属于本次代码现状审计的事实范围，将在 Stage 2 数据迁移前通过迁移盘点单独验证。
