# Stage 2 设计文档

> 日期：2026-04-23
> 状态：已完成
> 对应任务：NTL-S2-001 ~ NTL-S2-024

---

## 1. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         DataAgent                                │
│                    (capability router)                            │
│         按 dataset 字段路由到对应 skill，返回标准化 payload          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │fetch_hot_topics│ │fetch_topic_  │ │fetch_strong_ │            │
│  │              │ │constituents  │ │symbols       │            │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘            │
│         │                │                 │                     │
│  ┌──────▼────────────────▼─────────────────▼───────┐           │
│  │              SnapshotService                     │           │
│  │         (filesystem JSON backend)                │           │
│  └──────────────────────┬──────────────────────────┘           │
│                         │                                        │
│  ┌──────────────────────▼──────────────────────────┐           │
│  │         HotTopicsBuilder / ConstituentsResolver   │           │
│  │         / StrongSymbolsSelector                  │           │
│  └──────────────────────┬──────────────────────────┘           │
│                         │                                        │
│  ┌──────────────────────▼──────────────────────────┐           │
│  │           Provider 层（可级联降级）               │           │
│  │  ┌────────────┐  ┌────────────┐  ┌───────────┐ │           │
│  │  │ Kaipan     │  │ AkShare    │  │ Fallback  │ │           │
│  │  │ Provider   │  │ Provider   │  │ Provider  │ │           │
│  │  └────────────┘  └────────────┘  └───────────┘ │           │
│  └─────────────────────────────────────────────────┘           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 核心目标

- 建立 provider 抽象层，支持多数据源级联降级
- 生成每日热点、题材成分、强势池快照
- DataAgent 从"仅 last_price"升级为 capability router

---

## 2. Provider 抽象

### 基类契约（NTL-S2-001）

```python
class ProviderBase:
    """Provider 必须实现 request() 和 normalize()。"""

    provider_name: str

    def request(self, *, capability: str, **kwargs) -> dict[str, Any]:
        """发起请求，返回归一化前的原始数据。"""
        ...

    def normalize(self, *, capability: str, raw: dict, **kwargs) -> dict[str, Any]:
        """将 raw 数据归一化为标准 payload。"""
        ...

    def run(self, capability: str, *, request: dict | None = None) -> ProviderResult:
        """统一入口：request → normalize → ProviderResult"""
        ...
```

### ProviderResult 结构

```python
@dataclass
class ProviderResult:
    provider: str
    capability: str
    status: ProviderStatus  # ok / error / partial
    payload: dict[str, Any]
    errors: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
```

### 已实现 Provider

| Provider | 职责 | capability |
|----------|------|------------|
| `KaipanProvider` | 私有接口：热点、题材成分、强势池 | hot_topics / topic_constituents / strong_symbols |
| `AkShareProvider` | 公开行情：日线 OHLCV | ohlcv_1d |
| `MarketDataProvider` | 行情统一入口（复用 AkShare 或 cache） | ohlcv_1d / indicators |
| `FallbackProvider` | 级联降级：capability → 有序 provider 链 | 任意已注册 capability |

---

## 3. Market Universe 数据结构

### 快照类型

| 类型 | 构建器 | 输出 |
|------|--------|------|
| `hot_topics` | HotTopicsBuilder | HotTopicsPayload（topic 列表 + score） |
| `topic_constituents` | ConstituentsResolver | TopicConstituentsPayload（成分列表 + leader） |
| `strong_symbols` | StrongSymbolsSelector | StrongSymbolsPayload（标的列表 + strength_score） |

### Schema 设计原则

- **全部使用 Python `dataclass`**，无 ORM 依赖
- Schema 与 ORM 完全解耦——dataclass 约束内存结构，不绑定数据库表
- `MarketUniverse` 是三层 payload 的顶层聚合，供 TraderAgent / StrategyAgent 消费

### Schema ↔ ORM 转换路径（TD-003-b 已明确）

详见 `src/models/converters.py`。转换规则：

| 场景 | 存储方式 |
|------|----------|
| 标量字段（str/float/int/UUID） | ORM 列直写 |
| 复杂嵌套结构（PriceSpec / PositionSize） | JSONB 列 |
| 列表字段（rules_snapshot, triggered_rules） | JSONB 列 |
| 完整聚合对象（SignalContext, EvidencePack） | JSONB 列 + ID 引用 |

写入路径：Schema → `converters.py` → ORM 实例 → `session.add()`
读取路径：ORM 实例 → `converters.py` → Schema dataclass

### MarketUniverse 聚合结构

```python
@dataclass(frozen=True)
class MarketUniverse:
    trade_date: str
    slot: str
    hot_topics: HotTopicsPayload | None = None
    topic_constituents: TopicConstituentsPayload | None = None
    strong_symbols: StrongSymbolsPayload | None = None
    fetched_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

---

## 4. Snapshot Service

### 文件系统后端

- **存储路径**：`data/market_universe/snapshots/{dataset}/{trade_date}/{slot}.json`
- **元信息内嵌**：fetched_at、source、request 参数、provider 名称
- **操作接口**：

```python
class SnapshotService:
    async def save(self, dataset: str, trade_date: str, slot: str, payload: dict) -> None: ...
    async def load(self, dataset: str, trade_date: str, slot: str) -> dict | None: ...
    async def list_snapshots(self, dataset: str | None = None, limit: int = 30) -> list[dict]: ...
    async def delete(self, dataset: str, trade_date: str, slot: str) -> None: ...
```

---

## 5. DataAgent Capability Router

### 路由表

```python
# src/agents/data_agent/agent.py
async def handle(self, req: DataRequest) -> DataResponse:
    if req.dataset == "hot_topics":
        return await fetch_hot_topics(req)
    elif req.dataset == "topic_constituents":
        return await fetch_topic_constituents(req)
    elif req.dataset == "strong_symbols":
        return await fetch_strong_symbols(req)
    elif req.dataset == "ohlcv_1d":
        return await fetch_ohlcv(req)
    elif req.dataset == "indicators":
        return await fetch_indicators(req)
    elif req.fields and "last_price" in req.fields:
        return await fetch_market(req)
    else:
        return DataResponse(status=DataResponseStatus.capability_missing, ...)
```

### 降级策略

| 状态 | 行为 |
|------|------|
| `capability_missing` | 返回 missing 状态 + AgentTask |
| `error` | 上游 provider 异常，记录错误 |
| `partial` | 部分成功，返回可用 payload |
| `ok` | 正常返回 |

---

## 6. FallbackProvider 级联降级

### 降级链示例

```python
FallbackProvider(chains={
    "hot_topics": [kaipan_provider, akshare_provider],
    "ohlcv_1d": [akshare_provider, market_data_cache],
})
```

### 三种返回场景

| 场景 | 返回状态 | payload |
|------|----------|---------|
| 首个 provider 成功 | `ok` | 成功结果 |
| 所有 provider 部分成功 | `partial` | `{"partial": True, "partial_payloads": [...], "errors": [...]}` |
| 所有 provider 完全失败 | 抛出 `ProviderError` | 完整错误列表 |

### partial 结果合并（TD-002 已修复）

当 FallbackProvider 返回 `partial=True` 时，Builder 层会从 `partial_payloads` 中提取并合并各 provider 的 items 列表（topics/constituents/symbols），去重后输出完整结果：

- `HotTopicsBuilder`：合并多个 provider 的 `topics` 列表
- `ConstituentsResolver`：合并多个 provider 的 `constituents` 列表
- `StrongSymbolsSelector`：合并多个 provider 的 `symbols` 列表

trade_date/slot/sources 均从首个有效 payload 提取，sources 列表合并去重。

---

## 7. Pipeline 快照任务

| 任务 | handler | 触发时机 |
|------|---------|----------|
| 热点快照 | `handle_hot_topics_snapshot` | 盘后（17:30） |
| 题材成分快照 | `handle_topic_constituents_snapshot` | 盘后（17:30） |
| 强势池快照 | `handle_strong_symbols_snapshot` | 盘后（17:30） |

---

## 8. 测试覆盖

| 模块 | 测试数 | 验证内容 |
|------|--------|----------|
| provider base | - | ProviderBase 抽象契约 |
| kaipan_provider | - | 私有接口 raw fetch + capability 封装 |
| akshare_provider | - | AkShare 行情归一化为 ohlcv_1d |
| market_data_provider | - | 多数据源优先级 |
| fallback_provider | 17 | 级联降级、partial 处理、错误聚合 |
| market_universe/schemas | 9 | dataclass 结构与默认值 |
| hot_topics_builder | 9 (+1 partial) | 热点构建与去重 |
| constituents_resolver | 7 (+1 partial) | 题材成分解析与去重 |
| strong_symbols_selector | 8 (+1 partial) | 强势池筛选 |
| snapshot_service | 8 | save/load/list/delete |
| data_agent skills | - | hot_topics/topic_constituents/strong_symbols/ohlcv/indicators |
| **合计** | **54+** | |

---

## 9. 文件变更清单

| 类别 | 文件 |
|------|------|
| **Provider** | `src/providers/base.py`（ProviderBase/ProviderResult/ProviderStatus） |
| | `src/providers/kaipan_provider.py`（升级为 capability provider） |
| | `src/providers/akshare_provider.py`（新增） |
| | `src/providers/market_data_provider.py`（新增） |
| | `src/providers/fallback_provider.py`（新增） |
| **Market Universe** | `src/market_universe/schemas.py`（HotTopic/TopicConstituent/StrongSymbol + Payload + MarketUniverse） |
| | `src/market_universe/hot_topics_builder.py`（新增） |
| | `src/market_universe/constituents_resolver.py`（新增） |
| | `src/market_universe/strong_symbols_selector.py`（新增） |
| | `src/market_universe/snapshot_service.py`（新增） |
| **DataAgent** | `src/agents/data_agent/skills/fetch_hot_topics.py`（新增） |
| | `src/agents/data_agent/skills/fetch_topic_constituents.py`（新增） |
| | `src/agents/data_agent/skills/fetch_strong_symbols.py`（新增） |
| | `src/agents/data_agent/skills/fetch_ohlcv.py`（新增） |
| | `src/agents/data_agent/skills/fetch_indicators.py`（新增） |
| | `src/agents/data_agent/agent.py`（升级为 capability router） |
| **Pipeline** | `src/pipeline/tasks/snapshot_tasks.py`（新增 3 个 handler） |
| **配置** | `src/common/config.py`（KaipanConfig / DataConfig 扩展） |

---

## 10. 与其他 Stage 的关系

```
Stage 2（数据底座）
     │
     │ 提供 hot_topics / topic_constituents / strong_symbols 快照
     ▼
Stage 3（策略版本构建）
     │ 消费 MarketUniverse 构建 StrategyVersion
     ▼
Stage 4（盘前主链路）
     │ 消费 StrategyVersion + MarketUniverse 生成 TradeIdea
     ▼
Stage 5（盘后评估）
     │ 消费盘前信号 + 快照 + 评估结果
```

Stage 2 的 snapshot_service 和 market_universe schema 是整个主线的数据基础设施，被 Stage 3/4/5 依赖。
