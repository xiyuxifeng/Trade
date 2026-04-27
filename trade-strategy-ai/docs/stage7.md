# Stage 7 开发计划：自主优化与运行可观测性

> 日期：2026-04-27
> 依据：docs/TaskList.md §16、docs/superpowers/specs/Stage6-summary-desgin.md §12
> 前置依赖：Stage 6（NLT-S6-001~013）已完成，88 项测试 PASS

---

## 一、Stage 6 现状与 Stage 7 入口

### 6.1 Stage 6 当前可交付的输出

| 输出 | 格式 | 文件/模块 | Stage 7 用途 |
|------|------|------------|--------------|
| `BacktestResult` | JSON/Markdown | `src/backtest/engine.py` | S7-001 活跃 trader 筛选 |
| `RuleValidationResult[]` | JSON/Markdown | `src/backtest/engine.py:validate_rules_for_trader` | S7-002 策略调整建议 |
| `fingerprint` | SHA256 hex | `src/backtest/reproducibility.py` | S7-001 候选可信度评估 |
| Backtest summary | dict | `BacktestSummary` | S7-004 滚动评估窗口 |
| `StrategyVersion` | ORM | `src/strategy_library/` | S7-003 候选版本生成 |

### 6.2 Stage 6 待完善项（影响 Stage 7 接入）

**P0（阻塞项）：**

- `cli/backtest.py:_create_engine_from_config` 中 `SnapshotLoader` 的 `snapshot_service` 和 `strategy_repo` 仍为 `None`，需根据 `data.providers` 配置完成真实注入
  - 影响：`BacktestResult` 数据为空，所有回测记录 `skipped`
  - 修复位置：`cli/backtest.py:46-54`
  - 依赖：需 Stage 7 先明确 `data.providers` 的配置结构

**P1（建议完善）：**

- `BacktestResult` 落盘路径未统一，当前通过 `--output` CLI 参数指定，建议统一到 `data/processed/backtest/`
- `RuleValidationResult` 的 `notes` 和 `hit_symbols_per_day` 为新增字段，需确认下游消费方能正确解析

---

## 二、Stage 7 任务依赖关系与并行策略

```
S7-001 (活跃trader筛选)  ─────────────────┐
S7-002 (策略调整建议)    ─────────────────┼──┐
                                            │  ├──► S7-003 (候选版本机制) ──► S7-004 (滚动评估窗口)
                                            │                               ▲
S7-005 (API扩展)  ──────────┐              │
S7-006 (CLI扩展)  ──────────┼──► S7-008   │
S7-007 (告警逻辑)  ──────────┘  (集成测试) │
         │                        │
         └────────────────────────┘
```

**推荐并行策略：**
- `S7-001` + `S7-002` 可完全并行开发
- `S7-005` + `S7-006` + `S7-007` 可完全并行开发
- `S7-003` 依赖 `S7-002` 完成后解锁
- `S7-004` 依赖 `S7-001` + `S7-002` 完成后解锁
- `S7-008` 依赖所有其他任务完成后执行（无并行）

---

## 三、任务详细分析

### S7-001：活跃 trader 筛选

**目标：** 基于 ranking 与回测结果筛选活跃 trader

**输入：**
- Stage 5：`src/evaluation/` 中的 ranking 数据
- Stage 6：`BacktestResult.summary`（胜率、平均收益率、有效交易数）

**实现建议：**

```python
# src/optimization/active_trader_filter.py
def filter_active_traders(
    rankings: list[TraderRanking],
    backtest_results: dict[str, BacktestResult],
    min_win_rate: float = 0.4,
    min_trades: int = 10,
) -> list[str]:
    """返回满足活跃标准的 trader_id 列表"""
```

**筛选维度（建议，可配置）：**
- 胜率 ≥ 40%（可配置）
- 有效交易数 ≥ 10（避免样本过少）
- 胜率 × 交易数的综合得分（避免只做少量高胜率交易的 trader 排名过高）
- 结合 `RuleValidationResult` 中规则的 `hit_rate` 筛选规则质量高的 trader

**验收标准：** 能识别值得继续优化的 trader，输出可追溯的筛选理由

**注意事项：**
- 筛选标准应有配置文件支撑，不要硬编码
- 筛选结果应包含每条标准的具体数值，便于人工复核

---

### S7-002：策略调整建议

**目标：** 基于 postmortem 和回测结果输出策略调整建议

**输入：**
- `RuleValidationResult[]`（规则命中率、后验收益）
- `BacktestResult`（亏损来源分析）
- Stage 5 postmortem 的 `EvidencePack`

**实现建议：**

```python
# src/optimization/strategy_advisor.py
@dataclass
class StrategyAdjustment:
    trader_id: str
    rule_id: str
    current_status: str  # "hit_rate_too_low" / "return_negative" / ...
    suggestion: str
    confidence: float
   依据: str  # 具体的指标数值
```

**建议生成逻辑：**
- `hit_rate < 10%` + `posterior_return_mean < 0` → 建议删除该规则
- `hit_rate > 70%` 但 `avg_return < 0` → 建议复核止盈/止损参数
- 规则未命中但后验收益为正 → 建议升级为 fully_programmable
- 规则长期 `missing_snapshot` → 建议检查快照覆盖

**验收标准：** 调整建议有明确输入依据，不是泛泛的空话

---

### S7-003：候选版本机制

**目标：** 策略调整建议写入候选版本，不覆盖 released 版本

**输入：** `StrategyAdjustment` 列表

**实现建议：**

```python
# src/strategy_library/service.py
async def create_candidate_version(
    trader_id: str,
    adjustments: list[StrategyAdjustment],
    parent_version_id: str,
) -> StrategyVersion:
    """基于正式版本创建候选优化版本（draft 状态）"""
    # 规则快照引用正式版本的 rules_snapshot
    # 新增 adjustment_notes 说明本次优化改动点
    # 状态为 draft，不由 Agent 自动发布
```

**双轨机制：**
- `StrategyVersion.status = released`：正式版本，Agent 发布
- `StrategyVersion.status = draft`：候选优化版本，需人工 review 后发布

**验收标准：** 正式版本不会被自动优化结果直接覆盖

**关键约束：**
- `draft` 版本不得自动晋升为 `released`，必须人工确认
- 候选版本应保留对正式版本 `version_id` 的引用，便于追溯

---

### S7-004：滚动评估窗口

**目标：** 建立滚动评估窗口，避免单日噪声触发过拟合调整

**输入：** ranking、backtest 结果、调整建议

**实现建议：**

```python
# src/optimization/rolling_evaluator.py
class RollingEvaluator:
    def __init__(self, window_days: int = 30):
        self.window_days = window_days
        self.history: list[BacktestResult] = []

    def push(self, result: BacktestResult) -> None: ...

    def is_signal_stable(self, trader_id: str) -> bool:
        """判断调整信号是否在窗口内持续出现（不少于 50% 的交易日）"""
```

**窗口设计原则：**
- 默认 30 个交易日（约 6 周）
- 信号稳定判断：调整信号在窗口内出现次数 ≥ 50%
- 触发调整需同时满足：信号稳定 + 样本量足够（≥ 10 笔有效交易）

**验收标准：** 不会因单日噪声直接触发过拟合调整

---

### S7-005：API 查询能力扩展

**目标：** 通过 API 查询核心资产和结果

**输入：** 策略版本、快照、ranking、回测结果

**建议路由：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/backtest/results/{trader_id}` | 查询某 trader 的回测结果 |
| GET | `/api/backtest/results/{trader_id}/summary` | 查询回测汇总 |
| GET | `/api/rules/validation/{trader_id}` | 查询规则验真结果 |
| GET | `/api/trader/{trader_id}/active` | 查询活跃 trader 状态 |
| POST | `/api/optimization/adjustments` | 提交策略调整建议（→ S7-002） |
| GET | `/api/versions/{trader_id}/candidates` | 查询候选版本列表 |

**数据序列化注意：**
- `BacktestResult` 通过 `render_backtest_json` 序列化
- `datetime` 字段统一用 ISO 8601 格式（`YYYY-MM-DDTHH:MM:SS`）
- 比例字段（`win_rate`/`avg_return_pct`）已在 Stage 6 修复中输出为百分比字符串

**验收标准：** 可通过 API 查询核心资产和结果

---

### S7-006：CLI 扩展

**目标：** 关键链路都能通过 CLI 触发

**建议新增命令：**

| 命令 | 说明 | 对应模块 |
|------|------|----------|
| `python -m cli.main backtest run --trader X --from ... --to ...` | ✅ 已在 Stage 6 实现 |
| `python -m cli.main optimize filter --trader X` | 活跃 trader 筛选 |
| `python -m cli.main optimize advise --trader X` | 策略调整建议 |
| `python -m cli.main optimize candidate --trader X --parent-version X` | 生成候选版本 |
| `python -m cli.main alert check --date X` | 触发告警检查 |
| `python -m cli.main api-server` | 启动 API 服务 |

**验收标准：** 关键链路都能通过 CLI 触发

---

### S7-007：告警逻辑

**目标：** 关键数据问题能被及时发现

**输入：** 运行日志与快照状态

**建议告警类型：**

| 告警类型 | 触发条件 | 严重度 |
|----------|----------|--------|
| `snapshot_missing` | `BacktestResult.records` 中 > 50% 为 `skipped` 且 `skip_reason=missing_snapshot` | HIGH |
| `provider_failure` | `SnapshotLoader._load_snapshot` 连续 3 次异常 | HIGH |
| `rule_validation_empty` | 规则验真 `sample_count = 0` 超过 5 个交易日 | MEDIUM |
| `reproducibility_broken` | 相同 `BacktestRequest` 两次运行 `fingerprint` 不一致 | CRITICAL |
| `no_recent_release` | 某 trader 超过 30 天无新 `released` 版本 | LOW |
| `akshare_stale` | `TradeCalendar._trade_dates` 与当前日期偏差超过 7 天未更新 | MEDIUM |

**实现建议：**
- 告警规则定义在 `src/alerting/rules.py`（已存在）
- Stage 7 补充上述具体规则逻辑
- 告警触发后可发送至已有 `notifiers`（Slack/飞书/邮件）

**验收标准：** 关键数据问题能被及时发现

---

### S7-008：集成测试

**目标：** 关键链路具备一组稳定回归用例

**建议集成测试场景：**

| 测试 | 描述 | 前置依赖 |
|------|------|----------|
| `test_full_backtest_pipeline` | 快照 → 策略版本 → 回测 → 报告 | S7-001 依赖真实数据 |
| `test_trader_filter_round_trip` | 筛选 → 调整建议 → 候选版本 → 回测对比 | S7-001~S7-003 |
| `test_reproducibility_end_to_end` | 两次相同请求 fingerprint 一致 | Stage 6 |
| `test_rule_validation_with_real_snapshot` | 加载真实快照做规则验真 | S7-001 |
| `test_rolling_window_stability` | 噪声注入后不应触发调整信号 | S7-004 |
| `test_alert_trigger_and_recover` | 模拟快照缺失 → 告警触发 → 快照恢复 → 告警恢复 | S7-007 |

**Mock vs 真实数据策略：**
- 优先使用 Mock，消除外部依赖
- 使用固定种子的随机数据，保证每次运行一致
- 真实快照集成测试放在 CI 的 `integration` 标签下，不阻塞主测试套件

**验收标准：** 关键链路至少具备一组稳定回归用例

---

## 四、实施顺序建议

### Step 0（P0：阻塞项，与 S7-001/002 并行做）

**P0：完成 `cli/backtest.py` 真实依赖注入**

- 位置：`cli/backtest.py:46-54`，`SnapshotLoader(snapshot_service=None, strategy_repo=None)`
- 内容：从 `config` YAML 读取 `data.providers` 配置，初始化 `SnapshotLoader`
- 依赖：需先明确 `data.providers` 配置结构
- 建议做在：S7-005/S7-006 开始之前（或与之并行）
- 预估：2~4 小时

**P1：可与任意批次并行做的改进项**

| P1 项 | 建议做的时间点 | 原因 |
|--------|--------------|------|
| 回测结果统一落盘到 `data/processed/backtest/` | 和 S7-005（API）一起做 | API 需要知道数据写在哪 |
| `RuleValidationResult.notes` 字段使用说明 | 和 S7-002（建议）一起做 | S7-002 需要知道字段怎么用 |

---

### 第一批（可立即开始，用 Mock 数据开发）

**S7-001**（活跃 trader 筛选）+ **S7-002**（策略调整建议），完全并行

理由：
- 纯算法逻辑，用 Mock 数据即可开发和测试
- 不需要真实 `snapshot_service` / `strategy_repo` 注入
- 等 P0 完成后，用真实数据跑一遍验证即可

**S7-001 子任务：**
- 新建 `src/optimization/active_trader_filter.py`
- 实现筛选逻辑（胜率、有效交易数、综合得分）+ 配置文件支撑
- CLI 命令 `optimize filter`
- 单元测试（用 Mock `BacktestResult`）

**S7-002 子任务：**
- 新建 `src/optimization/strategy_advisor.py`
- 实现调整建议生成逻辑（hit_rate 低、后验收益负 等判断）
- 对接 `RuleValidationResult` 的 `notes` 和 `hit_symbols`
- CLI 命令 `optimize advise`
- 单元测试（用 Mock `RuleValidationResult[]`）

---

### 第二批（P0 完成后解锁）

**S7-005**（API 扩展）+ **S7-006**（CLI 扩展）+ **S7-007**（告警逻辑）

理由：
- 这三个任务需要真实 `BacktestResult` 数据才有意义
- P0 完成后，S7-005/006/007 可以返回真实数据

**S7-005 子任务：**
- 设计路由 → 实现 `src/api/routes/backtest.py`
- 实现 `BacktestResult` / `RuleValidationResult` 序列化 API
- 补充测试

**S7-006 子任务：**
- 实现 `optimize` 和 `alert` 子命令
- 补充测试

**S7-007 子任务：**
- 补充 `snapshot_missing` / `reproducibility_broken` 等告警规则
- 补充测试

---

### 第三批（S7-001 + S7-002 完成后解锁）

**S7-003**（候选版本）+ **S7-004**（滚动评估）

理由：都依赖 S7-001/S7-002 的输出

**S7-003 子任务：**
- 在 `StrategyVersion.status` 中新增 `candidate` 状态（或复用 `draft`）
- `strategy_library/service.py` 新增 `create_candidate_version`
- 候选版本列表 API
- 单元测试

**S7-004 子任务：**
- 新建 `src/optimization/rolling_evaluator.py`
- 实现窗口判断逻辑（信号稳定性 + 样本量门槛）
- 与 S7-002 联动测试
- 单元测试

---

### 第四批（S7-005/006/007 完成后）

**S7-008**（集成测试）

所有其他任务完成后，执行 `S7-008` 集成测试

---

### 并行关系总览

```
                Step 0 (P0)
                   │
    ┌──────────────┼──────────────┐
    │              │              │
S7-001/002    S7-005/006     P1
(立即开始)     (P0完成后)
    │           开始
    ▼              │
S7-003/004         │
(第二批判完成)      │
    │              │
    └────── S7-008 ─┘
         (集成测试)
```

---

## 五、技术债务与风险

### T1：BacktestResult 落盘格式稳定性（中等风险）

**问题：** 当前 `BacktestResult` 的 JSON 结构未做版本化，新增 `notes`/`hit_symbols` 字段后，旧代码读取新格式可能出错。

**建议：** 引入 `result_version: int` 字段，重大结构变更时递增。下游消费方应忽略未知字段（Pydantic 默认行为）。

### T2：CLI `--config` 依赖注入未完成（阻塞风险）

**问题：** `cli/backtest.py` 中 `SnapshotLoader` 的 `snapshot_service` 和 `strategy_repo` 仍为 `None`。

**建议：** 在 S7-005/S7-006 开发时优先完成 `config → loader` 的注入逻辑，明确 `data.providers` 的配置结构。

### T3：akshare 懒加载的网络依赖（运行风险）

**问题：** `TradeCalendar.load_from_akshare()` 在首次调用时访问网络，若 akshare 服务不可用会 fallback 到空节假日集。

**建议：** S7-007 中增加 `akshare_stale` 告警；在配置中支持注入本地交易日历文件作为 fallback。

### T4：规则 `notes` 字段可能导致 JSON 体积膨胀（性能风险）

**问题：** `hit_symbols_per_day` 在大量标的命中时会生成很长的字符串。

**建议：** 若 `notes` 超过阈值（如 1KB），在 `render_backtest_json` 中截断或改为列表格式。

---

## 六、测试策略

### 6.1 单元测试覆盖目标

| 模块 | 测试数（建议） | 关键场景 |
|------|--------------|----------|
| `src/optimization/active_trader_filter.py` | 8~10 | 筛选标准组合、边界值 |
| `src/optimization/strategy_advisor.py` | 10~12 | 建议生成逻辑、字段完整性 |
| `src/optimization/rolling_evaluator.py` | 6~8 | 窗口稳定性判断 |
| `src/strategy_library/`（候选版本） | 5~6 | 版本状态流转 |
| `src/alerting/rules.py` | 8~10 | 各告警类型触发 |
| `src/api/routes/backtest.py` | 6~8 | HTTP 路由与序列化 |

### 6.2 集成测试目标

| 测试 | 描述 | 目标 |
|------|------|------|
| `test_backtest_to_filter_pipeline` | 回测结果 → trader 筛选 | 端到端 |
| `test_filter_to_candidate_pipeline` | 筛选 → 建议 → 候选版本 | 端到端 |
| `test_rolling_window_ignores_noise` | 注入单日噪声，确认不触发调整 | 回归 |
| `test_reproducibility_holds` | 相同请求两次运行 fingerprint 一致 | 回归 |

---

## 七、完成标准

Stage 7 只有同时满足以下条件才算完成：

- [ ] S7-001~008 全部任务完成
- [ ] 已形成"正式版本 + 候选优化版本"的双轨机制
- [ ] 关键链路可观察（S7-005 API）、可告警（S7-007）、可查询（S7-005）、可回归（S7-008）
- [ ] 所有 Stage 6~7 跨模块数据流至少有一组稳定回归测试
- [ ] `cli/backtest.py` 的 `--config` 注入逻辑已完成

---

## Appendix: 关键文件清单

| 文件 | 职责 |
|------|------|
| `src/optimization/active_trader_filter.py` | 活跃 trader 筛选逻辑（S7-001） |
| `src/optimization/strategy_advisor.py` | 策略调整建议生成（S7-002） |
| `src/optimization/rolling_evaluator.py` | 滚动评估窗口（S7-004） |
| `src/api/routes/backtest.py` | 回测结果 API 路由（S7-005） |
| `src/api/routes/optimization.py` | 优化相关 API 路由（S7-005） |
| `src/alerting/rules.py` | 告警规则扩展（S7-007） |
| `cli/main.py` | 新增 optimize/alert 子命令（S7-006） |
| `src/strategy_library/service.py` | 候选版本创建（S7-003） |
| `tests/integration/test_*` | 集成测试（S7-008） |
