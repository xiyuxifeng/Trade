# Market Regime Features

## 目标

`NW-V2-S2-006` 在 V2 阶段只做市场状态特征派生，不做 rule 优化闭环。

输入只来自已落库的 `Market Snapshot`，输出为：

- `market_regime_features` DB 记录
- JSON artifact
- 可查询 API

## 约定

- 不直接调用 provider
- 不在前端计算 feature
- 不定义最终 Market Regime 决策
- 不把 regime 固定成不可扩展枚举

## Feature Key

固定预留以下 feature key：

- `trend`
- `sentiment`
- `liquidity`
- `volatility`
- `breadth`
- `theme_strength`
- `limit_up_count`
- `limit_down_count`
- `turnover_level`

每个 feature 都包含：

- `value`
- `source_section`
- `confidence`
- `missing_reason`

## 存储

### DB

- 表名：`market_regime_features`
- 唯一约束：`(snapshot_id, feature_version)`
- 查询维度：`snapshot_id`、`trade_date`、`market`、`feature_version`

### Artifact

默认输出到：

```text
data/processed/market_regime_features/{trade_date}/{snapshot_id}/{feature_version}.json
```

artifact 内容包含：

- `snapshot_id`
- `trade_date`
- `market`
- `feature_version`
- `quality_status`
- `features`
- `summary`
- `source_sections`
- `warnings`

## API

### 列表

`GET /api/ui/v1/market/regime-features`

支持参数：

- `trade_date`
- `snapshot_id`
- `market`
- `feature_version`
- `limit`
- `offset`

### 详情

`GET /api/ui/v1/market/snapshots/{snapshot_id}/regime-features`

支持参数：

- `feature_version`

## 状态

- `ok`：核心 feature 都可计算
- `partial`：部分 feature 缺失，但结果仍可用
- `error`：snapshot 不存在、输入非法、数据库异常等
