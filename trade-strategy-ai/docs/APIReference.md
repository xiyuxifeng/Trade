# API Reference

> 说明：本文档以当前代码为准，统一整理两套 FastAPI 入口的路由、功能、参数、鉴权和返回要点，方便后续按接口名快速查询。
>
> - 推荐管理入口：`api/main.py`
> - 推荐查询入口：`src/api/main.py`
> - Swagger 在线文档：各入口启动后访问 `/docs`

## 1. 入口总览

### 1.1 `api/main.py`

用途：

- 盘前/盘后触发
- 日报/考核/策略版本/快照/排名/回测结果/告警等管理查询

启动：

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 1.2 `src/api/main.py`

用途：

- 文章、交易、市场数据查询与导出
- 带 `X-API-Key` 的内部 API
- 日报、考核、persona route 查询
- 健康检查

启动：

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

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
- 鉴权：
  - `api/main.py` 当前主要是管理入口，代码里未统一强制 `X-API-Key`
  - `src/api/main.py` 的查询接口大多通过 `X-API-Key` 鉴权

## 3. `api/main.py` 路由

### 3.1 `GET /`

功能：

- 返回服务基本信息和主要 endpoint 索引

参数：

- 无

返回要点：

- `service`
- `version`
- `docs`
- `endpoints`

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

## 4. `src/api/main.py` 路由

### 4.1 `GET /`

功能：

- 返回服务基本信息

参数：

- 无

返回要点：

- `service`
- `version`
- `docs`

### 4.2 `GET /health`

功能：

- 健康检查

参数：

- 无

返回要点：

```json
{ "status": "ok" }
```

### 4.3 `GET /health/live`

功能：

- liveness probe，进程存活检查

参数：

- 无

返回要点：

- `status`

### 4.4 `GET /health/ready`

功能：

- readiness probe，检查数据库等关键依赖是否就绪

参数：

- 无

返回要点：

- `status`
- 依赖状态字段

### 4.5 `GET /health/detailed`

功能：

- 详细健康检查

参数：

- 无

返回要点：

- `status`
- `components`
- `metrics`

### 4.6 `GET /articles`

功能：

- 文章分页查询

鉴权：

- `X-API-Key`

参数：

- `page`：页码，默认 `1`
- `page_size`：每页数量，默认 `20`，最大 `100`
- `author_id`：作者 ID
- `source`：来源
- `trader_id`：交易员 ID
- `published_after`：发布时间下限
- `published_before`：发布时间上限

返回要点：

- `items`
- `total`
- `page`
- `page_size`
- `pages`

### 4.7 `GET /articles/export`

功能：

- 导出文章

鉴权：

- `X-API-Key`

参数：

- `format`：`csv` / `json` / `parquet`，默认 `csv`
- `author_id`
- `source`
- `published_after`
- `published_before`
- `trader_id`

返回：

- 文件下载

### 4.8 `GET /trades`

功能：

- 交易记录分页查询

鉴权：

- `X-API-Key`

参数：

- `page`：页码，默认 `1`
- `page_size`：每页数量，默认 `20`，最大 `100`
- `symbol`：标的代码
- `account_id`：账户 ID
- `side`：买卖方向
- `start_date`：开始时间
- `end_date`：结束时间
- `min_amount`：最小成交额
- `max_amount`：最大成交额

返回要点：

- `items`
- `total`
- `page`
- `page_size`
- `pages`

### 4.9 `GET /trades/export`

功能：

- 导出交易记录

鉴权：

- `X-API-Key`

参数：

- `format`：`csv` / `json` / `parquet`，默认 `csv`
- `symbol`
- `account_id`
- `side`
- `start_date`
- `end_date`
- `min_amount`
- `max_amount`

返回：

- 文件下载

### 4.10 `GET /market/latest`

功能：

- 查询某标的最新 OHLCV

鉴权：

- `X-API-Key`

参数：

- `symbol`：必填

返回要点：

- `symbol`
- `market`
- `timeframe`
- `traded_at`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `turnover`
- `source`

### 4.11 `GET /market/export`

功能：

- 导出 OHLCV 数据

鉴权：

- `X-API-Key`

参数：

- `format`：`csv` / `json` / `parquet`，默认 `csv`
- `symbol`：可选

返回：

- 文件下载

### 4.12 `GET /reports/daily/{as_of_date}`

功能：

- 查询指定日期日报

鉴权：

- `X-API-Key`

路径参数：

- `as_of_date`：`YYYY-MM-DD`

返回要点：

- `report_id`
- `as_of_date`
- `generated_at`
- `ideas`
- `highlights`
- `risks`

### 4.13 `GET /reports/daily`

功能：

- 日报列表查询

鉴权：

- `X-API-Key`

参数：

- `page`：页码，默认 `1`
- `page_size`：每页数量，默认 `10`，最大 `50`
- `start_date`：开始日期
- `end_date`：结束日期

返回要点：

- `items`
- `total`
- `page`
- `page_size`
- `pages`

### 4.14 `GET /reports/daily/{as_of_date}/export`

功能：

- 导出日报 JSON 或 HTML

鉴权：

- `X-API-Key`

参数：

- `format`：`json` / `html`，默认 `json`

返回：

- 文件下载

### 4.15 `GET /reports/evaluation/{as_of_date}`

功能：

- 查询指定日期考核结果

鉴权：

- `X-API-Key`

路径参数：

- `as_of_date`：`YYYY-MM-DD`

返回要点：

- `result_id`
- `as_of_date`
- `generated_at`
- `evaluations`
- `summary`

### 4.16 `GET /reports/evaluation`

功能：

- 考核结果列表查询

鉴权：

- `X-API-Key`

参数：

- `page`：页码，默认 `1`
- `page_size`：每页数量，默认 `10`，最大 `50`
- `start_date`：开始日期
- `end_date`：结束日期

返回要点：

- `items`
- `total`
- `page`
- `page_size`
- `pages`

### 4.17 `GET /reports/evaluation/{as_of_date}/export`

功能：

- 导出考核结果 JSON 或 HTML

鉴权：

- `X-API-Key`

参数：

- `format`：`json` / `html`，默认 `json`

返回：

- 文件下载

### 4.18 `GET /reports/persona-route/{as_of_date}`

功能：

- 查询某天的 persona routing 决策

鉴权：

- `X-API-Key`

路径参数：

- `as_of_date`：`YYYY-MM-DD`

返回要点：

- 原始 JSON 内容

### 4.19 `GET /reports/persona-route`

功能：

- persona routing 决策列表查询

鉴权：

- `X-API-Key`

参数：

- `page`：页码，默认 `1`
- `page_size`：每页数量，默认 `10`，最大 `50`
- `start_date`：开始日期
- `end_date`：结束日期

返回要点：

- `as_of_date`
- `clusters_path`
- `decisions_count`

### 4.20 `GET /reports/persona-route/{as_of_date}/export`

功能：

- 导出 persona routing JSON

鉴权：

- `X-API-Key`

路径参数：

- `as_of_date`：`YYYY-MM-DD`

返回：

- 文件下载

## 5. 说明

- `api/main.py` 更偏“业务管理入口”，适合触发运行、查看产物、查看回测和告警。
- `src/api/main.py` 更偏“数据查询入口”，适合给内部工具、页面和脚本调用。
- 这两套入口当前都保留在仓库中，因此后续排查接口问题时，先确认你启动的是哪一个 app。

