# Persona 风格路由规格（Phase 1 / 收益最大化）

适用范围：A 股 / ETF / 可转债（第一期），多博主集合，定时自动抓取。

目标：在“模仿博主思考模式 + 可执行规则”的前提下，盘前根据市场情况动态选择最优风格（Style Cluster），以收益最大化为主目标，同时保持必要的基本风险约束（不自动下单）。

---

## 1. 核心对象

### 1.1 PersonaKey

- `persona_key = { source, author_id }`

来源：`blog_articles.source`、`blog_articles.author_id`。

### 1.2 StyleCluster（风格簇）

一个博主可以有多个风格簇；每个簇对应一套“自洽的可执行规则集”。

建议结构（JSON）：

- `cluster_id`: string（稳定 ID，建议由“中心特征 hash”生成）
- `label`: string（自动命名，如“ETF 趋势突破 / 可转债低吸 / A股事件驱动”）
- `instrument_focus`: `stock | etf | cb | mixed`
- `ruleset`:
  - `entry_rules[]`, `exit_rules[]`, `filters[]`, `sizing_rules[]`, `risk_rules[]`
- `applicability`（适用性条件，用于路由）
  - `preferred_regimes[]`: 允许的市场态势
  - `volatility_preference`: `low | mid | high | any`
  - `liquidity_requirement`: `good | any`
  - `timeframe_preference`: `intraday | daily | swing | any`
- `evidence_refs[]`: 代表性证据（文章/交易），用于可解释输出
- `stats`（用于收益导向选择）
  - `activity_score`: 近期活跃度（文章数量 + 时间衰减）
  - `coherence_score`: 规则一致性（冲突少得分高）
  - `backtest_score`（可选，后续加入）

### 1.3 MarketState（市场态势）

用于“盘前路由”输入。第一期建议做成轻量、可解释的结构（不追求完美预测）。

建议字段：

- `as_of_date`: date
- `scope`: `market | instrument`
- `market`: `CN`
- `regime`: `trend_up | trend_down | range | panic | euphoria`
- `volatility`: `low | mid | high`
- `liquidity`: `good | bad | unknown`
- `breadth`: `strong | weak | unknown`
- `event_risk`: bool

实现建议（第一期）

- 市场级：用代表指数或 ETF（如沪深 300 / 中证 500 / 全指）日线指标生成。
- 标的级：对 watchlist 中每个标的生成（如果有 OHLCV）。

落地方式（Phase 0.5 推荐，先用本地 CSV）：

- 从指数/ETF 日线 CSV 计算 regime/vol（列：`date`,`close`；可选 `volume`）
- CLI：`python -m cli.main market-state-build --config config/app.yaml`
- 配置：
  - `persona.market_state_benchmark_symbol: "510300.SH"`
  - `persona.market_state_benchmark_csv: path/to/510300_daily.csv`
  - （可选）`persona.market_state_path`：直接读取预生成 JSON

分类规则（v0，解释性优先）：

- 趋势：`close > MA20 > MA60` 且 MA20 上行 → `trend_up`
- 下跌：`close < MA20 < MA60` 且 MA20 下行 → `trend_down`
- 震荡：否则 → `range`
- 若 `vol20` 位于高分位且 5 日涨跌幅超过阈值：
  - `ret5 <= -7%` → `panic`
  - `ret5 >= +7%` → `euphoria`

---

## 2. 多风格的构建（聚类策略）

要求：一个博主允许多个风格簇。

### 2.1 文章特征向量（用于聚类）

对每篇文章抽取以下特征（优先从结构化抽取产物生成）：

- `instrument_type`: stock/etf/cb
- `holding_horizon`: intraday/short/swing/long
- `entry_trigger`: breakout/pullback/mean_revert/event/news
- `risk_method`: fixed_pct/atr/structure/none
- `position_style`: light_probe/heavy_conviction/pyramid/averaging_down
- `timeframe_used`: 5m/15m/daily/weekly
- `symbols`: 常提及标的（或行业/主题映射）

第一期简化：先按 `instrument_type + holding_horizon` 分桶，再桶内聚类。

### 2.2 聚类输出

- 每个桶内得到 1..N 个 `StyleCluster`
- 每个 `StyleCluster` 聚合生成 `ruleset` 与 `applicability`

### 2.3 时间衰减

证据权重采用指数衰减：

- `w = w0 * 2^(-Δt / half_life_days)`

第一期建议：`half_life_days = 90`。

---

## 3. 盘前路由（动态选择最优解）

输入：

- `persona_key`
- `market_state`（市场级 + 可选标的级）
- `watchlist`（A股/ETF/可转债混合）
- 可选：用户偏好（收益最大化 / 风险最小化等）

输出：

- `selected_clusters`：Top-1（必选）+ Top-2（备选）
- `explanations`：可解释原因（3 条“为什么选它”）
- `plans`：按选中 cluster 的规则生成的操作计划（每个标的或每个风格）

### 3.1 两层路由

**层 1：可行性过滤（Hard Filter）**

过滤条件示例：

- `instrument_focus` 不匹配（例如可转债簇不用于 ETF）
- `liquidity_requirement=good` 但 `market_state.liquidity=bad`
- 数据缺失（计算规则所需指标不可得）

**层 2：收益导向评分（Scoring Router）**

收益最大化优先：

Score 由以下项构成：

- `A`：适用性匹配度（MarketState 与 applicability）
- `R`：近期活跃度（Recency / Activity）
- `C`：规则一致性与抽取置信度（Coherence / Confidence）
- `F`：标的适配度（该簇常涉及标的/行业 vs 当前 watchlist）
- `E`：收益预期项（Expected Return Proxy 或 backtest）
- `P`：风险惩罚项（只做“基本约束”，不把风险放到第一位）

第一期建议权重（收益最大化）：

- `wE = 0.40`
- `wA = 0.25`
- `wF = 0.15`
- `wR = 0.10`
- `wC = 0.10`
- `wP = 0.10`（惩罚项用减法）

总分：

- `Score = wE*E + wA*A + wF*F + wR*R + wC*C - wP*P`

> 注：第一期如果缺少可用回测，则 `E` 用代理指标（例如：趋势簇在 trend_up 得高分；均值回归簇在 range 得高分；事件驱动簇在 high volatility + breadth strong 得高分）。

### 3.2 代理收益项 E（无回测时）

建议用“风格 × 市场态势”的收益倾向表（可解释且易调参）。例如：

- 趋势突破（ETF/大盘）：
  - trend_up: 1.0
  - range: 0.3
  - trend_down/panic: 0.1

- 均值回归/低吸（可转债/部分股票）：
  - range: 0.8
  - trend_up: 0.6
  - panic: 0.5（但 P 会更高）
  - euphoria: 0.2

- 事件驱动（A股）：
  - high vol + breadth strong: 0.9
  - 其他：0.3

---

## 4. 输出（强可解释）

盘前输出必须包含：

- `SelectedCluster`: 选中的 cluster、匹配的 MarketState、以及 3 条理由
- `BackupCluster`: 备选 cluster 与切换条件
- `PerSymbolPlan`（建议结构化）：
  - `entry_condition`（可执行 condition）
  - `order_plan`（限价/触发/分批）
  - `stop_loss`、`take_profit`、`time_stop`
  - `invalidation`（触发后撤销/停止交易的条件）

---

## 5. 盘后评估与反哺（为收益最大化服务）

第一期建议做“弱监督”的评估，目标是：

- 更新 cluster 的 `applicability` 与 `E` 代理表参数
- 逐步引入可回测 `backtest_score`

### 5.1 评估信号（从轻到重）

1) 规则触发后的后验收益（不需要真实交易）
- 例如：触发后 1/3/5 日收益、最大回撤

2) 对齐真实交易（如果有 trade_logs）
- 该博主在相似 regime 下真实偏好的 cluster

3) 回测（后续）
- 在不同 regime 分桶后比较 cluster 的期望收益与方差

---

## 6. 第一期开箱即用的策略建议

- ETF：优先趋势类簇（收益最大化），但在 range 里允许切换到震荡/均值回归簇。
- 可转债：允许“低吸/均值回归”与“强势趋势”两个簇共存，路由按波动与 regime 选择。
- A股：允许事件驱动/趋势突破/波段三类簇并存，路由重点看 breadth 与 vol。

---

## 7. 最小实现清单（不依赖 DSL 也能跑）

- 文章抽取：把规则片段写入 `article_metadata.strategy_rules/preconditions`
- 聚类：按 `instrument_type + holding_horizon` 分桶 + 简单聚类
- MarketState：先做市场级（日线）
- Router：两层过滤 + 加权评分，输出 Top-1 + Top-2
- 盘后：对“被选择的 cluster”做弱监督评分并记录

---

## 8. strategy_rules / preconditions JSON Schema（字段标准化）

目的：把“文章中抽出的规则/前置条件”标准化成可聚合、可路由、可回放的结构化 JSON。

落地位置：

- 代码 Schema：trade-strategy-ai/src/persona/schemas.py
- claim_key 字典：trade-strategy-ai/src/persona/claim_keys.py

### 8.1 ArticleStrategyRule（写入 article_metadata.strategy_rules[]）

最小字段（v0）：

- `schema_version`: string（默认 `v0`）
- `claim_key`: string（必须在 claim_key 字典内，例如 `entry.trigger`）
- `rule_type`: `entry | exit | filter | sizing | risk`
- `instrument_focus`: `stock | etf | cb | mixed`
- `condition`: object（表达式树 JSON，允许扩展；至少包含 `op`）
- `action`: object（动作结构；至少包含 `type`，可选 `side/order/price/params`）
- `params`: object（参数，如 `target_pct/stop_pct/max_hold_days`）
- `confidence`: number（0~1，可选）
- `source_url`: string（可选，证据链）
- `quoted_text`: string（可选，证据链）
- `published_at`: string(datetime)（可选，证据链）

示例：

```json
{
  "schema_version": "v0",
  "claim_key": "entry.trigger",
  "rule_type": "entry",
  "instrument_focus": "etf",
  "condition": {"op": "and", "args": [{"op": ">", "lhs": {"var": "close"}, "rhs": {"ind": "ma", "n": 20}}]},
  "action": {"type": "enter", "side": "buy", "order": "limit", "price": {"var": "close"}, "params": {}},
  "params": {"target_pct": 0.06, "stop_pct": 0.03},
  "confidence": 0.62,
  "source_url": "https://example.com/post/123",
  "quoted_text": "放量突破20日线后回踩确认介入",
  "published_at": "2026-04-01T08:00:00Z"
}
```

### 8.2 ArticlePrecondition（写入 article_metadata.preconditions[]）

用途：把“适用市场环境/前置条件”从文章里结构化出来，供聚类与路由使用。

最小字段（v0）：

- `schema_version`: string（默认 `v0`）
- `claim_key`: string（默认可用 `filter.market_regime`，也可扩展）
- `instrument_focus`: `stock | etf | cb | mixed`
- `condition`: object（表达式树 JSON）
- `confidence`: number（0~1，可选）
- `source_url/quoted_text/published_at`: 证据链字段（可选）

示例：

```json
{
  "schema_version": "v0",
  "claim_key": "filter.market_regime",
  "instrument_focus": "cb",
  "condition": {"op": "range_or_panic"},
  "confidence": 0.5,
  "source_url": "https://example.com/post/456",
  "quoted_text": "震荡市更适合低吸做T",
  "published_at": "2026-03-20T08:00:00Z"
}
```

---

## 9. claim_key 字典（v0）

说明：claim_key 是“可聚合、可对齐”的字段名；同一个 claim_key 的不同取值会触发冲突检测与多风格拆分。

v0（首批）：

- Entry：`entry.trigger`、`entry.confirmation`、`entry.timing`、`entry.price_type`
- Filters：`filter.market_regime`、`filter.volatility`、`filter.event_risk`、`filter.liquidity`、`filter.avoid_gap`、`filter.avoid_high_limitup`
- Exit：`exit.take_profit`、`exit.stop_loss`、`exit.time_stop`、`exit.invalidation`
- Scaling：`scale.in`、`scale.out`、`pyramid.allow`、`averaging_down.allow`
- Risk：`sizing.base_pct`、`sizing.max_pct`、`sizing.concentration`、`risk.max_drawdown`、`risk.daily_loss_limit`、`risk.no_trade_conditions`
- Universe：`universe.instruments`、`universe.sectors_bias`、`universe.symbol_blacklist`
