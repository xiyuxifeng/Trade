# S7-003b Implementation Plan: 候选版本 DB 链路

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `optimize create-candidate` 添加 DB 持久化链路，与现有文件链路并存。

**Architecture:** 在 `trader_strategy_versions` 表新增 `version_type` + `parent_version_id` 独立列；更新 Repository ORM 映射；CLI 新增 `--db` 参数切换链路。复用已有 `StrategyLibraryService.create_candidate_version()`。

**Tech Stack:** Alembic migration, SQLAlchemy ORM, typer CLI, PostgreSQL

---

## 文件变更总览

| 操作 | 文件路径 |
|------|----------|
| Create | `src/db/migrations/versions/2026_04_29_0003_add_version_type_and_parent_version_id.py` |
| Modify | `src/models/trader_strategy_version.py` |
| Modify | `src/strategy_library/repository.py` |
| Modify | `cli/optimize.py` |
| Create | `tests/unit/strategy_library/test_repository_s7_003b.py` |
| Create | `tests/unit/optimization/test_candidate_builder_db.py` |

---

## Task 1: Alembic Migration

**Files:**
- Create: `src/db/migrations/versions/2026_04_29_0003_add_version_type_and_parent_version_id.py`
- Ref: `src/db/migrations/versions/2026_04_29_0002_add_trader_memory_table.py`（参考格式）

- [ ] **Step 1: 创建 migration 文件**

```python
"""Add version_type and parent_version_id columns to trader_strategy_versions."""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa

revision = "2026_04_29_0003"
down_revision = "2026_04_29_0002"  # 指向最新的 migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "trader_strategy_versions",
        sa.Column("version_type", sa.String(32), nullable=False, server_default="manual"),
    )
    op.add_column(
        "trader_strategy_versions",
        sa.Column("parent_version_id", sa.String(256), nullable=True),
    )
    op.create_index(
        "ix_trader_strategy_versions_version_type",
        "trader_strategy_versions",
        ["version_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_trader_strategy_versions_version_type", "trader_strategy_versions")
    op.drop_column("trader_strategy_versions", "parent_version_id")
    op.drop_column("trader_strategy_versions", "version_type")
```

- [ ] **Step 2: 验证 migration 文件格式**

Run: `python -c "import sys; sys.path.insert(0, '.'); exec(open('src/db/migrations/versions/2026_04_29_0003_add_version_type_and_parent_version_id.py').read())"`

- [ ] **Step 3: 提交 migration**

```bash
git add src/db/migrations/versions/2026_04_29_0003_add_version_type_and_parent_version_id.py
git commit -m "feat(s7-003b): add version_type and parent_version_id columns"
```

---

## Task 2: ORM Model 扩展

**Files:**
- Modify: `src/models/trader_strategy_version.py:40-46`

- [ ] **Step 1: 读取当前 ORM 文件确认插入位置**

Run: `grep -n "released_at\|notes\|strategy_payload" src/models/trader_strategy_version.py | head -20`

- [ ] **Step 2: 在 `notes` 列后、`created_at` 之前插入两列**

在 `notes` 列定义后、`created_at`（继承自 TimestampMixin）之前添加：

```python
    version_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual"
    )
    parent_version_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
```

- [ ] **Step 3: 验证语法正确**

Run: `python -c "from src.models.trader_strategy_version import TraderStrategyVersion; print('OK')"`

- [ ] **Step 4: 提交**

```bash
git add src/models/trader_strategy_version.py
git commit -m "feat(s7-003b): add version_type and parent_version_id to TraderStrategyVersion ORM"
```

---

## Task 3: Repository 映射更新

**Files:**
- Modify: `src/strategy_library/repository.py`

- [ ] **Step 1: 更新 `_to_orm_model()` 写入两列**

在 `strategy_payload=` 赋值之后添加：

```python
            version_type=version.version_type.value,  # S7-003b
            parent_version_id=version.parent_version_id,  # S7-003b
```

- [ ] **Step 2: 更新 `_from_orm_model()` 读取两列**

在 `orm_obj.strategy_payload.get("rules_snapshot", [])` 之后添加：

```python
            version_type=StrategyVersionType(
                getattr(orm_obj, 'version_type', 'manual') or 'manual'
            ),
            parent_version_id=getattr(orm_obj, 'parent_version_id', None),
```

- [ ] **Step 3: 更新 `_update_existing()` 同步两列**

在 `existing.notes = version.notes` 之后添加：

```python
        existing.version_type = version.version_type.value
        existing.parent_version_id = version.parent_version_id
```

- [ ] **Step 4: 验证导入**

确认文件顶部导入了 `StrategyVersionType`：

```python
from src.strategy_library.schemas import (
    StrategyRecommendation,
    StrategyVersion,
    StrategyVersionStatus,
    StrategyVersionType,  # 新增
)
```

- [ ] **Step 5: 运行 repository 单元测试确认无回归**

Run: `pytest tests/unit/strategy_library/ -v -k "not db" --tb=short 2>&1 | tail -20`

- [ ] **Step 6: 提交**

```bash
git add src/strategy_library/repository.py
git commit -m "feat(s7-003b): map version_type and parent_version_id in repository"
```

---

## Task 4: CLI --db 参数

**Files:**
- Modify: `cli/optimize.py:194-324`（`create-candidate` 命令）

- [ ] **Step 1: 在 `optimize_create_candidate` 函数签名中添加 `--db` 参数**

在 `output: str = typer.Option(...)` 之后添加：

```python
    db: bool = typer.Option(False, "--db", help="启用 DB 链路（默认关闭，走文件链路）"),
```

- [ ] **Step 2: 更新 `create-candidate` 命令 docstring**

在 `"""候选版本生成（S7-003）。` 后添加一行说明：

```
    --db 时从 DB 加载正式版本（trader_id + date），候选版本写入 DB。
```

- [ ] **Step 3: 在函数开头添加 DB 链路处理逻辑**

在 `adjustments_list: list[RuleAdjustment] = []` 之前插入：

```python
    # S7-003b DB 链路
    if db:
        from datetime import date as Date
        from src.strategy_library.service import StrategyLibraryService
        from config.database import get_session_factory

        if not trader or not date:
            typer.secho("--db=True 时必须指定 --trader 和 --date", fg=typer.colors.RED)
            return
        if not adjustments:
            typer.echo("无调整建议数据，请检查 --adjustments 参数")
            return

        # 加载调整建议（与文件链路相同）
        adj_path = Path(adjustments)
        if not adj_path.exists():
            typer.secho(f"调整建议文件不存在: {adj_path}", fg=typer.colors.YELLOW)
            return
        try:
            adj_data = json.loads(adj_path.read_text())
            if isinstance(adj_data, dict) and "adjustments" in adj_data:
                adj_data = adj_data["adjustments"]
            adjustments_list = [RuleAdjustment(**adj) for adj in adj_data]
        except Exception as exc:
            typer.secho(f"加载调整建议失败 {adj_path}: {exc}", fg=typer.colors.YELLOW)
            return

        # 从 DB 加载正式版本
        svc = StrategyLibraryService()
        factory = get_session_factory()

        async def run():
            async with factory() as session:
                released_versions = await svc._repo.get_released_by_trader_and_date(
                    session=session,
                    trader_id=trader,
                    strategy_date=Date.fromisoformat(date),
                )
                if not released_versions:
                    typer.secho(
                        f"未找到正式版本: trader={trader}, date={date}",
                        fg=typer.colors.RED,
                    )
                    return None
                return released_versions[0]

        parent_version = _run_async(run())
        if parent_version is None:
            return

        # 调用 create_candidate_version 写 DB
        async def create():
            async with factory() as session:
                candidate = await svc.create_candidate_version(
                    session=session,
                    trader_id=trader,
                    strategy_date=Date.fromisoformat(date),
                    parent_version_id=parent_version.version_id,
                    adjustments=adjustments_list,
                    recommendations=[],  # 候选版本暂不携带 recommendations
                )
                await session.commit()
                return candidate

        candidate = _run_async(create())

        typer.echo(f"\n=== 候选版本已写入 DB ===")
        typer.echo(f"  version_id: {candidate.version_id}")
        typer.echo(f"  parent_version_id: {candidate.parent_version_id}")
        typer.echo(f"  status: {candidate.status.value}")
        typer.echo(f"  version_type: {candidate.version_type.value}")

        # 如果指定了 --output，同时写 JSON 文件
        if output:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            json_data = {
                "version_id": candidate.version_id,
                "trader_id": candidate.trader_id,
                "strategy_date": candidate.strategy_date.isoformat(),
                "status": candidate.status.value,
                "version_type": candidate.version_type.value,
                "parent_version_id": candidate.parent_version_id,
                "rules_snapshot": candidate.rules_snapshot,
                "notes": candidate.notes,
            }
            out_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False))
            typer.secho(f"候选版本已写入: {out_path}", fg=typer.colors.GREEN)

        return
```

- [ ] **Step 4: 添加 `_run_async` 辅助函数（文件顶部已存在，检查是否需要调整）**

当前 `cli/optimize.py` 已有 `_run_async`，无需修改。如果不存在，在 `@app.command("create-candidate")` 之前添加：

```python
def _run_async(coro):
    """在同步上下文中执行异步任务。"""
    import asyncio
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
```

- [ ] **Step 5: 验证 CLI 注册成功**

Run: `python -m cli.main optimize create-candidate --help`

Expected 输出包含 `--db` 选项说明。

- [ ] **Step 6: 提交**

```bash
git add cli/optimize.py
git commit -m "feat(s7-003b): add --db flag to optimize create-candidate command"
```

---

## Task 5: 单元测试

**Files:**
- Create: `tests/unit/strategy_library/test_repository_s7_003b.py`
- Create: `tests/unit/optimization/test_candidate_builder_db.py`

- [ ] **Step 1: 编写 Repository 映射测试**

```python
"""S7-003b: Repository version_type / parent_version_id 映射测试"""
from datetime import date

import pytest

from src.strategy_library.repository import StrategyLibraryRepository
from src.strategy_library.schemas import (
    StrategyVersion,
    StrategyVersionStatus,
    StrategyVersionType,
)


class TestRepositoryVersionTypeMapping:
    """测试 _to_orm_model 和 _from_orm_model 对新列的映射。"""

    def test_to_orm_model_sets_version_type_and_parent(self):
        """验证写入时 version_type 和 parent_version_id 正确映射。"""
        version = StrategyVersion(
            version_id="test_v1",
            trader_id="trader_a",
            strategy_date=date(2026, 4, 25),
            status=StrategyVersionStatus.draft,
            version_type=StrategyVersionType.candidate,
            parent_version_id="trader_a_2026-04-25_released",
            recommendations=[],
            rules_snapshot=[],
        )
        orm_obj = StrategyLibraryRepository._to_orm_model(version)
        assert orm_obj.version_type == "candidate"
        assert orm_obj.parent_version_id == "trader_a_2026-04-25_released"

    def test_from_orm_model_reads_version_type_and_parent(self):
        """验证读取时 version_type 和 parent_version_id 正确映射。"""
        from src.models.trader_strategy_version import TraderStrategyVersion

        orm_obj = TraderStrategyVersion(
            trader_id="trader_a",
            strategy_date=date(2026, 4, 25),
            version_name="test_candidate",
            status="draft",
            version_type="candidate",
            parent_version_id="trader_a_2026-04-25_released",
            source_article_ids=[],
            evidence_refs=[],
            strategy_payload={},
        )
        version = StrategyLibraryRepository._from_orm_model(orm_obj)
        assert version.version_type == StrategyVersionType.candidate
        assert version.parent_version_id == "trader_a_2026-04-25_released"

    def test_from_orm_model_fallback_for_missing_columns(self):
        """验证旧记录（无新列）兼容：默认 manual + None。"""
        from src.models.trader_strategy_version import TraderStrategyVersion

        orm_obj = TraderStrategyVersion(
            trader_id="trader_a",
            strategy_date=date(2026, 4, 25),
            version_name="legacy_v1",
            status="released",
            source_article_ids=[],
            evidence_refs=[],
            strategy_payload={},
        )
        version = StrategyLibraryRepository._from_orm_model(orm_obj)
        assert version.version_type == StrategyVersionType.manual
        assert version.parent_version_id is None
```

- [ ] **Step 2: 运行 Repository 测试**

Run: `pytest tests/unit/strategy_library/test_repository_s7_003b.py -v`

- [ ] **Step 3: 编写 CLI --db 参数测试**

```python
"""S7-003b: create-candidate --db CLI 测试"""
import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli.optimize import app


runner = CliRunner()


class TestCreateCandidateDBFlag:
    """测试 --db 参数解析和链路分发。"""

    def test_db_flag_appears_in_help(self):
        """验证 --db 选项在 --help 中可见。"""
        result = runner.invoke(app, ["create-candidate", "--help"])
        assert "--db" in result.stdout

    @patch("cli.optimize._run_async")
    @patch("src.strategy_library.service.StrategyLibraryService")
    def test_db_mode_calls_create_candidate_version(
        self, mock_svc_class, mock_run_async
    ):
        """验证 --db=True 时调用 DB 链路。"""
        # Mock 异步返回值
        mock_run_async.return_value = None

        with tempfile.TemporaryDirectory() as tmpdir:
            adj_file = Path(tmpdir) / "adjustments.json"
            adj_file.write_text(json.dumps({
                "adjustments": [
                    {
                        "trader_id": "trader_a",
                        "rule_id": "rule_001",
                        "current_status": "hit_rate_too_low_and_return_negative",
                        "suggestion": "删除此规则",
                        "confidence": 0.8,
                        "依据": "hit_rate=0.2, return=-5%",
                    }
                ]
            }))

            # --db=True 但缺少 trader/date 应报错
            result = runner.invoke(
                app,
                [
                    "create-candidate",
                    "--db",
                    "--adjustments", str(adj_file),
                ],
            )
            assert result.exit_code != 0
            assert "必须指定 --trader 和 --date" in result.stdout
```

- [ ] **Step 4: 运行 CLI 测试**

Run: `pytest tests/unit/optimization/test_candidate_builder_db.py -v`

- [ ] **Step 5: 提交测试**

```bash
git add tests/unit/strategy_library/test_repository_s7_003b.py tests/unit/optimization/test_candidate_builder_db.py
git commit -m "test(s7-003b): add tests for version_type mapping and --db flag"
```

---

## Task 6: 集成验证

**Files:**
- N/A（无文件变更，仅验证）

- [ ] **Step 1: 运行完整 optimization 模块测试**

Run: `pytest tests/unit/optimization/ -v --tb=short 2>&1 | tail -30`

Expected: 所有测试 PASS

- [ ] **Step 2: 验证 CLI 所有子命令可用**

Run: `python -m cli.main optimize --help`

Expected: 列出 filter / advise / create-candidate 三个子命令

- [ ] **Step 3: 验证 migration 可执行（不实际运行，只做 dry-run 语法检查）**

Run: `python -c "from alembic.config import Config; from alembic import command; cfg = Config('src/db/migrations/alembic.ini'); print('Migration config OK')"`

---

## 实施顺序

1. Task 1: Alembic Migration
2. Task 2: ORM Model 扩展
3. Task 3: Repository 映射更新
4. Task 4: CLI --db 参数
5. Task 5: 单元测试
6. Task 6: 集成验证
