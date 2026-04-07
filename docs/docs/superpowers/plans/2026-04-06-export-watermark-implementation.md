# P1-026H: export_task 增量水位修复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 export_task 的增量水位从 UUID 比较改为 `crawled_at` 时间戳 watermark，状态持久化到 DuckDB `export_state` 表。

**Architecture:** 用 `crawled_at > watermark` 替代 `id > max_uuid`，watermark 存于 DuckDB 内建表 `export_state`，与 articles/metadata 同库同事务。

**Tech Stack:** Python async, DuckDB, SQLAlchemy, pytest

---

## 文件变更

| 操作 | 文件 |
|------|------|
| 修改 | `trade-strategy-ai/src/pipeline/tasks/export_task.py` |
| 创建 | `trade-strategy-ai/tests/unit/pipeline/test_export_task.py` |

---

## Task 1: 修改 `ExportStats` 数据类

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/export_task.py:37-43`

- [ ] **Step 1: 修改 `ExportStats` dataclass，添加 watermark_before 和 watermark_after 字段**

```python
@dataclass
class ExportStats:
    new_articles: int = 0
    new_metadata: int = 0
    skipped: int = 0
    duration_ms: int = 0
    watermark_before: datetime | None = None
    watermark_after: datetime | None = None
```

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/export_task.py
git commit -m "feat(export): add watermark_before/after to ExportStats"
```

---

## Task 2: 添加 `_ensure_export_state_table`

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/export_task.py`（在 `_ensure_tables` 函数后添加）

- [ ] **Step 1: 在 `_ensure_tables` 后添加 `_ensure_export_state_table` 函数**

```python
def _ensure_export_state_table(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS export_state (
            key VARCHAR PRIMARY KEY,
            watermark TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )
```

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/export_task.py
git commit -m "feat(export): add export_state table definition"
```

---

## Task 3: 实现 `_get_watermark` 函数

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/export_task.py`（在文件末尾 `_get_max_article_id` 位置后添加）

- [ ] **Step 1: 替换 `_get_max_article_id` 函数，改为 `_get_watermark`**

删除原函数：
```python
def _get_max_article_id(conn: duckdb.DuckDBPyConnection) -> str | None:
    result = conn.execute("SELECT MAX(id::VARCHAR) FROM articles").fetchone()
    if result and result[0]:
        return str(result[0])
    return None
```

替换为：
```python
WATERMARK_KEY = "articles_crawled_at"


def _get_watermark(conn: duckdb.DuckDBPyConnection) -> datetime | None:
    """Read the last exported crawled_at watermark from export_state."""
    result = conn.execute(
        "SELECT watermark FROM export_state WHERE key = ?",
        (WATERMARK_KEY,),
    ).fetchone()
    if result and result[0]:
        return datetime.fromisoformat(str(result[0]))
    return None


def _set_watermark(conn: duckdb.DuckDBPyConnection, watermark: datetime) -> None:
    """Update the export watermark in export_state (upsert)."""
    conn.execute(
        "INSERT OR REPLACE INTO export_state (key, watermark, updated_at) VALUES (?, ?, ?)",
        (WATERMARK_KEY, watermark.isoformat(), datetime.now().isoformat()),
    )
```

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/export_task.py
git commit -m "feat(export): replace _get_max_article_id with watermark functions"
```

---

## Task 4: 修改 `run_export_task` 核心逻辑

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/export_task.py`（重写 `run_export_task` 函数）

- [ ] **Step 1: 修改 `run_export_task`，使用 `crawled_at > watermark` + 事务**

删除原函数 `async def run_export_task(...)` 及全部内部实现（约第163-238行），替换为：

```python
async def run_export_task(
    *,
    duckdb_path: Path | None = None,
    force_full: bool = False,
) -> ExportResult:
    """Export articles + metadata from source DB to DuckDB.

    Incremental by default: exports articles with crawled_at > last_watermark.
    Use force_full=True to re-export everything (watermark reset).
    """
    import time

    start = time.monotonic()
    stats = ExportStats()
    dest = Path(duckdb_path) if duckdb_path else DUCKDB_PATH

    with _duckdb_conn(dest) as conn:
        _ensure_tables(conn)
        _ensure_export_state_table(conn)

        if force_full:
            watermark: datetime | None = None
        else:
            watermark = _get_watermark(conn)

        stats.watermark_before = watermark

        async with session_scope() as session:
            if watermark is None:
                stmt = (
                    select(BlogArticle, ArticleMetadata)
                    .outerjoin(ArticleMetadata, ArticleMetadata.article_id == BlogArticle.id)
                    .order_by(BlogArticle.crawled_at)
                )
            else:
                stmt = (
                    select(BlogArticle, ArticleMetadata)
                    .outerjoin(ArticleMetadata, ArticleMetadata.article_id == BlogArticle.id)
                    .where(BlogArticle.crawled_at > watermark)
                    .order_by(BlogArticle.crawled_at)
                )

            rows = await session.execute(stmt)
            all_rows = rows.all()

            if not all_rows:
                stats.duration_ms = int((time.monotonic() - start) * 1000)
                return ExportResult(stats=stats, duckdb_path=dest)

            # Collect existing article_ids in DuckDB for dedup
            existing_ids: set[str] = set()
            existing_ids = set(
                str(r[0]) for r in conn.execute("SELECT id::VARCHAR FROM articles").fetchall()
            )

            article_placeholders = ", ".join(["?"] * len(ARTICLES_COLUMNS))
            article_sql = f"INSERT OR REPLACE INTO articles ({', '.join(ARTICLES_COLUMNS)}) VALUES ({article_placeholders})"

            metadata_placeholders = ", ".join(["?"] * len(METADATA_COLUMNS))
            metadata_sql = f"INSERT OR REPLACE INTO metadata ({', '.join(METADATA_COLUMNS)}) VALUES ({metadata_placeholders})"

            max_crawled_at: datetime | None = None

            for article, meta in all_rows:
                article_id_str = str(article.id)

                if article_id_str in existing_ids:
                    stats.skipped += 1
                    continue

                conn.execute(article_sql, _serialize_article(article))
                stats.new_articles += 1

                if meta is not None:
                    conn.execute(metadata_sql, _serialize_metadata(meta))
                    stats.new_metadata += 1

                if max_crawled_at is None or article.crawled_at > max_crawled_at:
                    max_crawled_at = article.crawled_at

        # Update watermark in the same DuckDB connection (no explicit transaction needed —
        # autocommit per statement; using execute for atomicity)
        if max_crawled_at is not None:
            _set_watermark(conn, max_crawled_at)
            stats.watermark_after = max_crawled_at

    stats.duration_ms = int((time.monotonic() - start) * 1000)
    return ExportResult(stats=stats, duckdb_path=dest)
```

注意：移除 `import uuid`（不再需要 uuid.UUID 转换）。

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/export_task.py
git commit -m "feat(export): use crawled_at watermark instead of UUID comparison"
```

---

## Task 5: 清理不需要的 import

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/export_task.py`

- [ ] **Step 1: 移除未使用的 `import uuid`**

从文件顶部删除：
```python
import uuid
```

- [ ] **Step 2: Commit**

```bash
git add trade-strategy-ai/src/pipeline/tasks/export_task.py
git commit -m "chore(export): remove unused uuid import"
```

---

## Task 6: 编写单元测试

**Files:**
- Create: `trade-strategy-ai/tests/unit/pipeline/test_export_task.py`

- [ ] **Step 1: 写测试文件**

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile

import pytest

from src.pipeline.tasks.export_task import (
    ExportStats,
    ExportResult,
    _ensure_export_state_table,
    _get_watermark,
    _set_watermark,
    WATERMARK_KEY,
    run_export_task,
)


class TestWatermarkFunctions:
    def test_ensure_export_state_table_creates_table(self, tmp_path: Path) -> None:
        import duckdb
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))
        try:
            _ensure_export_state_table(conn)
            # Verify table exists
            result = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name = 'export_state'"
            ).fetchone()
            assert result is not None
        finally:
            conn.close()

    def test_get_watermark_returns_none_when_empty(self, tmp_path: Path) -> None:
        import duckdb
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))
        _ensure_export_state_table(conn)
        try:
            watermark = _get_watermark(conn)
            assert watermark is None
        finally:
            conn.close()

    def test_set_and_get_watermark(self, tmp_path: Path) -> None:
        import duckdb
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))
        _ensure_export_state_table(conn)
        try:
            ts = datetime(2026, 4, 6, 10, 0, 0, tzinfo=timezone.utc)
            _set_watermark(conn, ts)
            retrieved = _get_watermark(conn)
            assert retrieved is not None
            assert retrieved.year == 2026
            assert retrieved.month == 4
            assert retrieved.day == 6
        finally:
            conn.close()

    def test_watermark_key_is_correct(self) -> None:
        assert WATERMARK_KEY == "articles_crawled_at"


class TestExportStatsWatermarks:
    def test_export_stats_default_watermarks_none(self) -> None:
        stats = ExportStats()
        assert stats.watermark_before is None
        assert stats.watermark_after is None

    def test_export_stats_watermarks_settable(self) -> None:
        ts = datetime(2026, 4, 6, 10, 0, 0, tzinfo=timezone.utc)
        stats = ExportStats(watermark_before=ts, watermark_after=ts)
        assert stats.watermark_before == ts
        assert stats.watermark_after == ts
```

- [ ] **Step 2: 运行测试验证**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
pytest tests/unit/pipeline/test_export_task.py -v
```

期望：所有测试 PASS

- [ ] **Step 3: Commit**

```bash
git add trade-strategy-ai/tests/unit/pipeline/test_export_task.py
git commit -m "test(export): add unit tests for watermark functions"
```

---

## Task 7: 端到端验证

**Files:**
- None（运行验证）

- [ ] **Step 1: 验证 DuckDB 文件存在则备份，测试全量导出**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
cp data/processed/duckdb/trade_strategy_ai.duckdb data/processed/duckdb/trade_strategy_ai.duckdb.bak4 2>/dev/null || true
python -c "
import asyncio
from src.pipeline.tasks.export_task import run_export_task

async def test():
    result = await run_export_task(force_full=True)
    print(f'new_articles={result.stats.new_articles}')
    print(f'new_metadata={result.stats.new_metadata}')
    print(f'watermark_before={result.stats.watermark_before}')
    print(f'watermark_after={result.stats.watermark_after}')
    print(f'duration_ms={result.stats.duration_ms}')

asyncio.run(test())
"
```

- [ ] **Step 2: 验证增量导出（watermark_after 等于 watermark_before，无新增）**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
python -c "
import asyncio
from src.pipeline.tasks.export_task import run_export_task

async def test():
    result = await run_export_task(force_full=False)
    print(f'new_articles={result.stats.new_articles}')
    print(f'new_metadata={result.stats.new_metadata}')
    print(f'watermark_before={result.stats.watermark_before}')
    print(f'watermark_after={result.stats.watermark_after}')
    print(f'duration_ms={result.stats.duration_ms}')

asyncio.run(test())
"
```

期望：`new_articles=0, new_metadata=0`（无新文章），`watermark_before == watermark_after`

- [ ] **Step 3: 验证 DuckDB export_state 表数据**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
python -c "
import duckdb
conn = duckdb.connect('data/processed/duckdb/trade_strategy_ai.duckdb')
result = conn.execute('SELECT * FROM export_state').fetchall()
print('export_state rows:', result)
conn.close()
"
```

期望：1行，key='articles_crawled_at'，watermark 非空

- [ ] **Step 4: Commit 所有更改**

```bash
git add -A
git commit -m "feat(export): implement crawled_at watermark for incremental export"
```

---

## 依赖检查

实现本计划前，确认以下文件存在且可导入：
- `trade-strategy-ai/src/pipeline/tasks/export_task.py`（已存在）
- `trade-strategy-ai/src/models/blog_article.py`（已存在）
- `trade-strategy-ai/src/models/article_metadata.py`（已存在）
- `trade-strategy-ai/src/db/session.py`（已存在）

## 验收标准

1. `pytest tests/unit/pipeline/test_export_task.py -v` 全部 PASS
2. 全量导出后 `export_state` 表有 1 行 watermark
3. 增量导出（无新文章）返回 `new_articles=0, new_metadata=0`
4. `watermark_after` 正确记录本次导出最大 `crawled_at`
5. 原有 DuckDB 数据不变（INSERT OR REPLACE 幂等）
