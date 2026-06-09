# NTL-S5-013: 替换当前仅基于 current_price 的简化评估逻辑

## 1. 目标

将 `run_after_close` 中基于 `last_prices` 的简化 `return_pct` 计算，升级为统一使用 `compute_mfe_mae_return()` 的 MFE/MAE/return_pct 口径。

## 2. 现状分析

当前 `run_after_close`（agent.py:764）使用简化公式：

```python
return_pct = (float(current_price) - float(entry_price)) / float(entry_price)
```

其中 `current_price` 来自 `DataAgent.last_price`，是评估时刻的快照价格，不是持仓期间的真实波动数据。

已有新口径 `compute_mfe_mae_return()` 可以：
- 从 ohlcv_1d bars 计算 MFE（最大有利偏移）
- 从 ohlcv_1d bars 计算 MAE（最大不利偏移）
- 从 bars 收盘价计算真实 return_pct
- 判断止盈/止损触发
- 判断交易是否结束（`is_final`）

## 3. 升级规则

### 3.1 核心原则

**完全替换**：废弃基于 `last_price` 的 `return_pct` 计算公式，所有盘后评分统一走 MFE/MAE/return_pct 新口径。

### 3.2 计算规则

| 数据情况 | 计算方式 | status |
|----------|----------|--------|
| 有完整 bars（覆盖持仓期） | 使用 `compute_mfe_mae_return()` 计算 | `ok` |
| 有部分 bars（entry_date 之后有数据但不完整） | 使用 `compute_mfe_mae_return()` + 部分 bars 计算 | `partial` |
| 无 bars（完全没有数据） | 降级到 `last_prices` 计算，标记 `fallback` | `fallback` |

### 3.3 部分计算规则（Partial Bars）

当 bars 数据部分缺失时：
- **MFE**：使用 available bars 中的最大值（覆盖期间内）
- **MAE**：使用 available bars 中的最小值（覆盖期间内）
- **return_pct**：使用 available bars 末bar收盘价计算
- **exit_triggered**：无法判断时设为 None
- **is_final**：设为 False（交易未结束）
- extra 中增加 `"partial_data": True` 标记

### 3.4 完全无数据时的 Fallback

当 `evidence_pack.market_data["bars"]` 完全为空时：
- 降级使用 `last_prices[symbol]` 计算 return_pct（等同于旧逻辑）
- status 设为 `"fallback"`
- extra 中增加 `"fallback_reason": "no_bars_data"`
- 记录 warning 日志

### 3.5 Schema 处理（IdeaEvaluation）

`IdeaEvaluation` 字段处理：

| 字段 | 处理方式 |
|------|----------|
| `current_price` | **保留但标注废弃**，仍写入 exit_price（bars 末bar收盘价或 last_price） |
| `return_pct` | 改用新口径计算结果 |
| `entry_price` | 不变 |
| `status` | 扩展：`ok` / `partial` / `fallback` / `not_evaluated` |

> **废弃标注**：在 `IdeaEvaluation` 类注释中标注 `current_price` 字段废弃，未来清理。

### 3.6 extra 扩展字段

`IdeaEvaluation.notes` 扩展：

```python
# 正常
notes = ["mfe=0.05, mae=-0.03, return_pct=0.02, exit_triggered=target"]

# partial
notes = ["[partial] mfe=0.03, mae=-0.02, return_pct=0.01, insufficient_bars"]

# fallback
notes = ["[fallback] return_pct=0.015, reason=no_bars_data"]
```

## 4. 实现步骤

### Step 1: 扩展 IdeaEvaluation schema

- 扩展 `status` 取值（`ok` / `partial` / `fallback` / `not_evaluated`）
- 在类 docstring 中标注 `current_price` 废弃

### Step 2: 重构 run_after_close 评估循环

替换简化公式：

```python
# 旧（废弃）
return_pct = (float(current_price) - float(entry_price)) / float(entry_price)

# 新
bars = evidence_pack.market_data.get("bars", [])
entry_price_val = float(entry_price) if entry_price else 0.0
target_price = evidence_pack.market_data.get("target_price")
stop_loss_price = evidence_pack.market_data.get("stop_loss_price")

mfe_val, mae_val, return_pct, exit_triggered, exit_date = compute_mfe_mae_return(
    bars=bars,
    entry_price=entry_price_val,
    entry_date=str(as_of_date),
    target_price=target_price,
    stop_loss_price=stop_loss_price,
)

# 判断数据情况
if not bars:
    # fallback 到 last_prices
    current_price = last_prices.get(idea.symbol)
    if current_price and entry_price:
        return_pct = (float(current_price) - float(entry_price)) / float(entry_price)
        status = "fallback"
    else:
        status = "not_evaluated"
elif len(bars) < 完整持仓期:
    status = "partial"
else:
    status = "ok"
```

### Step 3: 扩展 IdeaEvaluation 创建逻辑

```python
IdeaEvaluation(
    idea_id=idea.idea_id,
    symbol=idea.symbol,
    entry_price=float(entry_price),
    current_price=exit_price,  # 标注废弃，但仍写入
    return_pct=round(return_pct, 6),
    status=status,
    notes=[f"mfe={mfe_val:.4f}, mae={mae_val:.4f}, exit={exit_triggered}"],
)
```

### Step 4: 废弃标注

在 `src/schemas/contracts.py` 的 `IdeaEvaluation` 类添加 docstring 标注废弃字段。

### Step 5: 测试

- 覆盖正常 bars / partial bars / 无 bars 三种场景
- 验证 status 值正确
- 验证 return_pct 计算正确性

## 5. 验证标准

1. `run_after_close` 中无 `current_price` 简化公式调用
2. 所有评估走 `compute_mfe_mae_return()`
3. bars 不足时有正确的降级处理
4. `IdeaEvaluation.status` 正确反映数据情况
5. 单元测试覆盖所有场景

## 6. 风险

- `last_prices` 获取可能失败 → 已有 `not_evaluated` 处理
- `compute_mfe_mae_return()` 依赖 bars 数据完整性 → partial 和 fallback 处理覆盖
