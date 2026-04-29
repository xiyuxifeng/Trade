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

**注意**：`StrategyAdjustment` 已定义在 `src/strategy_library/schemas.py`，无需重复定义。

**实现建议：**

```python
# src/optimization/strategy_advisor.py
# 使用 src.strategy_library.schemas 中的 StrategyAdjustment
from src.strategy_library.schemas import StrategyAdjustment
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
    session: AsyncSession,
    trader_id: str,
    strategy_date: date,
    parent_version_id: str,
    adjustments: list[StrategyAdjustment],
    recommendations: list[StrategyRecommendation],
) -> StrategyVersion:
    """基于正式版本创建候选优化版本（draft 状态）"""
    # 使用 StrategyVersionBuilder.build_candidate() 创建
    # version_type = StrategyVersionType.candidate
    # parent_version_id 追溯正式版本
    # notes 包含 adjustment_notes 说明本次优化改动点
```

**双轨机制（已实现）：**
- `StrategyVersion.status = released` + `version_type = manual`：正式版本，Agent 发布
- `StrategyVersion.status = draft` + `version_type = candidate`：候选优化版本，需人工 review 后发布
- `version_type = candidate` 的版本通过 `release_version()` 会抛出异常，必须人工确认

**已实现的约束：**
- `release_version()` 方法会检查 `version_type`，candidate 类型不能自动晋升
- 候选版本保留 `parent_version_id` 引用，便于追溯正式版本

**验收标准：** 正式版本不会被自动优化结果直接覆盖

---

### S7-004：滚动评估窗口

**目标：** 建立滚动评估窗口，避免单日噪声触发过拟合调整

**输入：** S7-002 的 `StrategyAdjustment[]`、回测结果

**与 S7-002 的联动：**
- S7-002 输出 `StrategyAdjustment[]`
- S7-004 通过 `push_adjustment()` 将每个 adjustment 记录到窗口
- 窗口内持续出现的信号才触发真正的调整动作

**实现建议：**

```python
# src/optimization/rolling_evaluator.py

@dataclass
class RollingEvaluatorConfig:
    """滚动评估器配置（可配置，非硬编码）"""
    window_days: int = 30           # 窗口大小（交易日）
    min_signal_frequency: float = 0.5  # 信号出现比例阈值（≥50%）
    min_sample_trades: int = 10    # 最小有效交易样本量

@dataclass
class SignalObservation:
    """窗口内观察到的信号"""
    trader_id: str
    signal_type: str  # 如 "delete_rule" / "upgrade_rule" / "review_stop_loss"
    rule_id: str
    observation_date: date
    confidence: float

class RollingEvaluator:
    def __init__(self, config: RollingEvaluatorConfig | None = None):
        self.config = config or RollingEvaluatorConfig()
        self._observations: list[SignalObservation] = []

    def push_adjustment(self, adjustment: StrategyAdjustment) -> None:
        """将 S7-002 的调整建议加入观察窗口"""
        self._observations.append(SignalObservation(...))
        self._prune_old_observations()

    def is_signal_stable(
        self,
        trader_id: str,
        signal_type: str,
        rule_id: str,
    ) -> bool:
        """判断信号是否在窗口内持续出现（不少于 min_signal_frequency 的交易日）"""

    def has_sufficient_samples(self, trader_id: str) -> bool:
        """判断样本量是否足够（≥ min_sample_trades）"""

    def should_trigger_adjustment(self, trader_id: str) -> bool:
        """综合判断是否应触发调整（信号稳定 + 样本足够）"""
```

**窗口设计原则：**
- 窗口大小可配置（`RollingEvaluatorConfig.window_days`）
- 信号稳定判断：调整信号在窗口内出现次数 ≥ `min_signal_frequency`（默认 50%）
- 触发调整需同时满足：信号稳定 + 样本量足够（`min_sample_trades`，默认 10 笔）

**验收标准：** 不会因单日噪声直接触发过拟合调整

---

### S7-005：API 查询能力扩展

**目标：** 通过 API 查询核心资产和结果

**输入：** 策略版本、快照、ranking、回测结果

**现有代码对照：**
- `api/main.py` 已注册 `run` 和 `reports` 路由
- `api/routers/backtest.py` 存在但为空，需实现回测相关路由
- `api/routers/strategy.py` 存在但为空，可用于策略版本路由

**建议路由：**

| 方法 | 路径 | 说明 | 实现位置 |
|------|------|------|----------|
| GET | `/api/backtest/results/{trader_id}` | 查询某 trader 的回测结果 | `api/routers/backtest.py` |
| GET | `/api/backtest/results/{trader_id}/summary` | 查询回测汇总 | `api/routers/backtest.py` |
| GET | `/api/rules/validation/{trader_id}` | 查询规则验真结果 | `api/routers/backtest.py` |
| GET | `/api/trader/{trader_id}/active` | 查询活跃 trader 状态 | `api/routers/optimization.py`（新建） |
| POST | `/api/optimization/adjustments` | 提交策略调整建议（→ S7-002） | `api/routers/optimization.py`（新建） |
| GET | `/api/versions/{trader_id}/candidates` | 查询候选版本列表 | `api/routers/strategy.py` |

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

**现有代码对照：**
- `src/alerting/models.py`：`AlertLevel`、`AlertEvent`、`AlertRule` ✅
- `src/alerting/notifiers.py`：`ConsoleNotifier`、`WebhookNotifier`、`MemoryNotifier`、`CompositeNotifier` ✅
- `src/alerting/rules.py`：预定义规则（数据新鲜度、异常率等）✅
- `src/alerting/manager.py`：`AlertManager`（规则评估、冷却管理）✅

**注意**：现有规则签名 `condition(stats, quality) -> bool` 基于 `DashboardStats`，S7-007 的告警需要回测/快照相关输入，需扩展评估接口。

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
- 在 `src/alerting/rules.py` 补充上述 6 个规则
- 告警评估入口可复用现有 `AlertManager.evaluate()` 接口
- 告警触发后可发送至已有 `notifiers`（`ConsoleNotifier` / `WebhookNotifier`）
- `WebhookNotifier` 可配置为对接 Slack/飞书 Webhook URL

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

### Step 0（P0：修复 CLI 注入阻塞项，S7-001/002 同步开始）

**P0：完成 `cli/backtest.py` 真实依赖注入**

- 位置：`cli/backtest.py:46-54`，`SnapshotLoader(snapshot_service=None, strategy_repo=None)`
- 内容：从 `config` YAML 读取 `data.providers` 配置，初始化 `SnapshotLoader`
- 依赖：需先明确 `data.providers` 配置结构
- 阻塞范围：仅影响 S7-005/S7-006/S7-007（需要真实数据）
- 预估：2~4 小时

**重要更正：S7-001/S7-002 不需要等待此 P0 完成**

S7-001（活跃 trader 筛选）和 S7-002（策略调整建议）是纯算法逻辑，使用 Mock 数据即可开发和测试。应**立即启动**，与 P0 修复并行进行。

**P1：可与任意批次并行做的改进项**

| P1 项 | 建议做的时间点 | 原因 |
|--------|--------------|------|
| 回测结果统一落盘到 `data/processed/backtest/` | 和 S7-005（API）一起做 | API 需要知道数据写在哪 |
| `RuleValidationResult.notes` 字段使用说明 | 和 S7-002（建议）一起做 | S7-002 需要知道字段怎么用 |

---

### 第一批（立即开始，用 Mock 数据开发）

**S7-001**（活跃 trader 筛选）+ **S7-002**（策略调整建议），完全并行

**立即启动，不需要等待 P0 完成**。

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
- 设计路由 → 实现 `src/api/routes/backtest.py`（回测结果查询）
- 设计路由 → 实现 `src/api/routes/optimization.py`（活跃 trader / 调整建议）
- 设计路由 → 实现 `src/api/routes/versions.py`（候选版本列表）
- 在 `src/api/routes/__init__.py` 注册新路由
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
- ✅ 已实现：`StrategyVersion` 新增 `version_type` 字段（`manual`/`candidate`）和 `parent_version_id`
- ✅ 已实现：`StrategyVersionBuilder.build_candidate()` 方法
- ✅ 已实现：`StrategyLibraryService.create_candidate_version()` 方法
- ✅ 已实现：`release_version()` 约束检查，candidate 类型不能自动晋升
- 新增候选版本列表 API：实现 `GET /api/versions/{trader_id}/candidates`
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
Step 0 (P0 修复)
       │
       ├──► S7-001/S7-002 (立即开始，用 Mock 数据)
       │         │
       │         ▼
       │    S7-003/S7-004
       │         │
       └────► S7-005/S7-006/S7-007 (P0 完成后)
                     │
                     ▼
                  S7-008
              (集成测试)
```

---

## 五、技术债务与风险

### T1：BacktestResult 落盘格式稳定性（中等风险）

**问题：** 当前 `BacktestResult` 的 JSON 结构未做版本化，新增 `notes`/`hit_symbols` 字段后，旧代码读取新格式可能出错。

**建议：** 引入 `result_version: int` 字段，重大结构变更时递增。下游消费方应忽略未知字段（Pydantic 默认行为）。

**TaskList 入口**：`NTL-S7-009`（P2）

### T2：CLI `--config` 依赖注入未完成（阻塞风险）

**问题：** `cli/backtest.py` 中 `SnapshotLoader` 的 `snapshot_service` 和 `strategy_repo` 仍为 `None`。

**建议：** 在 S7-005/S7-006 开发时优先完成 `config → loader` 的注入逻辑，明确 `data.providers` 的配置结构。

**TaskList 入口**：`NTL-S7-000`（P0）

### T3：akshare 懒加载的网络依赖（运行风险）

**问题：** `TradeCalendar.load_from_akshare()` 在首次调用时访问网络，若 akshare 服务不可用会 fallback 到空节假日集。

**建议：** S7-007 中增加 `akshare_stale` 告警；在配置中支持注入本地交易日历文件作为 fallback。

**TaskList 入口**：`NTL-S7-010`（P2）

### T4：规则 `notes` 字段可能导致 JSON 体积膨胀（性能风险）

**问题：** `hit_symbols_per_day` 在大量标的命中时会生成很长的字符串。

**建议：** 若 `notes` 超过阈值（如 1KB），在 `render_backtest_json` 中截断或改为列表格式。

**TaskList 入口**：`NTL-S7-011`（P2）

---

## 六、测试策略

### 6.1 测试标记约定

| 标记 | 说明 | CI 行为 |
|------|------|---------|
| 无标记 | 单元测试，使用 Mock | 必须通过 |
| `smoke` | 轻量回归测试 | 必须通过 |
| `integration` | 集成测试，需要真实数据/网络 | 可失败（不阻塞 CI） |

**注意**：`pyproject.toml` 中已定义 `smoke` 和 `integration` 标记。

### 6.2 单元测试覆盖目标

| 模块 | 测试数（建议） | 关键场景 |
|------|--------------|----------|
| `src/optimization/active_trader_filter.py` | 8~10 | 筛选标准组合、边界值 |
| `src/optimization/strategy_advisor.py` | 10~12 | 建议生成逻辑、字段完整性 |
| `src/optimization/rolling_evaluator.py` | 6~8 | 窗口稳定性判断 |
| `src/strategy_library/`（候选版本） | 5~6 | 版本状态流转 |
| `src/alerting/rules.py` | 8~10 | 各告警类型触发 |
| `src/api/routes/backtest.py` | 6~8 | HTTP 路由与序列化 |

### 6.3 集成测试目标

| 测试 | 描述 | 标记 | CI 行为 |
|------|------|------|---------|
| `test_backtest_to_filter_pipeline` | 回测结果 → trader 筛选 | `integration` | 可失败 |
| `test_filter_to_candidate_pipeline` | 筛选 → 建议 → 候选版本 | `integration` | 可失败 |
| `test_rolling_window_ignores_noise` | 注入单日噪声，确认不触发调整 | `smoke` | 必须通过 |
| `test_reproducibility_holds` | 相同请求两次运行 fingerprint 一致 | `smoke` | 必须通过 |

### 6.4 Mock vs 真实数据边界

**使用 Mock 的场景**（单元测试）：
- S7-001（活跃 trader 筛选）：Mock `BacktestResult`、`RankingEntry`
- S7-002（策略调整建议）：Mock `RuleValidationResult[]`
- S7-003（候选版本）：Mock `StrategyVersion`
- S7-004（滚动评估）：Mock `StrategyAdjustment[]`
- S7-007（告警逻辑）：Mock `AlertRule` 条件

**使用真实数据的场景**（集成测试，`@pytest.mark.integration`）：
- 完整链路回测 → 筛选 → 建议 → 候选版本
- 真实快照加载
- 真实数据库操作

---

## 七、与其他 Stage 的接口边界

### 7.1 Stage 6 → Stage 7 接口

| Stage 6 输出 | 类型 | Stage 7 消费 | 说明 |
|--------------|------|-------------|------|
| `BacktestResult` | `src/backtest/schemas.py` | S7-001 筛选 | 使用 `summary.win_rate`、`summary.avg_return_pct`、`records` |
| `RuleValidationResult[]` | `src/backtest/schemas.py` | S7-002 建议 | 使用 `hit_rate`、`posterior_return_mean`、`notes` |
| `BacktestSummary` | `src/backtest/schemas.py` | S7-004 窗口 | 使用样本量统计 |
| `StrategyVersion` | `src/strategy_library/schemas.py` | S7-003 候选 | 使用 `version_id`、`rules_snapshot`、`parent_version_id` |
| `fingerprint` | str (SHA256) | S7-007 告警 | 用于 reproducibility 检查 |

### 7.2 已定义的跨 Stage 数据类

| 类名 | 定义位置 | 被引用位置 |
|------|----------|-----------|
| `StrategyAdjustment` | `src/strategy_library/schemas.py` | S7-002、S7-003 |
| `StrategyVersion` | `src/strategy_library/schemas.py` | S7-003、S7-005 |
| `BacktestResult` | `src/backtest/schemas.py` | S7-001、S7-005、S7-007 |
| `RuleValidationResult` | `src/backtest/schemas.py` | S7-002、S7-005、S7-007 |

### 7.3 潜在兼容性问题

| 问题 | 影响 | 缓解措施 |
|------|------|----------|
| `BacktestResult` 无版本号 | 格式变更时下游可能出错 | S7-009 添加 `result_version` 字段 |
| `RuleValidationResult.notes` 体积膨胀 | JSON 序列化性能问题 | S7-011 添加截断逻辑 |
| `EvidencePack` 引用格式 | S7-002 是否能正确解析 | 需在实现时验证 |

### 7.4 接口稳定性要求

- 所有跨 Stage 引用的数据结构必须定义在 `src/xxx/schemas.py` 中
- 不允许在 Stage 7 中重新定义已在其他 Stage 定义的类
- 数据类变更需同步更新版本号（`result_version`）

---

## 八、完成标准

Stage 7 只有同时满足以下条件才算完成：

- [ ] S7-001~008 全部任务完成
- [ ] S7-009~011 技术债务处理完成
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
| `src/strategy_library/schemas.py` | 新增 `StrategyVersionType`、`StrategyAdjustment`（S7-003） |
| `src/strategy_library/builder.py` | 新增 `build_candidate()` 方法（S7-003） |
| `src/strategy_library/service.py` | 新增 `create_candidate_version()`、`get_latest_candidate_version()`（S7-003） |
| `src/api/routes/backtest.py` | 回测结果 API 路由（S7-005） |
| `src/api/routes/optimization.py` | 优化相关 API 路由（S7-005） |
| `src/api/routes/versions.py` | 策略版本查询 API 路由（S7-005） |
| `src/alerting/rules.py` | 告警规则扩展（S7-007） |
| `cli/main.py` | 新增 optimize/alert 子命令（S7-006） |
| `src/strategy_library/service.py` | 候选版本创建（S7-003） |
| `tests/integration/test_*` | 集成测试（S7-008） |
