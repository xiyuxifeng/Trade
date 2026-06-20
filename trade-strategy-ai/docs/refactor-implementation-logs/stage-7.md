# Stage 7 作者画像实施日志

## 当前摘要

- Stage：`Stage 7 作者画像`
- 当前活动：`2026-06-20 RT-S7-001 作者方法画像`
- 当前状态：`RT-S7-001 ACCEPTED`
- 当前 Task：`RT-S7-004`、`RT-S7-001` 已完成并接受；`RT-S7-002/003` 未开始
- 下一可执行 Task：`RT-S7-002 作者规则画像`
- 不得自动开始：`RT-S7-002` 需用户明确触发；不得开始 Stage 7 Gate

## 2026-06-19 Stage 7 Bootstrap

### Bootstrap Decision

`READY`

### Scope

This session only audited current implementation, froze Stage 7 contracts, created the Stage 7 implementation plan/log, and updated the main log. It did not implement production code, create migrations, modify frontend/backend runtime code, modify Prompt files, start `RT-S7-001`, start `RT-S7-004`, start Stage 8, publish strategies, generate daily trading behavior, commit, or push.

### Entry Verification

- Stage 0 accepted.
- Stage 1 accepted.
- Stage 2 accepted.
- Stage 3 accepted.
- Stage 4 accepted.
- Stage 5 Gate accepted.
- Stage 6 Gate accepted.
- Stage 7 had not started before this Bootstrap.
- Stage 8 has not started.
- Stage 6 formal facts did not contradict current Stage 7 Bootstrap requirements.
- Stage 6 formal path remains `Web/API -> BacktestApplicationService -> canonical repositories -> backtest_runs/backtest_results -> RuleApplicabilityProfile`.
- Formal `RuleApplicabilityProfile` source for Stage 7 validated profiles is identifiable and accepted.

Repository baseline before Bootstrap edits:

- Branch: `main`
- HEAD: `634d5be0f55abb3376683f95b46136184f372d50`
- Working tree: clean
- User-owned changes: none found
- Complete diff: empty

### Delegation

Used two bounded read-only `refactor_explorer_mini` subagents:

- Gate/log evidence explorer: verified Stage 0-6 acceptance, Stage 6 Gate acceptance, Stage 7/8 unstarted state, clean baseline and Stage 6 formal RuleApplicabilityProfile handoff.
- Implementation-surface explorer: mapped author/profile/persona/applicability routes, services, models, prompts, migrations and tests; classified legacy hazards and reusable canonical components.

No executor subagent was used. Bootstrap had no production-code write scope, and final contract decisions were retained by the Parent.

Runtime probe note: the refactor-orchestrator probe path from the skill was unavailable in this repository, so runtime probe metadata was not recorded. Configured mini-agent role files existed and declared `gpt-5.4-mini`.

### Frozen Contracts

- `AuthorMethodProfile` sources: `ArticleStructure`, article evidence, author-declared methods and LLM draft output with prompt/schema version.
- `AuthorRuleProfile` sources: reviewed `RuleVersion`, `RuleFamily`, rule governance evidence, rule dependencies and duplicate/conflict evidence.
- `AuthorValidatedProfile` sources: formal `RuleApplicabilityProfile`, formal `BacktestRun`, formal `BacktestResult`, Stage 6 level/market-state/sample evidence and inherited DatasetSnapshot/MarketSnapshot fingerprints.
- LLM output is draft evidence only and cannot approve, publish, overwrite, invalidate or replace official author profiles.
- Human review is required for official review/publication transitions.
- Every important conclusion must preserve evidence lane, source IDs, prompt/schema versions, evidence fingerprint and profile fingerprint.
- New evidence creates a draft, new version or superseding draft; it must not silently overwrite reviewed/published profiles.
- Author profiles are not author real trading performance.

### Current Implementation Assessment

`REUSE_AS_IS`:

- `Authors`, `ArticleRevision`, `ArticleStructure`, `PromptRun`.
- `RuleVersion`, `RuleVersionSourceLink`, `RuleFamily`, `RuleFamilyMembership`.
- `BacktestRun`, `BacktestResult`.
- Formal Stage 6 `RuleApplicabilityProfile` rows generated from immutable formal runs/results.
- `AuthorProfileKind`, prompt registry and canonical prompt/schema version concepts.
- `BusinessPageShell`, `ProductPageAdapter`.

`REFACTOR_AND_REUSE`:

- `AuthorProfileVersion`, pending Stage 7 audit for lifecycle, review, audit, fingerprints and time segmentation.
- `RuleCandidate` only where needed for provenance.
- `RuleApplicabilityService.generate_formal_draft()` and `review_formal_profile()` as formal Stage 6 path helpers.
- `/authors` route/page shell, replacing current persona fallback during Stage 7 implementation.
- Author-profile Prompt assets after Stage 7 schema/runtime/regression binding.

`COMPATIBILITY_ONLY`:

- `/persona`, persona UI, persona services and behavior-rule previews.
- `/profiles`, config profile UI/API/service.
- Legacy backtest pages and services where they remain old/admin/compatibility surfaces.

`REJECT_FROM_FORMAL_PATH`:

- Legacy `RuleApplicabilityService.build_profile()` and `review_profile()`.
- Legacy rule-pool profile UI/API output.
- Job payloads, Workflow results, Pipeline artifacts, file artifacts and old JSON result files.
- `SnapshotLoader`, `config_path`, EvidencePack, live Provider and mutable latest records.
- `backtest_result_runs` and `regime_metrics` as final formal truth.

`RETIRE_LATER`:

- Legacy persona/profile pages, file artifacts and duplicate legacy backtest/profile tooling after replacement, migration report, compatibility observation and rollback evidence.

### Final Task Order

1. `RT-S7-004 画像版本与时间分段`
2. `RT-S7-001 作者方法画像`
3. `RT-S7-002 作者规则画像`
4. `RT-S7-003 作者验证画像`

Rationale: RT-S7-004 must move earlier than the default order because all three profile types depend on shared version, lifecycle, review, audit, supersession, fingerprint and time-segment contracts. It must not generate profile content.

### Task Card Summary

- `RT-S7-004`: establish shared author-profile version/lifecycle/time-segment foundation; no content generation; stop if existing schema cannot safely preserve reviewed profiles.
- `RT-S7-001`: generate/review method profile drafts from ArticleStructure/article evidence; no real-performance claims; no full-text bulk prompt.
- `RT-S7-002`: generate/review rule profile drafts from reviewed RuleVersion/RuleFamily evidence; no RuleVersion/RuleFamily mutation.
- `RT-S7-003`: generate/review validated profile drafts from formal RuleApplicabilityProfile/BacktestRun/BacktestResult; no legacy profile/build_profile source and no strategy publication.

### Validation

Performed:

- Verified Stage 7 plan exists after write.
- Verified Stage 7 log exists after write.
- Verified main implementation log points to Stage 7 after write.
- Verified all four Stage 7 Task Cards exist in the plan.
- Verified legacy persona/profile restrictions are explicit.
- Verified canonical Stage 6 profile consumption is explicit.
- Verified author profile is not represented as real trading performance.
- Verified no Stage 8 / strategy publication behavior was started.
- Verified git diff contains only allowed documentation files.
- Ran `git diff --check`.

Tests not run:

- Full backend/frontend tests were not run because Bootstrap is documentation-only and no runtime, migration or Prompt file changed.

### Files Changed

- `docs/refactor-implementation-plans/stage-7-implementation-plan.md`
- `docs/refactor-implementation-logs/stage-7.md`
- `docs/Refactor-Implementation-Log.md`

### Risks

Blocking:

- None.

Non-blocking:

- Existing `/authors` page still falls back to legacy persona behavior.
- No dedicated Stage 7 runtime service/API/UI is accepted yet.
- Existing `AuthorProfileVersion` may need repair before implementation can satisfy all time-segment and audit requirements.
- Formal and legacy methods coexist inside `RuleApplicabilityService`; Stage 7 tasks must explicitly call only formal methods.
- Legacy `/persona`, `/profiles`, rule-pool profile and backtest-result paths remain reachable as compatibility/admin surfaces.

### Bootstrap Conclusion

`Bootstrap READY`.

Next executable Task is `RT-S7-004 画像版本与时间分段`, recommended model `gpt-5.5`. The next Task has not been started.

## 2026-06-19 RT-S7-004 画像版本与时间分段

### Task Decision

`ACCEPTED`

### Scope

Implemented only the shared author-profile version, lifecycle, audit, time-segment and diff foundation required by `RT-S7-004`.

Out of scope and not implemented: method/rule/validated profile content generation, author-profile Prompt runtime changes, Stage 8 strategy publication, daily strategy behavior, Stage 7 Gate, legacy persona retirement.

### Delegation

Used one bounded read-only `refactor_explorer_mini` subagent to inspect current author-profile/persona schema, API, UI, migration and test surfaces. Runtime probe script path remained unavailable; configured role files existed and declared `gpt-5.4-mini`, but effective runtime metadata was not independently verified.

No executor subagent was used. Parent retained implementation and final acceptance because lifecycle/version identity, migration safety and publication semantics are M3.

### Implemented Behavior

- Extended `AuthorProfileVersion` as the single formal author-profile version table for all three separated kinds: `method`, `rule`, `validated`.
- Added `pending_review` lifecycle support and `AuthorProfileVersionAudit` for actor, role, reason, source surface, before state and after state.
- Added explicit evidence period, effective period, source-version bindings, rule-family/applicability/backtest-result source bindings, evidence fingerprint, profile fingerprint and supersession fields.
- Added `AuthorProfileService` and repository operations for draft creation, list/get, submit for review, publish, archive and version diff.
- Enforced that new evidence creates a draft/revision and does not overwrite published profiles automatically.
- Enforced publish guard against overlapping already-published effective periods.
- Required profile conclusions in draft payloads to carry evidence, confidence, provenance and version binding.
- Added `/api/ui/v1/authors/profiles` list/get/create/review/publish/archive/diff API with viewer/operator boundaries and user-facing error messages.
- Updated `/authors` UI to consume the formal author-profile API and removed the default legacy persona fallback from the canonical `/authors` page.
- UI truthfully shows empty, loading, error, permission denied, partial evidence, draft, pending review, published and archived states, and states that author profiles are not real trading performance.

### Migration

Added `2026_06_19_0014_stage7_author_profile_versions`.

The migration is safe for both existing upgraded databases and fresh databases because Stage 2 table creation uses current ORM metadata. It conditionally adds missing columns, constraints and indexes, creates the audit table, and refuses downgrade when reviewed/published author-profile or audit data exists.

### Review Findings and Repairs

- `BLOCKER`: initial PostgreSQL fresh upgrade failed because `prompt_version` already existed when Stage 2 created `author_profile_versions` from current ORM metadata. Repaired by making the migration conditional for existing and fresh schema paths.
- `HIGH`: frontend `/authors` still used legacy persona fallback before implementation. Repaired by wiring `/authors` to the formal author-profile API and updating tests.
- `MEDIUM`: direct tests for service/router/migration were missing before this task. Added focused backend/API/frontend coverage.

No unresolved BLOCKER or required HIGH finding remains within the frozen `RT-S7-004` contract.

### Validation

Passed:

- `python -m pytest tests/unit/services/test_author_profile_service.py tests/api/routers/test_authors.py tests/unit/models/test_stage2_canonical_models.py tests/unit/db/test_migrations.py tests/api/test_api_app_factory.py tests/api/test_ui_openapi_contract.py tests/unit/domain/test_core_contracts.py tests/unit/services/test_home_dashboard_service.py`：`34 passed`
- `pnpm test -- src/lib/api/authors.test.ts src/pages/authors/index.test.tsx src/app/route-config.test.tsx src/app/navigation.test.ts src/app/product-journey.test.tsx src/pages/product-entry-pages.test.tsx`：`29 passed`
- `pnpm typecheck`：passed
- `python -m compileall api src tests/api/routers/test_authors.py tests/unit/services/test_author_profile_service.py`：passed
- PostgreSQL migration clean upgrade to head on temp DB `rt_s7_004_0619`：passed
- PostgreSQL migration safe re-run `upgrade head`：passed
- PostgreSQL migration `current`：`2026_06_19_0014 (head)`
- PostgreSQL migration rollback `downgrade 2026_06_19_0013`：passed
- PostgreSQL migration re-upgrade to head：passed
- `git diff --check`：passed

Notes:

- Sandbox local PostgreSQL connection was blocked by `PermissionError: Operation not permitted`; the same Alembic checks were rerun through approved unsandboxed local PostgreSQL commands.
- Frontend tests still print existing React Router future-flag warnings; this is existing non-blocking frontend technical debt.

### Files Changed

- `api/app.py`
- `api/routers/ui/__init__.py`
- `api/routers/ui/authors.py`
- `src/db/migrations/versions/2026_06_19_0014_stage7_author_profile_versions.py`
- `src/db/repositories/author_profile_repository.py`
- `src/domain/enums.py`
- `src/models/stage2_canonical.py`
- `src/services/author_profile_service.py`
- `tests/api/routers/test_authors.py`
- `tests/unit/db/test_migrations.py`
- `tests/unit/models/test_stage2_canonical_models.py`
- `tests/unit/services/test_author_profile_service.py`
- `web/src/lib/api/authors.ts`
- `web/src/lib/api/authors.test.ts`
- `web/src/pages/authors/index.tsx`
- `web/src/pages/authors/index.test.tsx`
- `web/src/pages/product-entry-pages.test.tsx`
- `web/src/types/authors.ts`

### Known Risks

- Source ID bindings are JSON fields with service-level validation rather than normalized FK tables. This preserves the frozen shared table contract for RT-S7-004 and avoids creating a second formal source, but later tasks must keep provenance explicit.
- `review_status` is stored as controlled service text rather than a separate DB enum; lifecycle remains the formal state axis.
- `invalidated` was not added because user and Task Card requested lifecycle support at minimum for draft/review-pending/published/archived and frozen RT-S7-004 scope did not require introducing new invalidation semantics. If future Gate requires invalidation, it should be handled as a bounded extension.

### Acceptance Conclusion

`RT-S7-004 ACCEPTED`.

Remaining Stage 7 tasks before Gate:

1. `RT-S7-001 作者方法画像`
2. `RT-S7-002 作者规则画像`
3. `RT-S7-003 作者验证画像`

Stage 7 is not complete. Stage 7 Gate has not started.

## 2026-06-20 RT-S7-001 作者方法画像

### Task Decision

`ACCEPTED`

### Scope

Implemented only `RT-S7-001 AuthorMethodProfile` draft generation from validated structured article results and the minimal `/authors` method section display.

Out of scope and not implemented: `RT-S7-002`, `RT-S7-003`, new migration/schema foundation beyond `RT-S7-004`, article full-text author total-profile generation, rule statistics generation, validated profile generation, strategy publication, Stage 7 Gate, Stage 8.

### Delegation

Used `refactor-orchestrator` with explicit delegation.

- One bounded read-only `refactor_explorer_mini` subagent mapped the RT-S7-001 implementation surface and confirmed no frozen-contract blocker.
- One bounded `refactor_executor_mini` subagent was started with a Task Card, but it did not return a usable handoff within the bounded wait window.
- Parent switched to the skill's `single-controller fallback`, kept the same frozen Task Card, completed implementation locally, and performed final semantic review and acceptance.

### Implemented Behavior

- Added formal `AuthorMethodProfile` generation runtime at `src/services/author_method_profile_service.py`.
- Formal generation consumes only canonical `ArticleStructure`, `ArticleRevision`, `PromptRun`, and `Authors` records; it does not read raw unbounded article text.
- Added `/api/ui/v1/authors/method-profiles/drafts` to generate method-profile drafts from explicit `article_structure_ids`.
- Added prompt orchestration for `author_method_profile_batch_v1` with one batch call over structured article payloads only, capped at 20 structures per request.
- Persisted prompt runtime evidence through `PromptRun` with `prompt/schema/model/token/cost/input_hash/run_id` metadata and reused cached runs by identity hash.
- Ensured LLM raw output is not the final formal fact source: runtime validates `author_method_profile_batch_v1` output, transforms it into formal draft payload/evidence, and writes through `AuthorProfileService`.
- Extended `AuthorProfileService` draft creation/view logic to preserve `prompt_run_id`, prompt metadata, and prompt-related partial-state checks.
- Generated formal method-profile payload sections for trading style, analysis framework, stock selection preference, entry/exit preference, risk expression, holding period, data dependencies, market-state assumptions, evidence, confidence, provenance, and version binding.
- Preserved separation from `AuthorRuleProfile` and `AuthorValidatedProfile`; method generation writes only `profile_kind=method` and keeps rule/backtest bindings empty.
- Missing or version-unaligned evidence now produces partial/unresolved draft output with `quality.status=insufficient_evidence`; it is not represented as success/false/zero.
- `/authors` now renders formal method-profile details from payload without reviving legacy persona behavior and without hiding other formal profile kinds.

### Contract Compliance

- No frozen Stage 7 foundation contract was redesigned.
- No migration was added.
- No second formal writer, fact source, Schema, or legacy entry point was introduced.
- No per-article author total-profile Prompt was added.
- Method generation uses structured-article batch input only and preserves review/publish semantics from `RT-S7-004`.
- New evidence still creates draft/revision output only; published profiles are not overwritten.
- UI text continues to state that author profiles are not real trading performance.

### Review Findings and Repairs

- `HIGH`: initial `/authors` method-section change filtered the canonical page down to method profiles only, which would have hidden later formal rule/validated versions. Repaired by restoring full formal list fetch and limiting the change to method-section rendering only.
- `MEDIUM`: router initially did not surface prompt-runtime failures with a user-facing error response. Repaired with explicit `PromptRuntimeError -> 503` mapping.
- `MEDIUM`: new unit tests initially failed on SQLite compatibility helpers; repaired by adding local SQLite compile helpers and `char_length` registration in the test fixture.

No unresolved `BLOCKER` or required `HIGH` finding remains within the frozen `RT-S7-001` contract.

### Validation

Passed:

- `python -m pytest tests/unit/services/test_author_method_profile_service.py tests/unit/services/test_author_profile_service.py tests/api/routers/test_authors.py tests/unit/llm/test_prompt_registry.py tests/api/test_ui_openapi_contract.py`：`12 passed`
- `pnpm test -- src/lib/api/authors.test.ts src/pages/authors/index.test.tsx`：`5 passed`
- `python -m compileall api src tests/api/routers/test_authors.py tests/unit/services/test_author_method_profile_service.py`：passed
- `pnpm typecheck`：passed
- `git diff --check`：passed

Not run:

- Database migration upgrade/safe-rerun/rollback was not run for RT-S7-001 because this task does not add or modify migrations.
- Additional frontend/API regression suites outside the touched authors surfaces were not rerun because the change stayed within the RT-S7-001 bounded surface and targeted suites passed.

### Files Changed

- `api/routers/ui/authors.py`
- `src/services/author_method_profile_service.py`
- `src/services/author_profile_service.py`
- `tests/api/routers/test_authors.py`
- `tests/unit/services/test_author_method_profile_service.py`
- `web/src/lib/api/authors.ts`
- `web/src/lib/api/authors.test.ts`
- `web/src/pages/authors/index.tsx`
- `web/src/pages/authors/index.test.tsx`
- `web/src/types/authors.ts`

### Known Risks

- `ArticleStructure` / `ArticleRevision` / content-hash bindings remain JSON source bindings plus `prompt_run_id`, not normalized FK detail rows. This stays within the frozen `RT-S7-004` storage contract and avoids a second formal table, but later Stage 7 tasks must continue to keep provenance explicit.
- Method-profile draft generation currently accepts explicit `article_structure_ids` from the caller and does not yet provide a full UI workflow for selecting structured articles. This is within RT-S7-001 scope because the formal runtime and method section are now available, but broader operator workflow ergonomics remain for later work.
- Batches under 10 structures are allowed only as partial evidence drafts with warnings. This matches the frozen “10–20 where applicable” constraint, but operator guidance still depends on choosing sensible batches.

### Acceptance Conclusion

`RT-S7-001 ACCEPTED`.

Remaining Stage 7 tasks before Gate:

1. `RT-S7-002 作者规则画像`
2. `RT-S7-003 作者验证画像`
3. `Stage 7 Gate`

Stage 7 is not complete. Stage 7 Gate has not started.
