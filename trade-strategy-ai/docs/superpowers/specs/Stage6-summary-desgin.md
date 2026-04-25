# Stage 6 Summary Design

> 日期：2026-04-25
> 对应范围：`docs/TaskList.md` Stage 6（`NTL-S6-001` ~ `NTL-S6-013`）
> 状态：设计草案

---

## 1. 目标与范围

Stage 6 的目标不是做“泛化回测平台”，而是围绕当前主线建立一套可复现、可解释、可与线上评分对账的离线验证系统。

唯一主线：

`历史快照 -> 历史策略版本 -> 离线执行 -> 与线上一致的 scoring -> 回测报告 -> 规则验真 -> 复现验证`

本阶段明确排除：

- 不做分钟级/逐笔级高频回测。
- 不做自动参数寻优。
- 不做真实下单模拟撮合。
- 不继续扩展 `src/agents/backtest_agent/` 为主线实现。

本阶段必须达成：

- 能按 `trader_id + 日期区间` 离线重放当日“当时可见”的输入。
- 能输出与 Stage 5 一致口径的 `return_pct / mfe / mae / ranking features`。
- 能对高频 LLM 规则做程序化命中验证，并形成覆盖率与后验收益报告。

---

## 2. Stage 6 在全局架构中的位置

Stage 6 不是独立系统，而是依赖 Stage 2、3、5 的验证层。

### 2.1 上游依赖

| 阶段 | 依赖内容 | Stage 6 用途 |
|------|----------|--------------|
| Stage 2 | 市场快照、`ohlcv_1d`、`hot_topics`、`topic_constituents`、`strong_symbols` | 提供离线市场输入 |
| Stage 3 | `StrategyVersion`、`rules_snapshot`、recommendations | 提供离线决策输入 |
| Stage 4 | `TradeIdea` 生成路径、SignalContext 追溯字段 | 提供线上主链路参照 |
| Stage 5 | `EvidencePack`、`compute_mfe_mae_return()`、ranking/postmortem | 提供统一评分口径 |

补充说明：

- `market_universe` 快照用于恢复“当日候选池上下文”。
- 标准化 `ohlcv_1d` 历史 bars 应从独立历史行情资产读取，而不是从 `market_universe` 快照推导。
- `SignalVersioning` / `EvidencePack` 只作为连续性补洞和对账来源，不作为正式主输入。

### 2.2 新增核心模块

Stage 6 应新建 `src/backtest/`，而不是复用旧 `backtest_agent`。

建议目录：

```text
src/backtest/
├── __init__.py
├── schemas.py              # BacktestRequest / Result / RuleValidationResult
├── snapshot_loader.py      # 快照与历史行情读取
├── strategy_replayer.py    # 历史策略版本重放（execution.py 的内部依赖）
├── execution.py            # 交易执行/持仓推进（与 TaskList 保持一致）
├── scoring.py              # 离线 scoring 适配层
├── engine.py               # 回测引擎编排
├── reporting.py            # 回测与规则验真报告
├── rule_registry.py        # LLM 规则白名单与程序化映射
└── reproducibility.py      # 复现校验工具
```

说明：

- `src/agents/backtest_agent/` 保留为历史目录，只读不扩展。
- Stage 6 的真实入口统一收敛到 `src/backtest/` + `cli/backtest.py`。
- `cli/backtest.py` 当前是空占位文件，Stage 6 应扩展该文件，而不是新增并行 CLI 入口。

### 2.3 连续性审查结果

在进入 Stage 6 实现前，必须先处理以下跨 Stage 连续性问题：

1. `StrategyVersion.rules_snapshot` 需要做历史兼容性审计  
当前代码已补齐 `rules_snapshot` 的持久化与发布链路，但历史上已经落库/落盘的数据仍可能缺失该字段，因此 Stage 6 仍需先做兼容性审计与补洞策略。

2. `market_universe` 快照与历史行情 bars 不是同一资产  
当前 `SnapshotService` 持久化的是候选池快照，不包含完整 `bars`。Stage 6 不能把候选池快照误当作完整市场数据源。

3. 已存在可追溯补充来源，但只能作为兼容兜底  
Stage 4/5 已把 `strategy_version_id`、`market_universe_snapshot`、`rules_snapshot` 写入 `SignalVersioning` 和 `EvidencePack`。这些资产可用于对账或补历史缺口，但不能替代 Stage 6 的正式主路径。

对应原则：

- Stage 6 plan 必须先安排“历史数据连续性补丁/校验”步骤。
- 正式主路径仍然是：`released StrategyVersion + historical snapshots + standardized bars`。
- `SignalVersioning` / `EvidencePack` 仅用于兼容核对和缺失场景诊断。

---

## 3. A 股规则基线与设计约束

Stage 6 的回测不是任意金融回测，必须遵守 A 股交易制度约束。以下规则作为设计基线写入回测约束层。

### 3.1 已确认并应参数化的市场规则

截至 2026-04-25，设计应按以下规则建模，并避免硬编码单一数值：

| 规则项 | 当前设计基线 | 设计要求 |
|--------|--------------|----------|
| 普通 A 股主板涨跌幅 | 默认 `10%` | 参数化，按板块/证券类型判定 |
| 科创板涨跌幅 | `20%` | 参数化，支持上市前 5 日无涨跌幅限制 |
| 创业板涨跌幅 | `20%` | 参数化，支持上市前 5 日无涨跌幅限制 |
| 风险警示股票（ST/*ST） | 当前需配置化，不允许硬编码为永久 `5%` | 因上交所已于 2026-04-24 发布 2026 年修订规则，且 2026-07-06 起沪市主板风险警示股票涨跌幅调整为 `10%`，因此必须用“按市场 + 生效日期”的规则配置 |
| T+1 | 当日买入股票不得当日卖出 | 必须建模为持仓可卖出日约束 |
| 最小交易单位 | 买入通常为 `100` 股整数倍，零股仅允许卖出残股 | 在执行器中建模申报/成交约束 |
| 零股处理 | 余额不足 `100` 股可一次性卖出 | 在持仓清算时支持残股一次卖出 |

### 3.2 Stage 6 对规则的实现原则

1. 不把规则散落在 `engine/executor/scoring` 多处。
2. 建立单独的 `MarketRuleSet` / `TradingConstraintSet`。
3. 所有规则必须支持：
   - `market`
   - `board_type`
   - `security_status`
   - `trade_date`
4. 规则变更必须可以按日期切换，而不是只能覆盖当前值。

建议数据结构：

```python
@dataclass(frozen=True)
class TradingConstraintSet:
    market: str
    board_type: str
    trade_date: date
    lot_size: int
    t_plus_n_sell: int
    price_limit_pct: float | None
    allow_intraday_roundtrip: bool
    first_n_days_no_limit: int
    residual_sell_allowed: bool
```

### 3.3 官方规则参考

设计编写时已参考以下官方页面：

- 上交所 2026-04-24《上海证券交易所交易规则（2026年修订）》发布说明：风险警示股票涨跌幅将自 2026-07-06 调整为 `10%`
- 上交所科创板交易特别规定/投教材料：科创板竞价交易涨跌幅 `20%`，新股上市前 `5` 个交易日无涨跌幅限制
- 深交所创业板投教材料：创业板涨跌幅 `20%`，新股上市前 `5` 个交易日无涨跌幅限制
- 上交所/深交所关于竞价交易申报数量通知：股票买卖以 `100` 股为基本单位，残股可一次性卖出

在实现层，不直接把网页文字写死到代码；统一转为可版本化配置。

---

## 4. 总体数据流

### 4.1 回测主链路

```text
Backtest CLI / API Request
        ->
BacktestRequest(trader_id, date_range, strategy_version_id?, mode)
        ->
SnapshotLoader
  -> load market_universe snapshot
  -> load standardized ohlcv_1d / bars
  -> load topic snapshots
        ->
StrategyReplayer
  -> load released StrategyVersion
  -> restore rules_snapshot / recommendations
        ->
Executor
  -> reconstruct daily candidate set
  -> generate simulated trade ideas / positions
  -> apply A-share constraints
        ->
Shared Scoring Adapter
  -> compute return_pct / mfe / mae / exit state
        ->
BacktestEngine
  -> aggregate by trader / version / symbol / day
        ->
Reporting
  -> summary report
  -> rule validation report
  -> reproducibility report
```

### 4.2 规则验真链路

```text
StrategyVersion.rules_snapshot / extracted rules
        ->
RuleRegistry (白名单 + 字段映射 + 程序化适配器)
        ->
Historical Snapshots / Bars
        ->
Rule Validator
  -> hit / miss
  -> unavailable_field
  -> unsupported_rule
        ->
RuleValidationResult
        ->
Reporting
  -> 覆盖率
  -> 命中率
  -> hit 后验收益分布
```

---

## 5. 核心数据模型

### 5.1 BacktestRequest

```python
class BacktestRequest(BaseModel):
    trader_id: str
    date_from: date
    date_to: date
    strategy_version_id: str | None = None
    symbols: list[str] = Field(default_factory=list)
    mode: Literal["replay", "rule_validation", "full"] = "full"
    use_snapshot_only: bool = True
    scoring_profile: str = "stage5"
```

约束：

- `date_from <= date_to`
- `strategy_version_id` 为空时，按 `trader_id + trade_date` 读取历史 released 版本
- `use_snapshot_only=True` 时禁止任何实时 provider 调用

### 5.2 BacktestTradeRecord

```python
class BacktestTradeRecord(BaseModel):
    trade_date: date
    trader_id: str
    strategy_version_id: str
    symbol: str
    entry_price: float | None
    exit_price: float | None
    entry_date: date | None
    exit_date: date | None
    return_pct: float | None
    mfe: float | None
    mae: float | None
    status: Literal["open", "closed", "skipped", "invalid"]
    skip_reason: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
```

### 5.3 RuleValidationResult

```python
class RuleValidationResult(BaseModel):
    trader_id: str
    strategy_version_id: str
    rule_id: str
    rule_text: str
    programmable: bool
    validation_status: Literal[
        "validated",
        "unsupported_rule",
        "missing_field",
        "missing_snapshot",
        "invalid_rule",
    ]
    hit_count: int = 0
    sample_count: int = 0
    hit_rate: float | None = None
    posterior_return_mean: float | None = None
    posterior_return_median: float | None = None
    notes: list[str] = Field(default_factory=list)
```

### 5.4 MarketContextSnapshot

Stage 6 不直接扩大 `EvidencePack`，但应定义离线回放内部标准上下文：

```python
class MarketContextSnapshot(TypedDict):
    trade_date: str
    market_universe: dict[str, Any] | None
    bars_by_symbol: dict[str, list[dict[str, Any]]]
    indicators_by_symbol: dict[str, dict[str, Any]]
    topic_snapshot: dict[str, Any] | None
    source_refs: list[str]
```

---

## 6. 任务级设计

以下内容按 `TaskList` 顺序展开。

### 6.1 `NTL-S6-001` 建立回测输入输出契约

**目标**

统一 Stage 6 的请求、结果、报告、规则验证输出，避免 CLI、engine、reporting 各自定义结构。

**实现说明**

- 新建 `src/backtest/schemas.py`
- 定义：
  - `BacktestRequest`
  - `BacktestResult`
  - `BacktestTradeRecord`
  - `RuleValidationResult`
  - `BacktestSummary`
- 保持与 Stage 5 的字段命名一致：
  - `return_pct`
  - `mfe`
  - `mae`
  - `strategy_version_id`
  - `trader_id`
  - `symbol`

**约束**

- 不重新发明与 Stage 5 冲突的评分字段。
- 所有时间字段必须使用绝对日期，不允许相对日期字符串。
- 所有输出都必须可 JSON 序列化，以便 CLI 直接落盘。

**数据流向**

`CLI/API -> BacktestRequest -> engine -> BacktestResult -> reporting/json`

**失败处理**

- 非法日期区间：请求校验直接失败
- 请求字段不足：返回结构化校验错误

**验收标准**

- CLI、engine、reporting 使用同一份 schema
- 核心结果可被测试和 JSON 文件复用

---

### 6.2 `NTL-S6-002` 建立策略版本回放执行器

**目标**

从历史 `StrategyVersion` 和历史快照中恢复“某天该 trader 理论上能看到什么、会基于什么规则做决策”。

**实现说明**

- 新建 `src/backtest/execution.py`
- 可选拆分内部辅助模块 `src/backtest/strategy_replayer.py`
- 输入：
  - `StrategyVersion`
  - `MarketContextSnapshot`
  - `TraderProfile`（如需要）
- 输出：
  - `ReplayedDecisionContext`
  - `TradeIdea` 或回测内部候选对象

建议拆分：

- `load_version_for_date(trader_id, trade_date)`
- `replay_candidates(version, market_context)`
- `replay_rules(version, market_context)`
- `apply_execution_constraints(position_state, trading_constraints)`

实现前置检查：

- 若 `StrategyVersion` 读回后 `rules_snapshot` 为空，必须先判定是“历史版本本身为空”还是“持久化丢失”。
- 对于“持久化丢失”的历史数据，允许临时从 `SignalVersioning` / `EvidencePack` 做兼容性补齐，但必须打标，不可视为正式长期方案。

**约束**

- 不调用实时 `DataAgent`
- 不重算“未来知道的信息”
- 只允许消费 `trade_date` 当时已经落盘的快照和 released version

**数据流向**

`StrategyVersionRepository + SnapshotLoader -> StrategyReplayer -> candidate decisions`

**失败处理**

- 缺失 released version：标记 `skipped`
- 版本存在但 `rules_snapshot` 为空：允许进入 recommendation-only 降级模式

**验收标准**

- 可按 `trader_id + trade_date` 回放出稳定的决策输入
- 同一输入多次重放结果一致

---

### 6.3 `NTL-S6-003` 建立回测评分模块

**目标**

建立 Stage 6 的离线评分适配层，但不复制 Stage 5 业务逻辑。

**实现说明**

- 新建 `src/backtest/scoring.py`
- 该模块不自行发明评分公式，只负责把回测执行结果适配到 Stage 5 评分接口
- 优先复用：
  - `src/evaluation/metrics_calculator.py`
  - `src/evaluation/postmortem_service.py` 可复用的公共逻辑

建议接口：

```python
def score_backtest_trade(
    *,
    bars: list[dict[str, Any]],
    entry_price: float,
    entry_date: str,
    target_price: float | None,
    stop_loss_price: float | None,
) -> dict[str, Any]:
    ...
```

**约束**

- `return_pct` 必须继续使用比例口径（`0.01 = 1%`）
- 字段命名必须与 Stage 5 完全一致
- 不允许出现线下口径独立分叉

**数据流向**

`Executor output -> scoring adapter -> trade metrics`

**失败处理**

- bars 缺失：输出 `partial/not_evaluable`
- 入场价缺失：输出 `invalid`

**验收标准**

- 给定同一笔案例，线上与线下指标差异必须可解释

---

### 6.4 `NTL-S6-004` 建立回测引擎

**目标**

把“版本读取、快照读取、执行、评分、汇总”串成一个可重复运行的引擎。

**实现说明**

- 新建 `src/backtest/engine.py`
- 核心职责：
  - 遍历日期区间
  - 逐日加载 released version
  - 逐日加载市场快照
  - 调用 `strategy_replayer`
  - 调用 `executor`
  - 调用 `scoring`
  - 聚合为 `BacktestResult`

建议主接口：

```python
class BacktestEngine:
    async def run(self, request: BacktestRequest) -> BacktestResult:
        ...
```

**约束**

- 引擎只负责编排，不负责任何交易规则细节
- 交易规则应下沉到 `executor` / `TradingConstraintSet`
- 输出必须包含：
  - per-trade records
  - per-day summary
  - per-version summary
  - warnings/errors

**数据流向**

`BacktestRequest -> Engine -> {Loader, Replayer, Executor, Scoring} -> BacktestResult`

**失败处理**

- 单日失败不应中断整个区间回测
- 采用“收集错误 + 继续回放”的策略

**验收标准**

- 能按 `trader_id / 日期区间` 完整输出回测结果

---

### 6.5 `NTL-S6-005` 建立回测报告模块

**目标**

把机器结果转换为人能读、能对账、能用于决策的输出。

**实现说明**

- 新建 `src/backtest/reporting.py`
- 输出格式至少包括：
  - JSON 全量结果
  - Markdown 摘要报告

报告内容应包括：

- 请求参数
- 样本覆盖天数
- 有效交易数 / 跳过交易数
- 胜率
- 平均收益率
- 回撤相关摘要
- 缺失快照/缺失版本告警
- 规则验真摘要（若开启）

**约束**

- 报告只读，不修改任何业务状态
- 报告必须标注样本缺失和降级路径，避免误解结果质量

**数据流向**

`BacktestResult -> reporting -> markdown/json output`

**验收标准**

- 用户不查看原始 JSON 也能理解核心结论和数据质量

---

### 6.6 `NTL-S6-006` 让回测读取快照和策略版本，而不是实时取数

**目标**

强制离线回放只消费历史落盘资产，建立真正的可重复性。

**实现说明**

- 新建 `src/backtest/snapshot_loader.py`
- 明确读取来源：
  - `market_universe` 快照
  - 标准化 `ohlcv_1d` 历史 bars（优先读取本地标准化资产/缓存）
  - topic 相关快照
  - historical released `StrategyVersion`
  - 兼容兜底：`SignalVersioning`、`EvidencePack`

建议接口：

```python
class SnapshotLoader:
    def load_market_context(self, trade_date: date, symbols: list[str]) -> MarketContextSnapshot:
        ...
```

**约束**

- 禁止从 provider 在线补数据
- 对缺失快照必须显式记录，不允许静默 fallback 到实时接口
- 同一 `trade_date + symbol` 输入必须返回同一批数据
- `SignalVersioning` / `EvidencePack` 只能用于兼容补洞或对账，不得替代正式历史快照资产

**数据流向**

`local snapshots + strategy library -> SnapshotLoader -> MarketContextSnapshot`

**失败处理**

- 快照缺失：记录 `missing_snapshot`
- 历史版本缺失：记录 `missing_strategy_version`

**验收标准**

- 相同输入可重复回放，不受网络、provider 状态影响

---

### 6.7 `NTL-S6-007` 回测与线上共用 scoring 口径

**目标**

把“线上评估”和“线下回测”统一到同一评分组件或共享接口。

**实现说明**

- Stage 6 不要求把全部实现并到一个文件，但要求逻辑单源
- 复用：
  - `compute_return_pct`
  - `compute_mfe_mae_return`
  - 统一 `status` 枚举/语义

建议方案：

- `src/evaluation/` 保留评分核心
- `src/backtest/scoring.py` 只做适配，不复制公式

**约束**

- 禁止在线下再写一套不同的 `mfe/mae/return_pct`
- 差异只能来自输入不同，而不能来自公式不同

**数据流向**

`online evaluation core -> imported by backtest scoring adapter`

**失败处理**

- 如需线下附加字段，放到 `extra`，不要污染核心口径

**验收标准**

- 同一 bars / entry / target / stop 输入，线上线下计算结果完全一致

---

### 6.8 `NTL-S6-008` 增加回测 CLI 入口

**目标**

让 Stage 6 不依赖手工脚本即可执行。

**实现说明**

- 在现有 `cli/backtest.py` 中实现回测命令，并接入 `cli/main.py`，例如：

```bash
python -m cli.main backtest run --trader trader_a --from 2026-04-01 --to 2026-04-20
python -m cli.main backtest validate-rules --trader trader_a --from 2026-04-01 --to 2026-04-20
```

建议子命令：

- `backtest run`
- `backtest report`
- `backtest validate-rules`
- `backtest reproducibility-check`

**约束**

- 所有参数都要能从 CLI 明确传入
- 输出路径应可配置，默认落到 `data/processed/backtest/`

**数据流向**

`CLI args -> BacktestRequest -> Engine -> Report files`

**验收标准**

- 命令行可直接运行 Stage 6 的关键链路

---

### 6.9 `NTL-S6-009` 建立 LLM 规则白名单

**目标**

把“LLM 抽出的自然语言规则”分成“可程序化验证”和“不可直接验证”两类。

**实现说明**

- 新建 `src/backtest/rule_registry.py`
- 输出规则元数据：
  - `rule_id`
  - `rule_type`
  - `required_fields`
  - `programmatic_level`
  - `adapter_name`

建议 `programmatic_level`：

- `fully_programmable`
- `partially_programmable`
- `descriptive_only`
- `unsupported`

**约束**

- 白名单不是“人工主观好规则列表”，而是“可程序化验证能力映射”
- 同一条规则必须能追溯到原始 `rule_id` / `rule_text`

**数据流向**

`StrategyVersion.rules_snapshot -> RuleRegistry classification`

**失败处理**

- 无法映射字段的规则标记为 `unsupported`
- 依赖事件型外部信息的规则标记为 `descriptive_only`

**验收标准**

- 能区分哪些规则可以直接验真，哪些只能保留文本解释价值

---

### 6.10 `NTL-S6-010` 对高频规则做命中验证

**目标**

对 10 到 20 条高频规则建立真实的 hit/miss 与后验收益统计。

**实现说明**

- 基于 `RuleRegistry`
- 对历史日期区间逐日扫描：
  - 是否满足规则
  - 若满足，对应标的后续收益分布如何

建议流程：

1. 统计最常出现规则
2. 过滤不可程序化规则
3. 对剩余规则构造 validator
4. 逐日跑 hit/miss
5. 汇总收益分布

**约束**

- 只能使用规则触发当日可见字段
- 不能看未来 bars 决定“当日是否命中”
- 后验收益窗口必须显式定义，如 `T+1`, `T+3`, `T+5`

**数据流向**

`RuleRegistry -> Historical Snapshots/Bars -> RuleValidator -> RuleValidationResult`

**失败处理**

- 字段缺失：记录 `missing_field`
- 快照缺失：记录 `missing_snapshot`

**验收标准**

- 至少有一批高频规则形成可复核的命中验证结果

---

### 6.11 `NTL-S6-011` 输出规则覆盖率、命中率、后验收益分布

**目标**

把规则验真从“是否跑过”提升到“能否用于筛选规则质量”。

**实现说明**

- 在 `reporting.py` 中新增规则报告段落，或拆出 `rule_validation_reporting.py`
- 指标至少包括：
  - 规则覆盖率 = 可验证规则数 / 总规则数
  - 命中率 = hit_count / sample_count
  - 命中后 `T+1/T+3/T+5` 收益均值/中位数
  - 规则有效样本量

**约束**

- 覆盖率和收益必须同时展示，避免只看 hit_rate
- 样本过少的规则必须加“低样本”警告

**数据流向**

`RuleValidationResult[] -> reporting aggregation -> markdown/json report`

**验收标准**

- 可以据此筛掉明显无效或不可验证的规则

---

### 6.12 `NTL-S6-012` 停止继续扩展旧 `backtest_agent` 路线

**目标**

在架构上完成主路径切换，避免新旧两套回测入口并行扩展。

**实现说明**

- 在 `src/agents/backtest_agent/` 顶层说明其历史定位
- 在 `docs/Project.md / docs/TaskList.md` 中明确：
  - 新回测开发只进入 `src/backtest/`
  - `backtest_agent` 不再承接新需求

**约束**

- 不删除旧目录，避免破坏历史上下文
- 不允许新增功能继续落到 `backtest_agent`

**数据流向**

无业务数据流；该任务是路径治理任务。

**验收标准**

- 后续回测任务不再以 `backtest_agent` 为默认入口

---

### 6.13 `NTL-S6-013` 验证回测结果可复现

**目标**

证明 Stage 6 不是“一次跑出来”，而是“同输入可重复得到同结果”。

**实现说明**

- 新建 `src/backtest/reproducibility.py`
- 核心检查：
  - 相同 `BacktestRequest`
  - 相同本地快照
  - 相同 `StrategyVersion`
  - 相同 scoring 口径
  - 输出 hash / summary 是否一致

建议输出：

```python
class ReproducibilityCheckResult(BaseModel):
    request_fingerprint: str
    run_a_hash: str
    run_b_hash: str
    is_equal: bool
    diff_summary: list[str]
```

**约束**

- 复现验证必须禁止实时取数
- 需要固定排序顺序、序列化格式、浮点 rounding 规则

**数据流向**

`BacktestRequest -> repeated engine run -> hash compare -> reproducibility report`

**失败处理**

- 不一致时必须输出“差异来源摘要”，例如：
  - 缺失快照补齐导致
  - 输出排序不稳定
  - 浮点 round 不一致

**验收标准**

- 同一输入重复运行结果一致，或差异可被定位和解释

---

## 7. Stage 6 的统一实现约束

### 7.1 输入一致性约束

- 一切离线执行输入都来自落盘快照和历史策略版本
- 不允许用当前最新版本覆盖历史版本
- 不允许用当前行情补历史缺口
- 若因历史版本持久化缺口而读取 `SignalVersioning/EvidencePack`，必须在结果中显式打 `compatibility_fallback` 标记

### 7.2 评分一致性约束

- 统一使用 Stage 5 比例口径
- 统一字段名：
  - `return_pct`
  - `mfe`
  - `mae`
  - `exit_triggered`
  - `exit_date`

### 7.3 A 股交易约束

- 买入后当日不得卖出（T+1）
- 买入量按 100 股整数倍约束
- 残股仅允许一次性卖出
- 涨跌停板约束由 `TradingConstraintSet` 决定
- 新股/注册制特殊时期“无涨跌幅限制”必须通过证券元数据识别

### 7.4 可解释性约束

- 所有 `skipped / invalid / partial` 必须有原因
- 报告必须显示数据缺失与降级路径

### 7.5 性能约束

- 初版优先正确性，不做复杂并行优化
- 但要避免 `O(n^2)` 无边界遍历
- 需要预留按 trader/date/symbol 的索引能力

---

## 8. 测试与验证要求

Stage 6 必须自带验证，而不是上线后再对账。

### 8.1 单元测试

- `schemas` 校验
- `TradingConstraintSet` 规则切换
- `strategy_replayer` 输出稳定性
- `scoring` 与 Stage 5 一致性
- `rule_registry` 分类正确性

### 8.2 集成测试

- 单 trader、单日回放
- 单 trader、区间回放
- 多规则命中验证
- 报告输出完整性

### 8.3 回归测试

- 固定样本快照运行两次结果一致
- 线上案例与线下评分结果对账

### 8.4 业务验真样本

建议至少准备三类样本：

1. 普通主板 10% 涨跌幅样本
2. 创业板/科创板 20% 涨跌幅样本
3. 风险警示/特殊状态证券样本

---

## 9. 实施顺序建议

按实现依赖，Stage 6 建议拆为四层：

1. 契约层：`S6-001`
2. 回放核心层：`S6-002`、`S6-003`、`S6-004`
3. 离线一致性层：`S6-006`、`S6-007`、`S6-013`
4. 输出与规则验真层：`S6-005`、`S6-008`、`S6-009`、`S6-010`、`S6-011`、`S6-012`

原因：

- 先有统一契约和引擎，再谈报告与 CLI。
- 先解决“能否正确重放”，再解决“规则能否验证”。
- 先建立与 Stage 5 一致的 scoring，再做结果解释。

---

## 10. 需要提前确认的实现决策

以下事项在真正进入实现前必须锁定：

1. 风险警示股票涨跌幅是否按“市场 + 生效日期”做规则切换，而不是静态配置
2. 回测窗口默认按自然日还是交易日推进
3. 规则后验收益窗口是否固定为 `T+1/T+3/T+5`
4. `StrategyVersion` 缺失时是否允许 recommendation-only 降级
5. 报告默认输出目录是否统一为 `data/processed/backtest/`

建议默认值：

- 采用交易日窗口
- 后验收益默认 `T+1/T+3/T+5`
- 缺失版本允许降级，但必须打标
- 报告默认落 `data/processed/backtest/`
- 风险警示规则按“市场 + 日期”参数化

---

## 11. 完成定义

Stage 6 只有同时满足以下条件才算完成：

- 能按日期区间重放某个 trader 的历史输入
- 只消费快照和历史策略版本，不实时取数
- 评分口径与 Stage 5 一致
- 至少 10 条高频规则完成程序化验真
- 能输出覆盖率、命中率、后验收益分布报告
- 同一输入重复运行结果一致或差异可解释

---

## 12. 与 Stage 7 的接口

Stage 6 的输出将直接供 Stage 7 使用：

| Stage 6 输出 | Stage 7 用途 |
|--------------|--------------|
| `BacktestResult` | 活跃 trader 筛选 |
| `RuleValidationResult` | 策略调整建议 |
| reproducibility report | 候选优化可信度评估 |
| backtest summary report | 滚动评估窗口输入 |

因此 Stage 6 的结果文件必须稳定、可追溯、可二次消费。
