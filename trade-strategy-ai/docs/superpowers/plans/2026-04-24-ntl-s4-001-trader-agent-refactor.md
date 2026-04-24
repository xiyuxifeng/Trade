# Plan: NTL-S4-001 - 重构 TraderAgent 输入

## 目标

重构 `TraderAgent` 输入，使其接受 `StrategyVersion`（已发布版本）、`MarketUniverse`（候选池快照）、画像和记忆，不再以 `watchlist` 为核心候选来源。

## 验收标准

- TraderAgent 不再以 watchlist 为核心输入
- `generate_trade_ideas` 可接受 StrategyVersion + MarketUniverse + TraderProfile + TraderMemoryStore
- 候选标的来源从 strategy_version.recommendations 派生（而非 watchlist）
- strong_symbols 提供强势标的上下文和评分参考
- 保留 memory hint 和 profile hint 生成逻辑
- Phase 0 兼容逻辑：当未传入 strategy_version 时，降级到原有 watchlist 逻辑

---

## Step 1: 分析当前实现

**文件**: `src/agents/trader_agent/agent.py`

当前 `generate_trade_ideas` 方法：
- 输入：`as_of_date`, `data_agent`
- 候选来源：`_candidate_symbols()` = `trader.watchlist` + `profile.top_symbols`
- 数据获取：`DataRequest(fields=["last_price"])`
- 输出：`List[TradeIdea]`

---

## Step 2: 设计新接口

### 新增参数（作为生成器的输入，非 `__init__`）

```python
async def generate_trade_ideas(
    self,
    *,
    as_of_date: date,
    data_agent,
    strategy_version: StrategyVersion | None = None,   # 新增
    market_universe: MarketUniverse | None = None,    # 新增
) -> list[TradeIdea]:
```

### 候选标的派生逻辑

```
if strategy_version is not None:
    # Stage 4 路径：基于策略版本推荐
    candidates = [
        (rec.symbol, rec.decision, rec.confidence)
        for rec in strategy_version.recommendations
        if rec.decision in ("buy", "hold")
    ]
    # 用 strong_symbols 做额外上下文标注
elif trader.watchlist:
    # Phase 0 兼容路径（watchlist 不为空）
    candidates = self._candidate_symbols()
else:
    return []
```

### 行情获取

仍然需要 `last_price` 来计算 `entry_price`、`target_price`、`stop_loss_price`：
```python
req = DataRequest(
    trader_id=self.trader.trader_id,
    symbols=[sym for sym, _, _ in candidates],
    fields=["last_price"],
)
```

---

## Step 3: 修改代码

### 3.1 添加 TYPE_CHECKING import

```python
from __future__ import annotations
from typing import TYPE_CHECKING

from src.market_universe.schemas import MarketUniverse
from src.strategy_library.schemas import StrategyVersion

if TYPE_CHECKING:
    from src.agents.data_agent import DataAgent
```

### 3.2 新增 `_candidates_from_strategy` 私有方法

从 `strategy_version.recommendations` 提取候选标的列表（symbol, side, confidence）。

### 3.3 修改 `generate_trade_ideas` 签名

```python
async def generate_trade_ideas(
    self,
    *,
    as_of_date: date,
    data_agent,  # DataAgent
    strategy_version: StrategyVersion | None = None,
    market_universe: MarketUniverse | None = None,
) -> list[TradeIdea]:
```

### 3.4 修改候选标的派生逻辑

替换原有的 `_candidate_symbols()` 调用逻辑：
- 有 `strategy_version` → 使用 `_candidates_from_strategy()`
- 无 `strategy_version` 但 `watchlist` 非空 → 降级到 `_candidate_symbols()`（Phase 0 兼容）
- 两者都无 → 返回空列表

### 3.5 新增 `_strong_symbol_hint` 方法（可选）

从 `market_universe.strong_symbols` 中提取标的对应的强势评分，生成提示文本。

### 3.6 修改 TradeIdea 生成逻辑

对每个候选标的：
- entry_price 从 last_price 获取
- target_price / stop_loss_price 仍使用配置百分比（`default_target_pct` / `default_stop_pct`）
- rationale 中补充 strategy_version 相关来源信息（如 version_id）
- 当 `market_universe.strong_symbols` 存在时，标注标的的 `strength_score` 和 `change_pct`
- confidence 优先使用 strategy_version 中的值（若存在），否则降级到原 confidence 计算逻辑

### 3.7 更新类 docstring

在类 docstring 中说明新的输入参数含义和 Phase 0 降级行为。

---

## Step 4: 验证

1. 运行现有测试：`tests/unit/agents/test_trader_agent.py`
2. 确保向后兼容：Phase 0 降级路径仍然可用
3. `python -m py_compile src/agents/trader_agent/agent.py` 无错误

---

## 依赖文件

- `src/agents/trader_agent/agent.py`（主要修改）
- `src/market_universe/schemas.py`（MarketUniverse, StrongSymbolsPayload, StrongSymbol）
- `src/strategy_library/schemas.py`（StrategyVersion, StrategyRecommendation）
- `tests/unit/agents/test_trader_agent.py`（回归测试）

## 不修改的文件

- `src/agents/data_agent/agent.py`（DataAgent 路由不属于本任务范围）
- `src/agents/manager_agent/agent.py`（Manager 编排属于 NTL-S4-006）
- `src/strategy/` 相关文件（Signal 类型扩展属于 NTL-S4-004）
