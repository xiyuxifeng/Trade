# NTL-S5-008 设计文档：postmortem 接入任务系统

## 1. 目标

把 `PostmortemService` 接入任务系统（`pending_tasks.jsonl` + `process_tasks`），实现：
- `run_after_close` 末尾为每个待复盘 idea 创建 `postmortem_analysis` 任务
- `process_tasks` 通过 handler 执行自动归因
- 归因结果写入 `TraderMemory`（类型：`postmortem`）

## 2. 前置依赖

| 任务 | 状态 | 说明 |
|------|------|------|
| NTL-S5-001 EvidencePack | ✅ | PostmortemService 依赖 EvidencePack |
| NTL-S5-002 失败归因分类 | ✅ | FailureAttribution 已定义 |
| NTL-S5-003 盘后复盘 Service | ✅ | PostmortemService 已实现 |
| NTL-S5-007 ReviewTask 扩展 | ✅ | ReviewTaskDetails.failure_attribution 已存在 |
| NTL-S5-009 Manager 生成 EvidencePack | ✅ | 已完成，handler 优先从 JSON 加载 EvidencePack，缺失时降级构造 |

**说明**：NTL-S5-009 已完成。handler 内优先通过 `evidence_pack_index.json` 查找并加载持久化的 EvidencePack；若未找到则降级构造最小 `EvidencePack`（含 last_price 映射为单日 bars）。

## 3. 任务类型定义

### 3.1 Task Type
```
postmortem_analysis
```

### 3.2 Details 字段

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `idea_id` | str (UUID) | `TradeIdea.idea_id` | 用于加载 TradeIdea 和构建 EvidencePack |
| `trade_date` | str | `as_of_date` | 交易日，用于路径和查询 |
| `trader_id` | str | `TradeIdea.trader_id` | 用于 TraderMemory 写入 |
| `symbol` | str | `TradeIdea.symbol` | 用于参考 |

### 3.3 触发时机
在 `run_after_close` 遍历每个 idea 完成后（非 `not_evaluated` 状态），创建 `postmortem_analysis` 任务并 `_append_task`。

## 4. Handler 实现

### 4.1 文件位置
```
src/pipeline/tasks/postmortem_tasks.py
```

### 4.2 核心逻辑

```python
async def handle_postmortem_analysis(
    details: dict[str, Any],
    *,
    config: AppConfig,
) -> None:
    """对单笔交易执行自动归因并写回 TraderMemory。

    Details 参数：
        idea_id: UUID string
        trade_date: YYYY-MM-DD
        trader_id: str
        symbol: str

    流程：
        1. 从 DailyReport 加载 TradeIdea
        2. 构造最小 EvidencePack（market_data 从 DataAgent 获取 last_price）
        3. 调用 PostmortemService.generate() 获取归因结果
        4. 将 PostmortemResult 写入 TraderMemory（类型=postmortem）
    """
```

### 4.3 EvidencePack 加载与 fallback 构造

handler 优先通过索引文件查找并加载已持久化的 EvidencePack：

```python
pack_id = _find_evidence_pack_id(idea_id_str, config)  # O(1) 索引查询
if pack_id:
    pack_path = _evidence_pack_path(pack_id, config)
    if pack_path.exists():
        pack_data = read_json(pack_path)
        evidence_pack = EvidencePack.from_dict(pack_data)
    else:
        # fallback：降级到最小实现
        ...
else:
    # fallback：降级到最小实现
    evidence_pack = EvidencePack(
        idea_id=trade_idea.idea_id,
        trade_date=str(trade_idea.as_of_date),
        trade_idea=trade_idea,
        signal_context=None,
        market_data=MarketDataSnapshot(
            last_price=fallback_price,
            bars=fallback_bars,
            entry_price=float(trade_idea.entry.price) if trade_idea.entry else 0.0,
            target_price=trade_idea.target_price,
            stop_loss_price=trade_idea.stop_loss_price,
        ),
        strategy_version_id=trade_idea.strategy_version_id,
        strategy_version_snapshot=[],
    )
```

### 4.4 TraderMemory 写入

写入内容：
- `TraderMemoryItem(memory_type=TraderMemoryType.postmortem, ...)`
- `failure_attribution` → `postmortem_data` 字段（JSON 序列化）
- `attribution_source` → `postmortem_data.source`
- tags 包含 `["postmortem", idea.trader_id, idea.symbol]`

## 5. run_after_close 修改

在 `run_after_close` 末尾（写入 EvaluationResult 之前），对每个 `return_pct < threshold` 的 idea：

```python
# 为每个未通过评估的 idea 创建 postmortem_analysis 任务
if return_pct < min_ret:
    review_task = self._build_review_task(...)  # 已有
    self._append_task(review_task)

    # NTL-S5-008 新增：创建 postmortem_analysis 任务
    postmortem_task = AgentTask(
        type="postmortem_analysis",
        title=f"Postmortem for {idea.symbol} on {as_of_date}",
        trader_id=idea.trader_id,
        idea_id=idea.idea_id,
        details={
            "idea_id": str(idea.idea_id),
            "trade_date": str(as_of_date),
            "trader_id": idea.trader_id,
            "symbol": idea.symbol,
        },
    )
    self._append_task(postmortem_task)
```

## 6. process_tasks.py 修改

### 6.1 注册 Handler

在 `_create_handlers()` 中添加：

```python
from src.pipeline.tasks.postmortem_tasks import handle_postmortem_analysis

async def handle_postmortem_analysis_wrapped(details: dict[str, Any]) -> None:
    await handle_postmortem_analysis(details, config=config)

return {
    ...
    "postmortem_analysis": handle_postmortem_analysis_wrapped,
}
```

## 7. 错误处理

| 错误场景 | 处理方式 |
|----------|----------|
| DailyReport 不存在 | 跳过，打印 warning |
| TradeIdea 找不到 | 跳过，打印 warning |
| PostmortemService.generate 异常 | 任务失败，由 process_tasks 重试机制处理 |
| TraderMemory 写入失败 | 任务失败，由 process_tasks 重试机制处理 |

## 8. 测试策略

### 8.1 单元测试
- `test_handle_postmortem_analysis_*`：测试各种错误场景
  - DailyReport 不存在
  - Idea 评估通过（无需 postmortem）
  - PostmortemService 异常

### 8.2 集成测试
- 已有 `test_trader_memory_schemas.py` 验证 TraderMemoryItem 序列化
- 已有 `test_contracts.py` 验证 ReviewTaskDetails 序列化

## 9. 产物清单

| 文件 | 操作 |
|------|------|
| `src/pipeline/tasks/postmortem_tasks.py` | 新增 |
| `src/agents/manager_agent/agent.py` | 修改（run_after_close 添加 postmortem_analysis task）|
| `src/pipeline/tasks/process_tasks.py` | 修改（注册 handler）|
| `tests/unit/pipeline/test_postmortem_tasks.py` | 新增（如需要） |

## 10. 后续任务

- **NTL-S5-009**：ManagerAgent 生成 Evidence Pack → handler 可直接加载已有 pack
- **NTL-S5-010**：升级盘后评分口径（MFE/MAE）→ PostmortemResult.mfe/mae 有值
- **NTL-S5-011**：生成 ranking → postmortem 结果供 ranking 使用
- **NTL-S5-012**：差评触发 LLM 归因并写回记忆 → 需要 LLMValidator
