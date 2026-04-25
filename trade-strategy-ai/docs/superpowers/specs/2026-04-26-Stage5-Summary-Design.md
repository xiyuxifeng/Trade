# Stage 5 总结：盘后评估与记忆系统

> 本文档是 Stage 5（NTL-S5-001~014）的设计规范与功能实现总结。

## 1. 架构概览

Stage 5 建立了完整的**盘后评估 → 评分 → 排名 → 记忆写回 → 下次盘前消费**闭环。

```
盘前(Pre-market)                          盘后(Post-market)
─────────────────                         ─────────────────
TraderAgent.generate_trade_ideas()  ──→   ManagerAgent.run_after_close()
       ↓                                       ↓
       │                              EvidencePack 生成(聚合所有数据)
       │                                       ↓
       │                              compute_mfe_mae_return()
       │                              (MFE/MAE/return_pct 计算)
       │                                       ↓
       │                              PostmortemService.generate()
Memory ───────────────────────────→      (自动归因 + LLM 校验)
summarize_context()                       ↓
       ↓                           RankingService.add_entry()
Memory Hint ────→ Idea Rationale    TraderMemoryStore.append/update()
```

## 2. 核心数据模型

### 2.1 EvidencePack

`src/evaluation/evidence_pack.py`

> Design: [evidence-pack-generation-design](2026-04-25-evidence-pack-generation-design.md)

聚合盘前到盘后的完整证据链：

| 字段 | 类型 | 说明 |
|------|------|------|
| `pack_id` | UUID | 唯一标识 |
| `idea_id` | UUID | 关联的交易想法 |
| `trade_idea` | TradeIdea | 原始交易想法 |
| `signal_context` | SignalContext | 信号上下文（含 rules_snapshot） |
| `market_data` | dict | 市场数据（含 bars） |
| `strategy_version_id` | str | 策略版本 ID |
| `strategy_version_snapshot` | StrategyVersion | 策略版本快照 |

工厂方法：`EvidencePack.from_trade_idea(idea, signal_context, market_data)`

### 2.2 PostmortemResult

`src/evaluation/postmortem_service.py`

> Design: [postmortem-service-design](2026-04-25-postmortem-service-design.md)

盘后复盘结果：

| 字段 | 类型 | 说明 |
|------|------|------|
| `mfe` | float | 最大有利偏移（Maximum Favorable Excursion） |
| `mae` | float | 最大不利偏移（Maximum Adverse Excursion） |
| `return_pct` | float | 收益率 |
| `failure_attribution` | FailureAttribution | 失败归因 |
| `postmortem_notes` | str | 复盘笔记 |
| `source` | str | 来源（auto/llm_confirmed/llm_corrected/llm_rejected） |
| `extra` | dict | 扩展数据（rules_hit/exit_triggered/is_final） |

### 2.3 FailureAttribution

`src/evaluation/failure_taxonomy.py`

> Design: [failure-taxonomy-design](2026-04-25-failure-taxonomy-design.md)

多维度失败归因：

| 字段 | 类型 | 说明 |
|------|------|------|
| `root_causes` | list[FailureRootCause] | 根因标签（9选n） |
| `stage` | FailureStage | 阶段标签（entry/exit/holding） |
| `rule_type` | FailureRuleType | 规则类型标签（entry/exit/filter/sizing） |

**FailureRootCause 枚举（9个）**：
- `rule_precondition_failed` — 规则前置条件失败
- `signal_quality_low` — 信号质量低
- `entry_timing_poor` — 入场时机差
- `exit_timing_poor` — 出场时机差
- `position_size_mismatch` — 仓位不匹配
- `market_mismatch` — 市场不适配
- `external_event` — 外部事件
- `symbol_selection_suboptimal` — 标的选择次优
- `data_quality_issue` — 数据质量问题

### 2.4 RankingEntry

`src/evaluation/ranking_service.py`

> Design: [ranking-service-design](2026-04-25-ranking-service-design.md)

排名条目：

| 字段 | 类型 | 说明 |
|------|------|------|
| `trade_date` | str | 交易日期 |
| `trader_id` | str | 交易员 ID |
| `strategy_version_id` | str | 策略版本（`__none__` 表示 Phase 0） |
| `symbol` | str | 标的代码 |
| `return_pct` | float | 收益率 |
| `mfe` | float | 最大有利偏移 |
| `mae` | float | 最大不利偏移 |
| `composite_score` | float | 综合评分 |
| `rank` | int | 排名 |
| `is_latest` | bool | 是否最新版本 |

**排序规则**：
1. `return_pct` 降序
2. 赔率（MFE - MAE）降序
3. None 值排最后

**唯一约束**：
```
(trade_date, trader_id, strategy_version_id, symbol)
```

### 2.5 TraderMemoryItem

`src/trader_memory/schemas.py`

> Design: [trader-memory-schema-extension-design](2026-04-25-trader-memory-schema-extension-design.md)

记忆条目：

| 字段 | 类型 | 说明 |
|------|------|------|
| `memory_type` | TraderMemoryType | 记忆类型 |
| `trader_id` | str | 交易员 ID |
| `symbol` | str | 标的（可选） |
| `content` | str | 记忆内容 |
| `idea_id` | UUID | 关联想法（可选） |
| `strategy_version_id` | str | 关联策略版本（可选） |
| `ranking_entry_id` | UUID | 关联排名条目（可选） |
| `extra` | dict | 扩展数据 |

**TraderMemoryType 枚举（6种）**：
- `review_note` — 复盘笔记
- `success_case` — 成功案例
- `failure_case` — 失败案例
- `postmortem` — 盘后复盘
- `strategy_adjustment` — 策略调整
- `market_regime_note` — 市场状态笔记

## 3. 核心计算逻辑

### 3.1 compute_mfe_mae_return()

`src/evaluation/metrics_calculator.py`

> Design: [postmortem-metrics-design](2026-04-25-postmortem-metrics-design.md)

从 OHLCV 日线数据计算 MFE/MAE/return_pct：

```python
def compute_mfe_mae_return(
    entry_price: float,
    target_price: float,
    stop_loss: float,
    bars: list[dict],      # [{"date": "2026-04-20", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2}, ...]
    entry_date: str,
) -> tuple[float, float, float, bool, str | None, bool]:
    """
    Returns: (mfe, mae, return_pct, exit_triggered, exit_reason, is_final)
    """
```

**计算逻辑**：
1. 找到 `entry_date` 对应的 bar 索引
2. 遍历持仓期间所有 bar：
   - MFE = max(high - entry_price, previous_mfe)
   - MAE = max(entry_price - low, previous_mae)
3. 判断止盈触发：`high >= target_price`
4. 判断止损触发：`low <= stop_loss`
5. return_pct = (exit_price - entry_price) / entry_price

**状态返回值**：
- `exit_triggered`: True/False（是否触发止盈/止损）
- `exit_reason`: "target_hit" / "stop_loss_hit" / None
- `is_final`: True/False（交易是否已结束）

### 3.2 _auto_attribution()

`src/evaluation/postmortem_service.py`

> Design: [failure-taxonomy-design](2026-04-25-failure-taxonomy-design.md)

自动归因逻辑：

```python
def _auto_attribution(
    return_pct: float,
    rules_hit: list[str],
    bars_exist: bool,
) -> FailureAttribution:
```

**归因规则**：

| 条件 | 归因结果 |
|------|----------|
| 亏损 + rules_hit 非空 | `RULE_PRECONDITION_FAILED` |
| 亏损 + rules_hit 为空 | `ENTRY_TIMING_POOR` |
| 缺 bars 数据 | `DATA_QUALITY_ISSUE` |

## 4. 数据流

### 4.1 盘前 → 盘后完整链路

```
1. TraderAgent.generate_trade_ideas()
   └→ 生成 TradeIdea 列表

2. ManagerAgent.run_pre_market()
   └→ 写入 DailyReport (JSON)
   └→ 写入 tasks (按 trader 分组)

3. ManagerAgent.run_after_close()
   │
   ├→ 读取 DailyReport
   │
   ├→ 对每个 Idea 评估：
   │   ├→ EvidencePack.from_trade_idea()
   │   │   └→ 获取 market_data["bars"]
   │   │
   │   ├→ compute_mfe_mae_return()
   │   │   └→ 计算 mfe/mae/return_pct
   │   │
   │   ├→ PostmortemService.generate()
   │   │   ├→ _auto_attribution()
   │   │   └→ llm_attribution() [可选]
   │   │
   │   └→ IdeaEvaluation
   │       └→ status: ok / partial / fallback / not_evaluated
   │
   ├→ handle_postmortem_analysis()
   │   ├→ RankingService.add_entry()
   │   └→ TraderMemoryStore.append() / update()
   │
   └→ 生成 AfterCloseReport
```

### 4.2 记忆写回 → 下次盘前消费

```
盘后写入:
handle_postmortem_analysis()
├→ 亏损 → failure_case
└→ 盈利 → success_case

TraderMemoryStore.summarize_context()
├→ 聚合 postmortem_notes
├─→ 聚合 success_case / failure_case (by_type)
└→ 提取 recent_titles, review_notes

盘前读取:
TraderAgent._memory_hint()
└→ "memory summary: symbol: XXX; review: XXX; recent: XXX"

TraderAgent._profile_hint()
├→ trader_profile.top_symbols
├→ trader_profile.concept_tags
└→ memory_store.summarize_context().by_type
    └→ success_case / failure_case 影响 confidence
```

## 5. 重要方法签名

### 5.1 ManagerAgent

```python
# 盘前执行
async def run_pre_market(
    self,
    as_of_date: date,
    force: bool = False,
) -> DailyReport

# 盘后执行
async def run_after_close(
    self,
    as_of_date: date,
    force: bool = False,
) -> AfterCloseReport
```

### 5.2 EvidencePack

```python
@classmethod
def from_trade_idea(
    cls,
    idea: TradeIdea,
    signal_context: SignalContext,
    market_data: dict,
) -> EvidencePack
```

### 5.3 MetricsCalculator

```python
def compute_mfe_mae_return(
    entry_price: float,
    target_price: float,
    stop_loss: float,
    bars: list[dict],
    entry_date: str,
) -> tuple[float, float, float, bool, str | None, bool]
```

### 5.4 PostmortemService

```python
async def generate(
    self,
    evidence_pack: EvidencePack,
    llm_validator: LLMValidator | None = None,
    enable_llm_notes: bool = False,
) -> PostmortemResult

async def llm_attribution(
    self,
    evidence_pack: EvidencePack,
    auto_attribution: FailureAttribution,
    auto_confidence: float,
) -> tuple[FailureAttribution, str]:
```

### 5.5 RankingService

```python
async def add_entry(
    self,
    evidence_pack: EvidencePack,
    mfe: float | None,
    mae: float | None,
    return_pct: float | None,
) -> RankingEntry

async def generate_ranking(
    self,
    trade_date: str,
    trader_id: str,
) -> RankingResult
```

### 5.6 TraderMemoryStore

```python
def append(
    self,
    memory_type: TraderMemoryType,
    trader_id: str,
    content: str,
    symbol: str | None = None,
    idea_id: UUID | None = None,
    extra: dict | None = None,
    tags: list[str] | None = None,
    topic_source: str | None = None,
    raw_topic_ids: dict[str, list[str]] | None = None,
    archived: bool = False,
) -> TraderMemoryItem

def update(
    self,
    item_id: UUID,
    updates: dict,
) -> bool

def summarize_context(
    self,
    trader_id: str,
    symbol: str | None = None,
    memory_types: list[TraderMemoryType] | None = None,
    limit: int = 10,
) -> TraderMemorySummary

def list_filtered(
    self,
    trader_id: str | None = None,
    memory_types: list[TraderMemoryType] | None = None,
    symbol: str | None = None,
    tags: list[str] | None = None,
    strategy_version_id: str | None = None,
    archived: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[TraderMemoryItem]
```

## 6. 评估状态机

```
IdeaEvaluation.status 状态转换:

评估开始
    ↓
entry_price 存在？
    ├─ 否 → status = "not_evaluated"
    └─ 是 → bars 存在？
              ├─ 否 → status = "fallback"（降级使用 last_price）
              ├─ 是 → bars >= 2？
                        ├─ 否 → status = "partial"
                        └─ 是 → status = "ok"
```

## 7. Unique Constraint 设计

### 7.1 ranking_entries

**约束**：`uq_ranking_entry (trade_date, trader_id, strategy_version_id, symbol)`

**设计理由**：
- 不同交易员可能有相同的 Phase 0 entry（strategy_version_id=`__none__`）
- 必须加入 `trader_id` 防止跨交易员冲突

### 7.2 upsert 策略

**原问题**：UPDATE + INSERT 分离操作无法处理 constraint 不含 `is_latest` 的情况

**解决方案**：DELETE + INSERT 原子操作

```python
async def upsert(self, entry: RankingEntry) -> None:
    # 1. DELETE 旧记录
    await self.session.execute(
        delete(RankingEntryRecord).where(
            RankingEntryRecord.trade_date == entry.trade_date,
            RankingEntryRecord.trader_id == entry.trader_id,
            RankingEntryRecord.strategy_version_id == entry.strategy_version_id,
            RankingEntryRecord.symbol == entry.symbol,
        )
    )
    # 2. INSERT 新记录
    await self.session.add(record)
    await self.session.commit()
```

## 8. LLM 校验流程

> Design: [ntl-s5-012-bad-rating-llm-attribution-design](2026-04-25-ntl-s5-012-bad-rating-llm-attribution-design.md)

```
自动归因结果
    ↓
LLM 配置存在？
    ├─ 否 → 直接返回 auto
    └─ 是 → 构建 prompt
              ├→ system_prompt: 从 prompts/llm_attribution.md 加载
              └→ user_prompt: 基于 evidence_pack 填充变量
                        ↓
              LLM.complete_json()
                        ↓
              解析结果 → ValidationDecision
                        ↓
         ┌──────────────┼──────────────┐
         ↓              ↓              ↓
    confirm         correct         reject
    (确认)         (修正)         (拒绝)
         ↓              ↓              ↓
    source =         source =       source =
  llm_confirmed   llm_corrected  llm_rejected
```

## 9. Phase 0 特殊处理

Phase 0（无策略版本）场景：

| 字段 | 值 | 说明 |
|------|-----|------|
| `strategy_version_id` | `"__none__"` | 显式标记非空 |
| `status` | `"fallback"` | 无 bars 时降级 |
| `unique constraint` | 包含 trader_id | 防止跨交易员冲突 |

## 10. 相关文件索引

### 核心实现

| 文件 | 职责 | Design Doc |
|------|------|------------|
| `src/evaluation/evidence_pack.py` | EvidencePack 数据结构 | [evidence-pack-generation-design](2026-04-25-evidence-pack-generation-design.md) |
| `src/evaluation/failure_taxonomy.py` | 失败归因标签体系 | [failure-taxonomy-design](2026-04-25-failure-taxonomy-design.md) |
| `src/evaluation/postmortem_service.py` | 盘后复盘 Service | [postmortem-service-design](2026-04-25-postmortem-service-design.md) |
| `src/evaluation/metrics_calculator.py` | MFE/MAE/return_pct 计算 | [postmortem-metrics-design](2026-04-25-postmortem-metrics-design.md) |
| `src/evaluation/ranking_service.py` | Ranking Service | [ranking-service-design](2026-04-25-ranking-service-design.md) |
| `src/evaluation/ranking_repository.py` | Ranking 持久化 | [ranking-generation-design](2026-04-25-ranking-generation-design.md) |
| `src/models/ranking_entry.py` | RankingEntry ORM | — |
| `src/trader_memory/schemas.py` | 记忆 Schema | [trader-memory-schema-extension-design](2026-04-25-trader-memory-schema-extension-design.md) |
| `src/trader_memory/service.py` | 记忆 Store | — |
| `prompts/llm_attribution.md` | LLM 归因 Prompt | [ntl-s5-012-bad-rating-llm-attribution-design](2026-04-25-ntl-s5-012-bad-rating-llm-attribution-design.md) |

### Schema 扩展

| 文件 | 改动 |
|------|------|
| `src/schemas/contracts.py` | IdeaEvaluation.status 扩展 | [S5-013-postmortem-logic-upgrade-design](2026-04-26-S5-013-postmortem-logic-upgrade-design.md) |
| `src/schemas/review_task.py` | ReviewTaskDetails.failure_attribution | — |

### Agent 层

| 文件 | 改动 | Design Doc |
|------|------|------------|
| `src/agents/manager_agent/agent.py` | run_after_close 重构 | [postmortem-metrics-design](2026-04-25-postmortem-metrics-design.md) |
| `src/agents/trader_agent/agent.py` | _memory_hint / _profile_hint | [topic-memory-integration-design](2026-04-25-topic-memory-integration-design.md) |

## 11. 验证状态

| 模块 | 测试数 | 状态 |
|------|--------|------|
| evaluation | 70 | ✅ PASS |
| trader_memory | 30 | ✅ PASS |
| schemas | 15+ | ✅ PASS |
| market_universe | 20+ | ✅ PASS |
| **核心模块合计** | **143** | ✅ PASS |

---

## 12. 各子任务 Design Doc 链接

| 任务 | Design Doc |
|------|------------|
| NTL-S5-001: Evidence Pack 结构 | [evidence-pack-generation-design](2026-04-25-evidence-pack-generation-design.md) |
| NTL-S5-002: 失败归因分类 | [failure-taxonomy-design](2026-04-25-failure-taxonomy-design.md) |
| NTL-S5-003: 盘后复盘 Service | [postmortem-service-design](2026-04-25-postmortem-service-design.md) |
| NTL-S5-004: Ranking Service | [ranking-service-design](2026-04-25-ranking-service-design.md) / [ranking-generation-design](2026-04-25-ranking-generation-design.md) |
| NTL-S5-005: TraderMemory Schema 扩展 | [trader-memory-schema-extension-design](2026-04-25-trader-memory-schema-extension-design.md) |
| NTL-S5-006: Topic-Memory 集成 | [topic-memory-integration-design](2026-04-25-topic-memory-integration-design.md) |
| NTL-S5-008: postmortem 接入任务系统 | [postmortem-task-integration-design](2026-04-25-postmortem-task-integration-design.md) |
| NTL-S5-010: 评分口径升级 | [postmortem-metrics-design](2026-04-25-postmortem-metrics-design.md) |
| NTL-S5-012: LLM 归因写回 | [ntl-s5-012-bad-rating-llm-attribution-design](2026-04-25-ntl-s5-012-bad-rating-llm-attribution-design.md) |
| NTL-S5-013: 替换简化评估逻辑 | [S5-013-postmortem-logic-upgrade-design](2026-04-26-S5-013-postmortem-logic-upgrade-design.md) |

---

## TaskList 索引

本文档链接到 TaskList.md Stage 5 完成情况：
- NTL-S5-001~014：全部完成 ✅
- Stage 5 完成标准：已满足 ✅
- Stage 6：`NTL-S6-001` 起，开始回测基础设施
