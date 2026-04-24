# Stage 4 设计文档

> 日期：2026-04-24
> 状态：已完成
> 对应任务：NTL-S4-001 ~ NTL-S4-011

---

## 1. 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ManagerAgent                                │
│                   （编排层，只负责循环调用）                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────┐    ┌──────────────────────┐               │
│  │   PreMarketService   │    │   run_after_close    │               │
│  │  (per-trader 编排)   │    │                      │               │
│  └───────┬──────────────┘    └──────────────────────┘               │
│          │                                                           │
│  ┌───────▼──────────────┐                                          │
│  │    TraderAgent        │◄── strategy_version (per-trader)         │
│  │  (per-trader 执行器)   │◄── market_universe (shared snapshot)     │
│  └───────┬──────────────┘                                          │
│          │ generate_trade_ideas()                                   │
│  ┌───────▼──────────────┐    ┌──────────────────────┐               │
│  │   StrategyAgent      │───►│     RiskAgent        │               │
│  │   (规则评估层)         │    │   (风险过滤层)        │               │
│  └──────────────────────┘    └──────────────────────┘               │
│                                                                      │
│  ┌──────────────────────┐    ┌──────────────────────┐               │
│  │   DataAgent          │    │   SignalVersioning   │               │
│  │  (capability router) │    │   (信号持久化)        │               │
│  └──────────────────────┘    └──────────────────────┘               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 职责边界

| 组件 | 职责 | 不承担 |
|------|------|--------|
| `ManagerAgent` | 循环调用 PreMarketService，汇总 DailyReport | 具体业务逻辑 |
| `PreMarketService` | per-trader 编排：版本加载→想法生成→定向深挖→信号评估→missing symbols | 单个 agent 实现 |
| `TraderAgent` | 基于策略版本和候选池生成 TradeIdea | 风险评估 |
| `StrategyAgent` | 基于规则快照生成 RawSignal | 数据获取 |
| `RiskAgent` | 基于账户快照和风控规则过滤信号 | 规则生成 |
| `DataAgent` | 按 dataset 路由到对应 skill | 业务判断 |

---

## 2. Phase 0 vs Stage 4 双路径决策

### 路径选择

```
stage4.enable = True?
├── Yes: 使用 Stage 4 路径
│   ├── strategy_version 可用?
│   │   ├── Yes: 使用 strategy_version.recommendations 生成候选
│   │   └── No: allow_phase0_fallback?
│   │       ├── Yes: 降级到 watchlist + last_price
│   │       └── No: 跳过该 trader（不生成任何 idea）
│   └── market_universe 快照存在?
│       └── Yes: 提取 strong_symbol_hint 注入 TraderAgent
│
└── No: 降级到 Phase 0 路径（watchlist + last_price）
```

### 配置控制

```python
class Stage4Config(BaseModel):
    enable: bool = True              # 是否启用 Stage 4 路径
    market_universe_slot: str = "09-25"  # 候选池快照时段
    allow_phase0_fallback: bool = True   # strategy_version 不可用时是否降级
```

### 关键区别

| 维度 | Phase 0 | Stage 4 |
|------|---------|---------|
| 候选来源 | watchlist + last_price | strategy_version.recommendations |
| 候选池上下文 | 无 | market_universe_snapshot |
| 决策类型 | 仅 buy | buy / sell / hold |
| 规则来源 | 硬编码模板 | strategy_version.rules_snapshot |
| 追溯能力 | 弱 | strategy_version_id + topic_source_ids |

---

## 3. 定向深挖 DataRequest 规划

### 工作流程

```
TraderAgent.generate_trade_ideas()
    │
    ▼
PreMarketService._plan_data_requests(strategy_version, candidate_symbols)
    │  分析 rules_snapshot 中引用的字段
    │  字段映射到 DataAgent dataset
    │
    ▼
DataRequest(symbols=candidate_symbols, dataset=indicators, fields=[rsi, macd, ...])
DataRequest(symbols=candidate_symbols, dataset=ohlcv_1d, fields=[close, volume, ...])
    │
    ▼
DataAgent.handle() → 获取额外市场数据
    │
    ▼
StrategyAgent.generate_raw_signal(market_data=deep_market_data)
```

### 字段 → Dataset 映射

| 字段 | Dataset |
|------|---------|
| rsi, macd, bollinger, atr, kdj, cci, obv | indicators |
| close, open, high, low, volume, turnover | ohlcv_1d |

### 触发条件

- `strategy_version` 存在
- `strategy_version.rules_snapshot` 非空
- 规则条件中引用了上述字段

---

## 4. SignalContext 追溯字段设计

### 新增字段

```python
class SignalContext(BaseModel):
    # ... 原有字段 ...

    # NTL-S4-004 新增
    strategy_version_id: str | None = None       # 来源策略版本
    market_universe_snapshot: dict | None = None  # 市场候选池快照
    topic_source_ids: list[str] = []             # 关联的主题来源

class Signal(BaseModel):
    # ... 原有字段 ...

    # NTL-S4-004 新增
    strategy_version_id: str | None = None
```

### 填充时机

| 字段 | 填充位置 | 条件 |
|------|----------|------|
| `strategy_version_id` | `_record_ideas_as_signals()` | strategy_version 存在 |
| `market_universe_snapshot` | `_record_ideas_as_signals()` | market_universe 非 None（TD-003 已修复） |
| `topic_source_ids` | `_record_ideas_as_signals()` | idea.source_topic_ids 非空 |

---

## 5. 关键数据结构

### TradeIdea 新增字段

```python
class TradeIdea(BaseModel):
    # ... 原有字段 ...

    # NTL-S4-008 新增
    source_recommendation_idx: int | None = None  # 来源 recommendation 索引
```

### DailyReport 新增字段

```python
class DailyReport(BaseModel):
    # ... 原有字段 ...

    # NTL-S4-008 新增
    strategy_version_ids: list[str] = []  # 本次使用的所有策略版本
```

### StrategyVersion 新增字段

```python
class StrategyVersion(BaseModel):
    # ... 原有字段 ...

    # NTL-S4-003 新增
    rules_snapshot: list[dict] = []  # 评估规则快照
```

---

## 6. PreMarketService 编排流程

```python
async def run_for_trader(trader_cfg, market_universe, as_of_date):
    # 1. 策略版本加载（Stage 4 路径）
    if stage4.enable:
        strategy_version = await strategy_library_service.get_current_released_version(...)
        if strategy_version is None and not allow_phase0_fallback:
            return PreMarketResult(ideas=[], ...)

    # 2. TraderAgent 生成想法
    ideas = await trader.generate_trade_ideas(
        strategy_version=strategy_version,
        market_universe=market_universe,
    )

    # 3. 定向深挖 DataRequest
    if strategy_version and strategy_version.rules_snapshot:
        needed = _plan_data_requests(strategy_version, candidate_symbols)
        for dataset, fields in needed.items():
            resp = await data_agent.handle(DataRequest(dataset=dataset, ...))
            if resp.status == ok:
                deep_market_data[dataset] = resp.payload

    # 4. 信号评估
    for idea in ideas:
        signal = await _evaluate_idea(idea, deep_market_data)
        evaluated_signals.append(signal)

    # 5. Missing symbols 任务
    missing_symbol_tasks = [...]

    return PreMarketResult(
        ideas=ideas,
        strategy_version_id=strategy_version.version_id if strategy_version else None,
        evaluated_signals=evaluated_signals,
        missing_symbol_tasks=missing_symbol_tasks,
    )
```

---

## 7. 测试覆盖

| 测试 | 验证内容 |
|------|----------|
| `test_stage4_path_with_strategy_version` | Stage 4 路径候选来自 recommendations，不是 watchlist |
| `test_phase0_fallback_when_no_strategy_version` | DB 不可用时降级到 watchlist |
| `test_allow_phase0_false_skips_trader` | allow_phase0_fallback=False 时跳过 trader |
| `test_daily_report_includes_strategy_version_ids` | DailyReport.strategy_version_ids 正确填充 |
| `test_trade_idea_side_reflects_strategy_decision` | buy/sell/hold 决策正确传递 |
| `test_manager_records_ideas_as_signals` | Signal side = BUY，metadata 正确 |
| `test_list_signals_filters_by_symbol` | 信号按标的过滤 |

**合计：10 tests PASS**

---

## 8. 技术债（已全部处理）

| 编号 | 描述 | 状态 |
|------|------|------|
| ~~TD-001~~ | ~~sell 决策的 target/stop 未镜像调整~~ | ✅ 已修复：sell 时 target=entry*(1-target_pct)，stop=entry*(1+stop_pct) |
| ~~TD-002~~ | ~~FallbackProvider partial 处理未实现~~ | ✅ 已修复：Builder 层从 partial_payloads 合并 items |
| ~~TD-003~~ | ~~SignalContext.market_universe_snapshot 未填充~~ | ✅ 已修复：dataclasses.asdict 序列化后写入 SignalContext |

---

## 9. 文件变更清单

| 文件 | 变更类型 |
|------|----------|
| `src/agents/trader_agent/agent.py` | 重构 |
| `src/agents/strategy_agent/agent.py` | 新增 strategy_version 支持 |
| `src/agents/manager_agent/agent.py` | 重构 |
| `src/agents/manager_agent/premarket_service.py` | 新增 |
| `src/strategy/types.py` | 新增追溯字段 |
| `src/strategy/signal_version.py` | 扩展序列化 |
| `src/strategy_library/schemas.py` | 新增 rules_snapshot |
| `src/common/config.py` | 新增 Stage4Config |
| `src/schemas/contracts.py` | TradeIdea + DailyReport 扩展 |
| `tests/unit/agents/test_trader_agent.py` | 新增 3 个测试 |
| `tests/unit/agents/test_manager_agent.py` | 新增 5 个测试 |
