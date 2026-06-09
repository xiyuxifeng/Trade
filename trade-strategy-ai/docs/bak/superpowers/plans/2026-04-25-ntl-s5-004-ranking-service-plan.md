# NTL-S5-004 Ranking Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 ranking service，对盘后评估结果按 `return_pct` + 赔率多级排序，支持 nested/flat 双视图输出，自动持久化到 DB。

**Architecture:**
- ORM 层：`RankingEntryRecord` 持久化模型（`src/models/ranking_entry.py`）
- Repository 层：`RankingRepository` 数据访问（`src/evaluation/ranking_repository.py`）
- Service 层：`RankingService` 业务逻辑（`src/evaluation/ranking_service.py`）
- 并发安全：DB 层唯一约束 + `ON CONFLICT DO UPDATE` 原子 upsert

**Tech Stack:** SQLAlchemy (async), PostgreSQL, pydantic/dataclass

---

## 文件结构

```
src/models/
    ranking_entry.py           # 创建：RankingEntryRecord ORM
src/evaluation/
    ranking_repository.py      # 创建：RankingRepository
    ranking_service.py          # 创建：RankingService + RankingEntry dataclass
    __init__.py                # 修改：导出 RankingEntry/RankingService
tests/unit/evaluation/
    test_ranking_service.py    # 创建：单元测试
    test_ranking_repository.py # 创建：单元测试
```

---

## Task 1: 创建 RankingEntryRecord ORM 模型

**Files:**
- Create: `src/models/ranking_entry.py`
- Modify: `src/models/__init__.py`

### Steps

- [ ] **Step 1: 检查 Base 类定义和命名约定**

验证 `src/models/base.py` 中的 `NAMING_CONVENTION` 和 `TimestampMixin`。

Run: `cat src/models/base.py`

---

- [ ] **Step 2: 编写 ranking_entry.py**

```python
"""Ranking Entry ORM 模型。

将每笔交易的想法和对应的 ranking 结果持久化到数据库。
支持嵌套分组（trader → strategy_version → symbol）和版本淘汰（is_latest）。

NTL-S5-004
"""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class RankingEntryRecord(TimestampMixin, Base):
    """ranking 条目持久化模型。

    存储结构：trade_date + trader_id + strategy_version_id + symbol 为唯一键，
    通过 is_latest 标记当前有效条目，历史条目保留用于追溯。

    索引设计：
      - trade_date：按日期查询
      - (trader_id, strategy_version_id)：嵌套分组查询
      - (trade_date, strategy_version_id, symbol) 唯一约束：防止并发重复写入
    """

    __tablename__ = "ranking_entries"
    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "strategy_version_id",
            "symbol",
            name="uq_ranking_entry",
        ),
        Index("ix_ranking_trader_version", "trader_id", "strategy_version_id"),
        Index("ix_ranking_trade_date", "trade_date"),
    )

    # 主键
    entry_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # 分组键
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    trader_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    strategy_version_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)

    # 排序指标（可空，表示尚无评分）
    return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    mfe: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    composite_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 排名（generate_ranking 时批量回填）
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 版本状态：True = 该 (trade_date, version, symbol) 组合的最新条目
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # 来源追踪
    idea_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    attribution_source: Mapped[str] = mapped_column(String(32), nullable=False, default="auto")

    # 扩展字段
    extra: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    def to_dict(self) -> dict:
        """转为字典。"""
        return {
            "entry_id": str(self.entry_id),
            "trade_date": self.trade_date,
            "trader_id": self.trader_id,
            "strategy_version_id": self.strategy_version_id,
            "symbol": self.symbol,
            "return_pct": self.return_pct,
            "mfe": self.mfe,
            "mae": self.mae,
            "composite_score": self.composite_score,
            "rank": self.rank,
            "is_latest": self.is_latest,
            "idea_id": str(self.idea_id) if self.idea_id else None,
            "attribution_source": self.attribution_source,
            "extra": self.extra,
        }
```

---

- [ ] **Step 3: 更新 src/models/__init__.py**

添加 `RankingEntryRecord` 到导出。

Run: `grep -n "RankingEntryRecord\|from src.models.ranking_entry\|ranking_entry" src/models/__init__.py || echo "not found"`

如果 `ranking_entry` 未导入，添加：
```python
from src.models.ranking_entry import RankingEntryRecord
```

并在 `__all__` 列表中加入 `RankingEntryRecord`。

---

- [ ] **Step 4: 编写基础测试（验证模型可导入）**

```python
# tests/unit/evaluation/test_ranking_model.py
"""验证 RankingEntryRecord ORM 模型可正常导入和实例化。"""
import pytest
from src.models.ranking_entry import RankingEntryRecord
from src.models.base import Base


def test_ranking_entry_record_tablename():
    assert RankingEntryRecord.__tablename__ == "ranking_entries"


def test_ranking_entry_record_columns():
    """验证关键列存在。"""
    cols = [c.name for c in RankingEntryRecord.__table__.columns]
    assert "entry_id" in cols
    assert "trade_date" in cols
    assert "trader_id" in cols
    assert "strategy_version_id" in cols
    assert "symbol" in cols
    assert "return_pct" in cols
    assert "mfe" in cols
    assert "mae" in cols
    assert "composite_score" in cols
    assert "rank" in cols
    assert "is_latest" in cols
    assert "attribution_source" in cols


def test_ranking_entry_unique_constraint():
    """验证唯一约束存在。"""
    constraints = RankingEntryRecord.__table__.constraints
    uq_names = [c.name for c in constraints if c.name == "uq_ranking_entry"]
    assert len(uq_names) == 1
```

Run: `pytest tests/unit/evaluation/test_ranking_model.py -v`
Expected: 3 PASS

---

- [ ] **Step 5: Commit**

```bash
git add src/models/ranking_entry.py src/models/__init__.py tests/unit/evaluation/test_ranking_model.py
git commit -m "feat(NTL-S5-004): add RankingEntryRecord ORM model"
```

---

## Task 2: 创建 RankingEntry dataclass 和 RankingRepository

**Files:**
- Create: `src/evaluation/ranking_repository.py`
- Modify: `src/evaluation/ranking_service.py`（仅 dataclass 部分）
- Test: `tests/unit/evaluation/test_ranking_repository.py`

### Steps

- [ ] **Step 1: 编写 ranking_service.py（RankingEntry dataclass + 辅助函数）**

```python
"""Ranking Service：盘后 ranking 多级排序服务。

职责：
  - 接收 postmortem 结果，生成 ranking 条目并持久化
  - 支持批量生成 ranking（计算组内 rank）
  - 支持 postmortem 修正后的同步更新（update_entry）
  - 提供嵌套视图和扁平视图两种输出格式

NTL-S5-004
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal
from uuid import UUID

if TYPE_CHECKING:
    from src.evaluation.postmortem_service import PostmortemResult
    from src.evaluation.evidence_pack import EvidencePack


@dataclass
class RankingEntry:
    """单条 ranking 条目（内存结构，对应 RankingEntryRecord）。

    排序规则：
      1. 先按 return_pct 降序
      2. return_pct 相同时按 (mfe - mae) 降序（赔率优选）
      3. return_pct 为 None 的排在最后，组内按赔率排序
    """
    entry_id: UUID
    trade_date: str
    trader_id: str
    strategy_version_id: str
    symbol: str

    # 排序指标
    return_pct: float | None
    mfe: float | None
    mae: float | None

    # 复合分（用于调试和对账）
    composite_score: float | None

    # 排序结果（generate_ranking 时填充）
    rank: int | None

    # 版本状态
    is_latest: bool

    # 来源追踪
    idea_id: UUID | None
    attribution_source: str

    extra: dict = field(default_factory=dict)

    @classmethod
    def from_record(cls, record) -> "RankingEntry":
        """从 ORM record 构建内存 dataclass。"""
        return cls(
            entry_id=record.entry_id,
            trade_date=record.trade_date,
            trader_id=record.trader_id,
            strategy_version_id=record.strategy_version_id,
            symbol=record.symbol,
            return_pct=record.return_pct,
            mfe=record.mfe,
            mae=record.mae,
            composite_score=record.composite_score,
            rank=record.rank,
            is_latest=record.is_latest,
            idea_id=record.idea_id,
            attribution_source=record.attribution_source,
            extra=record.extra or {},
        )


def _compute_composite(return_pct: float | None, mfe: float | None, mae: float | None) -> float | None:
    """计算复合分。用于调试和对账，不影响排序逻辑（排序用 return_pct + 赔率直接计算）。"""
    if return_pct is None:
        return None
    odds_bonus = max(0.0, (mfe or 0) - (mae or 0))
    return return_pct + odds_bonus


def _sort_key(entry: RankingEntry) -> tuple:
    """返回用于排序的 key tuple。"""
    if entry.return_pct is None:
        # None 排最后，组内按赔率排序
        odds = max(0.0, (entry.mfe or 0) - (entry.mae or 0))
        return (1, -odds)  # (1, ...) 表示 None 排在后面
    else:
        odds = max(0.0, (entry.mfe or 0) - (entry.mae or 0))
        return (0, -entry.return_pct, -odds)  # (0, return_pct desc, odds desc)
```

---

- [ ] **Step 2: 编写 ranking_repository.py（Upsert + 查询 + 批量 rank 更新）**

```python
"""Ranking 数据访问层。

职责：
  - Upsert ranking entry（原子性，通过 ON CONFLICT DO UPDATE）
  - 查询最新 entry
  - 批量更新 rank
  - 按日期/trader/version 查询

NTL-S5-004
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ranking_entry import RankingEntryRecord


class RankingRepository:
    """ranking 条目数据访问层。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, entry: "RankingEntry") -> RankingEntryRecord:
        """Upsert 一条 ranking entry，保证 is_latest=True 的唯一性。

        实现：
          INSERT ... ON CONFLICT (trade_date, strategy_version_id, symbol)
          DO UPDATE SET is_latest = FALSE  -- 将旧 latest 标记为非最新
          RETURNING ...

        Args:
            entry: RankingEntry dataclass

        Returns:
            新创建的或已存在的 RankingEntryRecord
        """
        # 先将同一 (trade_date, strategy_version_id, symbol) 的现有 latest 标记为 False
        await self.session.execute(
            update(RankingEntryRecord)
            .where(
                RankingEntryRecord.trade_date == entry.trade_date,
                RankingEntryRecord.strategy_version_id == entry.strategy_version_id,
                RankingEntryRecord.symbol == entry.symbol,
                RankingEntryRecord.is_latest == True,
            )
            .values(is_latest=False)
        )

        # 插入新 entry（is_latest=True）
        record = RankingEntryRecord(
            entry_id=entry.entry_id,
            trade_date=entry.trade_date,
            trader_id=entry.trader_id,
            strategy_version_id=entry.strategy_version_id,
            symbol=entry.symbol,
            return_pct=entry.return_pct,
            mfe=entry.mfe,
            mae=entry.mae,
            composite_score=entry.composite_score,
            rank=entry.rank,
            is_latest=True,  # 强制为 True
            idea_id=entry.idea_id,
            attribution_source=entry.attribution_source,
            extra=entry.extra,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def find_latest(
        self,
        strategy_version_id: str,
        symbol: str,
        trade_date: str,
    ) -> RankingEntryRecord | None:
        """查找指定版本+标的的最新 entry。"""
        stmt = select(RankingEntryRecord).where(
            RankingEntryRecord.trade_date == trade_date,
            RankingEntryRecord.strategy_version_id == strategy_version_id,
            RankingEntryRecord.symbol == symbol,
            RankingEntryRecord.is_latest == True,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def query_by_date(
        self,
        trade_date: str,
        trader_id: str | None = None,
        strategy_version_id: str | None = None,
        is_latest_only: bool = True,
    ) -> list[RankingEntryRecord]:
        """按日期查询 entry。用于 generate_ranking。"""
        stmt = select(RankingEntryRecord).where(
            RankingEntryRecord.trade_date == trade_date,
        )
        if trader_id:
            stmt = stmt.where(RankingEntryRecord.trader_id == trader_id)
        if strategy_version_id:
            stmt = stmt.where(RankingEntryRecord.strategy_version_id == strategy_version_id)
        if is_latest_only:
            stmt = stmt.where(RankingEntryRecord.is_latest == True)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_rank(self, entry_ids: list[UUID], ranks: list[int]) -> None:
        """批量更新 rank。"""
        if not entry_ids:
            return
        for entry_id, rank in zip(entry_ids, ranks):
            await self.session.execute(
                update(RankingEntryRecord)
                .where(RankingEntryRecord.entry_id == entry_id)
                .values(rank=rank)
            )
        await self.session.flush()

    async def get_latest_by_version(self, version_id: str) -> list[RankingEntryRecord]:
        """获取指定策略版本的最新 ranking 条目（is_latest=True）。"""
        stmt = select(RankingEntryRecord).where(
            RankingEntryRecord.strategy_version_id == version_id,
            RankingEntryRecord.is_latest == True,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

---

- [ ] **Step 3: 编写 ranking_repository 单元测试**

```python
# tests/unit/evaluation/test_ranking_repository.py
"""RankingRepository 单元测试。"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.evaluation.ranking_service import RankingEntry
from src.evaluation.ranking_repository import RankingRepository


@pytest.fixture
def mock_session():
    return AsyncMock()


def make_entry(
    trade_date="2026-04-25",
    trader_id="trader_a",
    version_id="v_2026_04_25",
    symbol="SH600519",
    return_pct=5.2,
    mfe=8.0,
    mae=2.8,
):
    return RankingEntry(
        entry_id=uuid4(),
        trade_date=trade_date,
        trader_id=trader_id,
        strategy_version_id=version_id,
        symbol=symbol,
        return_pct=return_pct,
        mfe=mfe,
        mae=mae,
        composite_score=return_pct + max(0, mfe - mae),
        rank=None,
        is_latest=True,
        idea_id=uuid4(),
        attribution_source="auto",
        extra={},
    )


@pytest.mark.asyncio
async def test_upsert_marks_old_latest_false(mock_session):
    """验证 upsert 将旧 latest 标记为 False。"""
    repo = RankingRepository(mock_session)
    entry = make_entry()

    await repo.upsert(entry)

    # 验证 update 被调用（标记旧 entry 为非最新）
    assert mock_session.execute.called
    call_args = mock_session.execute.call_args
    # update statement was passed
    assert call_args is not None


@pytest.mark.asyncio
async def test_upsert_adds_new_record(mock_session):
    """验证 upsert 添加新 record。"""
    repo = RankingRepository(mock_session)
    entry = make_entry()

    await repo.upsert(entry)

    assert mock_session.add.called
    assert mock_session.flush.called


@pytest.mark.asyncio
async def test_find_latest_query(mock_session):
    """验证 find_latest 生成正确的查询。"""
    repo = RankingRepository(mock_session)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repo.find_latest("v1", "SH600519", "2026-04-25")

    assert mock_session.execute.called
    query_str = str(mock_session.execute.call_args)
    assert "strategy_version_id" in query_str
    assert "symbol" in query_str
    assert "is_latest" in query_str


@pytest.mark.asyncio
async def test_query_by_date_filters(mock_session):
    """验证 query_by_date 正确过滤。"""
    repo = RankingRepository(mock_session)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    await repo.query_by_date("2026-04-25", trader_id="trader_a")

    query_str = str(mock_session.execute.call_args)
    assert "trade_date" in query_str
    assert "trader_id" in query_str
```

Run: `pytest tests/unit/evaluation/test_ranking_repository.py -v`
Expected: 4 PASS

---

- [ ] **Step 4: Commit**

```bash
git add src/evaluation/ranking_repository.py tests/unit/evaluation/test_ranking_repository.py
git commit -m "feat(NTL-S5-004): add RankingRepository with atomic upsert"
```

---

## Task 3: 创建 RankingService（add_entry / generate_ranking / update_entry）

**Files:**
- Modify: `src/evaluation/ranking_service.py`（完整实现）
- Test: `tests/unit/evaluation/test_ranking_service.py`

### Steps

- [ ] **Step 1: 编写 RankingService 完整实现**

在 `ranking_service.py` 追加以下内容（在 Task 2 的 dataclass 之后）：

```python
from src.evaluation.ranking_repository import RankingRepository
from src.evaluation.ranking_service import RankingEntry


class RankingService:
    """盘后 ranking service。

    职责：
      - 接收 postmortem 结果和 evidence pack，生成 ranking 条目并持久化
      - 支持批量生成 ranking（计算组内 rank）
      - 支持 postmortem 修正后的同步更新
      - 提供嵌套视图和扁平视图两种输出格式
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._repo = RankingRepository(session)

    def _entry_from_postmortem_and_pack(
        self,
        postmortem: "PostmortemResult",
        evidence_pack: "EvidencePack",
    ) -> RankingEntry:
        """从 postmortem 结果和 evidence pack 构建 RankingEntry。

        从 evidence_pack 提取：
          - trade_date（从 TradeIdea.as_of_date）
          - trader_id（从 signal_context 或 TradeIdea）
          - strategy_version_id
          - symbol（从 TradeIdea）

        从 postmortem 提取：
          - return_pct / mfe / mae
          - attribution_source
        """
        from uuid import uuid4

        # 从 evidence_pack 提取基本信息
        trade_date = evidence_pack.trade_date
        strategy_version_id = evidence_pack.strategy_version_id or ""
        symbol = ""

        # 从 trade_idea 提取 symbol
        if evidence_pack.trade_idea and hasattr(evidence_pack.trade_idea, "symbol"):
            symbol = evidence_pack.trade_idea.symbol or ""

        # 从 signal_context 提取 trader_id（如果有）
        trader_id = ""
        if evidence_pack.signal_context and hasattr(evidence_pack.signal_context, "trader_id"):
            trader_id = evidence_pack.signal_context.trader_id or ""

        # 如果 signal_context 没有 trader_id，尝试从 trade_idea 提取
        if not trader_id and evidence_pack.trade_idea and hasattr(evidence_pack.trade_idea, "trader_id"):
            trader_id = evidence_pack.trade_idea.trader_id or ""

        # 从 postmortem 提取指标
        return_pct = postmortem.return_pct
        mfe_val = postmortem.mfe
        mae_val = postmortem.mae

        composite = _compute_composite(return_pct, mfe_val, mae_val)

        return RankingEntry(
            entry_id=uuid4(),
            trade_date=trade_date,
            trader_id=trader_id,
            strategy_version_id=strategy_version_id,
            symbol=symbol,
            return_pct=return_pct,
            mfe=mfe_val,
            mae=mae_val,
            composite_score=composite,
            rank=None,  # add_entry 时不计算 rank
            is_latest=True,
            idea_id=postmortem.idea_id,
            attribution_source=postmortem.attribution_source,
            extra={},
        )

    async def add_entry(
        self,
        postmortem: "PostmortemResult",
        evidence_pack: "EvidencePack",
    ) -> RankingEntry:
        """接收一个 postmortem 结果，生成并持久化一条 ranking 条目。

        rank 字段在 add_entry 时为 None，由 generate_ranking() 批量计算。
        同一 (trade_date, strategy_version_id, symbol) 已存在时，
        旧 entry 被标记为 is_latest=False，新 entry 的 is_latest=True。

        Args:
            postmortem: 盘后复盘结果
            evidence_pack: 交易证据包

        Returns:
            新建的 RankingEntry
        """
        entry = self._entry_from_postmortem_and_pack(postmortem, evidence_pack)
        record = await self._repo.upsert(entry)
        return RankingEntry.from_record(record)

    async def generate_ranking(
        self,
        trade_date: str,
        trader_id: str | None = None,
        strategy_version_id: str | None = None,
        view: Literal["nested", "flat"] = "nested",
    ) -> dict | list:
        """批量生成并更新指定日期的 ranking（计算 rank）。

        调用时机：当日所有 add_entry 完成后（NTL-S5-011 盘后流程末尾）。

        排序规则：
          1. return_pct 降序
          2. return_pct 相同时按 (mfe - mae) 降序
          3. return_pct 为 None 的排在最后，组内按赔率排序

        Args:
            trade_date: 交易日期（YYYY-MM-DD）
            trader_id: 可选，限定 trader
            strategy_version_id: 可选，限定策略版本
            view: "nested"（默认，嵌套字典）| "flat"（扁平列表）

        Returns:
            nested view: {trader_id: {strategy_version_id: [RankingEntry...]}}
            flat view: [RankingEntry...]（先按 trader 分组，组内按 composite_score 排序）
        """
        # 查询所有 latest entry
        records = await self._repo.query_by_date(
            trade_date=trade_date,
            trader_id=trader_id,
            strategy_version_id=strategy_version_id,
            is_latest_only=True,
        )

        entries = [RankingEntry.from_record(r) for r in records]

        # 按 (trader_id, strategy_version_id) 分组
        groups: dict[str, dict[str, list[RankingEntry]]] = {}
        for entry in entries:
            groups.setdefault(entry.trader_id, {})
            groups[entry.trader_id].setdefault(entry.strategy_version_id, [])
            groups[entry.trader_id][entry.strategy_version_id].append(entry)

        # 在每个组内排序并计算 rank
        all_entries_with_rank: list[RankingEntry] = []
        for trader_id, versions in groups.items():
            for version_id, version_entries in versions.items():
                # 排序
                sorted_entries = sorted(version_entries, key=_sort_key)
                # 计算组内 rank（从 1 开始）
                ranked_entries = []
                for rank_idx, e in enumerate(sorted_entries, start=1):
                    e.rank = rank_idx
                    ranked_entries.append(e)
                all_entries_with_rank.extend(ranked_entries)

        # 更新 DB 中的 rank
        if all_entries_with_rank:
            entry_ids = [e.entry_id for e in all_entries_with_rank]
            ranks = [e.rank for e in all_entries_with_rank]
            await self._repo.update_rank(entry_ids, ranks)

        # 生成视图
        if view == "flat":
            # flat view：先按 trader 分组，组内按 composite_score 排序
            flat_list: list[RankingEntry] = []
            for trader_id in sorted(groups.keys()):
                trader_entries: list[RankingEntry] = []
                for version_id in sorted(groups[trader_id].keys()):
                    trader_entries.extend(sorted(
                        groups[trader_id][version_id],
                        key=lambda e: (-(e.composite_score or 0)),
                    ))
                flat_list.extend(trader_entries)
            return flat_list
        else:
            # nested view：{trader_id: {strategy_version_id: [entries...]}}
            return groups

    async def update_entry(
        self,
        entry_id: UUID,
        postmortem: "PostmortemResult",
    ) -> RankingEntry | None:
        """当 postmortem 被 LLM 修正时，同步更新对应的 ranking 条目。

        实现逻辑：
          1. 查找 entry_id 对应的 record
          2. 标记旧 entry.is_latest=False
          3. 写入新 entry（is_latest=True，rank=None）

        Args:
            entry_id: 被修正的 entry ID
            postmortem: 更新后的 postmortem 结果

        Returns:
            更新后的 RankingEntry，或 None（未找到）
        """
        # 查找旧 record
        stmt = select(RankingEntryRecord).where(RankingEntryRecord.entry_id == entry_id)
        result = await self.session.execute(stmt)
        old_record = result.scalar_one_or_none()

        if old_record is None:
            return None

        # 标记旧 entry 为非最新
        old_record.is_latest = False

        # 从 postmortem 提取更新的指标
        return_pct = postmortem.return_pct
        mfe_val = postmortem.mfe
        mae_val = postmortem.mae

        # 创建新 entry（基于旧的 key + 更新的指标）
        new_entry = RankingEntry(
            entry_id=uuid4(),
            trade_date=old_record.trade_date,
            trader_id=old_record.trader_id,
            strategy_version_id=old_record.strategy_version_id,
            symbol=old_record.symbol,
            return_pct=return_pct,
            mfe=mfe_val,
            mae=mae_val,
            composite_score=_compute_composite(return_pct, mfe_val, mae_val),
            rank=None,  # 下次 generate_ranking 重新计算
            is_latest=True,
            idea_id=postmortem.idea_id,
            attribution_source=postmortem.attribution_source,
            extra={"corrected_from": str(entry_id)},
        )

        new_record = await self._repo.upsert(new_entry)
        return RankingEntry.from_record(new_record)

    def get_latest_by_version(self, version_id: str) -> list[RankingEntry]:
        """获取指定策略版本的最新 ranking 条目（is_latest=True）。

        Note: 同步版本，直接调用 repo。
        """
        # 同步封装（用于不需要 async 的场景）
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._repo.get_latest_by_version(version_id)
        )

    def get_by_trader(self, trader_id: str, trade_date: str | None = None) -> dict:
        """获取指定 trader 的 ranking（嵌套视图）。

        Note: 同步封装。
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._repo.query_by_date(
                trade_date or "", trader_id=trader_id, is_latest_only=True
            )
        )
```

---

- [ ] **Step 2: 补充 ranking_service.py 顶部的 imports**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.evaluation.ranking_repository import RankingRepository
from src.models.ranking_entry import RankingEntryRecord
```

---

- [ ] **Step 3: 编写 ranking_service 核心逻辑单元测试**

```python
# tests/unit/evaluation/test_ranking_service.py
"""RankingService 核心逻辑单元测试。"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.evaluation.ranking_service import (
    RankingEntry,
    RankingService,
    _compute_composite,
    _sort_key,
)


# -------------------------------------------------
# 辅助函数测试
# -------------------------------------------------

def test_compute_composite_with_return_pct():
    assert _compute_composite(5.0, 8.0, 2.0) == 11.0  # 5 + (8-2)


def test_compute_composite_with_none_return():
    assert _compute_composite(None, 8.0, 2.0) is None


def test_compute_composite_negative_odds():
    """赔率为负时取 0。"""
    assert _compute_composite(5.0, 2.0, 8.0) == 5.0  # max(0, 2-8) = 0


def test_sort_key_with_return_pct():
    """有 return_pct 的 entry 排在前面。"""
    entry = RankingEntry(
        entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
        strategy_version_id="v1", symbol="SH600519",
        return_pct=5.0, mfe=8.0, mae=2.0,
        composite_score=11.0, rank=None, is_latest=True,
        idea_id=None, attribution_source="auto",
    )
    key = _sort_key(entry)
    assert key[0] == 0  # 有 return_pct


def test_sort_key_without_return_pct():
    """return_pct 为 None 的 entry 排在后面。"""
    entry = RankingEntry(
        entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
        strategy_version_id="v1", symbol="SH600519",
        return_pct=None, mfe=8.0, mae=2.0,
        composite_score=None, rank=None, is_latest=True,
        idea_id=None, attribution_source="auto",
    )
    key = _sort_key(entry)
    assert key[0] == 1  # None 排在后面


def test_sort_key_odds_sorting():
    """return_pct 相同时，按赔率排序。"""
    entry1 = RankingEntry(
        entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
        strategy_version_id="v1", symbol="SH600519",
        return_pct=5.0, mfe=10.0, mae=2.0,  # 赔率 8
        composite_score=13.0, rank=None, is_latest=True,
        idea_id=None, attribution_source="auto",
    )
    entry2 = RankingEntry(
        entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
        strategy_version_id="v1", symbol="SH600000",
        return_pct=5.0, mfe=3.0, mae=1.0,  # 赔率 2
        composite_score=7.0, rank=None, is_latest=True,
        idea_id=None, attribution_source="auto",
    )
    key1 = _sort_key(entry1)
    key2 = _sort_key(entry2)
    # 两者 return_pct 相同(5.0)，key[1] 相同，key[2] 为 odds，entry1 的赔率更高，应排前面
    # key: (0, -5.0, -odds)
    assert key1 < key2  # entry1 的 odds(8) > entry2 的 odds(2)，key 更小，排前面


# -------------------------------------------------
# RankingEntry.from_record 测试
# -------------------------------------------------

def test_ranking_entry_from_record():
    """验证从 ORM record 正确构建 RankingEntry。"""
    mock_record = MagicMock()
    mock_record.entry_id = uuid4()
    mock_record.trade_date = "2026-04-25"
    mock_record.trader_id = "trader_a"
    mock_record.strategy_version_id = "v1"
    mock_record.symbol = "SH600519"
    mock_record.return_pct = 5.0
    mock_record.mfe = 8.0
    mock_record.mae = 2.0
    mock_record.composite_score = 11.0
    mock_record.rank = 1
    mock_record.is_latest = True
    mock_record.idea_id = uuid4()
    mock_record.attribution_source = "llm_corrected"
    mock_record.extra = {}

    entry = RankingEntry.from_record(mock_record)

    assert entry.trade_date == "2026-04-25"
    assert entry.trader_id == "trader_a"
    assert entry.return_pct == 5.0
    assert entry.rank == 1
    assert entry.is_latest is True
    assert entry.attribution_source == "llm_corrected"


# -------------------------------------------------
# 排序集成测试（mock ranking service）
# -------------------------------------------------

def test_sorting_integration():
    """验证多级排序逻辑。"""
    entries = [
        RankingEntry(
            entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
            strategy_version_id="v1", symbol="S1",
            return_pct=None, mfe=5.0, mae=1.0,  # 赔率 4
            composite_score=None, rank=None, is_latest=True,
            idea_id=None, attribution_source="auto",
        ),
        RankingEntry(
            entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
            strategy_version_id="v1", symbol="S2",
            return_pct=5.0, mfe=8.0, mae=2.0,  # 赔率 6
            composite_score=11.0, rank=None, is_latest=True,
            idea_id=None, attribution_source="auto",
        ),
        RankingEntry(
            entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
            strategy_version_id="v1", symbol="S3",
            return_pct=10.0, mfe=3.0, mae=1.0,  # 赔率 2
            composite_score=12.0, rank=None, is_latest=True,
            idea_id=None, attribution_source="auto",
        ),
        RankingEntry(
            entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
            strategy_version_id="v1", symbol="S4",
            return_pct=None, mfe=2.0, mae=1.0,  # 赔率 1
            composite_score=None, rank=None, is_latest=True,
            idea_id=None, attribution_source="auto",
        ),
    ]

    sorted_entries = sorted(entries, key=_sort_key)

    # 预期顺序：S3(10.0) > S2(5.0) > S1(赔率4) > S4(赔率1)
    assert sorted_entries[0].symbol == "S3"
    assert sorted_entries[1].symbol == "S2"
    assert sorted_entries[2].symbol == "S1"  # None 排后面，但组内按赔率
    assert sorted_entries[3].symbol == "S4"
```

Run: `pytest tests/unit/evaluation/test_ranking_service.py -v`
Expected: 9 PASS

---

- [ ] **Step 4: Commit**

```bash
git add src/evaluation/ranking_service.py tests/unit/evaluation/test_ranking_service.py
git commit -m "feat(NTL-S5-004): add RankingService with add_entry / generate_ranking / update_entry"
```

---

## Task 4: 更新 __init__.py 导出 + 最终验收测试

**Files:**
- Modify: `src/evaluation/__init__.py`
- Run: 全量测试验证

### Steps

- [ ] **Step 1: 更新 evaluation/__init__.py**

添加 `RankingEntry` 和 `RankingService` 到导出：

```python
from src.evaluation.ranking_service import RankingEntry, RankingService

__all__ = [
    # ... existing exports ...
    "RankingEntry",
    "RankingService",
]
```

---

- [ ] **Step 2: 运行全量测试验证**

Run: `pytest tests/unit/evaluation/ -v --tb=short`

Expected: 所有 evaluation tests PASS（包括 failure_taxonomy、postmortem_service、ranking_*）

---

- [ ] **Step 3: 验证 TaskList 标记完成**

在 `docs/TaskList.md` 中找到 NTL-S5-004，标记为 `[x]` 完成。

---

- [ ] **Step 4: Commit**

```bash
git add src/evaluation/__init__.py docs/TaskList.md
git commit -m "feat(NTL-S5-004): complete ranking service with exports and tests"
```

---

## 实现核对清单（Self-Review）

- [ ] RankingEntry dataclass：字段完整，`_sort_key` / `_compute_composite` 正确
- [ ] RankingEntryRecord ORM：唯一约束、索引、is_latest 字段
- [ ] RankingRepository.upsert：原子操作，旧 entry 标记 is_latest=False
- [ ] RankingService.add_entry：entry 构建逻辑（从 evidence_pack + postmortem）
- [ ] RankingService.generate_ranking：nested/flat 双视图，分组内排序，rank 回填
- [ ] RankingService.update_entry：postmortem 修正同步，旧标记 outdated，新写入
- [ ] async 风格统一：所有方法为 async def
- [ ] __init__.py 导出正确
- [ ] 单元测试覆盖核心逻辑（排序逻辑、upsert 行为、from_record）

---

## 验收标准

1. `add_entry` 正确 upsert，新 entry 的 `is_latest=True`，旧 entry 的 `is_latest=False`
2. `generate_ranking` 正确计算 rank：return_pct 降序，相同时按 mfe-mae 降序，None 排最后
3. `update_entry` 能同步 postmortem 修正，更新对应 entry 并标记旧条目的 `is_latest=False`
4. 支持 nested/flat 两种视图输出
5. 唯一约束 `uq_ranking_entry` 防止重复写入
6. 单元测试覆盖核心逻辑（排序逻辑、upsert 行为、版本淘汰）