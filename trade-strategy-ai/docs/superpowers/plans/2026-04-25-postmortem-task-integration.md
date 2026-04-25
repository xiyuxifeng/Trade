# NTL-S5-008 Implementation Plan: postmortem 接入任务系统

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 PostmortemService 接入任务系统，使 run_after_close 为每个未通过评估的 idea 创建 postmortem_analysis 任务，由 process_tasks 执行自动归因并写回 TraderMemory。

**Architecture:** 在 run_after_close 末尾为未通过评估的 idea 创建 postmortem_analysis 任务写入 pending_tasks.jsonl；process_tasks 通过 handle_postmortem_analysis handler 执行归因；归因结果以 TraderMemoryType.postmortem 类型写回 TraderMemory。NTL-S5-009 完成前 handler 内构造最小 EvidencePack。

**Tech Stack:** Python asyncio, SQLAlchemy, JSONL, PostmortemService, TraderMemoryStore

---

## File Structure

| 文件 | 操作 |
|------|------|
| `src/pipeline/tasks/postmortem_tasks.py` | 新增 |
| `src/agents/manager_agent/agent.py` | 修改 |
| `src/pipeline/tasks/process_tasks.py` | 修改 |

---

## Task 1: 创建 postmortem_tasks.py handler

**Files:**
- Create: `trade-strategy-ai/src/pipeline/tasks/postmortem_tasks.py`
- Test: `trade-strategy-ai/tests/unit/pipeline/test_postmortem_tasks.py`

---

- [ ] **Step 1: 写测试文件**

```python
# trade-strategy-ai/tests/unit/pipeline/test_postmortem_tasks.py
from __future__ import annotations
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.pipeline.tasks.postmortem_tasks import handle_postmortem_analysis


class TestHandlePostmortemAnalysis:
    """测试 handle_postmortem_analysis 各种场景"""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.evaluation.min_expected_return = 0.05
        return config

    @pytest.fixture
    def valid_details(self):
        idea_id = str(uuid4())
        return {
            "idea_id": idea_id,
            "trade_date": "2026-04-25",
            "trader_id": "trader_001",
            "symbol": "000001",
        }

    async def test_daily_report_not_found_skips(self, mock_config, valid_details):
        """DailyReport 文件不存在时跳过"""
        with patch("src.pipeline.tasks.postmortem_tasks.DAILY_REPORT_DIR", new_callable=MagicMock()) as mock_dir:
            mock_dir.return_value.exists.return_value = False
            # 不应抛出异常
            await handle_postmortem_analysis(valid_details, config=mock_config)

    async def test_trade_idea_not_in_report_skips(self, mock_config, valid_details):
        """TradeIdea 不在 DailyReport 中时跳过"""
        mock_report = MagicMock()
        mock_report.ideas = []
        with patch("src.pipeline.tasks.postmortem_tasks.DAILY_REPORT_DIR", new_callable=MagicMock()) as mock_dir:
            mock_dir.return_value.exists.return_value = True
            mock_dir.return_value.__truediv__ = MagicMock(return_value=mock_dir)
            with patch("builtins.open", MagicMock()):
                with patch("src.pipeline.tasks.postmortem_tasks.read_json", return_value=mock_report.model_dump()):
                    # 不应抛出异常
                    await handle_postmortem_analysis(valid_details, config=mock_config)
```

---

- [ ] **Step 2: 运行测试验证失败**

```
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
pytest tests/unit/pipeline/test_postmortem_tasks.py -v --tb=short
```
Expected: FAIL — handle_postmortem_analysis not found

---

- [ ] **Step 3: 实现 minimal handler**

```python
# trade-strategy-ai/src/pipeline/tasks/postmortem_tasks.py
"""postmortem_analysis 任务处理器：NTL-S5-008"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.common.config import AppConfig
from src.db.session import session_scope
from src.evaluation.evidence_pack import EvidencePack
from src.evaluation.postmortem_service import PostmortemService
from src.schemas.contracts import DailyReport, DataRequest, DataResponseStatus, read_json
from src.trader_memory.schemas import TraderMemoryItem, TraderMemoryType
from src.trader_memory.store import TraderMemoryStore


async def handle_postmortem_analysis(
    details: dict[str, Any],
    *,
    config: AppConfig,
) -> None:
    """对单笔交易执行自动归因并写回 TraderMemory。

    Details 参数：
        idea_id: UUID string — TradeIdea.idea_id
        trade_date: YYYY-MM-DD — 交易日
        trader_id: str — 用于 TraderMemory
        symbol: str — 用于参考
    """
    idea_id_str: str | None = details.get("idea_id")
    trade_date_str: str | None = details.get("trade_date")
    trader_id: str | None = details.get("trader_id")
    symbol: str | None = details.get("symbol")

    if not idea_id_str or not trade_date_str:
        print(f"[postmortem] idea_id 或 trade_date 缺失，跳过: {details}")
        return

    # 加载 DailyReport
    report_path = _daily_report_path(trade_date_str)
    if not report_path.exists():
        print(f"[postmortem] DailyReport 不存在: {report_path}，跳过")
        return

    report_data = read_json(report_path)
    daily_report = DailyReport.model_validate(report_data)

    # 找到对应 TradeIdea
    trade_idea = None
    for idea in daily_report.ideas:
        if str(idea.idea_id) == idea_id_str:
            trade_idea = idea
            break

    if trade_idea is None:
        print(f"[postmortem] 未找到 idea_id={idea_id_str}，跳过")
        return

    # 获取当前价格
    last_prices = await _fetch_last_prices([symbol or trade_idea.symbol], config)

    # 构造 EvidencePack（NTL-S5-009 完成前：最小实现）
    evidence_pack = EvidencePack(
        idea_id=trade_idea.idea_id,
        trade_date=str(trade_idea.as_of_date),
        trade_idea=trade_idea,
        signal_context=None,
        market_data={"last_price": last_prices.get(symbol or trade_idea.symbol)},
        strategy_version_id=trade_idea.strategy_version_id,
        strategy_version_snapshot=[],
    )

    # 执行自动归因
    service = PostmortemService()
    result = await service.generate(evidence_pack)

    # 写入 TraderMemory
    memory = TraderMemoryItem(
        trader_id=trader_id or trade_idea.trader_id,
        memory_type=TraderMemoryType.postmortem,
        as_of_date=trade_idea.as_of_date,
        symbol=trade_idea.symbol,
        title=f"Postmortem: {trade_idea.symbol} on {trade_idea.as_of_date}",
        content=f"attribution={result.failure_attribution.root_causes}, source={result.attribution_source}",
        source="postmortem_task",
        source_ref=str(trade_idea.idea_id),
        tags=["postmortem", trade_idea.trader_id, trade_idea.symbol],
        topic_source=None,
        raw_topic_ids={},
        importance=0.9,
        postmortem_data={
            "root_causes": result.failure_attribution.root_causes,
            "stage": result.failure_attribution.stage,
            "rule_type": result.failure_attribution.rule_type,
            "attribution_source": result.attribution_source,
            "mfe": result.mfe,
            "mae": result.mae,
            "return_pct": result.return_pct,
        },
    )

    # 追加到 TraderMemoryStore（使用内存 store）
    store = TraderMemoryStore()
    store.append(memory)
    print(f"[postmortem] 已写入 memory for idea_id={idea_id_str}, attribution={result.failure_attribution.root_causes}")


def _daily_report_path(trade_date_str: str) -> Path:
    """获取 DailyReport 路径。"""
    from src.agents.manager_agent.agent import default_output_dir
    output_dir = default_output_dir()
    return output_dir / f"daily_report_{trade_date_str}.json"


async def _fetch_last_prices(symbols: list[str], config: AppConfig) -> dict[str, float]:
    """通过 DataAgent 获取当前价格。"""
    from src.agents.data_agent.agent import DataAgent

    if not symbols:
        return {}

    agent = DataAgent(config=config)
    req = DataRequest(trader_id="postmortem", symbols=symbols, fields=["last_price"])
    resp = await agent.handle(req)

    if resp.status == DataResponseStatus.ok:
        return resp.payload.get("last_price", {})
    return {}
```

---

- [ ] **Step 4: 运行测试验证通过**

```
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
pytest tests/unit/pipeline/test_postmortem_tasks.py -v --tb=short
```
Expected: PASS

---

- [ ] **Step 5: Commit**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
git add src/pipeline/tasks/postmortem_tasks.py tests/unit/pipeline/test_postmortem_tasks.py
git commit -m "feat(NTL-S5-008): add postmortem_analysis task handler"
```

---

## Task 2: 修改 manager_agent/agent.py — 在 run_after_close 添加 postmortem_analysis 任务

**Files:**
- Modify: `trade-strategy-ai/src/agents/manager_agent/agent.py:676-705`

---

- [ ] **Step 1: 查看现有代码确认插入位置**

当前 run_after_close 中，review_task 创建后有以下代码（行 693-705）：

```python
                # 3. 构建任务（带 memory_id，此时 writeback_status=written）
                review_task = self._build_review_task(
                    idea=idea,
                    as_of_date=as_of_date,
                    entry_price=float(entry_price),
                    current_price=float(current_price),
                    return_pct=return_pct,
                    threshold=min_ret,
                    memory_id=memory_id,
                )

                # 4. 落盘（此时 task 已包含完整信息）
                self._append_task(review_task)
```

需要在 `# 4. 落盘` 之后添加 postmortem_analysis 任务。

---

- [ ] **Step 2: 确认 `_append_task` 方法签名**

在 agent.py 中搜索 `_append_task` 方法，确认接受 `AgentTask` 参数。

---

- [ ] **Step 3: 添加 postmortem_analysis 任务创建**

在 `# 4. 落盘` 注释后添加：

```python
                # 4. 落盘（此时 task 已包含完整信息）
                self._append_task(review_task)

                # NTL-S5-008: 创建 postmortem_analysis 任务
                postmortem_task = AgentTask(
                    type="postmortem_analysis",
                    title=f"Postmortem for {idea.symbol} on {as_of_date}",
                    trader_id=idea.trader_id,
                    idea_id=idea.idea_id,
                    details={
                        "idea_id": str(idea.idea_id),
                        "trade_date": str(as_of_date),
                        "trader_id": idea.trader_id,
                        "symbol": idea.symbol,
                    },
                )
                self._append_task(postmortem_task)
```

---

- [ ] **Step 4: 确认 import**

确认 `AgentTask` 已在文件顶部 import（应该已有）。

---

- [ ] **Step 5: Commit**

```bash
git add src/agents/manager_agent/agent.py
git commit -m "feat(NTL-S5-008): create postmortem_analysis task in run_after_close"
```

---

## Task 3: 修改 process_tasks.py — 注册 postmortem_analysis handler

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/process_tasks.py:253-264`

---

- [ ] **Step 1: 查看 _create_handlers 函数确认位置**

找到 `return { ... }` 语句前的 `build_trader_strategy_version_wrapped` 注册位置（行 248-254）。

---

- [ ] **Step 2: 添加 import 和 handler 注册**

在 `handle_build_trader_strategy_version_wrapped` 之后添加：

```python
    # postmortem_analysis handler（NTL-S5-008）
    from src.pipeline.tasks.postmortem_tasks import handle_postmortem_analysis

    async def handle_postmortem_analysis_wrapped(details: dict[str, Any]) -> None:
        await handle_postmortem_analysis(details, config=config)
```

然后在 return dict 中添加：

```python
        "build_trader_strategy_version": handle_build_trader_strategy_version_wrapped,
        "postmortem_analysis": handle_postmortem_analysis_wrapped,
    }
```

---

- [ ] **Step 3: Commit**

```bash
git add src/pipeline/tasks/process_tasks.py
git commit -m "feat(NTL-S5-008): register postmortem_analysis handler in process_tasks"
```

---

## Task 4: 验证集成

---

- [ ] **Step 1: 运行相关测试**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
pytest tests/unit/evaluation/ tests/unit/pipeline/ tests/unit/agents/ -v --tb=short 2>&1 | head -100
```

---

- [ ] **Step 2: 检查 imports 是否正常**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
python -c "from src.pipeline.tasks.postmortem_tasks import handle_postmortem_analysis; print('OK')"
```

---

- [ ] **Step 3: 检查 process_tasks 注册是否正常**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
python -c "from src.pipeline.tasks.process_tasks import TASK_HANDLERS; print('postmortem_analysis' in TASK_HANDLERS)"
```

---

## Task 5: 更新 TaskList.md

**Files:**
- Modify: `trade-strategy-ai/docs/TaskList.md:1201-1208`

---

- [ ] **Step 1: 将 NTL-S5-008 标记为完成**

找到 NTL-S5-008 条目，更新状态：

```
- [x] `NTL-S5-008` `P1` ✅ 2026-04-25
  目标：把 postmortem 接入任务系统。
  ...
  完成情况：新增 `src/pipeline/tasks/postmortem_tasks.py`（handle_postmortem_analysis）；run_after_close 末尾为未通过评估的 idea 创建 postmortem_analysis 任务；process_tasks.py 注册 handler；自动归因结果以 TraderMemoryType.postmortem 写回。
```

---

- [ ] **Step 2: Commit**

```bash
git add docs/TaskList.md
git commit -m "docs(NTL-S5-008): mark complete in TaskList"
```

---

## Spec Coverage Check

- [x] postmortem_analysis task 类型定义 → Task 2
- [x] handler 实现（从 DailyReport 加载 + 构造 EvidencePack + 调用 PostmortemService + 写回 TraderMemory） → Task 1
- [x] process_tasks 注册 handler → Task 3
- [x] run_after_close 修改 → Task 2
- [x] 错误处理（DailyReport 不存在 / idea 找不到） → Task 1
- [x] 测试 → Task 1
- [x] TaskList 更新 → Task 5

## Self-Review

- **Placeholder scan**: 无 TBD/TODO
- **Type consistency**: AgentTask, TraderMemoryItem, PostmortemService, EvidencePack 方法签名与现有代码一致
- **Spec coverage**: 所有 spec 条目均有对应 task
