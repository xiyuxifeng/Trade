# 原始数据数据库存储设计（2026-04-11）

## 1. 目标

将 Crawl 阶段的原始数据从文件存储（`articles.jsonl`）改为直接写入 PostgreSQL 数据库，以支持：
- 增量抓取状态与原始数据的统一管理
- 简化流水线架构，消除中间产物的冗余存储
- 便于后续对原始数据进行查询和调试

## 2. 架构改动

### 2.1 新增数据模型

**RawArticle 表**（`src/models/raw_article.py`）：
- 存储爬取阶段的原始数据
- 对应原 `articles.jsonl` 的数据结构
- 包含 `is_processed` 标志，用于标记是否已被 clean 流程处理

**CrawlState 表**（`src/models/crawl_state.py`）：
- 替代原有的 `state.json` 文件
- 存储每个 (source, author_id) 的增量抓取状态
- 包括 `seen_urls`、`seen_hashes`、`last_seen_article_url` 等

### 2.2 流水线改动

**改动前**：
```
Crawl → articles.jsonl 文件 → Clean → .cleaned.jsonl → Validate → .validated.jsonl → Store
```

**改动后**：
```
Crawl → raw_articles 表（数据库）
         ↓
Clean → 从 raw_articles 读取 → .cleaned.jsonl → Validate → .validated.jsonl → Store
```

### 2.3 向后兼容

- `run_crawl` 函数新增 `use_db=False` 参数
- 当 `use_db=False`（默认）时，使用原有的文件模式
- 当 `use_db=True` 时，使用新的数据库模式
- 现有的 `articles.jsonl` 文件保留，可用于数据迁移

## 3. 数据库表结构

### 3.1 raw_articles 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| source | VARCHAR(50) | 来源标识 |
| site | VARCHAR(100) | 站点域名 |
| trader_id | VARCHAR(100) | 交易员ID |
| author_id | VARCHAR(128) | 作者ID |
| author_name | VARCHAR(100) | 作者名称 |
| source_url | VARCHAR(1024) | 文章URL（唯一） |
| source_article_id | VARCHAR(128) | 源站文章ID |
| title | VARCHAR(500) | 文章标题 |
| published_at | TIMESTAMP | 发布时间 |
| crawled_at | TIMESTAMP | 抓取时间 |
| content_text | TEXT | 正文文本 |
| content_html | TEXT | 正文HTML |
| content_hash | VARCHAR(64) | 内容哈希（SHA256） |
| comment_count | INT | 评论数 |
| comments | JSONB | 评论列表 |
| raw_payload | JSONB | 原始载荷 |
| is_processed | BOOLEAN | 是否已被处理 |
| processed_at | TIMESTAMP | 处理时间 |

**索引**：
- `ix_raw_articles_source_author` (source, author_id)
- `ix_raw_articles_crawled_at` (crawled_at)
- `ix_raw_articles_content_hash` (content_hash)
- `ix_raw_articles_is_processed` (is_processed)

### 3.2 crawl_state 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| source | VARCHAR(50) | 来源标识 |
| author_id | VARCHAR(128) | 作者ID |
| last_seen_article_url | TEXT | 最后看到的文章URL |
| last_seen_published_at | TIMESTAMP | 最后看到文章的发布时间 |
| seen_urls | TEXT[] | 已见URL列表 |
| seen_hashes | TEXT[] | 已见内容哈希列表 |
| last_success_article_count | INT | 最后成功抓取的文章数 |

**索引**：
- `ix_crawl_state_source_author` (source, author_id) - 唯一

## 4. 使用方式

### 4.1 数据库迁移

首次使用时需要执行数据库迁移：

```bash
python -m cli.main db-migrate --config config/app.yaml
```

### 4.2 使用数据库模式爬取

默认使用文件模式。如需使用数据库模式，需要在代码中设置 `use_db=True`：

```python
from src.agents.data_agent.skills.crawl_blog import run_crawl

# 使用数据库模式
results = run_crawl(config, base_dir=base_dir, use_db=True)
```

### 4.3 从数据库读取并清洗

```python
from src.pipeline.tasks.clean_task import run_clean_from_db_task

result = await run_clean_from_db_task(
    base_dir=base_dir,
    source="tgb",
    author_id="10461311",
    force=False
)
```

## 5. 增量抓取流程

### 5.1 数据库模式下的增量抓取

1. 爬取开始前，从 `crawl_state` 表加载 `seen_urls`、`seen_hashes`
2. 爬取过程中，遇到已见 URL 或已见哈希时立即停止
3. 爬取完成后，更新 `crawl_state` 表中的状态
4. 新爬取的文章写入 `raw_articles` 表

### 5.2 状态迁移

从文件模式迁移到数据库模式时：

1. 运行数据库迁移创建新表
2. 现有 `state.json` 中的状态会继续使用（文件模式）
3. 新爬取的数据可以选择写入数据库模式
4. 后续可以通过一次性迁移脚本将 `articles.jsonl` 导入 `raw_articles` 表

## 6. 代码位置

- 模型定义：`src/models/raw_article.py`、`src/models/crawl_state.py`
- 爬取逻辑：`src/agents/data_agent/skills/crawl_blog.py`
- 清洗逻辑：`src/pipeline/tasks/clean_task.py`
- 入口参数：`cli/main.py`、`src/pipeline/dag.py`

## 7. 风险与注意事项

- 数据库写入会增加爬取时间（约 5-10% 开销）
- 需要确保数据库连接可用
- 大量数据时需要关注数据库存储空间
- 建议定期清理已处理的 `raw_articles` 记录（`is_processed=True`）
