# Trade Strategy AI 重构对话模板与模型执行指南

> 建议作为仓库中的唯一 AI 执行入口。  
> 建议最终路径：`trade-strategy-ai/docs/AI-Conversation-Templates.md`  
> 适用范围：`Trade-Refactor-TaskList.md` 的 Stage 2～Stage 12  
> 当前状态依据：Stage 0、Stage 1 已完成；当前下一步为 `RT-S2-001`

---

# 1. 文档定位

本文档合并并替代以下两份执行说明：

1. 原 `trade-strategy-ai/docs/AI-Conversation-Templates.md`
2. `Trade-Refactor-Unfinished-Stages-Model-Workflow.md`

本文档统一包含：

- 模型选择与额度控制；
- Stage Bootstrap、Task 实现、Task Review、升级和 Stage Gate；
- Parent `gpt-5.5` 与 Parent `gpt-5.4` 的职责；
- `gpt-5.4-mini` subagent 的使用条件；
- 未完成 Stage 的风险与特殊注意事项；
- 可直接复制使用的 Prompt；
- UI、测试、迁移、回滚和日志规则。

本文档是 **AI 执行协议**，不仅是给用户阅读的说明。

AI 在执行任务时必须读取本文档中与当前阶段相关的规则，并执行其中的升级门禁。用户不需要持续人工判断技术风险。

---

# 2. 文件分工

## 2.1 主入口

```text
trade-strategy-ai/docs/AI-Conversation-Templates.md
```

用途：

- 决定当前应使用 `gpt-5.5` 还是 `gpt-5.4`；
- 复制 Stage、Task、升级、Review 和恢复 Prompt；
- 约束 subagent 数量和上下文；
- 规定验证、日志和 Stage Gate。

## 2.2 继续保留、按需读取的辅助文档

```text
trade-strategy-ai/docs/AI-Conversation-Project-Constraints-1.md
trade-strategy-ai/docs/AI-Conversation-Project-Constraints-2.md
trade-strategy-ai/docs/AI-Conversation-Task-Matrix.md
trade-strategy-ai/docs/Trade-Refactor-TaskList.md
trade-strategy-ai/docs/Refactor-Implementation-Log.md
trade-strategy-ai/docs/refactor-implementation-logs/stage-<n>.md
trade-strategy-ai/docs/refactor-implementation-plans/stage-<n>-implementation-plan.md
```

辅助文档不要全部合并到本文档：

- `Project-Constraints-*`：只粘贴当前 Task 需要的 1～2 个约束块；
- `Task-Matrix`：只在判断 Task 是否可组合时读取；
- `Trade-Refactor-TaskList`：权威业务范围和验收标准；
- `Refactor-Implementation-Log`：当前状态和下一步；
- `stage-<n>.md`：当前 Stage 的详细证据；
- `stage-<n>-implementation-plan.md`：5.5 冻结的共享契约和 Task Card。

不得把完整约束库、Task Matrix 和全部历史 Stage 日志发送给每个 subagent。

---

# 3. 推荐模型执行模式

## 3.1 Stage 级默认流程

```text
A. Stage Bootstrap
   Parent gpt-5.5
   → 核对仓库事实
   → 冻结共享契约
   → 生成 Stage 实现计划
   → 生成各 Task 的 Task Card

B. Task Implementation
   Parent gpt-5.4
   → 每次执行一个 Task
   → 必要时使用 0～1 个 gpt-5.4-mini
   → focused tests
   → Parent 5.4 Task Review
   → 更新日志

C. Conditional Escalation
   Parent 5.4 命中升级门禁
   → 停止相关实现
   → 输出 ESCALATION_REQUIRED
   → Parent gpt-5.5 确认或修订契约
   → 输出 RESUME_WITH_GPT_5_4 或 BLOCKED

D. Stage Gate
   Parent gpt-5.5
   → Review 完整 Stage diff
   → 运行或复用适用证据
   → ACCEPTED / CONDITIONAL / BLOCKED
```

正确的额度控制结构通常是：

```text
一次 5.5 Bootstrap
→ 多个 5.4 Task Session
→ 一次 5.5 Stage Gate
```

不要机械地对每个 Task 都重复：

```text
5.5 → 5.4 → 5.5
```

---

## 3.2 风险分级

| 风险 | 默认执行 |
|---|---|
| M1：局部、已定位、低风险 | Parent 5.4 直接执行，通常 0 个 subagent |
| M2：契约已冻结的普通实现 | Parent 5.4，默认 0～1 个 mini Executor |
| M3：Schema、迁移、时间语义、正式事实源、策略或退役 | 5.5 冻结，5.4 实现，当前 Task 专项验证，5.5 Stage Gate |

### M1 例子

- 小范围文案；
- 单个组件；
- 已定位 Bug；
- 小型测试；
- 实施日志；
- 明确枚举映射。

### M2 例子

- 已冻结 API 的页面或 Service；
- 审核工作台 UI；
- 数据聚合接口；
- 明确状态机；
- 调度管理页面；
- 错误组件。

### M3 例子

- 核心领域模型；
- 数据库 Schema 和 migration；
- Prompt/Schema 正式调用链；
- point-in-time 回测；
- 正式规则、画像、策略生命周期；
- 灰度迁移；
- destructive deletion；
- 最终验收。

---

# 4. 上下文模式

## 4.1 Stage Bootstrap

用于：

- 新 Stage；
- 新 Session 且上下文不确定；
- 公共契约变化；
- 工作区存在来源不明修改；
- 文档与运行事实冲突。

Parent 读取：

1. `AGENTS.md`
2. `trade-strategy-ai/AGENTS.md`
3. `Trade-Refactor-TaskList.md`
4. 完整重构方案
5. `Refactor-Implementation-Log.md`
6. 当前 `stage-<n>.md`，不存在则创建
7. 当前 Stage 直接相关设计、迁移和验收文档
8. 当前分支、基线、`git status`、完整 diff
9. 相关代码、测试、数据库和 API

Prompt、文章、作者画像文档只在对应 Stage 实际修改它们时读取。

## 4.2 Same-Stage Continuation

同一个 Stage 后续 Task 只读取：

- 当前 Task 要求；
- 当前实施计划中的 Task Card；
- 主实施日志的新状态；
- 当前 Stage 日志新增条目；
- 上游 handoff 和冻结契约；
- 当前 diff、相关代码和测试。

全局文档仅在以下情况重读：

- 文件已变化；
- 存在冲突；
- 当前事实不确定；
- 当前 Task 要改变共享公共契约。

## 4.3 New Session Recovery

新 Session 恢复任务时：

- 不根据聊天记忆推断进度；
- 以日志、工作区、diff 和测试证据为准；
- 先报告当前 Stage、当前 Task、已接受工作、未完成工作、阻塞和下一安全步骤；
- 在事实建立前不实施。

---

# 5. 委派与额度控制

## 5.1 Agent 预算

```text
小 Task：0 个 subagent
普通 Task：0～1 个 subagent
两个独立且不重叠的写入任务：最多 2 个 Executor
大型只读审计：最多 2～3 个 Explorer
```

`0` 个 subagent 是合法且常见的结果。

已知文件、调用链和所有权时，不创建 Explorer。

## 5.2 适合委派给 mini

- 全仓引用搜索；
- 调用链调查；
- 边界明确的局部实现；
- 补 focused tests；
- 机械字段迁移；
- 明确范围内的前端模块；
- 明确范围内的后端模块；
- 引用清理；
- 测试失败摘要。

## 5.3 不适合委派给 mini

- 决定核心领域模型；
- 决定正式事实源；
- 修改冻结 Schema；
- 决定 migration/rollback 策略；
- 决定 point-in-time 语义；
- 决定策略发布或正式规则选择；
- 决定旧入口是否可删除；
- 最终 Task/Stage 验收。

## 5.4 Task Card 必须包含

```text
Task ID
目标
当前事实
冻结契约
允许修改路径
禁止修改路径
明确输出
测试命令
专项验证
完成条件
停止条件
升级 gpt-5.5 条件
```

一个 Executor 应尽量同时完成：

```text
实现
→ 局部测试
→ 机械自查
→ 精简结果摘要
```

不要默认拆成写代码、补测试、跑 lint 三个 Agent。

---

# 6. Parent 5.4 的自动升级门禁

## 6.1 谁负责判断

以下门禁由 **Parent 5.4 自动检查**，不是让用户在执行过程中人工监控。

Parent 5.4 必须：

1. Task 开始前检查一次；
2. 调查完成、写入前检查一次；
3. 发现仓库事实与 Task Card 不一致时立即检查；
4. Task Review 前再次检查。

## 6.2 命中任意条件必须暂停

1. 需要改变冻结的核心领域对象；
2. 需要改变稳定 ID 或版本关系；
3. 需要改变数据库 Schema 或 migration 策略；
4. 需要改变公共 API 或 DTO 契约；
5. 需要改变正式事实源；
6. migration 无法按计划 rollback 或安全重跑；
7. 涉及 point-in-time、未来数据泄漏或可用时间不确定；
8. 涉及正式规则、画像或策略发布语义；
9. 自动建议可能直接覆盖正式资产；
10. 删除范围或兼容边界不清；
11. 文档与实际运行事实冲突；
12. 必须跨越当前 Task 或 Stage 边界才能解决；
13. mini 连续两轮无法按 Task Card 完成；
14. 发现多个生产写入入口或第二套正式 Schema；
15. 无法判断当前 Task 是否符合 Stage 目标；
16. 实现将使既有关键验收证据失效。

## 6.3 命中后的强制动作

Parent 5.4 不得自行改变冻结契约，不得继续相关实现。

必须：

- 停止风险写入；
- 保留工作区；
- 不回退用户修改和安全的已完成工作；
- 更新当前 Stage 日志；
- 输出 `ESCALATION_REQUIRED`；
- 清楚列出证据、受影响契约和需要 5.5 决定的问题。

固定输出格式：

```text
ESCALATION_REQUIRED

Task:
[Task ID and title]

Trigger:
[命中的升级条件]

Evidence:
- [文件、调用链、Schema、测试或运行证据]

Affected frozen contracts:
- [受影响契约]

Work completed safely:
- [安全完成的调查或修改]

Current working tree:
- [已修改文件或无修改]

Decision required from gpt-5.5:
- [需要确认或修订的事项]

Recommended next action:
Start a gpt-5.5 Contract Escalation Review.
```

Parent 5.4 不能自动切换自己的模型。用户看到 `ESCALATION_REQUIRED` 后，切换或新开 `gpt-5.5` Session。

---

# 7. 验证规则

## 7.1 普通 Task

默认运行：

- focused tests；
- 直接受影响回归；
- 一个必要静态检查；
- `git diff --check`。

## 7.2 高风险 Task 当前任务内必须验证

不得全部推迟到 Stage Gate：

- migration / rollback / safe rerun；
- 安全和权限；
- point-in-time；
- 中心事实源；
- destructive deletion；
- 缓存失效；
- 幂等和恢复；
- 发布与回滚状态；
- 正式资产不可被自动覆盖。

## 7.3 Stage Gate

运行或验证：

- 受影响前后端测试；
- 适用的 typecheck、lint、build；
- migration/rollback；
- 受影响关键业务路径 E2E；
- compatibility/retirement gate；
- `git diff --check`；
- 实现、主日志和 Stage 日志一致性。

可靠证据覆盖最终 diff 且之后相关代码未变化时可以复用。每个跳过项必须说明：

- 不适用；或
- 哪个已有证据覆盖。

## 7.4 日志控制

不要把数千行测试日志反复放进 Parent 上下文。

优先记录：

```text
命令
通过/失败数量
失败测试名称
核心错误
相关文件
是否影响冻结契约
```

仅在定位需要时读取失败附近的日志。

---

# 8. Stage Gate 与 UI 验收

普通局部 UI Task：

- 不做完整桌面/移动视觉遍历；
- 不要求用户逐 Task 批准；
- 自动测试验证行为、路由、权限、真实数据状态和关键交互。

以下修改在 Stage Gate 生成或更新：

```text
trade-strategy-ai/docs/ui-acceptance/stage-<n>-ui-checklist.md
```

适用：

- 全局导航；
- 全局布局和设计系统；
- 首页；
- 主要用户旅程；
- 交付关键页面。

UI checklist 只包含：

- 代表性关键页面；
- 必要 viewport；
- 核心路径；
- 必要人工观察项。

Agent 不代替用户声明主观视觉检查通过。

轻微间距、颜色、字体和响应式 polish 记为 MEDIUM/LOW follow-up，不作为代码 BLOCKER。

---

# 9. 未完成 Stage 的模型适用性

Stage 2～Stage 12 都适合 Stage 级模式，但强度不同。

| Stage | 推荐模式 | Bootstrap | Gate |
|---|---|---:|---:|
| Stage 2：领域模型、数据库和版本契约 | 完整模式 | 很高 | 很高 |
| Stage 3：Prompt 与文章处理链路 | 完整模式 | 很高 | 很高 |
| Stage 4：规则管理、去重和规则族 | 完整模式 | 高 | 高 |
| Stage 5：基础数据、调度与数据质量 | 完整模式 | 很高 | 很高 |
| Stage 6：回测与规则适用性 | 完整模式 | 很高 | 很高 |
| Stage 7：作者画像 | 完整模式 | 高 | 高 |
| Stage 8：策略中心 | 完整模式 | 很高 | 很高 |
| Stage 9：每日盘前 | 完整模式 | 很高 | 很高 |
| Stage 10：每日盘后 | 完整模式 | 很高 | 很高 |
| Stage 11：系统管理、自动化与告警 | 完整模式 | 很高 | 很高 |
| Stage 12：旧入口退役与最终交付 | 交付变体 | 高 | 最高 |

Stage 12 的 Bootstrap 重点不是重新设计架构，而是冻结：

- 可删除范围；
- 兼容读取；
- 最终 E2E；
- 文档交付范围；
- 正式版本；
- 回滚和恢复方案。

---

# 10. 各 Stage 与子 Task 特殊注意事项

## 10.1 Stage 2：领域模型、数据库和版本契约

| Task | 特殊注意 |
|---|---|
| RT-S2-001 | 对象边界、稳定 ID、版本关系、生命周期、唯一事实源；不要提前实现后续业务 |
| RT-S2-002 | 表、外键、唯一约束、索引、Prompt 原始输出；必须 migration/rollback 或 safe rerun |
| RT-S2-003 | 不可静默丢失旧数据；必须质量状态、迁移报告、重复执行和失败恢复 |

强制升级条件：

- 核心对象需要变化；
- 现有数据库无法映射冻结模型；
- migration 无法回滚或重跑；
- 发现多个正式事实源。

## 10.2 Stage 3：Prompt 与文章处理链路

| Task | 特殊注意 |
|---|---|
| RT-S3-001 | Prompt、Schema、调用编排版本化；事实与推断分离 |
| RT-S3-002 | 原文、证据、缺失项、可回测和 Kaipan 依赖必须可见 |
| RT-S3-003 | 先固定 10～15 篇样本；通过前不得全量重跑 |
| RT-S3-004 | 对照、Schema 映射、观察期、回滚、全仓无引用后才能删除 |

防止：

- 新旧 Prompt 同时产生正式数据；
- repair 成为常规第二次调用；
- 作者画像逐篇调用；
- 回归未通过就处理 100+ 篇文章。

## 10.3 Stage 4：规则管理、去重和规则族

| Task | 特殊注意 |
|---|---|
| RT-S4-001 | 自动通过仅代表可进入待回测；正式使用仍需门禁和人工确认 |
| RT-S4-002 | 指纹算法确定性、版本化；区分重复、参数变体和冲突 |
| RT-S4-003 | 状态转换集中管理；适合 Parent 5.4 标准实现 |

## 10.4 Stage 5：基础数据、调度与数据质量

| Task | 特殊注意 |
|---|---|
| RT-S5-001 | DatasetSnapshot 固定回测数据；补抓不能静默改变历史结果 |
| RT-S5-002 | 区分盘前/盘后 slot；缺失不能当成条件 false |
| RT-S5-003 | 时区、交易日、幂等、失败重试和重复调度 |

## 10.5 Stage 6：回测与规则适用性

| Task | 特殊注意 |
|---|---|
| RT-S6-001 | UI 参数与运行契约一致；自动检查数据依赖 |
| RT-S6-002 | 严禁未来数据泄漏；固定市场状态模型版本 |
| RT-S6-003 | 样本量、收益、胜率、回撤、置信度和推荐状态分开 |
| RT-S6-004 | Level 1/2/3 数据要求和降级语义固定 |

## 10.6 Stage 7：作者画像

| Task | 特殊注意 |
|---|---|
| RT-S7-001 | 只描述文章方法，不声称真实实盘结果 |
| RT-S7-002 | 程序统计与 LLM 解释分区保存 |
| RT-S7-003 | 只基于回测和每日证据；显示样本量和覆盖率 |
| RT-S7-004 | 新数据只生成草稿，不覆盖正式画像 |

## 10.7 Stage 8：策略中心

| Task | 特殊注意 |
|---|---|
| RT-S8-001 | 规则池、权重、画像、风险和仓位全部绑定版本 |
| RT-S8-002 | 样本外验证、比较、发布和回滚闭环 |
| RT-S8-003 | 只能生成 Proposal，不能直接修改正式策略 |

## 10.8 Stage 9：每日盘前

| Task | 特殊注意 |
|---|---|
| RT-S9-001 | 明确 ready/degraded/blocked；适合 5.4 标准实现 |
| RT-S9-002 | 选择优先级确定性；正式适用性优先 |
| RT-S9-003 | 每日对象是运行实例，不是新正式策略 |

## 10.9 Stage 10：每日盘后

| Task | 特殊注意 |
|---|---|
| RT-S10-001 | 冻结触发、执行、收益、MFE、MAE 计算口径 |
| RT-S10-002 | 程序事实优先；LLM 仅条件触发解释 |
| RT-S10-003 | Rule、Profile、Strategy Proposal 分离 |
| RT-S10-004 | 页面使用业务中文；适合 5.4 标准实现 |

## 10.10 Stage 11：系统管理、自动化与告警

| Task | 特殊注意 |
|---|---|
| RT-S11-001 | 业务与管理员入口分离；适合 5.4 |
| RT-S11-002 | 定时、重试、断点续跑、批处理恢复必须幂等 |
| RT-S11-003 | 统一稳定 run_id，跨系统追溯 |
| RT-S11-004 | 缓存失效、并发限制、重试上限、预算 |
| RT-S11-005 | 统一 trade_date/available_at/captured_at/effective_at/source/slot |
| RT-S11-006 | 对照→只读→小范围→默认→旧只读→退役 |
| RT-S11-007 | 错误说明发生了什么、影响什么、怎么处理 |

最高风险：

- RT-S11-002；
- RT-S11-005；
- RT-S11-006。

## 10.11 Stage 12：旧入口退役与最终交付

| Task | 特殊注意 |
|---|---|
| RT-S12-001 | 全仓引用、兼容读取、只读阶段和恢复方案完成后才删除 |
| RT-S12-002 | 必须走通文章→规则→回测→画像→策略→盘前→盘后 |
| RT-S12-003 | 文档必须与最终真实 UI、权限和流程一致 |

最终验收不得委派给 subagent。

---

# 11. 通用 Prompt 模板

## 11.1 Parent 5.5：Stage Bootstrap 与计划生成

```text
Use the refactor-orchestrator skill.

This is a Stage Bootstrap and contract-freezing session using gpt-5.5.

Work from the Trade repository root.

Analyze and prepare only:
[Stage ID, title, and Task list]

Do not perform the full Stage implementation.
Do not start the next Stage.

Parent must read:
- AGENTS.md
- trade-strategy-ai/AGENTS.md
- trade-strategy-ai/docs/AI-Conversation-Templates.md
- trade-strategy-ai/docs/Trade-Refactor-TaskList.md
- trade-strategy-ai/docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md
- trade-strategy-ai/docs/Refactor-Implementation-Log.md
- current refactor-implementation-logs/stage-<n>.md, or create it
- exact current Stage documents
- current branch, baseline, git status, complete diff
- related code, tests, data, database, API, migrations, and runtime entry points

Read Prompt/author-profile documents only when this Stage changes them.
Do not read unrelated Stage documents.

First verify:
- previous Stage acceptance
- whether this Stage may begin
- actual working-tree state and user-owned changes
- current official fact sources
- reusable existing implementation
- documentation/runtime conflicts

For the Stage:
- classify each Task as M1, M2, or M3
- freeze shared domain contracts
- freeze Schema, API, DTO, state transitions, permissions, and fact sources
- define migration, rollback, compatibility, and retirement rules
- define point-in-time semantics when applicable
- define Task dependencies and execution order
- define allowed and forbidden paths for each Task
- define focused and specialized verification
- define explicit gpt-5.5 escalation conditions
- define the final Stage Gate
- identify later-Stage behavior that is out of scope

Create or update:
trade-strategy-ai/docs/refactor-implementation-plans/stage-<n>-implementation-plan.md
trade-strategy-ai/docs/refactor-implementation-logs/stage-<n>.md

The plan must include bounded Task Cards executable by a gpt-5.4 Parent with
optional gpt-5.4-mini subagents.

Explicitly decide whether read-only delegation is justified.
Do not spawn a broad implementation Executor during Bootstrap.
Do not create an Explorer when ownership and call chains are known.

Update Refactor-Implementation-Log.md only with truthful current status,
blockers, plan path, and the next executable Task.

Return only:
- delegation decision
- verified repository facts
- frozen contracts
- Task order and Task Cards
- escalation conditions
- risks and blockers
- files created or updated
- next executable Task
```

---

## 11.2 Parent 5.4：Task 实现

```text
Use the refactor-orchestrator skill.

Continue within:
[Stage ID]

Execute only:
[Task ID and title]

Use:
- trade-strategy-ai/docs/AI-Conversation-Templates.md
- the frozen Stage plan
- the current Task Card

Read only:
- current Task requirements
- applicable frozen contracts
- current-status changes in Refactor-Implementation-Log.md
- new entries in current stage-<n>.md
- upstream handoff
- current git status and complete diff
- directly related code and tests
- 1–2 applicable project-constraint blocks

Do not reread unchanged global documents.
Do not redesign frozen contracts.
Do not implement another Task or later Stage.

Before implementation:
- verify that the Task Card matches the actual working tree
- classify M1/M2/M3
- run the gpt-5.5 escalation preflight
- explicitly decide whether delegation is justified
- use zero subagents for small or localized work
- use at most one gpt-5.4-mini Executor for an ordinary bounded Task
- do not create an Explorer when files and call chains are known

If delegating, provide a bounded Task Card with:
- exact goal
- allowed and forbidden paths
- frozen contracts
- tests
- stop conditions
- escalation conditions

Parent must:
- inspect the actual final diff
- verify frozen-contract compliance
- run focused tests
- run directly affected regressions
- run one necessary static check
- run git diff --check
- run specialized verification now for migration, security, permissions,
  point-in-time, central fact sources, cache invalidation, or deletion
- complete the Task Review
- update stage-<n>.md
- update Refactor-Implementation-Log.md

When any escalation condition is met:
- stop related implementation
- do not change the frozen contract
- output ESCALATION_REQUIRED using the required format
- do not start another Task

Otherwise:
- state whether this Task is accepted
- state whether the next Task may begin
- do not mark the Stage complete

Return only:
- delegation
- files changed
- contract compliance
- checks and results
- blockers or escalation
- handoff
```

---

## 11.3 Same-Stage Continuation

```text
Use the refactor-orchestrator skill.

Continue within the current Stage using established frozen contracts.

Execute only:
[Task ID and title]

Read only:
- the current Task requirements and Task Card
- current-status changes
- new Stage-log entries
- upstream handoff and frozen contracts
- current git status, complete diff, related code and tests
- applicable small constraint blocks

Do not reread unchanged global documents.
Reread them only when changed, conflicting, uncertain, or when this Task changes
a shared public contract.

Run the escalation preflight.
Explicitly decide whether delegation is justified.
Zero subagents is valid.
Do not spawn an Explorer when files, call chains, and ownership are known.

Verification:
- focused tests
- affected regressions
- one necessary static check
- git diff --check
- current-Task specialized checks
- defer broad checks to Stage Gate unless a high-risk shared contract changed

Update current Stage log and main implementation status.
Do not start another Task.
Do not mark the Stage complete.
```

---

## 11.4 Parent 5.4：Task Review

通常在实现 Session 内完成，不必为普通 Task 单独启动 5.5。

```text
Use the refactor-orchestrator skill.
Use the gpt-5.4 Parent as the Task reviewer.

Review only:
[Task ID and title]

Do not start another Task or Stage.

Read only:
- Task acceptance requirements
- Task Card and frozen contracts
- current status and Task entries
- upstream handoff
- current Task diff
- affected files and tests

Check:
- requirements
- frozen-contract compliance
- fact-source uniqueness
- compatibility
- scope
- truthful data states
- no later-Task implementation
- documentation accuracy
- escalation conditions

Run or verify:
- focused tests
- one required static check
- git diff --check
- specialized checks required by this Task

Reuse evidence only when it covers the final Task diff and no relevant code
changed afterward.

Classify findings as BLOCKER, HIGH, MEDIUM, or LOW.
Repair only bounded BLOCKER and required HIGH findings.

When a finding requires changing a frozen contract, output ESCALATION_REQUIRED.

Otherwise state:
- Task accepted or not accepted
- whether the next Task may start
- which Stage gates remain pending

Update current Stage log and main implementation status.
Do not mark the Stage complete.
```

---

## 11.5 Parent 5.5：Contract Escalation Review

```text
Use the refactor-orchestrator skill.

This is a Contract Escalation Review using gpt-5.5.

Review only:
[Task ID and title]

Read:
- trade-strategy-ai/docs/AI-Conversation-Templates.md
- the frozen Stage implementation plan
- the current Task Card
- the ESCALATION_REQUIRED handoff
- current Stage log and main status
- current git status and complete diff
- only code and tests relevant to the reported conflict

Do not restart the entire Stage.
Do not perform unrelated implementation.
Do not discard safe completed work or user-owned changes.

Determine whether:
1. implementation may continue under the existing contract;
2. the Task Card needs clarification without a public-contract change;
3. the Stage contract must be revised;
4. an upstream Task must be reopened;
5. the Stage must be marked BLOCKED.

When revising a contract:
- state the old contract
- state the new contract
- explain the evidence and reason
- list affected Tasks
- list evidence invalidated by the change
- update the Stage implementation plan
- update the current Stage log
- update Refactor-Implementation-Log.md
- issue a revised bounded Task Card for gpt-5.4

Do not continue broad implementation unless a small bounded change is required
to validate the revised contract.

Conclude exactly one:
- RESUME_WITH_GPT_5_4
- REOPEN_UPSTREAM_TASK
- BLOCKED

Return:
- escalation decision
- revised contracts, if any
- invalidated evidence
- required rework
- updated Task Card
- next model and action
```

---

## 11.6 Parent 5.5：Stage Gate Review

```text
Use the refactor-orchestrator skill.

Use the gpt-5.5 Parent as final Stage reviewer.
Do not delegate final acceptance.
Do not start the next Stage.

Strictly review:
[Stage ID and title]

Read:
- authoritative Stage requirements
- trade-strategy-ai/docs/AI-Conversation-Templates.md
- frozen Stage implementation plan
- Refactor-Implementation-Log.md
- complete current Stage log
- accepted Task handoffs
- complete Stage diff
- current repository state
- existing verification evidence

Verify:
- all Stage Tasks are actually complete
- implementation matches frozen contracts
- frontend, backend, database, API, and runtime contracts agree
- no second official entry point, Schema, or fact source exists
- no later-Stage behavior was improperly introduced
- data and user-visible states are truthful
- migrations and rollback/safe-rerun are verified when applicable
- point-in-time semantics are correct when applicable
- compatibility and retirement conditions are satisfied
- implementation logs match runtime truth
- user-owned unrelated changes were preserved

Run or verify each applicable gate:
- affected backend tests
- affected frontend tests
- applicable typecheck
- applicable lint
- applicable build
- migration and rollback/safe-rerun
- affected critical E2E journeys
- compatibility/retirement checks
- git diff --check
- documentation and implementation-log consistency

Do not rerun checks when reliable evidence covers the final diff and no relevant
code changed afterward. Record evidence reuse or why a check is not applicable.

UI acceptance:
- ordinary localized UI changes do not require full desktop/mobile inspection
- automated tests verify behavior, routes, permissions, truthful states, and key
  interactions
- for global navigation/layout/design system/homepage/primary journey/
  delivery-critical changes, create or update:
  trade-strategy-ai/docs/ui-acceptance/stage-<n>-ui-checklist.md
- do not claim user visual approval
- non-blocking visual polish is MEDIUM/LOW follow-up

Classify findings:
- BLOCKER
- HIGH
- MEDIUM
- LOW

Repair only bounded BLOCKER or required HIGH issues that do not require a new
architecture decision.

Conclude exactly one:
- ACCEPTED: next Stage may begin
- CONDITIONAL: list required remaining gates
- BLOCKED: list blockers and remediation

Update:
- current stage-<n>.md
- Refactor-Implementation-Log.md

Do not continue automatically.
```

---

## 11.7 New Session Recovery

```text
Use the refactor-orchestrator skill.

Do not infer progress from chat memory.

Read:
- AGENTS.md
- trade-strategy-ai/AGENTS.md
- trade-strategy-ai/docs/AI-Conversation-Templates.md
- authoritative TaskList
- current Stage plan
- Refactor-Implementation-Log.md
- current stage-<n>.md
- available handoffs
- current branch, baseline, git status, and complete diff

Treat prior runtime and completion claims as unverified without evidence.

Report:
- current Stage and Task
- accepted work
- incomplete work
- blockers
- dirty changes and ownership
- current frozen contracts
- next smallest safe action
- recommended Parent model

Do not implement until actual status is established.
```

---

# 12. Stage 2 可直接使用的示例

Stage 2 是当前下一步，推荐：

```text
1. gpt-5.5：Bootstrap 和冻结契约
2. gpt-5.4：RT-S2-001
3. gpt-5.4：RT-S2-002
4. gpt-5.4：RT-S2-003
5. gpt-5.5：Stage 2 Gate
```

## 12.1 Stage 2 Bootstrap

将通用 Bootstrap 中的范围替换为：

```text
Analyze and prepare only:

Stage 2: Domain Models, Database, and Version Contracts
- RT-S2-001 Define core domain objects
- RT-S2-002 Refactor the database
- RT-S2-003 Migrate existing data
```

额外要求冻结：

```text
- authoritative core domain object list
- object responsibilities and ownership
- stable ID rules
- version relationships
- draft/review/publish/archive/active semantics
- official fact sources
- database tables and relationships
- API and DTO boundaries affected by Stage 2
- Prompt raw-output and version metadata storage
- old-object to new-object mappings
- migration order and quality-state rules
- rollback or safe-rerun
- compatibility boundaries
- explicit later-Stage deferrals
```

输出文件：

```text
trade-strategy-ai/docs/refactor-implementation-plans/stage-2-implementation-plan.md
trade-strategy-ai/docs/refactor-implementation-logs/stage-2.md
```

## 12.2 RT-S2-001

使用通用 Parent 5.4 Task Prompt，范围替换为：

```text
Execute only:
RT-S2-001 Define core domain objects
```

额外停止条件：

```text
- a frozen core object must change
- stable ID or version semantics are insufficient
- the current database cannot support the contract without redesign
- more than one official fact source would remain
- a public API or migration decision is not covered by the plan
```

## 12.3 RT-S2-002 专项验证

```text
- migration upgrade
- rollback or documented safe-rerun
- indexes and constraints
- affected repository/API tests
```

## 12.4 RT-S2-003 专项验证

```text
- migration report
- quality status for incomplete records
- repeat execution
- failure recovery
- no silent data loss
```

## 12.5 Stage 2 Gate 重点

```text
- RT-S2-001～003 complete
- domain/database/API schemas agree
- stable IDs and version relationships consistent
- one official fact source
- no file path as formal business identifier
- Prompt metadata preserved when applicable
- migration traceable
- incomplete data has quality state
- rollback or safe-rerun verified
- no Stage 3 behavior introduced
```

---

# 13. 工作区与日志保护

每个 Task 开始前必须检查：

```bash
git status
git diff
```

区分：

- 当前 Task 修改；
- 前一 Task 已接受修改；
- 用户已有修改；
- 来源不明修改。

不得：

- 擅自覆盖用户已有差异；
- 为了清理工作区执行破坏性回退；
- 格式化不相关文件；
- 把未知修改归因于当前 Agent。

日志职责：

```text
详细实现和证据
→ refactor-implementation-logs/stage-<n>.md

当前状态、阻塞、下一步和索引
→ Refactor-Implementation-Log.md
```

---

# 14. 使用方法摘要

## 新 Stage 开始

```bash
codex -m gpt-5.5
```

复制“Stage Bootstrap”模板。

## 执行普通 Task

```bash
codex -m gpt-5.4
```

复制“Task 实现”模板。

## 同 Stage 继续

继续当前 5.4 Session 或新建 5.4 Session，复制“Same-Stage Continuation”。

## 出现升级

Parent 5.4 输出：

```text
ESCALATION_REQUIRED
```

用户切换：

```bash
codex -m gpt-5.5
```

复制“Contract Escalation Review”。

5.5 输出：

```text
RESUME_WITH_GPT_5_4
```

后再切回 5.4。

## Stage 完成

```bash
codex -m gpt-5.5
```

复制“Stage Gate Review”。

只有输出：

```text
ACCEPTED: next Stage may begin
```

才允许进入下一 Stage。

---

# 15. 核心原则

```text
Stage 级：
5.5 开始，5.5 结束

Task 级：
默认 5.4，按收益决定是否使用 mini

升级：
由 Parent 5.4 自动判断门禁
用户只负责切换模型或作产品决策

验证：
局部和专项验证在 Task
整体集成验收在 Stage Gate

事实：
只相信实际 diff、测试、迁移和运行证据

上下文：
只读取当前任务必要内容
不让子 Agent 重读所有全局文档
```
