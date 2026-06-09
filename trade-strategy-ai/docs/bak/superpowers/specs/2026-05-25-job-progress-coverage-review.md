# Job 进度展示覆盖评审

> 目的：确认哪些 `job` 能做真正进度展示，哪些只能做阶段态，并收口 Kaipan 的 UI 和任务语义，保证用户能看到“处理到哪一天、哪一步、还剩多少”。

## 结论

- `kaipan-fetch / kaipan-normalize` 这一版按**交易日期范围**运行和展示进度。
- `kaipan-run` 只保留“当天一键执行”语义，不参与历史范围回填。
- `kaipan-fetch` 不是纯抓取，它会抓 raw 并顺带标准化到 snapshot。
- UI 必须显示最近成功日期、slot、时间，并支持确认重跑，避免用户重复误触。
- 进度必须由后端显式写入，并以数据库契约为主，前端只展示，不推断。

## 可以实现的进度

| Job | 进度方式 | 说明 |
|---|---|---|
| `kaipan-fetch` | 交易日期范围进度 | 外层按 `trade_date`，内层按 `slot -> fetcher` |
| `kaipan-normalize` | 交易日期范围进度 | 外层按 `trade_date`，内层按 `slot -> dataset` |
| `ohlcv-crawl` | 精确进度 | 按 symbol 逐个抓取 |
| `snapshot-build` | 精确进度 | 按日期 x 快照类型组合计算 |
| `pipeline-run` | 混合进度 | 步骤级 + `process` 文章级 |
| `backtest-run` | 日期级进度 | 按交易日循环 |
| `rule-pool-backtest` | 日期级进度 | 按交易日循环 |
| 其他长流程 job | 阶段进度 | 先显示当前阶段，再逐步补细粒度 |

## 先不做

- `kaipan-run` 的历史范围回填
- `kaipan-fetch / normalize` 的单日专用视图
- `market-state-build / candidate-review / rule-review` 的剩余数量
- 秒级实时刷新
- websocket / event stream 作为第一版前提

## 进度口径

`kaipan-fetch / kaipan-normalize` 的进度口径统一为：

- 外层：当前交易日、已完成交易日数、总交易日数、剩余交易日数
- 内层：当前 slot、当前 fetcher / dataset、当前完成数、总数
- 状态：最近成功日期、最近成功 slot、最近成功时间

这样用户能同时看到：

- 现在处理到哪一天
- 这一天内部处理到哪一步
- 是否已经重复执行过

## 推荐实现顺序

1. 先把 `kaipan-fetch / kaipan-normalize` 的 UI 改成交易日期范围入口。
2. 再补 `kaipan-fetch / kaipan-normalize` 的交易日期范围进度。
3. 再补最近成功日期 / slot / 时间和确认重跑提示。
4. 再补 `ohlcv-crawl` 和 `snapshot-build` 的精确进度。
5. 再补 `pipeline-run`、`backtest-run`、`rule-pool-backtest`。

## 与回测的关系

- Kaipan 范围抓取和标准化负责准备交易日期范围内的数据。
- `market_universe` 快照负责把可回测的数据固定下来。
- 回测只消费已经生成好的快照和 DB 数据，不会现场去抓 Kaipan。

## TaskList

> 下面按两阶段收口：先交付 Kaipan 日期范围进度，再补其他长耗时 job 的进度。任务数量尽量少，但必须覆盖用户真正能感知到的进度能力。


### [x] NW-KAIPAN-PROGRESS-001 后端范围进度契约

目标：

- `kaipan-fetch / kaipan-normalize` 支持 `start_date / end_date`
- 按交易日展开执行
- 后端返回范围进度对象
- 进度以数据库契约落地，优先写入 `jobs.progress` 或等价的结构化进度字段，不作为临时文件侧车对外暴露
- `start_date / end_date` 仍然可选，默认当天，如果日期一样则只跑选择的这一天

验收标准：

- 能返回 `current / total / percent / remaining`
- 能返回当前交易日、当前 slot、当前 fetcher / dataset
- 能返回最近成功日期 / slot / 时间
- `kaipan-run` 仍然只跑当天
- 其他 job 的进度字段本次一起改造，但数据结构必须兼容后续扩展

### [x] NW-KAIPAN-PROGRESS-002 UI 范围进度与防重复提示

目标：

- Kaipan 页面支持日期范围选择
- 显示范围进度条和当前处理日期
- 显示最近成功日期、slot、时间
- 支持确认重跑，不直接阻断用户

验收标准：

- 用户能明确看到范围已完成多少、还剩多少
- 用户能判断当前范围是否已处理
- 用户重复点击时会看到明确提示或确认框

### [x] NW-KAIPAN-PROGRESS-003 验证与文档收口

目标：

- 补齐必要测试
- 同步更新本文档和相关 TaskList

验收标准：

- 进度展示与 UI contract 对齐
- 文档描述与实现一致
- 无未收口的单日 / 范围混用描述


### [x] NW-JOB-PROGRESS-004 精确进度作业

目标：

- 为 `ohlcv-crawl` 和 `snapshot-build` 接入精确进度

验收标准：

- `ohlcv-crawl` 能按 symbol 展示当前进度和剩余数量
- `snapshot-build` 能按日期 x 快照类型展示当前进度和剩余数量
- Job Detail 能展示这两类任务的实时进度条

### [x] NW-JOB-PROGRESS-005 流程与回测进度

目标：

- 为 `pipeline-run`、`backtest-run`、`rule-pool-backtest` 接入可感知进度

验收标准：

- `pipeline-run` 能展示步骤级进度，`process` 阶段能展示文章级进度
- `backtest-run` 和 `rule-pool-backtest` 能展示交易日级进度
- 用户能在 Job Detail 看见当前阶段和剩余日期/条目，而不是只有 running 状态
