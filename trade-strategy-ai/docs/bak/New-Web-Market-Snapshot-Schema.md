# New Web Market Snapshot Schema

## 目标

把 `snapshot-build` 的输出统一成一份可扩展、可解释、可被 Web 直接消费的结构化快照。

## 顶层结构

- `snapshot_id`
- `trade_date`
- `market`
- `data_version`
- `provider_sources`
- `created_at`
- `data_quality`
- `sections`
- `metadata`

## Section 结构

每个 section 统一使用 `MarketSnapshotSection`：

- `section_id`
- `provider`
- `source_time`
- `record_count`
- `missing_reason`
- `quality_status`
- `payload`
- `metadata`

## 第一批 section

- `overview`
- `limit_up_down`
- `sector_activity`
- `auction`
- `ohlcv`
- `hot_topics`
- `topic_constituents`
- `strong_symbols`
- `market_state`

## 扩展原则

1. 新 section 只能通过 registry + builder 接入。
2. 新 section 必须返回 `MarketSnapshotSection`，不能新增顶层字段。
3. 缺失数据必须写 `missing_reason`，不能 silently drop。
4. `snapshot.json`、`snapshot.summary.json`、`snapshot.quality.json` 必须同步输出。
5. 结构化快照只作为 Web/Job 的正式输出，不新增 CLI 产品入口。
