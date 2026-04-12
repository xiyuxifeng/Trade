# 数据爬取操作指南

## 概述

本文档说明如何使用本系统进行淘股吧文章的爬取、清洗、校验和入库全流程。

---

## 架构总览

### Pipeline 流程图（6 个步骤）

```
┌────────┐    ┌───────┐    ┌──────────┐    ┌────────┐    ┌─────────┐    ┌────────┐
│ Crawl  │ →  │ Clean │ →  │ Validate │ →  │ Store  │ →  │ Process │ →  │ Export │
└────────┘    └───────┘    └──────────┘    └────────┘    └─────────┘    └────────┘
     ↓            ↓             ↓              ↓              ↓              ↓
 articles.   .cleaned.     .validated.    PostgreSQL     pending_      trade_strategy.
 jsonl       jsonl         jsonl         blog_articles  tasks.jsonl   ai.duckdb
 (或raw_)                                  + article_md  + clusters
```

### 步骤依赖关系

| 步骤 | 输入 | 输出 | 是否涉及 DB |
|------|------|------|------------|
| **Crawl** | 无 | `articles.jsonl` 或 `raw_articles` 表 | 文件模式：否 / DB 模式：是 |
| **Clean** | `articles.jsonl` | `.cleaned.jsonl` | 否 |
| **Validate** | `.cleaned.jsonl` | `.validated.jsonl` | 否 |
| **Store** | `.validated.jsonl` | `blog_articles` 表 + `pending_tasks.jsonl` | 是 |
| **Process** | `pending_tasks.jsonl` | `article_metadata` 表 + `clusters.real.json` | 是 |
| **Export** | DB 数据 | `trade_strategy_ai.duckdb` | 是 |

---

## 前置条件

### 1. 配置文件

配置文件: `config/app.yaml` 中已配置的爬取源：

| 项目 | 值 |
|------|-----|
| 作者 | `javxsp` |
| 作者 ID | `10461311` |
| 站点 | 淘股吧 (tgb.cn) |
| 列表页 URL | `https://www.tgb.cn/user/blog/moreTopic?userID=10461311` |
| Cookie | 通过环境变量 `${TGB_COOKIE}` 注入 |

### 2. PostgreSQL 数据库

```bash
# 检查是否运行中
brew services list | grep postgresql

# 如果没运行，启动它
brew services start postgresql@15
```

### 3. Python 虚拟环境

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
source ../.venv/bin/activate
```

如果虚拟环境不存在，需先创建（见 `docs/使用说明.md`）。

### 4. 淘股吧 Cookie

**必须先获取 Cookie**，否则爬取会被拒绝（403/未登录态）。

获取方法：
1. 在浏览器登录 [淘股吧](https://www.tgb.cn)
2. 打开开发者工具 (F12) → `Network`
3. 刷新一个页面，选任意请求
4. 在 `Request Headers` 中复制 `Cookie` 整段内容

注入方式（二选一）：

**方式 A - 环境变量（推荐）：**
```bash
export TGB_COOKIE='你复制的完整 Cookie 内容'
```

**方式 B - 直接写入 `.env` 文件：**
```env
TGB_COOKIE=你的cookie内容
```

---

## 快速开始

### 首次运行

```bash
# 1) 数据库迁移（首次）
python -m cli.main db-migrate --config config/app.yaml

# 2) 一键爬取 + 清洗 + 入库
python -m cli.main pipeline-run --config config/app.yaml

# 3) 迁移 crawl-state 到数据库（首次）
python -m cli.main migrate-crawl-state --config config/app.yaml
```

### 日常运行

```bash
# 增量爬取（自动跳过已抓取的文章）
python -m cli.main pipeline-run --config config/app.yaml
```

---

## 命令参考

### pipeline-run — 一键执行全流程

按顺序自动完成全部步骤：`crawl → clean → validate → store → process → export`

```bash
python -m cli.main pipeline-run --config config/app.yaml
```

**常用参数：**

| 参数 | 说明 |
|------|------|
| `--max-articles N` | 限制处理的文章数量（crawl/clean/validate/store 步骤生效） |
| `--skip-crawl` | 跳过爬取，仅对已有 JSONL 执行后续 pipeline |
| `--force` | 强制重新处理（覆盖 clean/validate 产物） |
| `--from-step STEP` | 从指定步骤开始，可选：crawl, clean, validate, store, process, export |
| `--use-db` | Crawl 阶段直接写入 `raw_articles` 表（替代 `articles.jsonl`） |

**使用示例：**

```bash
# 从 validate 开始，强制重跑
python -m cli.main pipeline-run --from-step validate --force

# 跳过爬虫，直接处理已有文件
python -m cli.main pipeline-run --skip-crawl --force

# 数据库模式 + 从 store 开始
python -m cli.main pipeline-run --use-db --from-step store
```

---

### pipeline-step — 单独执行某一步骤

单独执行某个步骤，自动查找前置中间文件。如果前置文件不存在，会给出友好提示。

```bash
python -m cli.main pipeline-step <步骤名> [选项]
```

**可用步骤：**

| 步骤 | 说明 | 前置文件 |
|------|------|---------|
| `crawl` | 从网络爬取 | 无 |
| `clean` | 清洗 JSONL | `articles.jsonl` |
| `validate` | 校验并富化 | `.cleaned.jsonl` |
| `store` | 写入数据库 | `.validated.jsonl` |
| `process` | LLM 抽取 + 聚类 | `pending_tasks.jsonl` |
| `export` | 导出到 DuckDB | DB 数据 |

**常用示例：**

```bash
# 单独执行 clean
python -m cli.main pipeline-step clean

# 强制重跑 clean（覆盖已有）
python -m cli.main pipeline-step clean --force

# 单独执行 store
python -m cli.main pipeline-step store

# 强制重跑 process
python -m cli.main pipeline-step process --force

# 数据库模式爬取
python -m cli.main pipeline-step crawl --use-db

# 爬取最多 50 篇文章
python -m cli.main pipeline-step crawl --max-articles 50

# 清洗最多 100 篇（限制输入文件中的记录数）
python -m cli.main pipeline-step clean --max-articles 100 --force

# 验证最多 80 篇
python -m cli.main pipeline-step validate --max-articles 80

# 入库最多 50 篇
python -m cli.main pipeline-step store --max-articles 50
```

**通用参数：**

| 参数 | 说明 | 适用步骤 |
|------|------|---------|
| `--max-articles N` | 限制处理的文章数量 | `crawl`, `clean`, `validate`, `store` |
| `--force` | 强制重新执行（覆盖已有产物） | 所有步骤 |
| `--use-db` | 直接写入数据库（替代文件） | `crawl` |
| `--config` | 配置文件路径 | 所有步骤 |

**自动查找机制：**

| 当前步骤 | 向前查找的文件 |
|---------|---------------|
| `clean` | `data/processed/crawl/{source}/{author_id}/articles.jsonl` |
| `validate` | `data/processed/pipeline/clean/*.cleaned.jsonl` |
| `store` | `data/processed/pipeline/validate/*.validated.jsonl` |
| `process` | `data/processed/pipeline/pending_tasks.jsonl` |
| `export` | 直接读取数据库，无需文件 |

**缺少前置文件时的报错示例：**

```
$ python -m cli.main pipeline-step clean
未找到 articles.jsonl 文件。请先运行 'pipeline-step crawl' 或 'pipeline-run --from-step clean --skip-crawl'
```

**与 pipeline-run 的区别：**

| 特性 | `pipeline-run` | `pipeline-step` |
|------|---------------|-----------------|
| 执行范围 | 连续执行多个步骤 | 单独执行单个步骤 |
| 用途 | 日常增量运行 | 调试、修复、重跑特定步骤 |
| `--use-db` | 支持 | 仅 `crawl` 支持 |

---

### 其他命令

```bash
# 单独爬取（只生成 articles.jsonl，不入库）
python -m cli.main crawl --config config/app.yaml

# 数据库迁移
python -m cli.main db-migrate --config config/app.yaml

# 迁移 crawl-state 到数据库
python -m cli.main migrate-crawl-state --config config/app.yaml

# 备份数据
python -m cli.main backup-data --config config/app.yaml

# 恢复数据
python -m cli.main restore-data --config config/app.yaml --source ./my-backup --force
```

---

## 增量爬取机制

增量爬取是**自动实现的**，无需额外参数。直接重复运行 `pipeline-run` 命令即可。

### 状态存储

| 模式 | 文件 |
|------|------|
| 文件模式 | `data/processed/crawl/tgb/{author_id}/state.json` |
| 数据库模式 | `crawl_state` 表 |

### 状态内容

- `seen_urls`: 已见过的文章 URL 集合
- `seen_hashes`: 已见过文章内容的 SHA256 哈希集合
- `last_seen_article_url`: 最后一次抓取的文章 URL
- `last_seen_published_at`: 最后一篇文章的发布时间

### 增量逻辑

1. 检查 URL 是否在 `seen_urls` 中
2. 在 `seen_urls` 中 → **跳过**
3. 不在 `seen_urls` 中 → **抓取详情**，并加入 `seen_urls`
4. 直到列表遍历完毕

---

## 各阶段详细说明

### 阶段 1: Crawl — 从网络爬取

**代码位置**: `src/agents/data_agent/skills/crawl_blog.py` / `src/agents/data_agent/sites/tgb.py`

**输出文件**: `data/processed/crawl/tgb/{author_id}/articles.jsonl`

**输出字段示例**:

```json
{
  "source": "tgb",
  "site": "tgb.cn",
  "trader_id": "javxsp",
  "author_id": "10461311",
  "author_name": "javxsp",
  "source_url": "https://www.tgb.cn/article/xxxxx",
  "source_article_id": "xxxxx",
  "title": "文章标题",
  "published_at": "2026-04-09T10:00:00",
  "crawled_at": "2026-04-09T10:05:00+00:00",
  "content_text": "正文内容...",
  "content_html": "<p>正文HTML...</p>",
  "content_hash": "sha256哈希值",
  "topic_id": "7833368",
  "comment_count": 15,
  "comments": [...],
  "raw_payload": { "list_item": {...}, "detail": {...} }
}
```

#### 正文提取规则

优先使用精确的正文标签：
```python
soup.select_one(".article-text.p_coten#first")  # 最优先
    or soup.select_one("#first")
    or soup.select_one(".p_wenz")
    or soup.select_one(".p_coten")
    or soup.body  # 最终回退
```

#### 评论抓取规则

**URL 格式**：`https://www.tgb.cn/topic/lookUserTopic?topicID={topic_id}&lookUserID={author_id}`

- `topic_id`：从文章 HTML 的隐藏表单 `<input name="topicID" value='...'>` 中提取
- `lookUserID`：使用配置的 `author_id`
- **只抓取该作者发布的评论**，不抓取读者评论

**评论页数限制**：
- `max_comment_pages = None`（默认）：抓取全部评论
- `max_comment_pages = N`：最多抓取 N 页评论

#### TgbCrawler 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `auth_provider` | AuthProvider | - | 认证提供者（Cookie） |
| `list_url` | str | - | 列表页 base URL |
| `author_id` | str | - | 作者 ID |
| `source` | str | "tgb" | 来源标识 |
| `min_interval` | float | 1.0 | 请求最小间隔（秒） |
| `max_interval` | float | 2.0 | 请求最大间隔（秒） |
| `backoff_seconds` | tuple | (5, 15, 30) | 退避重试秒数 |
| `max_retries` | int | 3 | 最大重试次数 |
| `render_js` | bool | False | 是否启用 JS 渲染 |
| `render_timeout_ms` | int | 30000 | JS 渲染超时（毫秒） |
| `max_comment_pages` | int \| None | None | 评论最大页数（None=全部） |

---

### 阶段 2: Clean — 数据清洗

**代码位置**: `src/pipeline/tasks/clean_task.py`

**输入**: `articles.jsonl`
**输出**: `data/processed/pipeline/clean/{author_id}.articles.cleaned.jsonl`

| 步骤 | 说明 |
|------|------|
| **去重**（可选） | 根据 `content_hash` + `source_url` 去重 |
| **评论过滤** | 移除低价值评论（"谢谢""666""点赞"等）和纯图片评论 |
| **字段归一化** | `comments` → `comments_payload`，补充统计字段 |

**过滤规则**：
- `image_only`：纯图片评论（无文字内容）
- `low_value`：低价值评论（"谢谢""666""点赞"等，或长度 ≤ 2 字符）

**输出字段变化**:
- `comments` → `comments_payload`（仅保留非过滤评论）
- 新增 `comments_filtered_count`（被过滤的评论数）
- 新增 `comments_total_count`（评论总数）

---

### 阶段 3: Validate — 数据校验

**代码位置**: `src/pipeline/tasks/validate_task.py`

**输入**: `.cleaned.jsonl`
**输出**: `data/processed/pipeline/validate/{原文件名}.validated.jsonl`

| 步骤 | 说明 |
|------|------|
| **构建 ORM 对象** | 将 JSONL 记录转为 `BlogArticle` 模型实例（纯内存） |
| **数据校验** | 调用 `DataValidator.validate_article()` 做字段完整性/格式校验 |
| **可抽取判断** | content_text ≥ 80 字符 → 标记为可抽取 |
| **富化输出** | 追加 `validation` 和 `extractable` 字段 |

**输出字段变化**:
- 新增 `validation.is_valid`: 是否通过校验
- 新增 `validation.issues`: 校验问题列表
- 新增 `extractable`: 是否满足 LLM 抽取条件

**校验报告**: `data/processed/pipeline/validate/validation_report.json`

---

### 阶段 4: Store — 写入数据库

**代码位置**: `src/agents/data_agent/skills/store_db.py`

**输入**: `.validated.jsonl`
**输出**: PostgreSQL 数据库

#### Upsert 流程

```
读取 validated JSONL
        ↓
content_hash 冲突？ → 不同URL？ → 跳过（重复内容）
        ↓ 否
source_url 已存在？ → 否 → INSERT 新文章
        ↓ 是
字段有变化？ → 是 → UPDATE
        ↓ 否
    跳过（无变化）
```

#### 额外操作

- 每篇文章自动确保 `article_metadata` 记录存在
- 新插入或更新的文章，生成 `AgentTask` 落盘到 `pending_tasks.jsonl`

#### 统计指标

| 字段 | 说明 |
|------|------|
| `inserted_articles` | 新插入的文章数 |
| `updated_articles` | 更新的文章数 |
| `skipped_duplicates` | 因 content_hash 重复跳过的数量 |
| `generated_tasks` | 生成的待办任务数 |

---

### 阶段 5: Process — 任务处理

**代码位置**: `src/pipeline/tasks/process_tasks.py`

**输入**: `pending_tasks.jsonl`
**输出**: `article_metadata` 表 + `clusters.real.json`

#### 任务类型

| 任务类型 | 处理器 | 说明 |
|---------|--------|------|
| `article_ingested` | `extract_and_store_metadata()` | LLM 抽取文章元数据 |
| `article_metadata_extracted` | `build_clusters_from_db()` | 重建人物聚类 |

#### 失败任务处理

| 文件 | 说明 |
|------|------|
| `failed_tasks.jsonl` | 处理失败但未超过 TTL（可重试） |
| `dead_tasks.jsonl` | 超过 TTL 或重试次数上限（永久失败） |

---

### 阶段 6: Export — 导出 DuckDB

**输出**: `data/processed/duckdb/trade_strategy_ai.duckdb`

用于后续数据分析。

---

## 两种运行模式

| 模式 | 命令 | Crawl 输出 | 适用场景 |
|------|------|-----------|---------|
| **文件模式（默认）** | `pipeline-step crawl` | `articles.jsonl` | 调试、中间产物复用 |
| **数据库模式** | `pipeline-step crawl --use-db` | `raw_articles` 表 | 生产环境、跨设备迁移 |

---

## 备份与恢复

### 备份

```bash
# 备份到自动生成的目录
python -m cli.main backup-data --config config/app.yaml

# 备份到指定目录
python -m cli.main backup-data --config config/app.yaml --dest ./my-backup

# 仅备份数据库
python -m cli.main backup-data --config config/app.yaml --no-include-processed
```

### 恢复

```bash
python -m cli.main restore-data --config config/app.yaml --source ./my-backup --force
```

### 跨设备迁移

1. **设备 A**：`python -m cli.main backup-data --dest ./trade-backup`
2. 拷贝到设备 B
3. **设备 B**：`python -m cli.main restore-data --source ./trade-backup --force`

---

## 注意事项

| 项目 | 说明 |
|------|------|
| **Cookie 有效期** | 淘股吧 Cookie 可能过期，过期后会出现 403/429 错误，需重新获取 |
| **请求频率限制** | 配置了 1~2 秒随机间隔，避免被封 |
| **退避策略** | 出现 403/429 时按 `[5, 15, 30]` 秒序列重试 |
| **敏感信息** | 真实 Cookie / API Key 不要提交到代码仓库 |
