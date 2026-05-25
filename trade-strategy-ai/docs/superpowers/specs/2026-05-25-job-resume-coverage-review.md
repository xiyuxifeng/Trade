# Job 断点续跑覆盖评审

> 目的：回答“如果只完成断点续跑，下一个 job 是否会跳过已完成数据”。
> 范围：以 `src/services/job_registry.py` 中定义的所有 `job_type` 为准，逐个说明当前是否支持断点续跑、是否会跳过已完成部分、以及重新开始的资源代价。

## 结论

- 当前**没有**一套通用的 job 级 checkpoint / resume 机制。
- 真正接近“继续处理未完成数据”的，只有 `pipeline-run` 这一条链路，且也是**局部跳过**，不是通用断点恢复。
- 大多数 job 现在都是**重新开始**，只是部分任务具有幂等写入、upsert、watermark 或内部去重能力，因此“重跑不会污染结果”，但**不会自动接着上一次的中断位置继续**。
- 如果只做“进度展示”，不会改变 job 的重跑语义；必须把 checkpoint 也持久化并在下一次执行时读取，才会真正跳过已完成部分。

## 术语

- **断点续跑**：任务中断后，下一次从上次已完成的位置继续，不重复处理已完成数据。
- **幂等重跑**：任务可以再次执行，结果不会重复污染，但仍然会重新做大部分工作。
- **局部跳过**：同一次执行中，发现已有产物或已有处理痕迹后跳过一部分数据或步骤，但不等于通用 resume。

## 全量清单

### 系统与基础设施类

| Job | 当前语义 | 能跳过已完成部分吗 | 断点续跑 | 重新开始代价 | 备注 |
|---|---|---|---|---|---|
| `db-migrate` | 数据库迁移 | 否 | 否 | 高 | 一般不建议重复执行，属于一次性操作 |
| `init-project` | 初始化项目 | 否 | 否 | 高 | 组合迁移 + 样例导入，适合从头执行 |
| `seed-data` | 导入样例数据 | 否 | 否 | 中 | 可重复导入，但没有 resume 语义 |
| `backup-data` | 备份数据 | 否 | 否 | 中 | 备份本身是一次完整快照操作 |
| `restore-data` | 恢复数据 | 否 | 否 | 高 | 恢复是一次性恢复流程，不做断点续跑 |

### 文章与 pipeline 类

| Job | 当前语义 | 能跳过已完成部分吗 | 断点续跑 | 重新开始代价 | 备注 |
|---|---|---|---|---|---|
| `crawl` | 抓取文章 | 否 | 否 | 高 | 现阶段更像整次抓取重跑 |
| `import-trade-logs` | 导入交易记录 | 否 | 否 | 中 | 取决于输入文件，通常重新解析 |
| `pipeline-run` | 完整 Pipeline | 是，局部 | 部分支持 | 中到高 | `from_step`、`clean` 复用、`process` 失败重试、`export` 去重/watermark |
| `pipeline-step` | Pipeline 单步 | 仅单步内部 | 否 | 中 | 只跑某个步骤，不是通用 resume |
| `migrate-crawl-state` | 迁移爬虫状态 | 否 | 否 | 中 | 迁移型任务，通常整次跑完 |
| `clusters-build` | 构建画像聚类 | 否 | 否 | 中 | 计算型任务，暂无 checkpoint |
| `e2e-regression` | 端到端回归 | 否 | 否 | 中到高 | 回归任务应从头执行 |

### 运行与调度类

| Job | 当前语义 | 能跳过已完成部分吗 | 断点续跑 | 重新开始代价 | 备注 |
|---|---|---|---|---|---|
| `run-pre-market` | 盘前执行 | 否 | 否 | 中 | 一次性日常流程 |
| `run-after-close` | 盘后执行 | 否 | 否 | 中 | 一次性日常流程 |

### Persona / Market / Snapshot / Strategy 类

| Job | 当前语义 | 能跳过已完成部分吗 | 断点续跑 | 重新开始代价 | 备注 |
|---|---|---|---|---|---|
| `persona-init-sample` | 生成示例画像 | 否 | 否 | 低到中 | 生成样例文件，可直接重跑 |
| `market-state-build` | 构建市场状态 | 否 | 否 | 中 | 可重复生成输出文件，但无 resume |
| `snapshot-build` | 构建快照 | 否 | 否 | 中到高 | 按日期 x 类型重建，暂无 checkpoint |
| `strategy-build` | 构建策略版本 | 否 | 否 | 中 | 通常每次重新生成一个版本或覆盖输出 |

### 市场数据类

| Job | 当前语义 | 能跳过已完成部分吗 | 断点续跑 | 重新开始代价 | 备注 |
|---|---|---|---|---|---|
| `ohlcv-crawl` | 抓取 OHLCV | 部分（数据库幂等） | 否 | 高 | 每次会重新抓取，但落库是 upsert，不会重复污染 |
| `kaipan-fetch` | Kaipan 抓取 + 标准化 | 否 | 否 | 高 | 现阶段会按日期范围整段重跑 |
| `kaipan-normalize` | Kaipan 仅标准化 | 否 | 否 | 中到高 | 没有 checkpoint，通常重跑整个范围 |
| `kaipan-run` | Kaipan 调度器 | 不适用 | 否 | 低 | 主要是调度生命周期，不是数据处理任务 |

### 回测类

| Job | 当前语义 | 能跳过已完成部分吗 | 断点续跑 | 重新开始代价 | 备注 |
|---|---|---|---|---|---|
| `backtest-run` | 执行回测 | 否（仅记录 skipped 结果） | 否 | 高 | 按交易日整段重跑；缺数据会输出 skipped，不是 resume |
| `backtest-validate-rules` | 规则验真 | 否 | 否 | 中到高 | 整段验真重跑 |
| `backtest-reproducibility-check` | 回测可复现性检查 | 否 | 否 | 高 | 目标就是重复运行并比对结果 |
| `rule-pool-backtest` | 规则池回测 | 否（仅记录 skipped 结果） | 否 | 高 | 按交易日整段重跑 |

### 优化与审核类

| Job | 当前语义 | 能跳过已完成部分吗 | 断点续跑 | 重新开始代价 | 备注 |
|---|---|---|---|---|---|
| `optimize-create-candidate` | 生成候选版本 | 否 | 否 | 中 | 通常生成新的候选版本，不是 resume |
| `candidate-review` | 候选版本审核 | 否 | 否 | 低到中 | 审核动作本身很轻量，重复提交仍会走完整流程 |
| `rule-review` | 规则审核 | 否 | 否 | 低到中 | 目前不是可恢复任务 |

## 哪些任务最接近“继续”

1. `pipeline-run`
   - 这是当前最接近“继续处理未完成数据”的 job。
   - 已有 `from_step`、`retry_failed`、`clean` 复用、`export` 去重/watermark 等局部跳过能力。
   - 但这仍然不是通用 checkpoint resume。

2. `ohlcv-crawl`
   - 有数据库 upsert，因此重跑不会重复污染结果。
   - 但它不会自动识别“上次已经抓到哪一天/哪一个 symbol”并只续跑缺失部分。

3. `backtest-run` / `rule-pool-backtest`
   - 会在内部产生 `skipped` 记录，适合把缺失数据显式暴露出来。
   - 但每次启动仍然是整段日期区间重跑。

## 重新开始是否浪费资源

- **高浪费**
  - `kaipan-fetch`
  - `kaipan-normalize`
  - `ohlcv-crawl`
  - `snapshot-build`
  - `backtest-run`
  - `rule-pool-backtest`
- **中等浪费**
  - `pipeline-run`
  - `market-state-build`
  - `strategy-build`
- **低浪费**
  - `candidate-review`
  - `rule-review`
  - `persona-init-sample`

结论是：

- 对抓取类任务，重跑的主要浪费在网络请求和外部 API 限流。
- 对计算类任务，重跑的主要浪费在 CPU 和时间。
- 但当前系统更偏向幂等重跑，而不是复杂的断点恢复。

## 如果要真正支持“下一个 job 自动跳过已完成数据”

必须同时满足两点：

1. **保存 checkpoint**
   - 例如：
     - `kaipan-fetch`: 已完成到哪个 `trade_date / slot / fetcher`
     - `pipeline-run`: 已完成到哪个 `step / article_id`
     - `backtest-run`: 已完成到哪一天
     - `rule-pool-backtest`: 已完成到哪一天、哪条规则

2. **下一次启动时读取 checkpoint**
   - 新 job 不是只读 `progress`
   - 而是把 checkpoint 真正变成执行输入

如果这两步没同时完成，那么“继续”就只是显示层面的继续，不会真的跳过已完成数据。

## 结论

- 目前**没有**通用断点续跑。
- `pipeline-run` 是最接近局部继续的任务，但也只是一部分步骤与数据可跳过。
- 其他 job 大多数都是**重新开始**，只是幂等写入让它们不会轻易污染结果。
- 如果后续要做“暂停 / 继续”，先做 checkpoint/resume，再做状态机和 UI，是最合理的路线。
