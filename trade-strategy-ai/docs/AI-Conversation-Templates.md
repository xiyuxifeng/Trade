# Trade Strategy AI 重构对话模板

## 1. 使用说明

本文件用于指导你与 Codex、Claude Code、Cursor Agent 或其他代码 Agent 配合完成 `trade-strategy-ai` 重构，并支持在 Codex 中使用 `codex-refactor-orchestrator` Skill。

基本原则：

1. 一次只执行一个明确 Task，或一个 Stage 中紧密关联的少量 Task。
2. 每次开始前读取 `AGENTS.md`、正式 TaskList、实施记录和当前任务文档。
3. 当前代码、测试、注册关系和 Git diff 是事实源，不能只根据历史文档推断。
4. 每个任务完成后先 Review，再进入下一任务。
5. 未满足验收、未运行测试或存在阻塞时，禁止声称完成。
6. 不允许形成第二套正式入口、Schema、API、Service、Prompt 链或数据事实源。
7. 不允许使用 Mock、硬编码、空接口或占位页冒充完成。
8. 所有重构文档只能在 `trade-strategy-ai/docs` 中生成和更新。
9. 不要一次要求 AI 连续完成多个 Stage。

---

# 2. codex-refactor-orchestrator 使用方式

## 2.1 适用场景

推荐用于：

- 有明确 Task ID、实施计划和验收标准的重构；
- 跨多个前端、后端、数据库或任务系统文件；
- 需要兼容旧入口、迁移数据或退役旧事实源；
- 可以拆成边界明确、写入范围不重叠的实现任务；
- 需要 GPT-5.5 统一规划、冻结契约和最终 Review。

单文件小修改不必强制创建 subagent。最少 Agent 数量可以为 0。

## 2.2 安装与验证

```bash
cd /path/to/codex-refactor-orchestrator
bash install.sh /path/to/Trade/trade-strategy-ai

cd /path/to/Trade/trade-strategy-ai
bash .agents/skills/refactor-orchestrator/scripts/validate-install.sh
bash .agents/skills/refactor-orchestrator/scripts/runtime-probe.sh

codex -m gpt-5.5
```

建议一个 Task 或一个紧密关联的执行批次使用一个新的 GPT-5.5 Session。

## 2.3 Orchestrator Prompt 开场

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.
```

含义：

- GPT-5.5 主 Agent 必须按 Skill 规则判断和显式创建 subagent；
- 不允许只口头声称已经委派；
- Explorer 只读调查不清晰的调用链和边界；
- Executor 只执行已经冻结契约、文件范围明确的 Task Card；
- 不并行修改同一文件、公共契约、Schema、API 或迁移；
- 最终验收必须由 GPT-5.5 检查真实 diff 和测试结果；
- native subagent 不可用时使用 single-controller fallback，并诚实记录。

---

# 3. 当前下一步

当前状态以 `docs/Refactor-Implementation-Log.md` 为准：

- `RT-S0-001`：已完成；
- `RT-S0-002`：已完成；
- `RT-S1-001`：已完成；
- `RT-S1-002`：下一步执行；
- `RT-S1-003`：尚未开始；
- Stage 1：尚未完成。

本轮不要重新实现 `RT-S1-001`，不要开始 `RT-S1-003`，不要进入 Stage 2。

推荐把 `RT-S1-002` 拆成两个 Session：

```text
Session A：共享页面框架和布局接入
→ Review 和修复
→ Session B：正式业务入口装配和 RT-S1-002 验收
```

---

# 4. 下一步 Prompt：Session A

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.

Work only in the current trade-strategy-ai repository.
Read AGENTS.md and all applicable nested instructions first.

Authoritative documents:
- docs/2026-06-10-stage-1-implementation-plan.md
- docs/Refactor-Implementation-Log.md
- docs/Refactor-Current-State-Audit.md
- docs/Refactor-Migration-Matrix.md
- docs/Trade-Refactor-TaskList.md

Current status:
- RT-S1-001 is complete.
- RT-S1-002 is next.
- RT-S1-003 has not started.
- Stage 1 is not complete.

Execute only the shared-framework and shared-layout portion of RT-S1-002.

Implement and verify:
- BusinessPageShell and tests
- SectionNav and tests
- CompatibilityNotice and tests
- ProductPageAdapter and tests
- DashboardLayout route metadata and SectionNav integration
- StatusStrip removal of route/path developer information
- permission behavior required by route-config.tsx

Before delegation, the GPT-5.5 parent must freeze:
1. PageAvailability values.
2. BusinessPageShell public props.
3. ProductPageAdapter product/compatibility boundary.
4. SectionNav derivation and permission rules.
5. CompatibilityNotice metadata and actions.
6. DashboardLayout integration behavior.

Required states:
- ready
- loading
- empty
- error
- partial
- permission_denied
- unavailable

Every formal page contract must represent:
- 页面用途
- 输入
- 处理状态
- 输出
- 下一步

For every non-ready state, explain:
- what happened
- what is affected
- what the user should do next

Do not convert unavailable or unknown data into false, zero, an empty collection, or success.
Do not render empty decorative cards.

Formal product mode must not expose:
- job_type
- workflow_id
- Pipeline Step
- Artifact path
- Provider
- force
- config_path
- raw internal configuration objects

Scope constraints:
- Preserve route-config.tsx as the single route, navigation, permission, metadata, and compatibility fact source.
- Do not create another route or navigation array.
- Do not reimplement RT-S1-001.
- Do not assemble all domain pages in this Session, except minimal fixtures required to prove shared contracts.
- Do not start RT-S1-003.
- Do not implement HomeDashboardService.
- Do not modify the homepage dashboard API.
- Do not enter Stage 2.
- Do not add database migrations.
- Do not modify Prompt behavior.
- Do not delete legacy routes before retirement conditions are met.

Agent rules:
- Use Explorer only when a call chain, permission rule or route mapping is unclear.
- Delegate only bounded Task Cards with allowed files, forbidden files, dependencies, tests and acceptance criteria.
- Do not run parallel Executors that touch the same shared file or public contract.
- The GPT-5.5 parent must review every actual diff and test output.

Use TDD and run at minimum:

cd web
pnpm test -- src/components/layout/business-page-shell.test.tsx src/components/layout/section-nav.test.tsx src/components/layout/compatibility-notice.test.tsx src/components/layout/product-page-adapter.test.tsx src/components/layout/sidebar.test.tsx src/components/layout/status-strip.test.tsx
pnpm typecheck
pnpm lint
pnpm build
pnpm test
git diff --check

Perform desktop and mobile visual verification if a browser environment is available. Otherwise record it explicitly.

Update docs/Refactor-Implementation-Log.md as partial RT-S1-002 progress.
Normally keep RT-S1-002 as in progress after Session A.
Do not mark Stage 1 complete.
Do not start RT-S1-003 or Stage 2.

Final response must include:
- agents actually spawned and bounded scopes
- Task Cards executed
- shared contracts frozen
- files changed
- tests and exact results
- remaining work for Session B
- visual verification status
- confirmation that RT-S1-003 and Stage 2 were not started
```

---

# 5. 下一步 Prompt：Session B

Session A 完成并 Review 后，在新的 GPT-5.5 Session 中使用：

```text
Use the refactor-orchestrator skill.

Choose and explicitly spawn subagents according to the Skill rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.

Continue RT-S1-002 using the shared page contracts already implemented.

Read first:
- AGENTS.md and applicable nested instructions
- docs/2026-06-10-stage-1-implementation-plan.md
- docs/Refactor-Implementation-Log.md
- docs/Refactor-Migration-Matrix.md
- current shared component implementations
- current route configuration
- current git status and git diff

Verify Session A actually completed and tested:
- BusinessPageShell
- SectionNav
- CompatibilityNotice
- ProductPageAdapter
- DashboardLayout integration
- StatusStrip cleanup

Execute only the formal product route assembly and acceptance work required by RT-S1-002.

Expected formal routes include:
- /research/articles
- /research/add
- /research/results
- /rules/review
- /rules/library
- /rules/backtests
- /rules/results
- /authors
- /strategies
- /strategies/candidates
- /daily/overview
- /daily/pre-market
- /daily/after-close
- applicable /system child routes

Use the implementation plan to determine the existing page, API hook, business action, result component, permission rule and compatibility behavior for each route.

Rules:
- Reuse existing real API hooks, business actions and result components.
- Do not duplicate domain logic.
- Do not use mock data to claim completion.
- Do not invent RuleVersion, author proposal, StrategyVersion, daily object, count or status without a real fact source.
- If an old page mixes product operations and engineering forms, split or adapt it using product and compatibility modes.
- Keep legacy paths in compatibility mode while retirement conditions remain unmet.
- Formal pages must not expose job_type, workflow_id, Pipeline Step, Artifact path, Provider, force, config_path or raw internal configuration.
- Every formal page must represent 页面用途、输入、处理状态、输出、下一步。
- Every page must support loading、empty、error、partial、permission_denied、unavailable。
- Do not convert unavailable information to false, zero, an empty list or success.

Verify the formal user journey:
研究中心 → 待审核规则 → 回测实验 → 作者画像 → 策略中心 → 今日盘前 → 今日盘后

The formal journey must not require /jobs、/workflows、/artifacts or /market/* technical workbenches.

Agent rules:
- Use Explorer only for unclear ownership, hooks, permissions or compatibility behavior.
- GPT-5.5 retains ownership of route-config.tsx and shared public contract changes.
- Create bounded Executor Task Cards by domain only when write sets do not overlap.
- Only one Executor or the parent may update route-config.tsx.
- The parent must review the complete combined diff and all test output.

Suggested batches:
1. Research Center.
2. Rules and Backtest.
3. Daily Trading.
4. Authors, Strategies and System Management.
5. Route integration, state matrix, product journey, full regression and documentation.

Run at minimum:

cd web
pnpm test -- src/pages/product-entry-pages.test.tsx src/pages/product-page-state-matrix.test.tsx src/app/product-journey.test.tsx src/components/layout/product-page-adapter.test.tsx src/pages/articles/index.test.tsx src/pages/rule-pool/index.test.tsx src/pages/backtest/index.test.tsx src/pages/strategies/lifecycle.test.tsx src/pages/system/index.test.tsx
pnpm typecheck
pnpm lint
pnpm build
pnpm test
git diff --check

Review the full diff and confirm:
- every expected formal route mounts real capability or shows a truthful unavailable boundary
- no engineering parameters appear in formal pages
- compatibility routes remain where required
- admin-only operations remain protected
- no mock data or second fact source was introduced
- RT-S1-003 and Stage 2 were not started

Perform desktop and mobile visual verification when available. Record unavailable verification explicitly.

Update docs/Refactor-Implementation-Log.md with final RT-S1-002 evidence.
Mark only RT-S1-002 complete if all acceptance conditions pass.
Do not mark Stage 1 complete.
Do not start RT-S1-003 or Stage 2.

Final response must include:
- agents and scopes
- Task Cards
- files changed
- formal routes connected
- compatibility routes preserved
- tests and exact results
- visual verification status
- remaining risks
- whether RT-S1-002 passed
- confirmation that RT-S1-003 and Stage 2 were not started
```

---

# 6. Orchestrator 通用 Task 模板

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
- current task plans and acceptance documents
- current code, tests, git status and git diff

Before delegation:
1. Verify prerequisites and current status.
2. Inspect existing implementation and avoid duplication.
3. Freeze architecture, public contracts, Schema, API, migrations, compatibility and verification commands.
4. Decide whether a read-only Explorer is needed.
5. Create bounded Task Cards.

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

# 7. Orchestrator Review 模板

```text
Use the refactor-orchestrator skill.

Use the GPT-5.5 parent as the final reviewer.
Use read-only Explorer subagents only when additional repository evidence is needed.
Do not delegate final acceptance to an Executor.
Do not start the next Task or Stage.

Strictly review:
[填写 Task ID 或 Stage]

Read the TaskList, implementation log, relevant plans, current code, complete git diff and actual test output.

Check:
1. Every acceptance criterion.
2. Real code, registered routes, Schema, API, migrations, Prompt loading and user paths.
3. Real data versus Mock or placeholders.
4. Duplicate entries, Schema, Service, API, Prompt chain or fact sources.
5. Compatibility and retirement conditions.
6. Permissions and error states.
7. Actual tests and migration evidence.
8. Unrelated or out-of-scope diff.
9. Implementation log accuracy.

If issues exist, classify them, create bounded repair Task Cards, repair, rerun tests and repeat GPT-5.5 review.

Output:
- satisfied criteria
- unsatisfied criteria
- blocking issues
- repairs
- tests and evidence
- remaining risks
- acceptance conclusion
- whether the next Task or Stage is allowed

Do not enter the next Task or Stage automatically.
```

---

# 8. 非 Orchestrator 通用继续模板

```text
请继续执行 trade-strategy-ai 重构任务。

本次只执行：
[填写 Task ID 和任务名称]

执行前请读取：
- AGENTS.md
- trade-strategy-ai/docs/Trade-Refactor-TaskList.md
- trade-strategy-ai/docs/Refactor-Implementation-Log.md
- 当前任务依赖的设计、迁移和验收文档
- 当前代码和测试

要求：
1. 确认前置任务和依赖。
2. 检查现有实现，不重复建设。
3. 不跨 Task 或 Stage。
4. 不形成第二套入口、Schema、Service、API、Prompt 链或事实源。
5. 不使用 Mock、硬编码、空接口或占位页冒充完成。
6. 处理迁移、兼容、错误状态和用户说明。
7. 运行所有受影响测试。
8. 无法运行的测试必须明确记录。
9. 更新 Refactor-Implementation-Log.md。
10. 不自动开始下一个任务。

完成后回复：
任务：
状态：
已完成：
未完成：
修改文件：
数据库迁移：
已运行测试：
测试结果：
已知风险：
验收结论：
```

---

# 9. 新 Session 或中断后继续

```text
请继续 trade-strategy-ai 重构。

不要根据聊天记忆推断进度，请先读取：
1. AGENTS.md
2. docs/Trade-Refactor-TaskList.md
3. docs/Refactor-Implementation-Log.md
4. docs/Refactor-Current-State-Audit.md
5. docs/Refactor-Migration-Matrix.md
6. 当前任务计划和验收文档
7. Git 当前分支、最近提交和未提交改动

输出：
- 当前 Task ID
- 已完成 Stage
- 当前已完成内容
- 尚未完成内容
- 当前阻塞
- 下一步最小任务

确认实际状态后，只继续当前未完成任务。
不要重复工作，也不要跳到后续 Stage。
```

---

# 10. 完成核验与纠偏

## 10.1 AI 声称完成时

```text
请重新按 AGENTS.md、正式 TaskList 和当前实施计划严格核验。

检查：
- 是否使用真实数据而不是 Mock
- 页面是否调用正式 API
- 迁移是否执行和测试
- 测试是否真实运行
- 页面状态是否完整
- 正式入口是否可访问
- 实施记录是否更新
- 是否检查完整 Git diff
- 是否存在未完成项
- 是否越过当前 Task 或 Stage

提供修改文件、API、迁移、测试命令和结果、用户路径、diff Review 和风险证据。
任何一项未满足时，把状态改为进行中或阻塞。
```

## 10.2 AI 跑偏时

```text
停止扩展工作，不要创建新的 subagent。
重新读取 AGENTS.md、TaskList、实施记录、当前计划、验收标准和完整 Git diff。

检查是否：
- 新增未定义业务方向
- 创建第二套入口、Schema、Service、API、Prompt 链或事实源
- 把开发工具换皮成用户产品
- 越过 Task 或 Stage
- 省略迁移、测试或真实数据
- 多个 Executor 修改同一文件或公共契约
- 只接受 subagent 声明而未检查真实 diff

撤销或修正偏离部分，重新运行测试并汇报真实状态。
```

---

# 11. Stage 完成后的 Review

```text
请不要开始下一 Stage。

严格 Review Stage [编号]：
1. 逐条检查所有 Task 验收标准。
2. 使用真实数据走通用户演示路径。
3. 检查前端、后端、数据库、Prompt 和运行契约。
4. 检查 Mock、占位、硬编码和未接通功能。
5. 检查重复入口、Schema、Service、API 或事实源。
6. 检查兼容和退役计划。
7. 检查测试和迁移证据。
8. 检查完整 Git diff 是否越界。
9. 检查 Refactor-Implementation-Log.md。

输出已满足项、未满足项、阻塞项、修复项、测试证据、出口条件和是否允许进入下一 Stage。
存在问题时直接修复并重新 Review，但不要自动进入下一 Stage。
```

---

# 12. Stage 专用约束摘要

执行每个 Stage 时，必须读取 `docs/Trade-Refactor-TaskList.md` 中对应 Task 的完整验收标准。

- Stage 1：普通用户界面去开发术语；统一页面用途、输入、状态、输出、下一步；旧页仅兼容；状态完整。
- Stage 2：不建立第二套模型；对象版本化；迁移可重跑、可恢复、不丢数据；完整接入业务。
- Stage 3：Prompt、Schema、测试同契约；记录版本和输入；LLM 不编造参数；先固定样本再批处理。
- Stage 4：确定性自动审核；人工审核高风险；规则指纹、规则族和参数变体。
- Stage 5：OHLCV 历史回灌和增量；Kaipan 保留时序；数据任务幂等、可重试；回测不调用实时 Provider。
- Stage 6：固定 DatasetSnapshot；防未来数据；分 Regime；样本不足；结果可复现。
- Stage 7：三层作者画像；不声称真实实盘能力；正式画像人工发布。
- Stage 8：StrategyVersion 不按日生成；Proposal 不直接覆盖正式策略；支持审核、发布和回滚。
- Stage 9：每日对象与正式策略版本分离；规则选择可解释；盘前输入版本可追溯。
- Stage 10：信号结果和归因完整；LLM 不重算指标；单日结果只生成 Proposal。
- Stage 11：统一 run_id；运行、Prompt、成本和数据覆盖可观测；错误对用户可理解。
- Stage 12：满足退役条件后删除旧入口；真实数据全链路；完成 E2E、迁移和 Prompt 回归。

---

# 13. Prompt 调用编排核验

```text
请核验当前 Prompt 实现是否符合 docs/LLM-Prompt-Orchestration.md：
1. 单篇普通文章只调用一次 article_analysis_v1。
2. 只在 Schema 或局部字段失败时调用一次 article_analysis_repair_v1。
3. 避免逐篇调用作者画像 Prompt。
4. 只在低置信度、证据冲突或重要信号时调用 llm_attribution_v1。
5. 记录 Prompt、Schema、模型、Token、成本和 input_hash。
6. 相同输入启用缓存和幂等。
7. 旧 Prompt 停止产生正式数据。
8. 删除旧 Prompt 前满足全部退役验收。

任一项不满足时，修正后再标记 Prompt 任务完成。
```

---

# 14. 推荐执行节奏

```text
实现一个 Task
→ AI 自查
→ 严格 Review
→ 修复
→ Task 验收
→ Stage 验收
→ 进入下一任务
```

使用 Orchestrator 时：

```text
GPT-5.5 检查事实并冻结契约
→ 必要时 Explorer 只读调查
→ 创建依赖批次和 Task Card
→ 显式创建最少数量的 Executor
→ Executor 实现和测试
→ GPT-5.5 检查完整 diff 和测试
→ 修复
→ Task 或 Stage 验收
```
