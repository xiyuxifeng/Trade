# NTL-S5-010 盘后评分口径升级设计

> **日期：** 2026-04-25
> **任务：** NTL-S5-010 | 升级盘后评分口径
> **状态：** 已批准

---

## 目标

用 EvidencePack 中的 ohlcv_1d bars 和入场/出场数据，填充 `PostmortemResult.mfe` / `mae` / `return_pct`，替代当前的 None 占位符。

---

## 核心概念

| 指标 | 定义 |
|------|------|
| **MFE**（Maximum Favorable Excursion） | 持仓期间最大有利偏移：入场后最高盈利点数 |
| **MAE**（Maximum Adverse Excursion） | 持仓期间最大不利偏移：入场后最大亏损点数 |
| **return_pct** | 收益率：`exit_price / entry_price - 1` |
| **rules_hit** | 触发决策的 rule_id 列表，来自 SignalContext |
| **exit** | 出场信号触发：target_price 触及 或 stop_loss 触及 |

---

## 设计决策（已确认）

| # | 问题 | 选择 | 理由 |
|---|------|------|------|
| Q1 | exit 价格用什么 | A（当日收盘价 close） | 系统化交易标准，止盈/止损条件"是否触及"用价格比较，成交按收盘价 |
| Q2 | 多空方向 | B（默认只支持做多 buy） | 简化实现，做空场景后续扩展 |
| Q3 | bar 数据范围 | A（entry_date 当日起算） | postmortem 在 T 日盘后触发，entry_date bar 数据已存在 |

---

## 数据流

```
EvidencePack
  ├── market_data.bars: [{date, open, high, low, close, volume}]
  ├── market_data.entry_price: float
  ├── market_data.target_price: float | None
  ├── market_data.stop_loss_price: float | None
  ├── strategy_version_snapshot: [{rule_id, condition, action, confidence}]
  └── signal_context.rules: [rule_id, ...]  # rules_hit 来源

    → metrics_calculator.compute(evidence_pack)
    → (mfe, mae, return_pct, rules_hit, exit_triggered, exit_date)

    → PostmortemResult 填充 mfe/mae/return_pct
    → _auto_attribution(evidence_pack, rules_hit, return_pct)
    → FailureAttribution
```

---

## 计算逻辑

### 1. MFE / MAE 计算

**前提：仅支持做多（buy）**

对 bars 从 `entry_date` 到 `exit_date` 遍历：

```
mfe = max(high_i) - entry_price          # 做多：持仓期间最高价 - 入场价
mae = entry_price - min(low_i)            # 做多：入场价 - 持仓期间最低价
```

**注意：**
- `entry_date` 的 bar 包含在内（当日开盘价买入，当日 bar 的 high/low 都算入持仓区间）
- `exit_date` 的 bar 也算入（出场信号触发的当日）
- 如果 exit 未触发（仍持仓），用当前 bar 的 close 计算 return_pct，MFE/MAE 持续累积

### 2. exit 判定逻辑

遍历 bars 从 `entry_date` 起：

```
for bar in bars[start_index:]:
    if high >= target_price:
        exit_triggered = "target"
        exit_price = bar.close
        break
    if low <= stop_loss_price:
        exit_triggered = "stop_loss"
        exit_price = bar.close
        break
else:
    # 未触发出场，仍在持仓
    exit_triggered = None
    exit_price = bars[-1].close
```

### 3. return_pct 计算

```
return_pct = (exit_price / entry_price - 1) * 100
```

- exit_price 来自上文的 exit 判定
- 单位：百分比（%）

### 4. rules_hit 获取

```python
rules_hit: list[str] = []
if evidence_pack.signal_context and hasattr(evidence_pack.signal_context, 'rules'):
    rules_hit = evidence_pack.signal_context.rules
```

**数据来源：** SignalContext.rules 记录了触发决策的 rule_id 列表（来自策略版本评估时的命中规则）

---

## 归因增强（_auto_attribution）

在 `postmortem_service.py` 的 `_auto_attribution` 方法中增强：

```python
def _auto_attribution(
    self,
    evidence_pack: EvidencePack,
    rules_hit: list[str],
    return_pct: float,
) -> FailureAttribution:
    root_causes: list[str] = []

    # 数据质量问题
    if not evidence_pack.market_data:
        root_causes.append("data_quality_issue")

    # 亏损归因
    if return_pct < 0:
        if not rules_hit:
            # 没有规则依据，入场时机差
            root_causes.append("entry_timing_poor")
        else:
            # 有规则依据但仍亏损，规则前置条件可能未满足
            root_causes.append("rule_precondition_failed")

    return FailureAttribution(root_causes=root_causes)
```

---

## 持续跟踪机制

postmortem 不是一次性事件，而是**持仓期间持续跟踪**：

- 每次盘后都对每个 idea 生成 EvidencePack 并计算 MFE/MAE
- MFE/MAE 是**累积值**（从 entry 到当前）
- `return_pct` 用当前收盘价计算（不是最终 exit 价格）
- 当 exit 触发时，`return_pct` 才用真实 exit 价格，postmortem 标记为"最终报告"

**数据结构扩展：**
在 `postmortem_data` 字段中新增：
```python
{
    "mfe": float,
    "mae": float,
    "return_pct": float,
    "rules_hit": list[str],
    "exit_triggered": str | None,  # "target" | "stop_loss" | None
    "exit_date": str | None,
    "is_final": bool,              # exit 是否已发生
}
```

---

## 扩展路径（Future）

| 方向 | 具体做法 | 改动范围 |
|------|---------|---------|
| 显式 precondition 检测 | 解析 rules_snapshot.condition 字符串，用 market_data 验证条件是否真实满足 | 新增 `rules_checker.py`，改 `postmortem_service.py` |
| 做空支持 | 计算逻辑反转：做空 MFE = entry_price - min(low)，MAE = max(high) - entry_price | 改 `metrics_calculator.py` |
| 规则命中率统计 | 把 rules_hit 数据写入 ranking_service，新增统计维度 | 新增统计逻辑，不改现有流程 |
| 归因细化 | 将 `RULE_PRECONDITION_FAILED` 拆分为 `rule_signal_false` 和 `rule_condition_weak` | 改 `failure_taxonomy.py` |

---

## 改动文件清单

| 文件 | 动作 |
|------|------|
| `src/evaluation/metrics_calculator.py` | 新建：MFE/MAE/return_pct 计算逻辑 |
| `src/evaluation/postmortem_service.py` | 修改：引入 metrics_calculator，增强 _auto_attribution |
| `src/evaluation/ranking_service.py` | 不改（已正确消费 mfe/mae）|
| `src/pipeline/tasks/postmortem_tasks.py` | 不改（调用接口不变）|
| `tests/unit/evaluation/test_metrics_calculator.py` | 新建：单元测试 |

---

## 验收标准

1. `PostmortemResult.mfe` / `mae` / `return_pct` 不再是 None
2. MFE / MAE 计算覆盖 entry_date 到 exit_date 的完整 bars
3. exit 判定正确识别 target_price 触及 和 stop_loss 触及
4. `rules_hit` 非空时亏损归因到 `RULE_PRECONDITION_FAILED`
5. 单元测试覆盖：正常 exit、未触发生成（仍持仓）、数据异常降级
