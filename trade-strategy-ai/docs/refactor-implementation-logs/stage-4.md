# Stage 4 规则管理、去重和规则族实施日志

## Current Status

- Stage：`Stage 4 规则管理、去重和规则族`
- Stage 状态：`[-] 进行中`
- 当前活动：`Stage 4 Bootstrap` 已完成。
- 下一可执行 Task：`RT-S4-002 规则指纹与规则族`
- Bootstrap 决策：`READY`
- Stage 4 implementation：may begin only after explicit user instruction.

## 2026-06-16 Stage 4 Bootstrap

### Scope

本次只执行 Stage 4 Bootstrap，不实施 Stage 4 production code。

目标：

- 确认 Stage 3 `ACCEPTED` entry condition；
- 确认 repository、branch、HEAD 和 working tree baseline；
- 从权威文档解析 Stage 4 task scope、ordering、dependencies 和 exclusions；
- 检查 Stage 4 相关当前实现；
- 冻结 Stage 4 execution baseline 和 implementation plan；
- 更新主日志和 Stage 4 日志。

### Repository baseline

- Repository remote：`git@github.com:xiyuxifeng/Trade.git`
- Project root：`trade-strategy-ai`
- Branch：`main`
- HEAD：`77dba41a3149c03daa82cfbc72b9b83cd70b6881` (`Stage 3 Review`)
- Working tree：clean
- Staged changes before Bootstrap：none
- Pre-existing uncommitted Stage 3 Gate repair changes：not present locally; accepted Stage 3 repairs are incorporated in HEAD.
- Bootstrap changed only documentation under `trade-strategy-ai/docs`.

### Entry condition

Stage 3 is recorded as accepted in both:

- `docs/Refactor-Implementation-Log.md`
- `docs/refactor-implementation-logs/stage-3.md`

Stage 3 final Gate decision:

```text
ACCEPTED: next Stage may begin
```

Stage 4 was not started by Stage 3.

### Documents inspected

- `docs/Trade-Refactor-TaskList.md`
- `docs/AI-Conversation-Templates.md`
- `docs/AI-Conversation-Task-Matrix.md`
- `docs/AI-Conversation-Project-Constraints-1.md`
- `docs/AI-Conversation-Project-Constraints-2.md`
- `docs/Refactor-Implementation-Log.md`
- `docs/refactor-implementation-logs/stage-3.md`
- `docs/refactor-implementation-plans/stage-3-implementation-plan.md`
- `docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`
- `docs/PROMPT_REVIEW_AND_MIGRATION.md`
- `docs/AUTHOR_PROFILE_PROMPT_FLOW.md`
- `docs/LLM-Prompt-Orchestration.md`

`docs/AI-Conversation-Project-Constraints.md` was requested but does not exist as a current file. Current repository evidence points to split files `AI-Conversation-Project-Constraints-1.md` and `AI-Conversation-Project-Constraints-2.md`; this was treated as a reconciled documentation naming issue, not a blocker.

### Code and test areas inspected

Domain and models:

- `src/models/stage2_canonical.py`
- `src/domain/enums.py`
- `src/domain/contracts.py`
- `src/domain/references.py`
- `src/domain/stage2_repositories.py`

Database and migrations:

- `src/db/migrations/versions/2026_06_14_0003_stage2_domain_schema.py`
- `src/db/migrations/versions/2026_06_14_0005_stage2_gate_schema_repair.py`
- `src/migrations/stage2_data_migration.py`

Repositories and services:

- `src/common/stage2_writer_routing.py`
- `src/db/repositories/stage3_prompt_runtime_repository.py`
- `src/db/repositories/stage3_single_article_repository.py`
- `src/db/repositories/rule_applicability_repository.py`
- `src/services/stage3_prompt_runtime_service.py`
- `src/services/stage3_single_article_service.py`
- `src/services/stage3_regression_service.py`
- `src/services/stage3_batch_service.py`
- `src/services/rule_applicability_service.py`
- `src/services/regime_rule_selection_service.py`
- `src/rule_pool/repository.py`

APIs and schemas:

- `api/routers/ui/article_metadata.py`
- `api/routers/ui/rule_pool.py`
- `api/routers/ui/strategy_studio.py`
- `api/routers/backtest_results.py`
- `api/schemas/article_analysis.py`

Jobs, workers, pipelines, CLI:

- `src/services/job_registry.py`
- `src/services/job_runner.py`
- `src/pipelines/optimize_rule_pool_pipeline_spec.py`
- `cli/main.py`

Web:

- `web/src/app/route-config.tsx`
- `web/src/pages/articles/ArticleResultsJourneyPage.tsx`
- `web/src/pages/articles/ArticlePipelinePage.tsx`
- `web/src/pages/rules/index.tsx`
- `web/src/pages/rule-pool/index.tsx`
- `web/src/features/rule-pool/rule-pool-list.tsx`
- `web/src/features/rule-pool/rule-pool-detail.tsx`
- `web/src/features/backtest/backtest-center.tsx`
- `web/src/features/backtest/regime-backtest-report.tsx`
- `web/src/lib/api/article-analysis.ts`
- `web/src/lib/api/article-metadata.ts`
- `web/src/lib/api/rule-pool.ts`
- `web/src/lib/api/strategyStudio.ts`
- `web/src/types/article-analysis.ts`

Tests:

- `tests/unit/services/test_stage2_writer_routing.py`
- `tests/regression/stage3/test_fixed_set.py`
- `tests/unit/stage3/test_prompt_runtime_service.py`
- `tests/unit/stage3/test_single_article_service.py`
- `tests/unit/stage3/test_regression_and_batch_services.py`
- `tests/integration/test_stage3_single_article.py`
- `tests/integration/test_stage3_batch.py`
- `tests/api/routers/test_rule_pool.py`
- `tests/api/routers/ui/test_strategy_studio.py`
- `tests/api/routers/ui/test_rule_pool_applicability.py`
- `tests/api/test_api_app_factory.py`
- `web/src/pages/articles/index.test.tsx`
- `web/src/pages/rule-pool/index.test.tsx`
- `web/src/pages/rule-pool/RulePoolDetailPage.test.tsx`
- `web/src/features/backtest/backtest-center.test.tsx`

### Subagent read-only investigations

Bootstrap used three read-only explorer agents:

- backend/domain/database inspection;
- rule-governance flow, jobs, CLI, and audit/provenance inspection;
- Web/API inspection.

All subagents were instructed not to modify files. Parent made final scope, ordering, and plan decisions.

### Stage 4 tasks discovered

- `RT-S4-001 自动审核与人工审核工作台`
- `RT-S4-002 规则指纹与规则族`
- `RT-S4-003 规则生命周期`

### Execution order

Recommended and frozen Bootstrap order:

1. `RT-S4-002 规则指纹与规则族`
2. `RT-S4-003 规则生命周期`
3. `RT-S4-001 自动审核与人工审核工作台`
4. Stage 4 Gate

Rationale:

- fingerprint/family/conflict data is needed by the review workbench;
- lifecycle/audit transitions are needed by the workbench;
- `AI-Conversation-Task-Matrix.md` allows RT-S4-002 + RT-S4-003 in one session serially, while RT-S4-001 is recommended later and separate.

### Current-state findings

Canonical foundation:

- `RuleCandidate`, `Rule`, `RuleVersion`, `RuleFamily`, `RuleFamilyMembership`, and `LifecycleEvent` already exist in the canonical Stage 2 model.
- Stage 3 article analysis writes canonical `PromptRun`, `ArticleStructure`, and `RuleCandidate`.
- Stage 3 human review can create `Rule` and `RuleVersion` as draft/pending-backtest boundary under canonical write scope.
- Stage 3 summary provenance remains revision-bound and preserves truthful unavailable semantics.

Gaps:

- no active canonical RuleFamily runtime service;
- no active duplicate/similar/conflict detection service;
- no complete Stage 4 lifecycle transition service;
- no dedicated public RuleFamily UI/API;
- automatic review statuses are still Stage 3 limited and do not match the five Stage 4 statuses;
- direct review APIs/CLI/jobs do not visibly enforce fixed-set gate before mutation;
- legacy `rule_pool` / `strategy_studio` / jobs / CLI review paths still exist and must not become formal governance paths.

### Invariant and boundary decisions

- Stage 4 formal rule governance must use canonical `RuleCandidate`, `Rule`, `RuleVersion`, `RuleFamily`, `RuleFamilyMembership`, and `LifecycleEvent`.
- Existing canonical rule tables are the starting point; do not create a second formal rule schema.
- Legacy `rule_pool` and `strategy_studio` are compatibility/history only unless routed through the canonical governance service.
- Fixed-set gate must precede all Stage 4 governance mutations, including API, job, worker, scheduler, and CLI entry points.
- Automatic review cannot make a rule formally usable.
- Stage 4 must preserve revision-bound summary behavior and truthful unavailable semantics.
- Future-stage Prompt behavior remains inactive.
- No Stage 5+ data/backtest/strategy/daily behavior is included in Stage 4.

### Conflicts and reconciliations

- The product plan has older stage numbering where "Stage 4" refers to daily pre-market. Resolution: use `Trade-Refactor-TaskList.md` for Stage 4 scope, and only reuse matching rule-governance semantics from the product plan.
- Requested `AI-Conversation-Project-Constraints.md` does not exist. Resolution: use current split files referenced by `AI-Conversation-Templates.md`.
- Some current API comments call `api/routers/ui/rule_pool.py` canonical, but runtime evidence shows it still wraps legacy `RulePool` objects. Resolution: Stage 4 must converge this into canonical governance or mark it compatibility/history.
- Some Web pages expose `Job`, `Pipeline`, `Schema`, `Regime`, or internal fields. Resolution: Stage 4 implementation must clean affected rule-governance surfaces, but this is not a Bootstrap blocker.

### Bootstrap validation performed

- Reviewed generated Stage 4 plan against:
  - `Trade-Refactor-TaskList.md`
  - `AI-Conversation-Templates.md`
  - `AI-Conversation-Project-Constraints-1.md`
  - `AI-Conversation-Project-Constraints-2.md`
  - `AI-Conversation-Task-Matrix.md`
- Verified every Stage 4 task is represented.
- Verified no later-stage work is pulled into Stage 4.
- Verified Stage 3 invariants remain explicit.
- Verified fixed-set gate precedes rule-governance operations.
- Verified unavailable semantics remain explicit.
- Verified working tree was clean before Bootstrap documentation edits.
- Reviewed documentation diff for scope, contradictions, unsupported claims, and accidental deletions.

### Files created or updated

- Created `docs/refactor-implementation-plans/stage-4-implementation-plan.md`
- Created `docs/refactor-implementation-logs/stage-4.md`
- Updated `docs/Refactor-Implementation-Log.md`

### Tests run

No product tests were run during Bootstrap because this session performed analysis and documentation only.

Validation commands run:

- `pwd`
- `git rev-parse --show-toplevel`
- `git status --short --branch --untracked-files=all`
- `git rev-parse HEAD`
- `git branch --show-current`
- `git remote -v`
- `git log --oneline -5`
- repository text searches and file inspections using `rg`, `sed`, `nl`, and `ls`

### Blocking issues

None.

### Non-blocking risks

- Sandbox PostgreSQL socket restriction remains an accepted environment limitation; Stage 3 external rerun passed.
- Older revisions without frozen summaries remain unavailable by design.
- Legacy `rule_pool` and `strategy_studio` surfaces remain present and must be handled by Stage 4 implementation.
- User-facing technical terminology remains in some affected Web surfaces.

### Bootstrap conclusion

`READY`

Stage 4 implementation may begin with `RT-S4-002` after explicit user authorization. Do not start implementation automatically from Bootstrap.
