# 文章查询接口 trader_id 过滤修复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `GET /articles` 和 `GET /articles/export` 接口的 `trader_id` 过滤失效问题。

**Architecture:** 新增 `_build_trader_id_condition` 辅助函数，在 `list_articles` 和 `export_articles` 中添加过滤逻辑。过滤基于 `raw_payload.trader_id` 和 `crawl.sources` 的 `author_id → trader_id` 映射。

**Tech Stack:** Python, SQLAlchemy, FastAPI

---

## 文件变更概览

| 文件 | 操作 |
|------|------|
| `src/api/routes/articles.py` | 修改：新增辅助函数，修改 `list_articles` 和 `export_articles` 过滤逻辑 |

---

## Task 1: 新增 `_build_trader_id_condition` 辅助函数

**Files:**
- Modify: `src/api/routes/articles.py`

- [ ] **Step 1: 在文件顶部添加必要的导入**

在 `from datetime import datetime` 后添加：

```python
from sqlalchemy import or_
```

- [ ] **Step 2: 在 `_articles_query_filters` 函数上方添加辅助函数**

在 `src/api/routes/articles.py` 第 21 行（`@router.get` 前）添加：

```python
def _build_trader_id_condition(trader_id: str | None, config: Any):
    """Build SQLAlchemy filter condition for trader_id.

    Logic:
    - If trader_id is None, return None (no filter)
    - First try raw_payload['trader_id'] match
    - Then fall back to author_id mapping via crawl.sources config
    """
    if not trader_id:
        return None

    from src.models.blog_article import BlogArticle

    # Build trader_id → author_ids mapping from crawl sources
    author_ids = []
    for src in config.crawl.sources:
        if src.author_id and src.trader_id == trader_id:
            author_ids.append(src.author_id)

    if author_ids:
        return or_(
            BlogArticle.raw_payload["trader_id"].astext == trader_id,
            BlogArticle.author_id.in_(author_ids),
        )
    else:
        return BlogArticle.raw_payload["trader_id"].astext == trader_id
```

---

## Task 2: 修改 `list_articles` 路由添加 trader_id 过滤

**Files:**
- Modify: `src/api/routes/articles.py:21-72`

- [ ] **Step 1: 在 `list_articles` 中添加 trader_id 过滤逻辑**

在 `src/api/routes/articles.py:36` 的 `query = select(BlogArticle)` 后、第一个 `if author_id:` 之前添加：

```python
        # Apply trader_id filter
        if trader_id:
            from src.common.config import load_app_config
            cfg = load_app_config("config/app.yaml").config
            condition = _build_trader_id_condition(trader_id, cfg)
            if condition is not None:
                query = query.where(condition)
                count_query = count_query.where(condition)
```

**注意：** 需要在文件顶部添加 `from src.common.config import load_app_config` 导入（如果还没有的话）。

---

## Task 3: 修改 `export_articles` 路由添加 trader_id 过滤

**Files:**
- Modify: `src/api/routes/articles.py:92-136`

- [ ] **Step 1: 在 `export_articles` 中添加 trader_id 参数**

`export_articles` 函数签名（第 94-99 行）当前没有 `trader_id` 参数。需要添加：

```python
@router.get("/export")
async def export_articles(
    format: str = Query(default="csv", pattern="^(csv|json|parquet)$"),
    author_id: str | None = None,
    source: str | None = None,
    published_after: datetime | None = None,
    published_before: datetime | None = None,
    trader_id: str | None = None,  # 新增
    _: str = Depends(verify_api_key),
):
```

- [ ] **Step 2: 在 `export_articles` 中添加 trader_id 过滤逻辑**

在 `src/api/routes/articles.py:103` 的 `query = select(BlogArticle)` 后、`query, count_query = _articles_query_filters(...)` 之前添加：

```python
        # Apply trader_id filter
        if trader_id:
            from src.common.config import load_app_config
            cfg = load_app_config("config/app.yaml").config
            condition = _build_trader_id_condition(trader_id, cfg)
            if condition is not None:
                query = query.where(condition)
                count_query = count_query.where(condition)
```

---

## Task 4: 验证

- [ ] **Step 1: 运行 Python 语法检查**

Run: `cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai && python -m py_compile src/api/routes/articles.py`
Expected: 无输出（编译成功）

- [ ] **Step 2: 检查导入是否正常**

Run: `cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai && python -c "from src.api.routes.articles import router; print('import ok')"`
Expected: `import ok`

- [ ] **Step 3: 确认 `trader_id` 参数已添加到 `export_articles`**

Run: `grep -n "trader_id: str | None = None" src/api/routes/articles.py`
Expected: 两处（第 27 行 list_articles，第 97 行 export_articles）

---

## 完成后

- 设计文档：`docs/superpowers/specs/2026-04-09-fix-articles-trader-id-filter-design.md`
- 计划文档：`docs/superpowers/plans/2026-04-09-fix-articles-trader-id-filter-plan.md`
