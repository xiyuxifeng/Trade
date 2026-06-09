# API Reference

> 说明：本文档以当前代码为准，统一整理单一 FastAPI app 的路由、功能、参数、鉴权和返回要点，方便后续按接口名快速查询。
>
> - 统一 app factory：`api/app.py`
> - 对外主入口：`api/main.py`
> - Swagger 在线文档：启动主入口后访问 `/docs`

## 1. 入口总览

### 1.1 统一 app

当前仓库只保留 `api/main.py` 作为对外 FastAPI 入口，所有路由都由 `api/app.py` 统一组装。

启动推荐：

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

用途：

- 盘前/盘后触发
- 日报/考核/策略版本/快照/排名/回测结果/告警等管理查询
- 文章、交易、市场数据查询与导出
- 日报、考核、persona route 查询
- 健康检查

## 2. 通用约定

- 日期格式：`YYYY-MM-DD`
- 分页参数：
  - `page` / `page_size`
  - 或 `skip` / `limit`
- 导出格式：
  - `csv`
  - `json`
  - `parquet`
  - 个别报告接口支持 `html`
- 路径解析：
  - 文档和配置里出现的 `config/...`、`data/...`、`logs/...` 相对路径，默认以 `trade-strategy-ai` 项目根目录为基准解析
  - 不依赖当前 shell 的工作目录
- 鉴权：
  - `X-API-Key` 由具体路由决定，入口本身不再决定鉴权语义
  - 需要内部鉴权的查询接口仍会在路由层显式要求 `X-API-Key`

## 3. `api/main.py` 路由

### 3.1 `GET /`

功能：

- 返回服务基本信息

参数：

- 无

返回要点：

- `service`
- `version`
- `docs`

### 3.2 `GET /health`

功能：

- 全局健康检查

参数：

- 无

返回要点：

```json
{ "status": "ok" }
```

### 3.3 `POST /run/pre_market`

功能：

- 触发盘前日报生成

请求体 `RunPreMarketRequest`：

- `as_of_date`：指定日期，默认今天
- `force`：强制重跑并覆盖输出，默认 `false`
- `export_html`：同时导出 HTML 日报，默认 `false`

返回要点 `RunPreMarketResponse`：

- `status`
- `as_of_date`
- `ideas_count`
- `output_dir`
- `html_path`
- `report`

### 3.4 `POST /run/after_close`

功能：

- 触发盘后考核生成

请求体 `RunAfterCloseRequest`：

- `as_of_date`：指定日期，默认今天
- `force`：强制重跑并覆盖输出，默认 `false`
- `export_html`：同时导出 HTML 考核报告，默认 `false`

返回要点 `RunAfterCloseResponse`：

- `status`
- `as_of_date`
- `evaluations_count`
- `output_dir`
- `html_path`
- `result`

### 3.5 `GET /run/health`

功能：

- `/run` 子系统健康检查

参数：

- 无

返回要点：

```json
{ "status": "ok", "service": "run" }
```

### 3.6 `GET /reports/daily`

功能：

- 日报列表查询

参数：

- `skip`：跳过条数，默认 `0`
- `limit`：返回数量限制，默认 `50`

返回要点：

- `status`
- `count`
- `total`
- `skip`
- `limit`
- `reports`

### 3.7 `GET /reports/daily/{date_str}`

功能：

- 查询指定日期的日报详情

路径参数：

- `date_str`：`YYYY-MM-DD`

返回要点：

- `status`
- `report`

### 3.8 `GET /reports/daily/{date_str}/html`

功能：

- 下载指定日期的日报 HTML

路径参数：

- `date_str`：`YYYY-MM-DD`

返回：

- `text/html`

### 3.9 `GET /reports/evaluation`

功能：

- 考核报告列表查询

参数：

- `skip`：跳过条数，默认 `0`
- `limit`：返回数量限制，默认 `50`

返回要点：

- `status`
- `count`
- `total`
- `skip`
- `limit`
- `reports`

### 3.10 `GET /reports/evaluation/{date_str}`

功能：

- 查询指定日期的考核报告详情

路径参数：

- `date_str`：`YYYY-MM-DD`

返回要点：

- `status`
- `result`

### 3.11 `GET /reports/evaluation/{date_str}/html`

功能：

- 下载指定日期的考核 HTML 报告

路径参数：

- `date_str`：`YYYY-MM-DD`

返回：

- `text/html`

### 3.12 `GET /strategy_versions/`

功能：

- 策略版本列表查询

参数：

- `trader_id`：交易员 ID
- `status`：版本状态
- `date_from`：开始日期 `YYYY-MM-DD`
- `date_to`：结束日期 `YYYY-MM-DD`
- `skip`：跳过条数，默认 `0`
- `limit`：返回数量限制，默认 `50`

返回要点：

- `status`
- `count`
- `total`
- `skip`
- `limit`
- `items`

### 3.13 `GET /strategy_versions/{version_id}`

功能：

- 获取单个策略版本详情

路径参数：

- `version_id`

返回要点：

- `status`
- `item`

### 3.14 `GET /strategy_versions/{version_id}/download`

功能：

- 下载单个策略版本 JSON

路径参数：

- `version_id`

返回：

- `application/json`

## 4. UI BFF 路由

### 4.1 `GET /api/ui/v1/system/status`

功能：

- 返回系统、数据库和关键目录状态

兼容：

- `GET /api/ui/system/status` 作为 legacy 别名保留

返回要点：

- `status`
- `config_path`
- `project_root`
- `run_mode`
- `database`
- `directories`
- `warnings`

### 4.2 `GET /api/ui/v1/jobs/definitions`

功能：

- 返回 Job 白名单定义

### 4.3 `GET /api/ui/v1/jobs/definitions/{job_type}`

功能：

- 返回单个 Job 定义

### 4.4 `POST /api/ui/v1/jobs`

功能：

- 创建一个新的 Job

### 4.5 `POST /api/ui/v1/jobs/validate`

功能：

- 校验 UI 提交的 Job 参数

### 4.6 `GET /api/ui/v1/jobs`

功能：

- 列出 Job

### 4.7 `GET /api/ui/v1/jobs/{job_id}`

功能：

- 返回单个 Job 详情

### 4.8 `GET /api/ui/v1/jobs/{job_id}/logs`

功能：

- 返回 Job 日志行

### 4.9 `GET /api/ui/v1/jobs/{job_id}/timeline`

功能：

- 返回 Job 时间线事件
- 当前读取 Job audit events，后续 `NW-V1-S2-002` 会切换为正式 Step Timeline 数据
- 返回空 `items` 时 UI 应显示 empty timeline 状态

返回要点：

- `job_id`
- `count`
- `items`

### 4.10 `GET /api/ui/v1/jobs/{job_id}/artifacts`

功能：

- 返回 Job 绑定的 artifact 引用
- 只返回 contract 中的安全 artifact 元数据，不返回服务器绝对路径

返回要点：

- `job_id`
- `count`
- `items`

### 4.11 `POST /api/ui/v1/jobs/{job_id}/cancel`

功能：

- 请求取消 Job

### 4.12 `GET /api/ui/v1/workflows`

功能：

- 列出 Workflow 定义

### 4.13 `GET /api/ui/v1/workflows/{workflow_id}`

功能：

- 返回单个 Workflow 定义

### 4.14 `POST /api/ui/v1/workflows/{workflow_id}/run`

功能：

- 运行 Workflow 并创建 Job

### 4.15 `GET /api/ui/v1/pipelines`

功能：

- 列出 Web UI 支持的 Pipeline
- V1 仅暴露 canonical `article_pipeline`
- `article_pipeline` 映射到 `WorkflowService` 中的 `pipeline` workflow，不直接执行 pipeline 内部函数

返回要点：

- `count`
- `items[].pipeline_id`
- `items[].workflow_id`
- `items[].job_type`
- `items[].title`
- `items[].description`

### 4.16 `GET /api/ui/v1/pipelines/article_pipeline`

功能：

- 返回 `article_pipeline` 的运行定义
- definition 来源于后端 Workflow / JobDefinition schema，供 UI schema-driven form 使用

返回要点：

- `pipeline.pipeline_id`
- `pipeline.workflow_id`
- `pipeline.workflow`
- `pipeline.workflow.job_definition.params_schema`

### 4.17 `POST /api/ui/v1/pipelines/article_pipeline/run`

功能：

- 通过 Workflow / Job 体系创建 `article_pipeline` Job
- 不在 API Router 中直接调用 pipeline/provider

请求体 `PipelineRunRequest`：

- `params`
- `created_by`
- `idempotency_key`
- `confirmed`

返回要点：

- `workflow`
- `job`

错误结构：

```json
{
  "detail": {
    "code": "pipeline_not_found",
    "message": "pipeline not found",
    "status": "not_found",
    "fields": {}
  }
}
```

### 4.18 `GET /api/ui/v1/artifacts`

功能：

- 列出主要产物并返回基础索引

### 4.19 `GET /api/ui/v1/artifacts/{artifact_id}`

功能：

- 返回单个产物的预览信息

### 4.20 `GET /api/ui/v1/artifacts/{artifact_id}/download`

功能：

- 下载单个产物文件

### 4.21 `GET /api/ui/v1/market/symbols`

功能：

- 返回行情标的列表

### 4.22 `GET /api/ui/v1/market/ohlcv`

功能：

- 按 symbol 和日期区间返回 K 线数据

### 3.15 `GET /snapshots/`

功能：

- MarketUniverse 快照列表查询

参数：

- `type`：快照类型，支持 `hot_topics` / `topic_constituents` / `strong_symbols` / `market_universe`
- `date`：交易日期 `YYYY-MM-DD`
- `skip`：跳过条数，默认 `0`
- `limit`：返回数量限制，默认 `50`

返回要点：

- `status`
- `count`
- `total`
- `skip`
- `limit`
- `items`

### 3.16 `GET /snapshots/{snapshot_id}`

功能：

- 获取单个快照详情

路径参数：

- `snapshot_id`，格式通常为 `{trade_date}_{slot}`

返回要点：

- `status`
- `item`

### 3.17 `GET /snapshots/{snapshot_id}/download`

功能：

- 下载快照 JSON

路径参数：

- `snapshot_id`

返回：

- `application/json`

### 3.18 `GET /rankings/`

功能：

- ranking 列表查询

参数：

- `trader_id`：交易员 ID
- `date_from`：开始日期 `YYYY-MM-DD`
- `date_to`：结束日期 `YYYY-MM-DD`
- `skip`：跳过条数，默认 `0`
- `limit`：返回数量限制，默认 `50`

返回要点：

- `status`
- `count`
- `total`
- `skip`
- `limit`
- `items`

### 3.19 `GET /rankings/{entry_id}`

功能：

- 获取单个 ranking 条目详情

路径参数：

- `entry_id`

返回要点：

- `status`
- `item`

### 3.20 `GET /rankings/{entry_id}/download`

功能：

- 下载 ranking JSON

路径参数：

- `entry_id`

返回：

- `application/json`

### 3.21 `GET /backtest_results/`

功能：

- 回测结果列表查询

参数：

- `trader_id`：交易员 ID
- `date_from`：开始日期 `YYYY-MM-DD`
- `date_to`：结束日期 `YYYY-MM-DD`
- `skip`：跳过条数，默认 `0`
- `limit`：返回数量限制，默认 `50`

返回要点：

- `status`
- `count`
- `total`
- `skip`
- `limit`
- `items`

### 3.22 `GET /backtest_results/{result_id}`

功能：

- 获取单个回测结果详情

路径参数：

- `result_id`

返回要点：

- `status`
- `item`

### 3.23 `GET /backtest_results/{result_id}/report`

功能：

- 下载回测 Markdown 报告

路径参数：

- `result_id`

返回：

- `text/markdown`

### 3.24 `GET /backtest_results/{result_id}/validate_rules`

功能：

- 下载规则验真 Markdown 报告

路径参数：

- `result_id`

返回：

- `text/markdown`

### 3.25 `GET /alerts/history`

功能：

- 告警历史分页查询

参数：

- `status`：状态过滤
- `level`：级别过滤
- `tag`：标签过滤
- `date_from`：开始日期 `YYYY-MM-DD`
- `date_to`：结束日期 `YYYY-MM-DD`
- `skip`：跳过条数，默认 `0`
- `limit`：返回数量限制，默认 `50`

返回要点：

- `count`
- `total`
- `items`

### 3.26 `GET /alerts/history/{record_id}`

功能：

- 查询单条告警详情

路径参数：

- `record_id`

返回要点：

- `AlertHistoryItem`

### 3.27 `POST /alerts/{record_id}/acknowledge`

功能：

- 确认告警

请求体 `AlertAcknowledgeRequest`：

- `acknowledged_by`：确认人，默认空

返回要点：

- `status`
- `id`
- `new_status`

### 3.28 `POST /alerts/{record_id}/resolve`

功能：

- 解决告警

请求体 `AlertResolveRequest`：

- `resolved_by`：解决人，默认空

返回要点：

- `status`
- `id`
- `new_status`

### 3.29 `POST /alerts/test`

功能：

- 发送测试告警，验证 Webhook 配置

请求体：

- 无

返回要点：

- `status`
- `message`

## 4. 说明

- `api/main.py` 是唯一对外运行入口，适合触发运行、查看产物、查看回测和告警。
- 所有 API 路由都由 `api/app.py` 统一组装，不再区分两个运行入口。
- 后续排查接口问题时，直接确认是否启动了 `api.main:app`。
