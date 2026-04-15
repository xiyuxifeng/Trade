# Proposed Plan TaskList

## 说明

本文档基于以下三部分综合整理：
- 现有 `docs/TaskList.md`
- `docs/Proposed-Plan/Proposed-Plan-Project-TaskList.md`
- 当前仓库已实现代码状态

整理原则：
- 已经有稳定实现且与新方案仍然兼容的任务，标记为已完成。
- 已被新方案替代或已失去意义的旧任务，不纳入本清单。
- 任务按“对当前主链路的阻塞程度”排序，而不是按旧 Phase 原顺序排列。

---

## P0：现有可复用基础（已完成）

### 配置、编排与基础闭环
- [x] PP-BASE-001 配置加载框架（YAML + 环境变量）已完成
- [x] PP-BASE-002 `ManagerAgent` 盘前/盘后最小闭环已完成
- [x] PP-BASE-003 `DataAgent` 最小能力与 `capability_missing` 机制已完成
- [x] PP-BASE-004 `TraderAgent` 最小结构化 `TradeIdea` 输出已完成
- [x] PP-BASE-005 APScheduler 调度能力已完成
- [x] PP-BASE-006 盘前/盘后 HTML 报告输出已完成

### 数据与文章处理
- [x] PP-BASE-007 PostgreSQL 基础 schema 已完成：`blog_articles` / `article_metadata` / `market_data` / `trade_logs`
- [x] PP-BASE-008 文章抓取、清洗、校验、入库 pipeline 已完成
- [x] PP-BASE-009 `article_metadata` 抽取链路已完成
- [x] PP-BASE-010 `raw_articles` / `crawl_state` 增量抓取存储已完成
- [x] PP-BASE-011 AKShare 日线、指数、板块历史数据同步能力已完成

### 画像、记忆、信号骨架
- [x] PP-BASE-012 `TraderProfile` 最小聚合结构已完成
- [x] PP-BASE-013 `TraderMemory` 存储与检索已完成
- [x] PP-BASE-014 `StrategyAgent` 规则评估与信号合成骨架已完成
- [x] PP-BASE-015 `RiskAgent` 基础风控能力已完成
- [x] PP-BASE-016 `SignalVersioning` 基础版本追踪已完成

---

## P1：必须先完成的主链路基础

### P1-A 配置、契约、模型
- [ ] PP-P1-001 扩展 `src/common/config.py`：新增策略版本、热点快照、候选池、回测、ranking 配置
- [ ] PP-P1-002 更新 `cli/main.py` 默认 YAML 模板，暴露新增配置项
- [ ] PP-P1-003 扩展 `src/schemas/contracts.py`：支持 `hot_topics`、`topic_constituents`、`strong_symbols`、`ohlcv_1d`、`indicators`
- [ ] PP-P1-004 扩展 `TradeIdea`：增加 `strategy_version_id`、`source_topic_ids`、`evidence_refs`、`decision_mode`
- [ ] PP-P1-005 扩展 `EvaluationResult` 和 review task schema，支持 Evidence Pack、失败原因分类、ranking features
- [ ] PP-P1-006 新增 `src/models/trader_strategy_version.py`
- [ ] PP-P1-007 新增 `src/models/hot_topics_snapshot.py`
- [ ] PP-P1-008 新增 `src/models/topic_constituents_snapshot.py`
- [ ] PP-P1-009 新增 `src/models/strong_symbols_snapshot.py`
- [ ] PP-P1-010 扩展 `src/models/signal.py`：增加 trader/version/topic/evaluation 追踪字段
- [ ] PP-P1-011 新增 Alembic migration，落地新增表与 signal 字段

### P1-B 验证
- [ ] PP-P1-012 为新增 ORM 模型编写单元测试
- [ ] PP-P1-013 验证 migration 可正常升级到最新 schema

---

## P2：按 trader 版本化策略库

### P2-A 模块建设
- [ ] PP-P2-001 新增 `src/strategy_library/schemas.py`
- [ ] PP-P2-002 新增 `src/strategy_library/repository.py`
- [ ] PP-P2-003 新增 `src/strategy_library/builder.py`
- [ ] PP-P2-004 新增 `src/strategy_library/service.py`

### P2-B 接入现有链路
- [ ] PP-P2-005 扩展 `src/agents/data_agent/skills/extract_article_metadata.py`，补充质量门禁与聚合辅助字段
- [ ] PP-P2-006 扩展 `src/trader_profile/schemas.py`，增加更适合策略版本构建的 trader 特征
- [ ] PP-P2-007 扩展 `src/trader_profile/service.py`，输出可被策略库消费的画像结果
- [ ] PP-P2-008 扩展 `src/pipeline/tasks/process_tasks.py`，增加 `build_trader_strategy_version` handler

### P2-C 验证
- [ ] PP-P2-009 验证同一 trader 同日只产生一个 released 版本
- [ ] PP-P2-010 验证不同 trader 的策略版本相互隔离
- [ ] PP-P2-011 验证版本可追溯到 source articles 和质量门禁结果

---

## P3：市场候选池与 Provider 抽象

### P3-A Provider 抽象
- [ ] PP-P3-001 新增 `src/providers/base.py`
- [ ] PP-P3-002 新增 `src/providers/hot_topics_provider.py`
- [ ] PP-P3-003 新增 `src/providers/topic_constituents_provider.py`
- [ ] PP-P3-004 新增 `src/providers/market_data_provider.py`
- [ ] PP-P3-005 新增 `src/providers/akshare_provider.py`
- [ ] PP-P3-006 新增 `src/providers/fallback_provider.py`

### P3-B 候选池模块
- [ ] PP-P3-007 新增 `src/market_universe/schemas.py`
- [ ] PP-P3-008 新增 `src/market_universe/hot_topics_builder.py`
- [ ] PP-P3-009 新增 `src/market_universe/constituents_resolver.py`
- [ ] PP-P3-010 新增 `src/market_universe/strong_symbols_selector.py`
- [ ] PP-P3-011 新增 `src/market_universe/snapshot_service.py`

### P3-C DataAgent 扩展
- [ ] PP-P3-012 新增 `src/agents/data_agent/skills/fetch_hot_topics.py`
- [ ] PP-P3-013 新增 `src/agents/data_agent/skills/fetch_topic_constituents.py`
- [ ] PP-P3-014 新增 `src/agents/data_agent/skills/fetch_strong_symbols.py`
- [ ] PP-P3-015 新增 `src/agents/data_agent/skills/fetch_ohlcv.py`
- [ ] PP-P3-016 新增 `src/agents/data_agent/skills/fetch_indicators.py`
- [ ] PP-P3-017 改造 `src/agents/data_agent/agent.py` 为 capability router
- [ ] PP-P3-018 收敛 `src/agents/data_agent/skills/fetch_market.py` 为基础行情 skill

### P3-D Pipeline 接入
- [ ] PP-P3-019 扩展 `process_tasks.py`：增加热点快照任务
- [ ] PP-P3-020 扩展 `process_tasks.py`：增加成分快照任务
- [ ] PP-P3-021 扩展 `process_tasks.py`：增加强势池快照任务

### P3-E 验证
- [ ] PP-P3-022 验证热点快照生成和读取
- [ ] PP-P3-023 验证成分快照生成和读取
- [ ] PP-P3-024 验证强势池快照生成和读取
- [ ] PP-P3-025 验证缺 capability 时仍返回 `capability_missing`

---

## P4：盘前主链路升级

### P4-A Trader / Strategy / Signal
- [ ] PP-P4-001 改造 `src/agents/trader_agent/agent.py`：消费策略版本、强势池、画像、记忆
- [ ] PP-P4-002 支持 `buy/sell/hold` 三类决策
- [ ] PP-P4-003 扩展 `src/agents/strategy_agent/agent.py`：支持版本化规则快照
- [ ] PP-P4-004 扩展 `src/strategy/types.py`：增加版本、快照、主题来源上下文字段
- [ ] PP-P4-005 扩展 `src/strategy/signal_version.py`：持久化完整上下文

### P4-B Manager 编排
- [ ] PP-P4-006 改造 `src/agents/manager_agent/agent.py`：接入策略版本与候选池快照
- [ ] PP-P4-007 在盘前链路加入定向深挖 `DataRequest` 规划
- [ ] PP-P4-008 盘前输出增加 `strategy_version_id`、候选来源和证据引用

### P4-C 验证
- [ ] PP-P4-009 验证单 trader 的完整盘前链路
- [ ] PP-P4-010 验证多 trader 并行盘前建议生成
- [ ] PP-P4-011 验证盘前信号可追溯到版本和快照

---

## P5：盘后评分、差评归因、ranking

### P5-A Evaluation 模块
- [ ] PP-P5-001 新增 `src/evaluation/evidence_pack.py`
- [ ] PP-P5-002 新增 `src/evaluation/failure_taxonomy.py`
- [ ] PP-P5-003 新增 `src/evaluation/postmortem_service.py`
- [ ] PP-P5-004 新增 `src/evaluation/ranking_service.py`

### P5-B 记忆与复盘接入
- [ ] PP-P5-005 扩展 `src/trader_memory/schemas.py`：新增 `postmortem`、`strategy_adjustment` 等类型
- [ ] PP-P5-006 扩展 `src/trader_memory/service.py`：支持按策略版本、主题、标的检索
- [ ] PP-P5-007 扩展 `src/schemas/review_task.py`：支持结构化失败归因
- [ ] PP-P5-008 扩展 `process_tasks.py`：增加 `run_postmortem_analysis`

### P5-C Manager 接入
- [ ] PP-P5-009 改造 `src/agents/manager_agent/agent.py`：生成 Evidence Pack
- [ ] PP-P5-010 盘后评分增加 `MFE/MAE/规则命中/前置条件违背`
- [ ] PP-P5-011 盘后生成 ranking
- [ ] PP-P5-012 差评触发 LLM 归因并写回 TraderMemory

### P5-D 验证
- [ ] PP-P5-013 验证盘后评分输出
- [ ] PP-P5-014 验证 ranking 输出
- [ ] PP-P5-015 验证差评归因输出通过 schema 校验

---

## P6：开发期离线回测

### P6-A Backtest 模块
- [ ] PP-P6-001 新增 `src/backtest/schemas.py`
- [ ] PP-P6-002 新增 `src/backtest/execution.py`
- [ ] PP-P6-003 新增 `src/backtest/scoring.py`
- [ ] PP-P6-004 新增 `src/backtest/engine.py`
- [ ] PP-P6-005 新增 `src/backtest/reporting.py`

### P6-B 接入
- [ ] PP-P6-006 让回测读取策略版本与快照，而不是依赖实时链路
- [ ] PP-P6-007 与线上评分共用 scoring 口径
- [ ] PP-P6-008 增加 CLI 入口：执行某 trader 某区间回测

### P6-C 验证
- [ ] PP-P6-009 验证同一快照和版本下回测结果可复现
- [ ] PP-P6-010 验证多 trader 回测结果可对比

---

## P7：接口与可观测性

### P7-A API / CLI
- [ ] PP-P7-001 扩展 `api/routers/run.py` 返回更多追踪字段
- [ ] PP-P7-002 新增 API：查询策略版本、快照、ranking、回测结果
- [ ] PP-P7-003 新增 CLI：构建策略版本、构建热点/成分/强势快照、执行回测

### P7-B 验证
- [ ] PP-P7-004 验证 API 响应与 DB 状态一致
- [ ] PP-P7-005 验证 CLI 可触发关键链路

---

## 可并行开发的任务

以下任务在明确接口后可以并行推进：

- `PP-P2-001 ~ PP-P2-004`
- `PP-P3-001 ~ PP-P3-006`
- `PP-P3-007 ~ PP-P3-011`
- `PP-P5-001 ~ PP-P5-004`
- `PP-P6-001 ~ PP-P6-005`

在进入实现阶段后，比较适合拆给不同开发者或子任务并行的组合：

- 策略库：`PP-P2-*`
- 候选池与 provider：`PP-P3-*`
- 盘后评估与归因：`PP-P5-*`
- 回测：`PP-P6-*`

## 必须依赖前置项的任务

### 先有配置/契约/模型，才能往下做
- `PP-P2-*` 依赖 `PP-P1-001 ~ PP-P1-011`
- `PP-P3-*` 依赖 `PP-P1-001 ~ PP-P1-011`

### 先有策略版本和候选池，才能升级盘前链路
- `PP-P4-*` 依赖：
  - `PP-P2-001 ~ PP-P2-011`
  - `PP-P3-001 ~ PP-P3-025`

### 先有盘前链路，才能做盘后归因
- `PP-P5-*` 依赖：
  - `PP-P4-001 ~ PP-P4-011`

### 先有策略版本和快照，才能做开发期回测
- `PP-P6-*` 依赖：
  - `PP-P2-001 ~ PP-P2-011`
  - `PP-P3-001 ~ PP-P3-025`

### API / CLI 收尾依赖主链路稳定
- `PP-P7-*` 依赖：
  - `PP-P4-*`
  - `PP-P5-*`
  - `PP-P6-*`（至少核心接口完成）
