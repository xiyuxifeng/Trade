# NW-V2-S2-006 Market Regime Feature Build Design

## 1. 背景

V2 阶段的市场数据链路已经具备 `Market Snapshot` 的结构化输入、DB 持久化和查询 API。当前缺的是一层**基于快照派生的市场状态特征**，用于后续 V3 的 `Regime-aware Backtest`、`Rule Applicability Profile` 和更细粒度的市场环境解释。

本任务的目标不是定义最终的 Market Regime，更不是做规则优化闭环；只是在 V2 中把 `market_regime_features` 生成、落库、可查询，并把产物以 artifact 形式保留下来。

## 2. 目标

1. 基于指定 `snapshot_id` 生成一份 `market_regime_features`。
2. 每个 feature 都要带上 `value`、`source_section`、`confidence`、`missing_reason`。
3. feature 结果要同时写入 DB 和结构化 artifact。
4. 支持按 `snapshot_id` / `trade_date` 查询。
5. 输出必须保持 V2 的交付型 Web 架构风格，不引入 CLI 新业务入口，不做 rule 选择，不做 backtest。

## 3. 非目标

1. 不定义最终的 `Market Regime` 决策结果。
2. 不做 rule 启用 / 禁用 / 排序。
3. 不做 backtest 逻辑。
4. 不在前端计算 regime feature。
5. 不把 regime 直接写死成不可扩展枚举。
6. 不新开一套与现有 `Market Snapshot` 平行的 snapshot 系统。

## 4. 推荐方案

### 4.1 总体方案

采用**单一派生表 + 统一服务 + 查询 API + artifact** 的方案：

1. `MarketSnapshotService` 仍负责生成 `Market Snapshot`。
2. 新增 `MarketRegimeFeatureService`，只消费已经落库的 `Market Snapshot`。
3. 新增 `market_regime_features` 表，保存每次 feature build 的结果。
4. 同步输出 JSON artifact，便于 Job Detail、Artifact Center 和后续 UI 复用。
5. 提供 snapshot-scoped 和 list-scoped 查询 API，供 `UI-V2-010` 直接消费。

### 4.2 为什么这样做

- 复用现有的 snapshot 数据，不重复抓取 provider。
- V2 只需要“解释型特征”，不需要 regime 决策器。
- 单表设计足够支撑查询、展示和后续 V3 读取。
- 结果既能走 DB，也能走 artifact，符合当前 Web 交付路径。

## 5. 数据模型

### 5.1 新增模型

新增 `src/models/market_regime.py`，建议包含以下结构：

#### `MarketRegimeFeature`

主表记录一份 feature build 结果，字段建议如下：

- `id`
- `snapshot_id`
- `trade_date`
- `market`
- `feature_version`
- `quality_status`
- `available_feature_count`
- `partial_feature_count`
- `missing_feature_count`
- `feature_payload_json`
- `summary_json`
- `storage_ref`

#### `MarketRegimeFeatureItem`

如果需要未来更细粒度查询，可以预留 item 表；但 V2 不是必须。当前建议先不拆 item 表，直接用 JSON 结构存 feature 明细。

### 5.2 Feature payload 结构

每个 feature 至少包含：

- `feature_key`
- `value`
- `source_section`
- `confidence`
- `missing_reason`

建议 feature keys 预留为：

- `trend`
- `sentiment`
- `liquidity`
- `volatility`
- `breadth`
- `theme_strength`
- `limit_up_count`
- `limit_down_count`
- `turnover_level`

### 5.3 表结构建议

新增表名建议为 `market_regime_features`，并加索引：

- `snapshot_id` 唯一或唯一组合索引
- `trade_date`
- `market`
- `feature_version`

推荐唯一约束：

- `uq_market_regime_features_snapshot_feature_version(snapshot_id, feature_version)`

这样既能保留版本化，又能保证同一快照的同版本结果唯一。

## 6. 派生逻辑

### 6.1 输入

输入只接受：

- `snapshot_id`
- 可选 `feature_version`
- 可选 `config_path` 或服务依赖注入上下文

feature service 从 DB 读取对应 `Market Snapshot` 及其 sections / items / quality report。

### 6.2 来源 section 约定

feature 计算只允许从已存在的 snapshot 结构化 section 中提取，不直接调用 provider。

推荐映射如下：

- `trend`
  - 来源：`market_state` / `overview`
  - 依据：趋势描述、均线方向、市场状态摘要
- `sentiment`
  - 来源：`overview`
  - 依据：市场情绪、上涨家数、强势股情况
- `liquidity`
  - 来源：`overview` / `capacity`
  - 依据：成交额、换手、资金活跃度
- `volatility`
  - 来源：`market_state`
  - 依据：波动等级、近期波动摘要
- `breadth`
  - 来源：`overview` / `sector_activity`
  - 依据：涨跌广度、板块扩散程度
- `theme_strength`
  - 来源：`hot_topics` / `topic_constituents`
  - 依据：热点数量、主题集中度、强主题延续性
- `limit_up_count`
  - 来源：`limit_up_down`
  - 依据：涨停数
- `limit_down_count`
  - 来源：`limit_up_down`
  - 依据：跌停数
- `turnover_level`
  - 来源：`overview` / `capacity`
  - 依据：成交额、换手、放量程度

### 6.3 partial 语义

如果某些输入 section 缺失，允许返回 partial features：

- 已能计算的 feature 保持 `value` 和 `confidence`
- 缺失的 feature 返回 `value = null`
- 每个缺失 feature 写入 `missing_reason`
- 整体 `quality_status` 标记为 `partial`

### 6.4 versioning

建议 feature version 从 `market-regime-features-v1` 起步。

V1 只承诺：

- feature key 集合稳定
- 结构稳定
- 不承诺具体打分公式稳定到未来版本

## 7. 服务设计

新增 `src/services/market_regime_feature_service.py`。

### 7.1 职责

1. 读取 `Market Snapshot` 主表、sections、items 和 quality report。
2. 生成 `market_regime_features` payload。
3. 将结果写入 DB。
4. 输出 JSON artifact。
5. 提供查询能力给 API / repository。

### 7.2 推荐接口

建议提供：

- `build_market_regime_features(snapshot_id, feature_version="market-regime-features-v1")`
- `get_feature_detail(snapshot_id, feature_version=None)`
- `list_features(trade_date=None, snapshot_id=None, market=None, limit=50, offset=0)`

### 7.3 结果语义

返回 `ServiceResult`，约定：

- `ok`：所有核心 feature 可计算
- `partial`：部分 feature 缺失，但仍生成结果
- `error`：找不到 snapshot、数据库异常、输入非法或无法生成任何结果

### 7.4 artifact 输出

建议输出到：

- `data/processed/market_regime_features/{trade_date}/{snapshot_id}/{feature_version}.json`

artifact 内容至少包含：

- `snapshot_id`
- `trade_date`
- `market`
- `feature_version`
- `quality_status`
- `features`
- `summary`
- `source_sections`

## 8. 存储和查询

### 8.1 Repository

新增仓储层，建议文件：

- `src/db/repositories/market_regime_feature_repository.py`

职责：

- 按 `snapshot_id + feature_version` upsert
- 按 `snapshot_id` 查询详情
- 按 `trade_date` / `market` 分页查询

### 8.2 API

建议补充市场 UI API：

- `GET /api/ui/v1/market/regime-features`
- `GET /api/ui/v1/market/snapshots/{snapshot_id}/regime-features`

返回结构建议包含：

- `feature`
- `page`
- `filters`
- `warnings`

这样 `UI-V2-010` 后续可以直接展示，不需要再绕 DB。

## 9. 错误处理

### 9.1 必须覆盖的状态

- `loading`
- `empty`
- `partial`
- `snapshot not found`
- `invalid query`
- `db error`

### 9.2 规则

1. snapshot 不存在时返回 `error`，类型为 `snapshot_not_found`。
2. 输入日期非法返回 `invalid_query`。
3. 部分 section 缺失时返回 `partial`，不直接失败。
4. DB 持久化失败时，若 artifact 已成功写出，结果仍可返回 `partial`，但要在 `warnings` 中保留错误原因。
5. 不允许把缺失数据伪装成完整特征。

## 10. 依赖与改动范围

### 10.1 允许修改

- `src/services/market_regime_feature_service.py`
- `src/models/market_regime.py`
- `src/db/repositories/market_regime_feature_repository.py`
- `src/services/__init__.py`
- `api/routers/ui/market.py`
- `api/schemas/market.py`
- `tests/unit/services/test_market_regime_feature_service.py`
- `tests/api/routers/test_market_ui.py`
- `docs/New-Web-Market-Regime-Features.md`

### 10.2 需要新增 migration

新增 `market_regime_features` 表的 migration。

### 10.3 不修改

- 不修改 provider interface
- 不修改 backtest schema
- 不修改 CLI 用户入口
- 不修改 UI 页面结构
- 不引入第二套 snapshot 体系

## 11. 验收标准

1. 可以对指定 `snapshot_id` 生成 regime features。
2. 缺失输入数据时返回 partial features 和 `missing_reason`。
3. regime features 可被 API 或 repository 查询。
4. regime feature 结果以 artifact 形式落盘。
5. V3 Backtest 可以通过 `snapshot_id` 读取这些 features。
6. 相关测试覆盖成功、部分缺失、查询和错误态。
7. TaskList 和 daily 记录同步。

## 12. 测试建议

### 12.1 单元测试

- feature 计算逻辑
- 缺失 section 的 partial 语义
- repository upsert / list / get

### 12.2 API 测试

- list endpoint
- detail endpoint
- 404 / 422 / 206 / 500 语义

### 12.3 回归点

- 现有 `Market Snapshot` 存储与查询链路不回归
- `UI-V2-010` 后续可以直接消费新 API

## 13. 推荐结论

这次 `NW-V2-S2-006` 的最佳实现方式是：

1. 用现有 `Market Snapshot` 作为唯一输入源。
2. 用一张 `market_regime_features` 主表保存结果。
3. 用 JSON 结构表达 feature 明细，避免过早拆复杂子表。
4. 通过 repository 和 API 暴露查询。
5. 保留 artifact 输出，方便后续 UI 和审计。

这能确保 V2 的目标是“面向最终交付的 Web 重构”，不是继续堆 demo 式推断逻辑。
