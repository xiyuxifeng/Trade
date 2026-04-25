# NTL-S5-009 设计文档：Manager 生成 Evidence Pack

## 1. 目标

在 `run_after_close` 中为每条盘前建议生成并持久化 `EvidencePack`，供后续 `postmortem_analysis` 任务 handler 直接加载。

## 2. 前置依赖

| 任务 | 状态 |
|------|------|
| NTL-S5-001 EvidencePack 结构 | ✅ |
| NTL-S5-008 postmortem 接入任务系统 | ✅（NTL-S5-009 在其之后）|
| NTL-S4-008 策略版本追溯 | ✅（strategy_version_id 已写入 TradeIdea）|
| NTL-S4-005 SignalContext 扩展 | ✅（topic_source_ids/market_universe_snapshot）|

## 3. 现状 vs 目标

### 现状（NTL-S5-008 后）
- `postmortem_tasks` 构造**最小** EvidencePack：
  - `signal_context=None`
  - `market_data={"last_price": 9.5}`
  - `strategy_version_snapshot=[]`
- 无法做真正的归因分析（MFE/MAE/规则命中）

### 目标
- `run_after_close` 生成**完整** EvidencePack：
  - `trade_idea` — 原始 TradeIdea
  - `signal_context` — 从 `signal_versioning` 加载（已有持久化）
  - `market_data` — 从 DataAgent 获取 `ohlcv_1d` + `indicators`（完整行情）
  - `strategy_version_snapshot` — 从 `StrategyLibraryService` 加载 rules_snapshot

## 4. 持久化方式

**JSON 文件**（与 DailyReport/EvaluationResult 模式一致）

路径：`{output_dir}/evidence_packs/{idea_id}.json`

理由：
- 与现有 JSON 文件模式一致（DailyReport/EvaluationResult）
- `postmortem_tasks` 已有 `read_json()` 读取 DailyReport，加载 EvidencePack 只改路径
- YAGNI：当前无 DB 查询需求
- ORM (EvidencePackRecord) 后续可接入

## 5. EvidencePack 构造逻辑

### 5.1 文件位置
`src/agents/manager_agent/agent.py` — 在 `run_after_close` 末尾（每个 idea 评估完成后）调用

### 5.2 构造流程

```
对于每个被评估的 idea：
    1. 从 signal_versioning 加载 SignalContext（{output_dir}/signals/idea_{idea_id}.json）
    2. 从 DataAgent 获取 ohlcv_1d + indicators（用于 MFE/MAE 计算）
    3. 从 StrategyLibraryService 加载 StrategyVersion（获取 rules_snapshot）
    4. 构造 EvidencePack.from_trade_idea(...)
    5. 写入 {output_dir}/evidence_packs/{idea_id}.json
    6. 将 pack_id 追加到 evaluation.evidence_pack_refs
```

### 5.3 market_data 结构

```python
market_data = {
    "ohlcv_1d": {
        "symbol": {
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": float,
        }
    },
    "indicators": {
        "symbol": {
            "rsi_14": float | None,
            "macd": {...},
            ...
        }
    },
    "entry_price": float,    # 来自 TradeIdea.entry.price
    "current_price": float,  # 来自 DataAgent.last_price
}
```

### 5.4 signal_context 加载

```python
# signal_versioning 存储路径：{output_dir}/signals/idea_{idea_id}.json
# SignalWithContext = {"signal": {...}, "context": {...}}
signal_with_ctx = signal_versioning.get_version(f"idea_{idea_id}")
signal_context = signal_with_ctx.context if signal_with_ctx else None
```

### 5.5 strategy_version_snapshot 加载

```python
# 从 StrategyLibraryService 加载 StrategyVersion
service = StrategyLibraryService()
version = await service.get_version(session, strategy_version_id)
rules_snapshot = version.rules_snapshot if version else []
```

**注意**：`StrategyLibraryService` 方法需确认是否已有 `get_version` 或需要新增。

## 6. run_after_close 修改

在评估循环内（`for idea in daily_report.ideas`）的**每个 idea 评估完成后**，追加：

```python
# 为每个 idea 生成 EvidencePack（NTL-S5-009）
evidence_pack = await self._generate_evidence_pack(idea, daily_report, last_prices, config)
self._save_evidence_pack(evidence_pack)
evaluations[-1].evidence_pack_refs.append(str(evidence_pack.pack_id))
```

## 7. 新增方法

### 7.1 `_generate_evidence_pack`

```python
async def _generate_evidence_pack(
    self,
    idea: TradeIdea,
    daily_report: DailyReport,
    last_prices: dict[str, float],
    config: AppConfig,
) -> EvidencePack:
    """为单条 TradeIdea 生成完整 EvidencePack。"""
    # 1. 加载 SignalContext
    signal_context = self._load_signal_context(idea.idea_id)

    # 2. 获取完整行情（ohlcv_1d + indicators）
    market_data = await self._fetch_full_market_data([idea.symbol], config)
    market_data["entry_price"] = float(idea.entry.price) if idea.entry and idea.entry.price else None
    market_data["current_price"] = last_prices.get(idea.symbol)

    # 3. 获取策略版本快照
    rules_snapshot = await self._load_strategy_version_snapshot(idea.strategy_version_id, config)

    return EvidencePack.from_trade_idea(
        trade_idea=idea,
        signal_context=signal_context,
        market_data=market_data,
        strategy_version_id=idea.strategy_version_id,
        strategy_version_snapshot=rules_snapshot,
    )
```

### 7.2 `_load_signal_context`

```python
def _load_signal_context(self, idea_id: UUID) -> SignalContext | None:
    """从 signal_versioning 加载 SignalContext。"""
    signal_with_ctx = self.signal_versioning.get_version(f"idea_{idea_id}")
    return signal_with_ctx.context if signal_with_ctx else None
```

### 7.3 `_fetch_full_market_data`

```python
async def _fetch_full_market_data(self, symbols: list[str], config: AppConfig) -> dict[str, Any]:
    """从 DataAgent 获取完整行情（ohlcv_1d + indicators）。"""
    agent = DataAgent(config=config)
    req = DataRequest(
        trader_id="manager",
        symbols=symbols,
        fields=["ohlcv_1d", "indicators"],
    )
    resp = await agent.handle(req)
    if resp.status == DataResponseStatus.ok:
        return resp.payload
    return {}
```

### 7.4 `_load_strategy_version_snapshot`

```python
async def _load_strategy_version_snapshot(
    self,
    strategy_version_id: str | None,
    config: AppConfig,
) -> list[dict]:
    """从 StrategyLibraryService 加载 rules_snapshot。"""
    if not strategy_version_id:
        return []
    service = StrategyLibraryService()
    async with session_scope() as session:
        version = await service.get_version(session, strategy_version_id)
        return version.rules_snapshot if version else []
```

**注意**：`StrategyLibraryService` 当前无 `get_version` 方法，需在 `StrategyLibraryRepository` 新增 `get_by_version_id`，然后在 `StrategyLibraryService` 暴露。

### 7.5 `_save_evidence_pack`

```python
def _save_evidence_pack(self, pack: EvidencePack) -> None:
    """将 EvidencePack 写入 JSON 文件。"""
    pack_dir = self.output_dir / "evidence_packs"
    pack_dir.mkdir(parents=True, exist_ok=True)
    path = pack_dir / f"{pack.pack_id}.json"
    write_json(path, pack.to_dict())
```

## 8. postmortem_tasks 修改

`handle_postmortem_analysis` 中替换 EvidencePack 构造逻辑：

```python
# 之前（NTL-S5-008）：ad-hoc 构造
evidence_pack = EvidencePack(
    idea_id=trade_idea.idea_id,
    ...
)

# 之后（NTL-S5-009）：从文件加载
pack_path = _evidence_pack_path(pack_id)
if pack_path.exists():
    pack_data = read_json(pack_path)
    evidence_pack = EvidencePack.from_dict(pack_data)
else:
    # fallback：降级到最小实现（保留容错）
    evidence_pack = EvidencePack(...)
```

## 9. 产物清单

| 文件 | 操作 |
|------|------|
| `src/agents/manager_agent/agent.py` | 修改（新增 5 个方法 + run_after_close 调用）|
| `src/pipeline/tasks/postmortem_tasks.py` | 修改（从 JSON 加载 EvidencePack）|
| `tests/unit/agents/test_manager_agent.py` | 增强测试（如有） |

## 10. 验证

- `run_after_close` 生成 `evidence_packs/{pack_id}.json` 文件
- `postmortem_tasks` 从文件加载后 `failure_attribution` 归因结果正确
- 完整行情数据（ohlcv_1d + indicators）在 EvidencePack 中可用

## 11. 后续任务

- **NTL-S5-010**：使用 EvidencePack 中的完整行情计算 MFE/MAE
- **NTL-S5-011**：EvidencePack.rank_id → RankingEntry 生成
- **NTL-S5-012**：差评触发 LLM 归因（使用 signal_context 中的 topic_source_ids）
