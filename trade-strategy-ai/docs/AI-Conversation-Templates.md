# Trade Strategy AI 重构对话模板与 Stage Gate 执行协议

> 仓库唯一 AI 执行入口：`trade-strategy-ai/docs/AI-Conversation-Templates.md`
>
> 本文档合并并替代：
>
> - 原 `AI-Conversation-Templates.md`
> - `AI-Conversation-Templates-unified.md`
> - `AI-Conversation-Stage-Gate-Addendum.md`
>
> 合并后，后两份文档应归档或删除，避免形成第二套执行规则。

---

## 1. 权威边界

### 1.1 文档职责

- `Trade-Refactor-TaskList.md`：业务范围、Stage/Task 和验收要求。
- `refactor-implementation-plans/stage-<n>-implementation-plan.md`：当前 Stage 已冻结的共享契约和 Task Card。
- 本文档：模型分工、上下文、委派、升级、验证和 Gate 协议。
- `Refactor-Implementation-Log.md`：当前状态、阻塞、下一步和索引。
- `refactor-implementation-logs/stage-<n>.md`：详细实现、测试和 Gate 证据。
- 代码、数据库、运行结果和最终 diff：当前事实证据，但不得被用来静默改变冻结契约。

发生冲突时：

1. 先核对实际仓库、数据库和运行事实；
2. 不得按聊天记忆猜测；
3. 在冻结契约内可修的问题进入有界修复；
4. 需要改变冻结契约的问题必须 `ESCALATION_REQUIRED`。

### 1.2 必须保留的辅助文档

```text
trade-strategy-ai/docs/AI-Conversation-Project-Constraints-1.md
trade-strategy-ai/docs/AI-Conversation-Project-Constraints-2.md
trade-strategy-ai/docs/AI-Conversation-Task-Matrix.md
trade-strategy-ai/docs/Trade-Refactor-TaskList.md
trade-strategy-ai/docs/Refactor-Implementation-Log.md
trade-strategy-ai/docs/refactor-implementation-plans/
trade-strategy-ai/docs/refactor-implementation-logs/
```

只读取当前任务所需内容：

- Project Constraints：通常只给 Parent/subagent 1～2 个相关约束块；
- Task Matrix：仅在判断 Task 是否可组合时读取；
- 不得把全部约束库、历史日志和无关 Stage 文档发送给 subagent。

---

## 2. 标准执行流程

```text
Stage Bootstrap（Parent gpt-5.5）
→ 冻结契约和 Task Cards
→ Task Implementation + Task Review（Parent gpt-5.4）
→ 必要时 Contract Escalation（Parent gpt-5.5）
→ Stage Gate + 有界自动修复（Parent gpt-5.5）
→ ACCEPTED 后进入下一 Stage
```

默认额度结构：

```text
一次 5.5 Bootstrap
→ 多个 5.4 Task Session
→ 一次 5.5 Stage Gate
```

规则：

- Stage 未明确 `ACCEPTED`，不得进入下一 Stage。
- Stage 2～11 使用完整模式；Stage 12 使用交付变体，但仍必须执行 Bootstrap、Task Review 和最终 Gate。
- Task 接受不等于 Stage 接受。
- Parent 不能自行切换模型；输出升级 handoff 后由用户切换 Session/模型。
- 不自动开始下一 Task 或下一 Stage。
- 最终 Stage Gate 判断不得委派。

---

## 3. 模型、风险与委派

### 3.1 风险级别

| 级别 | 典型范围 | 默认模式 |
|---|---|---|
| M1 | 局部文案、单组件、已定位 Bug、小测试、日志、枚举映射 | Parent 5.4，通常 0 subagent |
| M2 | 契约已冻结的页面、Service、聚合接口、状态机、调度页 | Parent 5.4，0～1 mini Executor |
| M3 | 核心模型、Schema/migration、事实源、时间语义、正式资产、退役 | 5.5 冻结，5.4 实现和专项验证，5.5 Gate |

### 3.2 Agent 预算

```text
小 Task：0
普通 Task：0～1 个 `gpt-5.4-mini` Executor
两个完全独立且不重叠的写入任务：最多 2 Executor
大型只读审计：最多 2～3 Explorer
Stage Gate 有界修复：最多 1 mini Executor
```

`0` 个 subagent 是正常结果。

已知文件、所有权和调用链时，不创建 Explorer。不要默认把实现、测试、lint 拆成多个 Agent。

### 3.3 可委派

- 全仓引用和调用链调查；
- 边界明确的局部前端/后端实现；
- focused tests；
- 机械字段迁移、引用清理；
- 测试失败摘要。

### 3.4 不可委派

- 核心领域模型和正式事实源决策；
- 冻结 Schema、migration/rollback 或 point-in-time 语义；
- writer ownership、dual-write、cutover 模型；
- 正式规则、画像或策略发布语义；
- 是否删除旧入口；
- Task/Stage 最终验收。

### 3.5 Task Card 最小字段

```text
Task ID / 目标
当前事实
冻结契约
允许路径 / 禁止路径
明确输出
focused tests / 专项验证
完成条件
停止条件
升级条件
```

---

## 4. 上下文加载

### 4.1 Stage Bootstrap

Parent 读取：

1. `AGENTS.md`
2. `trade-strategy-ai/AGENTS.md`
3. 本文档
4. 权威 TaskList 和完整重构方案
5. 主实施日志和当前 Stage 日志
6. 当前 Stage 直接相关文档
7. 当前分支、基线、`git status`、完整 diff
8. 相关代码、测试、API、数据库、migration 和运行入口

Prompt、文章或作者画像文档只在当前 Stage 实际修改它们时读取。

### 4.2 Same-Stage Task

只读取：

- 当前 Task 和 Task Card；
- 当前 Stage 冻结契约；
- 主日志的新状态、Stage 日志新增条目和上游 handoff；
- 当前 `git status`、完整 diff、相关代码和测试；
- 1～2 个直接相关约束块。

全局文档仅在已变化、冲突、事实不确定或当前 Task 要改变公共契约时重读。

### 4.3 New Session Recovery

- 不根据聊天记忆推断完成状态；
- 以日志、工作区、diff、测试和运行证据为准；
- 先报告当前 Stage/Task、已接受工作、未完成工作、阻塞、dirty changes、冻结契约和下一安全动作；
- 状态未建立前不得实施。

---

## 5. 冻结契约与自动升级

### 5.1 Parent 5.4 检查时点

必须在以下时点检查升级门禁：

1. Task 开始前；
2. 调查完成、写入前；
3. 仓库事实与 Task Card 不一致时；
4. Task Review 前。

### 5.2 命中任一条件必须暂停

- 需要改变核心对象、稳定 ID、版本关系或生命周期；
- 需要改变 Schema、migration 策略、公共 API/DTO；
- 需要改变正式事实源或 writer ownership；
- rollback/safe-rerun 无法满足冻结方案；
- point-in-time、未来数据泄漏或数据可用时间不明确；
- 需要改变正式规则、画像、策略发布或人工审批语义；
- 自动建议可能覆盖正式资产；
- 删除范围、兼容边界或恢复方案不清；
- 文档、Task Card 与运行事实冲突且正确合同不明确；
- 必须跨 Task/Stage 或引入后续 Stage 行为才能解决；
- mini 连续两轮不能按 Task Card 完成；
- 出现第二套正式 Schema、事实源、writer 或 Alembic branch；
- 无法判断当前 Task 是否符合 Stage 目标；
- 修改将使关键验收证据失效，且计划未覆盖；
- 需要破坏性迁移，但现有恢复合同不足。

### 5.3 强制动作

- 停止相关风险写入；
- 保留工作区和安全完成的工作；
- 不覆盖用户修改，不做破坏性回退；
- 更新 Stage 日志；
- 输出：

```text
ESCALATION_REQUIRED

Task:
Trigger:
Evidence:
Affected frozen contracts:
Safe work completed:
Current working tree:
Decision required from gpt-5.5:
Recommended next action:
```

Parent 5.4 不得自行修改冻结契约或继续相关实现。

---

## 6. Canonical Writer 永久收敛规则

### 6.1 Stage 2 接受后的基线

当 Stage 2 Gate 为 `ACCEPTED` 后：

- `STAGE2_CANONICAL_WRITER_ENABLED` 在所有环境中必须视为 `true`；
- Application Service → canonical repository → canonical PostgreSQL database 是唯一正式写入链；
- legacy writer 不再权威；
- 不允许 dual-write；
- Stage 3 Bootstrap 必须验证该基线；
- Stage 3+ 的所有 Task、Review 和 Gate 自动继承本规则；
- 涉及 writer、migration、cutover 或兼容路径的 Task Card 必须再次明确本规则。

若仍存在两个正式 writer 或 dual-write，Stage 3 必须 `BLOCKED`。

### 6.2 `false` 的严格限制

`STAGE2_CANONICAL_WRITER_ENABLED=false` 仅允许作为**生产事故紧急回滚**，且必须同时满足：

- 已发生生产事故；
- canonical writer 正在造成系统故障或数据损坏；
- 有明确操作授权；
- 定义了限时回滚窗口；
- 已记录恢复计划和恢复截止时间。

禁止用于：

- 测试绕过；
- legacy 兼容；
- 部分迁移；
- 开发便利；
- 普通故障规避；
- 长期双轨运行。

启用 `false` 后必须：

- 记录事故、影响和授权；
- 隔离冲突 writer；
- 规定恢复 deadline；
- 尽快恢复为 `true`；
- 补做数据一致性和修复验证。

### 6.3 最终 Stage 退役

Stage 12 必须：

- 删除该环境变量；
- 删除 `false` 分支和 transitional guard；
- 删除 legacy writer/兼容写入路径；
- 把 canonical writer 变为不可配置的永久约束；
- 确保系统正确性不再依赖 feature flag。

---

## 7. Task 验证与 Review

### 7.1 普通 Task

默认运行：

- focused tests；
- 直接受影响回归；
- 一个必要静态检查；
- `git diff --check`。

### 7.2 高风险 Task 必须在当前 Task 内验证

不得全部推迟到 Stage Gate：

- migration / rollback / safe-rerun；
- 安全和权限；
- point-in-time；
- 正式事实源和 single-writer；
- destructive deletion；
- 缓存失效；
- 幂等、失败恢复和发布回滚；
- 正式资产不会被自动覆盖。

### 7.3 Task Review

Parent 必须检查最终 diff：

- 满足 Task 要求和冻结契约；
- 无第二事实源、Schema 或 writer；
- 兼容边界和数据状态真实；
- 未越界实现其他 Task/Stage；
- 文档、日志和运行事实一致；
- 用户已有修改被保留；
- 未命中升级条件。

发现分级：

```text
BLOCKER / HIGH / MEDIUM / LOW
```

只修复当前 Task 范围内、有界且不改变冻结契约的 BLOCKER/必要 HIGH。否则升级。

Task 结束必须说明：

- Task 是否接受；
- 下一 Task 是否可开始；
- 仍待完成的 Stage Gate；
- 已更新的日志。

不得标记 Stage 完成。

### 7.4 版本化数据来源与不可用状态

任何绑定到所选历史版本的字段都必须证明来自该版本：

- 优先使用该版本自身冻结的数据；
- 仅当当前记录与所选版本的稳定 ID、版本 ID 或内容 hash 明确一致时，才可使用当前记录中的值；
- 无法证明版本对齐时，必须返回 `unavailable`、`null` 或明确的部分可用状态；
- 不得使用最新记录替代旧版本数据，不得猜测、无证据回填或静默降级为成功；
- UI、API、Service、回归 fixture 和日志必须分别记录并验证字段来源与版本对齐；
- `unavailable` 是合法、可测试的真实状态，不得仅为通过测试而伪造历史值。

本文规则适用于文章摘要、结构化分析、规则解释、作者画像、市场状态、策略版本及其他版本化业务数据。

---

## 8. Stage Gate 有界自动修复

### 8.1 Gate 流程

```text
Review
→ 分类 findings
→ 有界修复
→ 重跑受影响证据
→ 从最终状态完整 Re-Review
→ Gate 决策
```

该机制不降低验收标准。Review 必须确定、可复现；不得隐藏修复，所有修复必须记录为明确的 Repair Task Card；不得静默改合同。

### 8.2 `AUTO_REPAIRABLE`

冻结契约内可修：

- 普通实现 Bug；
- repository、adapter、application-service routing 缺陷；
- 已冻结字段、FK、索引、约束或 metadata 漏实现；
- 测试、验证、backup manifest、日志或明确事实的文档缺失；
- legacy writer 未按已冻结 single-writer 合同被限制；
- 已冻结 feature flag/cutover guard 未接入真实运行路径；
- 不改变事实源、Schema 设计或数据解释的兼容修复。

当合同已明确：

```text
Application Service
→ canonical repository
→ canonical PostgreSQL database
```

而代码仍有 router、CLI、Job、Workflow 绕过服务层，或 guard/测试缺失，属于 `AUTO_REPAIRABLE`，不是自动升级理由。

### 8.3 `CONTRACT_SENSITIVE`

必须 `ESCALATION_REQUIRED`：

- 需要改变核心对象、ID、版本、生命周期；
- 需要重新设计 Schema、migration、rollback；
- 需要重新决定事实源、writer ownership 或 dual-write；
- 需要重新解释历史数据、正式状态或人工审批语义；
- 破坏性迁移超出现有恢复合同；
- 必须跨 Stage 或引入后续 Stage 行为；
- 修复会形成第二套正式 Schema、事实源、writer 或 migration branch。

### 8.4 Repair Task Card

```text
Owning Task
Finding / evidence / root cause
Frozen contracts
Allowed / forbidden paths
Exact minimal repair
Focused tests / specialized verification
Completion conditions
Stop / escalation conditions
```

Parent 5.5 必须：

1. 标注 owning Task；
2. 创建 Repair Task Card；
3. 保持冻结契约不变；
4. 实施最小修复；
5. 检查完整 repair diff；
6. 重跑直接影响的测试、专项验证和 Gate 证据；
7. 更新 Stage 日志和主日志；
8. 从修复后的最终状态重新执行完整 Gate Review。

不得仅因存在可修实现项就返回 handoff、`CONDITIONAL` 或 `BLOCKED`。

修复循环停止于：

- 所有 Gate 通过；
- 只剩不阻塞下一 Stage 的外部证据限制；
- 命中合同升级、真实外部 blocker 或修复失败。

### 8.5 委派限制

- final Gate 判断不可委派；
- Parent 5.5 负责分类、范围、合同合规、最终 diff 和决策；
- 最多 1 个 mini Executor 做机械且不重叠的修复；
- 不允许多个 writer 同时改 ORM、migration chain/state 或 canonical contract。

### 8.6 修复后证据

最终决策必须基于修复后的代码、数据库、配置和日志。

旧证据只有在以下全部满足时可复用：

- 修复未影响对应路径或结构；
- fixture、Schema、migration、运行配置未变；
- 证据覆盖最终 diff；
- 日志记录复用理由。

否则必须重跑。

### 8.7 Gate 决策

#### ACCEPTED

- 所有 material findings 已修复并验证；
- Stage 出口条件全部通过；
- 无合同级风险；
- 日志与运行事实一致；
- 下一 Stage 可开始。

#### CONDITIONAL

仅限：

- 剩余项依赖当前环境无法获得的外部证据；
- 不影响架构、数据完整性、迁移安全或下一 Stage；
- 明确限制、责任、补证方法和下一 Stage 是否阻塞。

不得因仍有可修实现工作而使用。

#### BLOCKED

- 有 material defect 未修；
- 修复失败；
- 数据完整性、兼容、恢复或 writer enforcement 不满足；
- 下一 Stage 不得开始。

#### ESCALATION_REQUIRED

仅在必须改变冻结契约或作新的高风险决定时使用。

---

## 9. Stage Gate 验证

运行或验证所有适用项：

- 受影响 backend/frontend tests；
- typecheck、lint、build；
- migration upgrade、rollback 或 safe-rerun；
- 受影响关键业务 E2E；
- compatibility/retirement checks；
- point-in-time 和正式事实源；
- `git diff --check`；
- TaskList、实现、主日志和 Stage 日志一致性。

每个未运行项必须记录：

- 不适用；或
- 哪个可靠证据覆盖最终 diff。

测试日志只保留：

```text
命令
通过/失败数量
失败测试名称
核心错误
相关文件
是否影响冻结契约
```

仅在定位时读取失败附近的详细日志。

---

## 10. UI 验收

普通局部 UI Task：

- 不做完整 desktop/mobile 视觉遍历；
- 不要求用户逐 Task 批准；
- 自动验证行为、路由、权限、真实数据状态和关键交互。

以下变化在 Stage Gate 创建或更新：

```text
trade-strategy-ai/docs/ui-acceptance/stage-<n>-ui-checklist.md
```

适用于：

- 全局导航、布局或设计系统；
- 首页；
- 主要用户旅程；
- 交付关键页面。

Checklist 只覆盖代表性页面、必要 viewport、核心路径和人工观察项。

Agent 不得代替用户声明主观视觉验收通过。轻微间距、颜色、字体和响应式 polish 记为 MEDIUM/LOW follow-up，不作为代码 blocker。

---

## 11. 各 Stage 特殊约束

| Stage / Task | 必须注意 |
|---|---|
| S2-001 | 对象边界、稳定 ID、版本关系、生命周期、唯一事实源；不提前实现后续业务 |
| S2-002 | 表、FK、唯一约束、索引、Prompt 原始输出；验证 migration/rollback 或 safe-rerun |
| S2-003 | 不静默丢旧数据；质量状态、迁移报告、重复执行和失败恢复 |
| S3-001 | Prompt、Schema、调用编排版本化；事实与推断分离 |
| S3-002 | 原文、证据、缺失项、可回测性和 Kaipan 依赖可见 |
| S3-003 | 先固定 10～15 篇样本；通过前不得全量重跑 |
| S3-004 | 对照、Schema 映射、观察期、回滚、全仓无引用后才能删除旧 Prompt |
| S4-001 | 自动通过仅表示可进入待回测；正式使用仍需门禁和人工确认 |
| S4-002 | 指纹确定性和版本化；区分重复、参数变体和冲突 |
| S4-003 | 状态转换集中管理 |
| S5-001 | DatasetSnapshot 固定回测数据；补抓不得静默改变历史结果 |
| S5-002 | 区分盘前/盘后 slot；缺失不得当作条件 false |
| S5-003 | 时区、交易日、幂等、失败重试和重复调度 |
| S6-001 | UI 参数与运行契约一致；自动检查数据依赖 |
| S6-002 | 严禁未来数据泄漏；固定市场状态模型版本 |
| S6-003 | 样本量、收益、胜率、回撤、置信度、推荐状态分开 |
| S6-004 | 固定 Level 1/2/3 数据要求和降级语义 |
| S7-001 | 只描述文章方法，不声称真实实盘结果 |
| S7-002 | 程序统计与 LLM 解释分区保存 |
| S7-003 | 只基于回测和每日证据；显示样本量和覆盖率 |
| S7-004 | 新数据只生成草稿，不覆盖正式画像 |
| S8-001 | 规则池、权重、画像、风险和仓位全部绑定版本 |
| S8-002 | 样本外验证、比较、发布、回滚闭环 |
| S8-003 | 只能生成 Proposal，不能直接修改正式策略 |
| S9-001 | 明确 ready/degraded/blocked |
| S9-002 | 选择优先级确定性；正式适用性优先 |
| S9-003 | 每日对象是运行实例，不是新正式策略 |
| S10-001 | 冻结触发、执行、收益、MFE、MAE 口径 |
| S10-002 | 程序事实优先；LLM 仅条件触发解释 |
| S10-003 | Rule、Profile、Strategy Proposal 分离 |
| S10-004 | 页面使用业务中文 |
| S11-001 | 业务与管理员入口分离 |
| S11-002 | 定时、重试、断点续跑、批处理恢复必须幂等 |
| S11-003 | 统一稳定 run_id，支持跨系统追溯 |
| S11-004 | 缓存失效、并发限制、重试上限和预算 |
| S11-005 | 统一 trade_date/available_at/captured_at/effective_at/source/slot |
| S11-006 | 对照→只读→小范围→默认→旧只读→退役 |
| S11-007 | 错误说明发生了什么、影响什么、怎么处理 |
| S12-001 | 全仓引用、兼容读取、只读阶段和恢复方案完成后才删除 |
| S12-002 | 走通文章→规则→回测→画像→策略→盘前→盘后 |
| S12-003 | 文档必须与最终真实 UI、权限和流程一致 |

补充禁止项：

- S3：新旧 Prompt 不得同时产生正式数据；repair 不得成为常规第二次 LLM 调用；作者画像不得逐篇生成；样本回归通过前不得处理 100+ 篇文章。
- S11 最高风险：S11-002、S11-005、S11-006。
- S12 最终验收不得委派。
- Stage 12 Bootstrap 只冻结删除范围、兼容读取、最终 E2E、交付文档、正式版本和恢复方案，不重新设计架构。

---

## 12. 可复制 Prompt

### 12.1 Stage Bootstrap — Parent gpt-5.5

```text
Use the refactor-orchestrator skill.
Choose and spawn subagents according to the Skill rules.

This is a gpt-5.5 Stage Bootstrap and contract-freezing session.
Work from the Trade repository root.

Prepare only:
[Stage ID, title, Task list]

Do not implement the full Stage or start the next Stage.

Read the required AGENTS files, AI-Conversation-Templates.md, authoritative
TaskList/plan, main and Stage logs, current branch/status/complete diff, and only
the Stage-related code, tests, API, database, migrations, runtime and documents.

First verify:
- previous Stage is explicitly ACCEPTED
- actual working tree and user-owned changes
- current official fact sources and reusable implementation
- documentation/runtime conflicts
- for Stage 3+, canonical writer is active and no dual-write exists

Then:
- classify Tasks M1/M2/M3
- freeze domain, Schema, API/DTO, states, permissions and fact sources
- freeze writer ownership, migration/rollback, compatibility and retirement
- freeze point-in-time semantics when applicable
- define Task order, allowed/forbidden paths, verification and escalation
- identify later-Stage behavior that is out of scope
- create/update the Stage plan and Stage log with bounded Task Cards

Do not spawn broad implementation Executors during Bootstrap.
Return only:
delegation; verified facts; frozen contracts; Task order/cards; gates;
risks/blockers; files updated; next executable Task.
```

### 12.2 Task Implementation + Review — Parent gpt-5.4

```text
Use the refactor-orchestrator skill.
Choose and spawn subagents according to the Skill rules.

Within [Stage ID], execute only:
[Task ID and title]

Use AI-Conversation-Templates.md, the frozen Stage plan and current Task Card.
Read only current requirements/contracts, status deltas, Stage-log additions,
upstream handoff, git status/complete diff, related code/tests and 1–2 relevant
constraint blocks. Do not reread unchanged global documents.

Before writing:
- verify Task Card against the working tree
- classify M1/M2/M3
- run escalation preflight
- decide delegation explicitly; 0 subagents is valid
- use at most one mini Executor for an ordinary bounded Task
- for Stage 3+, enforce canonical writer; restate it when this Task touches
  writer, migration, cutover or compatibility

Implement only within allowed paths. Do not redesign frozen contracts or
implement another Task/Stage.

Verify:
focused tests; affected regressions; one necessary static check;
git diff --check; all current-Task high-risk checks.

Review the final diff for requirements, contracts, single fact source/writer,
compatibility, truthful states, scope, docs/logs and user-owned changes.
Repair only bounded BLOCKER/required HIGH findings within the contract.

If a contract/escalation condition is hit, stop and output ESCALATION_REQUIRED.
Otherwise update Stage/main logs and return only:
delegation; files changed; contract compliance; checks/results;
Task accepted or not; blockers; remaining Stage gates; next-Task permission;
concise handoff.

Do not mark the Stage complete or start another Task.
```

同 Stage 后续 Task 继续使用本模板，只读取增量状态和当前 Task 范围。

### 12.3 Contract Escalation Review — Parent gpt-5.5

```text
Use the refactor-orchestrator skill.

This is a gpt-5.5 Contract Escalation Review for:
[Task ID and title]

Read the frozen plan/Task Card, ESCALATION_REQUIRED handoff, current logs,
git status/complete diff, and only the conflicting code/tests.

Do not restart the Stage, discard safe work or do unrelated implementation.

Decide exactly one:
1. existing contract is sufficient;
2. Task Card only needs clarification;
3. Stage contract must change;
4. an upstream Task must reopen;
5. Stage is BLOCKED.

For a contract change, record old/new contract, evidence, affected Tasks,
invalidated evidence and required rework; update plan/logs and issue a revised
bounded Task Card.

Conclude exactly one:
RESUME_WITH_GPT_5_4
REOPEN_UPSTREAM_TASK
BLOCKED
```

### 12.4 Stage Gate + Bounded Repair — Parent gpt-5.5

```text
Use the refactor-orchestrator skill.
Choose and spawn subagents according to the Skill rules.

Use the gpt-5.5 Parent as final reviewer for:
[Stage ID and title]

Do not delegate final acceptance or start the next Stage.

Read authoritative Stage requirements, AI-Conversation-Templates.md, frozen
plan, complete Stage/main logs, accepted Task handoffs, complete Stage diff,
repository/database/runtime state and existing evidence.

Verify all Tasks, frozen contracts, frontend/backend/database/API/runtime
agreement, single official fact source/writer, scope, truthful states,
migration/recovery, point-in-time, compatibility/retirement, logs and
preservation of user changes. For Stage 3+, verify canonical writer is active;
for Stage 12, verify the switch and legacy writer paths are removed.

Run or verify every applicable test, typecheck, lint, build, migration/
rollback/safe-rerun, critical E2E, compatibility/retirement check,
git diff --check and document/log consistency. Record evidence reuse or N/A.

Classify findings as AUTO_REPAIRABLE or CONTRACT_SENSITIVE and by severity.

For AUTO_REPAIRABLE BLOCKER/required HIGH:
- create a bounded Repair Task Card tied to the owning Task
- keep contracts frozen
- make the minimum repair
- inspect repair diff
- rerun affected and invalidated evidence
- update logs
- repeat the complete Gate review from the repaired final state

Use at most one mini Executor for mechanical non-overlapping repair.
Never silently change contracts.
For CONTRACT_SENSITIVE findings, output ESCALATION_REQUIRED.

Conclude exactly one:
ACCEPTED: next Stage may begin
CONDITIONAL: external non-blocking evidence only
BLOCKED: material defects remain
ESCALATION_REQUIRED: frozen contract must change

Return:
delegation; verified facts; initial findings/classification; repairs by Task;
files changed; contract compliance; post-repair evidence; remaining findings;
final decision; next-Stage permission; logs updated; concise handoff.
```

### 12.5 New Session Recovery

```text
Use the refactor-orchestrator skill.

Do not infer progress from chat memory.

Read AGENTS files, AI-Conversation-Templates.md, authoritative TaskList,
current Stage plan, main/Stage logs, handoffs, current branch/baseline,
git status and complete diff.

Treat prior completion claims as unverified without evidence.

Report only:
current Stage/Task; accepted work; incomplete work; blockers;
dirty changes/ownership; frozen contracts; next smallest safe action;
recommended Parent model.

Do not implement until actual status is established.
```

---

## 13. 工作区和日志保护

每个 Task/Gate 开始前：

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

- 覆盖用户已有差异；
- 为清理工作区执行破坏性回退；
- 格式化无关文件；
- 把未知修改归因于当前 Agent。

日志职责：

```text
详细实现和证据
→ refactor-implementation-logs/stage-<n>.md

当前状态、阻塞、下一步和索引
→ Refactor-Implementation-Log.md
```

---

## 14. 使用顺序

```text
新 Stage：
codex -m gpt-5.5
→ 使用 Stage Bootstrap

普通/后续 Task：
codex -m gpt-5.4
→ 使用 Task Implementation + Review

出现 ESCALATION_REQUIRED：
codex -m gpt-5.5
→ 使用 Contract Escalation Review

Stage Tasks 全部完成：
codex -m gpt-5.5
→ 使用 Stage Gate + Bounded Repair
```

只有 Stage Gate 输出：

```text
ACCEPTED: next Stage may begin
```

才允许进入下一 Stage。

---

## 15. 不可违反的最终原则

```text
Stage：5.5 开始，5.5 结束
Task：默认 5.4，mini 按收益使用
升级：由 Parent 自动判断，用户只切换模型或作产品决策
验证：局部和高风险专项验证在 Task，完整集成验收在 Gate
修复：合同内问题必须有界修复，合同变化必须升级
写入：Stage 3+ 只允许 canonical writer，不允许 dual-write
事实：只相信最终 diff、测试、migration、数据库和运行证据
上下文：只读取当前任务必要内容
保护：不得覆盖用户修改或静默改变冻结契约
推进：没有明确 ACCEPTED，不进入下一 Stage
```
