# NTL-S5-010 盘后评分口径升级实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 EvidencePack 中的 ohlcv_1d bars 计算 MFE / MAE / return_pct，填充 PostmortemResult，替代当前的 None 占位符。

**Architecture:**
- 新建 `metrics_calculator.py`（纯计算，无外部依赖），封装 MFE/MAE/return_pct 计算逻辑
- `postmortem_service.py` 引入 calculator，增强 `_auto_attribution` 方法
- `rules_hit` 通过 `signal_context.rules_snapshot` 提取（当前数据的简化方案）

**Tech Stack:** Python 3.11+, asyncio, pytest

---

## 文件清单

| 文件 | 动作 |
|------|------|
| `src/evaluation/metrics_calculator.py` | 新建：MFE/MAE 计算逻辑 |
| `src/evaluation/postmortem_service.py` | 修改：引入 calculator，增强归因 |
| `tests/unit/evaluation/test_metrics_calculator.py` | 新建：单元测试 |

---

## 数据格式约定

**bars**（来自 `EvidencePack.market_data.get("bars", [])`）：
```python
list[dict]  # [{"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0}, ...]
```

**market_data 预期字段：**
```python
{
    "bars": list[dict],           # ohlcv_1d 日线数据
    "entry_price": float,          # 入场价格
    "target_price": float | None, # 止盈价
    "stop_loss_price": float | None,  # 止损价
}
```

---

## Task 1: metrics_calculator.py

**Files:**
- Create: `src/evaluation/metrics_calculator.py`
- Test: `tests/unit/evaluation/test_metrics_calculator.py`

### 1.1 基础数据解析

- [ ] **Step 1: 写测试**

```python
# tests/unit/evaluation/test_metrics_calculator.py
import pytest
from src.evaluation.metrics_calculator import (
    _normalize_bar,
    _find_bar_index,
    _extract_rules_hit,
)

def test_normalize_bar_lowercase():
    bar = {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0}
    result = _normalize_bar(bar)
    assert result == {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0}

def test_normalize_bar_uppercase():
    bar = {"Date": "2026-04-01", "Open": 100.0, "High": 105.0, "Low": 99.0, "Close": 103.0}
    result = _normalize_bar(bar)
    assert result == {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0}

def test_find_bar_index_found():
    bars = [{"date": "2026-04-01"}, {"date": "2026-04-02"}, {"date": "2026-04-03"}]
    assert _find_bar_index(bars, "2026-04-02") == 1

def test_find_bar_index_not_found():
    bars = [{"date": "2026-04-01"}, {"date": "2026-04-02"}]
    assert _find_bar_index(bars, "2026-04-99") is None

def test_extract_rules_hit_from_snapshot():
    rules_snapshot = [
        {"rule_id": "r1", "condition": "ma_50_200_cross"},
        {"rule_id": "r2", "condition": "rsi_oversold"},
    ]
    result = _extract_rules_hit(rules_snapshot)
    assert result == ["r1", "r2"]  # snapshot 中所有 rule_id 作为 rules_hit
```

- [ ] **Step 2: 运行测试验证**

Run: `pytest tests/unit/evaluation/test_metrics_calculator.py -v`
Expected: FAIL（function not defined）

- [ ] **Step 3: 实现基础函数**

```python
# src/evaluation/metrics_calculator.py
"""MFE / MAE / return_pct 计算器（NTL-S5-010）。

职责：
- 从 ohlcv_1d bars 计算持仓期间的 MFE（最大有利偏移）和 MAE（最大不利偏移）
- 计算入场到出场的收益率
- 判定止盈/止损触发
"""

from __future__ import annotations

from typing import Any


def _normalize_bar(bar: dict[str, Any]) -> dict[str, float]:
    """统一 bar 数据格式，兼容不同 key 命名（lowercase / uppercase）。"""
    return {
        "date": bar.get("date") or bar.get("Date") or "",
        "open": float(bar.get("open") or bar.get("Open") or 0),
        "high": float(bar.get("high") or bar.get("High") or 0),
        "low": float(bar.get("low") or bar.get("Low") or 0),
        "close": float(bar.get("close") or bar.get("Close") or 0),
    }


def _find_bar_index(bars: list[dict[str, Any]], target_date: str) -> int | None:
    """在 bars 中查找指定日期的 index，不存在则返回 None。"""
    for i, bar in enumerate(bars):
        normalized = _normalize_bar(bar)
        if normalized["date"] == target_date:
            return i
    return None


def _extract_rules_hit(signal_context_rules_snapshot: list[dict[str, Any]]) -> list[str]:
    """从 SignalContext.rules_snapshot 提取 rules_hit。

    当前简化实现：rules_snapshot 中的每条 rule 都视为参与了决策，
    将其 rule_id 收集为 rules_hit。
    后续可扩展：增加 matched=True 过滤，或从 Signal.triggered_rules 获取。
    """
    return [rule.get("rule_id") for rule in signal_context_rules_snapshot if rule.get("rule_id")]
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/unit/evaluation/test_metrics_calculator.py::test_normalize_bar_lowercase tests/unit/evaluation/test_metrics_calculator.py::test_normalize_bar_uppercase tests/unit/evaluation/test_metrics_calculator.py::test_find_bar_index_found tests/unit/evaluation/test_metrics_calculator.py::test_find_bar_index_not_found tests/unit/evaluation/test_metrics_calculator.py::test_extract_rules_hit_from_snapshot -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/evaluation/metrics_calculator.py tests/unit/evaluation/test_metrics_calculator.py
git commit -m "feat(NTL-S5-010): add metrics_calculator with bar normalization and rules_hit extraction"
```

---

### 1.2 MFE / MAE / return_pct 计算

- [ ] **Step 1: 写测试**

```python
# tests/unit/evaluation/test_metrics_calculator.py 新增以下测试

def test_compute_target_hit():
    """止盈触发：价格涨到 target，exit_price 用当日收盘价。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0},  # entry bar
        {"date": "2026-04-02", "open": 103.0, "high": 110.0, "low": 102.0, "close": 109.0},  # target hit
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date = result
    assert mfe == 10.0      # high=110 - entry=100
    assert mae == 1.0       # entry=100 - low=99
    assert return_pct == pytest.approx(9.0)  # (109/100-1)*100 = 9%
    assert exit_triggered == "target"
    assert exit_date == "2026-04-02"

def test_compute_stop_loss_hit():
    """止损触发：价格跌破 stop_loss。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0},
        {"date": "2026-04-02", "open": 100.0, "high": 101.0, "low": 94.0, "close": 95.0},  # stop hit
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date = result
    assert mfe == 2.0        # high=102 - entry=100
    assert mae == 6.0        # entry=100 - low=94
    assert return_pct == pytest.approx(-5.0)  # (95/100-1)*100 = -5%
    assert exit_triggered == "stop_loss"
    assert exit_date == "2026-04-02"

def test_compute_no_exit_still_holding():
    """未触发出场（仍持仓），用最后 bar close 作为 exit_price。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 103.0, "low": 98.0, "close": 102.0},
        {"date": "2026-04-02", "open": 102.0, "high": 105.0, "low": 100.0, "close": 104.0},
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date = result
    assert mfe == 5.0        # max(high) - entry = 105 - 100
    assert mae == 2.0        # entry - min(low) = 100 - 98
    assert return_pct == pytest.approx(4.0)  # (104/100-1)*100 = 4%
    assert exit_triggered is None
    assert exit_date == "2026-04-02"

def test_compute_entry_date_only():
    """只有 entry_date 的 bar，没有下一日数据。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 103.0, "low": 98.0, "close": 102.0},
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date = result
    assert mfe == 3.0        # high=103 - entry=100
    assert mae == 2.0        # entry=100 - low=98
    assert return_pct == pytest.approx(2.0)  # (102/100-1)*100 = 2%
    assert exit_triggered is None

def test_compute_empty_bars():
    """bars 为空时返回默认值。"""
    result = compute_mfe_mae_return(
        bars=[],
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date = result
    assert mfe == 0.0
    assert mae == 0.0
    assert return_pct == pytest.approx(0.0)
```

- [ ] **Step 2: 运行测试验证**

Run: `pytest tests/unit/evaluation/test_metrics_calculator.py -v`
Expected: FAIL（compute_mfe_mae_return not defined）

- [ ] **Step 3: 实现核心计算**

在 `src/evaluation/metrics_calculator.py` 末尾添加：

```python
def compute_mfe_mae_return(
    bars: list[dict[str, Any]],
    entry_price: float,
    entry_date: str,
    target_price: float | None = None,
    stop_loss_price: float | None = None,
) -> tuple[float, float, float, str | None, str | None]:
    """计算 MFE / MAE / return_pct。

    做多（buy）场景：
    - MFE = max(high_i) - entry_price（持仓期间最大盈利）
    - MAE = entry_price - min(low_i)（持仓期间最大亏损）

    exit 判定：从 entry_date bar 起遍历，遇到 high >= target_price
    则止盈触发（exit_triggered="target"）；遇到 low <= stop_loss_price
    则止损触发（exit_triggered="stop_loss"）。未触发则用最后 bar close。

    Args:
        bars: ohlcv_1d 日线数据 list
        entry_price: 入场价格（元）
        entry_date: 入场日期（YYYY-MM-DD）
        target_price: 止盈价（可选）
        stop_loss_price: 止损价（可选）

    Returns:
        (mfe, mae, return_pct, exit_triggered, exit_date)
        exit_triggered: "target" | "stop_loss" | None
        exit_date: 触发 exit 的日期或 None
    """
    if not bars or entry_price <= 0:
        return (0.0, 0.0, 0.0, None, None)

    # 找 entry bar index
    entry_idx = _find_bar_index(bars, entry_date)
    if entry_idx is None:
        # entry_date 不在 bars 中，从第一条开始（保守处理）
        entry_idx = 0

    mfe = 0.0
    mae = 0.0
    exit_triggered: str | None = None
    exit_date: str | None = None
    exit_price = entry_price  # 默认用 entry_price

    for i in range(entry_idx, len(bars)):
        bar = _normalize_bar(bars[i])
        high = bar["high"]
        low = bar["low"]
        close = bar["close"]
        bar_date = bar["date"]

        # 累计 MFE / MAE
        mfe = max(mfe, high - entry_price)
        mae = max(mae, entry_price - low)

        # 检查止盈
        if target_price is not None and high >= target_price:
            exit_triggered = "target"
            exit_price = close
            exit_date = bar_date
            break

        # 检查止损
        if stop_loss_price is not None and low <= stop_loss_price:
            exit_triggered = "stop_loss"
            exit_price = close
            exit_date = bar_date
            break

        # 未触发：持续更新 exit_price 为当前 bar close（仍持仓）
        exit_price = close
        exit_date = bar_date

    # 计算收益率
    return_pct = (exit_price / entry_price - 1) * 100

    return (mfe, mae, return_pct, exit_triggered, exit_date)
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/unit/evaluation/test_metrics_calculator.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/evaluation/metrics_calculator.py tests/unit/evaluation/test_metrics_calculator.py
git commit -m "feat(NTL-S5-010): add compute_mfe_mae_return with exit detection"
```

---

## Task 2: 集成到 PostmortemService

**Files:**
- Modify: `src/evaluation/postmortem_service.py:1-184`

### 2.1 引入 metrics_calculator

- [ ] **Step 1: 读当前 postmortem_service.py**

确认 generate 方法和 _auto_attribution 方法的具体实现

- [ ] **Step 2: 修改 import**

在文件顶部（`from src.evaluation.failure_taxonomy import FailureAttribution` 之后）添加：
```python
from src.evaluation.metrics_calculator import compute_mfe_mae_return, _extract_rules_hit
```

### 2.2 修改 generate 方法

- [ ] **Step 3: 找到 `return PostmortemResult(...)` 位置**

在 `generate` 方法末尾，找到返回语句，替换为：

```python
    # 计算 MFE / MAE / return_pct（NTL-S5-010）
    bars: list[dict] = evidence_pack.market_data.get("bars", [])
    entry_price: float = evidence_pack.market_data.get("entry_price", 0.0)
    target_price: float | None = evidence_pack.market_data.get("target_price")
    stop_loss_price: float | None = evidence_pack.market_data.get("stop_loss_price")
    trade_date_str = evidence_pack.trade_date

    mfe, mae, return_pct, exit_triggered, exit_date = compute_mfe_mae_return(
        bars=bars,
        entry_price=entry_price,
        entry_date=trade_date_str,
        target_price=target_price,
        stop_loss_price=stop_loss_price,
    )

    # 提取 rules_hit
    rules_hit: list[str] = []
    if evidence_pack.signal_context and evidence_pack.signal_context.rules_snapshot:
        rules_hit = _extract_rules_hit(evidence_pack.signal_context.rules_snapshot)

    return PostmortemResult(
        idea_id=evidence_pack.idea_id,
        trade_date=evidence_pack.trade_date,
        failure_attribution=final_attribution,
        attribution_source=source,
        postmortem_notes=notes,
        mfe=mfe,
        mae=mae,
        return_pct=return_pct,
        extra={
            **extra,
            "rules_hit": rules_hit,
            "exit_triggered": exit_triggered,
            "exit_date": exit_date,
            "is_final": exit_triggered is not None,
        },
    )
```

### 2.3 增强 _auto_attribution 方法

- [ ] **Step 4: 修改 _auto_attribution 签名和实现**

将方法签名改为接受 `rules_hit` 和 `return_pct` 参数：

```python
def _auto_attribution(
    self,
    evidence_pack: EvidencePack,
    rules_hit: list[str],
    return_pct: float,
) -> FailureAttribution:
    """基于 EvidencePack 数据做自动归因（NTL-S5-010 增强）。

    归因逻辑：
    - 数据质量：无 market_data 或 bars 为空
    - 亏损归因（return_pct < 0）：
        - rules_hit 非空 → RULE_PRECONDITION_FAILED（规则前置条件可能未满足）
        - rules_hit 为空 → ENTRY_TIMING_POOR（入场时机差，无规则依据）
    """
    root_causes: list[str] = []

    # 数据质量问题
    if not evidence_pack.market_data or not evidence_pack.market_data.get("bars"):
        root_causes.append("data_quality_issue")

    # 亏损归因
    if return_pct < 0:
        if not rules_hit:
            root_causes.append("entry_timing_poor")
        else:
            root_causes.append("rule_precondition_failed")

    return FailureAttribution(root_causes=root_causes)
```

- [ ] **Step 5: 修改 generate 方法中 _auto_attribution 调用**

找到：
```python
    auto_attribution = self._auto_attribution(evidence_pack)
```

替换为：
```python
    rules_hit_for_attribution: list[str] = []
    if evidence_pack.signal_context and evidence_pack.signal_context.rules_snapshot:
        rules_hit_for_attribution = _extract_rules_hit(evidence_pack.signal_context.rules_snapshot)

    # 计算初步 return_pct（用于归因）
    bars_for_attr: list[dict] = evidence_pack.market_data.get("bars", [])
    entry_price_for_attr: float = evidence_pack.market_data.get("entry_price", 0.0)
    target_price_for_attr = evidence_pack.market_data.get("target_price")
    stop_loss_price_for_attr = evidence_pack.market_data.get("stop_loss_price")
    _, _, return_pct_for_attr, _, _ = compute_mfe_mae_return(
        bars=bars_for_attr,
        entry_price=entry_price_for_attr,
        entry_date=evidence_pack.trade_date,
        target_price=target_price_for_attr,
        stop_loss_price=stop_loss_price_for_attr,
    )

    auto_attribution = self._auto_attribution(
        evidence_pack,
        rules_hit=rules_hit_for_attribution,
        return_pct=return_pct_for_attr,
    )
```

**注意**：这个 double 计算 MFE/MAE 有些冗余（一次归因用，一次填 PostmortemResult 用）。可以在 _auto_attribution 之后把 mfe/mae 等值复用。

- [ ] **Step 6: 运行测试**

Run: `pytest tests/unit/evaluation/ -v`（如果有现有测试）
Expected: PASS（不破坏现有功能）

- [ ] **Step 7: 提交**

```bash
git add src/evaluation/postmortem_service.py
git commit -m "feat(NTL-S5-010): integrate MFE/MAE calculation into PostmortemService"
```

---

## Task 3: 端到端测试

**Files:**
- Create: `tests/unit/evaluation/test_postmortem_with_metrics.py`

- [ ] **Step 1: 写端到端测试**

```python
"""NTL-S5-010 端到端测试：PostmortemResult.mfe/mae/return_pct 不再是 None"""
import pytest
from datetime import date
from uuid import uuid4

from src.evaluation.postmortem_service import PostmortemService
from src.evaluation.evidence_pack import EvidencePack
from src.schemas.contracts import TradeIdea


def make_trade_idea(symbol: str, entry_price: float, as_of_date: str) -> TradeIdea:
    return TradeIdea(
        idea_id=uuid4(),
        trader_id="test_trader",
        as_of_date=date.fromisoformat(as_of_date),
        symbol=symbol,
        side="buy",
        entry={"type": "limit", "price": entry_price},
        target_price=110.0,
        stop_loss_price=95.0,
    )


def make_evidence_pack(
    trade_idea: TradeIdea,
    bars: list[dict],
    entry_price: float,
    target_price: float | None = None,
    stop_loss_price: float | None = None,
) -> EvidencePack:
    market_data = {
        "bars": bars,
        "entry_price": entry_price,
        "target_price": target_price,
        "stop_loss_price": stop_loss_price,
    }
    return EvidencePack(
        idea_id=trade_idea.idea_id,
        trade_date=str(trade_idea.as_of_date),
        trade_idea=trade_idea,
        market_data=market_data,
    )


@pytest.mark.asyncio
async def test_mfe_mae_filled_target_hit():
    """target 触发：mfe/mae/return_pct 全部填入正确值"""
    idea = make_trade_idea("AAPL", entry_price=100.0, as_of_date="2026-04-01")
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0},
        {"date": "2026-04-02", "open": 103.0, "high": 110.0, "low": 102.0, "close": 109.0},
    ]
    pack = make_evidence_pack(idea, bars, entry_price=100.0, target_price=110.0, stop_loss_price=95.0)

    service = PostmortemService()
    result = await service.generate(pack)

    assert result.mfe == 10.0
    assert result.mae == 1.0
    assert result.return_pct == pytest.approx(9.0)
    assert result.extra.get("exit_triggered") == "target"
    assert result.extra.get("is_final") is True


@pytest.mark.asyncio
async def test_mfe_mae_filled_stop_loss_hit():
    """stop_loss 触发：亏损，mfe/mae 仍正确计算"""
    idea = make_trade_idea("AAPL", entry_price=100.0, as_of_date="2026-04-01")
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0},
        {"date": "2026-04-02", "open": 100.0, "high": 101.0, "low": 94.0, "close": 95.0},
    ]
    pack = make_evidence_pack(idea, bars, entry_price=100.0, target_price=110.0, stop_loss_price=95.0)

    service = PostmortemService()
    result = await service.generate(pack)

    assert result.mfe == 2.0
    assert result.mae == 6.0
    assert result.return_pct == pytest.approx(-5.0)
    assert result.extra.get("exit_triggered") == "stop_loss"


@pytest.mark.asyncio
async def test_still_holding_no_exit():
    """未触发出场（仍持仓），return_pct 用当前 bar close"""
    idea = make_trade_idea("AAPL", entry_price=100.0, as_of_date="2026-04-01")
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 103.0, "low": 98.0, "close": 102.0},
        {"date": "2026-04-02", "open": 102.0, "high": 105.0, "low": 100.0, "close": 104.0},
    ]
    pack = make_evidence_pack(idea, bars, entry_price=100.0, target_price=110.0, stop_loss_price=95.0)

    service = PostmortemService()
    result = await service.generate(pack)

    assert result.mfe == 5.0
    assert result.mae == 2.0
    assert result.return_pct == pytest.approx(4.0)
    assert result.extra.get("exit_triggered") is None
    assert result.extra.get("is_final") is False
```

- [ ] **Step 2: 运行测试**

Run: `pytest tests/unit/evaluation/test_postmortem_with_metrics.py -v`
Expected: FAIL（如果 postmortem_service 未更新）或 PASS（验证实现正确）

- [ ] **Step 3: 提交**

```bash
git add tests/unit/evaluation/test_postmortem_with_metrics.py
git commit -m "test(NTL-S5-010): add end-to-end test for MFE/MAE/return_pct filling"
```

---

## Self-Review Checklist

- [ ] **Spec coverage:** 设计文档中每个验收标准都有对应任务
  - MFE/MAE 计算 → Task 1.2
  - exit 判定（target/stop）→ Task 1.2
  - rules_hit → Task 1.1 + Task 2
  - 归因增强（RULE_PRECONDITION_FAILED）→ Task 2.3
  - 单元测试覆盖 → Task 1.1 + Task 1.2 + Task 3
- [ ] **Placeholder scan:** 无 TBD/TODO/占位符
- [ ] **Type consistency:** `compute_mfe_mae_return` 返回 `(float, float, float, str | None, str | None)` 与测试中的 unpack 顺序一致
- [ ] **No placeholder in code:** 所有函数都有实际实现
- [ ] **Commands correct:** pytest 命令路径正确
