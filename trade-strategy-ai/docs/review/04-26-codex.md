# Stage 6 任务完成情况 Review

> Reviewer: Codex
> 日期: 2026-04-26
> 范围: Stage 6（NTL-S6-001 ~ NTL-S6-013）

## 结论概览

Stage 6 的主模块和测试骨架已落地，回测模块与 Stage 5 的评分口径复用路径清晰，规则验真与复现验证也有最小链路。但**当前实现仍处于“可跑但不完整”的阶段**，存在多标的处理、规则真值判断、A股交易日历、CLI 依赖注入等关键缺口，导致实际回测/规则验真结果容易失真。

## 1. 设计目标符合度与不合理点

- **符合目标**
  - 回测评分复用 Stage 5 口径，没有复制公式，接口适配清晰。[src/backtest/scoring.py](trade-strategy-ai/src/backtest/scoring.py#L12-L53)
  - 引擎/执行/快照加载/报告的模块拆分与 TaskList 目标一致。[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L115-L327)
  - 交易规则约束与 ST 规则切换逻辑已经落入评分组件。[src/evaluation/metrics_calculator.py](trade-strategy-ai/src/evaluation/metrics_calculator.py#L16-L140)

- **与设计偏离**
  - Stage 6 实施计划示例使用 Pydantic BaseModel，但实际用 dataclass，导致请求校验与序列化能力不足。[docs/superpowers/plans/2026-04-25-stage6-implementation-plan.md](trade-strategy-ai/docs/superpowers/plans/2026-04-25-stage6-implementation-plan.md#L109) / [src/backtest/schemas.py](trade-strategy-ai/src/backtest/schemas.py#L10-L35)

## 2. 代码缺陷 / 设计缺陷（按严重度）

### P0（阻塞正确性）

- **单日只处理首个 candidate**，其余推荐被静默丢弃，回测结果显著偏低且与设计“完整回测”目标冲突。[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L235-L250)
- **冻结 dataclass 被运行期修改**，`RuleValidationResult` 定义为 frozen，但 `validate_rules_for_trader` 会赋值字段，运行将触发 `FrozenInstanceError`。[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L78-L85) / [src/backtest/schemas.py](trade-strategy-ai/src/backtest/schemas.py#L120-L150)
- **`entry_date` / `exit_date` 类型不一致**，schema 定义为 `date`，引擎写入 `str`，序列化与后续处理会混乱。[src/backtest/schemas.py](trade-strategy-ai/src/backtest/schemas.py#L64-L72) / [src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L286-L296)

### P1（显著影响结果可靠性）

- **规则命中仅做字段存在性检查**，没有真正判断条件（如 `rsi < 30`），命中率和后验收益统计不可用。[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L353-L383)
- **CLI `run` 未注入 loader / strategy_repo**，实际回测全部走 `no_loader_configured` / `no_strategy_loader` 路径，产出为空结果。[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L180-L217) / [cli/backtest.py](trade-strategy-ai/cli/backtest.py#L49-L58)
- **交易日判断仅跳过周末**，未考虑法定节假日，回测区间包含休市日会生成无效记录。[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L90-L112)

### P2（健壮性/可维护性）

- **`run_sync` 在已有事件循环中会失败**（如异步环境 / Jupyter）。[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L162-L171)
- **规则分类正则过于宽泛**，`ma` 可能误匹配普通英文单词或字段名，导致规则被错误判定为可程序化。[src/backtest/rule_registry.py](trade-strategy-ai/src/backtest/rule_registry.py#L33-L35)

## 3. 与之前 Stage 的串联与数据传递

- **可正常串联**
  - Stage 5 评分口径复用路径正确，未复制公式。[src/backtest/scoring.py](trade-strategy-ai/src/backtest/scoring.py#L12-L53)
  - 快照加载器提供统一 `market_context` 入口，能够承接 Stage 2 快照体系与 Stage 3 策略版本读取。[src/backtest/snapshot_loader.py](trade-strategy-ai/src/backtest/snapshot_loader.py#L17-L124)

- **潜在断点**
  - `SnapshotLoader` 的 `strategy_repo` 与 `BacktestEngine` 的 `strategy_loader` 两套接口未在 CLI 中对齐注入，导致链路“理论可用、实跑为空”。[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L208-L223) / [cli/backtest.py](trade-strategy-ai/cli/backtest.py#L49-L58)
  - `MarketContextSnapshot` 缺少强类型定义，导致上下游字段约束弱，后续对齐成本高。[src/backtest/snapshot_loader.py](trade-strategy-ai/src/backtest/snapshot_loader.py#L40-L123)

## 4. A股市场规则符合度

- **已覆盖**
  - 涨跌停、T+1、停牌识别、ST 规则日期切换已在评分组件内体现。[src/evaluation/metrics_calculator.py](trade-strategy-ai/src/evaluation/metrics_calculator.py#L16-L200)

- **缺口**（未在当前回测链路中发现实现）
  - **最小交易单位 100 股与零股处理**：回测记录和评分中未看到手数约束或零股清算逻辑，交易可行性被高估。
  - **新股上市前 5 日无涨跌幅限制**：目前仅按板块与 ST 规则推断涨跌幅，未覆盖新股特殊规则。
  - **法定节假日**：仅用周末判断交易日，未接入交易日历。[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L90-L112)

## 5. 改进建议（按优先级）

1. **P0**：改为多 candidate 评分与记录（每条 recommendation 生成一条 `BacktestTradeRecord`）。[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L235-L299)
2. **P0**：修复 `RuleValidationResult` frozen 赋值问题（改为非 frozen 或构造时注入）。[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L78-L85) / [src/backtest/schemas.py](trade-strategy-ai/src/backtest/schemas.py#L120-L150)
3. **P0**：统一 `entry_date/exit_date` 类型（建议统一为 `date` 或 `str`，并在 scoring 处转换）。[src/backtest/schemas.py](trade-strategy-ai/src/backtest/schemas.py#L64-L72) / [src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L286-L296)
4. **P1**：实现规则条件判断（至少支持基础数值比较），否则命中率/后验收益无意义。[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L353-L383)
5. **P1**：CLI 注入真实 `SnapshotLoader` 与 `strategy_repo`，让回测命令可用。[cli/backtest.py](trade-strategy-ai/cli/backtest.py#L49-L58)
6. **P1**：接入 A 股交易日历，替代仅周末判断的 `is_trade_date`。[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L90-L112)
7. **P2**：收紧规则分类正则，避免误判；或增加白名单校验。[src/backtest/rule_registry.py](trade-strategy-ai/src/backtest/rule_registry.py#L33-L35)
8. **P2**：若后续需要 API/更强校验，按计划迁移到 Pydantic 模型。[docs/superpowers/plans/2026-04-25-stage6-implementation-plan.md](trade-strategy-ai/docs/superpowers/plans/2026-04-25-stage6-implementation-plan.md#L109) / [src/backtest/schemas.py](trade-strategy-ai/src/backtest/schemas.py#L10-L35)

---

如需我直接修复上述问题或补充 Stage 6 的集成测试，可以给出优先级顺序。