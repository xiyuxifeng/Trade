# 盘前 / 盘后从工作流迁移到策略的设计文档（更新版）

## 1. 背景与目标

当前 sidebar 中的「工作流」页面承载了多个业务流程，用户反馈内容过于复杂。最终目标是移除整个「工作流」入口，并将其中的子功能迁移到更符合业务语义的位置。

本次迁移只聚焦「工作流」中盘前 / 盘后相关功能：

- 盘前准备迁移到策略模块下的「盘前准备」。
- 盘后复盘迁移到策略模块下的「盘后复盘」。
- Job 状态、失败重试、日志、产物仍归「任务」中心承载。
- Web 不再暴露或提交 `config_path`，统一使用 Profile。
- `benchmark_symbol` 在 Web 中做成可选，未选择时由后端从 Profile 默认配置解析。

重要结论：

> `market-state-build` 不迁移到策略 Web 页面。它归类为旧 Persona / MarketState 兼容任务，当前不作为盘前准备的必要步骤。盘前主流程只承接 `snapshot-build` 与 `run-pre-market`。

---

## 2. 当前代码现状

### 2.1 工作流页面现状

当前 `/workflows` 页面由前端通用 `WorkflowCenter` 渲染，数据来自后端 Workflow 定义。盘前 / 盘后不是独立前端页面，而是后端 `DEFAULT_WORKFLOWS` 中的两个定义：

- `pre-market`：盘前工作台
- `after-close`：盘后工作台

原盘前工作流包含：

- `run-pre-market`：执行盘前日报
- `snapshot-build`：构建候选池快照
- `market-state-build`：构建旧 Persona / MarketState JSON

迁移后只承接：

- `snapshot-build`
- `run-pre-market`

不承接：

- `market-state-build`

原盘后工作流包含：

- `run-after-close`：执行盘后考核 / 盘后复盘

迁移后承接：

- `run-after-close`
- 盘后结果展示
- 产物链接
- 失败任务跳转与重试

### 2.2 策略页面现状

当前 `/strategies` 已经具备部分盘前 / 盘后能力：

- 选择 Trader ID
- 选择策略日期
- 选择 Profile
- 读取 Profile 最新 snapshot，并拿到 `config_path`
- 提交 `strategy-build`
- 提交 `run-pre-market`
- 提交 `run-after-close`
- 查看策略相关 Job
- 查看策略版本
- 查看候选版本
- 查看相关产物

但还存在问题：

1. 页面过大，承担了太多职责。
2. 盘前只覆盖了 `run-pre-market`，缺少 `snapshot-build`。
3. 盘后只覆盖了 `run-after-close`，缺少业务化的盘后结果、信号归因、今日策略表现、产物入口。
4. Web 仍然从 Profile snapshot 中解析并提交 `config_path`，没有真正完成 Profile-only。
5. 盘前 / 盘后的 `force`、`export_html` 没有暴露为设置项。
6. `benchmark_symbol` 没有按“可选，默认从 Profile 读取”的方式处理。

---

## 3. `market-state-build` 的处理结论

### 3.1 当前作用

`market-state-build` 当前的作用是：

```text
benchmark_symbol
-> 从 AkShare 或 MarketDataCache CSV 获取基准指数日线
-> classify_market_state()
-> 写出 data/processed/persona/market_state.json
```

它属于旧 Persona / MarketState 链路，不是当前 Market Snapshot 主链路。

### 3.2 当前问题

现有代码显示：

- 它不是从数据库直接构建，而是从 AkShare 或本地 MarketDataCache CSV 构建。
- 它输出的是 `market_state.json`，不是候选池快照。
- 没有看到当前策略主流程、盘前页面、`snapshot-build` 或 `strategy-build` 直接消费它的产物。
- `RuleEvaluator.evaluate()` 仍接收 `MarketState`，但当前可见调用主要在测试中手动构造 `MarketState`，没有看到生产流程从 `market-state-build` 产物读取后传入。

### 3.3 迁移结论

`market-state-build` 不迁移到策略 Web 页面，也不作为盘前准备必要步骤。

推荐处理：

```text
Web 层：不暴露入口，不放入策略盘前页面。
后端层：短期保留 job 定义和服务实现，作为兼容能力。
文档层：标记为旧 Persona / MarketState 兼容任务。
后续：如果仍需要 MarketState，应并入 snapshot-build 的 market_state section，而不是恢复独立 Web 入口。
```

盘前完整功能调整为：

```text
1. 构建候选池快照 snapshot-build
2. 运行盘前 run-pre-market
3. 查看盘前 Job / 产物 / 失败重试
```

---

## 4. 迁移原则

### 4.1 不把 WorkflowCenter 原样搬到策略页

迁移后不继续展示通用 workflow 概念，而以业务语言组织：

- 盘前准备
- 盘后复盘
- 策略版本
- 候选版本
- 规则选择
- 运行历史

### 4.2 策略首页只做摘要和入口

策略首页不要成为第二个任务中心，也不要把盘前 / 盘后 / 候选 / 产物全部展开。首页只展示：

- 今日状态摘要
- 最近关键状态
- 快捷入口
- 异常提示

复杂操作进入子页面。

### 4.3 Job 详情仍归任务中心

最新盘前 Job、最新盘后 Job、最近失败任务的主功能放在 sidebar 现有「任务」中。策略首页只展示摘要和跳转。

任务中心继续承载：

- 最近任务列表
- 状态筛选
- 类型筛选
- Job 详情
- 参数快照
- 日志
- 产物
- 失败原因
- 重新运行
- 取消任务

### 4.4 Web 不再支持 config_path

Web 表单和提交参数不再暴露 `config_path`。Web 统一传：

- `profile_id`
- `profile_snapshot_id` 或 `snapshot_id`，如果后端需要

由后端根据 Profile 解析配置。CLI 可以继续保留 `config_path` 支持，但 Web 不再依赖它。

### 4.5 benchmark_symbol 可选

`benchmark_symbol` 在 Web 上做成可选：

- 用户选择时，使用用户选择值。
- 用户不选择时，后端从 Profile 默认配置读取。
- 如果 Profile 也没有默认 benchmark，则后端返回明确错误。

不要在前端硬编码默认指数。

---

## 5. 推荐信息架构

策略内部页面建议：

```text
/strategies
/strategies/pre-market
/strategies/after-close
/strategies/versions
/strategies/candidates
/strategies/history
/strategies/regime-selection
```

sidebar 只显示「策略」，这些子页面通过策略首页内部卡片或 Tab 进入。

---

## 6. 策略首页设计

### 6.1 页面职责

策略首页回答用户一个问题：

> 今天策略相关工作做到哪一步了？下一步应该点哪里？

### 6.2 首页显示内容

建议显示：

```text
今日策略状态
- Profile
- 策略日期
- 盘前状态
- 盘后状态
- 策略版本状态
- 候选版本状态
- 最近失败任务数量

快捷入口
- 盘前准备
- 盘后复盘
- 构建策略版本
- 候选版本
- 规则选择
- 运行历史
- 任务中心
```

### 6.3 Job 摘要展示

策略首页可以展示三张摘要卡：

```text
最新盘前 Job
最新盘后 Job
最近失败任务
```

但只显示摘要，不展开完整列表。

每张卡提供跳转：

```text
查看盘前 Job -> /jobs?job_type=run-pre-market
查看盘后 Job -> /jobs?job_type=run-after-close
查看失败任务 -> /jobs?status=failed
```

如果当前任务页还不支持 URL query 初始化筛选，需要补充。

---

## 7. 盘前准备页设计

### 7.1 页面路径

```text
/strategies/pre-market
```

### 7.2 页面职责

承接盘前完整主流程：

```text
1. 构建候选池快照 snapshot-build
2. 运行盘前 run-pre-market
3. 查看盘前 Job / 产物 / 失败重试
```

不承接：

```text
market-state-build
```

### 7.3 基础设置

始终显示：

```text
Profile
执行日期
benchmark_symbol，可选
```

参数映射：

| UI 字段 | Job 参数 | 说明 |
|---|---|---|
| Profile | `profile_id` | Web 只传 Profile，不传 `config_path` |
| 执行日期 | `date` / `as_of_date` | `snapshot-build` 用 `date`，`run-pre-market` 用 `as_of_date` |
| benchmark_symbol | `benchmark_symbol?` | 可选，空则后端从 Profile 读取 |

### 7.4 快照构建设置

承接 `snapshot-build`。

建议设置项：

```text
快照日期 date：默认执行日期
开始日期 start_date：高级选项
结束日期 end_date：高级选项
时间槽 slot：默认 17-30
快照类型 snapshot_type：默认 all
强制重建 force：checkbox，默认 false
离线模式 offline：checkbox，默认 false
benchmark_symbol：可选
```

提交参数示例：

```json
{
  "profile_id": "default",
  "date": "2026-05-22",
  "benchmark_symbol": "000300.SH",
  "slot": "17-30",
  "snapshot_type": "all",
  "force": false,
  "offline": false
}
```

如果用户不选择 `benchmark_symbol`，则不要传该字段或传 `null`，由后端从 Profile 读取。

### 7.5 盘前运行设置

承接 `run-pre-market`。

建议设置项：

```text
执行日期 as_of_date：默认执行日期
强制重新执行 force：checkbox，默认 false
导出 HTML export_html：checkbox，默认 false
```

提交参数示例：

```json
{
  "profile_id": "default",
  "as_of_date": "2026-05-22",
  "force": false,
  "export_html": false
}
```

### 7.6 盘前操作按钮

建议提供三个按钮：

```text
构建候选池快照
运行盘前
执行完整盘前准备
```

其中「执行完整盘前准备」可以先由前端顺序提交两个 Job：

```text
snapshot-build -> run-pre-market
```

中长期更推荐新增后端编排 Job，例如：

```text
pre-market-full-run
```

由后端统一处理串行执行、失败恢复和结果汇总。

---

## 8. 盘后复盘页设计

### 8.1 页面路径

```text
/strategies/after-close
```

### 8.2 页面职责

承接：

```text
run-after-close
盘后结果
信号归因
今日策略表现
产物链接
失败任务跳转重试
```

### 8.3 基础设置

```text
Profile
执行日期
```

### 8.4 运行设置

承接 `run-after-close`。

设置项：

```text
执行日期 as_of_date：默认执行日期
强制重新执行 force：checkbox，默认 false
导出 HTML export_html：checkbox，默认 false
```

提交参数示例：

```json
{
  "profile_id": "default",
  "as_of_date": "2026-05-22",
  "force": false,
  "export_html": false
}
```

### 8.5 结果展示

现有代码可以复用：

- Job Detail 的 `result`
- Job Detail 的 `artifacts`
- ArtifactPanel
- 任务详情页的重新运行能力

需要新增或补齐：

- 盘后结果业务卡片
- 信号归因卡片
- 今日策略表现卡片

如果 `run-after-close` 已经在 result/artifacts 中产出结构化结果，盘后页先读取最近 `run-after-close` Job 并展示；如果没有，需要新增后端 summary/attribution 接口。

---

## 10. 任务中心与失败重试

任务中心继续作为 Job 主入口。

策略首页只显示：

```text
最新盘前 Job 摘要
最新盘后 Job 摘要
最近失败任务摘要
```

失败重试不在策略首页直接实现复杂逻辑，跳转到 Job Detail：

```text
/jobs/:jobId
```

Job Detail 已承载：

- 参数快照
- 执行结果
- 错误信息
- 日志
- 产物
- 重新运行
- 取消任务

---

## 11. 实现步骤

### Step 1：

- 从 sidebar navigation 「工作流」 中移除「盘前工作台」和「盘后工作台」。
- 相关 URL `/workflows/pre-market` 和 `/workflows/after-close` 移除。

### Step 2：拆分策略页面

将当前大而全的 `/strategies` 拆为：

```text
StrategyHomePage
PreMarketPage
AfterClosePage
StrategyVersionsPage
StrategyCandidatesPage
StrategyHistoryPage
RegimeRuleSelectionPage
```

### Step 3：实现盘前准备页

- 增加 `snapshot-build` 提交入口。
- 保留 `run-pre-market` 提交入口。
- 增加 `force`、`export_html`、`slot`、`snapshot_type`、`offline` 设置项。
- `benchmark_symbol` 可选。
- 不增加 `market-state-build` 入口。

### Step 4：实现盘后复盘页

- 保留 `run-after-close` 提交入口。
- 增加 `force`、`export_html` 设置项。
- 展示最近盘后 Job result。
- 展示 artifacts。
- 提供失败任务跳转。

### Step 5：Web 参数 Profile-only

- 前端不再传 `config_path`。
- 所有策略相关 Job 改传 `profile_id`。
- 后端 Job handler 负责从 Profile 解析配置。
- CLI 保留 `config_path` 兼容。

### Step 6：处理 `market-state-build`

- 不迁移到策略 Web 页面。
- 不作为盘前准备步骤。
- 后端短期保留兼容。
- 文档中标记为 deprecated / legacy。
- 后续如果需要 MarketState，合并进 `snapshot-build` 的 `market_state` section。

---

## 12. 最终目标状态


### 策略首页

```text
今日策略状态
快捷入口
最近关键 Job 摘要
异常提示
```

### 盘前准备

```text
snapshot-build
run-pre-market
Job / 产物 / 失败跳转
```

没有：

```text
market-state-build
```

### 盘后复盘

```text
run-after-close
盘后结果
信号归因
今日策略表现
产物链接
失败任务跳转
```

### market-state-build

```text
旧 Persona / MarketState 兼容任务
不迁移到策略 Web 页面
不作为盘前必要步骤
后续如仍需要，应并入 Snapshot section
```

---

## 13. 需求变更 TaskList（简版）

> 说明：
> 1. 本 TaskList 只覆盖本次 review 中“工作流里的盘前 / 盘后功能迁移到策略模块”的需求。
> 2. “sidebar 里的整个工作流入口移除”是最终目标，但不在本轮 TaskList 的直接实现范围内。
> 3. 所有 Task 必须同时满足本文件中的功能要求与第 14 节验收标准。

### [x] T1 策略工作台信息架构与导航迁移

目标：

- 将盘前 / 盘后入口从 `workflow` 语义迁移到 `strategy` 语义。
- 建立策略首页、盘前准备页、盘后复盘页的路由与导航入口。
- 策略首页不是空壳页，也不是 Demo 页，必须具备可直接验收的完整业务能力边界。

必须实现：

- 策略首页 `/strategies`。
- 盘前准备页 `/strategies/pre-market`。
- 盘后复盘页 `/strategies/after-close`。
- 策略首页展示今日状态摘要、最近关键 Job 摘要、快捷入口、异常提示。
- 策略首页必须完整展示并可读：
  - 今日策略状态
  - Profile
  - 策略日期
  - 盘前状态
  - 盘后状态
  - 策略版本状态
  - 候选版本状态
  - 最近失败任务数量
- 策略首页必须提供以下快捷入口：
  - 盘前准备
  - 盘后复盘
  - 构建策略版本
  - 候选版本
  - 规则选择
  - 运行历史
  - 任务中心
- 策略首页只展示状态摘要，不承担任务中心职责，但必须提供跳转到任务中心的入口。
- 策略首页的摘要项必须可以跳转到任务中心或带筛选条件的任务列表。
- 策略首页的数据必须来自真实后端能力，不允许只做纯静态文案或占位卡片。
- 策略首页需要覆盖 loading / empty / error / retry / success 状态。
- 策略首页依赖的任务中心跳转必须支持 query 初始化筛选。
- `/jobs` 的 query 初始化筛选至少支持 `job_type`、`status` 和项目实际需要的核心筛选条件。
- workflow 中原有的盘前 / 盘后入口不再作为正式入口继续扩张，需要移除。

### [x] T2 盘前准备页完整实现

目标：

- 完整承接 `snapshot-build` 与 `run-pre-market`。
- 不再暴露 `market-state-build`。
- Web 不暴露 `config_path`，统一使用 `profile_id`。
- `benchmark_symbol` 在 Web 中可选，空值时由后端按 Profile 默认值补齐。

必须实现：

- `snapshot-build` 的提交入口。
- `run-pre-market` 的提交入口。
- `Profile`、执行日期、`benchmark_symbol` 的基础设置。
- `snapshot-build` 的 `date / start_date / end_date / slot / snapshot_type / force / offline` 配置。
- `run-pre-market` 的 `as_of_date / force / export_html` 配置。
- `benchmark_symbol` 为空时不阻断前端，由后端从 Profile 读取。
- Job 状态、失败重试、日志、产物必须通过任务中心或 Job Detail 查看。
- 页面必须覆盖 loading / empty / error / retry / success 状态。

### [x] T3 盘后复盘页完整实现

目标：

- 完整承接 `run-after-close`。
- 展示盘后结果、信号归因、今日策略表现、产物链接。
- 失败任务跳转与重试仍回到任务中心。
- Web 不暴露 `config_path`，统一使用 `profile_id`。

必须实现：

- `run-after-close` 的提交入口。
- `Profile`、执行日期的基础设置。
- `run-after-close` 的 `as_of_date / force / export_html` 配置。
- 最近盘后 Job result 的展示。
- artifacts 的展示和来源跳转。
- 盘后结果业务卡片、信号归因卡片、今日策略表现卡片。
- 失败任务跳转到 Job Detail，重试由任务中心承载。
- 页面必须覆盖 loading / empty / error / retry / success 状态。

### [ ] T4 策略辅助页面与版本构建实现

目标：

- 补齐策略模块下的辅助页面，避免策略首页成为唯一入口。
- 提供策略版本、候选版本、运行历史、规则选择的独立页面。

必须实现：

- `/strategies/versions`
- `/strategies/candidates`
- `/strategies/history`
- `/strategies/regime-selection`
- 上述页面均需展示真实后端数据，而不是静态占位。
- 上述页面均需具备基础 loading / empty / error / retry / success 状态。
- 上述页面均需提供返回策略首页入口。
- 策略版本页需要支持 `strategy-build` 的提交与结果展示，不得只停留在版本列表。
- 策略版本页需要展示最新策略版本、可构建操作、版本结果与跳转入口。
- 规则选择页需要支持策略规则的查看与选择，不得只停留在列表展示。
- 运行历史页需要支持按日期 / 状态 / 类型等维度筛选历史运行记录。
- 需要收口旧 workflow 的盘前 / 盘后正式入口，不再继续作为正式导航。
- `market-state-build` 仅作为旧 Persona / MarketState 兼容能力保留，不进入策略页面。
- 相关 API、页面、路由、测试、文档同步更新。
- 验证 `config_path` 不再出现在策略 Web 提交参数中。
- 验证 `benchmark_symbol` 的可选逻辑与后端回填逻辑一致。

---

## 14. 验收标准

完成后必须满足以下验收条件：

1. `/strategies` 能作为策略工作台首页正常访问。
2. `/strategies/pre-market` 能完成 `snapshot-build` 与 `run-pre-market` 的操作入口与结果查看。
3. `/strategies/after-close` 能完成 `run-after-close` 的操作入口与结果查看。
4. Web 不再提交 `config_path`，统一以 `profile_id` 为准。
5. `benchmark_symbol` 在 Web 侧可选，未填写时后端能从 Profile 回填。
6. `market-state-build` 不出现在策略 Web 页面中。
7. Job 状态、失败重试、日志、产物都可通过任务中心或 Job Detail 查看。
8. 策略首页不是空壳页，必须能显示今日状态摘要并提供跳转到任务中心的入口。
9. 策略辅助页面（versions / candidates / history / regime-selection）可正常访问并具备基础功能。
10. 策略版本页可以完成 `strategy-build` 的提交与结果查看。
11. 任务中心支持 query 初始化筛选，且首页跳转能落到对应筛选结果。
12. 盘前 / 盘后页面覆盖 loading、empty、error、retry、success 状态。
13. workflow 中盘前 / 盘后正式入口已退役，不再作为默认导航使用。
14. 相关路由、导航、API contract、测试、文档均已同步。
15. 代码实现后不存在明显的占位 mock、临时跳过或未收口 TODO。
