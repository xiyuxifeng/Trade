# 2026-04-30 Stage 7 Review (Codex)

> 范围：Stage 7 (S7-000 ~ S7-011) 相关模块（优化、告警、API/CLI 扩展、回测与交易日历补强）。

## 一、整体结论

- 目标对齐度：Stage 7 的主线目标已落地（候选版本双轨、优化筛选/建议、告警、API/CLI、回测稳定性补丁）。
- 可串联性：此前存在 **回测结果 JSON 与 API/CLI 约定不一致**、**RollingEvaluator 默认不可触发** 的问题，现已修复，链路可正常串联。
- A 股约束：交易日历 fallback 已补齐，涨跌停/T+1 等在 Stage 5 已覆盖。Stage 7 未新增违反 A 股约束的逻辑。

## 二、设计目标符合性

### ✅ 符合

- S7-000：回测 CLI 已注入 SnapshotLoader（SnapshotService + StrategyRepoAdapter）用于真实数据加载。
- S7-001：ActiveTraderFilter 实现了贝叶斯收缩 + 样本置信度综合评分。
- S7-002：StrategyAdvisor 有明确规则触发逻辑，能输出结构化调整建议。
- S7-003/003b：候选版本双轨机制完成（文件链路 + DB 链路），且不覆盖 released。
- S7-004：RollingEvaluator 设计完整，支持窗口、频率阈值、样本门槛。
- S7-005/006：API/CLI 对策略、快照、ranking、回测等完成入口扩展。
- S7-007：告警扩展包含规则、聚合、渠道、日志落盘。
- S7-009/010/011：回测结果版本标识、交易日历 fallback、notes 截断已实现。

### ⚠️ 设计落差

- S7-000（已修复）：`_create_engine_from_config` 已改为使用配置中的快照目录，不再硬编码路径。
- S7-003（已修复）：`high_hit_rate_but_negative_return` 增加止损相关字段的轻度收紧；`programmable_but_rarely_hit` 保持删除逻辑，与 TaskList 对齐。

## 三、代码缺陷/风险点

1. **ActiveTraderFilter 与 backtest JSON 结构不一致，可能直接报错（已修复）**
   - `render_backtest_json` 已改为输出数值型 `win_rate/avg_return_pct`；
   - `optimize filter` 增加百分比字符串解析和字段兜底，避免 TypeError。

2. **CLI `optimize filter` 在 `--trader` 场景下有 KeyError 风险（已修复）**
   - 修正 trader 过滤逻辑，未命中时直接提示；
   - 输出使用 `r.trader_id`，避免展示错误。

3. **RollingEvaluator 默认无法触发稳定信号（已修复）**
   - 未注入 `trading_days` 时，自动基于 A 股交易日历生成窗口。

4. **BacktestResults API 与实际 JSON 文件字段不匹配（已修复）**
   - API 兼容 `request_*` 字段，并支持多个结果目录扫描。

## 四、与前序 Stage 串联情况

- **可串联的链路**
  - S7-002 ↔ S6-010：RuleValidationResult 作为输入输出结构一致。
  - S7-003 ↔ S3：StrategyVersion schema 复用，候选版本可追溯父版本。
  - S7-007 ↔ S9：告警日志和 alert.log 与日志规范一致。

- **存在断点的链路（已修复）**
   - S7-001 ↔ S6：BacktestResult JSON 字段和值格式已统一，筛选可正常运行。
   - S7-005（backtest_results API）↔ S6：目录与字段命名兼容已补齐，可正确展示结果。

## 五、A 股市场实际适配性

- ✅ 交易日历：TradeCalendar 增加本地文件 fallback，符合 A 股交易日现实。
- ✅ 价格约束：涨跌停/T+1 约束在 Stage 5 已实现；Stage 7 未新增破坏性逻辑。
- ✅ 滚动评估窗口：未注入交易日列表时已自动生成交易日窗口，可触发调整。

## 六、改进建议（优先级顺序）

1. **统一 BacktestResult JSON schema（已修复）**
   - `render_backtest_json` 输出数值型 `win_rate/avg_return_pct`；
   - `optimize filter` 增加百分比字符串解析；
   - backtest_results API 兼容新旧字段。

2. **修复 `optimize filter` 的 trader 过滤与输出显示（已修复）**
   - trader 命中才取值；
   - 输出使用 `r.trader_id`。

3. **RollingEvaluator 默认 fallback 到 TradeCalendar 生成窗口（已修复）**
   - 未注入 `trading_days` 时自动生成窗口。

4. **S7-000 配置注入与路径统一（已修复）**
   - 快照目录改为读取配置字段。

5. **候选规则调整操作更可解释（已修复）**
   - `review_stop_loss` 增加止损字段轻度收紧与调整记录。

---

## 附：涉及文件

- cli/optimize.py
- src/optimization/active_trader_filter.py
- src/optimization/strategy_advisor.py
- src/optimization/rolling_evaluator.py
- cli/backtest.py
- src/backtest/reporting.py
- src/backtest/schemas.py
- api/routers/backtest_results.py
- src/backtest/engine.py
- src/market_data/strategy_repo_adapter.py
- src/alerting/rules.py
