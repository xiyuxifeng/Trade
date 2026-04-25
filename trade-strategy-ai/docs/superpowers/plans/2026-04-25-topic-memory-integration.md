# Topic-Memory 完整集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** HotTopic 信息从盘前到盘后完整流转，实现基于 topic 的记忆检索。

**Architecture:**
- `DailyReport` 新增 `market_universe_snapshot` 字段
- `TradeIdea.source_topic_ids` 在生成时被关联
- `run_after_close()` 写入 canonical tags

**Tech Stack:** Python (Pydantic), JSONL, PostgreSQL

---

## 文件清单

| 文件 | 变更 |
|------|------|
| `src/schemas/contracts.py` | 修改：DailyReport 新增 market_universe_snapshot |
| `src/agents/trader_agent/agent.py` | 修改：generate_trade_ideas 关联 HotTopic 到 source_topic_ids |
| `src/agents/manager_agent/agent.py` | 修改：run_pre_market 保存快照 + run_after_close 填充 tags |
| `tests/unit/agents/manager_agent/test_manager_agent.py` | 修改：新增相关测试 |

---

## Task 1: DailyReport 新增 market_universe_snapshot 字段

**Files:**
- Modify: `src/schemas/contracts.py` — `DailyReport` 类

- [ ] **Step 1: 读取当前 DailyReport 定义**

- [ ] **Step 2: 添加 market_universe_snapshot 字段**

```python
class DailyReport(BaseModel):
    # ... 现有字段 ...

    # 新增：候选池快照（供盘后使用）
    market_universe_snapshot: dict[str, Any] | None = None
```

- [ ] **Step 3: 验证 schema**

Run: `python -c "from src.schemas.contracts import DailyReport; print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add src/schemas/contracts.py
git commit -m "feat: add market_universe_snapshot to DailyReport"
```

---

## Task 2: generate_trade_ideas 关联 HotTopic 到 idea.source_topic_ids

**Files:**
- Modify: `src/agents/trader_agent/agent.py` — `generate_trade_ideas()` 方法

- [ ] **Step 1: 找到 generate_trade_ideas 中 Idea 构建的位置**

读取 `src/agents/trader_agent/agent.py`，找到 `TradeIdea(` 构建位置。

- [ ] **Step 2: 添加 topic 关联逻辑**

在 `TradeIdea(` 构建完成后（Stage 4 路径），检查该 symbol 是否在 market_universe 的 hot_topics 中：

```python
# 在 TradeIdea 构建后，关联 topic
if market_universe and market_universe.hot_topics:
    # 查找该 symbol 关联的 HotTopic
    topic_ids = []
    if market_universe.topic_constituents:
        for tc in market_universe.topic_constituents:
            if tc.symbol == symbol and tc.topic_id:
                topic_ids.append(tc.topic_id)
    idea.source_topic_ids = topic_ids
```

- [ ] **Step 3: 验证语法**

Run: `python -c "from src.agents.trader_agent.agent import TraderAgent; print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add src/agents/trader_agent/agent.py
git commit -m "feat: associate HotTopic with TradeIdea in generate_trade_ideas"
```

---

## Task 3: run_pre_market 保存 market_universe_snapshot

**Files:**
- Modify: `src/agents/manager_agent/agent.py` — `run_pre_market()` 方法

- [ ] **Step 1: 找到 DailyReport 构建位置**

读取 `src/agents/manager_agent/agent.py`，找到 `DailyReport(` 构建位置。

- [ ] **Step 2: 添加 market_universe_snapshot 参数**

在 `DailyReport()` 构建时传入快照：

```python
from dataclasses import asdict

# 在 DailyReport 构建时
report = DailyReport(
    ...
    market_universe_snapshot=asdict(market_universe) if market_universe else None,
)
```

- [ ] **Step 3: 验证语法**

Run: `python -c "from src.agents.manager_agent.agent import ManagerAgent; print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add src/agents/manager_agent/agent.py
git commit -m "feat: persist market_universe_snapshot in DailyReport"
```

---

## Task 4: run_after_close 填充 canonical tags

**Files:**
- Modify: `src/agents/manager_agent/agent.py` — `run_after_close()` 中的 TraderMemoryItem 构建

- [ ] **Step 1: 读取 run_after_close 中 TraderMemoryItem 构建的代码**

找到 `self.memory_store.append(TraderMemoryItem(...)` 位置（lines 680-696）。

- [ ] **Step 2: 添加 canonical tag 构建逻辑**

```python
# Canonical tag 构建函数
def _build_topic_tags(
    idea: TradeIdea,
    market_universe_snapshot: dict[str, Any] | None,
) -> tuple[list[str], str | None, dict[str, str] | None]:
    """从 market_universe_snapshot 构建 canonical tags."""
    if not idea.source_topic_ids or not market_universe_snapshot:
        return [], None, None

    from src.market_universe.schemas import MarketUniverse

    mu = MarketUniverse(**market_universe_snapshot)
    hot_topics_map = {ht.topic_id: ht for ht in (mu.hot_topics or [])}

    canonical_tags = []
    raw_ids = {}

    for tid in idea.source_topic_ids:
        ht = hot_topics_map.get(tid)
        if ht:
            canonical_tags.append(f"kaipan:{ht.kind}:{ht.topic_name}")
            raw_ids["kaipan"] = ht.topic_id

    return canonical_tags, "kaipan", raw_ids or None
```

- [ ] **Step 3: 在 TraderMemoryItem 构建时使用**

在 lines 680-696 的 `self.memory_store.append(TraderMemoryItem(...))` 中：

```python
canonical_tags, topic_source, raw_topic_ids = _build_topic_tags(
    idea, daily_report.market_universe_snapshot
)

self.memory_store.append(
    TraderMemoryItem(
        trader_id=idea.trader_id,
        memory_type=memory_type,
        as_of_date=as_of_date,
        symbol=idea.symbol,
        title=f"{idea.symbol} {memory_type.value.replace('_', ' ')}",
        content=(
            f"entry={float(entry_price):.4f}, current={float(current_price):.4f}, "
            f"return_pct={round(return_pct, 6):.6f}, threshold={min_ret:.6f}"
        ),
        source="manager.run_after_close",
        source_ref=str(idea.idea_id),
        tags=["evaluation", memory_type.value] + canonical_tags,
        topic_source=topic_source,
        raw_topic_ids=raw_topic_ids,
        importance=0.8 if memory_type == TraderMemoryType.success_case else 0.9,
    )
)
```

同时在 `_append_review_memory()` 方法中做同样的处理。

- [ ] **Step 4: 验证语法**

Run: `python -c "from src.agents.manager_agent.agent import ManagerAgent; print('OK')"`

- [ ] **Step 5: Commit**

```bash
git add src/agents/manager_agent/agent.py
git commit -m "feat: populate canonical tags in run_after_close memory writing"
```

---

## Task 5: 测试验证

**Files:**
- Modify: `tests/unit/agents/manager_agent/test_manager_agent.py`

- [ ] **Step 1: 添加 DailyReport market_universe_snapshot 测试**

```python
def test_daily_report_has_market_universe_snapshot():
    from src.schemas.contracts import DailyReport

    mu = {"hot_topics": {"topics": []}, "trade_date": "2026-04-25", "slot": "open"}
    report = DailyReport(
        as_of_date=date(2026, 4, 25),
        ideas=[],
        market_universe_snapshot=mu,
    )
    assert report.market_universe_snapshot is not None
    assert report.market_universe_snapshot["trade_date"] == "2026-04-25"
```

- [ ] **Step 2: 添加 canonical tag 构建测试**

```python
def test_build_topic_tags():
    from src.market_universe.schemas import MarketUniverse, HotTopicsPayload, HotTopic

    mu_dict = {
        "trade_date": "2026-04-25",
        "slot": "open",
        "hot_topics": {
            "trade_date": "2026-04-25",
            "slot": "open",
            "topics": [
                HotTopic(
                    kind="concept",
                    topic_id="881121",
                    topic_name="芯片",
                    score=8.5,
                    increase_pct=3.2,
                )
            ],
        },
    }
    mu = MarketUniverse(**mu_dict)

    idea = TradeIdea(
        idea_id=uuid4(),
        trader_id="trader_a",
        as_of_date=date(2026, 4, 25),
        symbol="000001.SZ",
        entry=TradeEntry(price=10.0),
        source_topic_ids=["881121"],
    )

    tags, source, raw = _build_topic_tags(idea, mu_dict)
    assert "kaipan:concept:芯片" in tags
    assert source == "kaipan"
    assert raw == {"kaipan": "881121"}
```

- [ ] **Step 3: 运行所有测试**

Run: `pytest tests/unit/agents/manager_agent/test_manager_agent.py -v`

- [ ] **Step 4: Commit**

```bash
git add tests/... && git commit -m "test: add topic-memory integration tests"
```

---

## 验收标准

1. `DailyReport` 包含 `market_universe_snapshot` 字段
2. `generate_trade_ideas` 中 idea 的 `source_topic_ids` 被正确填充
3. `run_after_close` 写入的 `TraderMemoryItem` 包含正确的 canonical tags
4. 所有新增测试 PASS
