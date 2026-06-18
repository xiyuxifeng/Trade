# Stage 6 回测与规则适用性实施日志

## 当前状态

- Stage：`Stage 6 回测与规则适用性`
- 当前活动：`2026-06-18 RT-S6-001 回测工作台`
- 当前状态：`RT-S6-001 ACCEPTED`
- 当前已接受：`RT-S6-001`
- 下一可执行 Task：`RT-S6-002 分市场状态回测`
- 不得自动开始：`RT-S6-002` 需用户明确触发

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
