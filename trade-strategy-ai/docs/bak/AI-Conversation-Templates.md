# Trade Strategy AI 重构对话模板

本文件保存可直接复制的 Orchestrator Prompt 和最小使用规则。项目约束和 Task 组合信息已拆分，避免每次加载无关内容。

## 1. 文件分工

- 当前模板：`trade-strategy-ai/docs/AI-Conversation-Templates.md`
- 项目约束 1：`trade-strategy-ai/docs/AI-Conversation-Project-Constraints-1.md`
- 项目约束 2：`trade-strategy-ai/docs/AI-Conversation-Project-Constraints-2.md`
- Task 组合与示例：`trade-strategy-ai/docs/AI-Conversation-Task-Matrix.md`
- 当前状态：`trade-strategy-ai/docs/Refactor-Implementation-Log.md`
- 当前 Stage 详细日志：`trade-strategy-ai/docs/refactor-implementation-logs/stage-<n>.md`

每个 Task 只读取当前模板、当前状态、当前 Stage 日志和 1～2 个相关约束。不要把两个约束库和 Task Matrix 整体加载到子 Agent 上下文。

## 2. 上下文模式

### Stage Bootstrap

用于新 Session、新 Stage、上下文不确定、公共契约变化或工作区出现来源不明修改。

Parent 读取：

1. `AGENTS.md`
2. `trade-strategy-ai/AGENTS.md`
3. `trade-strategy-ai/docs/Trade-Refactor-TaskList.md`
4. `trade-strategy-ai/docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`
5. `trade-strategy-ai/docs/Refactor-Implementation-Log.md`
6. 当前 `refactor-implementation-logs/stage-<n>.md`
7. 当前 Stage/Task 的直接设计、迁移和验收文档
8. 当前分支、基线、`git status`、完整 diff、相关代码、测试、数据库和 API

Prompt、文章和作者画像文档只在对应 Stage 实际使用时读取。

### Same-Stage Continuation

同一个 Parent Session 内继续同一 Stage 时，只读取：

- 当前 Task 要求；
- 主实施日志的新状态；
- 当前 Stage 日志新增条目；
- 上游 handoff 和冻结契约；
- 当前 diff、相关代码和测试。

全局文档仅在变化、冲突、不确定或修改共享契约时重读。

## 3. 委派与验证预算

- 普通任务：0～1 个 subagent。
- 独立且不重叠的实现：最多 2 个 Executor。
- 大型只读审计：最多 3 个 Explorer。
- 已知文件、调用链和所有权时，不创建 Explorer。
- M1：Parent 直接执行或 1 个 Executor。
- M2：Parent 冻结契约后，默认 1 个 Executor。
- M3：Parent 主导，mini 只做严格限定支持。

普通 Task 默认运行：

- focused tests；
- 直接受影响回归；
- 一个必要静态检查；
- `git diff --check`。

迁移、安全、权限、point-in-time、中心事实源和 destructive deletion 必须在当前 Task 内完成专项验证。

## 4. Stage Gate 与 UI 验收

Stage Gate 只运行适用于最终 diff 的检查。可靠证据覆盖最终 diff，且之后相关代码未变化时，可以复用，不要重复执行。

默认检查：

- 受影响的前后端测试；
- 适用的 typecheck、lint、build；
- 涉及数据或 Schema 时的 migration/rollback；
- 受影响关键业务路径的 E2E；
- 适用的 compatibility/retirement gate；
- `git diff --check`；
- 实现、主日志和当前 Stage 日志一致性。

UI 规则：

- 普通局部 UI Task 不做完整桌面/移动视觉遍历，也不要求用户逐 Task 批准。
- 自动测试继续验证行为、路由、权限、真实数据状态和关键交互。
- 修改全局导航、全局布局/设计系统、首页、主要用户旅程或交付关键页面时，生成或更新：
  `trade-strategy-ai/docs/ui-acceptance/stage-<n>-ui-checklist.md`
- 清单只包含代表性关键页面、必要 viewport、核心路径和人工观察项。
- Agent 不代替用户声明视觉通过。
- 轻微间距、颜色、字体和响应式 polish 记为 MEDIUM/LOW follow-up，不阻塞 Stage。
- 缺少人工批准只有在权威 Stage 出口条件明确要求时才保持 pending；不得误报为代码 BLOCKER。
- 每个跳过项说明“不适用”或“已有证据覆盖”。

## 5. Stage Bootstrap Prompt

```text
Use the refactor-orchestrator skill.

Explicitly decide whether delegation is justified under the Skill rules.
If justified, explicitly spawn the selected configured subagent or subagents.
If not justified, proceed with the Parent only and record that zero subagents
were selected.

Work from the Trade repository root.
Execute only:
[Stage ID / Task ID / title]

Parent must read:
- AGENTS.md
- trade-strategy-ai/AGENTS.md
- Trade-Refactor-TaskList.md and the current Stage plan
- Refactor-Implementation-Log.md
- current refactor-implementation-logs/stage-<n>.md
- exact current Stage/Task documents: [paths]
- current branch, baseline, git status, complete diff, related code/tests/data/API

Read Prompt/author-profile documents only when this Stage actually changes them.
Do not read unrelated Stage documents.

Before implementation:
- verify prerequisites and actual status
- classify M1/M2/M3
- freeze applicable public contracts, Schema, API, permissions, migration,
  rollback, compatibility, and verification commands
- apply delegation eligibility and benefit gates
- do not spawn Explorer when files and call chains are known
- give children only bounded Task Cards and scoped context

Apply only these project constraints:
[paste 1–2 relevant blocks from the constraint files]

Verification:
- ordinary Task: focused tests, affected regressions, one static check,
  git diff --check
- high-risk Task: run its specialized verification now
- defer full suites and broad UI acceptance to the Stage Gate

Update records:
- details → current stage-<n>.md
- current status/blockers/next step/index → Refactor-Implementation-Log.md

Do not start the next Task or Stage.
Return only delegation, files changed, checks/results, blockers, and handoff.
```

## 6. Same-Stage Continuation Prompt

```text
Use the refactor-orchestrator skill.

Continue within the current Stage using the established context.
Execute only:
[Task ID and title]

Read only:
- current Task requirements
- current-status changes in Refactor-Implementation-Log.md
- new entries in current stage-<n>.md
- upstream contracts/handoff
- current git status, diff, related code and tests

Do not reread unchanged global documents.
Reread them only when changed, conflicting, uncertain, or when this Task changes
a shared public contract.

Explicitly decide whether delegation is justified.
Zero subagents is valid.
Do not spawn Explorer when files, call chains, and ownership are known.

Apply only these project constraints:
[paste 1–2 relevant blocks]

Verification:
- focused tests
- affected regressions
- one necessary static check
- git diff --check
- defer broad checks to Stage Gate unless a high-risk shared contract changed

Update records:
- details → current stage-<n>.md
- current status/blockers/next step/index → Refactor-Implementation-Log.md

Return only delegation, files changed, checks/results, blockers, and handoff.
```

## 7. Task Review Prompt

```text
Use the refactor-orchestrator skill.
Use the Parent as final reviewer.

Review only:
[Task ID and title]

Do not start the next Task or Stage.

Read only Task acceptance requirements, current status, current Stage entries for
this Task, upstream contracts/handoff, current Task diff, affected files/tests.

Check requirements, frozen contracts, fact-source uniqueness, compatibility,
scope, truthful data states, no later-Task work, and documentation accuracy.

Run or verify:
- focused tests
- one required static check
- git diff --check

Reuse evidence only when it covers the final Task diff and no relevant code
changed afterward. Run specialized verification for migration, security,
time semantics, central fact sources, or deletion.

For ordinary UI Tasks:
- verify behavior, routing, permissions, data states, and key interactions with
  automated tests
- do not require separate desktop/mobile visual inspection or user approval
- defer any manual UI checklist to Stage Gate

Classify findings as BLOCKER, HIGH, MEDIUM, or LOW.
Repair only BLOCKER and required HIGH findings.

State whether the Task is accepted, whether the next Task may start, and which
Stage gates remain pending.

Append details to stage-<n>.md.
Update the main implementation log only with current status and next step.
Do not mark the Stage complete.
```

## 8. Stage Gate Review Prompt

```text
Use the refactor-orchestrator skill.
Use the Parent as final reviewer.
Do not delegate final acceptance or start the next Stage.

Strictly review:
[Stage ID]

Read the authoritative Stage criteria, current status, complete current Stage
log, accepted handoffs/contracts, complete Stage diff, and existing evidence.

Run or verify each applicable gate:
- affected frontend/backend tests
- applicable typecheck, lint, and build
- migration/rollback when data or Schema changed
- E2E only for affected critical journeys
- compatibility/retirement when applicable
- git diff --check
- documentation/log consistency

Do not rerun checks when reliable evidence covers the final diff and no relevant
code changed afterward. Record why each skipped check is not applicable or
which evidence covers it.

UI acceptance:
- ordinary localized UI changes do not require full desktop/mobile inspection
  or explicit user approval
- automated tests still verify behavior, routes, permissions, truthful states,
  and critical interactions
- for global navigation/layout/design system/homepage/primary journey/
  delivery-critical changes, generate or update:
  trade-strategy-ai/docs/ui-acceptance/stage-<n>-ui-checklist.md
- keep it concise: representative pages, necessary viewports, primary
  interactions, and user observations only
- do not capture every page, duplicate automated results, or perform visual polish
- do not claim user visual approval
- non-blocking polish is MEDIUM/LOW follow-up
- missing user approval is acceptance pending only when authoritative exit
  criteria require it; it is not an implementation BLOCKER

Check all acceptance criteria, real data/routes/APIs, applicable Schema,
migration, permissions/time semantics, truthful states, duplicate facts,
rollback, and retirement conditions.

Clear implementation BLOCKER and required HIGH findings.

Update records:
- Stage Gate details → current stage-<n>.md
- current status/pending gates/next step/index → Refactor-Implementation-Log.md

Output only evidence reused/executed, findings/repairs, pending manual UI
checklist, residual risk, acceptance conclusion, and whether the next Stage is
allowed.

Do not continue automatically.
```

## 9. New Session Recovery Prompt

```text
Use the refactor-orchestrator skill.

Do not infer progress from chat memory.
Read:
- AGENTS.md and trade-strategy-ai/AGENTS.md
- authoritative TaskList and current Stage plan
- Refactor-Implementation-Log.md
- current stage-<n>.md
- available .codex/refactor-state handoffs
- current branch, baseline, git status, and complete diff

Treat prior runtime and completion claims as unverified without evidence.

Report current Stage/Task, accepted work, incomplete work, blockers, dirty
changes, and the next smallest safe Task.

Do not implement until actual status is established.
```

## 10. 按需加载资料

- 约束 11.1～11.7：
  `AI-Conversation-Project-Constraints-1.md`
- 约束 11.8～11.15 和 Task→约束矩阵：
  `AI-Conversation-Project-Constraints-2.md`
- 可组合 Task、示例和 Prompt 编排核验：
  `AI-Conversation-Task-Matrix.md`

只读取当前 Task 所需的小段内容，不把辅助文档整体发送给子 Agent。
