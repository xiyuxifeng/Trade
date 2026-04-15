# Proposed Plan Project

## 项目目标

在现有 `trade-strategy-ai` 的盘前/盘后最小闭环基础上，扩展为一个“按 trader 隔离策略、主动取数、可回测、可赛马、可复盘归因”的交易研究与决策系统。

系统支持两种运行形态：
- 开发期：基于每日快照与日线行情的离线回测，用于筛选最优 trader 和验证策略版本。
- 上线后：按日执行盘前候选生成、盘后评分与排名，形成持续滚动的 trader 赛马机制。

## 核心业务流

### 1. 文章到策略

- 从数据库中的文章与评论中，用 LLM 抽取：
  - `strategy_rules`
  - `preconditions`
  - `trading_symbols`
  - `comment_insights`
- 按 `trader_id` 聚合文章抽取结果，生成每日 `trader_strategy_version`。
- 每个 trader 只使用自己的策略版本，不共享规则集合。

### 2. 市场信息到候选池

- 每天先生成概念热点快照，再生成行业热点快照。
- 再解析热点对应的成分股。
- 再从成分股中筛选出强势标的池。
- 最后结合每个 trader 的策略版本、画像、记忆，定向获取更深的数据与指标。

## 目标目录结构

```text
trade-strategy-ai/
├── docs/
│   └── Proposed-Plan/
│       ├── Proposed-Plan.md
│       ├── Proposed-Plan-Change.md
│       ├── Proposed-Plan-Project.md
│       ├── Proposed-Plan-Project-TaskList.md
│       └── Proposed-Plan-Session.md
│
├── src/
│   ├── models/
│   │   ├── trader_strategy_version.py
│   │   ├── hot_topics_snapshot.py
│   │   ├── topic_constituents_snapshot.py
│   │   ├── strong_symbols_snapshot.py
│   │   ├── trader_ranking.py                  # 可选
│   │   ├── backtest_run.py                    # 可选
│   │   └── backtest_trade.py                  # 可选
│   │
│   ├── strategy_library/
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── builder.py
│   │   └── service.py
│   │
│   ├── market_universe/
│   │   ├── schemas.py
│   │   ├── hot_topics_builder.py
│   │   ├── constituents_resolver.py
│   │   ├── strong_symbols_selector.py
│   │   └── snapshot_service.py
│   │
│   ├── providers/
│   │   ├── base.py
│   │   ├── hot_topics_provider.py
│   │   ├── topic_constituents_provider.py
│   │   ├── market_data_provider.py
│   │   ├── akshare_provider.py
│   │   └── fallback_provider.py
│   │
│   ├── backtest/
│   │   ├── schemas.py
│   │   ├── engine.py
│   │   ├── execution.py
│   │   ├── scoring.py
│   │   └── reporting.py
│   │
│   ├── evaluation/
│   │   ├── evidence_pack.py
│   │   ├── postmortem_service.py
│   │   ├── ranking_service.py
│   │   └── failure_taxonomy.py
│   │
│   └── agents/
│       ├── manager_agent/
│       │   └── agent.py
│       ├── trader_agent/
│       │   └── agent.py
│       ├── data_agent/
│       │   ├── agent.py
│       │   └── skills/
│       │       ├── fetch_market.py
│       │       ├── fetch_hot_topics.py
│       │       ├── fetch_topic_constituents.py
│       │       ├── fetch_strong_symbols.py
│       │       ├── fetch_ohlcv.py
│       │       └── fetch_indicators.py
│       └── strategy_agent/
│           └── agent.py
```

## 各子系统职责

### `strategy_library`
- 从 `article_metadata` 聚合出 per-trader 规则集。
- 执行去重、过滤、质量门禁。
- 生成每日 released 版本。
- 提供“获取当前版本”和“查询历史版本”的服务入口。

### `market_universe`
- 生成概念热点和行业热点快照。
- 解析主题对应成分股。
- 从成分股中筛强势标的。
- 为回测和在线流程提供统一快照读写。

### `providers`
- 抽象数据源能力，隔离 AKShare 与未来第三方接口。
- 统一热点、主题成分、行情、指标的取数接口。

### `backtest`
- 提供开发期离线日线回测能力。
- 与线上评分共用 scoring 口径。
- 支持按 trader、按版本、按日期区间比较表现。

### `evaluation`
- 构建盘后 Evidence Pack。
- 统一失败分类。
- 调用 LLM 进行结构化归因。
- 生成 trader ranking。

## 对现有子系统的保留与演进

### 保留
- `ManagerAgent.run_pre_market/run_after_close`
- `DataAgent` 的 capability_missing 机制
- `StrategyAgent` 的规则评估与信号合成骨架
- `TraderProfile` / `TraderMemory` 作为画像和记忆输入
- `pipeline/tasks/process_tasks.py` 作为异步任务入口
- `article_metadata` 作为文章抽取结果主表

### 演进
- `ManagerAgent` 从最小编排升级为多阶段 orchestrator。
- `TraderAgent` 从 watchlist 模板生成升级为 per-trader policy 决策器。
- `DataAgent` 从单一行情入口升级为多能力路由器。
- `SignalContext` 从轻量追踪升级为完整回放上下文。

## 数据与决策链路

### 盘前链路
- 读取最新 released 策略版本。
- 读取热点/成分股/强势池快照。
- 为每个 trader 规划定向深挖数据需求。
- 调用 DataAgent 获取深挖数据。
- TraderAgent 给出 `buy/sell/hold` 建议。
- StrategyAgent 合成结构化 Signal。
- RiskAgent 做风控过滤。
- Manager 输出盘前日报与赛马输入。

### 盘后链路
- 拉取或读取盘后评估数据。
- 计算收益、MFE、MAE、规则命中、违背前置条件情况。
- 生成 ranking。
- 对差评建议构建 Evidence Pack。
- 用 LLM 产出结构化失败原因与改进动作。
- 写回 TraderMemory。

## 技术原则

- 程序负责确定性规则、评分、快照、回测、provider 适配。
- LLM 负责文章理解和盘后解释，但输出必须结构化、可校验。
- Agent 负责串联多步流程、降级与任务化。
- 所有关键中间结果尽量落库或落盘为快照，优先保证可回放和可追溯。

## 预期产物

- 每日 trader 策略版本
- 每日热点快照、成分快照、强势池快照
- 盘前建议与结构化信号
- 盘后评分、ranking、归因结果
- 开发期回测报告
