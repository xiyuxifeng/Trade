# P1-026H: export_task 增量水位修复设计

## 问题

当前 `export_task` 用 `MAX(articles.id)` 的 UUID 比较做增量水位。`BlogArticle.id` 是 UUID v4（随机生成），无法保证顺序，导致：
- **漏导出**：新文章 UUID 可能比历史最大值小
- **重复导出**：同一文章重新抓取后 UUID 不同

## 解法

用 `crawled_at`（文章入库时间）替代 UUID 比较作为增量水位，watermark 状态持久化到 DuckDB 内建表。

## 数据结构

### 新增 DuckDB 表 `export_state`

```sql
CREATE TABLE IF NOT EXISTS export_state (
    key VARCHAR PRIMARY KEY,
    watermark TIMESTAMP,
    updated_at TIMESTAMP
);
```

| 字段 | 类型 | 说明 |
|------|------|------|
| key | VARCHAR PRIMARY KEY | 导出键，如 `"articles_crawled_at"` |
| watermark | TIMESTAMP | 上次成功导出的最大 crawled_at |
| updated_at | TIMESTAMP | 行更新时间 |

### ExportStats 变更

新增 `watermark_before: datetime | None` 和 `watermark_after: datetime | None` 字段，便于问题追溯。

## 增量流程

```
1. 连接 DuckDB，确保 export_state + articles + metadata 表存在
2. force_full ?
   → 是：watermark = None（全量）
   → 否：读取 export_state WHERE key='articles_crawled_at' → watermark
3. 查询 blog_articles WHERE crawled_at > watermark ORDER BY crawled_at
   → LEFT JOIN article_metadata
4. INSERT OR REPLACE articles + metadata（DuckDB 内）
5. 记录 max(crawled_at) → 更新 export_state（同一事务内）
6. 返回 ExportStats
```

## 事务原子性

步骤 4+5 在同一 DuckDB 事务内，完成后 commit。中途失败则 rollback，watermark 不更新，下次重试不丢数据（INSERT OR REPLACE 幂等覆盖）。

## 失败处理

| 场景 | 行为 |
|------|------|
| 导出中途崩溃 | watermark 未更新，重试时重新导出已处理记录（幂等覆盖，无重复） |
| metadata 为 NULL | 文章仍导出（LEFT JOIN） |
| watermark 为 NULL | 等效 force_full |
| 文章无 metadata | 导出文章，metadata 跳过 |

## 验证

1. **增量无遗漏**：`crawled_at` 升序排列，连续两次增量导出无遗漏
2. **增量精准**：灌入新文章，增量导出只导出新文章
3. **全量重置**：`force_full=True` 导出后 watermark 重置

## 实现文件

- `trade-strategy-ai/src/pipeline/tasks/export_task.py` — 修改 `_get_max_article_id` → `_get_watermark` / `_set_watermark`，修改查询条件
- DuckDB 表结构：`_ensure_tables` 增加 `export_state` 表
