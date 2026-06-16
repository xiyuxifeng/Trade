# Stage 4 规则管理、去重和规则族实施日志

## Current Status

- Stage：`Stage 4 规则管理、去重和规则族`
- Stage 状态：`[-] 进行中`
- 当前活动：`RT-S4-003 规则生命周期` 已完成并接受。
- 下一可执行 Task：`RT-S4-001 自动审核与人工审核工作台`
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

## 2026-06-16 RT-S4-002 Rule Fingerprint And RuleFamily

### Task

- Task ID: `RT-S4-002`
- 状态: `[x]`
- 结论: `ACCEPTED`

### Scope implemented

- deterministic and evolvable canonical rule fingerprinting;
- exact duplicate, parameter variant, similar-rule, and conflict comparison semantics;
- canonical `RuleFamily` / `RuleFamilyMembership` runtime;
- `RuleVersionSourceLink` provenance bridge for repeated source candidates;
- idempotent family, membership, and source-link creation;
- repeated formal-rule-version prevention for exact duplicates;
- repeated backtest-eligibility prevention for exact duplicates;
- fixed-set gate enforcement before canonical candidate governance mutation;
- focused API/schema/type updates exposing governance findings;
- Stage 4 implementation log and main log updates.

### Design decisions

- Exact fingerprint uses normalized rule semantics only and ignores mutable display-only fields such as title, description, evidence text ordering, and source copy wording.
- Family fingerprint generalizes parameter slots while preserving rule intent, so equal-family-but-different-exact rules become parameter variants instead of duplicates.
- Conflict detection is explicit when comparable rules share trigger structure but diverge in action direction.
- Exact duplicates reuse the existing canonical `RuleVersion`; they do not create a second `Rule` or `RuleVersion`.
- Repeated source provenance is preserved through canonical `rule_version_source_links`, not by mutating legacy `rule_pool`.
- Stage 3 candidate approval is now routed through canonical rule governance and requires a passing fixed-set gate immediately before mutation.

### Files changed

- `src/services/rule_governance_service.py`
- `src/db/repositories/rule_governance_repository.py`
- `src/db/migrations/versions/2026_06_16_0007_stage4_rule_governance.py`
- `src/models/stage2_canonical.py`
- `src/services/stage3_prompt_runtime_service.py`
- `src/services/stage3_single_article_service.py`
- `src/db/repositories/stage3_single_article_repository.py`
- `api/schemas/article_analysis.py`
- `api/routers/ui/article_metadata.py`
- `web/src/types/article-analysis.ts`
- `web/src/pages/articles/index.test.tsx`
- `tests/unit/services/test_rule_governance_service.py`
- `tests/unit/db/test_stage4_rule_governance_migration.py`
- `tests/integration/test_stage4_rule_governance.py`
- `tests/unit/models/test_stage2_canonical_models.py`
- `tests/integration/test_stage3_single_article.py`

### Database migration

- Added `2026_06_16_0007_stage4_rule_governance.py`.
- Adds canonical `rule_version_source_links`.
- Backfills `rule_candidates.candidate_fingerprint` and `rule_versions.canonical_fingerprint` with the RT-S4-002 fingerprint contract.
- Seeds source links from existing `RuleVersion.source_candidate_id`.

### Compatibility handling

- Stage 3 accepted contracts remain in force: canonical writer only, no dual-write, no legacy writer fallback, revision-bound summaries, truthful unavailable semantics.
- `rule_pool` / `strategy_studio` remain compatibility/history only and were not promoted to formal governance authorities.
- API response builder now provides a deterministic governance payload even for older/fake journey objects without persisted governance findings, preserving response compatibility during transition.

### Tests run

- Baseline gate before mutation:
  - `../.venv/bin/python -m cli.main stage3-regression run --fixed-set`
  - Result: `passed` (`article_count=12`, `processed_count=12`, `cached_count=12`, `semantic_failures=[]`, `validation_failures=[]`, `provider_failures=[]`, `persistence_failures=[]`)
- Focused pytest suite:
  - `../.venv/bin/pytest tests/unit/stage3/test_single_article_service.py tests/unit/stage3/test_prompt_runtime_service.py tests/unit/stage3/test_regression_and_batch_services.py tests/integration/test_stage3_single_article.py tests/integration/test_stage3_batch.py tests/integration/test_stage3_legacy_compatibility.py tests/api/routers/ui/test_article_metadata.py tests/api/test_ui_openapi_contract.py tests/unit/models/test_stage2_canonical_models.py tests/unit/db/test_migrations.py tests/unit/db/test_stage4_rule_governance_migration.py tests/unit/services/test_rule_governance_service.py tests/integration/test_stage4_rule_governance.py -q`
  - Result: `41 passed`
- Frontend compile/type check:
  - `corepack pnpm --dir web typecheck`
  - Result: passed
- Diff hygiene:
  - `git diff --check`
  - Result: passed
- Final gate rerun after implementation:
  - `../.venv/bin/python -m cli.main stage3-regression run --fixed-set`
  - Result: `passed` (`article_count=12`, `processed_count=12`, `cached_count=12`, `semantic_failures=[]`, `validation_failures=[]`, `provider_failures=[]`, `persistence_failures=[]`)

### Self-review repairs

- Removed circular import between rule governance and Stage 3 regression/single-article services.
- Added API fallback governance serialization so existing fake journeys in tests remain valid while real runtime always returns canonical governance findings.
- Updated Stage 3 integration fixtures to include fixed-set gate stubs and the new canonical source-link/family tables.
- Fixed frontend test fixtures to satisfy the expanded article-analysis contract.

### Remaining non-blocking risks

- `rule_version_source_links` introduces a new canonical provenance bridge; full production migration upgrade/rollback on real PostgreSQL should still be exercised at Stage 4 Gate.
- Legacy `rule_pool` / `strategy_studio` review surfaces still exist as compatibility/history UI/API and must remain non-authoritative until later Stage 4 tasks finish the convergence.
- Similar-rule and conflict semantics are intentionally conservative in RT-S4-002; richer human-review workflow and lifecycle policy remain for RT-S4-001 / RT-S4-003.

### Acceptance conclusion

- Deterministic fingerprint contract is active for new candidates and formal rule governance.
- Exact duplicates no longer create repeated canonical rule versions and are marked not eligible for repeated backtest.
- RuleFamily creation/membership is idempotent and canonical.
- Fixed-set gate is enforced before canonical candidate governance mutation.
- RT-S4-003 may begin after explicit user instruction.

## 2026-06-16 RT-S4-003 Rule Lifecycle

### Scope

- Task ID: `RT-S4-003`
- Status: `[x]`
- Objective: implement and enforce the canonical rule lifecycle required by Stage 4 without weakening the Stage 2 `FormalLifecycleState` contract.

### Frozen lifecycle contract

Canonical persisted states used by RT-S4-003:

- `RuleCandidate.review_state`: `extracted`, `manual_review`, `auto_review`, `approved`, `rejected`, `superseded`
- `RuleVersion.lifecycle_state`: `draft`, `in_review`, `published`, `archived`
- Existing `FormalLifecycleState.approved`, `rejected`, `superseded` remain part of the canonical contract, but RT-S4-003 does not fabricate user-facing “可用” semantics from them without provable lifecycle evidence.

User-facing lifecycle mapping:

- `候选` -> `RuleCandidate.review_state=extracted`
- `待审核` -> `RuleCandidate.review_state in {manual_review, auto_review}`
- `已批准` -> `RuleVersion.lifecycle_state=draft` with lifecycle evidence `display_label=已批准`
- `待回测` -> `RuleVersion.lifecycle_state=draft` with lifecycle evidence `display_label=待回测`
- `验证中` -> `RuleVersion.lifecycle_state=in_review`
- `可用` -> `RuleVersion.lifecycle_state=published` and `Rule.current_published_version_id=rule_version_id`
- `限定使用` -> `RuleVersion.lifecycle_state=published` and lifecycle restriction `limited`, or published without current-use promotion
- `已停用` -> `RuleVersion.lifecycle_state in {archived, rejected, superseded}`

Truthful unavailable / compatibility-only behavior:

- `FormalLifecycleState.approved` rows without Stage 4 lifecycle evidence do not get silently mapped to `可用`; API returns `compatibility_only` / `unavailable`.
- legacy `rule_pool` rows do not prove formal lifecycle state and remain compatibility-only history.

Allowed transitions implemented:

- `候选 -> 待审核`
- `待审核 -> 已批准` (human approval only; exact duplicates reuse the existing `RuleVersion`)
- `待审核 -> rejected`
- `已批准 -> 待回测`
- `待回测 -> 验证中`
- `验证中 -> 可用` (requires explicit evidence refs)
- `验证中 -> 限定使用` (requires explicit evidence refs and visible restriction)
- `可用 <-> 限定使用` as explicit supported recovery/change-of-scope transitions
- `已批准|待回测|验证中|可用|限定使用 -> 已停用`

Forbidden or blocked transitions:

- candidate approval directly from `候选`
- any automatic transition that makes a rule formally usable
- any transition to `可用` / `限定使用` without explicit evidence refs
- any backwards transition not listed above
- any lifecycle mutation through legacy `rule_pool` or `strategy_studio` compatibility writers

Actor / reason / correlation / idempotency / concurrency rules:

- every lifecycle mutation requires actor, timestamp, reason, before/after, and `correlation_id`
- repeated identical mutation with the same `correlation_id` is idempotent and returns the current lifecycle view without creating a second audit row
- stale writes are rejected via `expected_updated_at`
- lifecycle mutations run under canonical writer scope and fixed-set gate

### Compatibility handling

- `src/services/rule_pool_service.py` now rejects `review_rule` and `review_batch` as `compatibility_only`.
- `/api/ui/v1/rule-pool/*/review` and legacy `strategy_studio` compatibility review endpoints therefore stop serving as formal lifecycle writers.
- Stage 3 single-article review now delegates approval/rejection to the lifecycle service, so candidate approval cannot skip `待审核`.

### Database migration

- No new migration was added for RT-S4-003.
- Decision: existing canonical schema was sufficient because lifecycle display/restriction metadata, source action, and evidence refs fit durably in `LifecycleEvent.after_json` and `RuleVersion.evidence_json`, while stale-write protection uses existing timestamps.

### Files changed

- `src/services/rule_lifecycle_service.py`
- `api/routers/ui/rule_lifecycle.py`
- `src/services/stage3_single_article_service.py`
- `src/services/rule_pool_service.py`
- `api/routers/ui/rule_pool.py`
- `src/db/repositories/rule_governance_repository.py`
- `api/app.py`
- `api/routers/ui/__init__.py`
- `tests/integration/test_stage4_rule_lifecycle.py`
- `tests/api/routers/test_rule_lifecycle.py`
- `tests/integration/test_stage3_single_article.py`
- `tests/api/routers/test_rule_pool.py`
- `tests/unit/services/test_optimize_rule_pool_service.py`

### Tests run

- Baseline gate before implementation:
  - `../.venv/bin/python -m cli.main stage3-regression run --fixed-set`
  - Result: `passed` (`article_count=12`, `processed_count=12`, `cached_count=12`, `semantic_failures=[]`, `validation_failures=[]`, `provider_failures=[]`, `persistence_failures=[]`)
- Focused regression suite:
  - `python -m pytest tests/integration/test_stage3_single_article.py tests/integration/test_stage4_rule_governance.py tests/integration/test_stage4_rule_lifecycle.py tests/api/routers/test_rule_lifecycle.py tests/api/routers/test_rule_pool.py tests/api/routers/ui/test_strategy_studio.py tests/api/routers/ui/test_article_metadata.py tests/api/test_ui_openapi_contract.py tests/unit/services/test_optimize_rule_pool_service.py -q`
  - Result: `18 passed`
- Incremental TDD suites during red/green:
  - `python -m pytest tests/integration/test_stage4_rule_lifecycle.py tests/api/routers/test_rule_lifecycle.py tests/unit/services/test_optimize_rule_pool_service.py tests/api/routers/test_rule_pool.py -q`
  - Result: `8 passed`
  - `python -m pytest tests/integration/test_stage3_single_article.py tests/integration/test_stage4_rule_governance.py tests/api/routers/ui/test_strategy_studio.py tests/api/test_ui_openapi_contract.py tests/api/routers/ui/test_article_metadata.py -q`
  - Result: `10 passed`
- Verification commands:
  - `../.venv/bin/python -m compileall src api cli`
  - `git diff --check`
  - final `../.venv/bin/python -m cli.main stage3-regression run --fixed-set`
  - Result: all passed

### Self-review repairs

- Refreshed ORM rows after lifecycle mutation so async SQLite tests do not rely on expired timestamp attributes.
- Promoted lifecycle display state to business Chinese in the canonical response surface.
- Updated Stage 3 integration coverage to require explicit `候选 -> 待审核 -> 批准`.
- Rejected legacy `rule_pool` fake-success tests and converted them to compatibility-only assertions.

### Remaining non-blocking risks

- formal candidate transition API currently covers `RuleVersion` detail/history/transition; candidate review queue entrypoint is enforced in service and tests but is not yet surfaced as a full user workbench, which remains RT-S4-001 scope.
- `FormalLifecycleState.approved` is intentionally not auto-mapped to `可用`; later stages must preserve this boundary when Stage 6 validation evidence and Stage 8 publication semantics arrive.
- legacy CLI `rule-pool review` / `review-batch` still exist as compatibility commands and should be rewritten or retired in later Stage 4 work so operator guidance matches the new formal path.

### Acceptance conclusion

- canonical persisted lifecycle remains anchored to Stage 2 contracts
- user-facing lifecycle is now truthfully derived and transitionable without creating a second writer
- lifecycle audit is append-only through the canonical `LifecycleEvent` ledger
- fixed-set gate is enforced before formal lifecycle mutation
- legacy `rule_pool` write fallback is rejected
- RT-S4-003 is accepted

## 2026-06-16 RT-S4-001 Automatic Review And Human Review Workbench

### Scope

- Task ID: `RT-S4-001`
- Status: `[x]`
- Objective: implement deterministic automatic review, the canonical human-review service/API/workbench, and batch review boundaries on top of accepted RT-S4-002 and RT-S4-003 contracts.

### Frozen automatic-review contract

Automatic-review statuses implemented:

- `auto_pass`: low-risk non-entry rule; complete evidence; no duplicate/conflict/manual-review finding.
- `recommend_pass`: low-risk entry rule or exact duplicate that can reuse the existing formal `RuleVersion` and lifecycle track.
- `manual_review`: ambiguity, missing fields, inference, conflict, similar/parameter-variant, Kaipan dependency, or post-edit review.
- `not_backtestable`: candidate cannot yet truthfully enter pending-backtest because required backtest evidence/fields are unavailable.
- `recommend_reject`: missing evidence, missing condition, or missing action.

Deterministic reasons are derived from canonical payload, `RuleCandidate` missing/inferred fields, data dependencies, and accepted RT-S4-002 governance findings.

### Human-review actions

Implemented canonical actions:

- `edit`
- `approve`
- `approve_after_edit`
- `merge`
- `hold`
- `reject`
- `approve_low_risk` batch action
- `reject_invalid` batch action

Rules enforced:

- automatic review never makes a rule formally usable
- low-risk batch approval only routes through canonical `approve` and stops at the accepted Stage 4 `已批准` boundary
- `merge` is allowed only for exact duplicates and reuses the existing canonical `RuleVersion`
- invalid batch rejection only accepts `recommend_reject` and `not_backtestable`
- all formal review mutations call the RT-S4-003 lifecycle service and therefore inherit fixed-set gate enforcement and canonical writer scope

### API and Web

Added:

- canonical API router: `/api/ui/v1/rule-review`
- Web workbench: `/rules/review`

Capabilities exposed:

- candidate list with human-review filtering
- candidate detail with source article / revision summary provenance, automatic-review reasons, missing fields, dependency display, duplicate/similar/conflict findings, lifecycle state, allowed actions, and audit history
- mutation endpoints for single-item and batch review actions
- business-Chinese user wording only on the normal-user surface

Legacy handling:

- old `rule_pool` / `strategy_studio` review writes remain compatibility-only rejected
- no dual-write or legacy fallback was restored

### Audit and correlation-id behavior

- all human actions append to the canonical `LifecycleEvent` ledger
- `edit` / `hold` append candidate-scoped audit rows without fabricating formal lifecycle progress
- `approve` / `approve_after_edit` / `merge` propagate the caller `correlation_id` into the canonical governance-created lifecycle rows
- history remains append-only in normal operation

### Migration decision

- no new migration was added for RT-S4-001
- decision: existing JSON audit columns and canonical candidate/rule tables were sufficient

### Files changed

- `src/db/repositories/rule_review_repository.py`
- `src/services/rule_review_service.py`
- `src/db/repositories/rule_governance_repository.py`
- `src/services/rule_governance_service.py`
- `src/services/rule_lifecycle_service.py`
- `api/routers/ui/rule_review.py`
- `api/routers/ui/__init__.py`
- `api/app.py`
- `web/src/lib/api/rule-review.ts`
- `web/src/types/rule-review.ts`
- `web/src/pages/rules/index.tsx`
- `web/src/pages/rules/review.test.tsx`
- `tests/integration/test_stage4_rule_review.py`
- `tests/api/routers/test_rule_review.py`
- `tests/integration/test_stage4_rule_governance.py`
- `docs/Refactor-Implementation-Log.md`
- `docs/refactor-implementation-logs/stage-4.md`
- `docs/refactor-implementation-plans/stage-4-implementation-plan.md`

### Tests run

- Baseline and final fixed-set gate:
  - `../.venv/bin/python -m cli.main stage3-regression run --fixed-set`
  - Result: `passed` (`article_count=12`, `processed_count=12`, `semantic_failures=[]`, `validation_failures=[]`, `provider_failures=[]`, `persistence_failures=[]`)
- New RT-S4-001 TDD suites:
  - `python -m pytest tests/integration/test_stage4_rule_review.py tests/api/routers/test_rule_review.py -q`
  - Result: `5 passed`
- Expanded backend/API regression:
  - `python -m pytest tests/integration/test_stage3_single_article.py tests/integration/test_stage4_rule_governance.py tests/integration/test_stage4_rule_lifecycle.py tests/integration/test_stage4_rule_review.py tests/api/routers/test_rule_lifecycle.py tests/api/routers/test_rule_review.py tests/api/routers/test_rule_pool.py tests/api/routers/ui/test_strategy_studio.py tests/api/routers/ui/test_article_metadata.py tests/api/test_ui_openapi_contract.py tests/unit/services/test_optimize_rule_pool_service.py -q`
  - Result: `23 passed, 1 warning`
- Frontend:
  - `pnpm test -- src/pages/rules/review.test.tsx`
  - Result: `3 passed`
  - `pnpm typecheck`
  - Result: passed
- Verification commands:
  - `../.venv/bin/python -m compileall src api cli`
  - `git diff --check`
  - Result: passed

### Self-review repairs

- aligned exact-duplicate / new-rule formal audit rows so they preserve caller `correlation_id`
- corrected RT-S4-001 sample fixtures so recommend-pass, conflict, and edit-after-approve cases do not collapse into the same fingerprint family by mistake
- replaced the old `/rules/review` compatibility placeholder with the new canonical workbench while keeping normal-user wording in Chinese
- fixed Web type mismatches and error-category usage during typecheck

### Remaining non-blocking risks

- the current workbench implements the required action surface but is still a compact operator UI; broader review dashboard ergonomics can improve during Stage 4 Review without changing the accepted contract
- existing backend warning `RuntimeWarning: coroutine 'Connection._cancel' was never awaited` still appears in one OpenAPI test path and remains an existing non-blocking async cleanup issue
- batch approval intentionally stops at `已批准`; Stage 6/8 evidence and publication semantics remain unavailable and are not fabricated

### Acceptance conclusion

- deterministic automatic review now uses the required five statuses
- canonical human-review mutations are centralized and audited
- exact duplicates reuse one formal lifecycle track
- `/rules/review` is now the normal-user review workbench
- fixed-set gate still blocks canonical mutation paths
- RT-S4-002 and RT-S4-003 regression suites remain green
- RT-S4-001 is accepted
