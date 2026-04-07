# DuckDB Export 设计

## 目标
将 SQLite/PostgreSQL 中的 `blog_articles` + `article_metadata` 增量导出到 DuckDB，供后续 OLAP 分析使用。

## 数据源
- **SQLite**: `data/trade_strategy_ai.db`（本地开发调试）
- **PostgreSQL**: `postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai`（生产）

## 输出
- DuckDB 数据库文件：`data/processed/duckdb/trade_strategy_ai.duckdb`
- 两张表：`articles` + `metadata`

## 表结构

### articles
| 字段 | DuckDB 类型 |
|------|------------|
| id | UUID |
| source | VARCHAR |
| source_article_id | VARCHAR |
| source_url | VARCHAR |
| title | VARCHAR |
| author_name | VARCHAR |
| author_id | VARCHAR |
| published_at | TIMESTAMP |
| crawled_at | TIMESTAMP |
| content_text | VARCHAR |
| content_html | VARCHAR |
| summary | VARCHAR |
| tags | JSON |
| view_count | BIGINT |
| like_count | BIGINT |
| bookmark_count | BIGINT |
| comment_count | BIGINT |
| comments_payload | JSON |
| raw_payload | JSON |
| content_hash | VARCHAR |

### metadata
| 字段 | DuckDB 类型 |
|------|------------|
| id | UUID |
| article_id | UUID |
| schema_version | VARCHAR |
| processed_at | TIMESTAMP |
| extracted_concepts | JSON |
| trading_symbols | JSON |
| strategy_rules | JSON |
| preconditions | JSON |
| comment_insights | JSON |
| raw_llm_output | JSON |
| sentiment_score | DOUBLE |
| confidence_score | DOUBLE |

## 导出逻辑（增量）

1. 连接源 DB（SQLite 或 PostgreSQL）
2. 连接/创建 DuckDB（如不存在则新建）
3. 确保 `articles` + `metadata` 表存在（如不存在则 CREATE TABLE）
4. 当前实现以 DuckDB 中 `articles.id` 的 max 值作为水位
5. 只查询 `id > max_id` 的新增记录（JOIN blog_articles + article_metadata）
6. 写入 DuckDB（`INSERT OR REPLACE` 或 `DELETE + INSERT`）
7. 返回统计：新增条数、更新条数、耗时

## Pipeline 集成

`run_pipeline()` 新增 export 步骤：

```
crawl → clean → validate → store(SQLite/PG) → **export(DuckDB)**
```

`PipelineRunResult` 新增 `export: ExportStats` 字段。

## 风险与后续

- 当前源表 `blog_articles.id` 为 `uuid4()`（随机、不可排序），因此 `id > max_id` 不能作为可靠的增量水位
- 后续应改为时间戳 watermark（`created_at` / `crawled_at` / `updated_at`）并持久化导出状态（DuckDB `export_state` 表或 pipeline state 文件）

## JSON 字段读写约定

### 写入约定
DuckDB 的 `JSON` 类型列接受 JSON 字符串。写入时 `_serialize_value()` 对 dict/list 调用 `json.dumps()` 转为字符串，因此：

- **写入时**：应用层 `json.dumps(dict/list)` → DuckDB `JSON` 列（底层存储为 TEXT）
- **DuckDB 自动验证**：写入值必须是合法 JSON，否则报错

### 读取约定（重要）

DuckDB `JSON` 列返回的是 **JSON 字符串**，需要应用层反序列化：

```python
import json
import duckdb

conn = duckdb.connect("data/processed/duckdb/trade_strategy_ai.duckdb")

# ❌ 错误：直接使用返回的字符串
tags = conn.execute("SELECT tags FROM articles LIMIT 1").fetchone()[0]
print(tags[0])  # TypeError 或 IndexError，取决于内容

# ✅ 正确：先 json.loads
tags = conn.execute("SELECT tags FROM articles LIMIT 1").fetchone()[0]
tags_list = json.loads(tags)
print(tags_list[0])
```

### json_extract 查询示例

对于需要查询 JSON 内部字段的场景，使用 `json_extract()` 或 `json_extract_path()`：

```sql
-- 查询 tags 数组第一个元素
SELECT json_extract(tags, '$[0]') FROM articles;

-- 查询 nested JSON 对象字段
SELECT json_extract(raw_payload, '$.author') FROM articles;

-- 查询 metadata 中的 trading_symbols 数组第1个
SELECT json_extract(trading_symbols, '$[0]') FROM metadata;

-- 查询 nested 深层字段
SELECT json_extract(raw_payload, '$.nested.deep.field') FROM articles;

-- 数组长度
SELECT json_array_length(tags) FROM articles;

-- 判断是否为合法 JSON
SELECT json_valid(tags) FROM articles;

-- 获取所有 JSON 对象键
SELECT json_keys(extracted_concepts) FROM metadata;
```

### Python 联合查询 + 反序列化

```python
import json
import duckdb

conn = duckdb.connect("data/processed/duckdb/trade_strategy_ai.duckdb")

rows = conn.execute("""
    SELECT
        a.id,
        a.title,
        a.tags,
        m.extracted_concepts,
        m.trading_symbols
    FROM articles a
    LEFT JOIN metadata m ON m.article_id = a.id
    LIMIT 10
""").fetchall()

for row in rows:
    article_id, title, tags_json, ec_json, ts_json = row
    tags = json.loads(tags_json) if tags_json else []
    concepts = json.loads(ec_json) if ec_json else []
    symbols = json.loads(ts_json) if ts_json else []
    print(f"{title}: {len(tags)} tags, {len(concepts)} concepts, {len(symbols)} symbols")
```

### 注意事项
- `json_extract()` 返回值也是 JSON 字符串，同样需要 `json.loads()`
- DuckDB 的 `JSON` 类型不等同于 PostgreSQL 的 JSONB（无二进制结构，无索引支持）
- 对于大量 JSON 查询，建议定期将常用字段提取为独立列

## 实现文件
- `src/pipeline/tasks/export_task.py` — 核心导出逻辑
- `src/pipeline/dag.py` — 集成到 pipeline DAG
