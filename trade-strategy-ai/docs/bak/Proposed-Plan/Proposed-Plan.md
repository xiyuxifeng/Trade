# 每 Trader 策略库 + 3→2→1 主动取数 + 开发期回测/上线赛马（Design + Implementation Plan）

## Summary

在现有 `ManagerAgent/DataAgent/StrategyAgent/RiskAgent + PostgreSQL + pipeline tasks + LLM 抽取 article_metadata` 基础上，新增一条每天可回放的“3(热点概念→行业)→2(强势池)→1(定向深挖)”数据与决策流水线；策略库按 `trader_id` 隔离并 **DB 版本化、每日自动发布**。开发期用离线日线回测筛选最优 trader，上线后用盘前/盘后在线赛马滚动排名；两者共用同一套“快照数据 + 评分口径 + 规则执行内核”。

## Key Changes (Agents/LLM/Program 的明确分工)

- **LLM（只做理解/解释，输出强制 JSON+校验）**
  - 从 `blog_articles` 抽取 `article_metadata.strategy_rules/preconditions/...`（已存在，继续迭代质量与覆盖）。
  - 盘后差评归因：输入程序生成的 Evidence Pack（收益/MFE/MAE/触发规则/市场态/缺失数据等），输出结构化“失败原因分类 + 改进动作”，写回 `TraderMemoryStore`。
- **程序（确定性、可回归、可复现）**
  - `claim_key -> required_fields/features` 白名单映射；DSL/规则校验与编译；指标计算；评分/排名；回测撮合（日线优先）。
  - “热点/强势”在 v1 用可复现的规则从历史数据计算，并将结果落库成每日快照（回测直接读快照）。
- **AI Agent + skills（多步编排、可回放、失败任务化）**
  - 每日构建并发布 trader 策略版本；每日生成热点/成分/强势/深挖取数请求；遇到 `capability_missing` 自动创建 `AgentTask` 驱动补能力或降级策略。

## Public Interfaces / Contracts

1. **新增 DataAgent capabilities（fields 扩展，仍走 `DataRequest.fields`）**
   - `hot_topics.concept`, `hot_topics.industry`：返回热点 topic 列表（带 score + features + evidence）。
   - `topic_constituents.concept`, `topic_constituents.industry`：topic -> symbols[]。
   - `strong_symbols`：强势候选池（symbol + strength_score + reason_features + originating_topic_ids）。
   - `ohlcv_1d`、`indicators`（逐步补齐）：为定向深挖与回测提供数据输入。
   - 兼容策略：DataAgent 若缺能力仍返回 `capability_missing`，Manager 记录 `AgentTask`。
2. **新增 Provider 抽象（先定义接口，AKShare/第三方后续实现）**
   - `HotTopicsProvider.get_hot_topics(date, kind)` -> topics[]
   - `TopicConstituentsProvider.get_constituents(date, kind, topic_id)` -> symbols[]
   - `MarketDataProvider.get_ohlcv(symbols, start, end, timeframe)` / `get_indicators(...)`
   - v1 默认实现：能用 AKShare 的就用 AKShare；不能保证的先返回 `capability_missing` 或用“规则推导热点/强势”的 fallback 实现。
3. **策略库 DB 版本化（每 trader 一套）**
   - `trader_strategy_versions`（核心字段）
     - `trader_id`, `as_of_date`, `version_id`, `status(released|candidate)`, `rules_snapshot(JSON)`, `preconditions_snapshot(JSON)`, `source_articles(list/refs)`, `quality_metrics`, `created_at`
   - 每日自动发布：生成当天 `released` 版本；盘前只读取最新 `released`。
4. **每日快照表（保证离线回测可复现）**
   - `hot_topics_snapshots(date, kind, topics_json, created_at)`
   - `topic_constituents_snapshots(date, kind, mapping_json, created_at)`
   - `strong_symbols_snapshots(date, symbols_json, created_at)`
   - 约定：回测/在线都优先读快照；缺失才触发“补算并写快照”。

## Daily Flow (3→2→1) 与编排点

1. **收盘后/夜间（或盘前早晨）**
   - 生成 `hot_topics`（概念优先，再行业）：基于板块近 N 日收益/量能/波动等确定性规则打分，写入 `hot_topics_snapshots`。
   - 解析 `topic_constituents`：优先 provider 获取；写入 `topic_constituents_snapshots`。
   - 从热点成分股里筛 `strong_symbols`：基于个股近 N 日动量/量能/趋势/波动等规则评分，写入 `strong_symbols_snapshots`。
   - 为每个 `trader_id` 生成并发布 `trader_strategy_versions`（聚合其文章抽取出的规则，做去重/过滤/质量门禁）。
2. **盘前（在线赛马的 pre_market）**
   - 对每个 trader：从 `strong_symbols_snapshot` 取宽入口候选；结合 trader 的策略版本与画像/记忆做重排。
   - `DeepDiveDataPlanner` 产出定向 `DataRequest`（白名单映射），调用 DataAgent 获取深挖数据/指标。
   - `TraderAgent/StrategyAgent/RiskAgent` 生成结构化 `TradeIdea/Signal`，Manager 汇总输出日报与信号版本归档。
3. **盘后（在线赛马的 after_close）**
   - 程序统一口径打分与排名（收益/回撤/MFE/MAE/触发情况/违背前置条件等）。
   - 差评触发：Evidence Pack -> LLM 归因 -> 写回 `TraderMemoryStore`；若归因需要缺失数据字段，则创建 `AgentTask`。

## Offline Backtest (开发期：日线优先)

- 输入：指定区间的每日快照（热点/成分/强势）+ 当日 `trader_strategy_version` + 日线行情（可来自 cache/DB/Provider）。
- 执行：按与线上一致的信号生成/风控/评分逻辑，逐日回放。
- 输出：每 trader 的回测报告、分项评分、规则贡献度统计（用于筛选最优 trader + 定位差规则）。

## Test Plan (验收用例)

1. **快照可复现**
   - 同一日期区间、同一快照、同一策略版本：离线回测结果严格一致（hash/关键指标一致）。
2. **能力缺失可闭环**
   - 当请求 `topic_constituents`/`strong_symbols` 等缺 capability：DataAgent 返回 `capability_missing`，Manager 生成 `AgentTask`，并能降级继续跑（例如仅用 watchlist/top_symbols）。
3. **策略版本隔离**
   - 两个 trader 同日发布不同 `trader_strategy_versions`，盘前生成建议应读取各自版本且可追溯到 `version_id`。
4. **线上赛马评分一致**
   - 在线盘后评分与离线评分口径一致（同一日同一输入应高度一致，允许数据源差异造成的小偏差但需可解释）。
5. **盘后归因结构化**
   - Evidence Pack 输入固定时，LLM 输出通过 schema 校验；失败时走降级模板并记录错误分类。

## Assumptions / Defaults

- 开发期回测粒度：**日线**；撮合默认用可复现的简化规则（如 next_open/close，止损止盈按日内 high/low 触发的保守/乐观口径需在实现时二选一并固定）。
- 热点计算 v1：先用可复现的规则从 AKShare 可得的板块历史与个股日线推导；后续接第三方“热点榜单/成分/涨停池”仅需实现 provider 接口并仍落同样快照表。
- 盘前宽入口采用你指定顺序：**概念热点 → 行业热点 → 强势池 → trader 定向深挖**；如果某层缺数据则降级到下一可用层（并产出待办）。

## 实施后可实现的效果

### 1. 每个 trader 拥有独立策略版本

- 每个 trader 可以按天生成独立的 `released` 策略版本。
- 每次盘前建议都能追溯到具体的 `strategy_version_id`。
- 同一天可以比较不同 trader 的策略版本效果，为“选出最优 trader”提供基础。

### 2. 盘前从被动 watchlist 变成主动取数

- 系统会先生成概念热点和行业热点。
- 再从热点里解析成分股并筛选强势池。
- 再根据每个 trader 的策略版本、画像、记忆，主动决定还要向数据提供者拿哪些行情和指标。
- 盘前输出不再只是固定观察列表，而是更接近“像交易员一样先看市场，再定向分析”。

### 3. 支持开发期离线回测

- 可以按日期区间回放某个 trader 在当日会看到的热点、成分股、强势池和策略版本。
- 可以在不依赖实时数据的情况下比较不同 trader 的策略效果。
- 可以用统一的评分口径筛选值得保留的 trader。

### 4. 支持上线后的 trader 赛马

- 每天盘前可同时为多个 trader 生成建议。
- 盘后可用同一套标准计算收益、MFE、MAE、规则命中和总体排名。
- 可以持续输出“当前表现最优 trader”和滚动比较结果。

### 5. 支持结构化失败归因

- 当某个建议盘后表现差时，系统可以先生成结构化 Evidence Pack。
- 再调用 LLM 输出“失败原因分类 + 改进动作”。
- 这些结果可以写回 TraderMemory，形成“失败 -> 归因 -> 记忆 -> 下次改进”的闭环。

### 6. 支持渐进式接入数据源

- 第一阶段可以用 AKShare 和规则推导先跑通。
- 后续如 AKShare 在热点榜单、主题成分股等能力上不足，可以只替换 provider 适配层，不必推翻上层 Agent 和流程。
