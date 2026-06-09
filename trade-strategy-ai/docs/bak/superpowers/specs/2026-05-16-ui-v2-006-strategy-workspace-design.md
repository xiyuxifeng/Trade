# UI-V2-006 Strategy Workspace Design

## 背景

`UI-V2-006` 是 V2 正式 Web 工作台的一部分，目标是把策略版本构建、盘前、盘后和证据包查看收口到统一的正式入口，而不是继续强化 Demo 式 CLI 命令或旧的 `strategy-studio` 实验页面。

本设计遵循以下约束：

- V2 目标是“面向最终交付的重构”的 Web 项目。
- UI 必须和 `UI-V2-002` 保持一致的浅色工作台风格。
- 只能通过 Web / Job / Workflow / Artifact 体系完成操作。
- 前端不计算策略结果，不推断排名，不拼接本地绝对路径。

## 目标

1. 提供一个正式的 Strategy Workspace 入口，用于执行策略版本构建、盘前和盘后任务。
2. 让用户可以选择 `trader / date / profile`，并把选中的 Profile 映射为运行所需的 `config_path`。
3. 显示最近策略任务、最近策略版本和报告 / 证据包的可解释入口。
4. 对高风险或覆盖性操作提供明确确认。
5. 保持与 `UI-V2-002` 一致的浅色、卡片式、低饱和蓝色强调的 UI 风格。

## 非目标

- 不在前端计算策略结果。
- 不在前端推断排名或规则适用性。
- 不新增 CLI 正式入口。
- 不做后续 V3 的回测 / rule pool / regime-aware 能力闭环。
- 不把 `strategy-studio` 继续演进成第二套正式入口。

## 路由与入口

正式入口使用：

- `/strategies`

兼容入口保留：

- `/strategy-studio`

策略工作台必须只把 `/strategies` 作为正式产品入口，兼容入口只用于历史书签和旧文档。

## 设计方案

### 总体结构

页面采用单页工作台布局，分成三个层次：

1. 顶部说明区
   - `PageHeader`
   - 明确告诉用户这是正式入口
   - 说明当前只做 Web 正式交付，不扩 CLI

2. 主操作区
   - `trader_id`
   - `strategy_date`
   - `profile`
   - `config_path` 预览
   - 三个主操作按钮：
     - `构建策略版本`
     - `盘前运行`
     - `盘后运行`

3. 结果解释区
   - 最近策略任务
   - 最近策略版本
   - 当前选中策略版本详情
   - 报告 / 证据包入口
   - Artifact Center 跳转

### 推荐实现形态

推荐使用“单页工作台 + 分区卡片”的方式，而不是 Tabs 重型布局。

原因：

- 更接近 `UI-V2-002` / `UI-V2-005` 的工作台风格。
- 用户可以在同一个页面完成选择、触发、查看结果。
- 后续只需把局部卡片替换成真实数据，不需要重做整体信息架构。

## 数据流

### 1. Profile 选择

- 用户在页面选择 `profile`
- 前端通过 `getProfile(profileId)` 读取 Profile 详情
- 从 Profile 详情里拿到最新可用的 `config_path` 或 snapshot 关联信息
- 该 `config_path` 仅作为 Job 参数的一部分，不作为新的事实源

### 2. 任务触发

触发任务统一走 `createJob()`：

- `strategy-build`
- `run-pre-market`
- `run-after-close`

前端只负责组装参数，不负责执行逻辑。

### 3. 结果查看

策略版本和结果解释优先通过既有 API 获取：

- `listStrategyVersions()`
- `getStrategyVersion()`
- `listJobs()`
- `getJob()` / `getJobLogs()`
- `listArtifacts()`

页面展示时只引用后端返回的版本、报告、证据包和产物引用。

## 页面组件

### 顶部区

- `PageHeader`
- `Badge`
- 简短说明文字

### 输入区

- `Select` 用于 `trader_id`
- `Input` 用于 `strategy_date`
- `Select` 或 `Profile chooser` 用于 `profile`
- 只读 `config_path` 预览
- `Button` 触发三类任务

### 结果区

- 最近策略任务列表
- 最近策略版本列表
- 策略版本详情卡片
- 报告 / 证据包摘要
- 跳转按钮：
  - `Artifact Center`
  - `Jobs`

## 确认与风险

### 需要确认的操作

- `strategy-build`
- `run-pre-market`
- `run-after-close`

这些操作需要确认弹窗，避免误触导致覆盖性运行。

### 风险分类

页面需要把错误明确归类为：

- `validation error`
- `permission denied`
- `config missing`
- `profile missing`
- `provider unavailable`
- `job failed`
- `artifact missing`
- `network error`

错误信息需要包含下一步建议，而不是只抛原始异常。

## 空状态与加载状态

必须覆盖：

- loading
- empty
- error
- retry
- success

空状态要求：

- 没有策略版本时展示明确空态
- 没有最近任务时展示明确空态
- 没有证据包或报告时提示去 `Market Data` / `Artifacts` 补上下文

## 验收标准

1. 用户能通过 Web 运行策略版本构建、盘前和盘后任务。
2. 用户能通过策略工作台查看最近策略任务和版本。
3. 用户能通过 artifact / report 入口解释运行结果。
4. 页面有明确确认流程。
5. 页面保持与 `UI-V2-002` 一致的浅色工作台风格。
6. 页面不直接读取本地文件路径，不调用 provider，不计算结果。
7. `strategy-studio` 仅作为兼容入口存在，不扩张为正式入口。

## 测试策略

### 组件测试

- 默认加载成功
- Profile 选择后更新 `config_path`
- 三类 Job 按钮触发正确 `job_type`
- 确认弹窗行为
- 最近任务、版本、报告、证据包的空态
- 错误态和重试态

### 路由测试

- `/strategies` 能正常打开
- `/strategy-studio` 仍然可访问
- 新的正式工作台不破坏既有 `market / profiles / jobs / artifacts` 路由

### 回归检查

- `git diff --check`
- 相关 Vitest
- 必要时跑局部页面渲染测试，确认浅色工作台风格没有回退

## 交付边界

本任务只负责 Strategy Workspace 的 Web 入口和用户操作面，不承担：

- 回测中心实现
- rule pool 实现
- regime-aware selection
- CLI 命令增强
- 后端策略算法变更

这些能力留给 `NW-V2-S3-001` / `NW-V2-S3-002` 和后续 V3 任务处理。

