# Proposed Plan Project TaskList

## 说明

本 TaskList 基于当前仓库已实现内容和 `docs/TaskList.md` 的完成状态整理，只保留这次 `Proposed-Plan` 真正需要推进的任务，并按“能开工”的顺序重排。

---

## Phase A：基础建模与配置扩展

### A1. 配置与契约
- [ ] PP-A1-001 扩展 `src/common/config.py`：新增策略版本、热点快照、回测、ranking 配置
- [ ] PP-A1-002 更新 `cli/main.py` 默认 YAML 模板，暴露新增配置项
- [ ] PP-A1-003 扩展 `src/schemas/contracts.py`：支持 `hot_topics/topic_constituents/strong_symbols/ohlcv_1d/indicators`
- [ ] PP-A1-004 扩展 `TradeIdea`：增加 `strategy_version_id/source_topic_ids/evidence_refs/decision_mode`
- [ ] PP-A1-005 扩展 `EvaluationResult` 与 review task schema，支持 Evidence Pack 与失败原因分类

### A2. 数据模型与迁移
- [ ] PP-A2-001 新增 `src/models/trader_strategy_version.py`
- [ ] PP-A2-002 新增 `src/models/hot_topics_snapshot.py`
- [ ] PP-A2-003 新增 `src/models/topic_constituents_snapshot.py`
- [ ] PP-A2-004 新增 `src/models/strong_symbols_snapshot.py`
- [ ] PP-A2-005 扩展 `src/models/signal.py`：增加 trader/version/topic/evaluation 追踪字段
- [ ] PP-A2-006 生成 Alembic migration，落地新增表与 signal 字段

### A3. 验证
- [ ] PP-A3-001 编写新增模型的 ORM 单元测试
- [ ] PP-A3-002 运行 migration 升级验证本地 schema 可用

---

## Phase B：策略库版本化

### B1. 策略库模块
- [ ] PP-B1-001 新增 `src/strategy_library/schemas.py`
- [ ] PP-B1-002 新增 `src/strategy_library/repository.py`
- [ ] PP-B1-003 新增 `src/strategy_library/builder.py`
- [ ] PP-B1-004 新增 `src/strategy_library/service.py`

### B2. 现有链路接入
- [ ] PP-B2-001 扩展 `src/agents/data_agent/skills/extract_article_metadata.py`，为策略版本构建保留质量门禁与证据字段
- [ ] PP-B2-002 扩展 `src/trader_profile/service.py`，让画像输出可作为策略版本构建的辅助输入
- [ ] PP-B2-003 扩展 `src/pipeline/tasks/process_tasks.py`：增加 `build_trader_strategy_version` handler

### B3. 验证
- [ ] PP-B3-001 为策略版本聚合编写单元测试
- [ ] PP-B3-002 验证同一 trader 同日只产生一个 released 版本
- [ ] PP-B3-003 验证不同 trader 的策略版本隔离

---

## Phase C：市场候选池与 Provider 抽象

### C1. Provider 抽象
- [ ] PP-C1-001 新增 `src/providers/base.py`
- [ ] PP-C1-002 新增 `src/providers/hot_topics_provider.py`
- [ ] PP-C1-003 新增 `src/providers/topic_constituents_provider.py`
- [ ] PP-C1-004 新增 `src/providers/market_data_provider.py`
- [ ] PP-C1-005 新增 `src/providers/akshare_provider.py`
- [ ] PP-C1-006 新增 `src/providers/fallback_provider.py`

### C2. 市场候选池模块
- [ ] PP-C2-001 新增 `src/market_universe/schemas.py`
- [ ] PP-C2-002 新增 `src/market_universe/hot_topics_builder.py`
- [ ] PP-C2-003 新增 `src/market_universe/constituents_resolver.py`
- [ ] PP-C2-004 新增 `src/market_universe/strong_symbols_selector.py`
- [ ] PP-C2-005 新增 `src/market_universe/snapshot_service.py`

### C3. DataAgent 扩展
- [ ] PP-C3-001 新增 `fetch_hot_topics.py`
- [ ] PP-C3-002 新增 `fetch_topic_constituents.py`
- [ ] PP-C3-003 新增 `fetch_strong_symbols.py`
- [ ] PP-C3-004 新增 `fetch_ohlcv.py`
- [ ] PP-C3-005 新增 `fetch_indicators.py`
- [ ] PP-C3-006 改造 `src/agents/data_agent/agent.py` 为 capability router
- [ ] PP-C3-007 将 `fetch_market.py` 收敛为基础行情 skill

### C4. Pipeline 接入
- [ ] PP-C4-001 扩展 `process_tasks.py`：增加热点快照任务
- [ ] PP-C4-002 扩展 `process_tasks.py`：增加成分快照任务
- [ ] PP-C4-003 扩展 `process_tasks.py`：增加强势池快照任务

### C5. 验证
- [ ] PP-C5-001 验证热点快照可生成并可重读
- [ ] PP-C5-002 验证成分快照可生成并可重读
- [ ] PP-C5-003 验证强势池快照可生成并可重读
- [ ] PP-C5-004 验证缺 capability 时仍返回 `capability_missing`

---

## Phase D：盘前主链路升级

### D1. Trader 与 Strategy
- [ ] PP-D1-001 改造 `src/agents/trader_agent/agent.py`：消费策略版本、强势池、画像、记忆
- [ ] PP-D1-002 扩展 `src/agents/strategy_agent/agent.py`：支持版本化规则快照
- [ ] PP-D1-003 扩展 `src/strategy/types.py`：增加版本与快照上下文字段
- [ ] PP-D1-004 扩展 `src/strategy/signal_version.py`：持久化完整上下文

### D2. Manager 编排
- [ ] PP-D2-001 改造 `src/agents/manager_agent/agent.py`：接入策略版本与候选池快照
- [ ] PP-D2-002 在盘前流程中加入定向深挖 `DataRequest` 规划
- [ ] PP-D2-003 支持 `buy/sell/hold` 三类建议
- [ ] PP-D2-004 盘前输出增加 `strategy_version_id` 与候选来源引用

### D3. 验证
- [ ] PP-D3-001 验证一个 trader 的完整盘前链路可运行
- [ ] PP-D3-002 验证多个 trader 可并行生成建议且互不串线
- [ ] PP-D3-003 验证盘前输出可追溯到策略版本与快照

---

## Phase E：盘后评分、归因、排名

### E1. Evaluation 模块
- [ ] PP-E1-001 新增 `src/evaluation/evidence_pack.py`
- [ ] PP-E1-002 新增 `src/evaluation/failure_taxonomy.py`
- [ ] PP-E1-003 新增 `src/evaluation/postmortem_service.py`
- [ ] PP-E1-004 新增 `src/evaluation/ranking_service.py`

### E2. 记忆与复盘接入
- [ ] PP-E2-001 扩展 `src/trader_memory/schemas.py`：新增 postmortem / strategy_adjustment 等类型
- [ ] PP-E2-002 扩展 `src/trader_memory/service.py`：支持按策略版本和主题检索
- [ ] PP-E2-003 扩展 `src/schemas/review_task.py`：增加结构化归因输出
- [ ] PP-E2-004 扩展 `process_tasks.py`：增加 `run_postmortem_analysis`

### E3. Manager 接入
- [ ] PP-E3-001 改造 `src/agents/manager_agent/agent.py`：生成 Evidence Pack
- [ ] PP-E3-002 盘后评分增加 `MFE/MAE/规则命中/前置条件违背`
- [ ] PP-E3-003 盘后生成 ranking，并写回 trader 结果
- [ ] PP-E3-004 差评触发 LLM 归因并写回 TraderMemory

### E4. 验证
- [ ] PP-E4-001 验证盘后评分可生成
- [ ] PP-E4-002 验证 ranking 可按 trader 输出
- [ ] PP-E4-003 验证差评归因通过 schema 校验

---

## Phase F：开发期离线回测

### F1. Backtest 模块
- [ ] PP-F1-001 新增 `src/backtest/schemas.py`
- [ ] PP-F1-002 新增 `src/backtest/execution.py`
- [ ] PP-F1-003 新增 `src/backtest/scoring.py`
- [ ] PP-F1-004 新增 `src/backtest/engine.py`
- [ ] PP-F1-005 新增 `src/backtest/reporting.py`

### F2. 接入现有链路
- [ ] PP-F2-001 让 backtest 读取策略版本与快照，而不是直接依赖实时取数
- [ ] PP-F2-002 让 scoring 与线上盘后评分共用口径
- [ ] PP-F2-003 增加 CLI 入口：运行某 trader 某区间回测

### F3. 验证
- [ ] PP-F3-001 验证相同快照与相同策略版本下回测结果可复现
- [ ] PP-F3-002 验证可输出多 trader 对比结果

---

## Phase G：接口与可观测性

### G1. API / CLI
- [ ] PP-G1-001 扩展 `api/routers/run.py` 返回更多追踪字段
- [ ] PP-G1-002 新增 API：查询策略版本、快照、ranking、回测结果
- [ ] PP-G1-003 新增 CLI：构建策略版本、构建候选池快照、执行回测

### G2. 验证
- [ ] PP-G2-001 验证 API 响应与 DB 状态一致
- [ ] PP-G2-002 验证 CLI 可完整触发关键链路

---

## 当前最建议先做的 3 个任务包

- [ ] 优先包 1：`Phase A + Phase B`
- [ ] 优先包 2：`Phase C`
- [ ] 优先包 3：`Phase D`

## 暂不进入首批实现的内容

- [ ] 分钟级回测
- [ ] 全市场扫描
- [ ] 第三方商业数据源真实接入
- [ ] UI 层可视化管理页面
