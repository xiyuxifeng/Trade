# Stage 8 策略中心实施计划

## Bootstrap Decision

`READY`

本计划只冻结 `Stage 8 策略中心` 的实施契约、任务顺序和 Task Cards。不得在 Bootstrap 中实现生产代码、发布策略、生成每日盘前计划或启动盘后行为。

## Entry Verification

- Stage 7 Gate：已在 `docs/refactor-implementation-logs/stage-7.md` 和 `docs/Refactor-Implementation-Log.md` 明确记录为 `ACCEPTED` / `[x] 已完成`。
- Stage 8 进入前状态：未发现既有 `stage-8-implementation-plan.md`；主日志记录 Stage 8 仅可在用户明确授权后开始。
- 分支：`main`。
- Baseline HEAD：`f53027faf5d16dbed1735d0fc4aafd6edc17687d`。
- Bootstrap 前 working tree：clean。
- Bootstrap 前完整 diff：empty。
- 用户本次授权范围：仅准备 Stage 8 plan/log/Task Cards，不实现生产代码。

## Delegation

使用 `refactor-orchestrator` 后，Parent 明确决定委派两个 bounded read-only `refactor_explorer_mini`：

- Backend/data Explorer：映射 canonical strategy/domain/database/service/test 事实源和 legacy strategy hazards。
- Frontend/API Explorer：映射 `/strategies`、strategy UI/API/client/test 事实和用户可见 legacy/developer wording。

未使用 Executor。原因：本次 Bootstrap 禁止生产实现，且 source-of-truth、生命周期、发布、回滚和 proposal 边界必须由 Parent 冻结。

Runtime probe verified:

- `.codex/skills/refactor-orchestrator/SKILL.md` exists.
- `.codex/agents/refactor-explorer-mini.toml` exists and declares `gpt-5.4-mini`, `read-only`.
- `.codex/agents/refactor-executor-mini.toml` exists and declares `gpt-5.4-mini`, `workspace-write`.
- Native subagent spawning worked in this session.
- Effective child model and effective read-only permissions are not independently verified beyond configured role and successful read-only handoff.

## Current Facts

### Formal Strategy Schema Already Exists

- `src/models/stage2_canonical.py` defines canonical `Strategy`, `StrategyVersion`, `StrategyRuleMembership`, `DailyRuleSelection`, `DailyStrategyInstance`, `TradingDayPlan`, `PostMarketReview`, and `OptimizationProposal`.
- `strategies` has `business_key` and `current_published_version_id`.
- `strategy_versions` has `strategy_id`, `version_no`, `schema_version`, `lifecycle_state`, `parent_version_id`, `risk_policy_json`, `selection_policy_json`, `universe_json`, author profile version FKs, `evidence_json`, `quality_status`, `published_at`, and actor fields.
- `strategy_rule_memberships` links formal `StrategyVersion` to formal `RuleVersion` with `base_weight`, `status`, and per-rule configuration.
- `optimization_proposals` already supports `ProposalType.strategy_revision`; there is no dedicated `StrategyRevisionProposal` table/service yet.

### Formal Fact Sources From Stage 6/7

Stage 8 formal strategy generation and validation may consume only these canonical facts through canonical repositories/services:

- `DatasetSnapshot`
- `MarketSnapshot`
- `BacktestRun`
- `BacktestResult`
- `RuleApplicabilityProfile`
- `RuleVersion`
- `RuleFamily`
- `AuthorProfileVersion` with `profile_kind = method`
- `AuthorProfileVersion` with `profile_kind = rule`
- `AuthorProfileVersion` with `profile_kind = validated`

Stage 8 must preserve immutable IDs, fingerprints, versions, provenance, availability timestamps, quality state, and sample-coverage state in strategy evidence.

### Existing Gaps

- `CanonicalStrategyVersionRepository` exists only as protocol-level intent; no concrete canonical strategy repository/service is implemented.
- `src/db/repositories/strategy_repo.py` is empty.
- No formal Stage 8 service/API/UI exists for draft, validation, publish, current-use, rollback, diff, or proposal review.
- Formal backtests are currently rule/rule-family centric. Stage 8 validation must record strategy-level validation evidence in `StrategyVersion.evidence_json` or a bounded Stage 8 validation relation without making legacy `backtest_result_runs.strategy_version_id` formal.
- `strategies.current_published_version_id` is not enforced as an FK in current ORM.
- `/strategies` exists but currently shows a compatibility shell over candidate data and states formal strategy versions are not established.

### Legacy / Compatibility Strategy Paths

The following are compatibility-only or rejected from formal Stage 8 inputs:

- `TraderStrategyVersion` and `trader_strategy_versions`.
- `src/strategy_library/*`.
- `src/services/strategy_service.py`.
- `src/pipeline/tasks/strategy_version_tasks.py`.
- `job_registry` `strategy-build` and related Job/Workflow/Pipeline paths.
- `/api/ui/v1/strategy-studio`.
- `/api/ui/v1/optimize` while it reads/writes `TraderStrategyVersion`.
- `/strategy_versions`.
- legacy `BacktestService`, `SnapshotLoader`, `config_path`, file JSON downloads, old market-state artifacts, live Provider calls, mutable latest records.
- `backtest_result_runs.strategy_version_id` and `legacy_strategy_version_id`.
- compatibility views such as `strategy_regime_selections` and `regime_rule_selections`.

Existing compatibility routes may remain readable during Stage 8, but they must not be formal strategy facts, formal inputs, or formal write paths.

## Frozen Contracts

### Source Of Truth

- Formal strategy object: canonical `StrategyVersion` in `strategy_versions`.
- Strategy aggregate/current pointer: canonical `Strategy` in `strategies`.
- Rule pool membership: canonical `StrategyRuleMembership`.
- Proposal carrier for Stage 8: canonical `OptimizationProposal` rows where `proposal_type = strategy_revision`; the user-facing/domain name is `StrategyRevisionProposal`.
- `TraderStrategyVersion` is legacy compatibility only and cannot become formal Stage 8 source-of-truth.

### StrategyVersion Contents

Every formal `StrategyVersion` must carry or reference:

- Rule pool: `StrategyRuleMembership.rule_version_id`.
- Rule base weights: `StrategyRuleMembership.base_weight`.
- Rule configuration/status: `StrategyRuleMembership.configuration_json` and `status`.
- Author profile versions: method/rule/validated `AuthorProfileVersion` IDs.
- Risk policy: `risk_policy_json`.
- Position constraints: inside `risk_policy_json` or a clearly named strategy policy block.
- Target universe: `universe_json`.
- Market-state selection policy: `selection_policy_json`.
- Degradation policy: `selection_policy_json` or `risk_policy_json` with explicit unavailable/partial/conflict/invalid/insufficient_coverage behavior.
- Evidence: `evidence_json` with IDs/fingerprints/versions for rule applicability, backtests, datasets, market snapshots, author profiles, reviewer decisions, validation summaries, sample coverage, and data quality.

### Lifecycle

TaskList target lifecycle:

```text
draft -> pending_validation -> backtested -> pending_review -> published -> current -> archived
```

Current enum only has:

```text
draft / pending_review / approved / published / archived / rejected / superseded
```

Frozen Stage 8 implementation may use either of these two acceptable shapes:

1. Add explicit strategy lifecycle states needed by TaskList (`pending_validation`, `backtested`, `current`) through a safe migration, or
2. Keep `FormalLifecycleState` unchanged and encode validation/current substate in explicit StrategyVersion fields/evidence only if the UI/API still presents the TaskList lifecycle clearly and tests prove transitions.

Escalate before implementation if neither shape can satisfy lifecycle clarity without creating a second formal strategy state machine.

Required transition semantics:

- `draft`: editable draft; no current-use effect.
- `pending_validation`: draft locked for validation or validation requested.
- `backtested`: required validation evidence is attached and passes minimum gates or clearly reports insufficiency.
- `pending_review`: reviewer decision required.
- `published`: approved immutable version available for current-use transition.
- `current`: the single active strategy for a strategy scope. This may be represented by `strategies.current_published_version_id`, not necessarily by a separate row state.
- `archived`: retained history, not current, not mutable.

No transition may silently mutate a published/current version.

### Validation Requirements

Before publication/current-use, validation must include:

- Backtest evidence using canonical `BacktestRun` and `BacktestResult`.
- Out-of-sample validation or explicit unavailable/insufficient_coverage state.
- Comparison with current strategy when one exists.
- Rule applicability coverage using formal `RuleApplicabilityProfile`.
- Dataset and market-state bindings using canonical `DatasetSnapshot` and `MarketSnapshot`.
- Data quality and sample coverage, including `insufficient_sample` when applicable.
- Reviewer decision with actor, role, reason, timestamp, and before/after state.

Missing formal data must remain `unavailable`, `partial`, `conflict`, `invalid`, or `insufficient_coverage`. Legacy/live data cannot fill missing canonical coverage.

### Publication And Current Use

- Only one current strategy per strategy scope is allowed unless a later explicit frozen contract introduces a different scope rule.
- `strategies.business_key` defines the strategy scope unless implementation freezes a stricter scoped key.
- Publishing a version and marking it current are audited transitions.
- Marking a new current version must preserve the previous current version and record the transition.
- Published/current versions are immutable except for audit and supersession/current-pointer metadata explicitly controlled by the canonical strategy service.

### Rollback

- Rollback means creating an audited version transition that points current-use back to a prior published version or creates an explicit rollback version derived from prior evidence.
- Rollback must not overwrite or delete history.
- Rollback must record actor, reason, from-version, to-version, affected scope, and validation/waiver evidence.

### Proposal Boundary

- `StrategyRevisionProposal` is proposal-only.
- Stage 8 maps it to `OptimizationProposal(proposal_type = strategy_revision)` unless implementation proves a dedicated table is required and escalates before schema changes.
- Proposal acceptance may create a new draft strategy version and fill `accepted_draft_version_id`.
- A proposal cannot directly modify `StrategyVersion`, `Strategy`, published/current pointers, rule versions, author profiles, or daily runtime objects.
- Post-market and cumulative statistics may create StrategyRevisionProposal only; Stage 8 must not implement Stage 10 post-market behavior.

### Daily Runtime Boundary

- `DailyStrategyInstance` is a runtime object, not a formal strategy.
- Stage 8 may preserve schema references and display boundaries, but must not implement Stage 9 daily pre-market generation or Stage 10 post-market generation.
- Formal `StrategyVersion` is not regenerated daily.

## Allowed Paths

Stage 8 implementation tasks may touch only paths directly needed for the Task Card:

- `src/models/stage2_canonical.py`
- `src/domain/enums.py`
- `src/domain/contracts.py`
- `src/domain/references.py`
- `src/domain/stage2_repositories.py`
- `src/db/repositories/strategy_repo.py` or a clearly named canonical strategy repository.
- `src/services/*strategy*` only for canonical Stage 8 services; legacy services must remain compatibility-only.
- `src/db/migrations/versions/*stage8*`
- `api/routers/ui/*strategy*` or a new formal strategy-center router.
- `web/src/pages/strategies/*`
- `web/src/lib/api/*strategy*`
- `web/src/types/*strategy*`
- focused tests under `tests/` and `web/src/**.test.*`
- docs updates under `docs/Refactor-Implementation-Log.md` and `docs/refactor-implementation-logs/stage-8.md`

## Forbidden Paths And Behaviors

- Do not implement Stage 9 daily pre-market selection/plan generation.
- Do not implement Stage 10 post-market review/attribution generation.
- Do not publish any strategy in Bootstrap or tests using production data.
- Do not use legacy/live data to fill missing canonical data.
- Do not make Job, Workflow, Pipeline, Artifact, Provider, CLI, file path, `config_path`, raw table names, or `Regime` visible in formal strategy UI.
- Do not create a second formal strategy source-of-truth.
- Do not let proposals or daily runtime objects overwrite published/current strategy versions.
- Do not use `TraderStrategyVersion`, strategy jobs, file JSON, compatibility views, or mutable latest records as formal inputs.

## Task Order

1. `RT-S8-001 策略草稿与发布`
2. `RT-S8-002 策略验证和回滚`
3. `RT-S8-003 策略优化建议`

`RT-S8-001` and `RT-S8-002` may be implemented in the same Stage 8 Task Session only if the frozen contracts remain stable and work is done serially. `RT-S8-003` must be implemented separately. Stage 8 must not combine with Stage 9 or Stage 10.

## Task Cards

### RT-S8-001 策略草稿与发布

- Risk: `M3`.
- Target: create the formal strategy draft/review/publish foundation using canonical `Strategy`, `StrategyVersion`, and `StrategyRuleMembership`.
- Current facts: canonical schema exists; concrete canonical strategy repository/service/API/UI does not; `/strategies` currently renders candidate compatibility data; legacy `TraderStrategyVersion` write path is rejected under canonical writer routing.
- Frozen contracts: formal source is canonical `strategy_versions`; no daily regeneration; lifecycle and publication semantics above; only one current strategy per scope after publication/current transition.
- Allowed paths: canonical strategy repo/service, formal UI router, `/strategies` page/API/types/tests, focused migration if needed, Stage 8 logs.
- Forbidden paths: legacy strategy-build jobs, `TraderStrategyVersion` as formal input, `/api/ui/v1/strategy-studio` as formal write path, Stage 9/10 daily pages, production strategy publication.
- Expected user-visible result: user can see a strategy center that explains strategy composition, create/save a draft from approved canonical rules/profiles/policies, submit for review, publish through a reviewed action, and see current strategy status without developer terminology.
- Backend/API scope: repository/service methods for create draft, list/get, submit review, publish, set current if included in publish contract, diff metadata, validation-state surface; enforce canonical write scope.
- Frontend scope: replace compatibility shell on `/strategies` with formal strategy center states: loading, empty, error, partial, permission denied, unavailable, draft, pending validation/review, published/current, archived.
- Database scope: use existing canonical tables where possible; add only bounded fields/indexes/audit table needed for lifecycle/current/publish safety.
- Focused tests: canonical repository/service unit tests, API route tests, migration upgrade/rerun/rollback tests when migration changes, frontend `/strategies` tests, route/navigation wording tests, writer routing tests.
- Special verification: prove no formal path calls legacy strategy jobs, `TraderStrategyVersion`, live Providers, file JSON, or mutable latest records.
- Escalation triggers: lifecycle states cannot be represented; current-use ownership unclear; migration needs destructive rewrite; a second formal strategy fact source appears; publish could mutate existing published/current rows.
- Acceptance criteria:
  - Formal draft creation uses only canonical RuleVersion, RuleApplicabilityProfile, AuthorProfileVersion, DatasetSnapshot/MarketSnapshot evidence.
  - Strategy contents include rule pool, weights, author profile versions, risk policy, position constraints, target universe, market-state selection policy, degradation policy.
  - Published/current strategy is traceable and audited.
  - UI does not expose forbidden developer terminology in the formal strategy flow.
  - Implementation log updated with tests and residual risks.

### RT-S8-002 策略验证和回滚

- Risk: `M3`.
- Target: add validation evidence, current-vs-candidate comparison, version diff, and audited rollback without mutating history.
- Current facts: formal BacktestRun/BacktestResult and RuleApplicabilityProfile exist; backtests are rule/rule-family centric; no formal strategy validation service exists.
- Frozen contracts: validation must bind canonical datasets, market snapshots, backtest runs/results, applicability profiles, author profile versions, quality/sample coverage, and reviewer decision.
- Allowed paths: canonical strategy validation service/repository/API/UI/tests, bounded schema additions for validation evidence if required.
- Forbidden paths: legacy `BacktestService`, `backtest_result_runs` as formal evidence, strategy jobs, live Providers, Stage 9/10 runtime generation.
- Expected user-visible result: user can verify a strategy, see full-cycle and market-state evidence, compare it with the current strategy, review differences, publish only after requirements pass or are explicitly insufficient/unavailable, and rollback through an audited action.
- Backend/API scope: validation request/status/read models, comparison endpoint/service, rollback endpoint/service, audit and transition guards.
- Frontend scope: validation panel, evidence comparison, current strategy diff, rollback confirmation with reason, unavailable/insufficient coverage handling.
- Database scope: prefer `StrategyVersion.evidence_json` for validation summaries; add normalized validation/audit relation only if necessary and before implementation freeze.
- Focused tests: service validation state machine tests, rollback audit tests, API permission/error tests, frontend validation/rollback tests, migration tests if schema changes.
- Special verification: validation run cannot call live Provider or legacy backtest; missing canonical data is not converted to success/zero/false.
- Escalation triggers: direct strategy-level formal backtest linkage requires public BacktestRun schema change; rollback needs to mutate history; current pointer cannot be made single-scope safe; validation evidence cannot distinguish insufficient sample.
- Acceptance criteria:
  - Backtest, out-of-sample validation, comparison, evidence, sample coverage, data quality, and reviewer decision are all visible and traceable.
  - Rollback creates/audits a transition and leaves all historical versions intact.
  - Only one current strategy per scope remains true.
  - UI/API errors explain what happened, impact, and remediation.

### RT-S8-003 策略优化建议

- Risk: `M2/M3` depending on whether schema changes are needed.
- Target: implement proposal-only StrategyRevisionProposal handling without changing published/current strategies directly.
- Current facts: generic `OptimizationProposal` exists with `proposal_type = strategy_revision`; prompt output schema and registry include `strategy_revision_proposal_v1`; no dedicated proposal service/API/UI exists.
- Frozen contracts: StrategyRevisionProposal maps to `OptimizationProposal` unless escalated; acceptance can create a draft only; proposal cannot mutate formal strategy/current pointers.
- Allowed paths: proposal service/repository/API/UI/tests, prompt-registry tests only if Stage 8 wires existing prompt output to proposals, Stage 8 logs.
- Forbidden paths: direct mutation of `StrategyVersion`, direct publication/current changes, Stage 10 post-market behavior, daily runtime generation, legacy optimize candidate write paths as formal proposal input.
- Expected user-visible result: user can see strategy revision suggestions, evidence, confidence, affected strategy version, proposed changes, and choose reject/archive/accept-to-draft without publishing.
- Backend/API scope: create/list/get/review proposal, accept-to-draft, evidence validation, lifecycle audit.
- Frontend scope: proposal list/detail on strategy center with clear “生成草稿” boundary, not “发布策略”.
- Database scope: use `OptimizationProposal`; add only bounded indexes/fields if proposal traceability cannot be met.
- Focused tests: proposal service lifecycle tests, proposal acceptance creates draft and does not publish/current, API tests, frontend proposal boundary tests, prompt output validation tests if touched.
- Special verification: proposals from post-market/cumulative facts remain proposals only and do not require Stage 10 generation.
- Escalation triggers: generic `OptimizationProposal` cannot safely represent StrategyRevisionProposal; proposal acceptance could overwrite current/published strategy; Stage 10 behavior becomes required.
- Acceptance criteria:
  - StrategyRevisionProposal cannot directly modify published/current `StrategyVersion`.
  - Accepted proposal creates or links to a draft version and records `accepted_draft_version_id`.
  - Rejected/archived/superseded proposals remain traceable.
  - UI copy clearly separates suggestion, draft, review, publish, and current-use actions.

## Gates / Validation Plan

Per Task:

- Run focused backend unit/API tests for changed services/routes.
- Run focused migration upgrade/rerun/rollback tests for any schema change.
- Run focused frontend component/API client/route tests.
- Run `git diff --check`.
- Run `pnpm typecheck` when frontend types change.
- Run OpenAPI/UI contract tests when API routes change.
- Update `docs/refactor-implementation-logs/stage-8.md` after each Task.
- Update `docs/Refactor-Implementation-Log.md` current state and Task index after each accepted Task.

Stage 8 Gate must verify:

- Formal strategy is not rebuilt daily.
- User can understand rule pool, profile versions, risk settings, validation evidence, publish, current, archive, rollback, and proposals.
- No formal input comes from legacy Job/Workflow/Pipeline/Artifact/file JSON/`config_path`/live Provider/mutable latest records.
- StrategyVersion, DailyStrategyInstance, and StrategyRevisionProposal are separated.
- Proposal and runtime objects cannot overwrite published/current strategy.
- One current strategy per strategy scope.
- Stage 9 and Stage 10 behavior remains unstarted.

## Risks / Blockers

Blocking risks at Bootstrap: none.

Non-blocking implementation risks:

- Current canonical lifecycle enum may need explicit strategy states or clear substate mapping.
- `strategies.current_published_version_id` lacks an explicit FK and may need hardening.
- Formal backtest run/result schema is rule-centric; strategy-level validation evidence must be designed without reusing legacy `backtest_result_runs`.
- Existing `/strategies` UI contains candidate compatibility behavior and links toward daily pages; it must be re-centered on formal strategy before acceptance.
- Existing strategy UI/API still exposes Job/Artifact/raw regime keys in daily/candidate surfaces; Stage 8 formal pages must not inherit that wording.
- Legacy `/api/ui/v1/optimize` and `/api/ui/v1/strategy-studio` overlap and must remain compatibility-only until retirement evidence.

## Next Executable Task

Next executable Task: `RT-S8-001 策略草稿与发布`.

Recommended model/session: Parent `gpt-5.4` Task Implementation with this plan as the frozen contract, 0-1 bounded Executor only after repository/service/API/UI scope is narrowed. Escalate back to `gpt-5.5` if lifecycle, migration, current-use ownership, rollback, proposal boundary, or canonical data path needs contract changes.
