# Job 暂停 / 恢复 / 取消 / 错误重试设计

> 目标：为指定长任务补齐统一的 Job 控制能力，使 Web 端可以对运行中的任务执行暂停、恢复、取消和错误重试。
> 说明：这不是可选优化，而是用户明确提出的交付需求，以下范围内的任务必须实现。

## 1. 背景

当前系统已经具备统一 Job Center、Job Detail、进度展示、取消请求、失败重试次数和 worker 心跳等基础能力，但仍然缺少真正可恢复的执行语义。

现状有两个直接问题：

1. `cancel` 只是请求取消，依赖执行器在自然边界停下来。
2. `retry` 目前更接近“重新提交一个新 Job”，不是同一个 Job 基于 checkpoint 的恢复执行。

对以下 7 个 Job，用户要求必须补齐：

- `ohlcv-crawl`
- `kaipan-fetch`
- `kaipan-normalize`
- `snapshot-build`
- `backtest-run`
- `backtest-validate-rules`
- `rule-pool-backtest`

这些 Job 都属于长任务，单次执行成本高，失败后重新开始浪费资源，因此需要统一的控制面与恢复面。

## 2. 目标

### 2.1 必须实现的能力

对上述 7 个 Job，Web 端必须支持：

- 暂停 `pause`
- 恢复 `resume`
- 取消 `cancel`
- 错误重试 `retry`

### 2.2 必须保证的行为

- 暂停后，任务应在安全边界停下，并进入可恢复状态。
- 恢复后，任务应从上次 checkpoint 继续，而不是从头完全重跑。
- 取消后，任务应进入终态，不再继续执行。
- 错误重试后，优先从 checkpoint 恢复；若 checkpoint 不可用，则从头重跑。
- UI 必须提供触发入口，不只存在于 Job Detail 的隐藏接口中。

### 2.3 不在本次范围内

- `kaipan-run`
  - 它是调度器/生命周期控制，不是数据处理主体，不纳入本次 pause/resume 语义。
- `backtest-reproducibility-check`
  - 它是重复执行与 fingerprint 对比的验证动作，不纳入本次控制面覆盖范围。

## 3. 设计原则

### 3.1 协作式暂停，不做强杀

暂停与取消都不应通过强杀 worker 进程实现。

原因：

- 强杀会破坏写文件与数据库事务一致性。
- 强杀无法保证 checkpoint 落盘完整。
- 强杀会让后续恢复逻辑变得不可预测。

推荐方式是协作式控制：

- worker 在执行循环中的安全边界检查控制指令。
- 安全边界到达后再暂停、取消或写 checkpoint。

### 3.2 checkpoint 必须持久化

仅有 `progress` 不足以恢复任务。

`progress` 只负责 UI 展示。
真正决定恢复位置的是 `checkpoint`，必须持久化。

### 3.3 retry 和 resume 语义分离

- `resume`：针对 `paused` 状态，继续当前 Job。
- `retry`：针对 `failed` 状态，重新进入可执行状态。

二者都可以继续利用 checkpoint，但业务语义不同。

## 4. 推荐架构

### 4.1 状态机扩展

建议在 Job 状态中新增：

- `paused`

现有终态保持不变：

- `success`
- `failed`
- `cancelled`

建议状态流转：

- `pending` -> `running`
- `running` -> `paused`
- `paused` -> `pending` 或 `running`
- `running` -> `failed`
- `running` -> `cancelled`
- `failed` -> `pending`
- `paused` -> `cancelled`

### 4.2 Runtime State 载体

建议新增一层持久化运行态，用于保存：

- 当前执行位置
- checkpoint 版本
- 上次安全边界
- 临时恢复元信息
- 是否请求暂停 / 取消

推荐实现顺序：

1. 先用 `Job` 记录上的 JSON 字段承载 runtime state。
2. 如果后续需要更强的查询/审计能力，再独立拆出 runtime state 表。

第一版建议直接挂在 Job 记录上，降低落地复杂度。

### 4.3 统一 Job Control Context

`JobRunner` 在执行每个 Job 时注入控制上下文，提供：

- `should_pause()`
- `should_cancel()`
- `save_checkpoint(payload)`
- `load_checkpoint()`
- `mark_paused()`
- `mark_resumed()`

执行器不直接读写 UI 状态，而是通过这个上下文与 JobService 交互。

## 5. Job 级实现策略

### 5.1 `ohlcv-crawl`

特点：

- 按 symbol 串行处理
- 数据落库是 upsert
- 天然适合按 symbol 作为 checkpoint 粒度

建议 checkpoint：

- 当前 symbol index
- 当前 symbol 名称
- 当前日期区间
- 最近一次成功 upsert 的日期

暂停/恢复：

- 每处理完一个 symbol 或一个 symbol 的日期段后检查控制指令
- 恢复时跳过已完成的 symbol，继续下一个

重试：

- 如果 checkpoint 存在，优先从最后一个未完成 symbol 继续
- 如果 checkpoint 丢失，则从头重新抓取

### 5.2 `kaipan-fetch`

特点：

- 按 `trade_date -> slot -> fetcher` 分层
- 内部有明确的日期范围与进度事件

建议 checkpoint：

- 当前 trade_date
- 当前 slot
- 当前 fetcher index
- 当前 fetcher 名称

暂停/恢复：

- 每完成一个 fetcher 或一个 slot 后检查控制指令
- 恢复时继续未完成的 trade_date / slot / fetcher

### 5.3 `kaipan-normalize`

特点：

- 按 `trade_date -> slot -> dataset` 进行归一化
- 与 `kaipan-fetch` 具有相同的日期切片语义

建议 checkpoint：

- 当前 trade_date
- 当前 slot
- 当前 dataset index
- 当前 dataset 名称

暂停/恢复：

- 每完成一个 dataset 或一个 slot 后检查控制指令
- 恢复时从最后一个未完成 dataset 继续

### 5.4 `snapshot-build`

特点：

- 按 `trade_date x snapshot_type` 组合构建
- 每个组合都可以作为一个独立安全边界

建议 checkpoint：

- 当前 trade_date
- 当前 snapshot_type
- 当前 section / builder 位置

暂停/恢复：

- 每完成一个 snapshot_type 或一个 date 批次后检查控制指令
- 恢复时跳过已完成组合

### 5.5 `backtest-run`

特点：

- 按交易日循环
- 可能有内部状态、账户状态、持仓状态和评分状态
- 不是简单的“循环到下一天”就能恢复

建议 checkpoint：

- 当前 trade_date
- 当前策略/账户状态摘要
- 当前回测引擎内部 cursor
- 当前已输出结果片段

暂停/恢复：

- 必须在交易日边界写 checkpoint
- 如引擎支持更细粒度状态快照，可在单日内进一步细分

重试：

- 优先恢复引擎快照
- 若引擎快照不兼容，则回退到最近一个日级 checkpoint

### 5.6 `backtest-validate-rules`

特点：

- 同样按交易日循环
- 相比完整回测，状态依赖更少

建议 checkpoint：

- 当前 trade_date
- 当前规则集合版本
- 当前验证 cursor

暂停/恢复：

- 每个交易日结束后检查控制指令

### 5.7 `rule-pool-backtest`

特点：

- 当前定义里是高风险任务
- 目前 `can_retry=False`
- 用户明确要求必须支持错误重试，因此需要改 Job Definition

建议 checkpoint：

- 当前 rule index
- 当前 trade_date
- 当前市场状态版本
- 当前引擎状态摘要

暂停/恢复：

- 每完成一个 rule 或一个 trade_date 批次后检查控制指令
- 恢复时跳过已完成的 rule/date 组合

## 6. Job Definition 与权限改造

需要扩展 Job Definition 能力字段，建议至少新增：

- `can_pause`
- `can_resume`
- `can_cancel`
- `can_retry`

现有 `can_retry` 只能表达是否允许重试，不足以描述 pause/resume。

对这 7 个 Job 的建议：

| Job | can_pause | can_resume | can_cancel | can_retry |
|---|---|---|---|---|
| `ohlcv-crawl` | true | true | true | true |
| `kaipan-fetch` | true | true | true | true |
| `kaipan-normalize` | true | true | true | true |
| `snapshot-build` | true | true | true | true |
| `backtest-run` | true | true | true | true |
| `backtest-validate-rules` | true | true | true | true |
| `rule-pool-backtest` | true | true | true | true |

## 7. API 设计

### 7.1 建议新增接口

统一以 Job 维度提供控制 API：

- `POST /api/ui/v1/jobs/{jobId}/pause`
- `POST /api/ui/v1/jobs/{jobId}/resume`
- `POST /api/ui/v1/jobs/{jobId}/cancel`
- `POST /api/ui/v1/jobs/{jobId}/retry`

### 7.2 返回约定

每个控制接口都应返回：

- job 当前状态
- runtime_state 摘要
- checkpoint 摘要
- 是否已真正生效

### 7.3 约束

- pause/resume/cancel/retry 需要走权限校验
- 高风险 Job 仍需保留确认机制
- API 不返回服务器绝对路径

## 8. UI 设计

### 8.1 必须新增按钮入口

按钮必须存在于：

- Job List
- Job Detail

不建议只放在详情页，否则用户发现成本过高。

### 8.2 按状态显示按钮

建议按钮规则：

- `pending`
  - `暂停`
  - `取消`
- `running`
  - `暂停`
  - `取消`
- `paused`
  - `恢复`
  - `取消`
- `failed`
  - `重试`
- `success`
  - 不显示 pause/resume/retry
  - 仅保留“重新运行”作为新 Job 入口，如产品仍需保留
- `cancelled`
  - 不显示恢复
  - 可保留“重新运行”作为新 Job 入口

### 8.3 UI 反馈要求

点击操作后必须有：

- loading
- 成功反馈
- 失败反馈
- 状态刷新

### 8.4 Job List 额外要求

Job List 需要补充：

- 当前状态 badge 包含 `paused`
- 操作列按钮
- 与 Job type 能力联动

## 9. 错误重试策略

### 9.1 retry 的默认策略

当用户点击重试：

- 若 Job 有有效 checkpoint，优先继续 checkpoint
- 若 checkpoint 不可用，回退为从头执行

### 9.2 错误类型分类

建议对以下错误设置可重试策略：

- provider unavailable
- network error
- timeout
- transient db error
- stale recovery

建议对以下错误默认不自动重试：

- validation error
- missing required param
- permission denied
- config missing
- data invalid

### 9.3 最大重试次数

重试次数建议继续复用现有 Job 字段：

- `retry_count`
- `max_retries`
- `retry_backoff_seconds`

但需要明确：

- `retry_count` 统计失败重试，不统计 pause/resume
- `pause/resume` 不应增加 `retry_count`

## 10. 监控与审计

必须记录：

- 谁发起了 pause/resume/cancel/retry
- 什么时间发起
- 发起时 Job 状态是什么
- checkpoint 在哪里
- 恢复后从哪里继续

审计事件建议新增：

- `pause`
- `resume`
- `retry`

`cancel` 继续沿用现有审计事件。

## 11. 风险与边界

### 11.1 `backtest-run` 的技术风险最高

原因：

- 回测引擎可能包含隐式状态
- 仅保存 trade_date 不一定足够恢复
- 可能需要引擎内部快照支持

### 11.2 不要把“暂停”做成假按钮

如果只是改 UI 状态，不落 checkpoint，不改变执行器行为，用户会误以为任务真的恢复了。

### 11.3 不要混淆“新 Job 重跑”和“当前 Job 恢复”

这两者必须在 UI 和 API 中明确区分。

## 12. 推荐实施顺序

### Phase 1：Job Control 基础

- 增加 `paused` 状态
- 增加 pause/resume/retry API
- 增加 runtime_state / checkpoint 持久化
- 增加审计事件
- Job List / Job Detail 增加按钮

### Phase 2：最容易的 4 个 Job

- `ohlcv-crawl`
- `kaipan-fetch`
- `kaipan-normalize`
- `snapshot-build`

### Phase 3：回测与规则池

- `backtest-run`
- `backtest-validate-rules`
- `rule-pool-backtest`

### Phase 4：收口与回归

- 文档收口
- TaskList 更新
- 回归测试
- Job Detail / Job List 验收

## 13. 验收标准

以下条件全部满足时，才能认为本需求完成：

1. 上述 7 个 Job 都可以在 Web 中触发 pause / resume / cancel / retry。
2. pause 后任务会停在安全边界，并保存 checkpoint。
3. resume 后任务从 checkpoint 继续，不从头开始。
4. cancel 后任务进入终态，不再继续执行。
5. retry 可从 checkpoint 继续，缺少 checkpoint 时可从头重跑。
6. Job List 与 Job Detail 都有可用的按钮入口。
7. Job 状态、审计、进度和错误提示都能正确反映真实状态。
8. 文档、TaskList 与 API contract 保持一致。

## 14. 结论

这不是单纯的 UI 改动，也不是单纯的 job runner 改动，而是一个完整的“Job 控制面 + checkpoint 恢复面”能力补齐。

如果只做按钮，不做 checkpoint，不做 worker 协作式暂停，那么 pause/resume 只是表面能力，无法满足用户要求。

因此，本设计的推荐方案是：

- 先补 Job 状态机与 checkpoint 持久化
- 再补执行器协作式暂停/恢复
- 再补 Job List / Job Detail 的按钮入口
- 最后按 job type 分批落地到这 7 个必须覆盖的任务上

## 15. 可执行 TaskList

> 说明：
> - 本 TaskList 只承接本设计文档，不回写之前的两份 TaskList。
> - 所有任务完成后，必须同时满足第 13 节的验收标准。
> - 7 个指定 Job 都是用户明确要求覆盖的交付范围，不能拆成“后续优化”。

### [x] JC-001 定义 Job 控制面 contract

任务目标：

- 给 Job 增加统一控制能力的 contract，明确 pause / resume / cancel / retry 的状态流转。

允许修改：

- `src/models/job.py`
- `src/services/job_registry.py`
- `src/services/job_service.py`
- `src/services/job_runner.py`
- `src/services/base.py`
- `web/src/types/jobs.ts`

实现要求：

- 新增 `paused` 状态。
- 明确 `pause / resume / retry` 与现有 `cancel`、`failed`、`pending`、`running` 的关系。
- Job Definition 增加 `can_pause / can_resume / can_cancel / can_retry` 能力字段。
- `retry_count` 仅统计失败重试，不统计 pause/resume。

验收标准：

- Job contract 能表达暂停、恢复、取消、重试四种动作。
- 前后端类型定义一致。
- 现有 Job 查询与详情接口不会因为新增字段而破坏兼容性。

---

### [x] JC-002 为 Job 增加持久化 runtime_state

任务目标：

- 使用 `jobs` 表上的 JSON 字段持久化 checkpoint / runtime state。

允许修改：

- `src/models/job.py`
- `src/services/job_service.py`
- `src/services/job_runner.py`
- `api/routers/ui/jobs.py`
- `web/src/types/jobs.ts`
- 相关 migration / test

实现要求：

- 新增 `runtime_state` 字段，作为 checkpoint 的主载体。
- `progress` 只用于 UI 展示，不承担恢复语义。
- `runtime_state` 至少包含：
  - `schema_version`
  - `checkpoint_type`
  - `cursor`
  - `stage`
  - `sub_cursor`
  - `paused_at`
  - `resume_from`
  - `last_safe_point`
  - `updated_at`
- 读写 `runtime_state` 必须通过 JobService 统一封装，不允许页面直接推断。

验收标准：

- 任意 Job 的 checkpoint 都能随 Job 一起持久化。
- Job 重启后仍能从 `runtime_state` 恢复继续执行。
- 详情页可以展示 checkpoint 摘要，但不能暴露敏感路径。

---

### [x] JC-003 实现 Job 控制 API

任务目标：

- 给 Job Center 提供 pause / resume / cancel / retry 的统一控制入口。

允许修改：

- `api/routers/ui/jobs.py`
- `src/services/job_service.py`
- `src/services/job_runner.py`
- `web/src/lib/api/jobs.ts`
- `web/src/types/jobs.ts`
- API 测试

实现要求：

- 新增控制接口：
  - `POST /api/ui/v1/jobs/{jobId}/pause`
  - `POST /api/ui/v1/jobs/{jobId}/resume`
  - `POST /api/ui/v1/jobs/{jobId}/cancel`
  - `POST /api/ui/v1/jobs/{jobId}/retry`
- 所有控制动作必须记录审计。
- pause/resume/cancel/retry 都必须返回当前 Job 的最新状态和 checkpoint 摘要。
- `cancel` 保持终态语义。
- `retry` 优先从 checkpoint 恢复，缺少 checkpoint 时允许从头执行。

验收标准：

- API 层可以真实驱动 Job 状态变化。
- 权限校验生效。
- 失败返回有清晰错误信息。

---

### [x] JC-004 改造 JobRunner 的协作式控制上下文

任务目标：

- 让 worker 在执行过程中识别 pause / resume / cancel / retry 的控制指令。

允许修改：

- `src/services/job_runner.py`
- `src/services/job_service.py`
- `src/pipeline/tasks/*`
- `src/services/backtest_service.py`
- `src/services/market_service.py`
- `src/services/kaipan_service.py`
- `src/market_data/ohlcv_service.py`

实现要求：

- 在安全边界检查控制指令，不做强杀。
- 支持保存 checkpoint 的统一上下文。
- 支持恢复时读取 checkpoint 并继续执行。
- `progress` 继续负责 UI 的实时展示。
- 取消请求要能在下一次安全边界生效。

验收标准：

- 运行中的 Job 可以被暂停并在恢复后继续。
- 取消不会破坏后续 Job 状态一致性。
- 任务执行器不依赖进程内存保存恢复点。

---

### [x] JC-005 为 `ohlcv-crawl` 接入 checkpoint 与恢复

任务目标：

- 让 `ohlcv-crawl` 支持 pause / resume / cancel / retry，并且能从上次 symbol 进度继续。

允许修改：

- `src/market_data/ohlcv_service.py`
- `src/services/market_service.py`
- `src/services/job_runner.py`
- `src/services/job_registry.py`
- `tests/unit/market_data/*`

实现要求：

- checkpoint 粒度按 `symbol` 和日期区间。
- 恢复时跳过已完成 symbol，继续未完成 symbol。
- `retry` 优先从最后一个未完成 symbol 恢复。
- `cancel` 进入终态时不会重复污染数据库。

验收标准：

- 中断后再次执行可跳过已完成 symbol。
- UI 进度可以正确显示当前 symbol 和剩余量。
- 不会因为重复运行导致数据重复插入。

---

### [x] JC-006 为 `kaipan-fetch` 与 `kaipan-normalize` 接入 checkpoint 与恢复

任务目标：

- 让 Kaipan 抓取与归一化支持 pause / resume / cancel / retry。

允许修改：

- `src/services/kaipan_service.py`
- `src/services/job_runner.py`
- `src/services/job_registry.py`
- `src/providers/kaipan_provider.py`
- `src/providers/kaipan_normalizer.py`
- `tests/unit/services/*`

实现要求：

- `kaipan-fetch` checkpoint 粒度按 `trade_date / slot / fetcher`。
- `kaipan-normalize` checkpoint 粒度按 `trade_date / slot / dataset`。
- 暂停后恢复，应从最后一个已完成组合继续。
- 重试应优先使用 checkpoint。

验收标准：

- 日期范围任务可以被中断并续跑。
- 当前 trade_date、slot、fetcher/dataset 的进度能准确回显。
- 断点恢复后不会重复写已完成的组合。

---

### [x] JC-007 为 `snapshot-build` 接入 checkpoint 与恢复

任务目标：

- 让 `snapshot-build` 支持 pause / resume / cancel / retry，并按日期 x 快照类型恢复。

允许修改：

- `src/services/snapshot_service.py`
- `src/services/job_runner.py`
- `src/services/job_registry.py`
- `tests/unit/services/*`

实现要求：

- checkpoint 粒度按 `trade_date x snapshot_type`。
- 恢复时跳过已完成组合。
- 进度必须能反映当前日期与快照类型。

验收标准：

- snapshot 构建可在中途暂停并恢复。
- 已完成的日期/类型组合不会重复构建。
- 失败重试可继续未完成组合。

---

### [x] JC-008 为 `backtest-run` 接入 checkpoint 与恢复

任务目标：

- 让回测主流程支持 pause / resume / cancel / retry。

允许修改：

- `src/services/backtest_service.py`
- `src/services/job_runner.py`
- `src/backtest/*`
- `src/services/job_registry.py`
- `tests/unit/services/*`

实现要求：

- checkpoint 至少要记录交易日 cursor。
- 如果引擎支持更细粒度快照，应优先使用引擎快照。
- 恢复后必须继续上次回测，而不是重新开始。
- fingerprint、报告和结果输出必须保持一致性。

验收标准：

- `backtest-run` 可以暂停、恢复、取消、重试。
- 恢复后回测结果可继续产出，不丢失上下文。
- UI 能看到回测当前日期级进度。

---

### [x] JC-009 为 `backtest-validate-rules` 接入 checkpoint 与恢复

任务目标：

- 让规则验真支持 pause / resume / cancel / retry。

允许修改：

- `src/services/backtest_service.py`
- `src/services/job_runner.py`
- `src/services/job_registry.py`
- `tests/unit/services/*`

实现要求：

- checkpoint 至少按交易日记录 cursor。
- 恢复后继续剩余日期的规则验真。
- 错误重试优先恢复 checkpoint。

验收标准：

- 验真任务可以中断后继续。
- 验真报告最终结果保持完整。

---

### [x] JC-010 为 `rule-pool-backtest` 接入 checkpoint 与恢复，并补齐 retry 能力

任务目标：

- 让规则池回测支持 pause / resume / cancel / retry。
- 补齐当前 `can_retry=False` 的定义，使其满足用户要求。

允许修改：

- `src/services/backtest_service.py`
- `src/services/job_runner.py`
- `src/services/job_registry.py`
- `tests/unit/services/*`

实现要求：

- checkpoint 至少记录 rule cursor、trade_date cursor、市场状态版本。
- 恢复后继续未完成的 rule/date 组合。
- `can_retry` 必须改为 `true`。

验收标准：

- 规则池回测可以暂停、恢复、取消、重试。
- 失败后可根据 checkpoint 继续，而不是只能从头跑。

---

### [x] JC-011 在 Job List 页面增加控制按钮

任务目标：

- 让任务列表页直接支持 pause / resume / cancel / retry 的触发入口。

允许修改：

- `web/src/pages/jobs/JobListPage.tsx`
- `web/src/components/jobs/JobTable.tsx`
- `web/src/lib/api/jobs.ts`
- `web/src/types/jobs.ts`
- 前端测试

实现要求：

- 列表页展示 `paused` 状态。
- 对 `pending/running/paused/failed` 显示合适的操作按钮。
- 按钮行为与 Job 能力字段一致。
- 操作后刷新列表状态。

验收标准：

- 用户不进入详情页也能触发控制动作。
- 按钮状态和权限控制正确。

---

### [x] JC-012 在 Job Detail 页面增加控制按钮与 checkpoint 展示

任务目标：

- 让 Job Detail 页面完整支持控制动作、状态展示和 checkpoint 摘要展示。

允许修改：

- `web/src/pages/jobs/JobDetailPage.tsx`
- `web/src/lib/api/jobs.ts`
- `web/src/types/jobs.ts`
- `web/src/components/jobs/*`
- 前端测试

实现要求：

- 增加 pause / resume / cancel / retry 按钮。
- 显示 checkpoint 摘要和 runtime state 摘要。
- `paused` 状态要有明确 badge 和提示。
- 不展示服务器绝对路径和 secret 原文。

验收标准：

- 详情页可以完整完成任务控制闭环。
- 状态、进度、审计、错误和 checkpoint 都能看到。

---

### [x] JC-013 回归测试与文档收口

任务目标：

- 确保本需求实现完整、可验收、无明显回归。

允许修改：

- `tests/**`
- `docs/superpowers/specs/2026-05-26-job-control-pause-resume-cancel-retry-design.md`
- 必要的使用说明文档

实现要求：

- 补齐 API、runner、job-specific、UI 的回归测试。
- 验证 7 个必选 Job 的控制动作都可触发。
- 验证 pause / resume / cancel / retry 的状态流转正确。
- 验证 checkpoint 恢复不是“假恢复”。

验收标准：

- 所有相关测试通过。
- 文档与实际实现一致。
- 7 个指定 Job 都达到第 13 节验收标准。
