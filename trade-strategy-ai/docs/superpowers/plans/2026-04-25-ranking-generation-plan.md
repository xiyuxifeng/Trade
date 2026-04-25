# NTL-S5-011 盘后生成 Ranking 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `run_after_close` 末尾调用 `RankingService`，生成盘后 ranking 并持久化到 JSON 文件。

**Architecture:**
- 新增 `RankingService.add_entry_from_metrics()` — 直接接收 mfe/mae/return_pct，不依赖 PostmortemService
- 新增 `RankingService.generate_ranking_and_save()` — 生成 ranking 并写入 `{output_dir}/rankings/{trade_date}.json`
- `run_after_close` 末尾：先收集所有 idea 的 metrics，批量 `add_entry_from_metrics`，最后 `generate_ranking_and_save`

**Tech Stack:** Python 3.11+, asyncio, pytest, SQLAlchemy async

---

## 文件清单

| 文件 | 动作 |
|------|------|
| `src/evaluation/ranking_service.py` | 修改：新增 `add_entry_from_metrics` + `generate_ranking_and_save` |
| `src/agents/manager_agent/agent.py` | 修改：`run_after_close` 末尾调用 ranking 生成 |
| `tests/unit/evaluation/test_ranking_service.py` | 修改：新增 `add_entry_from_metrics` 测试用例 |
| `tests/unit/agents/test_manager_agent_ranking.py` | 新建：端到端测试（可选） |

---

## 数据流回顾

```
run_after_close(as_of_date)
│
├── for idea in daily_report.ideas:
│   ├── return_pct = (current_price - entry_price) / entry_price
│   ├── pack = _generate_evidence_pack(idea, ...)
│   ├── _save_evidence_pack(pack)
│   ├── metrics = compute_mfe_mae_return(bars, entry_price, ...)
│   │     └→ mfe, mae, return_pct（从 bars 重新计算，更准确）
│   ├── write memory
│   ├── create postmortem_task
│   └── 【收集】pending_rankings.append((pack, mfe, mae, return_pct))
│
├── 【新增】async with session_scope() as session:
│   ├── ranking_svc = RankingService(session)
│   ├── for pack, mfe, mae, return_pct in pending_rankings:
│   │   └── await ranking_svc.add_entry_from_metrics(pack, mfe, mae, return_pct)
│   └── await ranking_svc.generate_ranking_and_save(trade_date=str(as_of_date))
│
└── return EvaluationResult
```

---

## Task 1: RankingService.add_entry_from_metrics

**Files:**
- Modify: `src/evaluation/ranking_service.py`（在 `add_entry` 方法之后添加）
- Test: `tests/unit/evaluation/test_ranking_service.py`

### 1.1 新增 add_entry_from_metrics 方法

- [ ] **Step 1: 写测试**

```python
# tests/unit/evaluation/test_ranking_service.py 新增

@pytest.mark.asyncio
async def test_add_entry_from_metrics_creates_entry(db_session):
    """直接传入 mfe/mae/return_pct，生成 RankingEntry（NTL-S5-011）"""
    from src.evaluation.ranking_service import RankingService
    from src.evaluation.evidence_pack import EvidencePack
    from src.schemas.contracts import TradeIdea
    from datetime import date
    from uuid import uuid4

    service = RankingService(db_session)

    idea = TradeIdea(
        idea_id=uuid4(),
        trader_id="trader_001",
        as_of_date=date.fromisoformat("2026-04-25"),
        symbol="AAPL",
        side="buy",
        entry={"type": "limit", "price": 150.0},
    )
    pack = EvidencePack(
        idea_id=idea.idea_id,
        trade_date="2026-04-25",
        trade_idea=idea,
        market_data={
            "bars": [
                {"date": "2026-04-25", "open": 150.0, "high": 160.0, "low": 148.0, "close": 155.0}
            ],
            "entry_price": 150.0,
            "target_price": 165.0,
            "stop_loss_price": 140.0,
        },
        strategy_version_id="trader_001_2026-04-25_released",
    )

    entry = await service.add_entry_from_metrics(
        evidence_pack=pack,
        mfe=10.0,
        mae=2.0,
        return_pct=3.333,
    )

    assert entry.mfe == 10.0
    assert entry.mae == 2.0
    assert entry.return_pct == pytest.approx(3.333)
    assert entry.trader_id == "trader_001"
    assert entry.symbol == "AAPL"
    assert entry.strategy_version_id == "trader_001_2026-04-25_released"
    assert entry.attribution_source == "auto"  # 固定为 auto
    assert entry.is_latest is True
```

- [ ] **Step 2: 运行测试验证**

Run: `pytest tests/unit/evaluation/test_ranking_service.py::test_add_entry_from_metrics_creates_entry -v`
Expected: FAIL（method not defined）

- [ ] **Step 3: 实现 add_entry_from_metrics**

在 `ranking_service.py` 的 `add_entry` 方法之后添加：

```python
async def add_entry_from_metrics(
    self,
    evidence_pack: EvidencePack,
    mfe: float,
    mae: float,
    return_pct: float,
) -> RankingEntry:
    """从 metrics 计算结果生成 ranking 条目（NTL-S5-011）。

    用于 run_after_close 场景：此时没有完整的 PostmortemResult，
    但 ranking 数据（mfe/mae/return_pct）在 EvidencePack 生成时就能算出来。

    attribution_source 固定为 "auto"，因为 run_after_close
    没有 LLM validator 参与归因。

    与 add_entry(postmortem, pack) 的区别：
    - add_entry：需要 PostmortemResult（由 PostmortemService.generate() 产生）
    - add_entry_from_metrics：直接接收 metrics 结果，不需要 PostmortemService

    Args:
        evidence_pack: 当前 idea 的 EvidencePack
        mfe: Maximum Favorable Excursion
        mae: Maximum Adverse Excursion
        return_pct: 收益率（%）

    Returns:
        新建的 RankingEntry
    """
    # 从 evidence_pack 提取基本信息
    trade_date = evidence_pack.trade_date
    strategy_version_id = evidence_pack.strategy_version_id or ""
    symbol = ""
    trader_id = ""

    # 从 trade_idea 提取 symbol 和 trader_id
    if evidence_pack.trade_idea:
        if hasattr(evidence_pack.trade_idea, "symbol"):
            symbol = evidence_pack.trade_idea.symbol or ""
        if hasattr(evidence_pack.trade_idea, "trader_id"):
            trader_id = evidence_pack.trade_idea.trader_id or ""

    # 从 signal_context 提取 trader_id（如果 trade_idea 没有）
    if not trader_id and evidence_pack.signal_context:
        if hasattr(evidence_pack.signal_context, "trader_id"):
            trader_id = evidence_pack.signal_context.trader_id or ""

    composite = _compute_composite(return_pct, mfe, mae)

    entry = RankingEntry(
        entry_id=_uuid4(),
        trade_date=trade_date,
        trader_id=trader_id,
        strategy_version_id=strategy_version_id,
        symbol=symbol,
        return_pct=return_pct,
        mfe=mfe,
        mae=mae,
        composite_score=composite,
        rank=None,  # add_entry 时不计算 rank
        is_latest=True,
        idea_id=evidence_pack.idea_id,
        attribution_source="auto",  # run_after_close 无 LLM
        extra={},
    )

    record = await self._repo.upsert(entry)
    return RankingEntry.from_record(record)
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/unit/evaluation/test_ranking_service.py::test_add_entry_from_metrics_creates_entry -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/evaluation/ranking_service.py tests/unit/evaluation/test_ranking_service.py
git commit -m "feat(NTL-S5-011): add RankingService.add_entry_from_metrics"
```

---

## Task 2: RankingService.generate_ranking_and_save

**Files:**
- Modify: `src/evaluation/ranking_service.py`
- Test: `tests/unit/evaluation/test_ranking_service.py`

### 2.1 新增 generate_ranking_and_save 方法

- [ ] **Step 1: 写测试**

```python
# tests/unit/evaluation/test_ranking_service.py 新增

@pytest.mark.asyncio
async def test_generate_ranking_and_save_creates_file(db_session, tmp_path):
    """generate_ranking_and_save 生成 nested + flat 视图并写入文件（NTL-S5-011）"""
    from src.evaluation.ranking_service import RankingService
    from src.evaluation.evidence_pack import EvidencePack
    from src.schemas.contracts import TradeIdea
    from datetime import date
    from uuid import uuid4
    import json

    service = RankingService(db_session)
    # 写入 tmp_path / rankings
    service._output_dir = tmp_path

    idea1 = TradeIdea(
        idea_id=uuid4(), trader_id="trader_001", as_of_date=date.fromisoformat("2026-04-25"),
        symbol="AAPL", side="buy", entry={"type": "limit", "price": 150.0},
    )
    pack1 = EvidencePack(
        idea_id=idea1.idea_id, trade_date="2026-04-25", trade_idea=idea1,
        market_data={"bars": [], "entry_price": 150.0},
        strategy_version_id="v1",
    )
    await service.add_entry_from_metrics(pack1, mfe=10.0, mae=2.0, return_pct=5.0)

    idea2 = TradeIdea(
        idea_id=uuid4(), trader_id="trader_001", as_of_date=date.fromisoformat("2026-04-25"),
        symbol="TSLA", side="buy", entry={"type": "limit", "price": 200.0},
    )
    pack2 = EvidencePack(
        idea_id=idea2.idea_id, trade_date="2026-04-25", trade_idea=idea2,
        market_data={"bars": [], "entry_price": 200.0},
        strategy_version_id="v1",
    )
    await service.add_entry_from_metrics(pack2, mfe=5.0, mae=8.0, return_pct=-2.0)

    result = await service.generate_ranking_and_save(trade_date="2026-04-25")

    # 验证返回值是 nested dict
    assert "nested" in result
    assert "flat" in result
    assert "trader_001" in result["nested"]

    # 验证文件写入
    ranking_file = tmp_path / "rankings" / "2026-04-25.json"
    assert ranking_file.exists()
    with open(ranking_file) as f:
        data = json.load(f)
    assert data["trade_date"] == "2026-04-25"
    assert "nested" in data
    assert "flat" in data
```

- [ ] **Step 2: 运行测试验证**

Run: `pytest tests/unit/evaluation/test_ranking_service.py::test_generate_ranking_and_save_creates_file -v`
Expected: FAIL（method not defined）

- [ ] **Step 3: 实现 generate_ranking_and_save**

在 `RankingService` 类中添加属性和方法的步骤：

**Step 3a: 添加 `_output_dir` 属性到 `__init__`**

找到 `__init__`:
```python
def __init__(self, session: AsyncSession):
    self.session = session
    self._repo = RankingRepository(session)
```

添加：
```python
def __init__(self, session: AsyncSession, output_dir: Path | None = None):
    self.session = session
    self._repo = RankingRepository(session)
    self._output_dir = output_dir or Path(".") / "output"
```

**Step 3b: 添加 generate_ranking_and_save 方法**

在 `generate_ranking` 方法之后添加：

```python
async def generate_ranking_and_save(
    self,
    trade_date: str,
    trader_id: str | None = None,
    strategy_version_id: str | None = None,
) -> dict:
    """生成 ranking 并持久化到文件（NTL-S5-011）。

    调用链路：run_after_close 末尾 -> add_entry_from_metrics() -> 本方法

    文件路径：{output_dir}/rankings/{trade_date}.json

    排序规则（来自 generate_ranking）：
      1. return_pct 降序
      2. return_pct 相同时按 (mfe - mae) 降序
      3. return_pct 为 None 的排在最后

    Args:
        trade_date: 交易日期（YYYY-MM-DD）
        trader_id: 可选，限定 trader
        strategy_version_id: 可选，限定策略版本

    Returns:
        nested view: {trader_id: {strategy_version_id: [RankingEntry...]}}
    """
    # 生成 ranking（计算组内 rank）
    nested = await self.generate_ranking(
        trade_date=trade_date,
        trader_id=trader_id,
        strategy_version_id=strategy_version_id,
        view="nested",
    )

    flat = await self.generate_ranking(
        trade_date=trade_date,
        trader_id=trader_id,
        strategy_version_id=strategy_version_id,
        view="flat",
    )

    result = {
        "trade_date": trade_date,
        "generated_at": datetime.now(UTC).isoformat(),
        "nested": nested,
        "flat": flat,
    }

    # 写入文件
    ranking_dir = self._output_dir / "rankings"
    ranking_dir.mkdir(parents=True, exist_ok=True)
    ranking_file = ranking_dir / f"{trade_date}.json"

    with open(ranking_file, "w") as f:
        json.dump(result, f, indent=2, default=str)

    return result
```

**注意**：需要确认 `generate_ranking` 的返回类型支持 `view` 参数。当前 `generate_ranking` 返回 `dict | list`，需要检查其 `view` 参数处理。

查看当前 `generate_ranking` 的 return 语句位置（在第 202-259 行附近）。

需要在文件顶部添加 `import json`（如果还没有）。

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/unit/evaluation/test_ranking_service.py::test_generate_ranking_and_save_creates_file -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/evaluation/ranking_service.py tests/unit/evaluation/test_ranking_service.py
git commit -m "feat(NTL-S5-011): add RankingService.generate_ranking_and_save"
```

---

## Task 3: 集成到 run_after_close

**Files:**
- Modify: `src/agents/manager_agent/agent.py`

### 3.1 添加 import

在 `agent.py` 顶部 import 区添加：
```python
from src.evaluation.ranking_service import RankingService
from src.db.session import session_scope
```

### 3.2 修改 run_after_close — 收集 pending_rankings

在 `run_after_close` 方法开头（`evaluations: list[IneaEvaluation] = []` 行之后）添加：

```python
# NTL-S5-011: 收集待写入 ranking 的数据
pending_rankings: list[tuple[EvidencePack, float, float, float]] = []
```

在 `for idea in daily_report.ideas:` 循环内，`_save_evidence_pack(evidence_pack)` 之后添加：

```python
# NTL-S5-011: 计算 mfe/mae/return_pct 用于 ranking
mfe_val, mae_val, return_pct_val, _, _ = compute_mfe_mae_return(
    bars=evidence_pack.market_data.get("bars", []),
    entry_price=float(entry_price),
    entry_date=str(as_of_date),
    target_price=evidence_pack.market_data.get("target_price"),
    stop_loss_price=evidence_pack.market_data.get("stop_loss_price"),
)
pending_rankings.append((evidence_pack, mfe_val, mae_val, return_pct_val))
```

### 3.3 修改 run_after_close — 末尾调用 ranking 生成

在 `for idea` 循环结束后（`summary = [...]` 之前，`result = EvaluationResult(...)` 之前）添加：

```python
# NTL-S5-011: 生成盘后 ranking
if pending_rankings:
    async with session_scope() as session:
        ranking_svc = RankingService(session, output_dir=self.output_dir)
        for pack, mfe_val, mae_val, return_pct_val in pending_rankings:
            await ranking_svc.add_entry_from_metrics(
                evidence_pack=pack,
                mfe=mfe_val,
                mae=mae_val,
                return_pct=return_pct_val,
            )
        await ranking_svc.generate_ranking_and_save(trade_date=str(as_of_date))
```

- [ ] **Step 1: 运行测试验证**

Run: `pytest tests/unit/evaluation/ tests/unit/agents/data_agent/ -q`
Expected: PASS（不破坏现有功能）

- [ ] **Step 2: 提交**

```bash
git add src/agents/manager_agent/agent.py
git commit -m "feat(NTL-S5-011): integrate RankingService into run_after_close"
```

---

## Self-Review Checklist

- [ ] **Spec coverage:** 设计文档中每个验收标准都有对应任务
  - ranking 文件生成 → Task 2 (`generate_ranking_and_save`)
  - nested + flat 视图 → Task 2
  - add_entry_from_metrics → Task 1
  - run_after_close 集成 → Task 3
- [ ] **Placeholder scan:** 无 TBD/TODO/占位符
- [ ] **Type consistency:** `add_entry_from_metrics` 返回 `RankingEntry`，与 `add_entry` 一致
- [ ] **No placeholder in code:** 所有函数都有实际实现
- [ ] **Commands correct:** pytest 命令路径正确
