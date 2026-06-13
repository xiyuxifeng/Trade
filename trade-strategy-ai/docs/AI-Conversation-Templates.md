# Trade Strategy AI 重构对话模板

## Part A：使用规则

### 1. 文档用途与仓库范围

本文件用于指导 Codex、Claude Code、Cursor Agent 或其他代码 Agent 完成 `trade-strategy-ai` 重构，并提供适配 `codex-refactor-orchestrator` 的短 Prompt 模板。

仓库关系：

```text
Trade/                       # Git 仓库根目录
└── trade-strategy-ai/       # 业务项目
```

基本约束：

- Codex 和 Orchestrator 从 `Trade` 根目录启动。
- 业务实现通常只修改 `trade-strategy-ai`。
- 正式重构文档只放在 `trade-strategy-ai/docs`。
- `.codex/refactor-state` 仅保存临时执行证据，不能替代正式 TaskList、设计、迁移或验收文档。
- 默认一次执行一个明确 Task。
- 只有用户明确指定时，才可执行同一 Stage 中紧密关联、共享冻结契约且可共同验收的少量 Task。
- 不跨 Stage 合并执行。
- 不建立第二套正式入口、Schema、API、Service、Prompt 链或数据事实源。
- 不使用 Mock、硬编码、空接口或占位页冒充完成。

---

### 2. 文档优先级

```text
AGENTS.md
> Trade-Refactor-TaskList.md
> 最新正式重构方案
> 当前 Task 设计和实施计划
> Refactor-Implementation-Log.md
> 历史文档
```

发生冲突时遵循高优先级文件，并把冲突、选择和影响记录到 `Refactor-Implementation-Log.md`。

`trade-strategy-ai/docs/bak` 只用于历史参考，不能作为当前实现事实源。

---

### 3. 上下文模式

#### 3.1 Stage Bootstrap

以下情况使用完整 Bootstrap：

- 新建 Parent Session；
- 进入新的 Stage；
- 上下文已压缩、丢失或不确定；
- TaskList、正式方案或公共契约发生变化；
- 上一个 Task 没有完成 Parent Review；
- Git 工作区出现来源不明的新修改。

Parent 读取：

1. `AGENTS.md`
2. `trade-strategy-ai/docs/Trade-Refactor-TaskList.md`
3. `trade-strategy-ai/docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`
4. 当前 Stage 的正式设计、迁移和验收文档
5. `trade-strategy-ai/docs/Refactor-Implementation-Log.md`
6. 当前 Task 的直接实施计划
7. 当前分支、基线、未提交修改、实际代码、测试、数据库和注册 API

只有 Stage 3、Stage 7、Stage 10，或其他确实修改 LLM/文章/作者画像链路的 Task，才额外读取：

```text
trade-strategy-ai/docs/PROMPT_REVIEW_AND_MIGRATION.md
trade-strategy-ai/docs/AUTHOR_PROFILE_PROMPT_FLOW.md
trade-strategy-ai/docs/LLM-Prompt-Orchestration.md
```

#### 3.2 Same-Stage Continuation

在同一个 Parent Session 内继续同一 Stage 时，不重读未变化的全局文档。

只读取：

- 当前 Task 定义和直接验收要求；
- 自上一个已接受 Task 后新增的实施记录；
- 上游 Task 产生的冻结契约和 handoff；
- 当前 `git status` 和完整 diff；
- 当前 Task 直接相关的代码和测试。

仅在以下情况重读全局文档：

- 出现文档或契约冲突；
- 引用文档发生变化；
- Parent 对权威约束不确定；
- 当前 Task 修改共享公共契约；
- 即将进入新的 Stage。

---

### 4. Orchestrator 使用规则

#### 4.1 委派不是自动发生

所有执行 Prompt 都应包含：

```text
Use the refactor-orchestrator skill.

Explicitly decide whether delegation is justified under the Skill rules.
If justified, explicitly spawn the selected configured subagent or subagents.
If not justified, proceed with the Parent only and record that zero subagents
were selected.
Do not rely on implicit delegation.
```

`0` 个 subagent 是合法结果。

#### 4.2 Trade 默认 Agent 预算

```text
普通任务：0–1 个 subagent
互不重叠的独立实现：最多 2 个 Executor
大型只读审计：最多 3 个 Explorer
```

超出默认预算必须由 Parent 说明理由。

| 风险 | 默认强度 | 建议方式 |
| --- | --- | --- |
| M1 | lean | Parent 直接执行或 1 个 Executor |
| M2 | standard | Parent 冻结契约，默认 1 个 Executor |
| M3 | assurance | Parent 主导，mini 仅做严格限定支持 |

#### 4.3 已知范围默认不使用 Explorer

以下情况不得仅为了“保险”创建 Explorer：

- 目标文件已知；
- 调用链已经记录；
- 上游 handoff 已指出实现入口；
- Parent 阅读少量文件即可解决；
- 当前任务主要是机械实现或测试。

Explorer 只用于：

- 未知调用链；
- 全仓 legacy 或重复事实源搜索；
- 删除前引用扫描；
- 迁移历史调查；
- 大型测试日志和失败分类。

#### 4.4 Parent 与子 Agent 的上下文边界

Parent 负责读取全局规则、TaskList、架构、迁移和实施记录。

Explorer/Executor 只读取：

- Task Card；
- 适用的根级和嵌套 `AGENTS.md`；
- 明确范围内的实现文件；
- 直接受影响的测试；
- 冻结契约和上游 handoff。

不要让每个子 Agent 重读完整 TaskList 和全部全局设计文档。Task Card 控制范围；当前代码和测试仍是实现事实。发现冲突时停止并升级给 Parent。

#### 4.5 Runtime Truth

完整规则以 `.agents/skills/refactor-orchestrator/SKILL.md` 为准。

必须有证据才能声称：

- 命令或测试已执行；
- diff 或文件已修改；
- migration 已应用或验证；
- 验收条件满足；
- Task 或 Stage 完成。

模型、有效权限和 spawning 细节只有可验证时才报告；否则省略或标记为 `not independently verified`。

只有 native spawning 不可用、child 创建失败，或任务依赖的权限边界无法保证时，才使用 single-controller fallback。仅无法确认确切 child model，不需要自动 fallback。

---

### 5. 验证预算

#### 5.1 普通 Task

普通 M1/M2 Task 默认只运行：

- focused tests；
- 直接受影响的 regression tests；
- 一个必要静态检查，例如 typecheck、lint 或 build；
- `git diff --check`。

不要在每个普通 Task 中重复执行全量测试、完整 build、E2E 和全部视觉验收。

#### 5.2 高风险 Task

以下任务必须在当前 Task 内完成专项验证：

- 数据库 Schema 和 migration；
- 数据迁移和回滚；
- 权限和安全边界；
- point-in-time / 防未来数据；
- 公共 API、共享路由或中心事实源；
- destructive deletion 和兼容退役。

#### 5.3 Stage Gate

Stage 完成时统一执行：

- 全量前端/后端测试；
- 完整 typecheck、lint 和 build；
- migration/rollback 验证；
- E2E；
- 桌面/移动视觉验收；
- 完整用户业务路径；
- 最终工作区和文档一致性检查。

---

## Part B：可复制 Prompt

### 6. Stage Bootstrap Prompt

用于新 Session 或进入新 Stage。

```text
Use the refactor-orchestrator skill.

Explicitly decide whether delegation is justified under the Skill rules.
If justified, explicitly spawn the selected configured subagent or subagents.
If not justified, proceed with the Parent only and record that zero subagents
were selected.
Do not rely on implicit delegation.

Work from the Trade repository root.
Execute only:
[Stage ID / Task ID / title]

Parent must read:

1. AGENTS.md
2. trade-strategy-ai/docs/Trade-Refactor-TaskList.md
3. trade-strategy-ai/docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md
4. trade-strategy-ai/docs/Refactor-Implementation-Log.md
5. the current Stage design, implementation, migration, and acceptance documents:
   - [insert exact Stage document paths]
6. the current Task definition and direct implementation plan:
   - [insert exact Task document paths]
7. current branch, baseline, git status, complete diff, directly relevant code,
   tests, database state, and registered APIs

Read these only when the current Stage directly changes Prompt, article, or
author-profile behavior:
- trade-strategy-ai/docs/PROMPT_REVIEW_AND_MIGRATION.md
- trade-strategy-ai/docs/AUTHOR_PROFILE_PROMPT_FLOW.md
- trade-strategy-ai/docs/LLM-Prompt-Orchestration.md

Do not read unrelated Stage documents.

Before implementation:
- verify prerequisites and actual status
- classify the Task as M1, M2, or M3
- freeze public contracts, Schema, API, permissions, migrations, rollback,
  compatibility, and verification commands
- apply the Skill delegation eligibility and benefit gates
- do not spawn Explorer when target files and call chains are already known
- give children only bounded Task Cards and necessary scoped context

Apply these project-specific constraints:
[Paste only the relevant constraint block from Part C]

Verification:
- ordinary Task: focused tests, affected regressions, one static check,
  git diff --check
- high-risk Task: run the required migration/security/time-semantics/deletion
  verification immediately
- defer full suites, E2E, and broad visual checks to the Stage Gate

Update Refactor-Implementation-Log.md.
Do not start the next Task or Stage automatically.

Return only:
- delegation decision
- files changed
- checks and exact results
- blockers or contract deviations
- concise handoff
```

---

### 7. Same-Stage Continuation Prompt

用于同一个 Parent Session 内继续同一 Stage。

```text
Use the refactor-orchestrator skill.

Continue within the current Stage and reuse the authoritative context already
established in this Parent Session.

Execute only:
RT-S1-003 首页改造

Do not reread unchanged global project documents.

Read only:
- current Task requirements
- implementation-log entries added since the previous accepted Task
- upstream frozen contracts and handoff
- current git status and complete diff
- directly related code and tests

Reread global documents only when changed, conflicting, uncertain, or when this
Task changes a shared public contract.

Explicitly decide whether delegation is justified.
Zero subagents is valid.
Do not spawn Explorer when files, call chains, and ownership are known.

Apply these project-specific constraints:
[Paste only the relevant constraint block from Part C]

Verification:
- focused tests
- directly affected regressions
- one necessary static check
- git diff --check
- defer full suites, E2E, and broad visual checks to the Stage Gate unless this
  Task changes a high-risk shared contract

Update Refactor-Implementation-Log.md.

Return only:
- delegation decision
- files changed
- checks and exact results
- blockers or contract deviations
- concise handoff
```

---

### 8. Task Review Prompt

用于 Task 实现完成后的 Parent Review，不替代 Stage Gate。

```text
Use the refactor-orchestrator skill.
Use the Parent as final reviewer.

Review only:
[Task ID and title]

Do not start the next Task or Stage.

Read only:
- Task acceptance requirements
- latest implementation-log entry
- upstream contracts and Task handoff
- current git status and complete Task diff
- affected files and tests

Check:
- requirements and frozen contracts
- official fact-source uniqueness
- compatibility and scope boundaries
- truthful loading/empty/error/partial/unavailable states when applicable
- no unrelated or later-Task work
- documentation accuracy

Run:
- focused tests
- one required static check
- git diff --check

For migrations, security, time semantics, central fact sources, or deletion,
also run the Task's required specialized verification.

Classify findings as BLOCKER, HIGH, MEDIUM, or LOW.
Repair only BLOCKER and required HIGH findings, then rerun affected checks.

State:
- whether the Task implementation is accepted
- whether the next Task may start
- which Stage-level checks remain pending

Do not mark the Stage complete.
```

---

### 9. Stage Gate Review Prompt

用于 Stage 完成时的完整验收。

```text
Use the refactor-orchestrator skill.
Use the Parent as final reviewer.
Do not delegate final Stage acceptance.
Do not start the next Stage.

Strictly review:
Stage 1

Read:
- authoritative Stage requirements and acceptance criteria
- Stage implementation-log entries
- accepted Task handoffs and frozen contracts
- complete Stage diff
- actual test, migration, E2E, and visual evidence

Run or verify:
- full affected frontend/backend test suites
- complete typecheck, lint, and build
- migration and rollback checks when applicable
- E2E and complete business journey
- desktop/mobile visual verification
- compatibility and retirement gates
- git diff --check
- documentation consistency

Check:
- every acceptance criterion
- real data and registered routes/APIs
- Schema, migration, permissions, and time semantics
- truthful loading/empty/error/partial/unavailable states
- duplicate fact sources and unrelated changes
- rollback and legacy-retirement conditions

Classify findings as BLOCKER, HIGH, MEDIUM, or LOW.
Clear all BLOCKER and required HIGH findings before acceptance.

Output:
- verified evidence
- findings and repairs
- residual risk
- Stage acceptance conclusion
- whether the next Stage is allowed

fix all find issues, and Do not continue next stage automatically.
```

---

### 10. New Session Recovery Prompt

用于中断后恢复，不根据聊天记忆推断进度。

```text
Use the refactor-orchestrator skill.

Do not infer progress from chat memory.
Work from the Trade repository root.

Recover the current Stage by reading:
- AGENTS.md
- authoritative TaskList and current Stage plan
- latest Refactor-Implementation-Log.md
- available .codex/refactor-state handoffs
- current branch, baseline, git status, and complete diff

Treat prior model, permission, spawning, test, and completion claims as
unverified unless evidence is present.

Report:
- current Stage and Task
- accepted work
- in-progress and incomplete work
- blockers and dirty changes
- next smallest safe Task

Do not implement until the actual status is established.
```

---

## Part C：项目专用附加约束

项目专用约束放在通用 Prompt 的“当前 Task/范围”之后、“执行和验证规则”之前。

每个 Task 通常只追加一个主约束，最多两个。不要把全部约束复制进同一个 Prompt。

### 11.1 Stage 1 产品页面

```text
Stage 1 constraints:
- Preserve trade-strategy-ai/web/src/app/route-config.tsx as the single route,
  navigation, permission, metadata, and compatibility fact source.
- Formal pages use business Chinese and do not expose Job, Workflow, Pipeline,
  Artifact, Provider, force, config_path, database names, or internal paths.
- Every formal page represents 页面用途、输入、处理状态、输出、下一步。
- Support loading, empty, error, partial, permission_denied, and unavailable
  truthfully.
- Do not convert unavailable data into false, zero, an empty list, or success.
- Legacy pages remain compatibility-only until retirement conditions pass.
- Do not enter Stage 2 before the Stage 1 exit Review.
```

### 11.2 领域契约冻结

```text
Domain contract constraints:
- Freeze stable IDs, version relationships, lifecycle states, source references,
  and audit fields before implementation.
- Produce object relationships and old-to-new mappings before changing ORM,
  API, or frontend types.
- Distinguish formal versions, daily runtime instances, proposals, and
  compatibility objects.
- Do not delegate unresolved source-of-truth decisions.
```

### 11.3 数据库迁移安全

```text
Database migration constraints:
- Inspect ORM models, metadata imports, Alembic heads, existing tables, and
  actual data first.
- Freeze target Schema and migration order before delegation.
- Migrations must be safely rerunnable, observable, and recoverable.
- Never silently drop or overwrite legacy data.
- Produce pre/post counts, rejected rows, and quality reports.
- Test upgrade, transformation, and rollback/recovery paths.
- Only one writer modifies a migration chain or shared ORM contract.
```

### 11.4 Prompt 迁移与退役

```text
Prompt migration constraints:
- Treat Prompt files, loader code, Schema, and regression fixtures as one contract.
- Record prompt_version, schema_version, model, input_hash, raw output,
  validation, tokens, and cost.
- Compare new and legacy results on the fixed regression set before cutover.
- New Prompt becomes the only formal write path before legacy becomes
  compatibility_only.
- Do not delete legacy Prompt until all references, observation, and rollback
  checks pass.
```

### 11.5 单篇文章闭环

```text
Single-article constraints:
- A normal article uses article_analysis_v1 as one main call.
- article_analysis_repair_v1 is targeted and used at most once.
- Modular extraction Prompts are Schema/test tools, not four default production
  calls.
- Preserve original text, evidence, explicit facts, hypotheses, missing fields,
  dependencies, and backtestability.
- Automatic pass means pending backtest, not formally usable.
- Only human-reviewed results may create a formal RuleVersion.
```

### 11.6 回归样本与批处理

```text
Batch processing constraints:
- Freeze 10–15 representative articles and expected outcomes first.
- Do not process all 100+ articles before the fixed set passes.
- Record article/content versions, Prompt/Schema versions, raw output,
  automatic review, and human conclusion.
- Support resume, bounded retry, idempotency, concurrency limits, and
  incremental updates.
- Do not send all article bodies in one LLM request.
```

### 11.7 规则治理

```text
Rule governance constraints:
- Automatic review cannot make a rule formally usable.
- High-risk, ambiguous, conflicting, parameter-edited, and strategy-entry rules
  require human approval.
- Freeze fingerprint, RuleFamily, parameter variant, conflict, and lifecycle
  semantics.
- Every transition records actor, time, reason, and before/after values.
```

### 11.8 数据时间语义与调度

```text
Data and scheduling constraints:
- Preserve trade_date, available_at, captured_at, effective_at, source, and slot.
- Separate pre-market and post-market Kaipan data.
- Backfill and daily incremental update are independently testable.
- Tasks are idempotent, resumable, and retryable.
- Missing data remains unavailable, not false or zero.
- Backtests do not call live Providers during execution.
```

### 11.9 回测安全

```text
Backtest safety constraints:
- Bind every run to DatasetSnapshot, rule version, market-state model version,
  and code version.
- Prevent future-data leakage and live Provider calls.
- Separate Level 1 OHLCV, Level 2 OHLCV + market state, and Level 3 including
  Kaipan.
- Missing Kaipan is a coverage limitation.
- Mark insufficient_sample instead of producing strong conclusions.
- Include replay and reproducibility evidence.
```

### 11.10 作者画像边界

```text
Author profile constraints:
- Keep AuthorMethodProfile, AuthorRuleProfile, and AuthorValidatedProfile separate.
- Do not describe results as the author's real trading performance.
- Separate article expression, rule statistics, and backtest validation.
- Every conclusion has evidence and confidence.
- New evidence creates drafts/revisions and does not overwrite published profiles.
- Batch method profiles use 10–20 structured articles.
```

### 11.11 策略版本与 Proposal

```text
Strategy constraints:
- StrategyVersion is formal and is not regenerated daily.
- DailyStrategyInstance is a runtime object.
- StrategyRevisionProposal cannot directly modify a published strategy.
- Freeze lifecycle, validation, publication, current-use, archive, and rollback
  behavior.
```

### 11.12 每日盘前

```text
Pre-market constraints:
- Complete data, market-state, strategy, and applicability checks before selection.
- Generate DailyRuleSelection, DailyStrategyInstance, and TradingDayPlan, not a
  formal strategy version.
- Explain enabled, reduced, and suspended rules.
- Trace every result to input versions and data-quality states.
- Missing inputs require repair or explicit degradation.
```

### 11.13 每日盘后归因

```text
Post-market constraints:
- Program facts calculate trigger, execution, MFE, MAE, return, and
  market-state change.
- LLM validates or explains but does not recompute program metrics.
- Use llm_attribution_v1 only for low confidence, conflict, or important signals.
- Use llm_postmortem_notes_v1 conditionally or once for daily summary.
- Keep rule, author, and strategy proposals separate.
- A single day never directly modifies formal objects.
```

### 11.14 运行保障与系统管理

```text
Operations constraints:
- Separate normal-user status/actions from administrator technical details.
- Use stable run_id and record steps, duration, errors, and retries.
- Record Prompt model/version/Schema/tokens/cost and data
  range/coverage/time semantics.
- Recovery supports resume, retry limits, and visible actions.
- User errors explain what happened, impact, and remediation.
- Freeze rollout stages and provide rollback/recovery.
```

### 11.15 最终退役与交付

```text
Final retirement constraints:
- Before deletion, verify target migration, data migration, reference scan,
  observation period, and rollback evidence.
- Do not retire legacy paths merely because a new page exists.
- Run the full real-data journey.
- Run E2E, frontend, backend, migration, and Prompt regression suites.
- Verify user/admin documentation against the actual UI.
```

---

## Part D：Task 与约束选择

### 12. Task → 约束选择矩阵

| Task 范围 | 必须附加 | 可选附加 |
| --- | --- | --- |
| RT-S1-* | Stage 1 产品页面 | 无 |
| RT-S2-001 | 领域契约冻结 | 无 |
| RT-S2-002～003 | 数据库迁移安全 | 领域契约冻结 |
| RT-S3-001、RT-S3-004 | Prompt 迁移与退役 | 回归样本与批处理 |
| RT-S3-002 | 单篇文章闭环 | Prompt 迁移与退役 |
| RT-S3-003 | 回归样本与批处理 | Prompt 迁移与退役 |
| RT-S4-* | 规则治理 | 数据库迁移安全 |
| RT-S5-* | 数据时间语义与调度 | 运行保障与系统管理 |
| RT-S6-* | 回测安全 | 数据时间语义与调度 |
| RT-S7-* | 作者画像边界 | Prompt 迁移与退役 |
| RT-S8-* | 策略版本与 Proposal | 规则治理 |
| RT-S9-* | 每日盘前 | 策略版本与 Proposal |
| RT-S10-* | 每日盘后归因 | 策略版本与 Proposal |
| RT-S11-* | 运行保障与系统管理 | 数据时间语义与调度 |
| RT-S12-* | 最终退役与交付 | 当前被退役领域的对应约束 |

可选约束只有在当前 Task 实际触及该风险时才追加。

---

### 13. 可组合执行矩阵

| Stage | Task 组合 | 建议 |
| --- | --- | --- |
| 0 | RT-S0-001 + RT-S0-002 | 可以，同 Session 串行；已完成 |
| 1 | RT-S1-001 | 单独；已完成 |
| 1 | RT-S1-002 | 已执行，不再保留专用 Prompt |
| 1 | RT-S1-003 | 单独；同 Stage 延续时使用 Continuation |
| 2 | RT-S2-001、RT-S2-002、RT-S2-003 | 分别单独，M3 |
| 3 | RT-S3-001 + RT-S3-002 | 有条件；默认分两 Task，同 Session 时串行 |
| 3 | RT-S3-003 | 单独 |
| 3 | RT-S3-004 | 单独且最后 |
| 4 | RT-S4-002 + RT-S4-003 | 可以，同 Session 串行 |
| 4 | RT-S4-001 | 建议后置单独 |
| 5 | RT-S5-001 + RT-S5-002 | 有条件，同 Parent Session 多批次 |
| 5 | RT-S5-003 | 后置单独 |
| 6 | RT-S6-001 + RT-S6-002 | 可以，同 Session 串行 |
| 6 | RT-S6-003 + RT-S6-004 | 可以，同 Session 串行 |
| 7 | RT-S7-001 + RT-S7-002 | 可以，同 Session 多批次 |
| 7 | RT-S7-003 + RT-S7-004 | 有条件，同 Session 串行 |
| 8 | RT-S8-001 + RT-S8-002 | 可以，同 Session 串行 |
| 8 | RT-S8-003 | 单独 |
| 9 | RT-S9-001 + RT-S9-002 | 可以，同 Session 串行 |
| 9 | RT-S9-003 | 后置单独 |
| 10 | RT-S10-001 + RT-S10-002 | 可以，同 Session 串行 |
| 10 | RT-S10-003 + RT-S10-004 | 可以，同 Session 串行 |
| 11 | RT-S11-002 + RT-S11-003 | 有条件，同 Session 串行 |
| 11 | RT-S11-004 + RT-S11-005 | 有条件，同 Session 多批次 |
| 11 | RT-S11-001 + RT-S11-007 | 可以，同 Session |
| 11 | RT-S11-006 | 单独且最后 |
| 12 | RT-S12-001 | 单独，M3 |
| 12 | RT-S12-002 + RT-S12-003 | 有条件，同 Session 串行 |

不得组合：

- RT-S2-001 与 RT-S2-003；
- RT-S3-001 与 RT-S3-004；
- 未稳定的数据任务与 RT-S5-003；
- RT-S8-001 与 RT-S9-003；
- RT-S10-001 与 RT-S10-003；
- 灰度迁移与被灰度实现；
- 旧入口退役与未完成迁移或观察期。

Stage 5 和 Stage 6 的“部分并行”不表示可在一个 Prompt 中跨 Stage 合并。必须由用户明确授权、使用不同 Parent Session/工作范围，并先冻结稳定的数据契约。

---

## Part E：使用示例

### 14. RT-S1-003

```text
Same-Stage Continuation Prompt
+ Stage 1 产品页面约束
```

如果已新建 Session，则使用：

```text
Stage Bootstrap Prompt
+ Stage 1 产品页面约束
```

### 15. RT-S2-002

```text
Same-Stage Continuation Prompt
+ 数据库迁移安全
+ 领域契约冻结（仅在当前 Task 仍会修改领域契约时追加）
```

### 16. RT-S6-002

```text
Same-Stage Continuation Prompt
+ 回测安全
+ 数据时间语义与调度
```

### 17. RT-S12-001

```text
Stage Bootstrap Prompt
+ 最终退役与交付
+ 被退役领域对应的专项约束
```

该任务必须使用高风险专项验证，不能仅运行普通 Task 验证。

---

## 18. Prompt 调用编排核验

仅在 Stage 3、Stage 7、Stage 10，或其他实际修改 LLM 调用链的 Task 中追加：

```text
Verify compliance with trade-strategy-ai/docs/LLM-Prompt-Orchestration.md:
- one article_analysis_v1 main call for a normal article
- at most one targeted article_analysis_repair_v1
- modular extraction Prompts are not four default production calls
- no per-article author total-profile Prompt
- author batches use 10–20 structured articles
- conditional llm_attribution_v1 only
- llm_postmortem_notes_v1 is conditional or once per daily summary
- Prompt/Schema/model/token/cost/input_hash/run_id records
- cache and idempotency
- LLM raw output is not the final formal fact source
- legacy Prompt stops formal writes after cutover
- deletion only after retirement conditions pass
```

不要在与 LLM 调用链无关的 UI、数据库基础设施或系统管理 Task 中追加此段。

---

## 19. 使用结论

1. 新 Session 或新 Stage使用 `Stage Bootstrap Prompt`。
2. 同一 Session 内继续同一 Stage使用 `Same-Stage Continuation Prompt`。
3. 每个 Task 实现后使用 `Task Review Prompt`。
4. Stage 结束时使用 `Stage Gate Review Prompt`。
5. 中断后恢复使用 `New Session Recovery Prompt`。
6. 复制一个 Prompt 模板后，只追加 1～2 段当前 Task 所需的项目约束。
7. 普通 Task 只运行 focused/affected checks。
8. 全量测试、E2E 和完整视觉验收统一放到 Stage Gate。
9. 已知范围默认不创建 Explorer。
10. 不根据 subagent 声明直接进入下一 Task。
11. Task 和 Stage 状态始终服从当前实施计划中更严格的验收门禁。
