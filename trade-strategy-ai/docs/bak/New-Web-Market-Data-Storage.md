# New Web Market Data DB Storage

本文档说明 `NW-V2-S2-004` 的数据库存储结构、写入链路和兼容边界。

## 目标

- 市场数据从文件为主事实源，收敛为数据库为主查询源。
- 文件继续保留为导出、调试、归档和备份产物。
- 不新增产品级 CLI 命令。
- 不在 Web Router 中拼接 SQL。

## 表结构

### `market_snapshots`
快照主表，保存 `snapshot_id`、`trade_date`、`market`、`profile_id`、`data_version`、`quality_status`、`provider_sources`、摘要计数和安全引用。

### `market_snapshot_sections`
section 摘要表，保存 `snapshot_id`、`section_id`、`provider`、`source_time`、`record_count`、`missing_reason`、`quality_status`、`payload_json`。

### `market_snapshot_items`
明细表，保存 `snapshot_id`、`section_id`、`dataset_id`、`symbol`、`item_key`、`item_type`、`source_time`、`quality_status`、`payload_json`。

### `market_datasets`
统一数据集事实源，保存 `dataset_id`、`dataset_type`、`trade_date`、`market`、`snapshot_id`、`profile_id`、`quality_status`、`storage_ref`。

### `market_data_quality_reports`
质量报告表，保存 `snapshot_id`、`overall_status`、`warning_count`、`error_count`、`section_summary_json`、`report_json`、`storage_ref`。

## 写入链路

1. `snapshot-build` 生成结构化 `MarketSnapshot`。
2. `MarketSnapshotService` 写出 `snapshot.json`、`snapshot.summary.json`、`snapshot.quality.json`。
3. `MarketDataStorageService` 把 snapshot 拆成主表、section、item、dataset 和 quality report。
4. `JobRunner` 继续绑定安全 artifact 元数据。

## 查询路径

Repository 层支持按以下维度查询：

- `snapshot_id`
- `trade_date`
- `symbol`
- `section`
- `dataset_id`

主查询字段通过列和索引完成，`payload_json` 只用于扩展明细，不作为主查询入口。

## 兼容边界

保留：

- 文件导出
- artifact 下载
- 旧 debug 读取路径

退役：

- 文件作为主查询源
- 新 CLI 产品入口
- 对外暴露绝对路径

## 验证

- 模型测试：`tests/unit/models/test_market_data_snapshot_models.py`
- Repository 测试：`tests/unit/db/repositories/test_market_data_repositories.py`
- Storage Service 测试：`tests/unit/services/test_market_data_storage_service.py`
- 编排回归：`tests/unit/services/test_market_snapshot_service.py`

