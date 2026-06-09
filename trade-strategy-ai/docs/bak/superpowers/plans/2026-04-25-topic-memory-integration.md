# Topic-Memory 完整集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> **更新（2026-04-25）：** source_topic_ids 改用 "topic_name|kind" 编码格式，直接从 topic_constituents 生成 canonical tag，不再依赖 hot_topics 查表（原因：hot_topics.topic_id 与 topic_constituents.topic_id ID 空间不同，实测重叠率 0%）。

**Goal:** Topic 信息从盘前到盘后完整流转，实现基于 topic 的记忆检索。

**Architecture:**
- `DailyReport` 新增 `market_universe_snapshot` 字段
- `TradeIdea.source_topic_ids` 存储 "topic_name|kind" 编码格式
- `run_after_close()` 直接解析编码字符串生成 canonical tags

**Tech Stack:** Python (Pydantic), JSONL, PostgreSQL

---

## 文件清单

| 文件 | 变更 |
|------|------|
| `src/schemas/contracts.py` | 修改：DailyReport 新增 market_universe_snapshot |
| `src/agents/trader_agent/agent.py` | 修改：source_topic_ids 存储 "topic_name|kind" 编码 |
| `src/agents/manager_agent/agent.py` | 修改：run_pre_market 保存快照 + _build_topic_tags 解析编码 |
| `tests/unit/agents/manager_agent/test_manager_agent.py` | 修改：新增相关测试 |

---

## Task 1: DailyReport 新增 market_universe_snapshot 字段

**Files:**
- Modify: `src/schemas/contracts.py` — `DailyReport` 类

- [x] **Step 1: 读取当前 DailyReport 定义**

- [x] **Step 2: 添加 market_universe_snapshot 字段**

```python
class DailyReport(BaseModel):
    # ... 现有字段 ...

    # 新增：候选池快照（供盘后使用）
    market_universe_snapshot: dict[str, Any] | None = None
```

- [x] **Step 3: 验证 schema**

Run: `python -c "from src.schemas.contracts import DailyReport; print('OK')"`

---

## Task 2: generate_trade_ideas 关联 topic_constituents 到 source_topic_ids

**Files:**
- Modify: `src/agents/trader_agent/agent.py` — `generate_trade_ideas()` 方法

**注意：** 新方案使用 "topic_name|kind" 编码格式，直接从 topic_constituents 获取，不依赖 hot_topics。

- [x] **Step 1: 找到 generate_trade_ideas 中 Idea 构建的位置**

- [x] **Step 2: 修改 topic 关联逻辑**

```python
# 在 TradeIdea 构建后，从 topic_constituents 关联 topic
# 编码格式："topic_name|kind"，用于后续 canonical tag 生成
if market_universe is not None and market_universe.topic_constituents:
    topic_entries = [
        f"{tc.topic_name}|{tc.kind}"
        for tc in market_universe.topic_constituents.constituents
        if tc.symbol == symbol and tc.topic_name and tc.kind
    ]
    if topic_entries:
        ideas[-1].source_topic_ids = topic_entries
```

- [x] **Step 3: 验证语法**

Run: `python -c "from src.agents.trader_agent.agent import TraderAgent; print('OK')"`

---

## Task 3: run_pre_market 保存 market_universe_snapshot

**Files:**
- Modify: `src/agents/manager_agent/agent.py` — `run_pre_market()` 方法

- [x] **Step 1: 找到 DailyReport 构建位置**

- [x] **Step 2: 添加 market_universe_snapshot 参数**

```python
from dataclasses import asdict

# 在 DailyReport 构建时
report = DailyReport(
    ...
    market_universe_snapshot=asdict(market_universe) if market_universe else None,
)
```

- [x] **Step 3: 验证语法**

Run: `python -c "from src.agents.manager_agent.agent import ManagerAgent; print('OK')"`

---

## Task 4: run_after_close 填充 canonical tags（解析编码格式）

**Files:**
- Modify: `src/agents/manager_agent/agent.py` — `_build_topic_tags()` 方法

**注意：** 新方案直接解析 source_topic_ids 编码字符串，不查 hot_topics。

- [x] **Step 1: 读取 _build_topic_tags 方法**

- [x] **Step 2: 修改为解析 "topic_name|kind" 编码格式**

```python
def _build_topic_tags(
    self,
    idea: "TradeIdea",
    market_universe_snapshot: dict[str, Any] | None,
) -> tuple[list[str], str | None, dict[str, list[str]] | None]:
    """从 market_universe_snapshot 构建 canonical tags。

    source_topic_ids 编码格式："topic_name|kind"
    直接解析编码字符串生成 canonical tag，不依赖 hot_topics 查表。

    Returns:
        tuple of (canonical_tags, topic_source, raw_topic_ids)
        - canonical_tags: ["kaipan:{kind}:{topic_name}", ...]
        - topic_source: provider 名称，如 "kaipan"（有 tags 时才返回）
        - raw_topic_ids: {provider: [encoded_str, ...]}
    """
    if not idea.source_topic_ids or not market_universe_snapshot:
        return [], None, None

    # source_topic_ids 格式："topic_name|kind"（编码字符串）
    # 直接解析生成 canonical tags，不查 hot_topics
    canonical_tags = []
    raw_ids: dict[str, list[str]] = {}

    for encoded in idea.source_topic_ids:
        if "|" not in encoded:
            continue
        parts = encoded.rsplit("|", 1)
        if len(parts) != 2:
            continue
        topic_name, kind = parts
        if topic_name and kind:
            canonical_tags.append(f"kaipan:{kind}:{topic_name}")
            raw_ids.setdefault("kaipan", []).append(encoded)

    return canonical_tags, "kaipan" if canonical_tags else None, raw_ids or None
```

- [x] **Step 3: 在 TraderMemoryItem 构建时使用**

```python
canonical_tags, topic_source, raw_topic_ids = self._build_topic_tags(
    idea, daily_report.market_universe_snapshot
)

self.memory_store.append(
    TraderMemoryItem(
        ...
        tags=["evaluation", memory_type.value] + canonical_tags,
        topic_source=topic_source,
        raw_topic_ids=raw_topic_ids,
        ...
    )
)
```

- [x] **Step 4: 验证语法**

Run: `python -c "from src.agents.manager_agent.agent import ManagerAgent; print('OK')"`

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

- [ ] **Step 2: 添加 _build_topic_tags 编码格式测试**

```python
def test_build_topic_tags_uses_encoded_format():
    """验证 _build_topic_tags 正确解析 'topic_name|kind' 编码格式。"""
    from uuid import uuid4
    from src.schemas.contracts import TradeIdea, TradeEntry

    idea = TradeIdea(
        idea_id=uuid4(),
        trader_id='trader_a',
        as_of_date=date(2026, 4, 25),
        symbol='000001.SZ',
        side='buy',
        entry=TradeEntry(price=10.0),
        source_topic_ids=['芯片|concept', '半导体|industry'],
    )

    # Mock manager agent's _build_topic_tags
    from src.agents.manager_agent.agent import ManagerAgent

    agent = ManagerAgent(...)
    tags, src, raw = agent._build_topic_tags(idea, {'trade_date': '2026-04-25'})

    assert tags == ['kaipan:concept:芯片', 'kaipan:industry:半导体']
    assert src == 'kaipan'
    assert raw == {'kaipan': ['芯片|concept', '半导体|industry']}
```

- [ ] **Step 3: 运行所有测试**

Run: `pytest tests/unit/agents/manager_agent/test_manager_agent.py -v`

---

## 验收标准

1. ✅ `DailyReport` 包含 `market_universe_snapshot` 字段
2. ✅ `generate_trade_ideas` 中 idea 的 `source_topic_ids` 使用 "topic_name|kind" 编码格式
3. ✅ `_build_topic_tags` 直接解析编码字符串生成 canonical tags，不查 hot_topics
4. ✅ `run_after_close` 写入的 `TraderMemoryItem` 包含正确的 canonical tags
5. ⏳ 所有新增测试 PASS（待完成）