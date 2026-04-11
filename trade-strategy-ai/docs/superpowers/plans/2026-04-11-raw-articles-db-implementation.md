# 原始数据数据库存储实现计划（2026-04-11）

## 1. 概述

根据设计文档 `2026-04-11-raw-articles-db-design.md`，本计划记录实现细节。

## 2. 已完成的实现

### 2.1 新增数据模型

- [x] `src/models/raw_article.py` - RawArticle 模型
- [x] `src/models/crawl_state.py` - CrawlState 模型
- [x] 更新 `src/models/__init__.py` 导出新模型

### 2.2 爬取逻辑改动

- [x] `src/agents/data_agent/skills/crawl_blog.py`
  - [x] 新增 `load_crawl_state_from_db()` - 从数据库加载增量状态
  - [x] 新增 `save_crawl_state_to_db()` - 保存增量状态到数据库
  - [x] 新增 `upsert_raw_article()` - 写入 raw_articles 表
  - [x] 新增 `crawl_source_to_db()` - 数据库模式爬取
  - [x] 新增 `run_crawl_to_db()` - 数据库模式入口
  - [x] 修改 `run_crawl()` 支持 `use_db` 参数

### 2.3 清洗逻辑改动

- [x] `src/pipeline/tasks/clean_task.py`
  - [x] 新增 `_clean_raw_articles_from_db()` - 从数据库读取并清洗
  - [x] 新增 `run_clean_from_db_task()` - 数据库清洗入口

### 2.4 Pipeline 改动

- [x] `src/pipeline/dag.py`
  - [x] 新增 `from_step` 参数支持
  - [x] 新增 `use_db` 参数支持
  - [x] `_should_skip()` 函数判断是否跳过步骤
  - [x] 各步骤的跳过处理

### 2.5 CLI 改动

- [x] `cli/main.py`
  - [x] `pipeline-run` 命令新增 `--from-step` 参数
  - [x] `pipeline-run` 命令新增 `--use-db` 参数
  - [x] 更新命令帮助文档

### 2.6 数据库迁移

- [x] 创建 `2026-04-11_0001_add_raw_articles_and_crawl_state_tables.py` migration
- [x] 执行 `python -m cli.main db-migrate` 成功创建表

### 2.7 文档更新

- [x] `docs/superpowers/specs/2026-04-11-raw-articles-db-design.md` - 设计文档
- [x] `docs/superpowers/specs/2026-04-11-from-step-design.md` - --from-step 和 --use-db 设计文档
- [x] `docs/superpowers/specs/2026-04-04-tgb-incremental-crawl-design.md` - 更新参考
- [x] `docs/crawl.md` - 更新架构说明和 --from-step、--use-db 使用说明
- [x] `docs/使用说明.md` - 添加 --from-step、--use-db 使用示例
- [x] `docs/TaskList.md` - 新增 P1-026K、P1-026L、P1-026M、P1-026N 任务

## 3. 待完成事项

### 3.1 数据迁移（可选）

将现有的 `articles.jsonl` 数据迁移到 `raw_articles` 表：

```python
# 待实现迁移脚本
```

## 4. 代码位置汇总

| 文件 | 改动类型 |
|------|---------|
| `src/models/raw_article.py` | 新增 |
| `src/models/crawl_state.py` | 新增 |
| `src/models/__init__.py` | 修改 |
| `src/agents/data_agent/skills/crawl_blog.py` | 修改 |
| `src/pipeline/tasks/clean_task.py` | 修改 |
| `src/pipeline/dag.py` | 修改 |
| `cli/main.py` | 修改 |
| `src/db/migrations/versions/2026-04-11_0001_add_raw_articles_and_crawl_state_tables.py` | 新增 |
