# Kaipan Provider 设计

## 背景

`src/providers/kaipan_provider.py` 原本只承担私有接口抓取草案，主要职责是发起 HTTP 请求并保存 raw JSON。随着 Stage 2 推进，它需要升级为一个可调用的 provider：能够对外输出热点、题材成分和强势标的三类标准结构，同时保留现有 raw 抓取方法，供 `kaipan_scheduler.py` 和后续快照流程继续复用。

## 目标

- 把 `KaipanProvider` 从“抓取草案”推进为“可调用 provider”。
- 至少支持三个 capability：
  - `hot_topics`
  - `topic_constituents`
  - `strong_symbols`
- 对外输出与当前 Stage 1 快照一致的标准结构，便于后续 `market_universe` 和 fallback provider 复用。
- 保留现有 raw fetch 方法，不破坏 `kaipan_scheduler.py` 的抓取路径。

## 职责边界

### 负责

- 组装 Kaipan 私有接口请求参数。
- 调用现有 raw 接口方法拉取数据。
- 将 raw 响应归一为标准 provider payload。
- 提供 `fetch_hot_topics()`、`fetch_topic_constituents()`、`fetch_strong_symbols()` 这类高层能力入口。

### 不负责

- 不负责最终快照文件落盘。
- 不负责 schema 文件映射和批量 normalize。
- 不负责调度编排和定时任务。
- 不把 `device_id` 作为外部配置项暴露给调用方。

## 现阶段 capability

### 1. `hot_topics`

聚合以下 raw 接口：

- `fetch_board_strength()`
- `fetch_industry_ranking()`
- `fetch_concept_fengkou()`

输出：

- `dataset = "hot_topics"`
- `trade_date`
- `slot`
- `topics` 列表
- `sources` 标识

### 2. `topic_constituents`

聚合以下 raw 接口：

- `fetch_stock_sector_v2()`
- `fetch_theme_detail()`
- `fetch_limit_up_reason()`
- `fetch_limit_up_info()`
- `fetch_lhb_list()`

输出：

- `dataset = "topic_constituents"`
- `trade_date`
- `slot`
- `constituents` 列表
- `sources` 标识

### 3. `strong_symbols`

聚合以下 raw 接口：

- `fetch_strong_fengkou()`
- `fetch_interval_stats_stock()`
- `fetch_morning_bidding_list()`

输出：

- `dataset = "strong_symbols"`
- `trade_date`
- `slot`
- `symbols` / `candidates` 列表
- `sources` 标识

## 扩展方法

- 新增能力时，优先增加一个新的 capability 分支，而不是把多个业务场景混进同一返回结构。
- 每个 capability 都应保持稳定的标准输出字段，避免上层消费者跟着 raw 接口变化。
- 如果后续要支持 `market_context` 或 `postmarket_evidence`，建议按同样模式新增 capability，再逐步接入 provider router。
- raw 方法可以继续存在，用于调度器、脚本和补抓场景；高层 capability 方法只负责组装与归一。

## 验收标准

- `provider.run("hot_topics", ...)` 能输出标准热点结构。
- `provider.run("topic_constituents", ...)` 能输出标准题材成分结构。
- `provider.run("strong_symbols", ...)` 能输出标准强势标的结构。
- 现有 raw fetch 方法仍可被 `kaipan_scheduler.py` 直接调用。

