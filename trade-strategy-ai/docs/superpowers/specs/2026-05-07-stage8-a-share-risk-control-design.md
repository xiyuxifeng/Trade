# 2026-05-07 Stage 8 A 股风控约束设计

## 背景

项目的回测与盘后评分已经进入统一口径，但 A 股市场的交易约束仍需要在同一层里显式建模，避免不同入口对同一标的使用不同的限制规则。当前实现集中在 `src/evaluation/metrics_calculator.py`，并由 `src/backtest/scoring.py` 复用。

## 目标

- 统一 A 股交易约束的推断与补全逻辑
- 让盘后评分与回测复用同一套限制口径
- 明确 ETF、可转债、新股、ST 股票、北交所的差异
- 保持实现轻量，不引入撮合级订单簿仿真

## 核心模型

### `TradeConstraint`

`TradeConstraint` 是所有限制规则的输入容器，包含：

- `t_plus_one`
- `limit_up_pct`
- `limit_down_pct`
- `board_type`
- `market`
- `trade_date`
- `is_new_stock`
- `listing_date`

这个结构允许调用方显式覆盖规则，也允许系统根据 `symbol` 自动补全默认值。

## 板块识别

### `_infer_board_type(symbol)`

当前识别结果包括：

- `main`
- `chinext`
- `star`
- `st`
- `bse`
- `etf`
- `convertible_bond`

识别策略遵循保守优先：

- `ST` 代码优先识别为 `st`
- ETF 前缀识别为 `etf`
- 可转债常见代码段识别为 `convertible_bond`
- 其余数字代码按 A 股常规股票板块识别

## 涨跌停规则

### `_get_limit_pct(board_type, trade_date, market)`

当前设计如下：

- `main`：10%
- `chinext`：20%
- `star`：20%
- `st`：默认 5%，沪市自 2026-07-06 起切换为 10%
- `bse`：30%
- `etf`：10%
- `convertible_bond`：无涨跌幅限制

`trade_date` 只用于 ST 规则切换，不影响其他板块。

## 价格笼子

### `_get_price_cage_pct(board_type)`

价格笼子只用于风控告警和回测记录，不改变成交模拟。当前口径为：

- `main` / `chinext` / `star` / `st`：2%
- `bse`：5%
- `etf`：10%
- `convertible_bond`：30%

这部分的设计目标是“可解释、可记录”，不是撮合级约束。

## 约束解析

### `_resolve_constraint(constraint, symbol)`

解析流程固定为：

1. 如果 `constraint` 为空，使用默认值
2. 如果 `board_type == "auto"`，从 `symbol` 推断板块
3. 如果 `market` 为空，从代码前缀推断沪深市场
4. 如果是新股上市前 5 日，清空涨跌停限制
5. 如果是 ETF 或可转债，强制 `t_plus_one=False`
6. 如果限幅未显式设置，从板块默认值补齐

这样盘后评分和回测的上层调用只需要传入最少字段，也能得到一致的结果。

## 业务边界

本设计明确不覆盖以下内容：

- Level2 级别的订单簿撮合
- 科创板盘后固定价格交易
- 复杂申赎场景的 ETF 分支规则
- 可转债的逐日临停与更细的交易细则

这些内容对当前项目来说属于过拟合，超出 Stage 8 的目标范围。

## 测试策略

已覆盖的测试方向：

- 板块识别测试
- ST 规则切换测试
- ETF / 可转债 默认约束测试
- 涨跌停与价格笼子约束测试

未来如果扩展更多交易品种，测试应先补板块识别，再补约束默认值，最后补回测行为断言。

## 结论

Stage 8 的实现原则是“统一约束口径，保留可覆盖性，避免撮合级过拟合”。当前代码已经按这个设计落地，后续扩展只需要在 `_infer_board_type`、`_get_limit_pct`、`_get_price_cage_pct` 和对应测试上增量维护即可。

