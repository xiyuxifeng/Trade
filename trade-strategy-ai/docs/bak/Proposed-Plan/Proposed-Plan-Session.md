# Proposed Plan Session

## 一句话目标

将当前 `trade-strategy-ai` 从“最小盘前/盘后闭环”扩展为“按 trader 独立策略版本、主动取数、开发期回测、上线后赛马、盘后归因写回”的系统。

## 已确认的关键业务决策

- 策略与习惯按 `trader_id` 隔离，不共享一套全局策略库。
- 开发期间使用离线回测筛选 trader；上线后使用在线赛马。
- 开发期回测先用 **日线** 落地，后续再考虑分钟级和事件驱动优化。
- 每个 trader 的策略库采用 **DB 版本化**。
- 策略版本采用 **每日自动发布**。
- 盘前候选标的来源不是固定 watchlist，而是：
  - **概念热点 -> 行业热点 -> 强势池 -> trader 定向深挖**
- 热点和成分股能力优先尝试 AKShare；若不足，先定义 provider 接口，后续可接第三方。
- 开发期离线回测要求 **保存每日快照**，确保结果可复现。
- 盘后“差评”主要来源是 **量化评分**，不是人工主导。

## 当前代码库现状摘要

### 已有基础
- 已有 `ManagerAgent`、`TraderAgent`、`DataAgent`、`StrategyAgent`、`RiskAgent` 基本骨架。
- 已有 `article_metadata` 抽取链路，字段包括 `strategy_rules`、`preconditions`、`trading_symbols`。
- 已有 `pipeline/tasks/process_tasks.py`，支持任务式串联处理。
- 已有 `TraderProfile` 和 `TraderMemory` 的最小实现。
- 已有 `StrategyAgent` 的规则评估和信号合成骨架。
- 已有 `SignalVersioning`，但上下文追踪字段还不够。
- 已有 AKShare 日线、指数、行业板块、概念板块历史抓取能力。

### 当前主要缺口
- `DataAgent` 当前几乎只支持 `last_price`。
- `TraderAgent` 仍偏 `watchlist + last_price` 模板逻辑。
- `ManagerAgent` 还没有策略版本、热点快照、强势池、ranking、Evidence Pack 编排。
- 缺少：
  - trader 策略版本表
  - 热点快照表
  - 成分快照表
  - 强势池快照表
  - backtest 模块
  - ranking / postmortem 模块

## 推荐架构边界

- `ManagerAgent`：只做编排，不做重业务。
- `DataAgent`：只做 capability 路由与 skill 分发。
- `strategy_library`：负责 per-trader 策略版本聚合与发布。
- `market_universe`：负责热点、成分股、强势池与快照。
- `providers`：负责 AKShare / 第三方 / fallback 数据源抽象。
- `backtest`：负责开发期回测。
- `evaluation`：负责评分、排名、差评归因和写回。

## 新增核心数据对象

- `trader_strategy_version`
- `hot_topics_snapshot`
- `topic_constituents_snapshot`
- `strong_symbols_snapshot`
- 可选：`trader_ranking`
- 可选：`backtest_run` / `backtest_trade`

## 新能力清单

### 盘前
- 读取最新 released 策略版本
- 读取热点/成分/强势池快照
- 为每个 trader 规划定向 `DataRequest`
- 返回 `buy/sell/hold` 建议
- 输出可追溯到策略版本和快照的信号

### 盘后
- 基于统一评分口径生成结果
- 输出 ranking
- 生成 Evidence Pack
- 调用 LLM 做结构化失败归因
- 写回 TraderMemory

### 开发期
- 可按 trader / 日期区间运行日线回测
- 可复现同一快照下的结果

## 当前文档产物

位于 `trade-strategy-ai/docs/Proposed-Plan/`：
- `Proposed-Plan.md`
- `Proposed-Plan-Change.md`
- `Proposed-Plan-Project.md`
- `Proposed-Plan-Project-TaskList.md`
- `Proposed-Plan-Session.md`

## Review 后的下一步建议

如果 review 通过，建议按下面顺序启动实现：

1. `Phase A：配置、契约、模型、migration`
2. `Phase B：strategy_library`
3. `Phase C：providers + market_universe + DataAgent 扩展`
4. `Phase D：TraderAgent / ManagerAgent / StrategyAgent 接入`
5. `Phase E：evaluation + ranking + postmortem`
6. `Phase F：backtest`

## 风险与注意事项

- 不建议第一版就引入分钟级回测，会显著放大复杂度。
- 不建议把热点/强势/版本聚合直接堆进 `ManagerAgent`。
- 不建议让 LLM 直接决定 DataAgent 请求字段，必须通过白名单映射。
- AKShare 可以作为 v1 数据源，但热点榜单和成分股能力可能不足，provider 抽象必须先做好。
