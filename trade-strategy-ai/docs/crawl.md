# 数据爬取操作指南

## 概述

本文档说明如何使用本系统进行淘股吧文章的爬取、清洗、校验和入库全流程。

## 架构总览

```
┌──────────┐    ┌──────────┐    ┌────────────┐    ┌──────────┐
│  Crawl   │ →  │  Clean   │ →  │  Validate  │ →  │  Store   │
│ 爬取网络 │    │ 清洗JSONL │    │ 校验JSONL  │    │ 写入DB   │
└──────────┘    └──────────┘    └────────────┘    └──────────┘
     ↓               ↓                 ↓                ↓
 articles.jsonl  .cleaned.jsonl     .validated.jsonl   PostgreSQL
 (原始爬取)      (清洗后)            (校验+富化)        (最终入库)
```

**核心原则：原始数据可选择文件或数据库存储，逐步精炼。** Pipeline 支持两种模式：
- **文件模式（默认）**：Crawl → articles.jsonl → Clean → .cleaned.jsonl → Validate → .validated.jsonl → Store
- **数据库模式**：Crawl → raw_articles 表 → Clean → .cleaned.jsonl → Validate → .validated.jsonl → Store

优势：中间产物可复用、可断点续跑、方便调试回放。

---

## 前置条件

### 当前配置

配置文件: `config/app.yaml` 中已配置的爬取源：

| 项目 | 值 |
|------|-----|
| 作者 | `javxsp` |
| 作者 ID | `10461311` |
| 站点 | 淘股吧 (tgb.cn) |
| 列表页 URL | `https://www.tgb.cn/user/blog/moreTopic?userID=10461311` |
| Cookie | 通过环境变量 `${TGB_COOKIE}` 注入 |

### PostgreSQL 数据库

确保数据库已启动：

```bash
# 检查是否运行中
brew services list | grep postgresql

# 如果没运行，启动它
brew services start postgresql@15
```

### Python 虚拟环境

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
source ../.venv/bin/activate
```

如果虚拟环境不存在，需先创建（见 `docs/使用说明.md` 第3-16行）。

---

## 操作步骤（按顺序执行）

### 第 1 步：配置淘股吧 Cookie

**必须先获取 Cookie**，否则爬取会被拒绝（403/未登录态）。

#### 获取方法

1. 在浏览器登录 [淘股吧](https://www.tgb.cn)
2. 打开开发者工具 (F12) → `Network`
3. 刷新一个页面，选任意请求
4. 在 `Request Headers` 中复制 `Cookie` 整段内容

#### 注入方式（二选一）

**方式 A - 环境变量（推荐）：**

```bash
export TGB_COOKIE='你复制的完整 Cookie 内容'
```

**方式 B - 直接写入 `.env` 文件：**

编辑 `.env` 文件，取消 `TGB_COOKIE` 的注释并填入值：

```env
TGB_COOKIE=你的cookie内容
```

### 第 2 步：验证数据库连接与迁移（可选但建议）

```bash
# 验证连接
python -m cli.main db-check --config config/app.yaml

# 首次使用需要创建表结构
python -m cli.main db-migrate --config config/app.yaml
```

### 第 3 步：执行 Pipeline 一键爬取 + 清洗 + 入库

这是**核心命令**，按顺序自动完成全部步骤：`crawl → clean → validate → store → process → export`

```bash
python -m cli.main pipeline-run --config config/app.yaml
```

#### 常用参数

| 参数 | 说明 |
|------|------|
| `--max-articles N` | 限制每个作者最多抓取 N 篇文章（首次全量爬取可不加） |
| `--skip-crawl` | 跳过爬取，仅对已有 JSONL 执行后续 pipeline |
| `--force` | 强制重新处理 |
| `--from-step STEP` | 从指定步骤开始执行，可选值：crawl, clean, validate, store, process, export |
| `--use-db` | Crawl 阶段直接写入数据库（raw_articles 表），替代 articles.jsonl 文件 |

### 第 4 步：（可选）单独爬取命令

如果只想爬取、不跑完整 pipeline：

```bash
# 单独执行爬取（输出到 articles.jsonl）
python -m cli.main crawl --config config/app.yaml

# 限制每个作者最多抓取 10 篇
python -m cli.main crawl --config config/app.yaml --max-articles 10
```

> 注意：单独 crawl 只会生成 `articles.jsonl` 文件，**不会写入数据库**。要入库还是需要跑 `pipeline-run`。

---

## 增量爬取机制

增量爬取是**自动实现的**，无需额外参数。**直接重复运行 `pipeline-run` 命令即可实现增量爬取**，程序会自动跳过已有文章，只抓取新发布的文章。

### 状态持久化

每次爬取后在以下位置保存状态：

```
data/processed/crawl/tgb/10461311/state.json
```

保存内容：
- `seen_urls`: 已见过的文章 URL 集合
- `seen_hashes`: 已见过文章内容的 SHA256 哈希集合
- `last_seen_article_url`: 最后一次看到的文章 URL
- `last_seen_published_at`: 最后一篇文章的发布时间

### 停止条件（代码位置：`src/agents/data_agent/skills/crawl_blog.py:70-87`）

函数 `should_stop_incremental_scan()` 的判断逻辑：

1. 遇到 URL 已经在 `seen_urls` 中的文章 → **停止**
2. 遇到 content_hash 已经在 `seen_hashes` 中的文章 → **停止**
3. 文章发布时间 <= 上次最后看到的时间 → **停止**

---

## 各阶段详细说明

### 阶段 1: Crawl — 从网络爬取

**代码位置**: `src/agents/data_agent/skills/crawl_blog.py`
**CLI 入口**: `cli/crawl.py`
**Pipeline Task**: `src/pipeline/tasks/crawl_task.py`

**功能**:
- 通过 HTTP 请求从淘股吧获取作者的**文章列表**和每篇的**详情页**
- 同时抓取每篇文章的**评论列表**
- 对评论做初步分类过滤（低价值评论如"谢谢""666"等标记为 filtered）
- 计算 `content_hash`（SHA256）用于去重判断
- 输出原始 JSONL 到磁盘

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
  "comment_count": 15,
  "comments": [...],
  "raw_payload": { "list_item": {...}, "detail": {...} }
}
```

**状态文件**: 同目录下的 `state.json`（记录增量爬取断点）

**是否涉及数据库**: **否**，纯文件操作

---

### 阶段 2: Clean — 数据清洗

**代码位置**: `src/pipeline/tasks/clean_task.py`

**输入**: Crawl 阶段的 `articles.jsonl`
**输出**: `data/processed/pipeline/clean/{author_id}.articles.cleaned.jsonl`

**核心逻辑** (`clean_articles_jsonl` 函数):

| 步骤 | 说明 | 代码行 |
|------|------|--------|
| **去重**（可选） | 根据 `content_hash` + `source_url` 去重，移除重复文章 | 第 90~115 行 |
| **评论过滤** | 移除低价值评论（`is_filtered=True` 的，如"谢谢""666""点赞"等） | 第 124~127 行 |
| **字段归一化** | 将 `comments` 统一为 `comments_payload`，补充统计字段 | 第 129~137 行 |

**低价值评论定义** (`crawl_blog.py:15`):
```python
LOW_VALUE_COMMENTS = {"谢谢", "感谢", "打卡", "点赞", "666"}
# 以及长度 ≤ 2 的评论
```

**输出字段变化**:
- `comments` → 重命名为 `comments_payload`（仅保留非过滤评论）
- 新增 `comments_filtered_count`（被过滤的评论数）
- 新增 `comments_total_count`（评论总数）

**是否涉及数据库**: **否**，纯文件→文件转换

---

### 阶段 3: Validate — 数据校验

**代码位置**: `src/pipeline/tasks/validate_task.py`
**校验引擎**: `src/pipeline/validation.py`（`DataValidator` 类）

**输入**: Clean 阶段的 `.cleaned.jsonl`
**输出**: `data/processed/pipeline/validate/{原文件名}.validated.jsonl`

**核心逻辑** (`run_validate_task` 函数):

| 步骤 | 说明 | 代码行 |
|------|------|--------|
| **构建 ORM 对象** | 将 JSONL 记录转为 `BlogArticle` 模型实例（纯内存，不入库） | 第 106 行 |
| **数据校验** | 调用 `DataValidator.validate_article()` 做字段完整性/格式校验 | 第 107 行 |
| **严重度分级** | 问题分为 ERROR 和 WARNING 两级 | 第 119~122 行 |
| **可抽取判断** | 校验通过 且 content_text ≥ 80 字符 → 标记为可抽取 | 第 124 行 |
| **富化输出** | 追加 `validation` 和 `extractable` 字段 | 第 129~134 行 |

**输出字段变化**:
- 新增 `validation.is_valid`: 是否通过校验（bool）
- 新增 `validation.issues`: 校验问题列表（含 code / severity / message / field_name）
- 新增 `extractable`: 是否满足 LLM 抽取条件（bool）

**校验报告**: `data/processed/pipeline/validate/validation_report.json`

**是否涉及数据库**: **否**，纯文件→文件转换（ORM 对象仅用于内存校验）

---

### 阶段 4: Store — 写入数据库

**代码位置**: `src/agents/data_agent/skills/store_db.py`

**输入**: Validate 阶段的 `.validated.jsonl`
**输出**: **PostgreSQL 数据库**（BlogArticle 表 + ArticleMetadata 表）

**核心逻辑** (`store_articles_jsonl_to_db` 函数, 第 162~223 行):

逐条读取 validated JSONL，调用 `upsert_article_from_payload()` 执行 **UPSERT** 操作。

#### Upsert 详细流程 (`upsert_article_from_payload`, 第 106~146 行)

```
                    ┌─────────────────────┐
                    │ 读取 validated JSONL │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │ content_hash 冲突？  │──是──→ 不同URL？──是──→ 跳过（重复内容）
                    └──────────┬──────────┘          否         否
                               │ 否
                               ▼
                    ┌─────────────────────┐
                    │ source_url 已存在？   │──否──→ INSERT 新文章
                    └──────────┬──────────┘
                               │ 是
                               ▼
                    ┌─────────────────────┐
                    │ 字段有变化？          │──是──→ UPDATE 原地更新
                    └──────────┬──────────┘
                               │ 否
                               ▼
                            跳过（无变化）
```

具体规则：
1. 先查 `content_hash` 是否已存在且对应不同 URL → **跳过**（视为重复内容）
2. 再查 `source_url` 是否已存在 → 不存在则 **INSERT**
3. URL 已存在 → 逐字段比较，有变化则 **UPDATE**（原地更新），无变化则跳过

#### 额外操作

- **确保 Metadata**: 每篇文章自动确保 `article_metadata` 记录存在（第 200~201 行）
- **生成待办任务**: 新插入或更新的文章，自动生成 `AgentTask` 落盘到 `pending_tasks.jsonl`（第 204~222 行），用于后续触发 LLM 抽取/聚类

#### 统计指标 (`StoreStats`)

| 字段 | 说明 |
|------|------|
| `read_records` | 读取的总记录数 |
| `inserted_articles` | 新插入的文章数 |
| `updated_articles` | 更新的文章数 |
| `skipped_duplicates` | 因 content_hash 重复跳过的数量 |
| `ensured_metadata` | 确保的 metadata 记录数 |
| `generated_tasks` | 生成的待办任务数 |

---

## 各阶段对比总结

| 阶段 | 代码位置 | 输入来源 | 输出目标 | 是否涉及 DB |
|------|---------|---------|---------|------------|
| **Crawl** | `crawl_blog.py` | 网络 HTTP 请求 | `articles.jsonl` 文件 | 否 |
| **Clean** | `clean_task.py` | `articles.jsonl` | `.cleaned.jsonl` 文件 | 否 |
| **Validate** | `validate_task.py` | `.cleaned.jsonl` | `.validated.jsonl` 文件 | 否 |
| **Store** | `store_db.py` | `.validated.jsonl` | **PostgreSQL 数据库** | **是**（UPSERT） |

---

## 注意事项 / 风险点

| 项目 | 说明 |
|------|------|
| **Cookie 有效期** | 淘股吧 Cookie 可能过期，过期后会出现 403/429 错误，需重新获取 |
| **请求频率限制** | 配置了 1~2 秒随机间隔（`throttling.min_interval_seconds` / `max_interval_seconds`），避免被封 |
| **退避策略** | 出现 403/429 时按 `[5, 15, 30]` 秒序列重试（`throttling.backoff_seconds`） |
| **数据存储位置** | 原始 JSONL 存在 `data/processed/crawl/tgb/{author_id}/`，数据库为 PostgreSQL |
| **不要提交敏感信息** | 真实 Cookie / API Key 不要提交到代码仓库 |

---

## 推荐的最简操作序列

```bash
# 0) 确保 PostgreSQL 运行中
brew services start postgresql@15

# 1) 激活环境
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
source ../.venv/bin/activate

# 2) 设置 Cookie
export TGB_COOKIE='你的 cookie'

# 3) 数据库迁移（首次）
python -m cli.main db-migrate --config config/app.yaml

# 4) 一键爬取 + 入库（增量，可重复运行）
python -m cli.main pipeline-run --config config/app.yaml
```

**之后每天或定期重复第 4 步即可**，系统会自动增量爬取新文章并存入数据库。


## 不抓取直接入库

  最简单的方法：删缓存，让 pipeline 重新处理
  ```
  # 删掉 clean 和 validate 的缓存输出
  rm data/processed/pipeline/clean/10461311.articles.cleaned.jsonl
  rm data/processed/pipeline/validate/10461311.articles.cleaned.validated.jsonl

  # 重置 crawl 增量状态（这样 pipeline-run 会从头处理）
  rm data/processed/crawl/tgb/10461311/state.json

  # 跑 pipeline，用 --skip-crawl 跳过爬虫，直接用现有的 102 条数据
  python -m cli.main pipeline-run --config config/app.yaml --skip-crawl --force

  这样：
  articles.jsonl (102条)
    ↓ [clean, --force 重新处理]
  cleaned.jsonl (102条)
    ↓ [validate, --force 重新处理]
  validated.jsonl (102条)
    ↓ [store]
    → 写入数据库 102 条

  如果你连都不想删

  直接跑 Python 手动触发 store（绕过 clean/validate 缓存问题）：
  ```

## --from-step 参数详解

`--from-step` 参数允许从指定步骤开始执行 pipeline，跳过前面的步骤。

### 步骤顺序

```
crawl → clean → validate → store → process → export
```

### 使用示例

| 命令 | 说明 |
|------|------|
| `pipeline-run` | 从头开始跑完整流程 |
| `pipeline-run --from-step clean` | 跳过 crawl，从 clean 开始 |
| `pipeline-run --from-step validate` | 跳过 crawl 和 clean，从 validate 开始 |
| `pipeline-run --from-step store` | 跳过前三个步骤，只跑 store/process/export |
| `pipeline-run --from-step export` | 只导出数据到 DuckDB |

### 与 --force 配合使用

`--from-step` 通常与 `--force` 配合使用，以确保跳过的步骤使用最新的数据：

```bash
# 从 validate 开始，强制重跑 validate 及后续步骤
python -m cli.main pipeline-run --from-step validate --force

# 从 store 开始，只更新数据库
python -m cli.main pipeline-run --from-step store
```

### 注意事项

- `--from-step` 依赖已存在的中间产物文件（如 `.cleaned.jsonl`、`.validated.jsonl`）
- 如果跳过的步骤所需的输入文件不存在，会导致后续步骤失败
- `--skip-crawl` 和 `--from-step` 可以同时使用

## --use-db 参数详解

`--use-db` 参数让 Crawl 阶段直接将数据写入 PostgreSQL 数据库，而不是生成 `articles.jsonl` 文件。

### 架构对比

**默认模式（文件）**：
```
Crawl → articles.jsonl → Clean → .cleaned.jsonl → Validate → .validated.jsonl → Store
```

**数据库模式（--use-db）**：
```
Crawl → raw_articles 表 → Clean → .cleaned.jsonl → Validate → .validated.jsonl → Store
```

### 使用示例

```bash
# 使用数据库模式爬取
python -m cli.main pipeline-run --use-db

# 使用数据库模式 + 从 clean 开始
python -m cli.main pipeline-run --use-db --from-step clean
```

### 数据库表说明

使用 `--use-db` 时会涉及以下两张新表：

| 表名 | 说明 |
|------|------|
| `raw_articles` | 原始爬取数据，保留 `is_processed` 标志 |
| `crawl_state` | 增量抓取状态，替代 `state.json` |

### 迁移现有数据

现有数据不受影响。如果需要将现有的 `articles.jsonl` 数据迁移到 `raw_articles` 表，需要编写迁移脚本。

### 注意事项

- 数据库写入会增加约 5-10% 的爬取时间
- 需要确保 PostgreSQL 数据库可用
- `raw_articles` 表中的 `is_processed=False` 记录表示未被 clean 流程处理