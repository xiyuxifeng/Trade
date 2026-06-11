# Trade Strategy AI 重构对话模板

## 1. 仓库范围与基本原则

仓库根目录：`Trade`；业务项目：`Trade/trade-strategy-ai`。

- Codex 和 Orchestrator 从 `Trade` 根目录启动。
- 业务代码通常只修改 `trade-strategy-ai`。
- 正式文档只放在 `trade-strategy-ai/docs`。
- `.codex/refactor-state` 仅保存临时执行证据，不能替代正式文档。
- 默认一次只执行一个 Task；只有用户明确指定时，才可组合同一 Stage 中紧密关联、共享冻结契约且可共同验收的少量 Task。
- 不跨 Stage 合并执行。
- 不建立第二套正式入口、Schema、API、Service、Prompt 链或事实源。
- 不使用 Mock、硬编码、空接口或占位页冒充完成。

## 2. 必读顺序

1. `AGENTS.md`
2. `trade-strategy-ai/docs/Trade-Refactor-TaskList.md`
3. `trade-strategy-ai/docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`
4. `trade-strategy-ai/docs/PROMPT_REVIEW_AND_MIGRATION.md`
5. `trade-strategy-ai/docs/AUTHOR_PROFILE_PROMPT_FLOW.md`
6. `trade-strategy-ai/docs/LLM-Prompt-Orchestration.md`
7. `trade-strategy-ai/docs/Refactor-Implementation-Log.md`
8. 当前 Task 的设计、实施、迁移和验收文档
9. 当前分支、基线、未提交修改、代码、测试、数据库和 API

优先级：

```text
AGENTS.md
> Trade-Refactor-TaskList.md
> 最新正式方案
> 当前 Task 实施计划
> Refactor-Implementation-Log.md
> 历史文档
```

`trade-strategy-ai/docs/bak` 仅供历史参考。

## 3. codex-refactor-orchestrator

### 3.1 安装与启动

```bash
cd /path/to/codex-refactor-orchestrator
bash install.sh /path/to/Trade

cd /path/to/Trade
bash .agents/skills/refactor-orchestrator/scripts/validate-install.sh
bash .agents/skills/refactor-orchestrator/scripts/runtime-probe.sh
codex -m gpt-5.5
```

### 3.2 固定开场

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.
```

小型局部任务可以由 Parent 直接完成，Agent 数量可以为 0。

### 3.3 运行证据说明

完整规则以 `.agents/skills/refactor-orchestrator/SKILL.md` 为准。

配置文件和 `runtime-probe.sh` 只能表示预期配置，不能单独证明实际模型、权限或 subagent 已生效。执行所需的最小规则已经直接写入下方可复制 Prompt，因此执行任务时不依赖 Agent 额外读取本节。

### 3.4 角色和风险

- Parent：冻结架构、领域、API、Schema、权限、迁移、回滚和兼容契约，创建 Task Card，Review 完整 diff 和测试，负责最终验收。
- Explorer：只读调查调用链、数据流、引用、legacy 和重复实现。
- Executor：只执行契约已冻结、范围明确的 Task Card。

| 等级 | 执行方式 | 典型任务 |
| --- | --- | --- |
| M1 | Executor 主导，Parent Review | 局部组件、机械修复 |
| M2 | Parent 冻结契约，Executor 实现 | 可冻结接口的跨层功能 |
| M3 | Parent 主导 | 领域模型、迁移、权限、时间语义、不可逆删除 |

每个 Task Card 至少包含：Task ID、风险、目标、依赖、基线、必读文件、冻结契约、允许/禁止路径、实现要求、验证命令、验收标准和 handoff。

正常批次限制为 1～3 个 Executor；写入路径或公共契约重叠时不得并行。同一委派 Task 最多三轮实现/修复，三轮后仍失败则标记阻塞。

## 4. 通用模板与专用约束

正确组合：

```text
通用 Task Prompt（已包含固定开场和运行证据规则）
+ 当前 Task 专用约束
+ 当前实施计划的文件、测试和验收要求
```

| Task 类型 | Task | 专用约束 |
| --- | --- | --- |
| 产品页面与首页 | RT-S1-001～RT-S1-003 | Stage 1 产品页面 |
| 领域模型 | RT-S2-001 | 领域契约冻结 |
| 数据库与迁移 | RT-S2-002～RT-S2-003 | 数据库迁移安全 |
| Prompt 套件 | RT-S3-001、RT-S3-004 | Prompt 迁移与退役 |
| 单篇文章闭环 | RT-S3-002 | 单篇文章闭环 + Prompt 迁移 |
| 批量文章 | RT-S3-003 | 回归样本与批处理 |
| 规则治理 | RT-S4-001～RT-S4-003 | 规则治理 |
| 数据与调度 | RT-S5-001～RT-S5-003 | 数据时间语义与调度 |
| 回测 | RT-S6-001～RT-S6-004 | 回测安全 |
| 作者画像 | RT-S7-001～RT-S7-004 | 作者画像边界 |
| 策略 | RT-S8-001～RT-S8-003 | 策略版本与 Proposal |
| 每日盘前 | RT-S9-001～RT-S9-003 | 每日盘前 |
| 每日盘后 | RT-S10-001～RT-S10-004 | 每日盘后归因 |
| 系统管理 | RT-S11-001～RT-S11-007 | 运行保障与系统管理 |
| 最终交付 | RT-S12-001～RT-S12-003 | 最终退役与交付 |

## 5. Orchestrator 通用 Task Prompt

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.

Runtime truth requirements:
- Verify actual native subagent spawning before reporting that subagents were used.
- TOML configuration and runtime-probe.sh show expected configuration only; they do not prove the actual runtime model or effective permissions.
- Report a model or permission only when runtime evidence supports it.
- When native spawning, runtime identity, or effective permissions cannot be verified, use single-controller fallback and state that explicitly.
- Do not report a subagent, model, permission, test result, or Task completion as verified without runtime, command, or workspace evidence.

Work from the Trade repository root.
Limit business implementation changes to trade-strategy-ai.
Store formal refactor documents only under trade-strategy-ai/docs.

Execute only:
[Task ID and title]

Read in order:
1. AGENTS.md
2. trade-strategy-ai/docs/Trade-Refactor-TaskList.md
3. trade-strategy-ai/docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md
4. trade-strategy-ai/docs/PROMPT_REVIEW_AND_MIGRATION.md
5. trade-strategy-ai/docs/AUTHOR_PROFILE_PROMPT_FLOW.md
6. trade-strategy-ai/docs/LLM-Prompt-Orchestration.md
7. trade-strategy-ai/docs/Refactor-Implementation-Log.md
8. current Task design, implementation, migration and acceptance documents
9. current branch, baseline, dirty changes, code, tests, database and registered APIs

Before delegation:
- verify prerequisites and current status
- inspect existing implementation and avoid duplication
- record branch, baseline and dirty changes
- apply the Runtime truth requirements above
- classify work as M1, M2 or M3
- freeze architecture, public contracts, Schema, API, permissions, migrations, rollback, compatibility and verification commands
- use Explorer only when investigation is necessary
- create bounded Task Cards with allowed and forbidden paths

Execution rules:
- do not cross into the next Task or Stage
- do not create duplicate formal entries, Schema, Service, API, Prompt chains or fact sources
- do not use mocks or placeholders to claim completion
- preserve compatibility until retirement conditions pass
- do not parallelize overlapping files, migrations or contracts
- use 1–3 Executors per normal batch
- limit each delegated Task to three implementation/fix rounds
- inspect the shared workspace and actual diff after every batch
- do not rely only on a subagent completion message

Verification:
- run focused and affected regression tests
- run applicable typecheck, lint, build, API, migration, Prompt regression, E2E and manual checks
- run git diff --check
- record exact commands, counts, failures, skipped checks and residual risk

Documentation:
- update trade-strategy-ai/docs/Refactor-Implementation-Log.md
- use [ ], [-], [x], [!], [~] status markers
- update authoritative status only after Parent acceptance
- do not automatically start the next Task

Final response:
- verified runtime mode and actual agents
- models/permissions only when verified
- fallback mode when applicable
- risk classification and Task Cards
- files changed
- migrations, compatibility and rollback
- tests and exact results
- visual/manual verification
- incomplete items and risks
- acceptance conclusion
- confirmation that no later Task or Stage was started
```

## 6. 专用附加约束

### 6.1 Stage 1 产品页面

```text
- Preserve trade-strategy-ai/web/src/app/route-config.tsx as the single route, navigation, permission, metadata and compatibility fact source.
- Formal pages use business Chinese and do not expose Job, Workflow, Pipeline, Artifact, Provider, force, config_path, database names or internal paths.
- Every formal page represents 页面用途、输入、处理状态、输出、下一步。
- Support loading, empty, error, partial, permission_denied and unavailable truthfully.
- Do not convert unavailable data into false, zero, an empty list or success.
- Legacy pages remain compatibility-only until retirement conditions pass.
- Do not start RT-S1-003 while executing RT-S1-002.
- Do not enter Stage 2 before Stage 1 exit Review.
```

### 6.2 领域契约冻结

```text
- Freeze stable IDs, version relationships, lifecycle states, source references and audit fields before implementation.
- Produce object relationships and old-to-new mappings before changing ORM, API or frontend types.
- Distinguish formal versions, daily runtime instances, proposals and compatibility objects.
- Do not delegate unresolved source-of-truth decisions.
```

### 6.3 数据库迁移安全

```text
- Inspect ORM models, metadata imports, Alembic heads, existing tables and actual data first.
- Freeze target Schema and migration order before delegation.
- Migrations must be safely rerunnable, observable and recoverable.
- Never silently drop or overwrite legacy data.
- Produce pre/post counts, rejected rows and quality reports.
- Test upgrade, transformation and rollback/recovery paths.
- Only one writer modifies a migration chain or shared ORM contract.
```

### 6.4 Prompt 迁移与退役

```text
- Treat Prompt files, loader code, Schema and regression fixtures as one contract.
- Record prompt_version, schema_version, model, input_hash, raw output, validation, tokens and cost.
- Compare new and legacy results on the fixed regression set before cutover.
- New Prompt becomes the only formal write path before legacy becomes compatibility_only.
- Do not delete legacy Prompt until all references, observation and rollback checks pass.
```

### 6.5 单篇文章闭环

```text
- A normal article uses article_analysis_v1 as one main call.
- article_analysis_repair_v1 is targeted and used at most once.
- Modular extraction Prompts are Schema/test tools, not four default production calls.
- Preserve original text, evidence, explicit facts, hypotheses, missing fields, dependencies and backtestability.
- Automatic pass means pending backtest, not formally usable.
- Only human-reviewed results may create a formal RuleVersion.
```

### 6.6 回归样本与批处理

```text
- Freeze 10–15 representative articles and expected outcomes first.
- Do not process all 100+ articles before the fixed set passes.
- Record article/content versions, Prompt/Schema versions, raw output, automatic review and human conclusion.
- Support resume, bounded retry, idempotency, concurrency limits and incremental updates.
- Do not send all article bodies in one LLM request.
```

### 6.7 规则治理

```text
- Automatic review cannot make a rule formally usable.
- High-risk, ambiguous, conflicting, parameter-edited and strategy-entry rules require human approval.
- Freeze fingerprint, RuleFamily, parameter variant, conflict and lifecycle semantics.
- Every transition records actor, time, reason and before/after values.
```

### 6.8 数据时间语义与调度

```text
- Preserve trade_date, available_at, captured_at, effective_at, source and slot.
- Separate pre-market and post-market Kaipan data.
- Backfill and daily incremental update are independently testable.
- Tasks are idempotent, resumable and retryable.
- Missing data remains unavailable, not false or zero.
- Backtests do not call live Providers during execution.
```

### 6.9 回测安全

```text
- Bind every run to DatasetSnapshot, rule version, market-state model version and code version.
- Prevent future-data leakage and live Provider calls.
- Separate Level 1 OHLCV, Level 2 OHLCV + market state, and Level 3 including Kaipan.
- Missing Kaipan is a coverage limitation.
- Mark insufficient_sample instead of producing strong conclusions.
- Include replay and reproducibility evidence.
```

### 6.10 作者画像边界

```text
- Keep AuthorMethodProfile, AuthorRuleProfile and AuthorValidatedProfile separate.
- Do not describe results as the author's real trading performance.
- Separate article expression, rule statistics and backtest validation.
- Every conclusion has evidence and confidence.
- New evidence creates drafts/revisions and does not overwrite published profiles.
- Batch method profiles use 10–20 structured articles.
```

### 6.11 策略版本与 Proposal

```text
- StrategyVersion is formal and is not regenerated daily.
- DailyStrategyInstance is a runtime object.
- StrategyRevisionProposal cannot directly modify a published strategy.
- Freeze lifecycle, validation, publication, current-use, archive and rollback behavior.
```

### 6.12 每日盘前

```text
- Complete data, market-state, strategy and applicability checks before selection.
- Generate DailyRuleSelection, DailyStrategyInstance and TradingDayPlan, not a formal strategy version.
- Explain enabled, reduced and suspended rules.
- Trace every result to input versions and data-quality states.
- Missing inputs require repair or explicit degradation.
```

### 6.13 每日盘后归因

```text
- Program facts calculate trigger, execution, MFE, MAE, return and market-state change.
- LLM validates or explains but does not recompute program metrics.
- Use llm_attribution_v1 only for low confidence, conflict or important signals.
- Use llm_postmortem_notes_v1 conditionally or once for daily summary.
- Keep rule, author and strategy proposals separate.
- A single day never directly modifies formal objects.
```

### 6.14 运行保障与系统管理

```text
- Separate normal-user status/actions from administrator technical details.
- Use stable run_id and record steps, duration, errors and retries.
- Record Prompt model/version/Schema/tokens/cost and data range/coverage/time semantics.
- Recovery supports resume, retry limits and visible actions.
- User errors explain what happened, impact and remediation.
- Freeze rollout stages and provide rollback/recovery.
```

### 6.15 最终退役与交付

```text
- Before deletion, verify target migration, data migration, reference scan, observation period and rollback evidence.
- Do not retire legacy paths merely because a new page exists.
- Run the full real-data journey.
- Run E2E, frontend, backend, migration and Prompt regression suites.
- Verify user/admin documentation against the actual UI.
```

## 7. 可组合执行矩阵

| Stage | Task 组合 | 建议 |
| --- | --- | --- |
| 0 | RT-S0-001 + RT-S0-002 | 可以，同 Session 串行；已完成 |
| 1 | RT-S1-001 | 单独；已完成 |
| 1 | RT-S1-002 | 单独，拆 Session A/B |
| 1 | RT-S1-003 | 单独 |
| 2 | RT-S2-001、RT-S2-002、RT-S2-003 | 分别单独，M3 |
| 3 | RT-S3-001 + RT-S3-002 | 有条件，默认分两 Session；同 Session 时串行 |
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

不得组合：RT-S2-001 与 RT-S2-003、RT-S3-001 与 RT-S3-004、未稳定的数据任务与 RT-S5-003、RT-S8-001 与 RT-S9-003、RT-S10-001 与 RT-S10-003、灰度迁移与被灰度实现、旧入口退役与未完成迁移。

Stage 5 和 Stage 6 的“部分并行”不表示可在一个 Prompt 中跨 Stage 合并。需要用户明确授权、不同 Parent Session/工作范围和稳定的数据契约。

## 8. 当前下一步：RT-S1-002

当前状态：RT-S1-001 已完成；RT-S1-002 是下一步；RT-S1-003 尚未开始；Stage 1 尚未完成。

Stage 1 实施计划要求 Task 1～8 和共享门禁全部通过后，三个 Task 才能标记 `[x]`。Session A/B 只是 RT-S1-002 实现批次。Session B 后通常保持 `[-]`，直到 RT-S1-003、视觉验收、全量回归、E2E、静态门禁和最终工作区检查通过。

执行顺序：

```text
Session A
→ Parent Review
→ Session B
→ Parent Review
→ RT-S1-003
→ Stage 1 完整验收
```

### 8.1 Session A Prompt

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.

Runtime truth requirements:
- Verify actual native subagent spawning before reporting that subagents were used.
- TOML configuration and runtime-probe.sh show expected configuration only; they do not prove the actual runtime model or effective permissions.
- Report a model or permission only when runtime evidence supports it.
- When spawning, runtime identity, or permissions cannot be verified, use single-controller fallback and state that explicitly.
- Do not report a subagent, model, permission, test result, or Task completion as verified without runtime, command, or workspace evidence.

Work from the Trade repository root. Limit business changes to trade-strategy-ai.
Execute only the shared-framework and shared-layout portion of RT-S1-002.

Read the mandatory documents in section 2, then read:
- trade-strategy-ai/docs/2026-06-10-stage-1-implementation-plan.md
- current branch, baseline, dirty changes, code, tests and diff

Freeze PageAvailability, BusinessPageShell, ProductPageAdapter, SectionNav, CompatibilityNotice and DashboardLayout contracts before delegation.

Implement only:
- business-page-shell.tsx and tests
- section-nav.tsx and tests
- compatibility-notice.tsx and tests
- product-page-adapter.tsx and tests
- DashboardLayout and StatusStrip integration
- route permission behavior

Apply section 6.1 constraints. Preserve route-config.tsx as the only route/navigation/permission fact source.
Do not assemble all domain pages, start RT-S1-003/Stage 2, add migrations or modify Prompt behavior.

Run:
cd trade-strategy-ai/web
pnpm test -- src/components/layout/business-page-shell.test.tsx src/components/layout/section-nav.test.tsx src/components/layout/compatibility-notice.test.tsx src/components/layout/product-page-adapter.test.tsx src/components/layout/sidebar.test.tsx src/components/layout/status-strip.test.tsx
pnpm typecheck
pnpm lint
pnpm build
pnpm test
cd ../..
git diff --check

Update Refactor-Implementation-Log.md with [-] evidence. Do not mark RT-S1-002 complete.
Report verified runtime mode, actual agents, risks, Task Cards, contracts, files, tests, visual status, remaining work and scope confirmation.
```

### 8.2 Session B Prompt

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.

Runtime truth requirements:
- Verify actual native subagent spawning before reporting that subagents were used.
- TOML configuration and runtime-probe.sh show expected configuration only; they do not prove the actual runtime model or effective permissions.
- Report a model or permission only when runtime evidence supports it.
- When spawning, runtime identity, or permissions cannot be verified, use single-controller fallback and state that explicitly.
- Do not report a subagent, model, permission, test result, or Task completion as verified without runtime, command, or workspace evidence.

Work from the Trade repository root. Continue only RT-S1-002 after verifying Session A.
Read the mandatory documents, Stage 1 implementation plan, shared components, route-config.tsx, branch, baseline, dirty changes and complete diff.

Assemble formal product routes for research, rules/backtest, authors, strategies, daily trading and applicable system pages.
Reuse real hooks, actions and results. Do not invent unavailable facts. Keep legacy paths in compatibility mode. Apply section 6.1 constraints.

Verify the journey:
研究中心 → 待审核规则 → 回测实验 → 作者画像 → 策略中心 → 今日盘前 → 今日盘后

Do not require /jobs, /workflows, /artifacts or /market/* workbenches.
Only Parent or one designated Executor may modify route-config.tsx and shared state matrices.

Run:
cd trade-strategy-ai/web
pnpm test -- src/pages/product-entry-pages.test.tsx src/pages/product-page-state-matrix.test.tsx src/app/product-journey.test.tsx src/components/layout/product-page-adapter.test.tsx src/pages/articles/index.test.tsx src/pages/rule-pool/index.test.tsx src/pages/backtest/index.test.tsx src/pages/strategies/lifecycle.test.tsx src/pages/system/index.test.tsx
pnpm typecheck
pnpm lint
pnpm build
pnpm test
cd ../..
git diff --check

Update Refactor-Implementation-Log.md. Keep RT-S1-002 as [-] until the shared Stage 1 final gates pass. Missing Browser/E2E evidence is not sufficient for [x]. Do not start Stage 2.
Report verified runtime mode, actual agents, Task Cards, routes, compatibility, tests, visual status, risks and scope confirmation.
```

## 9. Review、恢复和纠偏

### 9.1 Review Prompt

```text
Use the refactor-orchestrator skill.
Use GPT-5.5 Parent as final reviewer.
Do not delegate final acceptance or start the next Task/Stage.

Runtime truth requirements:
- Do not accept claimed subagent spawning, model identity, effective permissions, test results, or Task completion without runtime, command, or workspace evidence.
- TOML configuration and runtime-probe.sh prove expected configuration only.
- When runtime identity or permissions cannot be verified, record the uncertainty and evaluate the work as single-controller fallback.

Strictly review:
[Task ID or Stage]

Read mandatory documents, current plan, implementation log, complete diff, runtime artifacts and actual test/migration output.
Check every acceptance criterion, real data, routes, Schema/API/migrations, time semantics, compatibility, permissions, error states, duplicate facts, unrelated changes and documentation accuracy.
Classify findings as BLOCKER, HIGH, MEDIUM or LOW. Clear BLOCKER and required HIGH findings before acceptance.
Use bounded repair Task Cards and respect the three-round limit.
Output verified runtime facts, findings, repairs, evidence, residual risk, acceptance conclusion and whether the next Task/Stage is allowed.
```

### 9.2 新 Session 恢复

```text
Do not infer progress from chat memory.
Read mandatory documents, implementation log, current plan, available .codex/refactor-state handoffs, branch, baseline, git status and diff.
Treat prior model, permission, subagent and test claims as unverified unless evidence is present.
Report current Task, accepted work, in-progress work, blockers, dirty changes and the next smallest safe task.
```

### 9.3 完成核验

```text
Recheck completion against AGENTS.md, TaskList, implementation plan, complete diff, runtime artifacts and verification output.
Do not accept subagent, model, permission, test or completion claims without evidence.
If any required item is missing, use [-] in progress or [!] blocked.
```

### 9.4 跑偏纠正

```text
Stop expansion and do not spawn new agents.
Re-read authoritative documents, current plan, baseline and complete diff.
Find duplicate facts, out-of-scope work, overlapping writes, missing tests, unsupported runtime claims, fake completion and later-Stage work.
Repair only the deviation and rerun affected checks.
```

## 10. Prompt 调用编排核验

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

## 11. 使用结论

1. 从 `Trade` 根目录安装并启动 Orchestrator。
2. 通用 Prompt 已包含固定开场和 runtime truth 规则，不要重复追加。
3. 追加当前 Task 的专用约束。
4. 当前优先使用 RT-S1-002 Session A Prompt。
5. 每个实现 Session 后单独运行 Parent Review。
6. 不根据 subagent 声明直接进入下一 Task。
7. 状态始终服从当前实施计划中更严格的验收门禁。
