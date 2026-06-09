# Fix: 文章查询接口 trader_id 过滤失效

> 日期：2026-04-09
> 问题来源：`docs/issues.md` 中优先级问题 3

## 目标

修复 `GET /articles` 和 `GET /articles/export` 接口声明支持 `trader_id` 过滤但实现中完全未生效的问题。

## 问题根因

- `list_articles` 和 `export_articles` 都声明了 `trader_id` 参数，但未使用
- `_articles_query_filters` 函数不接受 `trader_id` 参数
- `BlogArticle` 模型没有直接的 `trader_id` 字段，需要通过两个途径推断

## 过滤逻辑

`trader_id` 过滤基于两个数据来源（优先级从高到低）：

### 途径 A：raw_payload JSON 字段
`BlogArticle.raw_payload` 中存储了 `trader_id`，直接过滤：
```python
BlogArticle.raw_payload["trader_id"].astext == trader_id
```

### 途径 B：crawl.sources 配置映射
通过 `crawl.sources` 配置中的 `author_id → trader_id` 映射关系过滤：
```python
BlogArticle.author_id.in_(author_ids_for_trader)
```

### 组合条件
```python
from sqlalchemy import or_

# 构建 trader_id → author_ids 映射
trader_to_authors = {src.trader_id: src.author_id for src in config.crawl.sources if src.author_id}
author_ids_for_trader = trader_to_authors.get(trader_id, [])

# 组合条件
if author_ids_for_trader:
    condition = or_(
        BlogArticle.raw_payload["trader_id"].astext == trader_id,
        BlogArticle.author_id.in_(author_ids_for_trader)
    )
else:
    condition = BlogArticle.raw_payload["trader_id"].astext == trader_id
```

## 实现方案

### 1. 新增辅助函数 `_build_trader_id_condition`

```python
def _build_trader_id_condition(trader_id: str | None, config: AppConfig):
    """Build SQLAlchemy filter condition for trader_id.

    Logic:
    - If trader_id is None, return None (no filter)
    - First try raw_payload['trader_id'] match
    - Then fall back to author_id mapping via crawl.sources config
    """
    if not trader_id:
        return None

    from sqlalchemy import or_
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

### 2. 修改 `_articles_query_filters` 函数签名

```python
def _articles_query_filters(
    query,
    count_query,
    author_id,
    source,
    published_after,
    published_before,
    trader_id: str | None = None,
    config: AppConfig | None = None,  # 新增参数
):
    """Apply filters to article query."""
    # ... existing filters ...

    # trader_id filter
    if trader_id and config:
        condition = _build_trader_id_condition(trader_id, config)
        if condition is not None:
            query = query.where(condition)
            count_query = count_query.where(condition)

    return query, count_query
```

### 3. 修改 `list_articles` 路由

```python
@router.get("", response_model=dict[str, Any])
async def list_articles(
    # ... existing params ...
    trader_id: str | None = None,
    _: str = Depends(verify_api_key),
):
    # ... setup ...
    from src.common.config import load_app_config

    config = load_app_config("config/app.yaml").config

    query = select(BlogArticle)
    count_query = select(func.count(BlogArticle.id))

    # Apply existing filters...

    # Apply trader_id filter
    if trader_id:
        condition = _build_trader_id_condition(trader_id, config)
        if condition is not None:
            query = query.where(condition)
            count_query = count_query.where(condition)
```

### 4. 修改 `export_articles` 路由

同样添加 `trader_id` 过滤支持，需要传入 `config`。

## 涉及文件

- `src/api/routes/articles.py`：
  - 新增 `_build_trader_id_condition` 辅助函数
  - 修改 `_articles_query_filters` 增加 `trader_id` 和 `config` 参数
  - 修改 `list_articles` 路由，添加 `trader_id` 过滤逻辑
  - 修改 `export_articles` 路由，添加 `trader_id` 过滤逻辑

## 验证点

1. `GET /articles?trader_id=xxx` 返回只包含该 trader 的文章
2. `GET /articles/export?trader_id=xxx` 导出只包含该 trader 的文章
3. 不传 `trader_id` 时返回所有文章（向后兼容）
4. 当 `author_id` 映射和 `raw_payload.trader_id` 同时存在时，两个条件用 OR 组合
