# P1-027 FastAPI 数据查询 API 设计方案

## 状态
- **日期**：2026-04-07
- **状态**：已批准，待实现
- **对应任务**：P1-027

## 目标
构建 FastAPI 查询接口，提供文章/交易/市场数据的查询和导出 API，支持内部工具 + 团队共享 + 前端对接。

## 需求摘要
- **场景**：内部工具 + 团队共享 + 前端（混合）
- **规模**：轻量，低并发，快速落地
- **查询**：灵活查询（过滤、分页、排序）
- **认证**：内部免认证，外部 API Key 认证
- **导出**：CSV/JSON/Parquet
- **数据**：文章 + 交易 + 市场三类数据

---

## 架构

```
src/api/
├── main.py              # FastAPI 应用入口
├── dependencies.py      # 认证依赖（API Key）
├── routes/
│   ├── __init__.py
│   ├── articles.py     # /articles 查询 + 导出
│   ├── trades.py       # /trades 查询 + 导出
│   └── market.py        # /market/latest 查询 + 导出
└── schemas/
    ├── __init__.py
    ├── common.py       # 分页、排序、过滤参数
    ├── article.py      # 文章 schemas
    ├── trade.py        # 交易 schemas
    └── market.py       # 市场数据 schemas
```

---

## 认证设计

### 公开端点（无需认证）
- `GET /health` — 健康检查

### 需认证端点
- `X-API-Key` Header 验证
- 配置于 `config/app.yaml` 的 `api.auth.api_keys`

```yaml
api:
  host: "0.0.0.0"
  port: 8000
  auth:
    enabled: true
    api_keys:
      - "internal-key-001"
```

---

## 查询接口

### GET /articles

**过滤参数：**
- `page` (int, default=1)
- `page_size` (int, default=20, max=100)
- `author_id` (str)
- `source` (str)
- `trader_id` (str)
- `published_after` (datetime)
- `published_before` (datetime)

**响应：**
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

---

### GET /trades

**过滤参数：**
- `page` (int, default=1)
- `page_size` (int, default=20, max=100)
- `symbol` (str)
- `account_id` (str)
- `side` (str, enum: buy/sell)
- `start_date` (date)
- `end_date` (date)
- `min_amount` (float)
- `max_amount` (float)

---

### GET /market/latest

**过滤参数：**
- `symbol` (str, required)
- `timeframe` (str, default="1d")
- `market` (str)

**响应：** 最新一条 OHLCV 数据

---

## 导出接口

### GET /articles/export
### GET /trades/export
### GET /market/export

**参数：**
- `format` (str, enum: csv/json/parquet, default=csv)
- 继承对应查询接口的过滤参数

**行为：** 返回文件下载响应

---

## 启动方式

```bash
uvicorn src.api.main:app --reload --port 8000
```

---

## 目录结构

```
src/api/
├── main.py              # FastAPI app + 路由注册
├── dependencies.py      # verify_api_key() 认证依赖
├── routes/
│   ├── __init__.py
│   ├── articles.py     # /articles 查询 + 导出
│   ├── trades.py       # /trades 查询 + 导出
│   └── market.py        # /market/latest 查询 + 导出
└── schemas/
    ├── __init__.py
    ├── common.py       # PaginationParams, SortParams
    ├── article.py      # ArticleResponse, ArticleFilter
    ├── trade.py        # TradeResponse, TradeFilter
    └── market.py       # MarketResponse, MarketFilter
```

---

## 依赖
- FastAPI（已依赖）
- Uvicorn（已依赖）
- Pydantic（已有）
- SQLAlchemy（已有）

---

## 待后续实现（Backlog）
- Webhook 告警推送（飞书/Slack/钉钉）
- 前端 Web 页面

---

## 验证
- `uvicorn src.api.main:app --reload` 启动无报错
- 各端点返回正确数据格式
- 导出接口生成正确格式文件
- API Key 认证正常工作
