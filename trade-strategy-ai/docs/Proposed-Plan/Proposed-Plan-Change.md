# Proposed Plan 变更清单

本文档记录为落地 `Proposed-Plan.md` 所需的代码修改点、建议新增模块，以及每项修改的原因。

## 一、需要修改的现有文件

### 1. 配置与运行入口

#### `src/common/config.py`
- 修改内容：
  - 扩展 `DataConfig`，新增热点快照、强势股筛选、provider 优先级、回测参数、策略版本发布参数。
  - 扩展 `TraderConfig`，新增 trader 是否参与赛马、候选池限制、评分偏好、策略版本偏好。
  - 新增独立配置块，如 `BacktestConfig`、`StrategyLibraryConfig`、`HotspotConfig`、`RankingConfig`。
- 修改原因：
  - 当前配置只覆盖 Phase 0/0.5 的盘前盘后最小闭环，无法表达“每日策略版本发布、热点快照生成、开发期回测、上线后赛马”的运行参数。

#### `cli/main.py`
- 修改内容：
  - 更新默认 YAML 模板，暴露新增配置项。
  - 后续挂载新命令，如构建策略版本、构建快照、运行回测、查询 ranking。
- 修改原因：
  - CLI 是当前项目的主要控制面。若不补配置模板和命令入口，新能力难以手工验证和渐进上线。

#### `api/routers/run.py`
- 修改内容：
  - 保留 `/run/pre_market` 和 `/run/after_close`，但补充返回字段，如 `strategy_version_id`、赛马摘要、快照引用。
- 修改原因：
  - 未来盘前盘后不再只是简单 report/result，还需要暴露“用的是哪版策略、来自哪一批候选池、盘后如何排名”的追踪信息。

### 2. 契约与数据结构

#### `src/schemas/contracts.py`
- 修改内容：
  - 扩展 `DataRequest`，支持 `purpose`、`snapshot_date`、`topic_ids`、`universe_scope`、更明确的 constraints。
  - 扩展 `DataResponse.payload` 的标准结构，支持 `hot_topics`、`topic_constituents`、`strong_symbols`、`ohlcv_1d`、`indicators`。
  - 扩展 `TradeIdea`，增加 `strategy_version_id`、`source_topic_ids`、`evidence_refs`、`decision_mode`。
  - 扩展 `IdeaEvaluation` / `EvaluationResult`，增加 `mfe`、`mae`、规则命中、市场态快照、失败原因分类、ranking features。
- 修改原因：
  - 现有契约适合最小闭环，不足以承载“3→2→1 取数链路、盘后 Evidence Pack、离线回测与在线赛马共用评分”的新需求。

#### `src/schemas/review_task.py`
- 修改内容：
  - 增加盘后差评归因所需的结构化字段，如 evidence pack 引用、失败分类、建议动作、写回结果。
- 修改原因：
  - 当前 review task 更偏“触发复盘”记录，不足以支撑后续 LLM 归因和经验写回。

### 3. DataAgent 与数据技能

#### `src/agents/data_agent/agent.py`
- 修改内容：
  - 从单一 `last_price` 能力升级为 capability router。
  - 支持按 field 分发到热点、成分股、强势池、OHLCV、指标等 skill。
- 修改原因：
  - 新方案的核心是“按策略主动定向取数”。如果 DataAgent 仍然只会 `last_price`，整个计划无法成立。

#### `src/agents/data_agent/skills/fetch_market.py`
- 修改内容：
  - 保留为 `last_price` 专用 skill，或者降级成基础行情 skill。
  - 不再承担全部市场数据入口。
- 修改原因：
  - 这个文件当前职责过窄，无法承载热点、成分、强势、指标等不同类型的数据返回。

#### `src/agents/data_agent/skills/extract_article_metadata.py`
- 修改内容：
  - 增强规则抽取质量门禁与 trader 归属辅助信息。
  - 为“策略版本构建”保留更稳定的结构化证据。
- 修改原因：
  - 策略版本的上游就是文章抽取。如果这一层缺少质量标记和结构化证据，后续版本构建和追溯都不稳定。

### 4. 编排与交易决策

#### `src/agents/manager_agent/agent.py`
- 修改内容：
  - 在保留 `run_pre_market` / `run_after_close` 入口的前提下，新增编排阶段：
    - 读取或生成 trader 策略版本
    - 读取或生成热点/成分/强势池快照
    - 调度定向深挖取数
    - 汇总盘前候选、盘后排名、失败归因
  - 将复杂业务拆到独立 service，避免文件继续膨胀。
- 修改原因：
  - `ManagerAgent` 是主链路入口，但当前只适合最小闭环。新方案会显著增加编排步骤，必须拆分职责，否则后续难维护和测试。

#### `src/agents/trader_agent/agent.py`
- 修改内容：
  - 从 `watchlist + last_price` 模板生成，升级为消费：
    - `trader_strategy_version`
    - `strong_symbols_snapshot`
    - `trader_profile`
    - `trader_memory`
  - 输出支持 `buy/sell/hold`，并可先规划深挖请求再给最终建议。
- 修改原因：
  - 你要的是“像交易员一样根据习惯和策略主动分析”，不是简单盯 watchlist。TraderAgent 必须变成真正的 per-trader policy 执行器。

#### `src/agents/strategy_agent/agent.py`
- 修改内容：
  - 支持直接消费版本化规则快照，而不是临时 rules 列表。
  - 支持热点、市场态、前置条件过滤。
- 修改原因：
  - 策略库版本化后，信号生成必须以“某版本规则”为准，否则无法复盘、无法对比 trader。

#### `src/strategy/types.py`
- 修改内容：
  - 给 `SignalContext` 增加 `strategy_version_id`、`preconditions_snapshot`、`source_topic_ids`、`universe_snapshot_ref`。
- 修改原因：
  - 盘后归因、赛马排名、信号审计都需要完整上下文。现有上下文字段不够。

#### `src/strategy/signal_version.py`
- 修改内容：
  - 持久化新上下文字段。
- 修改原因：
  - 版本控制必须覆盖新增决策信息，否则“回放和审计”只完成了一半。

### 5. 画像、记忆、评估

#### `src/trader_profile/schemas.py`
- 修改内容：
  - 增加更接近策略偏好的字段，如常用条件、风险风格、主题偏好、仓位倾向。
- 修改原因：
  - 现有画像只够做轻量 hint，不够支持策略版本构建和 trader 间对比。

#### `src/trader_profile/service.py`
- 修改内容：
  - 保持为画像聚合服务，但输出要能为策略版本构建提供稳定输入。
- 修改原因：
  - 新方案需要画像参与策略库和定向深挖决策，但不应直接把版本构建逻辑塞进 profile service。

#### `src/trader_memory/schemas.py`
- 修改内容：
  - 新增 memory type，如 `postmortem`、`strategy_adjustment`、`market_regime_note`。
- 修改原因：
  - 差评归因和经验修正需要比 `success_case/failure_case/review_note` 更细的写回分类。

#### `src/trader_memory/service.py`
- 修改内容：
  - 支持按策略版本、主题、标的检索。
  - 支持归因结果与调整建议写回。
- 修改原因：
  - 后续 TraderAgent 需要拿历史失败模式和修正建议作为真正可检索的“记忆”，而不是只拼接少量文本摘要。

### 6. Pipeline 与任务链

#### `src/pipeline/tasks/process_tasks.py`
- 修改内容：
  - 新增任务类型并扩展 handler：
    - `build_trader_strategy_version`
    - `build_hot_topics_snapshot`
    - `build_topic_constituents_snapshot`
    - `build_strong_symbols_snapshot`
    - `run_postmortem_analysis`
- 修改原因：
  - 当前 pipeline 只覆盖“文章入库 → metadata → cluster”。新方案的日常闭环需要更多异步节点和失败重试能力。

### 7. ORM 模型

#### `src/models/signal.py`
- 修改内容：
  - 增加 `trader_id`、`strategy_version_id`、`source_topic_ids`、`evaluation_ref` 等字段。
- 修改原因：
  - 没有这些字段，盘前信号与盘后评分、策略版本和主题来源无法建立稳定关联。

#### `src/models/article_metadata.py`
- 修改内容：
  - 视需要补充抽取质量和聚合辅助字段。
- 修改原因：
  - 策略版本生成依赖 article metadata 的稳定性，需要更好的质量控制和可追溯性。

## 二、建议新增的模块

### 1. 数据库模型

#### `src/models/trader_strategy_version.py`
- 原因：
  - 需要按 `trader_id + as_of_date` 维护可发布、可比较、可回放的策略版本。

#### `src/models/hot_topics_snapshot.py`
- 原因：
  - 需要固化每日热点快照，保证离线回测可复现。

#### `src/models/topic_constituents_snapshot.py`
- 原因：
  - 主题到成分股的映射在未来可能来自不同 provider，需要独立快照化保存。

#### `src/models/strong_symbols_snapshot.py`
- 原因：
  - 强势池是盘前候选的直接输入，也是回测和赛马的重要中间结果。

#### `src/models/trader_ranking.py`（可选）
- 原因：
  - 若要长期保存赛马结果和滚动排名，单独建表更清晰。

#### `src/models/backtest_run.py` / `src/models/backtest_trade.py`（可选）
- 原因：
  - 开发期回测如果需要可追溯和横向对比，最好把 run 和 trade 结果显式落库。

### 2. Migration

#### `src/db/migrations/versions/<timestamp>_add_trader_strategy_and_universe_snapshots.py`
- 原因：
  - 新模型必须通过 Alembic 落地，确保本地开发和未来服务部署使用同一套 schema。

### 3. 策略库子系统

#### `src/strategy_library/schemas.py`
- 原因：
  - 需要定义“策略版本”“规则聚合结果”“质量门禁结果”等结构。

#### `src/strategy_library/repository.py`
- 原因：
  - 版本读写、按 trader 查询、发布状态切换需要稳定的数据访问封装。

#### `src/strategy_library/builder.py`
- 原因：
  - 聚合 `article_metadata` 到 per-trader 规则集是独立职责，不应塞进 Manager 或 TraderProfile。

#### `src/strategy_library/service.py`
- 原因：
  - 需要提供“构建版本、发布版本、获取当前版本”的业务入口。

### 4. 市场候选池子系统

#### `src/market_universe/schemas.py`
- 原因：
  - 需要统一定义热点 topic、主题成分、强势标的、评分特征等结构。

#### `src/market_universe/hot_topics_builder.py`
- 原因：
  - 热点生成逻辑独立且会持续演进，不应直接写在 DataAgent 或 Manager 里。

#### `src/market_universe/constituents_resolver.py`
- 原因：
  - 主题成分股解析具有 provider 依赖，单独抽象更容易替换为第三方接口。

#### `src/market_universe/strong_symbols_selector.py`
- 原因：
  - “强势股池”是热点和定向深挖之间的桥梁，逻辑独立、适合单测。

#### `src/market_universe/snapshot_service.py`
- 原因：
  - 回测和在线赛马都依赖快照读取/写入，需要统一入口。

### 5. Provider 抽象层

#### `src/providers/base.py`
- 原因：
  - 需要统一 provider 接口，避免 DataAgent 直接绑定 AKShare。

#### `src/providers/hot_topics_provider.py`
- 原因：
  - 热点数据源未来大概率会变化，必须抽象。

#### `src/providers/topic_constituents_provider.py`
- 原因：
  - 主题成分股是最不稳定的一类数据能力，单独接口最稳妥。

#### `src/providers/market_data_provider.py`
- 原因：
  - OHLCV、指标、行情补数未来也可能需要多源切换。

#### `src/providers/akshare_provider.py`
- 原因：
  - v1 默认数据源就是 AKShare，需要一个正式适配层而不是散落工具函数。

#### `src/providers/fallback_provider.py`
- 原因：
  - 某些能力 AKShare 不足时，需要规则推导或空实现兜底，不影响主流程。

### 6. DataAgent skills

#### `src/agents/data_agent/skills/fetch_hot_topics.py`
- 原因：
  - 热点请求应作为独立 skill，便于 capability 管理和测试。

#### `src/agents/data_agent/skills/fetch_topic_constituents.py`
- 原因：
  - 成分股解析通常需要 provider 调用和快照封装。

#### `src/agents/data_agent/skills/fetch_strong_symbols.py`
- 原因：
  - 强势池筛选逻辑与基础行情拉取不是一回事，应该独立出来。

#### `src/agents/data_agent/skills/fetch_ohlcv.py`
- 原因：
  - 后续回测和深挖取数都要走稳定的行情入口。

#### `src/agents/data_agent/skills/fetch_indicators.py`
- 原因：
  - 技术指标通常是深挖判断的直接输入，适合独立 skill。

### 7. 回测子系统

#### `src/backtest/schemas.py`
- 原因：
  - 定义回测输入、输出、评分结果和撮合记录。

#### `src/backtest/engine.py`
- 原因：
  - 回测主循环需要独立封装，不能混在 Manager 里。

#### `src/backtest/execution.py`
- 原因：
  - 撮合逻辑和主引擎职责不同，适合单独收敛。

#### `src/backtest/scoring.py`
- 原因：
  - 开发期回测和上线后赛马要共用评分口径。

#### `src/backtest/reporting.py`
- 原因：
  - 回测结果输出格式与日常 report 不同，适合分离。

### 8. 盘后归因与排名

#### `src/evaluation/evidence_pack.py`
- 原因：
  - 盘后差评需要标准化输入给 LLM，先有结构化 evidence 才能稳定归因。

#### `src/evaluation/postmortem_service.py`
- 原因：
  - 归因与写回是独立业务，不应散在 Manager 内。

#### `src/evaluation/ranking_service.py`
- 原因：
  - trader 对比与滚动排名会在开发期和上线后反复复用，需要稳定服务层。

#### `src/evaluation/failure_taxonomy.py`
- 原因：
  - 需要统一失败分类，避免不同 LLM 输出风格导致结果不可比较。

## 三、结构调整原则

- `ManagerAgent` 只保留编排职责，不直接承载热点构建、回测和策略版本聚合细节。
- `DataAgent` 只做 capability 路由与 skill 调用，不直接承担复杂业务判断。
- `strategy_library` 负责策略版本。
- `market_universe` 负责热点、成分股、强势池。
- `backtest` 负责开发期回放。
- `evaluation` 负责评分、归因、排名。

## 四、修改后带来的直接收益

- 每个 trader 可以拥有独立、可发布、可比较的策略版本。
- 盘前候选不再只依赖 watchlist，而是来自“热点 → 成分 → 强势 → 深挖”的主动取数链路。
- 开发期可通过日线回测筛选最优 trader。
- 上线后可按同一口径进行赛马和盘后排名。
- 盘后差评可以结构化归因并写回记忆，形成持续优化闭环。
