# Trade Strategy AI 重构对话模板

## 1. 文档用途

本文件用于指导 Codex、Claude Code、Cursor Agent 或其他代码 Agent 完成 `trade-strategy-ai` 重构，并为 Codex 提供 `codex-refactor-orchestrator` 的项目专用 Prompt。

本项目的 Git 仓库根目录是 `Trade`，业务项目位于：

```text
Trade/trade-strategy-ai
```

因此：

- Codex 和 Orchestrator 必须从 `Trade` 仓库根目录启动；
- `.agents`、`.codex` 和根级 `AGENTS.md` 位于 `Trade` 根目录；
- 业务代码修改范围通常限制在 `trade-strategy-ai`；
- 重构正式文档只能放在 `trade-strategy-ai/docs`；
- 临时 Orchestrator 执行记录可以放在 `.codex/refactor-state`，但不能把它当成正式 TaskList、设计或验收文档。

基本原则：

1. 一次只执行一个明确 Task，或同一 Stage 中紧密关联、共享同一冻结契约并能够共同验收的少量 Task。
2. 当前代码、注册关系、数据库、迁移、测试、Git 分支和 Git diff 是实施事实源。
3. `AGENTS.md`、主 TaskList 和最新正式方案决定产品方向与执行优先级。
4. 每个 Task 完成后先 Review，再进入下一 Task。
5. 未满足验收、未运行测试或存在阻塞时，禁止声称完成。
6. 不允许形成第二套正式入口、Schema、API、Service、Prompt 链或数据事实源。
7. 不允许使用 Mock、硬编码、空接口或占位页冒充正式完成。
8. 不要一次连续执行多个 Stage。

---

# 2. 必读文档顺序

任何重构 Task 开始前，按以下顺序读取：

1. `AGENTS.md`
2. `trade-strategy-ai/docs/Trade-Refactor-TaskList.md`
3. `trade-strategy-ai/docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`
4. `trade-strategy-ai/docs/PROMPT_REVIEW_AND_MIGRATION.md`
5. `trade-strategy-ai/docs/AUTHOR_PROFILE_PROMPT_FLOW.md`
6. `trade-strategy-ai/docs/LLM-Prompt-Orchestration.md`
7. `trade-strategy-ai/docs/Refactor-Implementation-Log.md`
8. 当前 Task 直接相关的设计、实施计划、迁移和验收文档
9. 当前分支、基线提交、未提交修改、实际代码、测试、数据库和 API

文档优先级：

```text
AGENTS.md
> Trade-Refactor-TaskList.md
> 最新正式重构方案
> 当前 Task 设计和实施计划
> 实施记录
> 历史文档
```

发现冲突时，遵循更高优先级文件，并把冲突、选择和影响记录到 `Refactor-Implementation-Log.md`。

`docs/bak` 只用于历史参考，不得作为当前实现事实源。

---

# 3. codex-refactor-orchestrator 安装与启动

## 3.1 正确安装位置

安装目标必须是 Git 仓库根目录 `Trade`，不能安装到 `Trade/trade-strategy-ai`：

```bash
cd /path/to/codex-refactor-orchestrator
bash install.sh /path/to/Trade
```

验证：

```bash
cd /path/to/Trade
bash .agents/skills/refactor-orchestrator/scripts/validate-install.sh
bash .agents/skills/refactor-orchestrator/scripts/runtime-probe.sh
```

启动：

```bash
cd /path/to/Trade
codex -m gpt-5.5
```

建议一个 Task 或一个紧密关联的执行批次使用一个新的 GPT-5.5 Session。

## 3.2 固定开场

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.
```

这不表示每次都必须创建 subagent。已知的小型局部任务可以由 Parent 直接完成，最少 Agent 数量可以为 0。

## 3.3 运行证据要求

第一次在仓库中委派任务，或 Codex 升级后，Parent 必须确认：

- `.codex/agents/refactor-explorer-mini.toml` 存在并声明 GPT-5.4 mini；
- `.codex/agents/refactor-executor-mini.toml` 存在并声明 GPT-5.4 mini；
- Explorer 的有效权限为只读；
- Executor 的有效权限允许限定范围写入；
- Parent 当前模型为 GPT-5.5；
- native subagent spawning 实际可用。

静态配置或 `runtime-probe.sh` 成功不能单独证明实际运行模型和权限。没有运行证据时，不得声称：

- 已创建 subagent；
- 使用了某个具体模型；
- Explorer 确实只读；
- 测试已通过；
- Task 已完成。

native subagent 不可用或无法验证时，使用 single-controller fallback，并明确记录，不得假装已经使用 mini subagent。

## 3.4 Parent、Explorer 和 Executor 边界

GPT-5.5 Parent 负责：

- 解释范围和优先级；
- 识别正式事实源；
- 冻结架构、领域、API、Schema、权限、迁移、回滚和兼容契约；
- 建立依赖图和执行批次；
- 对 Task 做 M1/M2/M3 风险分级；
- 创建 Task Card；
- Review 真实工作区、完整 diff、测试和迁移证据；
- 决定 Task 或 Stage 是否通过。

Explorer mini 只用于：

- 只读定位路由、API、模型、Job、Workflow、Schema、Prompt 和测试；
- 追踪调用链和数据流；
- 查找 legacy、重复实现和删除前引用；
- 不修改代码，不决定架构。

Executor mini 只用于：

- 契约已冻结后的限定实现和测试；
- 只修改 Task Card 允许的路径；
- 不重定义公共契约；
- 不决定迁移、权限、安全或正式事实源；
- 不负责最终验收。

## 3.5 风险分级

| 等级 | 使用方式 | 典型任务 |
| --- | --- | --- |
| M1 | Executor mini 主导，Parent 批次 Review | 已知组件、局部测试、机械修复 |
| M2 | Parent 冻结契约，Executor 实现，Parent 语义 Review | 跨前后端但接口可先冻结的功能 |
| M3 | Parent 主导，mini 只做严格限定支持 | 领域模型、迁移、权限、时间语义、事实源、不可逆删除 |

## 3.6 Task Card 最低内容

每个委派 Task Card 必须包含：

- Task ID、标题和风险等级；
- 单一目标；
- 前置条件和依赖 ID；
- 当前分支、基线 commit 或上游 handoff；
- 必读文件和冻结契约；
- 允许修改路径和禁止修改路径；
- 实现要求；
- 测试、lint、build 和迁移命令；
- 验收标准；
- 升级给 Parent 的条件；
- 必须返回的结构化 handoff。

不得只给 subagent 一句“实现这个 Stage”。

## 3.7 批次、修复轮次和执行产物

- 正常实现批次限制为 1～3 个 Executor。
- 仅在写入路径和公共契约不重叠时并行。
- 领域模型 → 迁移 → API/Schema、共享路由、共享状态、删除和兼容退役必须串行。
- 同一个委派 Task 最多三轮：初始实现、定向修复、最终限定修复。
- 三轮后仍失败，标记阻塞并交回 Parent 或用户，不得扩大范围强行完成。

重要 Task 的临时执行记录放在：

```text
.codex/refactor-state/<stage-id>/
```

每轮至少保留 diff、测试日志、状态、结果和 Review。正式设计、迁移、验收和实施记录仍必须写入 `trade-strategy-ai/docs`。

---

# 4. 通用 Task 模板的适用范围

通用 Task 模板适用于所有 Task 的基础约束，但不能单独覆盖全部 Task。

正确组合：

```text
Orchestrator 通用 Task 模板（已经包含固定开场）
+ 当前 Task 对应的专用附加 Prompt
+ 当前实施计划中的文件、测试和验收要求
```

不要再重复追加一次固定开场。

必须使用专用附加 Prompt 的任务：

| 类型 | Task | 专用附加 Prompt |
| --- | --- | --- |
| 产品信息架构、页面和首页 | RT-S1-001 至 RT-S1-003 | Stage 1 产品页面 |
| 领域模型 | RT-S2-001 | 领域契约冻结 |
| 数据库和数据迁移 | RT-S2-002、RT-S2-003 | 数据库迁移安全 |
| Prompt 套件接入 | RT-S3-001 | Prompt 迁移与退役 |
| 单篇文章到正式规则 | RT-S3-002 | 单篇文章闭环，同时使用 Prompt 迁移约束 |
| 固定样本与批处理 | RT-S3-003 | 回归样本与批处理 |
| 旧 Prompt 退役 | RT-S3-004 | Prompt 迁移与退役 |
| 规则审核、规则族和生命周期 | RT-S4-001 至 RT-S4-003 | 规则治理 |
| OHLCV、Kaipan 和调度 | RT-S5-001 至 RT-S5-003 | 数据时间语义与调度 |
| 回测与规则适用性 | RT-S6-001 至 RT-S6-004 | 回测安全 |
| 作者画像 | RT-S7-001 至 RT-S7-004 | 作者画像边界 |
| 策略中心 | RT-S8-001 至 RT-S8-003 | 策略版本与 Proposal |
| 每日盘前 | RT-S9-001 至 RT-S9-003 | 每日盘前 |
| 每日盘后 | RT-S10-001 至 RT-S10-004 | 每日盘后归因 |
| 系统管理、自动化、追踪、成本、时间语义和灰度 | Stage 11 全部任务 | 运行保障与系统管理 |
| 旧入口退役、E2E 和用户交付 | RT-S12-001 至 RT-S12-003 | 最终退役与交付 |

普通局部 UI、局部 Service、测试和文档修复，可以使用通用模板加当前 Task 验收标准。

---

# 5. Orchestrator 通用 Task 模板

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.

Repository root:
- Work from the Trade repository root.
- Limit business implementation scope to trade-strategy-ai unless repository-level Orchestrator state/config is explicitly required.
- Store formal refactor documents only under trade-strategy-ai/docs.

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
9. current branch, baseline commit, uncommitted changes, code, tests, database and registered APIs

Before delegation:
- verify prerequisites and actual current status
- inspect existing implementation and avoid duplication
- record current branch, baseline commit and existing dirty changes
- verify Orchestrator bootstrap/runtime evidence when delegation is used
- classify work as M1, M2 or M3
- freeze architecture, public contracts, Schema, API, permissions, migrations, rollback, compatibility and verification commands
- decide whether read-only Explorer work is necessary
- create bounded Task Cards with allowed/forbidden paths and structured handoff requirements

Execution rules:
- do not cross into the next Task or Stage
- do not create a second formal entry, Schema, Service, API, Prompt chain or fact source
- do not use mocks, placeholders or hardcoded success
- preserve compatibility until retirement conditions are verified
- do not parallelize overlapping files, migrations or public contracts
- limit normal Executor batches to 1–3 agents
- limit one delegated Task to three implementation/fix rounds
- inspect the shared workspace and actual diff after every batch
- do not rely solely on a subagent completion claim

Verification:
- run all focused tests required by the Task
- run all affected regression tests
- run applicable typecheck, lint, build, API, migration, Prompt regression, E2E and manual acceptance checks
- run git diff --check
- record exact commands, counts, failures, skipped checks and residual risk

Documentation and status:
- update trade-strategy-ai/docs/Refactor-Implementation-Log.md
- use [ ] not started, [-] in progress, [x] complete, [!] blocked, [~] deferred
- update authoritative Task status only after Parent acceptance
- do not mark completion without real diff and verification evidence
- do not automatically start the next Task

Final response:
- actual agents spawned, models/permissions only when verified, and scopes
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

---

# 6. 专用附加 Prompt

把对应段落追加到通用 Task 模板末尾。

## 6.1 Stage 1 产品页面

```text
Stage 1 constraints:
- Preserve trade-strategy-ai/web/src/app/route-config.tsx as the single route, navigation, permission, metadata and compatibility fact source.
- Formal pages must use business Chinese and must not expose Job, Workflow, Pipeline, Artifact, Provider, force, config_path, database names or internal paths.
- Every formal page must represent 页面用途、输入、处理状态、输出、下一步。
- Support loading, empty, error, partial, permission_denied and unavailable truthfully.
- Do not convert unavailable data into false, zero, an empty list or success.
- Legacy pages remain compatibility-only until retirement conditions pass.
- Do not start RT-S1-003 while executing RT-S1-002.
- Do not enter Stage 2 before the Stage 1 exit Review.
```

## 6.2 领域契约冻结

```text
Domain contract constraints:
- Freeze stable IDs, version relationships, lifecycle states, source references and audit fields before implementation.
- Produce an object relationship map and old-to-new mapping before changing ORM, API or frontend types.
- Distinguish formal versions, daily runtime instances, proposals and historical compatibility objects.
- Do not delegate unresolved domain modeling or source-of-truth decisions.
- Record unresolved decisions as blockers instead of inventing a temporary second model.
```

## 6.3 数据库迁移安全

```text
Database migration constraints:
- Inspect all ORM models, SQLAlchemy metadata imports, Alembic heads, existing tables and actual data before writing migrations.
- Freeze target Schema and migration order before delegation.
- Migrations must be safely rerunnable, observable and recoverable.
- Never silently drop or overwrite legacy data.
- Produce pre/post counts, rejected rows and quality-status reports.
- Test upgrade, transformation and rollback/recovery paths.
- Only one writer may modify a migration chain or shared ORM contract at a time.
- Unit tests alone are not migration acceptance evidence.
```

## 6.4 Prompt 迁移与退役

```text
Prompt migration constraints:
- Treat Prompt files, loader code, Pydantic/JSON Schema and regression fixtures as one contract.
- Record prompt_version, schema_version, model, input_hash, raw output, validation, token usage and cost.
- Compare new and legacy Prompt results on the fixed regression set before production cutover.
- New Prompt must become the only formal write path before legacy Prompt becomes compatibility_only.
- Legacy Prompt must not produce new formal data after cutover.
- Do not delete legacy Prompt until code, tests, CLI, scripts, Jobs, Workflows and docs have no references and observation/rollback checks pass.
```

## 6.5 单篇文章闭环

```text
Single-article constraints:
- A normal article uses article_analysis_v1 as one main production call.
- article_analysis_repair_v1 is used only for targeted repair and at most once.
- concept_extraction_v1, article_structure_extraction_v1, rule_extraction_v1 and explicit_precondition_extraction_v1 are modular Schema/test tools and must not become four default production calls.
- Preserve original text, evidence, explicit facts, inferred hypotheses, missing fields, data dependencies and backtestability.
- Run deterministic automatic review after Schema validation.
- Automatic pass means eligible for pending backtest, not formally usable.
- Only human-reviewed results may create a formal RuleVersion.
```

## 6.6 回归样本与批处理

```text
Batch processing constraints:
- First select and freeze 10–15 representative articles and expected review outcomes.
- Do not run all 100+ articles before the fixed regression set passes.
- Record article_id, content hash/version, Prompt/Schema versions, raw output, automatic review and human conclusion.
- Support resume, bounded retry, idempotency, concurrency limits and incremental updates.
- Do not send all article bodies in one LLM request.
- Report cost, failures, quality distribution and reprocessing reasons.
```

## 6.7 规则治理

```text
Rule governance constraints:
- Automatic review must be deterministic where possible and cannot make a rule formally usable.
- High-risk, ambiguous, conflicting, parameter-edited and strategy-entry rules require human approval.
- Freeze rule fingerprint, RuleFamily, parameter-variant, conflict and lifecycle semantics before implementation.
- Do not merge semantically different rules merely because text is similar.
- Every lifecycle transition records actor, time, reason and before/after values.
```

## 6.8 数据时间语义与调度

```text
Data and scheduling constraints:
- Preserve trade_date, available_at, captured_at, effective_at, source and slot.
- Separate pre-market and post-market Kaipan data.
- Historical backfill and daily incremental update must be independently testable.
- Tasks must be idempotent, resumable and retryable.
- Missing data remains missing/unavailable and never becomes false or zero.
- Backtests may repair data before a run but must not call live Providers during a run.
- Prevent duplicate schedulers and process-local state drift.
```

## 6.9 回测安全

```text
Backtest safety constraints:
- Every run binds an immutable DatasetSnapshot, rule version, market-state model version and code version.
- Prohibit live Provider calls during backtest execution.
- Verify point-in-time availability for every trading day and prevent future-data leakage.
- Separate Level 1 OHLCV, Level 2 OHLCV plus market state and Level 3 including Kaipan.
- Missing Kaipan is a coverage limitation, not a failed condition.
- Mark insufficient_sample instead of producing strong conclusions.
- Include reproducibility and replay evidence.
```

## 6.10 作者画像边界

```text
Author profile constraints:
- Keep AuthorMethodProfile, AuthorRuleProfile and AuthorValidatedProfile separate.
- Never describe the result as the author's real trading performance, position, drawdown or discipline.
- Separate article expression, rule statistics and backtest validation in storage and UI.
- Every conclusion requires evidence and confidence.
- New evidence creates drafts/revisions and must not overwrite a published profile.
- Batch method profiles use structured articles in groups of 10–20, not full-corpus prompts.
```

## 6.11 策略版本与 Proposal

```text
Strategy constraints:
- StrategyVersion is a formal version and must not be regenerated daily.
- DailyStrategyInstance is a runtime object, not a new StrategyVersion.
- StrategyRevisionProposal cannot directly modify a published strategy.
- Freeze lifecycle, validation, publication, current-use, archive and rollback behavior before implementation.
- Every release and rollback requires evidence, actor and version-diff records.
```

## 6.12 每日盘前

```text
Pre-market constraints:
- Complete data, market-state, strategy and rule-applicability checks before selection.
- Generate DailyRuleSelection, DailyStrategyInstance and TradingDayPlan; do not create a new formal strategy.
- Explain enabled, reduced and suspended rules.
- Trace every result to all input versions and data-quality states.
- Missing inputs require repair or explicit degradation, never silent defaults.
```

## 6.13 每日盘后归因

```text
Post-market constraints:
- Program facts calculate trigger, execution, MFE, MAE, return and market-state change.
- LLM may validate or explain but must not recompute program metrics.
- Use llm_attribution_v1 only for low confidence, conflicting evidence or important signals.
- Prefer program templates for normal postmortem text; use llm_postmortem_notes_v1 only when needed or once for daily summary.
- Keep RuleOptimizationProposal, AuthorProfileRevisionProposal and StrategyRevisionProposal separate.
- A single day must never directly modify formal rules, profiles or strategies.
```

## 6.14 运行保障与系统管理

```text
Operations constraints:
- Keep normal-user status/actions separate from administrator technical details.
- Use stable run_id and record every step, duration, error and retry.
- Record Prompt model/version/Schema/Tokens/cost and data source/range/coverage/time semantics.
- Recovery supports resume, retry limits and operator-visible actions.
- User-facing errors explain what happened, impact and remediation; do not expose stack traces or Job failed.
- Freeze rollout stages: comparison, read-only, limited enablement, default, legacy read-only, retirement.
- Provide rollback/recovery for database, Prompt and batch-processing changes.
```

## 6.15 最终退役与交付

```text
Final retirement constraints:
- Before deleting an entry, verify target migration, data migration, reference scan, observation period and rollback evidence.
- Do not retire legacy paths merely because a new page exists.
- Run the complete real-data journey from article import through optimization proposals.
- Run E2E, frontend, backend, migration and Prompt regression suites.
- Verify user and administrator documentation against the actual UI.
- Any failed final acceptance item blocks Stage 12 completion.
```

---

# 7. 可合并执行的 Task 矩阵

“同一 Stage 中紧密关联的少量 Task”必须同时满足：

1. 属于同一 Stage。
2. 共享同一冻结契约或同一可共同验收的业务闭环。
3. 不需要独立迁移、观察期或人工验收后才能继续。
4. 可以在一个 Parent Session 内完整 Review。
5. 并行 Executor 不修改相同文件、公共契约或迁移链。
6. 即使同一 Session，存在依赖的 Task 仍按顺序执行，不能同时开始。

| Stage | Task 组合 | 建议 | 执行条件 |
| --- | --- | --- | --- |
| 0 | RT-S0-001 + RT-S0-002 | 可以，同 Session 串行；已完成 | 先审计，再生成迁移矩阵 |
| 1 | RT-S1-001 | 单独；已完成 | 集中路由和权限先冻结 |
| 1 | RT-S1-002 | 单独，但拆 Session A/B | 共享框架与正式页面装配分开 Review |
| 1 | RT-S1-003 | 单独 | 后端聚合、API 和首页共同验收 |
| 2 | RT-S2-001 | 单独，M3 | 先冻结全局领域对象和版本关系 |
| 2 | RT-S2-002 | 单独，M3 | Schema、ORM、迁移骨架和升级测试 |
| 2 | RT-S2-003 | 单独，M3 | 使用真实数据迁移、核对和恢复；不能与 S2-002 同时宣布完成 |
| 3 | RT-S3-001 + RT-S3-002 | 有条件，默认分两 Session | 只有 Prompt/Schema 契约先通过固定样本，且无未完成迁移时才可在同 Parent Session 串行 |
| 3 | RT-S3-003 | 单独 | 固定样本、批处理、成本和恢复范围大 |
| 3 | RT-S3-004 | 单独且最后 | 需要引用扫描、观察期和回滚验证 |
| 4 | RT-S4-002 + RT-S4-003 | 可以，同 Session 串行 | Parent 先冻结指纹、规则族、冲突和生命周期契约 |
| 4 | RT-S4-001 | 建议后置单独 | 审核服务/UI 依赖稳定的去重、冲突和生命周期契约 |
| 5 | RT-S5-001 + RT-S5-002 | 有条件，同 Parent Session 多批次 | 先冻结共享时间语义；写集和测试必须独立，通常各自一个 Executor |
| 5 | RT-S5-003 | 后置单独 | 依赖 OHLCV/Kaipan 稳定命令、状态和修复动作 |
| 6 | RT-S6-001 + RT-S6-002 | 可以，同 Session 串行 | 先冻结快照、point-in-time 和防未来数据契约 |
| 6 | RT-S6-003 + RT-S6-004 | 可以，同 Session 串行 | 都派生自稳定回测结果契约 |
| 7 | RT-S7-001 + RT-S7-002 | 可以，同 Session 多批次 | 方法画像和规则画像分离存储、共享证据引用 |
| 7 | RT-S7-003 + RT-S7-004 | 有条件，同 Session 串行 | Stage 6 已完成，三层画像版本/发布契约已冻结 |
| 8 | RT-S8-001 + RT-S8-002 | 可以，同 Session 串行 | 先冻结 StrategyVersion 状态机、验证、发布和回滚 |
| 8 | RT-S8-003 | 单独 | Proposal 与正式策略隔离，并为 Stage 10 提供契约 |
| 9 | RT-S9-001 + RT-S9-002 | 可以，同 Session 串行 | 前置检查输出直接驱动规则选择 |
| 9 | RT-S9-003 | 后置单独 | DailyStrategyInstance 和 TradingDayPlan 依赖前两项稳定输出 |
| 10 | RT-S10-001 + RT-S10-002 | 可以，同 Session 串行 | 程序信号事实先完成，再做结构化归因 |
| 10 | RT-S10-003 + RT-S10-004 | 可以，同 Session 串行 | 归因契约已稳定，Proposal 与页面可共同验收 |
| 11 | 自动化恢复 + 运行追踪 | 有条件，同 Session 串行 | 先冻结 run_id、步骤状态和恢复契约 |
| 11 | 成本增量控制 + 数据时间语义 | 有条件，同 Session 多批次 | 避免并行修改同一核心模型 |
| 11 | 系统管理入口 + 用户友好错误 | 可以，同 Session | 普通用户/管理员展示和可操作错误共同验收；执行前必须确认 TaskList 唯一 Task ID |
| 11 | 灰度迁移和回滚 | 单独且最后 | 需要前面链路稳定和观察证据 |
| 12 | RT-S12-001 | 单独，M3 | 删除旧入口前逐项满足退役门禁 |
| 12 | RT-S12-002 + RT-S12-003 | 有条件，同 Session 串行 | 先通过真实 E2E，再按实际 UI 修正文档 |

不得合并：

- RT-S2-001 与 RT-S2-003；
- RT-S3-001 与 RT-S3-004；
- RT-S5-003 与尚未稳定的 RT-S5-001/002 并行；
- RT-S8-001 与 RT-S9-003；
- RT-S10-001 与 RT-S10-003 并行；
- 灰度迁移与被灰度的实现同时完成；
- RT-S12-001 与任何尚未完成迁移或观察期的任务。

`Trade-Refactor-TaskList.md` 提到 Stage 5 和 Stage 6 可以部分并行。这不表示可以在同一 Prompt 中跨 Stage 合并。默认仍先满足 Stage 5 的快照、时间语义和数据完整性契约；确需部分并行时，必须由用户明确授权，并使用不同 Parent Session/工作范围，Stage 6 不得在 Stage 5 未满足的事实源上宣称完成。

---

# 8. 当前下一步：RT-S1-002

当前实施记录表明：

- RT-S1-001 已完成；
- RT-S1-002 尚未开始，是下一步；
- RT-S1-003 尚未开始；
- Stage 1 尚未完成。

推荐：

```text
Session A：共享页面框架和布局接入
→ 独立 Review 和修复
→ Session B：正式业务入口装配和 RT-S1-002 验收
```

## 8.1 Session A Prompt

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.

Work from the Trade repository root. Limit business changes to trade-strategy-ai.

Execute only the shared-framework and shared-layout portion of RT-S1-002.

Read in order:
1. AGENTS.md
2. trade-strategy-ai/docs/Trade-Refactor-TaskList.md
3. trade-strategy-ai/docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md
4. trade-strategy-ai/docs/PROMPT_REVIEW_AND_MIGRATION.md
5. trade-strategy-ai/docs/AUTHOR_PROFILE_PROMPT_FLOW.md
6. trade-strategy-ai/docs/LLM-Prompt-Orchestration.md
7. trade-strategy-ai/docs/Refactor-Implementation-Log.md
8. trade-strategy-ai/docs/2026-06-10-stage-1-implementation-plan.md
9. current branch, baseline commit, uncommitted changes, code, tests and git diff

Before delegation:
- verify Orchestrator runtime evidence if subagents will be used
- classify tasks and freeze PageAvailability, BusinessPageShell, ProductPageAdapter, SectionNav, CompatibilityNotice and DashboardLayout contracts
- create bounded Task Cards; do not assign unresolved shared-contract decisions to Executor mini

Implement and verify only:
- trade-strategy-ai/web/src/components/layout/business-page-shell.tsx and tests
- section-nav.tsx and tests
- compatibility-notice.tsx and tests
- product-page-adapter.tsx and tests
- DashboardLayout route metadata and SectionNav integration
- StatusStrip removal of route/path developer information
- route permission behavior

Apply the Stage 1 constraints in trade-strategy-ai/docs/AI-Conversation-Templates.md.
Preserve route-config.tsx as the only route/navigation/permission fact source.
Do not assemble all domain pages yet.
Do not start RT-S1-003 or Stage 2.
Do not add migrations or modify Prompt behavior.

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
Normally do not mark RT-S1-002 complete after Session A.

Report runtime mode, actual agents, risk levels, Task Cards, contracts, files, tests, visual verification, remaining Session B work and confirmation that RT-S1-003/Stage 2 were not started.
```

## 8.2 Session B Prompt

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.

Work from the Trade repository root. Limit business changes to trade-strategy-ai.

Continue only RT-S1-002 after verifying Session A contracts, implementation-log entry and tests.

Read the mandatory documents in trade-strategy-ai/docs/AI-Conversation-Templates.md section 2, then read:
- trade-strategy-ai/docs/2026-06-10-stage-1-implementation-plan.md
- current shared components
- route-config.tsx
- current branch, baseline commit, uncommitted changes and complete git diff

Assemble the formal product routes required by the implementation plan:
- research
- rules and backtest
- authors
- strategies
- daily trading
- applicable system pages

Reuse real hooks, actions and result components.
Do not duplicate domain logic or invent unavailable facts.
Keep legacy paths in compatibility mode.
Apply the Stage 1 constraints in trade-strategy-ai/docs/AI-Conversation-Templates.md.

Verify the formal journey:
研究中心 → 待审核规则 → 回测实验 → 作者画像 → 策略中心 → 今日盘前 → 今日盘后

The journey must not require /jobs, /workflows, /artifacts or /market/* technical workbenches.

Use dependency batches. Only Parent or one designated Executor may modify route-config.tsx and shared page-state matrices.

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
Mark only RT-S1-002 complete when every acceptance criterion has diff, test and visual/manual evidence or an explicitly accepted residual limitation.
Do not start RT-S1-003 or Stage 2.

Report runtime mode, actual agents, Task Cards, formal routes, compatibility, tests, visual verification, risks, acceptance conclusion and scope confirmation.
```

---

# 9. Review、恢复和纠偏模板

## 9.1 Task 或 Stage Review

```text
Use the refactor-orchestrator skill.
Use the GPT-5.5 Parent as final reviewer.
Use read-only Explorer mini only when additional repository evidence is required.
Do not delegate final acceptance to Executor mini.
Do not start the next Task or Stage.

Strictly review:
[Task ID or Stage]

Read mandatory project documents, current plan, implementation log, complete git diff, runtime artifacts and actual test/migration output.
Check every acceptance criterion, real data, registered routes, Schema/API/migrations, time semantics, compatibility, permissions, error states, duplicate facts, unrelated changes and documentation accuracy.
Classify findings as BLOCKER, HIGH, MEDIUM or LOW.
Clear all BLOCKER and required HIGH findings before acceptance.
If repairs are needed, create bounded repair Task Cards, respect the three-round limit, rerun verification and repeat Parent Review.

Output findings, repairs, tests, residual risk, acceptance conclusion and whether the next Task/Stage is allowed.
Do not continue automatically.
```

## 9.2 新 Session 恢复

```text
Do not infer progress from chat memory.
Work from the Trade repository root.
Read AGENTS.md, all mandatory project documents, Refactor-Implementation-Log.md, current plan, .codex/refactor-state handoffs when present, current branch, baseline, git status and git diff.
Report current Task, accepted work, in-progress work, incomplete work, blockers, dirty changes and the next smallest safe task.
Continue only the actual incomplete Task.
```

## 9.3 完成核验

```text
Recheck the completion claim against AGENTS.md, the authoritative TaskList, implementation plan, complete git diff, runtime artifacts and actual verification output.
Verify real data, formal API/UI wiring, migrations, all required states, user path, compatibility, documentation and scope.
Do not accept subagent claims without workspace evidence.
If any required item is missing, change status to [-] in progress or [!] blocked.
```

## 9.4 跑偏纠正

```text
Stop expansion and do not spawn new agents.
Re-read the authoritative documents, current plan, baseline and complete git diff.
Identify duplicate facts, out-of-scope work, overlapping Executor writes, missing tests, fake completion and later-Stage work.
Revert or repair only the deviation, rerun affected verification and report actual status.
```

---

# 10. Prompt 调用编排核验

```text
Verify compliance with trade-strategy-ai/docs/LLM-Prompt-Orchestration.md:
- one article_analysis_v1 main call for a normal article
- at most one targeted article_analysis_repair_v1 when required
- modular extraction Prompts are not four default production calls
- no per-article author total-profile Prompt
- author method batches use 10–20 structured articles
- conditional llm_attribution_v1 only
- llm_postmortem_notes_v1 is conditional or once per daily summary, not per normal signal
- Prompt/Schema/model/token/cost/input_hash/run_id records
- cache and idempotency
- LLM raw output is not the final formal fact source
- legacy Prompt no longer writes formal data after cutover
- deletion only after every retirement condition passes
```

---

# 11. 文档使用结论

使用本文件时：

1. 从 `Trade` 根目录安装并启动 Orchestrator。
2. 直接复制完整通用模板，不再重复固定开场。
3. 追加对应 Task 的专用约束。
4. 当前任务优先使用 RT-S1-002 Session A Prompt。
5. 每个实现 Session 后单独运行 Parent Review。
6. 不根据 subagent 的完成声明直接进入下一 Task。
