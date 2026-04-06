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
4. 查询源 DB 中所有 article.id 与 DuckDB articles 表中 max(id) 比较
5. 只查询 `id > max_id` 的新增/更新记录（JOIN blog_articles + article_metadata）
6. 写入 DuckDB（`INSERT OR REPLACE` 或 `DELETE + INSERT`）
7. 返回统计：新增条数、更新条数、耗时

## Pipeline 集成

`run_pipeline()` 新增 export 步骤：

```
crawl → clean → validate → store(SQLite/PG) → **export(DuckDB)**
```

`PipelineRunResult` 新增 `export: ExportStats` 字段。

## 实现文件
- `src/pipeline/tasks/export_task.py` — 核心导出逻辑
- `src/pipeline/dag.py` — 集成到 pipeline DAG
