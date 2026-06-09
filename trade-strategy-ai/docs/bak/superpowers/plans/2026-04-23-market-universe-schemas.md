# NTL-S2-008 Market Universe Schema 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `src/market_universe/schemas.py`，定义候选池相关的所有 Python dataclass 模型（`HotTopic`、`TopicConstituent`、`StrongSymbol` 及其聚合 payload），为 builder/selector/service 提供统一的类型契约。

**Architecture:** 所有 schema 定义为标准 Python `dataclass`，放在 `src/market_universe/schemas.py`。使用 `typing.Optional` 和默认值确保字段可缺省。与数据库 ORM 模型（`HotTopicsSnapshot` 等）完全解耦——dataclass 只约束内存中的数据结构。

**Tech Stack:** Python 标准库 `dataclasses`，无额外依赖。

---

## 文件结构

- Create: `src/market_universe/schemas.py`
- Create: `src/market_universe/__init__.py`
- Create: `tests/unit/market_universe/test_schemas.py`
- Modify: `docs/TaskList.md`（标记完成）

---

### Task 1: 创建 market_universe 包骨架

**Files:**
- Create: `src/market_universe/__init__.py`
- Test: `tests/unit/market_universe/test_schemas.py::test_market_universe_package_importable`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/market_universe/test_schemas.py
def test_market_universe_package_importable():
    """market_universe 包应可导入。"""
    from src.market_universe import schemas
    assert hasattr(schemas, "HotTopic")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/market_universe/test_schemas.py::test_market_universe_package_importable -v`
Expected: FAIL - No module named 'src.market_universe'

- [ ] **Step 3: 创建目录和 __init__.py**

```python
# src/market_universe/__init__.py
"""市场候选池模块。"""

from . import schemas

__all__ = ["schemas"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/market_universe/test_schemas.py::test_market_universe_package_importable -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/market_universe/__init__.py
git commit -m "feat(s2-008): bootstrap market_universe package"
```

---

### Task 2: 定义 HotTopic 和 HotTopicsPayload

**Files:**
- Create: `src/market_universe/schemas.py`
- Test: `tests/unit/market_universe/test_schemas.py::test_hot_topic_fields`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/market_universe/test_schemas.py 新增
def test_hot_topic_fields():
    """HotTopic 应包含所有热点字段。"""
    from src.market_universe.schemas import HotTopic

    t = HotTopic(
        kind="concept",
        topic_id="001",
        topic_name="人工智能",
        score=85.5,
        increase_pct=3.2,
        speed_pct=1.1,
        turnover=5000.0,
        net_inflow=2000.0,
    )
    assert t.kind == "concept"
    assert t.topic_id == "001"
    assert t.topic_name == "人工智能"
    assert t.score == 85.5
    assert t.increase_pct == 3.2
    assert t.speed_pct == 1.1
    assert t.turnover == 5000.0
    assert t.net_inflow == 2000.0


def test_hot_topic_defaults():
    """HotTopic 可缺省字段应默认 None。"""
    from src.market_universe.schemas import HotTopic

    t = HotTopic(kind="concept", topic_id="001", topic_name="人工智能")
    assert t.score is None
    assert t.increase_pct is None
    assert t.speed_pct is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/market_universe/test_schemas.py::test_hot_topic_fields -v`
Expected: FAIL - HotTopic not defined

- [ ] **Step 3: 写 schemas.py**

```python
# src/market_universe/schemas.py
"""市场候选池数据结构定义。

职责：
- 定义 HotTopic、TopicConstituent、StrongSymbol 等原子数据结构
- 定义 HotTopicsPayload、TopicConstituentsPayload、StrongSymbolsPayload 等聚合结构
- 为 builder/selector/service 提供统一的类型契约
- 与 ORM 模型完全解耦，仅约束内存数据结构
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


# ============================
# 热点主题（Hot Topics）
# ============================

@dataclass(frozen=True)
class HotTopic:
    """单个热点主题。"""

    kind: str                          # e.g. "concept", "industry", "concept_fengkou"
    topic_id: str                      # 板块/概念 ID
    topic_name: str                    # 板块/概念名称
    score: float | None = None         # 综合得分
    increase_pct: float | None = None  # 涨跌幅 %
    speed_pct: float | None = None    # 涨速 %
    turnover: float | None = None      # 成交额（万元）
    net_inflow: float | None = None    # 净流入（万元）


@dataclass(frozen=True)
class HotTopicsPayload:
    """热点主题聚合 payload。"""

    trade_date: str                    # ISO 格式日期
    slot: str                           # 时段标识，如 "09-25"
    topics: list[HotTopic] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)   # ["board_strength", "industry", "concept_fengkou"]
    fetched_at: datetime | None = None


# ============================
# 题材成分（Topic Constituents）
# ============================

@dataclass(frozen=True)
class TopicConstituent:
    """单个题材成分。"""

    kind: str                           # e.g. "stock_sector_v2", "theme_detail", "limit_up_reason", "limit_up_info", "lhb_list"
    topic_id: str | None = None        # 题材 ID（部分 kind 有）
    topic_name: str | None = None      # 题材名称
    symbol: str | None = None          # 股票代码（部分 kind 有）
    name: str | None = None            # 名称
    # kind 特定字段
    topic_change_pct: float | None = None
    leader_symbol: str | None = None
    leader_name: str | None = None
    leader_change_pct: float | None = None
    board_num: int | None = None       # 涨停板数量
    net_buy: float | None = None       # 龙虎榜净买入
    brief_intro: str | None = None    # 主题简介


@dataclass(frozen=True)
class TopicConstituentsPayload:
    """题材成分聚合 payload。"""

    trade_date: str
    slot: str
    constituents: list[TopicConstituent] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    fetched_at: datetime | None = None


# ============================
# 强势标的（Strong Symbols）
# ============================

@dataclass(frozen=True)
class StrongSymbol:
    """单个强势标的。"""

    kind: str                           # e.g. "strong_fengkou", "interval_stats_stock", "morning_bidding_list"
    symbol: str | None = None          # 股票代码
    name: str | None = None            # 名称
    strength_score: float | None = None  # 强势得分
    change_pct: float | None = None   # 涨跌幅 %
    turnover: float | None = None      # 成交额
    turnover_ratio: float | None = None  # 换手率 %
    return_pct: float | None = None    # 区间的收益率 %
    net_inflow: float | None = None   # 净流入
    main_force_buy: float | None = None
    main_force_sell: float | None = None
    rt_change_pct: float | None = None  # 竞价涨幅 %
    bid_net: float | None = None       # 竞价净买额
    bid_turnover: float | None = None  # 竞价成交额
    topic_tags: str | None = None      # 题材标签


@dataclass(frozen=True)
class StrongSymbolsPayload:
    """强势标的聚合 payload。"""

    trade_date: str
    slot: str
    symbols: list[StrongSymbol] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    fetched_at: datetime | None = None


# ============================
# 候选池聚合（Market Universe）
# ============================

@dataclass(frozen=True)
class MarketUniverse:
    """候选池顶层聚合结构。

    包含热点、题材成分、强势标的三类数据快照，
    可按需组合供 TraderAgent 或 StrategyAgent 消费。
    """

    trade_date: str
    slot: str
    hot_topics: HotTopicsPayload | None = None
    topic_constituents: TopicConstituentsPayload | None = None
    strong_symbols: StrongSymbolsPayload | None = None
    fetched_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/market_universe/test_schemas.py::test_hot_topic_fields -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/market_universe/schemas.py
git commit -m "feat(s2-008): add HotTopic and HotTopicsPayload schemas"
```

---

### Task 3: 定义 TopicConstituent、TopicConstituentsPayload、StrongSymbol、StrongSymbolsPayload

**Files:**
- Modify: `src/market_universe/schemas.py`（已在上一步创建）
- Test: `tests/unit/market_universe/test_schemas.py::test_topic_constituent_fields`

- [ ] **Step 1: 写失败测试**

```python
def test_topic_constituent_fields():
    """TopicConstituent 应包含所有成分字段。"""
    from src.market_universe.schemas import TopicConstituent

    c = TopicConstituent(
        kind="stock_sector_v2",
        topic_id="ZS001",
        topic_name="人工智能",
        symbol="000001",
        name="平安银行",
        topic_change_pct=2.5,
        leader_symbol="000001",
        leader_name="平安银行",
        leader_change_pct=3.1,
    )
    assert c.kind == "stock_sector_v2"
    assert c.topic_id == "ZS001"
    assert c.topic_name == "人工智能"
    assert c.symbol == "000001"
    assert c.leader_change_pct == 3.1


def test_topic_constituent_optional():
    """TopicConstituent 大部分字段可缺省。"""
    from src.market_universe.schemas import TopicConstituent

    c = TopicConstituent(kind="limit_up_reason", topic_id="ZS001", topic_name="人工智能")
    assert c.symbol is None
    assert c.leader_change_pct is None


def test_strong_symbol_fields():
    """StrongSymbol 应包含所有强势标的字段。"""
    from src.market_universe.schemas import StrongSymbol

    s = StrongSymbol(
        kind="strong_fengkou",
        symbol="000001",
        name="平安银行",
        strength_score=88.0,
        change_pct=5.2,
        turnover=30000.0,
        turnover_ratio=2.5,
        return_pct=8.0,
        net_inflow=15000.0,
        topic_tags="AI，银行",
    )
    assert s.kind == "strong_fengkou"
    assert s.strength_score == 88.0
    assert s.turnover_ratio == 2.5


def test_strong_symbol_optional():
    """StrongSymbol 可缺省字段应默认 None。"""
    from src.market_universe.schemas import StrongSymbol

    s = StrongSymbol(kind="morning_bidding_list", symbol="000001", name="平安银行")
    assert s.strength_score is None
    assert s.return_pct is None
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/unit/market_universe/test_schemas.py::test_topic_constituent_fields -v`
Expected: PASS（schemas.py 已在 Task 2 创建完）

- [ ] **Step 3: Commit**

```bash
git add src/market_universe/schemas.py
git commit -m "feat(s2-008): add TopicConstituent, StrongSymbol and payload schemas"
```

---

### Task 4: 定义 MarketUniverse 聚合结构

**Files:**
- Modify: `src/market_universe/schemas.py`
- Test: `tests/unit/market_universe/test_schemas.py::test_market_universe_aggregates_all`

- [ ] **Step 1: 写失败测试**

```python
def test_market_universe_aggregates_all():
    """MarketUniverse 应聚合三类 payload。"""
    from datetime import datetime
    from src.market_universe.schemas import (
        MarketUniverse,
        HotTopicsPayload,
        TopicConstituentsPayload,
        StrongSymbolsPayload,
        HotTopic,
        TopicConstituent,
        StrongSymbol,
    )

    mu = MarketUniverse(
        trade_date="2026-04-23",
        slot="17-30",
        hot_topics=HotTopicsPayload(
            trade_date="2026-04-23",
            slot="17-30",
            topics=[HotTopic(kind="concept", topic_id="001", topic_name="AI")],
            sources=["board_strength"],
            fetched_at=datetime.now(),
        ),
        topic_constituents=TopicConstituentsPayload(
            trade_date="2026-04-23",
            slot="17-30",
            constituents=[TopicConstituent(kind="limit_up_reason", topic_id="ZS001", topic_name="AI")],
            sources=["limit_up_reason"],
        ),
        strong_symbols=StrongSymbolsPayload(
            trade_date="2026-04-23",
            slot="17-30",
            symbols=[StrongSymbol(kind="strong_fengkou", symbol="000001", name="平安银行", strength_score=85.0)],
            sources=["strong_fengkou"],
        ),
        metadata={"source": "kaipan"},
    )

    assert mu.trade_date == "2026-04-23"
    assert mu.hot_topics is not None
    assert len(mu.hot_topics.topics) == 1
    assert mu.topic_constituents is not None
    assert mu.strong_symbols is not None
    assert mu.strong_symbols.symbols[0].strength_score == 85.0


def test_market_universe_optional_payloads():
    """MarketUniverse 的三类 payload 均可为 None。"""
    from src.market_universe.schemas import MarketUniverse

    mu = MarketUniverse(trade_date="2026-04-23", slot="09-25")
    assert mu.hot_topics is None
    assert mu.topic_constituents is None
    assert mu.strong_symbols is None
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/unit/market_universe/test_schemas.py::test_market_universe_aggregates_all -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/market_universe/schemas.py
git commit -m "feat(s2-008): add MarketUniverse aggregate schema"
```

---

### Task 5: 端到端验证

**Files:**
- Test: `pytest tests/unit/market_universe/ -v`
- Validate: `python -m py_compile src/market_universe/schemas.py`

- [ ] **Step 1: Run all market_universe tests**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && pytest tests/unit/market_universe/ -v`
Expected: ALL PASS（预计 9 个测试）

- [ ] **Step 2: Validate py_compile**

Run: `python -m py_compile src/market_universe/schemas.py && echo "OK"`
Expected: OK

- [ ] **Step 3: 同步 TaskList**

将 `NTL-S2-008` 标记为已完成。

- [ ] **Step 4: Commit**

```bash
git add src/market_universe/schemas.py src/market_universe/__init__.py tests/unit/market_universe/test_schemas.py docs/TaskList.md
git commit -m "feat(s2-008): complete market_universe schemas with all aggregate types"
```

---

## Self-Review Checklist

1. **Spec coverage:** NTL-S2-008 验收标准"候选池的热点、成分、强势股结构统一" - ✅ 覆盖（HotTopicsPayload、TopicConstituentsPayload、StrongSymbolsPayload、MarketUniverse）
2. **Placeholder scan:** 无 TBD/TODO - ✅
3. **Type consistency:** 所有字段使用一致的命名（trade_date, slot, topics/constituents/symbols, sources）- ✅
4. **与 provider 对齐：** provider normalize 输出结构（topics 列表、constituents 列表、symbols 列表）与 schema 一一对应 - ✅

---

## 执行选择

**Plan complete and saved to `docs/superpowers/plans/2026-04-23-market-universe-schemas.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**