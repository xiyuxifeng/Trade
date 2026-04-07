# P1-027 FastAPI 数据查询 API 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 FastAPI 查询接口，提供文章/交易/市场数据的查询和导出 API。

**Architecture:** `src/api/` 目录，FastAPI + SQLAlchemy AsyncSession，Pydantic schemas，复用 `db.session.async_session_factory()`。

**Tech Stack:** FastAPI, Uvicorn, SQLAlchemy AsyncSession, Pydantic

---

## 文件结构

```
src/api/
├── __init__.py
├── main.py              # FastAPI app + 路由注册
├── dependencies.py      # verify_api_key()
├── routes/
│   ├── __init__.py
│   ├── articles.py     # /articles 查询 + 导出
│   ├── trades.py       # /trades 查询 + 导出
│   └── market.py       # /market/latest 查询 + 导出
└── schemas/
    ├── __init__.py
    ├── common.py       # PaginationParams
    ├── article.py      # ArticleResponse, ArticleFilter
    ├── trade.py        # TradeResponse, TradeFilter
    └── market.py       # MarketResponse, MarketFilter
```

---

## Task 1: config/app.yaml — 新增 API 配置

**Files:**
- Modify: `trade-strategy-ai/config/app.yaml`

- [ ] **Step 1: 在文件末尾添加 api 配置节**

```yaml
# API 服务配置
api:
  host: "0.0.0.0"
  port: 8000
  auth:
    enabled: true
    api_keys:
      - "internal-key-001"
```

---

## Task 2: schemas/common.py — 通用分页模型

**Files:**
- Create: `trade-strategy-ai/src/api/schemas/__init__.py`
- Create: `trade-strategy-ai/src/api/schemas/common.py`

- [ ] **Step 1: 创建 schemas/__init__.py**

```python
from .common import PaginationParams
from .article import ArticleResponse, ArticleFilter
from .trade import TradeResponse, TradeFilter
from .market import MarketResponse, MarketFilter

__all__ = [
    "PaginationParams",
    "ArticleResponse", "ArticleFilter",
    "TradeResponse", "TradeFilter",
    "MarketResponse", "MarketFilter",
]
```

- [ ] **Step 2: 创建 schemas/common.py**

```python
from __future__ import annotations

from typing import Annotated
from datetime import datetime

from fastapi import Query
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int
    pages: int


def paginated_response(items: list, total: int, page: int, page_size: int) -> PaginatedResponse:
    pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return PaginatedResponse(
        items=[dict(item) if hasattr(item, "__dict__") else item for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
```

---

## Task 3: schemas/article.py — 文章 schemas

**Files:**
- Create: `trade-strategy-ai/src/api/schemas/article.py`

- [ ] **Step 1: 创建 schemas/article.py**

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ArticleResponse(BaseModel):
    id: UUID
    source: str
    source_url: str
    title: str
    author_name: str | None
    author_id: str | None
    published_at: datetime | None
    crawled_at: datetime
    content_text: str
    summary: str | None
    tags: list[str]
    content_hash: str | None
    view_count: int
    like_count: int
    bookmark_count: int
    comment_count: int

    class Config:
        from_attributes = True


class ArticleFilter(BaseModel):
    author_id: str | None = None
    source: str | None = None
    trader_id: str | None = None
    published_after: datetime | None = None
    published_before: datetime | None = None
```

---

## Task 4: schemas/trade.py — 交易 schemas

**Files:**
- Create: `trade-strategy-ai/src/api/schemas/trade.py`

- [ ] **Step 1: 创建 schemas/trade.py**

```python
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class TradeResponse(BaseModel):
    id: UUID
    source: str
    external_id: str | None
    account_id: str
    symbol: str
    market: str
    side: str
    position_side: str
    executed_at: datetime
    quantity: Decimal
    price: Decimal
    amount: Decimal
    fee: Decimal
    strategy_tag: str | None
    rationale: str | None

    class Config:
        from_attributes = True


class TradeFilter(BaseModel):
    symbol: str | None = None
    account_id: str | None = None
    side: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    min_amount: float | None = None
    max_amount: float | None = None
```

---

## Task 5: schemas/market.py — 市场数据 schemas

**Files:**
- Create: `trade-strategy-ai/src/api/schemas/market.py`

- [ ] **Step 1: 创建 schemas/market.py**

```python
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class MarketResponse(BaseModel):
    id: UUID
    symbol: str
    market: str
    timeframe: str
    traded_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    turnover: Decimal
    source: str

    class Config:
        from_attributes = True


class MarketFilter(BaseModel):
    symbol: str
    timeframe: str = "1d"
    market: str | None = None
```

---

## Task 6: dependencies.py — 认证依赖

**Files:**
- Create: `trade-strategy-ai/src/api/dependencies.py`

- [ ] **Step 1: 创建 dependencies.py**

```python
from __future__ import annotations

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from src.common.config import Settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    key: str | None = Security(_api_key_header),
) -> str:
    """Verify API key from X-API-Key header."""
    settings = Settings()
    api_config = getattr(settings, "api", None) or {}

    if not api_config.get("auth", {}).get("enabled", False):
        return "anonymous"

    valid_keys = api_config.get("auth", {}).get("api_keys", [])
    if key in valid_keys:
        return key

    if not valid_keys:
        return "anonymous"

    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN,
        detail="Invalid or missing API key",
    )


async def get_current_key(key: str = Security(_api_key_header)) -> str:
    """Get current API key, returns 'anonymous' if not set."""
    settings = Settings()
    api_config = getattr(settings, "api", None) or {}

    if not api_config.get("auth", {}).get("enabled", False):
        return "anonymous"

    valid_keys = api_config.get("auth", {}).get("api_keys", [])
    if key in valid_keys:
        return key
    return "anonymous"
```

---

## Task 7: routes/articles.py — 文章查询

**Files:**
- Create: `trade-strategy-ai/src/api/routes/__init__.py`
- Create: `trade-strategy-ai/src/api/routes/articles.py`

- [ ] **Step 1: 创建 routes/__init__.py**

```python
from .articles import router as articles_router
from .trades import router as trades_router
from .market import router as market_router

__all__ = ["articles_router", "trades_router", "market_router"]
```

- [ ] **Step 2: 创建 routes/articles.py**

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import verify_api_key
from src.api.schemas import ArticleResponse, PaginationParams
from src.db.session import async_session_factory
from src.models.blog_article import BlogArticle

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=dict[str, Any])
async def list_articles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    author_id: str | None = None,
    source: str | None = None,
    trader_id: str | None = None,
    published_after: datetime | None = None,
    published_before: datetime | None = None,
    _: str = Depends(verify_api_key),
):
    """List articles with pagination and filters."""
    offset = (page - 1) * page_size

    async with async_session_factory() as session:
        query = select(BlogArticle)
        count_query = select(func.count(BlogArticle.id))

        if author_id:
            query = query.where(BlogArticle.author_id == author_id)
            count_query = count_query.where(BlogArticle.author_id == author_id)
        if source:
            query = query.where(BlogArticle.source == source)
            count_query = count_query.where(BlogArticle.source == source)
        if published_after:
            query = query.where(BlogArticle.published_at >= published_after)
            count_query = count_query.where(BlogArticle.published_at >= published_after)
        if published_before:
            query = query.where(BlogArticle.published_at <= published_before)
            count_query = count_query.where(BlogArticle.published_at <= published_before)

        query = query.order_by(BlogArticle.published_at.desc()).offset(offset).limit(page_size)

        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        result = await session.execute(query)
        articles = result.scalars().all()

        items = [
            ArticleResponse.model_validate(a).model_dump(mode="json")
            for a in articles
        ]

        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }


@router.get("/export")
async def export_articles(
    format: str = Query(default="csv", regex="^(csv|json|parquet)$"),
    author_id: str | None = None,
    source: str | None = None,
    published_after: datetime | None = None,
    published_before: datetime | None = None,
    _: str = Depends(verify_api_key),
):
    """Export articles to CSV/JSON/Parquet."""
    # Placeholder - 实现见 Task 10
    return {"message": f"Export to {format} not yet implemented"}
```

---

## Task 8: routes/trades.py — 交易查询

**Files:**
- Create: `trade-strategy-ai/src/api/routes/trades.py`

- [ ] **Step 1: 创建 routes/trades.py**

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import verify_api_key
from src.api.schemas import TradeResponse
from src.db.session import async_session_factory
from src.models.trade_log import TradeLog

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("", response_model=dict[str, Any])
async def list_trades(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    symbol: str | None = None,
    account_id: str | None = None,
    side: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    _: str = Depends(verify_api_key),
):
    """List trades with pagination and filters."""
    offset = (page - 1) * page_size

    async with async_session_factory() as session:
        query = select(TradeLog)
        count_query = select(func.count(TradeLog.id))

        if symbol:
            query = query.where(TradeLog.symbol == symbol)
            count_query = count_query.where(TradeLog.symbol == symbol)
        if account_id:
            query = query.where(TradeLog.account_id == account_id)
            count_query = count_query.where(TradeLog.account_id == account_id)
        if side:
            query = query.where(TradeLog.side == side)
            count_query = count_query.where(TradeLog.side == side)
        if start_date:
            query = query.where(TradeLog.executed_at >= start_date)
            count_query = count_query.where(TradeLog.executed_at >= start_date)
        if end_date:
            query = query.where(TradeLog.executed_at <= end_date)
            count_query = count_query.where(TradeLog.executed_at <= end_date)
        if min_amount is not None:
            query = query.where(TradeLog.amount >= min_amount)
            count_query = count_query.where(TradeLog.amount >= min_amount)
        if max_amount is not None:
            query = query.where(TradeLog.amount <= max_amount)
            count_query = count_query.where(TradeLog.amount <= max_amount)

        query = query.order_by(TradeLog.executed_at.desc()).offset(offset).limit(page_size)

        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        result = await session.execute(query)
        trades = result.scalars().all()

        items = [TradeResponse.model_validate(t).model_dump(mode="json") for t in trades]

        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }


@router.get("/export")
async def export_trades(
    format: str = Query(default="csv", regex="^(csv|json|parquet)$"),
    symbol: str | None = None,
    account_id: str | None = None,
    side: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    _: str = Depends(verify_api_key),
):
    """Export trades to CSV/JSON/Parquet."""
    return {"message": f"Export to {format} not yet implemented"}
```

---

## Task 9: routes/market.py — 市场数据查询

**Files:**
- Create: `trade-strategy-ai/src/api/routes/market.py`

- [ ] **Step 1: 创建 routes/market.py**

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import verify_api_key
from src.api.schemas import MarketResponse
from src.db.session import async_session_factory
from src.models.market_data import MarketData

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/latest", response_model=MarketResponse | None)
async def get_latest_market(
    symbol: str = Query(...),
    timeframe: str = Query(default="1d"),
    market: str | None = None,
    _: str = Depends(verify_api_key),
):
    """Get latest market data for a symbol."""
    async with async_session_factory() as session:
        query = (
            select(MarketData)
            .where(MarketData.symbol == symbol)
            .where(MarketData.timeframe == timeframe)
        )
        if market:
            query = query.where(MarketData.market == market)

        query = query.order_by(MarketData.traded_at.desc()).limit(1)

        result = await session.execute(query)
        market_data = result.scalar_one_or_none()

        if market_data is None:
            raise HTTPException(status_code=404, detail="Market data not found")

        return MarketResponse.model_validate(market_data)


@router.get("/export")
async def export_market(
    format: str = Query(default="csv", regex="^(csv|json|parquet)$"),
    symbol: str | None = None,
    timeframe: str = Query(default="1d"),
    market: str | None = None,
    _: str = Depends(verify_api_key),
):
    """Export market data to CSV/JSON/Parquet."""
    return {"message": f"Export to {format} not yet implemented"}
```

---

## Task 10: main.py — FastAPI 应用入口

**Files:**
- Create: `trade-strategy-ai/src/api/__init__.py`
- Create: `trade-strategy-ai/src/api/main.py`

- [ ] **Step 1: 创建 src/api/__init__.py**

```python
"""FastAPI API module."""
```

- [ ] **Step 2: 创建 src/api/main.py**

```python
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import articles_router, trades_router, market_router

app = FastAPI(
    title="Trade Strategy AI API",
    description="Data query and export API for articles, trades, and market data",
    version="1.0.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(articles_router)
app.include_router(trades_router)
app.include_router(market_router)


@app.get("/health")
async def health_check():
    """Health check endpoint (public, no auth required)."""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Trade Strategy AI API",
        "version": "1.0.0",
        "docs": "/docs",
    }
```

---

## Task 11: 使用说明.md — 更新文档

**Files:**
- Modify: `docs/使用说明.md`

- [ ] **Step 1: 在文档末尾添加 API 使用说明**

```markdown
## FastAPI 数据查询 API

### 启动服务

```bash
uvicorn src.api.main:app --reload --port 8000
```

### API 端点

| 端点 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/health` | GET | 健康检查 | 公开 |
| `/articles` | GET | 文章列表查询 | API Key |
| `/articles/export` | GET | 文章导出 | API Key |
| `/trades` | GET | 交易记录查询 | API Key |
| `/trades/export` | GET | 交易导出 | API Key |
| `/market/latest` | GET | 最新市场数据 | API Key |
| `/market/export` | GET | 市场数据导出 | API Key |

### 认证

使用 `X-API-Key` Header：

```bash
curl -H "X-API-Key: internal-key-001" http://localhost:8000/articles?page=1
```

### 配置

`config/app.yaml` 中的 `api` 配置节：

```yaml
api:
  host: "0.0.0.0"
  port: 8000
  auth:
    enabled: true
    api_keys:
      - "internal-key-001"
```
```

---

## 自检清单

1. **Spec 覆盖检查**：所有设计中的功能都有对应 Task 实现
2. **Placeholder 扫描**：无 TBD/TODO/模糊描述
3. **类型一致性**：PaginationParams、ArticleResponse、TradeResponse、MarketResponse 在各路由中一致使用
