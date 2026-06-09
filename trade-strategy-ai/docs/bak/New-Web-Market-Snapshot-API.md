# New Web Market Snapshot API

本文档说明 `NW-V2-S2-005` 暴露的 Market Snapshot / Dataset 查询 API。

## 目标

- 为 Web UI 和外部系统提供稳定查询接口。
- 查询源以数据库为准，不读取文件作为主路径。
- 不暴露服务器绝对路径。
- 不引入新的 CLI surface。

## 端点

- `GET /api/ui/v1/market/snapshots`
- `GET /api/ui/v1/market/snapshots/{snapshot_id}`
- `GET /api/ui/v1/market/snapshots/{snapshot_id}/sections`
- `GET /api/ui/v1/market/snapshots/{snapshot_id}/sections/{section}`
- `GET /api/ui/v1/market/datasets`
- `GET /api/ui/v1/market/datasets/{dataset_id}`
- `GET /api/ui/v1/market/snapshots/{snapshot_id}/quality`

## 查询参数

### Snapshot 列表

支持：
- `trade_date`
- `market`
- `section`
- `symbol`
- `topic`
- `quality_status`
- `limit`
- `offset`

### Section 列表 / 详情

支持：
- `limit`
- `offset`
- `symbol`
- `topic`

### Dataset 列表 / 详情

支持：
- `trade_date`
- `market`
- `dataset_type`
- `quality_status`
- `limit`
- `offset`

## 返回形状

### Snapshot 列表

返回：
- `filters`
- `page`
- `items`

每个 snapshot item 至少包含：
- `snapshot_id`
- `trade_date`
- `market`
- `data_version`
- `quality_status`
- `created_at`
- `section_count`
- `available_section_count`
- `partial_section_count`
- `missing_section_count`
- `profile_id`

### Snapshot 详情

返回：
- `snapshot`
- `sections`
- `item_count`
- `quality_report`
- `dataset`
- `warnings`

### Section 详情

返回：
- `snapshot_id`
- `section`
- `page`
- `items`
- `filters`

### Dataset 详情

返回：
- `dataset`
- `snapshot`
- `page`
- `items`
- `warnings`

### Quality 报告

返回：
- `quality_report`

## 错误契约

统一结构化错误形状：

```json
{
  "type": "snapshot_not_found",
  "message": "snapshot not found",
  "detail": "snap-001",
  "metadata": {
    "snapshot_id": "snap-001"
  }
}
```

已定义错误类型：
- `invalid_query`
- `permission_denied`
- `snapshot_not_found`
- `dataset_not_found`
- `section_not_found`
- `quality_report_not_found`
- `api_unavailable`
- `empty_data`

## 兼容边界

- 只通过 repository / service 查询 DB。
- 不直接读取 Market Snapshot 文件作为主查询源。
- 不暴露绝对路径。
- 不返回 provider secret 或私有凭据。
- 不新增 CLI 命令。

## 验证

- `tests/unit/services/test_market_snapshot_query_service.py`
- `tests/api/routers/test_market_ui.py`
- `tests/api/test_ui_openapi_contract.py`
- `tests/api/test_api_app_factory.py`

