# Kaipan Ingestion and Storage Design

## 1. 目标

本文档定义 `New-Web-Market-Regime-Definition.md` 中 `10.5 建议新增的 Kaipan 接口清单` 的落表与计算分层方案，用于把新增 Kaipan 接口接入现有 Web 数据链路，并保证：

- 原始抓取数据可回放
- 标准化事实可查询
- 派生特征可复现
- 最终 regime 结论不依赖前端计算
- 尽量复用现有表结构，避免新增并行事实源

## 2. 设计原则

### 2.1 三层分离

1. 原始事实层
2. 派生特征层
3. 最终结论层

### 2.2 现有表优先

优先复用现有表：

- `market_snapshots`
- `market_snapshot_sections`
- `market_snapshot_items`
- `ohlcv_bars`
- `market_regime_features`
- `market_regimes`

只有在需要保留抓取批次、重试、原始响应审计时，才补通用 raw payload 表。

### 2.3 计算不回写原始表

接口返回中的派生值，不直接写入原始表的业务字段，而是进入 feature 层或 regime 层。

## 3. 数据分层

### 3.1 原始事实层

这一层保存“provider 返回后标准化”的结果。

落点：

- `market_snapshots`
- `market_snapshot_sections`
- `market_snapshot_items`
- `ohlcv_bars`

适合存放：

- `MarketStockZDNum`
- `ZhangTingExpression`
- `DailyLimitIndex`
- `WeightPerformance`
- `GetFengKListBest`

规则：

- 原始响应先标准化
- 再写入 section / item
- 不在这一层直接做 regime 判定

### 3.2 派生特征层

这一层保存由原始事实和 OHLCV 计算得到的特征。

落点：

- `market_regime_features`

适合存放：

- `benchmark_ohlcv_window`
- `ret_5d`
- `ret_20d`
- `ma20_gap`
- `ma60_gap`
- `vol_spike`
- `extreme_drop_count`
- `breadth_up_ratio`
- `breadth_down_ratio`
- `turnover_ratio`
- `gap_down_rate`
- `theme_concentration`

规则：

- 仅由 snapshot / ohlcv / 标准化事实计算
- 必须记录 `feature_version`
- 必须记录 `benchmark_symbol`
- 必须记录 `source_snapshot_id`

### 3.3 最终结论层

这一层保存最终 market regime 画像。

落点：

- `market_regimes`

适合存放：

- `primary_label`
- `labels`
- `confidence`
- `quality_status`
- `missing_reason`

规则：

- 只读 feature 层
- 不直接读 provider
- 不在 UI 中再计算

## 4. 接口到落表映射

| Kaipan 接口 | 归类 | 落表位置 | 说明 |
|---|---|---|---|
| `MarketStockZDNum` | 原始事实 | `market_snapshot_sections` / `market_snapshot_items` | 保存涨跌停总数等原始统计 |
| `ZhangTingExpression` | 原始事实 | `market_snapshot_sections` / `market_snapshot_items` | 保存涨停晋级、破板、连板结构 |
| `DailyLimitIndex` | 原始事实 | `market_snapshot_sections` / `market_snapshot_items` | 保存一板/二板/三板/高板结构 |
| `WeightPerformance` | 原始事实 | `market_snapshot_sections` / `market_snapshot_items` | 保存权重板块涨跌分布和热点集中度 |
| `GetFengKListBest` | 原始事实（增强） | `market_snapshot_sections` / `market_snapshot_items` | 保存全量强势标的，供后续增强使用 |

说明：

- 上述接口的结果应先标准化为 JSON 结构。
- 如果返回里存在数组，应尽量拆成 `items`，方便按 symbol / topic 查询。

## 5. 计算链路

### 5.1 抓取

Provider 拉取 Kaipan / 行情接口后，先落原始响应。

### 5.2 标准化

将原始响应转换为统一的 section/item 结构，写入现有 snapshot 表体系。

### 5.3 特征计算

`MarketRegimeFeatureService` 读取 snapshot 和 OHLCV，产出 feature 表。

### 5.4 Regime 计算

`MarketRegimeService` 读取 feature 表，产出 regime 表。

## 6. 推荐的新增字段

### 6.1 在现有表中建议保留的元数据

建议在 feature / regime 产物中统一保留：

- `benchmark_symbol`
- `feature_version`
- `regime_version`
- `source_snapshot_id`
- `source_section_version`
- `calculation_meta`

### 6.2 可选的 raw 审计表

如果后续需要保留完整抓取批次，可以新增一张通用表：

- `market_raw_payloads`

建议字段：

- `provider`
- `endpoint`
- `trade_date`
- `request_params`
- `response_status`
- `raw_payload_ref`
- `error_message`
- `created_at`

这张表只用于审计和排障，不参与 regime 计算主链路。

## 7. 实施顺序

1. 先把 10.5 的接口补到 provider 封装层。
2. 再写入现有 snapshot 表体系。
3. 再补 feature 计算和入库。
4. 再补 regime 计算和入库。
5. 如有必要，最后补 raw payload 审计表。

## 8. 验收标准

- 新 Kaipan 接口可以进入现有 Web 数据链路
- 原始事实、派生特征、最终结论三层分离
- UI 和 Backtest 只依赖标准化后的事实和最终结论
- 关键派生字段可复现、可回放、可版本化
- 不新增并行事实源
