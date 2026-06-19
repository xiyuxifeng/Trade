# Stage 6 回测与规则适用性实施日志

## 当前状态

- Stage：`Stage 6 回测与规则适用性`
- 当前活动：`2026-06-19 RT-S6-003 规则适用性画像`
- 当前状态：`RT-S6-003 ACCEPTED`
- 当前已接受：`RT-S6-001`, `RT-S6-002`, `RT-S6-004`, `RT-S6-003`
- 下一可执行 Task：`Stage 6 Gate`
- 不得自动开始：Stage 6 Gate 需用户明确触发；Stage 6 未完成

## 2026-06-18 Stage 6 Bootstrap

### Bootstrap Decision

`READY`

### Scope

This session only audited current implementation, froze Stage 6 contracts, created the Stage 6 implementation plan/log, and updated the main log. It did not implement production code, create migrations, start `RT-S6-001`, start Stage 7, or mark any Stage 6 Task accepted.

### Repository Baseline

- Branch：`main`
- HEAD：`066300e514a38dd283093ea846a4b5adcaf5add7`
- Working tree before Bootstrap edits：clean
- Complete diff before Bootstrap edits：empty
- User-owned or partial Stage 6 changes before Bootstrap：none found

### Materials Inspected

- `AGENTS.md`
- `trade-strategy-ai/AGENTS.md`
- `docs/AI-Conversation-Templates.md`
- `docs/Trade-Refactor-TaskList.md`
- `docs/AI-Conversation-Task-Matrix.md`
- `docs/AI-Conversation-Project-Constraints-2.md`
- `docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md` Stage-6-related sections
- `docs/Refactor-Implementation-Log.md`
- `docs/refactor-implementation-logs/stage-5.md`
- `docs/refactor-implementation-plans/stage-5-implementation-plan.md`
- current branch, HEAD, git status, complete diff
- Stage-6-related backend code, models, repositories, jobs, CLI/API, tests, Web routes/pages/API clients/types

### Delegation

Used read-only subagents:

- Stage 5 entry-gate and canonical data ownership audit.
- Backend backtest/rule-applicability/data/runtime audit.
- Frontend/API route/UI/compatibility audit.

Parent independently verified critical findings before writing docs.

### Entry Gate Evidence

- Stage 5 Gate is explicitly `ACCEPTED`.
- `RT-S5-001`, `RT-S5-002`, and `RT-S5-003` are accepted.
- `Stage 6 Bootstrap` is documented as the next action.
- Canonical writer remains effective true in normal runtime; guarded emergency fallback branches are non-formal and cannot be used by Stage 6.
- No accepted formal dual-write path was found.
- DatasetSnapshot formal source remains `dataset_snapshots`.
- MarketSnapshot formal source remains `market_snapshots` and child tables.
- Stage 5 formal mutation remains under `系统管理 -> 数据与调度`, `/api/ui/v1/system/data/*`, `DataSchedulingService`, and `system-data-operation`.
- Raw Stage 5 data Job/Workflow/API/CLI mutation paths remain rejected, read-only, or compatibility-only.
- Truthful unavailable/partial/invalid/conflict/insufficient_coverage semantics remain required and intact at the Stage 5 contract level.

### Current Implementation Assessment

`REUSE_AS_IS`:

- RuleVersion/RuleFamily canonical models.
- RuleGovernanceService fingerprint/family logic.
- RuleLifecycleService.
- DatasetSnapshot model/repository/service.
- MarketSnapshot stored facts and repositories.
- BusinessPageShell/ProductPageAdapter UI shell components.

`REFACTOR_AND_REUSE`:

- BacktestEngine execution primitives.
- BacktestService orchestration ideas.
- MarketSnapshotService producer, excluding file/config_path formal reads.
- MarketRegimeRepository and market-state records with point-in-time query additions.
- IndicatorService only after non-mutating read/derivation split.
- Existing backtest result/profile models as migration input, not final contract.
- `/rules/backtests` and `/rules/results` product wrappers.

`COMPATIBILITY_ONLY`:

- `SnapshotLoader` as currently written.
- legacy `backtest_results` job fallback.
- `JobService`/`JobRunner`/`JobRegistry` as raw business entry.
- CLI backtest commands.
- legacy rule_pool surfaces.
- `/backtest`, `/backtest/regime`, `/backtest/candidates`.

`REJECT_FROM_FORMAL_PATH`:

- file snapshots;
- config_path runtime dependency;
- EvidencePack fallback;
- live Provider calls during formal execution;
- Workflow/Pipeline/Artifact as business contract;
- raw Job submission as normal-user entry;
- direct mutable OHLCV/latest-record reads as Stage 6 truth source;
- runtime indicator mutation during frozen execution.

`RETIRE_LATER`:

- rule_backtest scheduler.
- legacy technical pages and deep links after migration/observation/rollback evidence.

### Frozen Contracts

Frozen in `docs/refactor-implementation-plans/stage-6-implementation-plan.md`:

- canonical data flow;
- selection unit;
- BacktestRun;
- BacktestResult;
- RuleApplicabilityProfile;
- recommendation/sample policy;
- point-in-time matrix;
- DatasetSnapshot/indicator contract;
- MarketSnapshot/market-state contract;
- Level 1/2/3 matrix;
- API/application-service contract;
- Web user journey;
- permissions and audit;
- Schema and migration plan;
- compatibility/retirement matrix;
- reproducibility contract;
- Task order and four bounded Task Cards.

### Schema and Migration Decision

Bootstrap decided Stage 6 implementation is expected to require new or extended canonical Schema:

- immutable BacktestRun table or equivalent canonical table;
- immutable BacktestResult table or equivalent canonical table;
- per-market-state/per-rule metric persistence;
- RuleApplicabilityProfile extension or replacement for versioning, source result IDs, requested/effective level, coverage, quality, review, and supersession;
- existing `backtest_result_runs` remains compatibility/adaptor until retirement.

No migration was created in this Bootstrap session.

### Validation

Performed:

- reviewed required documentation and Stage-6-related implementation surfaces;
- reviewed current git branch, HEAD, status, and complete diff;
- verified Stage 5 accepted evidence;
- verified all four Task Cards exist in the Stage 6 plan;
- verified canonical data ownership is explicit in the Stage 6 plan;
- verified existing implementation dispositions are recorded;
- verified legacy paths are not formal Stage 6 inputs;
- verified snapshot-only execution is mandatory on formal path;
- verified point-in-time semantics are frozen;
- verified indicator behavior is frozen;
- verified Level 1/2/3 semantics are frozen;
- verified missing Kaipan remains a limitation;
- verified RuleApplicabilityProfile does not overwrite rules;
- verified human-review boundaries remain explicit;
- verified one formal API/Web/application entry exists;
- verified generic Job remains internal transport only;
- verified Stage 5 contracts are unchanged;
- verified `RT-S6-001` has not been started.

Not run:

- Full test suites; Bootstrap is documentation-only.
- PostgreSQL migration tests; no migration was created.

### Files Changed

- `docs/refactor-implementation-plans/stage-6-implementation-plan.md`
- `docs/refactor-implementation-logs/stage-6.md`
- `docs/Refactor-Implementation-Log.md`

### Risks

Blocking:

- None identified.

Non-blocking:

- Legacy internal tooling retirement remains deferred.
- Existing emergency rollback code paths for canonical writer disabled state remain present but are not active formal runtime.
- Readiness coverage persistence may be shallow for historical Stage 6 audit queries.
- Historical Kaipan availability depends on provider credentials/network and upstream source availability.
- Existing backtest implementation is legacy-heavy and must not be preserved as formal architecture.

External evidence limitations:

- Bootstrap did not run full test suites.
- Bootstrap did not run PostgreSQL migration replay.
- Provider-backed Kaipan evidence cannot be proven without credentials/network.

### Next Task

`RT-S6-001 回测工作台` may begin after explicit user instruction. Recommended Parent model: `gpt-5.5`. It may share a Parent session with `RT-S6-002` only as separate sequential acceptance batches. It has not been started.

## 2026-06-18 RT-S6-001 回测工作台

### Task Decision

`ACCEPTED`

### Scope

Implemented the formal normal-user backtest workbench foundation only:

- RuleVersion primary selection and optional RuleFamily selection;
- canonical dependency check over RuleVersion/RuleFamily, DatasetSnapshot, and required MarketSnapshot facts;
- immutable `BacktestRun` foundation with frozen RuleFamily member RuleVersion IDs;
- formal `BacktestApplicationService` and `/api/ui/v1/rules/backtests/*` API boundary;
- formal `/rules/backtests` normal-user workbench UI;
- viewer dependency check, operator run creation, and audit fields;
- raw Job/legacy backtest paths isolated from the formal business entry.

Did not start or implement:

- `RT-S6-002` point-in-time market-state execution;
- `RT-S6-003` applicability profile generation/review;
- `RT-S6-004` full Level 1/2/3 enforcement;
- Stage 7 or strategy/author-profile publication behavior.

### Delegation

Used two bounded read-only subagents:

- Backend/API/schema explorer: inspected RuleVersion/RuleFamily, DatasetSnapshot/MarketSnapshot, auth/audit, legacy backtest paths, migration/test surfaces.
- Frontend/API-client explorer: inspected `/rules/backtests`, route config, API client/types, auth patterns, and user-facing terminology risks.

Parent implemented all core M3 decisions, schema, service/API, UI, tests, migration replay, review, and acceptance decision.

### Files Changed

- `src/models/stage2_canonical.py`
- `src/db/repositories/backtest_run_repository.py`
- `src/db/repositories/__init__.py`
- `src/services/backtest_application_service.py`
- `src/db/migrations/versions/2026_06_18_0010_stage6_backtest_run_foundation.py`
- `api/routers/ui/formal_backtests.py`
- `api/routers/ui/__init__.py`
- `api/app.py`
- `tests/unit/services/test_backtest_application_service.py`
- `tests/api/routers/test_formal_backtests.py`
- `tests/unit/db/test_migrations.py`
- `tests/api/test_ui_openapi_contract.py`
- `web/src/features/backtest/formal-backtest-workbench.tsx`
- `web/src/features/backtest/backtest-center.stage6.test.tsx`
- `web/src/lib/api/backtests.ts`
- `web/src/lib/api/backtests.test.ts`
- `web/src/types/backtests.ts`
- `web/src/pages/rules/index.tsx`
- `web/src/pages/product-entry-pages.test.tsx`

### Key Design Decisions

- Created canonical `backtest_runs` as the formal immutable run foundation; `backtest_result_runs` remains compatibility-only.
- Formal run identity binds request fingerprint, RuleVersion/RuleFamily identity, frozen RuleFamily member RuleVersion IDs, DatasetSnapshot ID/fingerprint, requested/effective level, snapshot-only policy, engine/policy versions, audit fields, and reproducibility fingerprint.
- Formal API is `Web/API -> BacktestApplicationService -> dependency check -> BacktestRun creation`; it does not call raw Job, Workflow, CLI, file snapshot, config path, EvidencePack, or live Provider.
- Dependency check returns truthful business states and keeps missing data as `unavailable` / `insufficient_coverage`; missing facts are not converted to false/zero/success.
- `/rules/backtests` now uses a dedicated normal-user formal workbench instead of the legacy raw-job backtest page.
- `profile_id` remains accepted only as optional configuration context and is not treated as the tested fact source.

### Database Migration

- Added linear migration `2026_06_18_0010_stage6_backtest_run_foundation.py` after `2026_06_17_0009`.
- Migration creates `backtest_runs` and indexes without modifying existing legacy result tables.
- Downgrade drops only the new `backtest_runs` foundation and leftover status enum if present.
- PostgreSQL replay evidence:
  - `alembic current` before upgrade: `2026_06_17_0009`
  - `alembic upgrade head`: passed
  - `alembic current`: `2026_06_18_0010 (head)`
  - `alembic downgrade 2026_06_17_0009`: passed
  - `alembic upgrade head`: passed
  - final `alembic current`: `2026_06_18_0010 (head)`
- Repair during replay: initial enum migration attempted duplicate PostgreSQL enum creation; fixed by storing status as bounded string in the migration while the application keeps enum-level values.

### Compatibility

- Legacy `/backtest`, `/backtest/regime`, `/backtest_results`, `BacktestService`, `SnapshotLoader`, raw backtest Job types, CLI, Workflow, and Pipeline paths remain compatibility/admin-only and are not formal RT-S6-001 inputs.
- No formal API or normal-user UI can disable snapshot-only execution.

### Validation

Ran:

- `../.venv/bin/python -m pytest tests/unit/services/test_backtest_application_service.py tests/api/routers/test_formal_backtests.py tests/unit/db/test_migrations.py tests/api/test_ui_openapi_contract.py tests/api/test_api_app_factory.py -q`
  - `18 passed`
- `pnpm test -- src/lib/api/backtests.test.ts src/features/backtest/backtest-center.stage6.test.tsx src/pages/product-entry-pages.test.tsx src/app/route-config.test.tsx`
  - `4 files passed`, `28 tests passed`
- `pnpm typecheck`
  - passed
- `../.venv/bin/python -m compileall src api cli`
  - passed
- `../.venv/bin/python -m alembic -c src/db/migrations/alembic.ini heads`
  - single head: `2026_06_18_0010`
- PostgreSQL migration upgrade/downgrade/re-upgrade replay as listed above.
- `git diff --check`
  - passed

Warnings:

- Existing React Router v7 future-flag warnings appeared in frontend tests and remain non-blocking existing technical debt.

### Review Findings and Repairs

- Frontend explorer found `/rules/backtests` still using raw Job submission and user-facing technical wording. Repaired by replacing the formal result slot with `FormalBacktestWorkbench` and formal API client calls.
- Backend migration replay found duplicate PostgreSQL enum creation. Repaired migration to use bounded status string storage and reran upgrade/downgrade/re-upgrade successfully.
- Existing product entry test expected the legacy backtest marker. Repaired to expect the formal workbench marker.
- Final source guards verify the formal application service does not use `JobService`, `SnapshotLoader`, `EvidencePack`, `config_path`, Provider concepts, raw job creation, or legacy result fallback.

### Remaining Risks

Blocking:

- None identified for `RT-S6-001`.

Non-blocking:

- Full point-in-time market-state execution remains `RT-S6-002`.
- Full Level 1/2/3 enforcement remains `RT-S6-004`; RT-S6-001 records requested level and truthful dependency state only.
- Applicability profile draft/review remains `RT-S6-003`.
- Legacy backtest/result routes remain compatibility surfaces until later retirement evidence.
- Formal workbench currently accepts known canonical IDs as user input; richer selector/list endpoints can be added later without changing the formal run foundation.

### Acceptance Conclusion

`RT-S6-001 ACCEPTED`.

`RT-S6-002` may begin only after explicit user instruction. `RT-S6-002` has not been started.

## 2026-06-19 RT-S6-002 分市场状态回测

### Task Decision

`ACCEPTED`

### Scope

Implemented the formal Level 2 market-state-aware execution/results portion only:

- point-in-time market-state lookup from canonical `MarketSnapshot`-derived `MarketRegimeRecord` facts;
- `available_at <= decision_time` enforcement for market snapshots and market-state records using Asia/Shanghai decision-time semantics;
- immutable `BacktestResult` foundation in `backtest_results`;
- formal per-market-state metrics, sample-state counts, coverage, warnings, limitations, provenance and fingerprints;
- formal execute/read API under `/api/ui/v1/rules/backtests/runs/{run_id}/execute` and `/result`;
- `/rules/results` formal result reader using business wording “市场状态”;
- migration and focused backend/API/frontend verification.

Did not start or implement:

- `RT-S6-004` full Level 1/2/3 downgrade/reject policy;
- `RT-S6-003` RuleApplicabilityProfile generation/review;
- Stage 7 author profile, strategy publication, daily trading objects, Prompt changes, Workflow/CLI/raw Job entries, or legacy retirement.

### Delegation

Used two bounded read-only subagents:

- Stage 6 docs/task-card explorer: verified `RT-S6-001` acceptance, exact `RT-S6-002` requirements, log requirements, and M3 risks.
- Backend/API/UI explorer: mapped accepted `RT-S6-001` service/model/API/UI surfaces, canonical MarketSnapshot/market-state fields, result gaps, and legacy paths to avoid.

Parent implemented the schema, service, API, UI, tests, migration replay, review, and acceptance decision.

### Files Changed

- `src/models/stage2_canonical.py`
- `src/db/repositories/backtest_run_repository.py`
- `src/services/backtest_application_service.py`
- `src/db/migrations/versions/2026_06_19_0011_stage6_market_state_backtest_results.py`
- `api/routers/ui/formal_backtests.py`
- `tests/unit/services/test_backtest_application_service.py`
- `tests/unit/db/repositories/test_backtest_run_repository.py`
- `tests/api/routers/test_formal_backtests.py`
- `tests/api/test_ui_openapi_contract.py`
- `tests/unit/db/test_migrations.py`
- `web/src/features/backtest/formal-backtest-results.tsx`
- `web/src/features/backtest/backtest-center.stage6.test.tsx`
- `web/src/lib/api/backtests.ts`
- `web/src/lib/api/backtests.test.ts`
- `web/src/types/backtests.ts`
- `web/src/pages/rules/index.tsx`
- `web/src/pages/product-entry-pages.test.tsx`
- `docs/refactor-implementation-logs/stage-6.md`
- `docs/Refactor-Implementation-Log.md`

### Key Design Decisions

- Kept the formal entry under `BacktestApplicationService`; no raw Job, Workflow, CLI, file artifact, `config_path`, EvidencePack, live Provider or legacy result fallback was added.
- Added immutable `backtest_results` instead of promoting legacy `backtest_result_runs` / legacy `regime_metrics` to formal truth.
- Bound result identity to `request_fingerprint`, DatasetSnapshot fingerprint, MarketSnapshot fingerprints, market-state model/source version, market-state result version, decision-time policy, sample-state counts, and per-market-state metrics.
- Missing market-state is recorded as `insufficient_coverage` / `market_state_unavailable` and excluded from loss, return and win-rate denominators.
- `/rules/results` now uses the formal result API and user-facing “市场状态” wording.

### Database Migration

- Added one linear Alembic revision: `2026_06_19_0011_stage6_market_state_backtest_results`.
- Creates `backtest_results` with unique `run_id`, unique `result_fingerprint`, per-market-state metrics, sample-state counts, coverage, warnings, limitations, provenance, audit and fingerprint fields.
- PostgreSQL replay evidence on a temporary database:
  - `upgrade head` passed;
  - `downgrade 2026_06_18_0010` passed;
  - re-`upgrade head` passed.
- `alembic heads` returned single head `2026_06_19_0011`.
- SQLite replay was attempted but blocked by an older pre-existing migration using unsupported SQLite constraint ALTER before this revision; PostgreSQL replay was used as authoritative evidence.

### Compatibility Handling

- Legacy `/backtest`, `/backtest/regime`, `/backtest_results`, raw Job, Workflow, CLI, JSON result files and legacy `regime_metrics` remain compatibility-only/non-formal.
- No legacy fallback is used by the formal result API or `/rules/results` product page.
- `RT-S6-001` formal run contract remains intact; `backtest_runs` is only extended by reading the existing frozen market-state fields.

### Validation

Run and passed:

- `python -m pytest tests/unit/db/repositories/test_backtest_run_repository.py tests/unit/services/test_backtest_application_service.py tests/api/routers/test_formal_backtests.py tests/unit/db/test_migrations.py tests/api/test_ui_openapi_contract.py -q` -> `22 passed`, 1 existing async cleanup warning.
- `python -m pytest tests/unit/db/repositories/test_backtest_run_repository.py tests/unit/services/test_backtest_application_service.py -q` -> `9 passed`.
- `python -m compileall src/models/stage2_canonical.py src/services/backtest_application_service.py src/db/repositories/backtest_run_repository.py api/routers/ui/formal_backtests.py src/db/migrations/versions/2026_06_19_0011_stage6_market_state_backtest_results.py` -> passed.
- `pnpm test -- src/lib/api/backtests.test.ts src/features/backtest/backtest-center.stage6.test.tsx src/pages/product-entry-pages.test.tsx` -> `19 passed`.
- `pnpm typecheck` -> passed.
- `git diff --check` -> passed.
- Alembic PostgreSQL `upgrade head`, `downgrade 2026_06_18_0010`, re-`upgrade head` -> passed.
- `alembic heads` -> single head `2026_06_19_0011`.

Warnings observed:

- existing async connection cleanup warning in OpenAPI/router-related pytest.
- existing React Router future-flag warnings in frontend tests.
- shell startup warnings from local RVM `ps` sandbox restriction.

### Review Findings and Repairs

- RED tests first showed existing code treated future market snapshots as ready and lacked formal execution/result methods.
- Repaired by adding point-in-time repository lookup, service availability proof, immutable result persistence and API read/execute endpoints.
- Frontend product page initially still pointed at the legacy result component; repaired by introducing a formal result component and updating product page tests.
- Migration replay initially failed against a removed local database, then SQLite was blocked by an older migration; repaired verification by creating a temporary PostgreSQL database and replaying upgrade/downgrade/re-upgrade.
- Final review found oldest-eligible market-state selection and partial coverage validity issues; repaired by selecting latest market-state record available at decision time and marking partial market-state coverage as `insufficient_coverage` / `completed_invalid`.

### Risks

Blocking:

- None identified for `RT-S6-002`.

Non-blocking:

- Formal sample generation/evaluation remains intentionally narrow: RT-S6-002 aggregates deterministic canonical samples supplied through the frozen DatasetSnapshot contract and does not implement broader Level 1/2/3 policy enforcement. Full level policy remains `RT-S6-004`.
- Legacy result/report pages still exist as compatibility surfaces outside the formal `/rules/results` product page.
- Temporary PostgreSQL migration database was created for verification and dropped after replay.

### Acceptance Conclusion

`RT-S6-002 ACCEPTED`.

`RT-S6-004` may begin only after explicit user instruction. `RT-S6-004` has not been started.

`RT-S6-003` has not been started and must not begin before `RT-S6-004`. Stage 6 is not complete.

## 2026-06-19 RT-S6-004 回测分级

### Task Decision

`ACCEPTED`

### Scope

Implemented the formal Level 1 / Level 2 / Level 3 data-level policy only:

- Level 1 OHLCV, Level 2 OHLCV + 市场状态, Level 3 OHLCV + 市场状态 + Kaipan 数据 enforcement;
- rule minimum-level detection from `RuleVersion.data_dependencies`;
- RuleFamily strictest-member minimum-level behavior with member-level dependency details;
- dependency-check states for runnable, downgradeable, repair-needed/insufficient coverage, not-runnable, unavailable, conflict and invalid;
- Level 3 Kaipan slot proof using canonical `MarketSnapshot` slot, captured/available time and decision-time policy;
- explicit downgrade acceptance with actor/reason/effective-level audit;
- immutable run/result level policy persistence and API/UI visibility;
- missing Kaipan limitation semantics so missing Kaipan is not false, no signal, loss, success or silent downgrade.

Did not start or implement:

- `RT-S6-003` RuleApplicabilityProfile generation/review;
- Stage 7 author profile;
- Stage 8 strategy publication;
- daily selection, strategy publication, Prompt changes, Workflow/CLI/raw Job entries, or legacy retirement.

### Delegation

Used one bounded read-only subagent:

- Explorer Alpha: mapped formal backtest service/repository/model/API/UI/migration/test surfaces, verified RT-S6-001 and RT-S6-002 acceptance evidence, and identified RT-S6-004 gaps. It did not edit files.

Parent implemented the level policy, schema/migration, API, UI, tests, migration replay, semantic review and acceptance decision.

### Files Changed

- `src/services/backtest_application_service.py`
- `src/models/stage2_canonical.py`
- `src/db/migrations/versions/2026_06_19_0012_stage6_backtest_level_policy.py`
- `api/routers/ui/formal_backtests.py`
- `tests/unit/services/test_backtest_application_service.py`
- `tests/api/routers/test_formal_backtests.py`
- `tests/unit/db/test_migrations.py`
- `web/src/types/backtests.ts`
- `web/src/features/backtest/formal-backtest-workbench.tsx`
- `web/src/features/backtest/formal-backtest-results.tsx`
- `web/src/features/backtest/backtest-center.stage6.test.tsx`

### Key Design Decisions

- Kept the formal path under `BacktestApplicationService`; no raw Job, Workflow, CLI, file artifact, `config_path`, EvidencePack, live Provider or legacy result fallback was added.
- Added a bounded level-policy contract in the formal service instead of introducing a second formal backtest source.
- Persisted `level_policy_version`, `downgrade_reason` and `repair_guidance` on `backtest_runs`, and `level_policy_version` on `backtest_results`.
- Used existing `RuleVersion.data_dependencies` as the smallest safe rule minimum-level extension surface; no Stage 4 lifecycle redesign was needed.
- RuleFamily dependency checks use the strictest member minimum level and report the blocking member instead of silently dropping unsupported members.
- Level 3 requires the configured Kaipan slot `09-25` to be captured and available before simulated decision time; other slots cannot satisfy Level 3.
- Level 3 downgrade is never silent: dependency check returns `downgradeable`, creation remains blocked unless the operator sends explicit acceptance, and audit records actor, role, reason, accepted effective level and time.
- Missing Kaipan during execution is counted as `kaipan_unavailable` and excluded from false/loss/success metrics.

### Database Migration

- Added one linear Alembic revision: `2026_06_19_0012_stage6_backtest_level_policy`.
- Migration is additive:
  - `backtest_runs.level_policy_version`;
  - `backtest_runs.downgrade_reason`;
  - `backtest_runs.repair_guidance`;
  - `backtest_results.level_policy_version`.
- PostgreSQL replay evidence on temporary database `rt_s6_004_migration_0619`:
  - `upgrade head` passed;
  - `downgrade 2026_06_19_0011` passed;
  - re-`upgrade head` passed;
  - clean replay `upgrade head` passed;
  - final `alembic current` reported `2026_06_19_0012 (head)`.
- Temporary database was dropped after verification.

### Compatibility Handling

- RT-S6-001 formal run foundation remains intact; `backtest_runs` is only additively extended.
- RT-S6-002 formal result foundation remains intact; `backtest_results` is only additively extended.
- Legacy `/backtest`, `/backtest/regime`, `/backtest_results`, raw Job, Workflow, CLI, JSON result files and legacy result tables remain compatibility-only/non-formal.
- A completed internal job remains insufficient evidence for a valid formal level result.

### Validation

Run and passed:

- `../.venv/bin/python -m pytest tests/unit/services/test_backtest_application_service.py -q` -> `14 passed`.
- `../.venv/bin/python -m pytest tests/unit/services/test_backtest_application_service.py tests/api/routers/test_formal_backtests.py tests/unit/db/test_migrations.py tests/api/test_ui_openapi_contract.py -q` -> `29 passed`, 1 existing async cleanup warning.
- `pnpm test -- src/lib/api/backtests.test.ts src/features/backtest/backtest-center.stage6.test.tsx src/pages/product-entry-pages.test.tsx` -> `19 passed`.
- `pnpm typecheck` -> passed.
- `../.venv/bin/python -m compileall src/models/stage2_canonical.py src/services/backtest_application_service.py api/routers/ui/formal_backtests.py src/db/migrations/versions/2026_06_19_0012_stage6_backtest_level_policy.py` -> passed.
- `../.venv/bin/python -m alembic -c src/db/migrations/alembic.ini heads` -> single head `2026_06_19_0012`.
- PostgreSQL `upgrade head`, `downgrade 2026_06_19_0011`, re-`upgrade head`, clean `upgrade head`, `current` -> passed as listed above.

Warnings observed:

- Existing async connection cleanup warning in OpenAPI/router-related pytest.
- Existing React Router future-flag warnings in frontend tests.
- Shell startup warning from local RVM `ps` sandbox restriction.

### Review Findings and Repairs

- RED tests first showed Level 3 still returned generic insufficient coverage, allowed no explicit downgrade audit, lacked RuleFamily mixed-level details, and did not represent missing Kaipan in execution coverage. Repaired through the formal level-policy path and new persistence/API/UI fields.
- Initial downgrade fixture also lacked Level 1 OHLCV coverage for the requested range, which correctly blocked downgrade. Repaired the test fixture to isolate Level 3 Kaipan behavior.
- Review found rule minimum-level rejection could also invent a DatasetSnapshot missing reason because dependency checks were skipped after the rule blocker. Repaired so the OHLCV check is marked not checked instead of creating a false missing-data fact.
- Frontend test found Level 3 workbench wording did not include established “Kaipan 数据”; repaired the label.
- Migration final `current` check was first run in parallel with dropping the temporary database, causing an expected missing-database error after successful re-upgrade. Re-ran serial clean upgrade/current and confirmed `2026_06_19_0012 (head)`.

### Risks

Blocking:

- None identified for `RT-S6-004`.

Non-blocking:

- Rule dependencies are interpreted from existing `RuleVersion.data_dependencies`; richer future structured dependency metadata can be added later without changing the RT-S6-004 formal policy.
- Level 3 exact slot is frozen to `09-25` for this task; additional decision policies would require explicit future contract work.
- Legacy result/report pages still exist as compatibility surfaces outside the formal `/rules/backtests` and `/rules/results` product surfaces.

### Acceptance Conclusion

`RT-S6-004 ACCEPTED`.

`RT-S6-003` may begin only after explicit user instruction. `RT-S6-003` has not been started.

Stage 6 is not complete.

## 2026-06-19 RT-S6-003 规则适用性画像

### Task Decision

`ACCEPTED`

### Scope

Implemented the formal RuleApplicabilityProfile draft/version and review foundation only:

- versioned, auditable `RuleApplicabilityProfile` drafts generated from immutable `backtest_runs` and `backtest_results`;
- source binding to BacktestRun IDs, BacktestResult IDs and result fingerprints;
- frozen RuleVersion identity and RuleFamily identity/frozen member IDs when applicable;
- market-state model/source version, DatasetSnapshot fingerprint and MarketSnapshot fingerprint binding;
- requested/effective level, level policy version, Level 3 limitations, warnings and coverage visibility;
- deterministic recommendation states separated from sample count, coverage, confidence and human review;
- insufficient sample behavior that does not become `not_recommended` or zero score;
- reviewed profiles are not overwritten; new evidence creates a new version or superseding draft;
- formal generation/review API under `/api/ui/v1/rules/backtests/*`;
- formal `/rules/results` UI panel for draft generation, sample/coverage/recommendation/review display and approve/reject actions;
- audit rows for draft creation, supersession and review transitions.

Did not start or implement:

- Stage 6 Gate;
- Stage 7 author profile;
- strategy publication;
- daily pre-market or post-market behavior;
- automatic formal rule publication;
- RuleVersion content mutation;
- RuleFamily membership mutation;
- legacy profile migration as formal accepted profiles;
- legacy retirement.

### Delegation

Used three bounded read-only subagents:

- Explorer Alpha: verified Stage 6 docs, RT-S6-001/002/004 acceptance handoffs, RT-S6-003 task card and log conventions.
- Explorer Beta: mapped backend/API/database profile, backtest, rule identity, level-policy, audit/permission and legacy compatibility surfaces.
- Explorer Gamma: mapped frontend formal `/rules/backtests` and `/rules/results` surfaces, existing rule-pool profile UI, client/types/tests and user-facing terminology risks.

Parent implemented all M3 decisions, schema/migration, service/API, UI, tests, migration replay, review and acceptance decision.

### Files Changed

- `src/models/rule_applicability.py`
- `src/models/__init__.py`
- `src/db/repositories/rule_applicability_repository.py`
- `src/services/rule_applicability_service.py`
- `src/services/backtest_application_service.py`
- `src/db/migrations/versions/2026_06_19_0013_stage6_rule_applicability_profiles.py`
- `api/routers/ui/formal_backtests.py`
- `tests/unit/services/test_rule_applicability_service.py`
- `tests/api/routers/test_formal_backtests.py`
- `tests/unit/db/test_migrations.py`
- `tests/api/test_ui_openapi_contract.py`
- `web/src/types/backtests.ts`
- `web/src/lib/api/backtests.ts`
- `web/src/lib/api/backtests.test.ts`
- `web/src/features/backtest/formal-backtest-results.tsx`
- `web/src/features/backtest/backtest-center.stage6.test.tsx`

### Key Design Decisions

- Kept legacy `build_profile()` behavior as compatibility-only; it may still read Job payloads and write sidecar artifacts, but it is not used by the formal Stage 6 API.
- Added formal `generate_formal_draft()` and `review_formal_profile()` methods that consume only immutable BacktestRun/BacktestResult rows.
- Kept recommendation, confidence, sample status and review status as separate fields.
- Used `approved/rejected/invalidated/superseded` for profile review state without changing Stage 4 rule lifecycle.
- Did not mutate RuleVersion content, RuleFamily membership, rule lifecycle or strategy assets.

### Database Migration

- Added one linear Alembic revision: `2026_06_19_0013_stage6_rule_applicability_profiles`.
- Migration additively extends `rule_applicability_profiles` with formal source bindings, frozen identity, level, sample, coverage, recommendation, review, limitation and supersession fields.
- Migration creates `rule_applicability_profile_audits` for review/state transition audit.
- Existing legacy profile rows are preserved; they are not promoted to formal accepted profiles.
- PostgreSQL replay evidence on temporary database `rt_s6_003_migration_0619`:
  - clean `upgrade head` passed;
  - `downgrade 2026_06_19_0012` passed;
  - re-`upgrade head` passed;
  - final `alembic current` reported `2026_06_19_0013 (head)`.
- Temporary database was dropped after verification.

### Compatibility Handling

- RT-S6-001 formal BacktestApplicationService and `/rules/backtests` workbench remain intact.
- RT-S6-002 immutable `backtest_results` and `/rules/results` result view remain intact.
- RT-S6-004 requested/effective level and Level 3 limitation semantics remain intact and are preserved on profiles.
- Legacy Job/file/artifact profile generation remains compatibility-only and is not the formal profile source.
- Legacy rule-pool profile UI remains outside the formal Stage 6 product surface.

### Validation

Run and passed:

- `../.venv/bin/python -m pytest tests/unit/services/test_rule_applicability_service.py -q` -> `7 passed`.
- `../.venv/bin/python -m pytest tests/api/routers/test_formal_backtests.py -q` -> `9 passed`.
- `../.venv/bin/python -m pytest tests/unit/services/test_rule_applicability_service.py tests/api/routers/test_formal_backtests.py tests/unit/db/test_migrations.py -q` -> `25 passed`.
- `../.venv/bin/python -m pytest tests/unit/services/test_backtest_application_service.py tests/unit/services/test_rule_applicability_service.py tests/api/routers/test_formal_backtests.py tests/unit/db/test_migrations.py tests/api/test_ui_openapi_contract.py -q` -> `40 passed`, 1 existing async cleanup warning.
- `pnpm test -- src/lib/api/backtests.test.ts src/features/backtest/backtest-center.stage6.test.tsx` -> `7 passed`.
- `pnpm typecheck` -> passed.
- `../.venv/bin/python -m compileall src/models/rule_applicability.py src/db/repositories/rule_applicability_repository.py src/services/rule_applicability_service.py src/services/backtest_application_service.py api/routers/ui/formal_backtests.py src/db/migrations/versions/2026_06_19_0013_stage6_rule_applicability_profiles.py` -> passed.
- `../.venv/bin/python -m alembic -c src/db/migrations/alembic.ini heads` -> single head `2026_06_19_0013`.
- PostgreSQL `upgrade head`, `downgrade 2026_06_19_0012`, re-`upgrade head`, `current` -> passed as listed above.
- `git diff --check` -> passed.

Warnings observed:

- Existing async connection cleanup warning in OpenAPI/router-related pytest.
- Shell startup warning from local RVM `ps` sandbox restriction.

### Review Findings and Repairs

- RED tests first showed formal profile methods and formal API routes did not exist.
- Repaired by adding canonical draft/review service methods, repository reads from BacktestRun/BacktestResult, API routes and frontend client/types.
- Initial model initialization converted UUID fields to strings, preventing prior reviewed profiles from being found as the same formal identity. Repaired by preserving scalar UUID fields and serializing only JSON fields.
- Frontend typecheck found the Web role model has no `reviewer` role. Repaired UI permission check to use existing operator/admin hierarchy while backend continues to allow reviewer/operator/admin.
- Contract review found legacy Job/file references still exist in compatibility `build_profile()` only; formal generation does not call that path.
- Final review found the legacy `rule_id/profile_version/source_backtest_id` uniqueness constraint would block multiple formal versions for the same immutable run. Repaired by including `profile_version_no` in the uniqueness key.
- Final review found UI/service/router review permissions were inconsistent. Repaired router and tests to use the existing operator/admin hierarchy for the current auth model.
- Final review found downgrade could silently drop formal profile/audit data. Repaired downgrade with an explicit refusal when formal profile audit rows exist.

### Risks

Blocking:

- None identified for `RT-S6-003`.

Non-blocking:

- Legacy rule-pool profile generation remains compatibility-only and can still expose old wording on its legacy surface until future retirement work.
- Formal profile list/detail beyond the generated/reviewed draft response remains minimal; future UX may add a dedicated profile history browser before Stage 7 consumes profiles.
- Existing async cleanup warning remains outside this task.

### Acceptance Conclusion

`RT-S6-003 ACCEPTED`.

Stage 6 Gate may begin only after explicit user instruction. Stage 6 Gate has not been started.

Stage 6 is not complete until Gate acceptance.
