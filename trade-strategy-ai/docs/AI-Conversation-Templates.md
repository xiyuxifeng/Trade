# Trade Strategy AI 重构对话模板

## 1. 使用说明

本文件用于指导 Codex、Claude Code、Cursor Agent 或其他代码 Agent 完成 `trade-strategy-ai` 重构，并支持 Codex 的 `codex-refactor-orchestrator` Skill。

基本原则：

1. 一次只执行一个明确 Task，或同一 Stage 中紧密关联、共享同一契约且能够共同验收的少量 Task。
2. 每次开始前读取 `AGENTS.md`、正式 TaskList、实施记录、当前实施计划和实际代码。
3. 当前代码、测试、注册关系、数据库迁移和 Git diff 是事实源。
4. 每个 Task 完成后先 Review，再进入下一 Task。
5. 未满足验收、未运行测试或存在阻塞时，禁止声称完成。
6. 不允许形成第二套正式入口、Schema、API、Service、Prompt 链或数据事实源。
7. 不允许使用 Mock、硬编码、空接口或占位页冒充完成。
8. 所有重构文档只能在 `trade-strategy-ai/docs` 中生成和更新。
9. 不要一次连续执行多个 Stage。

---

# 2. codex-refactor-orchestrator

## 2.1 安装与验证

```bash
cd /path/to/codex-refactor-orchestrator
bash install.sh /path/to/Trade/trade-strategy-ai

cd /path/to/Trade/trade-strategy-ai
bash .agents/skills/refactor-orchestrator/scripts/validate-install.sh
bash .agents/skills/refactor-orchestrator/scripts/runtime-probe.sh

codex -m gpt-5.5
```

建议一个 Task 或一个紧密关联的执行批次使用一个新的 GPT-5.5 Session。

## 2.2 固定开场

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.
```

职责边界：

- GPT-5.5 Parent：检查事实、冻结架构和公共契约、创建 Task Card、决定依赖批次、Review 完整 diff 和测试、给出最终验收。
- Explorer mini：只读调查不清晰的调用链、权限、兼容映射和文件归属。
- Executor mini：只执行契约已冻结、范围明确的 Task Card。
- 不得并行修改同一文件、公共契约、Schema、API、数据库迁移或集中事实源。
- native subagent 不可用时使用 single-controller fallback，并明确记录。

---

# 3. Orchestrator 通用 Task 模板是否适用于所有任务

**通用 Task 模板适用于所有 Task 的基础约束，但并不足以单独覆盖所有 Task。**

使用方式：

```text
固定 Orchestrator 开场
+ Orchestrator 通用 Task 模板
+ 当前 Stage / Task 的专用附加 Prompt
+ 当前实施计划中的文件、测试和验收要求
```

以下任务必须追加专用 Prompt：

| 类型 | Task | 原因 | 必须追加的专用约束 |
| --- | --- | --- | --- |
| 信息架构与兼容路由 | RT-S1-001、RT-S1-002、RT-S1-003 | 集中路由、产品模式/兼容模式、真实状态容易形成第二事实源 | Stage 1 产品页面专用 Prompt |
| 领域模型设计 | RT-S2-001 | 需要先冻结跨 Stage 公共对象和版本关系 | 领域契约冻结 Prompt |
| 数据库与迁移 | RT-S2-002、RT-S2-003 | 涉及不可逆风险、迁移顺序、回滚和数据核对 | 数据库迁移安全 Prompt |
| Prompt 接入与退役 | RT-S3-001、RT-S3-004 | 新旧 Prompt 双链、Schema 对照和退役门禁 | Prompt 迁移与退役 Prompt |
| 批量文章处理 | RT-S3-003 | 涉及固定样本、成本、断点续跑和批量重跑风险 | 回归样本与批处理 Prompt |
| 规则审核和去重 | RT-S4-001、RT-S4-002、RT-S4-003 | 自动审核、人工审核、指纹和生命周期相互约束 | 规则审核与规则族 Prompt |
| 数据底座与调度 | RT-S5-001、RT-S5-002、RT-S5-003 | 时间语义、回灌、增量、幂等、调度和修复 | 数据时间语义与调度 Prompt |
| 回测与适用性 | RT-S6-001 至 RT-S6-004 | 防未来数据泄漏、固定快照、分市场状态和可复现 | 回测安全 Prompt |
| 作者画像 | RT-S7-001 至 RT-S7-004 | 三层画像边界、证据和版本发布 | 作者画像边界 Prompt |
| 策略发布与回滚 | RT-S8-001 至 RT-S8-003 | StrategyVersion、Proposal、发布和回滚不可混淆 | 策略版本与 Proposal Prompt |
| 每日盘前 | RT-S9-001 至 RT-S9-003 | 每日实例不能替代正式策略，输入必须可追溯 | 每日盘前 Prompt |
| 每日盘后 | RT-S10-001 至 RT-S10-004 | 程序事实、LLM 解释和 Proposal 必须隔离 | 每日盘后归因 Prompt |
| 可观测性与灰度迁移 | RT-S11-002 至 RT-S11-006 | 自动恢复、run_id、成本、时间语义和回滚 | 运行保障与灰度 Prompt |
| 旧入口退役与最终验收 | RT-S12-001 至 RT-S12-003 | 删除风险、全链路验收和用户交付 | 最终退役与交付 Prompt |

未列出的普通 UI、局部 Service、测试补充和文档任务，可以使用通用模板加当前 Task 验收标准，不必再增加大型专用 Prompt。

---

# 4. Orchestrator 通用 Task 模板

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.

Continue the trade-strategy-ai refactor.
Execute only:
[填写 Task ID 和任务名称]

Read first:
- AGENTS.md and applicable nested instructions
- docs/Trade-Refactor-TaskList.md
- docs/Refactor-Implementation-Log.md
- docs/Refactor-Current-State-Audit.md
- docs/Refactor-Migration-Matrix.md
- current implementation plan and acceptance documents
- current code, tests, git status and git diff

Before delegation:
1. Verify prerequisites and actual current status.
2. Inspect existing implementation and avoid duplication.
3. Freeze architecture, public contracts, Schema, API, migrations, compatibility behavior and verification commands.
4. Decide whether a read-only Explorer is needed.
5. Create bounded Task Cards with allowed files, forbidden files, dependencies, tests and acceptance criteria.

Execution rules:
- Do not cross into the next Task or Stage.
- Do not create a second formal entry, Schema, Service, API, Prompt chain or fact source.
- Do not use mocks, placeholders or hardcoded success.
- Preserve compatibility until retirement conditions are satisfied.
- Do not parallelize overlapping files or shared contracts.
- The GPT-5.5 parent must review the real combined diff and verification evidence.

Run all focused and regression tests required by the Task, plus applicable typecheck, lint, build, backend, migration, Prompt regression or E2E checks, and git diff --check.

Update docs/Refactor-Implementation-Log.md.
Do not mark completion without evidence.
Do not automatically start the next Task.

Final response:
- agents and scopes
- Task Cards
- files changed
- migrations and compatibility
- tests and exact results
- incomplete items and risks
- acceptance conclusion
- confirmation that no later Task or Stage was started
```

---

# 5. 专用附加 Prompt

使用时，把对应段落追加到通用 Task 模板末尾。

## 5.1 Stage 1 产品页面专用 Prompt

```text
Stage 1 special constraints:
- Preserve route-config.tsx as the single route, navigation, permission, metadata and compatibility fact source.
- Formal pages must use business Chinese and must not expose Job, Workflow, Pipeline, Artifact, Provider, force, config_path or internal paths.
- Every formal page must represent 页面用途、输入、处理状态、输出、下一步。
- Support loading, empty, error, partial, permission_denied and unavailable truthfully.
- Do not convert unavailable data into false, zero, an empty list or success.
- Legacy pages remain compatibility-only until retirement conditions pass.
- Do not start RT-S1-003 while executing RT-S1-002.
- Do not enter Stage 2 before Stage 1 exit review.
```

## 5.2 领域契约冻结 Prompt

```text
Domain contract constraints:
- Freeze stable IDs, version relationships, lifecycle states, source references and audit fields before implementation.
- Produce an object relationship map and old-to-new mapping before changing ORM or API code.
- Distinguish formal versions, daily runtime instances, proposals and historical compatibility objects.
- Do not allow Executors to independently redefine shared domain objects.
- Record every unresolved contract decision as a blocker instead of inventing a temporary second model.
```

## 5.3 数据库迁移安全 Prompt

```text
Database migration constraints:
- Inspect all ORM models, Alembic heads, migration imports, existing tables and actual data before writing migrations.
- Freeze the target Schema and migration order before delegation.
- Migrations must be idempotent or safely rerunnable, observable and recoverable.
- Never silently drop or overwrite legacy data.
- Produce pre-migration counts, post-migration counts, rejected rows and quality-status reports.
- Test upgrade, data transformation and rollback/recovery paths.
- Only one Executor may modify a migration chain or shared ORM contract at a time.
- Do not mark completion from unit tests alone; include migration evidence.
```

## 5.4 Prompt 迁移与退役 Prompt

```text
Prompt migration constraints:
- Treat Prompt files, loader code, Pydantic/JSON Schema and regression fixtures as one public contract.
- Record prompt_version, schema_version, model, input_hash, raw output and validation result.
- Compare new and legacy Prompt results on the fixed regression set before changing production routing.
- New Prompt must become the only formal write path before legacy Prompt enters compatibility_only.
- Legacy Prompt must not produce new formal data after cutover.
- Do not delete legacy Prompt until code, tests, scripts, Jobs, Workflows and docs have no references and rollback observation has passed.
```

## 5.5 回归样本与批处理 Prompt

```text
Batch processing constraints:
- First select and freeze 10–15 representative articles and their expected review outcomes.
- Do not run all 100+ articles before the fixed regression set passes.
- Record article_id, content version, Prompt version, output, automatic review and human conclusion.
- Batch execution must support resume, retry, idempotency, concurrency limits and incremental updates.
- Do not send all article bodies in one LLM request.
- Report cost, failures, quality distribution and reprocessing reasons.
```

## 5.6 规则审核与规则族 Prompt

```text
Rule governance constraints:
- Automatic review must be deterministic where possible and cannot make a rule formally usable.
- High-risk, ambiguous, conflicting, parameter-edited and strategy-entry rules require human approval.
- Freeze rule fingerprint, RuleFamily, parameter-variant and conflict semantics before implementation.
- Do not merge semantically different rules merely because text is similar.
- Every lifecycle transition must record actor, time, reason and before/after values.
```

## 5.7 数据时间语义与调度 Prompt

```text
Data and scheduling constraints:
- Preserve trade_date, available_at, captured_at, effective_at, source and slot.
- Separate pre-market and post-market Kaipan data.
- Historical backfill and daily incremental update must be independently testable.
- Tasks must be idempotent, resumable and retryable.
- Missing data must remain missing/unavailable and must not become false or zero.
- Backtests may repair data before a run but must not call live Providers during a run.
- Prevent duplicate schedulers and process-local state drift.
```

## 5.8 回测安全 Prompt

```text
Backtest safety constraints:
- Every run must bind an immutable DatasetSnapshot, rule version, market-state model version and code version.
- Prohibit live Provider calls during backtest execution.
- Verify point-in-time availability for every trading day and prevent future-data leakage.
- Separate Level 1 OHLCV, Level 2 OHLCV plus market state and Level 3 including Kaipan.
- Missing Kaipan is a coverage limitation, not a failed condition.
- Mark insufficient_sample instead of producing strong conclusions.
- Include reproducibility tests and replay evidence.
```

## 5.9 作者画像边界 Prompt

```text
Author profile constraints:
- Keep AuthorMethodProfile, AuthorRuleProfile and AuthorValidatedProfile separate.
- Never describe the result as the author's real trading performance, position, drawdown or discipline.
- Separate article expression, rule statistics and backtest validation in storage and UI.
- Every conclusion requires evidence and confidence.
- New evidence creates drafts or revisions and must not overwrite a published profile.
```

## 5.10 策略版本与 Proposal Prompt

```text
Strategy constraints:
- StrategyVersion is a formal version and must not be regenerated daily.
- DailyStrategyInstance is a runtime object, not a new StrategyVersion.
- StrategyRevisionProposal cannot directly modify a published strategy.
- Freeze lifecycle, validation, publication, current-use, archive and rollback behavior before implementation.
- Every release and rollback requires evidence, actor and version-diff records.
```

## 5.11 每日盘前 Prompt

```text
Pre-market constraints:
- Complete data, market-state, strategy and rule-applicability checks before selection.
- Generate DailyRuleSelection, DailyStrategyInstance and TradingDayPlan; do not create a new formal strategy.
- Explain enabled, reduced and suspended rules.
- Every result must trace to all input versions and data-quality states.
- Missing inputs require repair or explicit degradation, never silent defaults.
```

## 5.12 每日盘后归因 Prompt

```text
Post-market constraints:
- Program facts calculate trigger, execution, MFE, MAE, return and market-state change.
- LLM may validate or explain but must not recompute program metrics.
- Use llm_attribution_v1 only for low confidence, conflicting evidence or important signals.
- Keep RuleOptimizationProposal, AuthorProfileRevisionProposal and StrategyRevisionProposal separate.
- A single day must never directly modify formal rules, profiles or strategies.
```

## 5.13 运行保障与灰度 Prompt

```text
Operations constraints:
- Use stable run_id and record every step, duration, error and retry.
- Record Prompt model/version/Schema/Tokens/cost and data source/range/coverage/time semantics.
- Recovery must support resume, retry limits and operator-visible actions.
- Freeze rollout stages: comparison, read-only, limited enablement, default, legacy read-only, retirement.
- Provide rollback or recovery for database, Prompt and batch-processing changes.
- User-facing errors must explain what happened, impact and remediation.
```

## 5.14 最终退役与交付 Prompt

```text
Final retirement constraints:
- Before deleting an entry, verify its migration target, data migration, reference scan, observation period and rollback evidence.
- Do not retire legacy paths merely because the new page exists.
- Run the complete real-data journey from article import through optimization proposals.
- Run E2E, frontend, backend, migration and Prompt regression suites.
- Verify user and administrator documentation against the actual UI.
- Any failed final acceptance item blocks Stage 12 completion.
```

---

# 6. 哪些 Task 可以放在一起执行

“紧密关联的少量 Task”必须同时满足：

1. 属于同一 Stage。
2. 共享同一业务闭环或同一已冻结契约。
3. 前一个 Task 的输出不需要经过独立数据迁移或观察期，后一个 Task 才能安全开始。
4. 可以在一个 Session 内共同测试和验收。
5. 不要求多个 Executor 同时修改同一公共文件或迁移链。
6. 合并后范围仍能被 GPT-5.5 完整 Review。

下表是推荐执行矩阵：

| Stage | Task 组合 | 是否建议同一 Session | 执行方式 | 原因与限制 |
| --- | --- | --- | --- | --- |
| Stage 0 | RT-S0-001 + RT-S0-002 | 可以 | 串行 | 都是只读审计文档；先审计，再生成迁移矩阵。已完成。 |
| Stage 1 | RT-S1-001 | 单独 | 单 Task | 集中路由和权限是后续公共契约，必须先独立冻结。已完成。 |
| Stage 1 | RT-S1-002 | 单独但拆两 Session | Session A/B | 共享组件和正式页面装配范围较大；不要与首页聚合混在一起。 |
| Stage 1 | RT-S1-003 | 单独 | 单 Task | 同时涉及后端聚合、API 和首页 UI，需独立验收。 |
| Stage 2 | RT-S2-001 | 单独 | 单 Task | 必须先冻结全局领域契约。 |
| Stage 2 | RT-S2-002 + RT-S2-003 | 不建议一次完成 | 连续 Session | 先建 Schema 和迁移骨架，再用真实数据迁移；数据迁移必须独立核对和恢复。 |
| Stage 3 | RT-S3-001 + RT-S3-002 | 可以，有条件 | 串行同 Session | Prompt 契约与单篇闭环紧密关联；仅在版本化 Prompt 和 Schema 已冻结后执行。 |
| Stage 3 | RT-S3-003 | 单独 | 单 Task | 固定样本、批处理、成本和恢复范围较大。 |
| Stage 3 | RT-S3-004 | 单独且最后 | 单 Task | 需要观察期、引用扫描和回滚验证，不能与新 Prompt 接入同时宣布完成。 |
| Stage 4 | RT-S4-002 + RT-S4-003 | 可以，有条件 | 串行同 Session | 规则指纹/规则族与生命周期关联；先冻结状态和合并语义。 |
| Stage 4 | RT-S4-001 | 建议单独 | 单 Task | 自动审核、人工 UI 和审计范围大，并依赖规则族契约。也可先实现审核基础，再接 RT-S4-002/003。 |
| Stage 5 | RT-S5-001 + RT-S5-002 | 可并行探索，不建议同一 Executor | 同 Session 多批次 | OHLCV 与 Kaipan 写集通常不同，但共享时间语义和快照契约；Parent 先冻结契约。 |
| Stage 5 | RT-S5-003 | 后置单独 | 单 Task | 依赖两个数据体系的稳定命令、状态和修复动作。 |
| Stage 6 | RT-S6-001 + RT-S6-002 | 可以，有条件 | 串行同 Session | 工作台与分市场状态执行链共享回测契约；先冻结防未来数据规则。 |
| Stage 6 | RT-S6-003 + RT-S6-004 | 可以 | 串行同 Session | 适用性画像和回测分级都是回测结果契约的派生。 |
| Stage 6 | RT-S6-001 至 RT-S6-004 | 不建议一次全部实现 | 两个 Session | 范围过大，建议按“执行引擎/工作台”和“结果画像/分级”拆分。 |
| Stage 7 | RT-S7-001 + RT-S7-002 | 可以 | 同 Session 多批次 | 共享文章和规则证据，但存储与生成职责可分离。 |
| Stage 7 | RT-S7-003 + RT-S7-004 | 可以，有条件 | 串行同 Session | 验证画像依赖 Stage 6，版本发布必须在三层画像契约稳定后。 |
| Stage 8 | RT-S8-001 + RT-S8-002 | 可以，有条件 | 串行同 Session | 策略生命周期、验证、发布和回滚是同一闭环；先冻结版本状态机。 |
| Stage 8 | RT-S8-003 | 单独或与盘后接口设计联合规划 | 单 Task | Proposal 由盘后产生但不应提前实现盘后业务。 |
| Stage 9 | RT-S9-001 + RT-S9-002 | 可以 | 串行同 Session | 前置检查直接决定每日规则选择。 |
| Stage 9 | RT-S9-003 | 建议后置单独 | 单 Task | 盘前计划 UI 和每日实例需要前两项稳定输出。 |
| Stage 10 | RT-S10-001 + RT-S10-002 | 可以 | 串行同 Session | 信号事实与结构化归因是同一数据链。 |
| Stage 10 | RT-S10-003 + RT-S10-004 | 可以，有条件 | 串行同 Session | Proposal 与盘后页面紧密关联；必须先有稳定归因契约。 |
| Stage 11 | RT-S11-002 + RT-S11-003（运行追踪） | 可以，有条件 | 串行同 Session | 自动恢复依赖统一 run_id 和步骤状态；先冻结运行契约。 |
| Stage 11 | RT-S11-004 + RT-S11-005 | 可以，有条件 | 同 Session 多批次 | 成本/增量与时间语义相关，但避免同时修改同一核心模型。 |
| Stage 11 | RT-S11-006 | 单独且后置 | 单 Task | 灰度和回滚需要前面各链路稳定及观察证据。 |
| Stage 11 | RT-S11-001 | 可与用户友好错误子任务一起 | 同 Session | 都是系统管理展示层；注意 TaskList 中“用户友好错误”编号与 RT-S11-003 重复，执行前必须先修正文档编号。 |
| Stage 12 | RT-S12-001 | 单独 | 单 Task | 删除旧入口属于高风险变更，必须先满足退役门禁。 |
| Stage 12 | RT-S12-002 + RT-S12-003 | 可以，有条件 | 串行同 Session | E2E 验收通过后可同步修正文档；文档必须以实际 UI 和操作结果为准。 |

## 6.1 不得合并的典型情况

- `RT-S2-001` 与 `RT-S2-003`：领域契约尚未冻结就迁移数据。
- `RT-S3-001` 与 `RT-S3-004`：新 Prompt 刚接入就立即删除旧 Prompt，没有观察期。
- `RT-S5-001/002` 与 `RT-S5-003` 一次并行完成：调度 UI 可能绑定尚未稳定的执行契约。
- `RT-S8-001` 与 `RT-S9-003`：正式策略版本与每日实例容易混淆。
- `RT-S10-001` 与 `RT-S10-003` 并行：归因事实未稳定就生成优化建议。
- `RT-S11-006` 与其他 Stage 11 实现并行：灰度与回滚必须建立在稳定链路上。
- `RT-S12-001` 与任何未完成迁移的 Task：不能提前删除兼容入口。

---

# 7. 当前下一步：RT-S1-002

当前状态：

- `RT-S1-001` 已完成。
- `RT-S1-002` 下一步执行。
- `RT-S1-003` 尚未开始。
- Stage 1 尚未完成。

推荐：

```text
Session A：共享页面框架和布局接入
→ Review 和修复
→ Session B：正式业务入口装配和 RT-S1-002 验收
```

## 7.1 Session A Prompt

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.

Execute only the shared-framework and shared-layout portion of RT-S1-002.

Read:
- AGENTS.md
- docs/2026-06-10-stage-1-implementation-plan.md
- docs/Refactor-Implementation-Log.md
- docs/Refactor-Migration-Matrix.md
- docs/Trade-Refactor-TaskList.md
- current code, tests, git status and git diff

Implement and verify:
- BusinessPageShell
- SectionNav
- CompatibilityNotice
- ProductPageAdapter
- DashboardLayout integration
- StatusStrip cleanup
- route permission behavior

Freeze all shared public contracts before delegation.
Preserve route-config.tsx as the only route/navigation/permission fact source.
Do not assemble all domain pages yet.
Do not start RT-S1-003 or Stage 2.
Do not add migrations or modify Prompt behavior.

Apply the Stage 1 special constraints from this document.
Use TDD.
Run focused component tests, pnpm typecheck, pnpm lint, pnpm build, full pnpm test and git diff --check.
Update Refactor-Implementation-Log.md as partial RT-S1-002 progress.
Normally keep RT-S1-002 in progress after this Session.

Report agents, Task Cards, contracts, files, tests, visual verification and remaining Session B work.
```

## 7.2 Session B Prompt

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.

Continue only RT-S1-002 after verifying Session A contracts and tests.

Assemble the formal product routes required by docs/2026-06-10-stage-1-implementation-plan.md:
- research
- rules and backtest
- authors
- strategies
- daily trading
- applicable system pages

Reuse real hooks, actions and result components.
Do not duplicate domain logic or invent unavailable facts.
Keep legacy routes in compatibility mode.
Apply the Stage 1 special constraints from this document.

Verify the formal journey:
研究中心 → 待审核规则 → 回测实验 → 作者画像 → 策略中心 → 今日盘前 → 今日盘后

The formal journey must not require /jobs, /workflows, /artifacts or /market/* technical workbenches.

Run product entry tests, page-state matrix, product journey, affected page regressions, pnpm typecheck, pnpm lint, pnpm build, full pnpm test and git diff --check.
Perform desktop/mobile visual verification when available.
Update Refactor-Implementation-Log.md.

Mark only RT-S1-002 complete when all acceptance evidence passes.
Do not start RT-S1-003 or Stage 2.
```

---

# 8. Orchestrator Review 模板

```text
Use the refactor-orchestrator skill.

Use the GPT-5.5 parent as final reviewer.
Use read-only Explorer subagents only when additional evidence is required.
Do not delegate final acceptance to an Executor.
Do not start the next Task or Stage.

Strictly review:
[Task ID or Stage]

Read the TaskList, implementation log, plans, current code, complete git diff and actual verification output.

Check every acceptance criterion, real data use, registered routes, Schema/API/migrations, compatibility, permissions, error states, duplicate fact sources, unrelated changes and implementation-log accuracy.

If issues exist, create bounded repair Task Cards, repair, rerun tests and repeat GPT-5.5 review.

Output satisfied criteria, unsatisfied criteria, blockers, repairs, tests, risks, acceptance conclusion and whether the next Task or Stage is allowed.
Do not enter the next Task or Stage automatically.
```

---

# 9. 新 Session、完成核验与纠偏

## 9.1 新 Session

```text
Do not infer progress from chat memory.
Read AGENTS.md, Trade-Refactor-TaskList.md, Refactor-Implementation-Log.md, audit, migration matrix, current plan, git status and git diff.
Report current Task, completed work, incomplete work, blockers and the next smallest task.
Continue only the actual incomplete Task.
```

## 9.2 AI 声称完成时

```text
Recheck the claimed completion against AGENTS.md, the TaskList, the implementation plan, the complete git diff and actual test output.
Verify real data, formal API wiring, migrations, all states, user path, documentation, compatibility and scope boundaries.
If any item is missing, change status to in progress or blocked.
```

## 9.3 跑偏时

```text
Stop expansion and do not spawn new agents.
Re-read the TaskList, implementation log, current plan and complete git diff.
Find duplicate facts, out-of-scope work, overlapping Executor writes, missing tests, fake completion and later-Stage work.
Revert or repair the deviation, rerun tests and report actual status.
```

---

# 10. Prompt 调用编排核验

```text
Verify compliance with docs/LLM-Prompt-Orchestration.md:
- one normal article_analysis_v1 main call
- at most one targeted article_analysis_repair_v1 when needed
- no per-article author-profile Prompt
- conditional llm_attribution_v1 only
- Prompt/Schema/model/Token/cost/input_hash records
- cache and idempotency
- legacy Prompt no longer writes formal data
- deletion only after retirement acceptance
```
