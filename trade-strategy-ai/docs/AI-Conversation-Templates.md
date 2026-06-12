# Trade Strategy AI 重构对话模板

## 1. 文档用途与仓库范围

本文件用于指导 Codex、Claude Code、Cursor Agent 或其他代码 Agent 完成 `trade-strategy-ai` 重构，并提供适配 `codex-refactor-orchestrator` 的最终可用 Prompt。

仓库关系：

```text
Trade/                       # Git 仓库根目录
└── trade-strategy-ai/       # 业务项目
```

执行要求：

- Codex 和 Orchestrator 从 `Trade` 根目录启动。
- 业务实现通常只修改 `trade-strategy-ai`。
- 正式重构文档只放在 `trade-strategy-ai/docs`。
- `.codex/refactor-state` 仅保存临时执行证据，不替代正式 TaskList、设计、迁移或验收文档。
- 默认一次执行一个明确 Task。
- 只有用户明确指定时，才可执行同一 Stage 中紧密关联、共享冻结契约且可共同验收的少量 Task。
- 不跨 Stage 合并执行。
- 不建立第二套正式入口、Schema、API、Service、Prompt 链或数据事实源。
- 不使用 Mock、硬编码、空接口或占位页冒充完成。

---

## 2. 必读文档与优先级

Parent 在规划当前 Task 前按顺序读取：

1. `AGENTS.md`
2. `trade-strategy-ai/docs/Trade-Refactor-TaskList.md`
3. `trade-strategy-ai/docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`
4. `trade-strategy-ai/docs/PROMPT_REVIEW_AND_MIGRATION.md`
5. `trade-strategy-ai/docs/AUTHOR_PROFILE_PROMPT_FLOW.md`
6. `trade-strategy-ai/docs/LLM-Prompt-Orchestration.md`
7. `trade-strategy-ai/docs/Refactor-Implementation-Log.md`
8. 当前 Task 直接相关的设计、实施、迁移和验收文档
9. 当前分支、基线、未提交修改、实际代码、测试、数据库和注册 API

文档优先级：

```text
AGENTS.md
> Trade-Refactor-TaskList.md
> 最新正式重构方案
> 当前 Task 设计和实施计划
> Refactor-Implementation-Log.md
> 历史文档
```

发现冲突时遵循高优先级文件，并把冲突、选择和影响记录到 `Refactor-Implementation-Log.md`。

`trade-strategy-ai/docs/bak` 只用于历史参考，不能作为当前实现事实源。

---

## 3. Orchestrator 使用规则

### 3.1 安装、验证与启动

```bash
cd /path/to/codex-refactor-orchestrator
bash install.sh /path/to/Trade

cd /path/to/Trade
bash .agents/skills/refactor-orchestrator/scripts/validate-install.sh
bash .agents/skills/refactor-orchestrator/scripts/runtime-probe.sh
codex -m gpt-5.5
```

建议一个 Stage 或紧密关联的 Task 组使用一个新的 Parent Session。

### 3.2 委派不是自动发生

任何使用 Orchestrator 的 Prompt 都应包含：

```text
Use the refactor-orchestrator skill.

Explicitly decide whether delegation is justified under the Skill rules.
If justified, explicitly spawn the selected configured subagent or subagents.
If not justified, proceed with the Parent only and record that zero subagents
were selected.
Do not rely on implicit delegation.
```

`0` 个 subagent 是合法结果。

### 3.3 Trade 项目的默认 Agent 预算

```text
普通任务：0–1 个 subagent
互不重叠的独立实现：最多 2 个 Executor
大型只读审计：最多 3 个 Explorer
```

超出默认预算必须由 Parent 说明理由。

默认风险和执行强度：

| 风险 | 默认强度 | 建议方式 |
| --- | --- | --- |
| M1 | lean | Parent 直接执行或 1 个 Executor |
| M2 | standard | Parent 冻结契约，默认 1 个 Executor |
| M3 | assurance | Parent 主导，mini 仅做严格限定支持 |

### 3.4 Parent 与子 Agent 的上下文边界

Parent 读取全局规则、TaskList、架构、迁移和实施记录。

Explorer/Executor 只读取：

- Task Card；
- 适用的根级和嵌套 `AGENTS.md`；
- 明确范围内的实现文件；
- 直接受影响的测试；
- 冻结契约和上游 handoff。

不要让每个子 Agent 重读完整 TaskList 和全部全局设计文档。Task Card 控制范围；当前代码和测试仍是实现事实。发现冲突时停止并升级给 Parent。

### 3.5 Runtime Truth

完整规则以 `.agents/skills/refactor-orchestrator/SKILL.md` 为准。

始终必须有证据才能声称：

- 命令或测试已执行；
- diff 或文件已修改；
- migration 已应用或验证；
- 验收条件满足；
- Task 或 Stage 完成。

模型、有效权限和 spawning 细节只有可验证时才报告；否则省略或标记为 `not independently verified`。

只有 native spawning 不可用、child 创建失败，或任务依赖的权限边界无法保证时，才使用 single-controller fallback。仅无法确认确切 child model，不需要自动 fallback。

---

## 4. Orchestrator 通用 Task Prompt

使用时填写 Task ID，并追加第 5 节对应的项目专用约束。

```text
Use the refactor-orchestrator skill.

Explicitly decide whether delegation is justified under the Skill rules.
If justified, explicitly spawn the selected configured subagent or subagents.
If not justified, proceed with the Parent only and record that zero subagents
were selected.
Do not rely on implicit delegation.

Apply the Skill runtime-truth policy:
- require evidence for commands, tests, diffs, migrations, acceptance, and completion
- report exact runtime model, permissions, and spawning details only when verified
- use fallback only when spawning is unavailable/fails or a required permission boundary cannot be guaranteed

Work from the Trade repository root.
Limit business implementation changes to trade-strategy-ai.
Store formal refactor documents only under trade-strategy-ai/docs.

Execute only:
[Task ID and title]

Parent must read:
1. AGENTS.md
2. trade-strategy-ai/docs/Trade-Refactor-TaskList.md
3. trade-strategy-ai/docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md
4. trade-strategy-ai/docs/PROMPT_REVIEW_AND_MIGRATION.md
5. trade-strategy-ai/docs/AUTHOR_PROFILE_PROMPT_FLOW.md
6. trade-strategy-ai/docs/LLM-Prompt-Orchestration.md
7. trade-strategy-ai/docs/Refactor-Implementation-Log.md
8. current Task design, implementation, migration, and acceptance documents
9. current branch, baseline, dirty changes, code, tests, database, and registered APIs

Before implementation:
- verify prerequisites and actual current status
- inspect existing implementation and avoid duplication
- record branch, baseline, and dirty changes
- classify the task as M1, M2, or M3
- freeze architecture, public contracts, Schema, API, permissions, migrations, rollback, compatibility, and verification commands
- apply the Skill delegation eligibility and benefit gates
- when delegation is used, create bounded Task Cards with allowed/forbidden paths and structured handoffs
- children read only their Task Card, applicable AGENTS.md, scoped files/tests, frozen contracts, and upstream handoffs

Execution rules:
- do not cross into the next Task or Stage
- do not create duplicate formal entries, Schema, Service, API, Prompt chains, or fact sources
- do not use mocks, placeholders, or hardcoded success to claim completion
- preserve compatibility until retirement conditions pass
- do not parallelize overlapping files, migrations, routes, or public contracts
- respect the default Trade agent budget unless a larger batch is explicitly justified
- limit each delegated Task to three implementation/fix rounds
- inspect the shared worktree and actual diff after every batch
- do not accept only a subagent completion message

Verification:
- run focused and affected regression tests
- run applicable typecheck, lint, build, API, migration, Prompt regression, E2E, and manual checks
- run git diff --check
- record exact commands, counts, failures, skipped checks, and residual risk

Documentation and status:
- update trade-strategy-ai/docs/Refactor-Implementation-Log.md
- use [ ], [-], [x], [!], and [~] status markers
- update authoritative status only after Parent acceptance
- do not automatically start the next Task

Final response:
- delegation decision and justification
- actual agents used; exact models/permissions only when verified
- fallback mode when applicable
- risk classification and Task Cards
- files changed
- migrations, compatibility, and rollback
- tests and exact results
- visual/manual verification
- incomplete items and risks
- acceptance conclusion
- confirmation that no later Task or Stage was started
```

---

## 5. 项目专用附加约束

### 5.1 Stage 1 产品页面

```text
Stage 1 constraints:
- Preserve trade-strategy-ai/web/src/app/route-config.tsx as the single route, navigation, permission, metadata, and compatibility fact source.
- Formal pages use business Chinese and do not expose Job, Workflow, Pipeline, Artifact, Provider, force, config_path, database names, or internal paths.
- Every formal page represents 页面用途、输入、处理状态、输出、下一步。
- Support loading, empty, error, partial, permission_denied, and unavailable truthfully.
- Do not convert unavailable data into false, zero, an empty list, or success.
- Legacy pages remain compatibility-only until retirement conditions pass.
- Do not enter Stage 2 before the Stage 1 exit Review.
```

### 5.2 领域契约冻结

```text
Domain contract constraints:
- Freeze stable IDs, version relationships, lifecycle states, source references, and audit fields before implementation.
- Produce object relationships and old-to-new mappings before changing ORM, API, or frontend types.
- Distinguish formal versions, daily runtime instances, proposals, and compatibility objects.
- Do not delegate unresolved source-of-truth decisions.
```

### 5.3 数据库迁移安全

```text
Database migration constraints:
- Inspect ORM models, metadata imports, Alembic heads, existing tables, and actual data first.
- Freeze target Schema and migration order before delegation.
- Migrations must be safely rerunnable, observable, and recoverable.
- Never silently drop or overwrite legacy data.
- Produce pre/post counts, rejected rows, and quality reports.
- Test upgrade, transformation, and rollback/recovery paths.
- Only one writer modifies a migration chain or shared ORM contract.
```

### 5.4 Prompt 迁移与退役

```text
Prompt migration constraints:
- Treat Prompt files, loader code, Schema, and regression fixtures as one contract.
- Record prompt_version, schema_version, model, input_hash, raw output, validation, tokens, and cost.
- Compare new and legacy results on the fixed regression set before cutover.
- New Prompt becomes the only formal write path before legacy becomes compatibility_only.
- Do not delete legacy Prompt until all references, observation, and rollback checks pass.
```

### 5.5 单篇文章闭环

```text
Single-article constraints:
- A normal article uses article_analysis_v1 as one main call.
- article_analysis_repair_v1 is targeted and used at most once.
- Modular extraction Prompts are Schema/test tools, not four default production calls.
- Preserve original text, evidence, explicit facts, hypotheses, missing fields, dependencies, and backtestability.
- Automatic pass means pending backtest, not formally usable.
- Only human-reviewed results may create a formal RuleVersion.
```

### 5.6 回归样本与批处理

```text
Batch processing constraints:
- Freeze 10–15 representative articles and expected outcomes first.
- Do not process all 100+ articles before the fixed set passes.
- Record article/content versions, Prompt/Schema versions, raw output, automatic review, and human conclusion.
- Support resume, bounded retry, idempotency, concurrency limits, and incremental updates.
- Do not send all article bodies in one LLM request.
```

### 5.7 规则治理

```text
Rule governance constraints:
- Automatic review cannot make a rule formally usable.
- High-risk, ambiguous, conflicting, parameter-edited, and strategy-entry rules require human approval.
- Freeze fingerprint, RuleFamily, parameter variant, conflict, and lifecycle semantics.
- Every transition records actor, time, reason, and before/after values.
```

### 5.8 数据时间语义与调度

```text
Data and scheduling constraints:
- Preserve trade_date, available_at, captured_at, effective_at, source, and slot.
- Separate pre-market and post-market Kaipan data.
- Backfill and daily incremental update are independently testable.
- Tasks are idempotent, resumable, and retryable.
- Missing data remains unavailable, not false or zero.
- Backtests do not call live Providers during execution.
```

### 5.9 回测安全

```text
Backtest safety constraints:
- Bind every run to DatasetSnapshot, rule version, market-state model version, and code version.
- Prevent future-data leakage and live Provider calls.
- Separate Level 1 OHLCV, Level 2 OHLCV + market state, and Level 3 including Kaipan.
- Missing Kaipan is a coverage limitation.
- Mark insufficient_sample instead of producing strong conclusions.
- Include replay and reproducibility evidence.
```

### 5.10 作者画像边界

```text
Author profile constraints:
- Keep AuthorMethodProfile, AuthorRuleProfile, and AuthorValidatedProfile separate.
- Do not describe results as the author's real trading performance.
- Separate article expression, rule statistics, and backtest validation.
- Every conclusion has evidence and confidence.
- New evidence creates drafts/revisions and does not overwrite published profiles.
- Batch method profiles use 10–20 structured articles.
```

### 5.11 策略版本与 Proposal

```text
Strategy constraints:
- StrategyVersion is formal and is not regenerated daily.
- DailyStrategyInstance is a runtime object.
- StrategyRevisionProposal cannot directly modify a published strategy.
- Freeze lifecycle, validation, publication, current-use, archive, and rollback behavior.
```

### 5.12 每日盘前

```text
Pre-market constraints:
- Complete data, market-state, strategy, and applicability checks before selection.
- Generate DailyRuleSelection, DailyStrategyInstance, and TradingDayPlan, not a formal strategy version.
- Explain enabled, reduced, and suspended rules.
- Trace every result to input versions and data-quality states.
- Missing inputs require repair or explicit degradation.
```

### 5.13 每日盘后归因

```text
Post-market constraints:
- Program facts calculate trigger, execution, MFE, MAE, return, and market-state change.
- LLM validates or explains but does not recompute program metrics.
- Use llm_attribution_v1 only for low confidence, conflict, or important signals.
- Use llm_postmortem_notes_v1 conditionally or once for daily summary.
- Keep rule, author, and strategy proposals separate.
- A single day never directly modifies formal objects.
```

### 5.14 运行保障与系统管理

```text
Operations constraints:
- Separate normal-user status/actions from administrator technical details.
- Use stable run_id and record steps, duration, errors, and retries.
- Record Prompt model/version/Schema/tokens/cost and data range/coverage/time semantics.
- Recovery supports resume, retry limits, and visible actions.
- User errors explain what happened, impact, and remediation.
- Freeze rollout stages and provide rollback/recovery.
```

### 5.15 最终退役与交付

```text
Final retirement constraints:
- Before deletion, verify target migration, data migration, reference scan, observation period, and rollback evidence.
- Do not retire legacy paths merely because a new page exists.
- Run the full real-data journey.
- Run E2E, frontend, backend, migration, and Prompt regression suites.
- Verify user/admin documentation against the actual UI.
```

---

## 6. 可组合执行矩阵

| Stage | Task 组合 | 建议 |
| --- | --- | --- |
| 0 | RT-S0-001 + RT-S0-002 | 可以，同 Session 串行；已完成 |
| 1 | RT-S1-001 | 单独；已完成 |
| 1 | RT-S1-002 | 单独，拆 Session A/B |
| 1 | RT-S1-003 | 单独 |
| 2 | RT-S2-001、RT-S2-002、RT-S2-003 | 分别单独，M3 |
| 3 | RT-S3-001 + RT-S3-002 | 有条件；默认分两 Session，同 Session 时串行 |
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

## 7. 当前下一步：RT-S1-002

当前状态：

- RT-S1-001 已完成；
- RT-S1-002 是下一步；
- RT-S1-003 尚未开始；
- Stage 1 尚未完成。

Stage 1 实施计划要求 Task 1～8 和共享门禁全部通过后，三个 Stage 1 Task 才能标记 `[x]`。Session A/B 只是 RT-S1-002 的实现批次。Session B 后通常保持 `[-]`，直到 RT-S1-003、桌面/移动视觉验收、全量回归、E2E、静态迁移门禁和最终工作区检查通过。

正确顺序：

```text
RT-S1-002 Session A
→ Parent Review
→ RT-S1-002 Session B
→ Parent Review
→ RT-S1-003
→ Stage 1 完整验收
```

### 7.1 RT-S1-002 Session A Prompt

```text
Use the refactor-orchestrator skill.

Explicitly decide whether delegation is justified under the Skill rules.
If justified, explicitly spawn the selected configured subagent or subagents.
If not justified, proceed with the Parent only and record that zero subagents
were selected.
Do not rely on implicit delegation.

Apply the Skill runtime-truth policy. Require evidence for commands, tests,
diffs, acceptance, and completion. Report exact runtime metadata only when
verified. Use fallback only when spawning fails/is unavailable or a required
permission boundary cannot be guaranteed.

Work from the Trade repository root.
Limit business changes to trade-strategy-ai.
Execute only the shared-framework and shared-layout portion of RT-S1-002.
Do not start RT-S1-003 or Stage 2.

Parent reads:
- AGENTS.md
- trade-strategy-ai/docs/Trade-Refactor-TaskList.md
- trade-strategy-ai/docs/Refactor-Implementation-Log.md
- trade-strategy-ai/docs/2026-06-10-stage-1-implementation-plan.md
- relevant migration/design documents
- current branch, baseline, dirty changes, code, tests, and diff

Classify this work as M2 / standard unless repository evidence requires a higher risk.
Freeze these contracts before any Executor delegation:
- PageAvailability
- BusinessPageShell
- ProductPageAdapter product/compat boundary
- SectionNav derivation and permission rules
- CompatibilityNotice metadata/actions
- DashboardLayout integration

Delegation rules for this Session:
- default budget is 0–1 Executor
- use Explorer only for an actually unknown route/permission/component ownership question
- use up to 2 Executors only when write sets are independent and the Parent records the benefit
- Parent retains ownership of route-config.tsx and shared public contract decisions
- children read only their Task Card, applicable AGENTS.md, scoped files/tests, and frozen contracts

Implement only:
- business-page-shell.tsx and tests
- section-nav.tsx and tests
- compatibility-notice.tsx and tests
- product-page-adapter.tsx and tests
- DashboardLayout route metadata and SectionNav integration
- StatusStrip cleanup
- route permission behavior

Project constraints:
- route-config.tsx remains the single route/navigation/permission/metadata/compatibility fact source
- formal pages use business Chinese and do not expose Job, Workflow, Pipeline, Artifact, Provider, force, config_path, database names, or internal paths
- page contracts represent 页面用途、输入、处理状态、输出、下一步
- support loading, empty, error, partial, permission_denied, and unavailable truthfully
- do not convert unavailable data into false, zero, empty collection, or success
- do not assemble all domain pages
- do not add migrations or modify Prompt behavior

Use TDD. Run:
cd trade-strategy-ai/web
pnpm test -- src/components/layout/business-page-shell.test.tsx src/components/layout/section-nav.test.tsx src/components/layout/compatibility-notice.test.tsx src/components/layout/product-page-adapter.test.tsx src/components/layout/sidebar.test.tsx src/components/layout/status-strip.test.tsx
pnpm typecheck
pnpm lint
pnpm build
pnpm test
cd ../..
git diff --check

Perform desktop/mobile visual verification when available; otherwise record it as incomplete verification.
Update trade-strategy-ai/docs/Refactor-Implementation-Log.md with [-] in-progress evidence.
Do not mark RT-S1-002 complete after Session A.

Final response:
- delegation decision and benefit justification
- actual agents used; model/permissions only when verified
- contracts frozen
- files changed
- tests and exact results
- visual verification status
- remaining Session B work
- confirmation that RT-S1-003 and Stage 2 were not started
```

### 7.2 RT-S1-002 Session B Prompt

```text
Use the refactor-orchestrator skill.

Explicitly decide whether delegation is justified under the Skill rules.
If justified, explicitly spawn the selected configured subagent or subagents.
If not justified, proceed with the Parent only and record that zero subagents
were selected.
Do not rely on implicit delegation.

Apply the Skill runtime-truth policy. Require evidence for commands, tests,
diffs, acceptance, and completion. Report exact runtime metadata only when
verified. Use fallback only when spawning fails/is unavailable or a required
permission boundary cannot be guaranteed.

Work from the Trade repository root.
Continue only RT-S1-002 after verifying Session A contracts, implementation-log entry, tests, and current diff.
Do not start Stage 2.

Parent reads the mandatory project documents, then:
- trade-strategy-ai/docs/2026-06-10-stage-1-implementation-plan.md
- current shared page components
- route-config.tsx
- current branch, baseline, dirty changes, and complete diff

Assemble formal product routes for:
- research
- rules and backtest
- authors
- strategies
- daily trading
- applicable system pages

Reuse real hooks, actions, and result components.
Do not duplicate domain logic or invent unavailable facts.
Keep legacy paths in compatibility mode.

Delegation rules for this Session:
- Parent owns route-config.tsx and any shared public contract change
- default budget is one domain Executor at a time
- at most 2 independent domain Executors may run in parallel when paths and contracts do not overlap
- children receive only bounded domain Task Cards and scoped implementation/test context

Verify the formal journey:
研究中心 → 待审核规则 → 回测实验 → 作者画像 → 策略中心 → 今日盘前 → 今日盘后

The journey must not require /jobs, /workflows, /artifacts, or /market/* technical workbenches.
Formal pages must preserve truthful loading, empty, error, partial, permission_denied, and unavailable states and must not expose engineering parameters.

Run:
cd trade-strategy-ai/web
pnpm test -- src/pages/product-entry-pages.test.tsx src/pages/product-page-state-matrix.test.tsx src/app/product-journey.test.tsx src/components/layout/product-page-adapter.test.tsx src/pages/articles/index.test.tsx src/pages/rule-pool/index.test.tsx src/pages/backtest/index.test.tsx src/pages/strategies/lifecycle.test.tsx src/pages/system/index.test.tsx
pnpm typecheck
pnpm lint
pnpm build
pnpm test
cd ../..
git diff --check

Perform desktop/mobile visual verification when available.
Update trade-strategy-ai/docs/Refactor-Implementation-Log.md.
Keep RT-S1-002 as [-] until RT-S1-003 and the shared Stage 1 visual, full-regression, E2E, migration-gate, and final-workspace checks pass.
Missing Browser/E2E evidence is not sufficient for [x].
Parent may allow RT-S1-003 to start only after confirming no blocking RT-S1-002 defect.

Final response:
- delegation decision and benefit justification
- actual agents used; model/permissions only when verified
- formal routes connected to real capabilities
- compatibility routes retained
- files changed
- tests and exact results
- visual verification status
- remaining risks
- confirmation that Stage 2 was not started
```

---

## 8. Review、恢复与纠偏 Prompt

### 8.1 Task 或 Stage Review

```text
Use the refactor-orchestrator skill.
Use the Parent as final reviewer.
Do not delegate final acceptance or start the next Task/Stage.

Apply the Skill runtime-truth policy:
- require evidence for commands, tests, diffs, migrations, acceptance, and completion
- report model, permissions, and spawning details only when verified
- do not force fallback merely because an exact child model is unknown

Strictly review:
[Task ID or Stage]

Read mandatory project documents, current plan, implementation log, complete diff, runtime artifacts, and actual test/migration output.
Check every acceptance criterion, real data, routes, Schema/API/migrations, time semantics, compatibility, permissions, error states, duplicate fact sources, unrelated changes, and documentation accuracy.
Classify findings as BLOCKER, HIGH, MEDIUM, or LOW.
Clear all BLOCKER and required HIGH findings before acceptance.
If repairs are needed, create bounded repair Task Cards, respect the three-round limit, rerun verification, and repeat Parent Review.

Output:
- verified evidence
- findings and repairs
- residual risk
- acceptance conclusion
- whether the next Task/Stage is allowed

Do not continue automatically.
```

### 8.2 新 Session 恢复

```text
Do not infer progress from chat memory.
Work from the Trade repository root.
Read mandatory project documents, Refactor-Implementation-Log.md, current plan, available .codex/refactor-state handoffs, branch, baseline, git status, and diff.
Treat prior model, permission, spawning, and test claims as unverified unless evidence is present.
Report current Task, accepted work, in-progress work, incomplete work, blockers, dirty changes, and the next smallest safe task.
Continue only the actual incomplete Task.
```

### 8.3 完成核验

```text
Recheck completion against AGENTS.md, the authoritative TaskList, implementation plan, complete diff, runtime artifacts, and verification output.
Do not accept subagent, model, permission, test, migration, or completion claims without evidence.
If any required item is missing, use [-] in progress or [!] blocked.
```

### 8.4 跑偏纠正

```text
Stop expansion and do not spawn new agents.
Re-read authoritative documents, current plan, baseline, and complete diff.
Find duplicate facts, out-of-scope work, overlapping writes, missing tests, unsupported runtime claims, fake completion, and later-Stage work.
Repair only the deviation and rerun affected checks.
```

---

## 9. Prompt 调用编排核验

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

---

## 10. 使用结论

1. 从 `Trade` 根目录启动 Orchestrator。
2. 每次显式决定是否委派；不要自动创建 subagent。
3. Parent 读取全局文档，children 只读取 Task Card 和必要上下文。
4. 当前优先使用 RT-S1-002 Session A Prompt。
5. 每个实现 Session 后单独运行 Parent Review。
6. 不根据 subagent 声明直接进入下一 Task。
7. Task 和 Stage 状态始终服从当前实施计划中更严格的验收门禁。
