# NTL-S5-011 盘后生成 Ranking 设计

> **日期：** 2026-04-25
> **任务：** NTL-S5-011 | 盘后生成 ranking
> **状态：** 已批准

---

## 目标

在 `run_after_close` 末尾生成当日盘后 ranking，按 trader / 策略版本分组，计算组内排序。

---

## 核心概念

| 概念 | 说明 |
|------|------|
| `RankingEntry` | 单条 ranking 记录：trade_date / trader_id / strategy_version_id / symbol / return_pct / mfe / mae / composite_score / rank |
| `RankingService.add_entry()` | 接收 `PostmortemResult`，生成并持久化 ranking 条目（现有方法）|
| `RankingService.add_entry_from_metrics()` | 接收 mfe/mae/return_pct，生成并持久化 ranking 条目（NTL-S5-011 新增）|
| `RankingService.generate_ranking()` | 批量计算组内 rank，返回 nested/flat 视图（现有方法）|

---

## 数据流

```
run_after_close(as_of_date=T日)
│
├── 生成 EvidencePack（已有）
│   └→ 保存到 {output_dir}/evidence_packs/{pack_id}.json
│
├── 计算 mfe / mae / return_pct（NTL-S5-010 metrics_calculator）
│   └→ metrics = compute_mfe_mae_return(bars, entry_price, ...)
│
├── 写入 TraderMemory（已有）
│
├── 创建 postmortem_task（已有）
│
├── 【NTL-S5-011 新增】生成 RankingEntry
│   └→ RankingService.add_entry_from_metrics(
│          evidence_pack=pack,
│          mfe=mfe,
│          mae=mae,
│          return_pct=return_pct,
│       )
│   └→ Repo.upsert() → DB 持久化
│
└── 【NTL-S5-011 新增】生成 Ranking
    └→ RankingService.generate_ranking(trade_date=str(T日))
    └→ 计算组内 rank
    └→ 写入 {output_dir}/rankings/{trade_date}.json
```

**注意：** `postmortem_tasks` 异步执行，继续调用 `add_entry(postmortem_result, pack)`，两者互不阻塞。

---

## RankingService 改动

### 新增方法：add_entry_from_metrics

```python
async def add_entry_from_metrics(
    self,
    evidence_pack: EvidencePack,
    mfe: float,
    mae: float,
    return_pct: float,
) -> RankingEntry:
    """从 metrics 计算结果生成 ranking 条目（NTL-S5-011）。

    用于 run_after_close 场景：此时没有完整的 PostmortemResult
    （PostmortemService.generate() 需要异步 postmortem_task 执行后才存在），
    但 ranking 数据（mfe/mae/return_pct）在 EvidencePack 生成时就能算出来。

    attribution_source 固定为 "auto"，因为 run_after_close
    没有 LLM validator 参与归因。

    与 add_entry(postmortem, pack) 的区别：
    - add_entry：需要 PostmortemResult（由 PostmortemService.generate() 产生）
    - add_entry_from_metrics：直接接收 metrics 结果，不需要 PostmortemService

    Args:
        evidence_pack: 当前 idea 的 EvidencePack
        mfe: Maximum Favorable Excursion
        mae: Maximum Adverse Excursion
        return_pct: 收益率（%）

    Returns:
        新建的 RankingEntry
    """
```

### 新增方法：generate_ranking_and_save

```python
async def generate_ranking_and_save(
    self,
    trade_date: str,
    trader_id: str | None = None,
    strategy_version_id: str | None = None,
) -> dict:
    """生成 ranking 并持久化到文件（NTL-S5-011）。

    调用链路：run_after_close 末尾 -> add_entry_from_metrics() -> 本方法

    文件路径：{output_dir}/rankings/{trade_date}.json

    排序规则（来自 generate_ranking）：
      1. return_pct 降序
      2. return_pct 相同时按 (mfe - mae) 降序
      3. return_pct 为 None 的排在最后

    Args:
        trade_date: 交易日期（YYYY-MM-DD）
        trader_id: 可选，限定 trader
        strategy_version_id: 可选，限定策略版本

    Returns:
        nested view: {trader_id: {strategy_version_id: [RankingEntry...]}}
    """
```

---

## run_after_close 改动

在 `run_after_close` 末尾（所有 ideas 处理完成后、返回 EvaluationResult 之前）新增：

```python
# NTL-S5-011: 生成盘后 ranking
ranking_result = await self._generate_ranking(as_of_date)
self._save_ranking_result(ranking_result, as_of_date)
```

新增两个私有方法：
- `_generate_ranking(as_of_date)` — 调用 `RankingService.generate_ranking()`
- `_save_ranking_result(result, as_of_date)` — 写入 JSON 文件

---

## 文件持久化

**ranking 文件路径：**
```
{output_dir}/rankings/{trade_date}.json
```

**文件格式：**
```json
{
  "trade_date": "2026-04-25",
  "generated_at": "2026-04-25T16:00:00Z",
  "nested": {
    "trader_001": {
      "trader_001_2026-04-25_released": [
        {"entry_id": "...", "symbol": "AAPL", "return_pct": 5.2, "mfe": 8.1, "mae": 1.2, "rank": 1, ...},
        {"entry_id": "...", "symbol": "TSLA", "return_pct": -2.3, "mfe": 1.5, "mae": 4.7, "rank": 2, ...}
      ]
    }
  },
  "flat": [...]
}
```

---

## 扩展路径（Future）

| 方向 | 改动范围 |
|------|---------|
| ranking 推送通知 | 新增 web hook 或 message queue 通知 |
| ranking 历史对比 | 新增 `rankings/` 目录历史文件查询 |
| ranking 可视化 | 新增 `ranking_dashboard.py` 读取 ranking 文件生成图表 |

---

## 验收标准

1. `run_after_close` 执行后生成 `{output_dir}/rankings/{trade_date}.json`
2. ranking 文件包含 nested 和 flat 两种视图
3. ranking 数据从 `RankingService.add_entry_from_metrics()` 持久化到 DB
4. 可以按 trader_id / strategy_version_id 查询 ranking
5. 排序规则：return_pct 降序，相同按 (mfe-mae) 降序
