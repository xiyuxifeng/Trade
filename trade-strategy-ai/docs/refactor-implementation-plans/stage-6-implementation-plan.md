# Stage 6 回测与规则适用性实施计划

## 1. Stage Scope and Exclusions

Stage 6 prepares and implements:

```text
Human-reviewed RuleVersion or RuleFamily
→ dependency check
→ canonical BacktestApplicationService
→ immutable DatasetSnapshot
→ immutable required MarketSnapshots
→ point-in-time market-state model/version
→ deterministic backtest engine
→ immutable BacktestRun
→ immutable BacktestResult
→ RuleApplicabilityProfile draft/version
→ human review where required
→ later strategy consumption
```

Bootstrap only freezes contracts and Task Cards. It does not implement production code, create migrations, start `RT-S6-001`, start Stage 7, accept any Stage 6 Task, or mark Stage 6 complete.

Stage 6 excludes author-profile generation, strategy publication, daily trading objects, Prompt changes, and legacy retirement without migration/observation/rollback evidence.

## 2. Entry-Gate Evidence

- Stage 5 Gate is explicitly `ACCEPTED` in the Stage 5 log.
- `RT-S5-001`, `RT-S5-002`, and `RT-S5-003` are accepted in the main log.
- `Stage 6 Bootstrap` is documented as the next action and was explicitly authorized by the user.
- Canonical writer is effective true in normal runtime; guarded emergency rollback branches are not formal Stage 6 paths.
- No accepted formal dual-write path was found.
- `DatasetSnapshot` formal source is `dataset_snapshots`.
- `MarketSnapshot` formal source is `market_snapshots` and child section tables.
- Stage 5 formal mutation remains under `系统管理 -> 数据与调度`, `/api/ui/v1/system/data/*`, `DataSchedulingService`, and `system-data-operation`.
- Raw Stage 5 data Job/Workflow/API/CLI mutation paths remain rejected, read-only, or compatibility-only.
- Truthful `unavailable` / `partial` / `invalid` / `conflict` / `insufficient_coverage` semantics remain required.

Repository baseline at Bootstrap:

- Branch: `main`
- HEAD: `066300e514a38dd283093ea846a4b5adcaf5add7`
- Working tree before Bootstrap edits: clean
- Complete diff before Bootstrap edits: empty

## 3. Current Implementation Audit

Current implementation is migration input, not the target contract.

- `BacktestRequest` is currently `trader_id` / optional `strategy_version_id` based and includes `use_snapshot_only`.
- `BacktestEngine` resolves strategy by `trader_id + trade_date`, not immutable `RuleVersion` or frozen `RuleFamily`.
- `SnapshotLoader` can use `config_path`, file snapshots, file `source_refs`, direct OHLCV DB reads, and EvidencePack compatibility fallback.
- `IndicatorService` can compute and upsert indicators on read, which is invalid during frozen execution.
- Market-state lookup is date/version based but does not yet prove `available_at <= simulated decision time` per simulated date.
- `backtest_result_runs` is a legacy summary/adaptor table; it does not bind every immutable Stage 6 input and allows nullable snapshot/version fields.
- `RuleApplicabilityService` currently derives profiles from Job payloads and artifact files.
- `JobRegistry` exposes runnable backtest job types and `config_path` parameters.
- `/rules/backtests` and `/rules/results` are the current product route group but still delegate to legacy Job/result behavior.
- `/backtest`, `/backtest/regime`, `/jobs`, `/workflows`, and `/artifacts` remain routable compatibility/admin surfaces.

## 4. Existing-Component Disposition Matrix

| Component | Disposition | Reason |
| --- | --- | --- |
| `RuleVersion`, `RuleFamily`, `RuleFamilyMembership` | `REUSE_AS_IS` | Canonical UUID identity, fingerprint, lifecycle, family membership. |
| `RuleGovernanceService` | `REUSE_AS_IS` | Accepted fingerprint/family owner. |
| `RuleLifecycleService` | `REUSE_AS_IS` | Accepted lifecycle transition owner. |
| `DatasetSnapshot` model/repository/service | `REUSE_AS_IS` | Accepted immutable OHLCV snapshot contract. |
| `MarketSnapshot` stored facts/repositories | `REUSE_AS_IS` | Accepted immutable Kaipan snapshot facts. |
| `MarketSnapshotService` | `REFACTOR_AND_REUSE` | Producer can remain; formal Stage 6 read path must not use file/config_path/live Provider. |
| `MarketRegimeRepository` | `REFACTOR_AND_REUSE` | Needs point-in-time availability query. |
| `BacktestEngine` | `REFACTOR_AND_REUSE` | Useful primitives, wrong formal input unit and incomplete sample states. |
| `SnapshotLoader` | `REJECT_FROM_FORMAL_PATH` | Uses config/file/EvidencePack/direct mutable read patterns. |
| `BacktestService` | `REFACTOR_AND_REUSE` | Useful orchestration ideas, not formal service as-is. |
| `backtest_result_runs` | `REFACTOR_AND_REUSE` | Migration input/adaptor, not final immutable run/result fact. |
| `RuleApplicabilityProfile` existing model/repo | `REFACTOR_AND_REUSE` | Needs source-result binding, versioning, review, supersession, level fields. |
| `RuleApplicabilityService` | `REJECT_FROM_FORMAL_PATH` | Current formal source is Job/artifact payload; a future replacement may reuse only reviewed non-formal logic. |
| `IndicatorService` | `REFACTOR_AND_REUSE` | Must split pure read/derivation from mutating compute. |
| `OHLCVService` | `REUSE_AS_IS` | Reused only as accepted ingestion/repair owner; it is not the formal backtest read path. |
| `JobService` / `JobRunner` / `JobRegistry` | `COMPATIBILITY_ONLY` | Not allowed as business entry; internal transport allowed only under application service. |
| Workflow/Pipeline backtest specs | `REJECT_FROM_FORMAL_PATH` | Must not define normal-user contract. |
| `cli/backtest.py` | `COMPATIBILITY_ONLY` | Trader/config/file oriented. |
| `src/rule_pool/*` | `COMPATIBILITY_ONLY` | Legacy source, not formal RuleVersion truth. |
| `src/rule_backtest/scheduler.py` | `RETIRE_LATER` | Duplicate automated entry. |
| `/rules/backtests`, `/rules/results` | `REFACTOR_AND_REUSE` | Correct product group, legacy internals. |
| `/backtest`, `/backtest/regime`, `/jobs`, `/workflows`, `/artifacts` | `COMPATIBILITY_ONLY` | Routable for compatibility/admin, not formal journey. |
| `BusinessPageShell`, `ProductPageAdapter` | `REUSE_AS_IS` | Existing state shells fit Stage 6 UI requirements. |

Unknown, ambiguous, or unverified components do not default to reuse.

## 5. Canonical Data Flow

Formal Stage 6 backtests and applicability results must consume only canonical `DatasetSnapshot`, canonical `MarketSnapshot`, canonical repositories/application services, immutable IDs, fingerprints, versions, provenance, and availability timestamps.

Formal Stage 6 must not consume legacy API, CLI, raw Job, Workflow, Pipeline, compatibility views, file-based snapshots, old market-state artifacts, EvidencePack fallback, `config_path`, live Provider calls, mutable latest records, or old JSON result files.

Missing canonical data remains `unavailable`, `partial`, `conflict`, `invalid`, `insufficient_coverage`, or `insufficient_sample`. It must never become false, zero, empty success, silently skipped success, fabricated coverage, fabricated market state, or fabricated readiness.

Generic Job infrastructure may be reused only under `BacktestApplicationService`; completed Job does not imply valid BacktestRun.

## 6. Frozen Core Contracts

### Selection

Formal selection is `RuleVersion` primary and `RuleFamily` optional. RuleFamily freezes exact member `RuleVersion` IDs at run creation. User also selects date range, target/universe, benchmark, mode, and requested data level. `profile_id` may be configuration context only, not the tested fact source. Old trader/strategy backtests are compatibility-only.

No mutable latest rule, latest strategy, current family membership, current market-state version, or current dataset may be used after run creation.

### BacktestRun

Immutable run contract must include `run_id`, request fingerprint, RuleVersion ID/fingerprint/version, RuleFamily ID and frozen member IDs when applicable, date range, universe, benchmark, mode, requested/effective level, DatasetSnapshot ID/fingerprint, required MarketSnapshot IDs/fingerprints, market-state model/source version, indicator or derivation version, engine/code version, execution policy version, recommendation policy version when relevant, decision-time semantics, status, coverage state, quality state, unavailable reasons, audit fields, and reproducibility fingerprint.

Status must distinguish dependency failure, running, cancelled, failed, completed_invalid, and completed_valid.

### BacktestResult

Immutable result contract must include `result_id`, `run_id`, input fingerprint, result fingerprint, overall metrics, per-rule metrics, per-market-state metrics, per-level metrics, eligible/skipped/unavailable/invalid/conflict samples, unsupported rules, coverage, warnings, limitations, requested/effective level, and reproducibility evidence.

Sample states are separate: eligible sample, evaluated true, evaluated false, condition unavailable, data missing, unsupported, invalid, skipped. Missing/unavailable conditions must not be counted as false.

### RuleApplicabilityProfile

Profile must be versioned and auditable with `profile_id`, `profile_version`, RuleVersion ID, RuleFamily ID and frozen membership when applicable, market-state label, market-state model version, source BacktestRun IDs, source BacktestResult IDs, sample count, eligible sample count, coverage, return, win rate, max drawdown, confidence, recommendation status, data level, requested/effective level, review status, quality status, insufficient-sample status, policy version, audit fields, and supersession/current-version relationship.

BacktestResult must not automatically make a rule formally usable, publish a profile, overwrite a reviewed profile, modify RuleVersion content, modify RuleFamily membership, or bypass human review.

### Recommendation and Sample Policy

Deterministic recommendation states: `recommended`, `limited`, `not_recommended`, `insufficient_sample`, `unavailable`, `conflict`, `invalid`.

Keep separate: sample count, return, win rate, drawdown, confidence, coverage, recommendation, and human review. No strong conclusion may be produced when sample size or coverage is insufficient.

## 7. Point-In-Time Matrix

| Fact | Required proof |
| --- | --- |
| market timezone | `Asia/Shanghai` unless later extended |
| simulated decision time | persisted policy version and timestamp rule |
| observable OHLCV | DatasetSnapshot member and `available_at <= decision_time` |
| observable indicators | immutable snapshot member or deterministic derivation version/fingerprint |
| observable MarketSnapshot slot | canonical snapshot ID/slot/trade_date/source/fingerprint |
| observable market-state record | model/source version and source snapshot relationship |
| observable Kaipan slot | canonical MarketSnapshot slot with captured/available time |
| observable benchmark data | same DatasetSnapshot availability rule |
| valid RuleVersion | fixed ID/fingerprint at run creation |
| entry/exit/holding policy | execution policy version |
| missing price/suspension/limit handling | invalid/unavailable policy, not false/zero |
| adjustment policy | DatasetSnapshot OHLCV manifest |

Invariant:

```text
available_at <= simulated decision time
```

Prevent future OHLCV, indicator, MarketSnapshot, market-state, benchmark leakage; latest-record substitution; post-close data used for pre-market decisions; and data repairs changing old results without new snapshot/run.

## 8. DatasetSnapshot and Indicator Contract

Level 1 OHLCV must bind to canonical DatasetSnapshot. Indicators are either immutable DatasetSnapshot members or deterministic derived data bound to `DatasetSnapshot.content_fingerprint + indicator_version + code_version`.

Formal execution must not compute/upsert indicators. Missing indicators produce `unavailable` or `insufficient_coverage` and a repair path outside the frozen run.

## 9. MarketSnapshot and Market State Contract

Formal Stage 6 binds MarketSnapshot ID, slot, trade_date, source, fingerprint, normalization version, captured_at, available_at, market-state model version, market-state result version, and source snapshot relationship.

User-facing wording is “市场状态”, never `Regime`.

## 10. Level 1 / Level 2 / Level 3 Matrix

| Level | Meaning | Requirements | Missing-data behavior |
| --- | --- | --- | --- |
| Level 1 | OHLCV | canonical DatasetSnapshot, OHLCV/benchmark/indicator coverage | unavailable or insufficient_coverage |
| Level 2 | OHLCV + 市场状态 | Level 1 plus point-in-time market-state data/model version | unavailable, not unknown success |
| Level 3 | OHLCV + 市场状态 + Kaipan | Level 2 plus exact canonical Kaipan/MarketSnapshot slot, normalization, source, availability evidence | limitation, not false/no signal/loss |

Persist requested level, effective level, downgrade/reject policy, minimum coverage, permitted rule types, rule-specific minimum level, RuleFamily mixed-level behavior, UI wording, and persistence fields. No silent downgrade is allowed.

## 11. API/Application-Service Contract

Formal entry:

```text
Web/API
→ BacktestApplicationService
→ canonical dependency check
→ BacktestRun creation
→ internal Job execution if needed
→ canonical result persistence
```

Required API: dependency check, create BacktestRun, run status/progress, result read, reproducibility evidence, applicability draft generation, profile review/publish/invalidate.

Forbidden formal entries: raw Job submission, Workflow execution, CLI execution, legacy `/backtest_results` job fallback, config_path runtime, and file artifact truth.

## 12. Web User Journey

Formal normal-user journey under `规则与回测`:

```text
选择规则或规则族
→ 选择回测区间
→ 选择标的范围
→ 选择基准
→ 选择回测模式和数据等级
→ 自动检查数据依赖
→ 显示可运行 / 可降级 / 需修复 / 不可运行
→ 提交正式回测
→ 查看运行进度
→ 查看整体结果
→ 查看分市场状态结果
→ 查看数据覆盖和限制
→ 查看可复现证据
→ 查看或生成适用性画像草稿
→ 进入必要的人工审核
```

Normal-user UI must show page purpose, input, processing status, output, limitations, and next step. It must not expose Job, Workflow, Pipeline, Artifact, Provider, `config_path`, database table names, internal job type, file paths, Schema names, or regime.

## 13. Permissions and Audit

- view dependency status: viewer.
- submit formal runs: operator.
- cancel/retry: operator with ownership/admin escalation where needed.
- view technical details: admin only.
- generate applicability drafts: operator.
- review/publish/invalidate profiles: reviewer/operator role with admin override policy.

Every mutation records actor, role, time, reason, source surface, run_id, and before/after state where applicable.

## 14. Schema and Migration Plan

Stage 6 implementation is expected to require new or extended canonical Schema. Bootstrap creates no migrations.

Expected implementation decision:

- create immutable `backtest_runs` or equivalent canonical table;
- create immutable `backtest_results` or equivalent canonical table;
- persist per-market-state and per-rule metrics, either normalized or JSON with indexed canonical keys;
- extend or replace `rule_applicability_profiles` for source result IDs, version/review/supersession, requested/effective level, coverage, quality, and policy version;
- keep `backtest_result_runs` as compatibility/adaptor until retirement.

Migration requirements when implementation begins: one linear Alembic branch, metadata registration, safe upgrade, existing-data preservation, safe rerun where applicable, downgrade or documented recovery, and PostgreSQL evidence.

## 15. Compatibility and Retirement Matrix

| Legacy surface | Allowed behavior | Forbidden behavior | Replacement | Retirement condition |
| --- | --- | --- | --- | --- |
| `/backtest` | compatibility notice/read-only or redirect | formal mutation | `/rules/backtests` formal journey | Stage 6 accepted and links observed |
| `/backtest/regime` | compatibility read-only | formal result truth | `/rules/results` formal view | Stage 6 accepted |
| `/api/backtest_results` job fallback | compatibility read only | formal result truth | BacktestRun/Result API | migration/parity evidence |
| `backtest-run` raw Job | internal transport only under service | normal-user entry | BacktestApplicationService | formal API/Web accepted |
| `rule-pool-backtest` | compatibility/admin only | formal applicability write | RuleVersion/RuleFamily run | rule_pool retired |
| Workflow/Pipeline specs | compatibility/admin only | business contract source | formal API/service | Stage 11/12 evidence |
| `cli/backtest.py` | local/admin compatibility | formal business entry | formal API/service | scripted users migrated |
| file snapshots/JSON result files | historical compatibility | formal fact source | canonical DB snapshots/results | consumers migrated |
| EvidencePack fallback | historical compatibility only | filling missing canonical data | unavailable/repair path | parity evidence |

## 16. Reproducibility Contract

Identity must include RuleVersion fingerprint, RuleFamily membership, DatasetSnapshot fingerprint, MarketSnapshot fingerprints, market-state model/source version, indicator version, engine/code version, execution policy, recommendation policy, date range, universe, benchmark, requested/effective level, and decision-time semantics.

Re-running the same fingerprint must produce the same result fingerprint or a truthful conflict/invalid state with evidence.

## 17. Final Task Order and Risk

Stage 6 is M3. Final order:

1. `RT-S6-001 回测工作台` - M3.
2. `RT-S6-002 分市场状态回测` - M3.
3. `RT-S6-004 回测分级` - M3.
4. `RT-S6-003 规则适用性画像` - M3.

Rationale: profiles depend on immutable runs/results, market-state splits, and level semantics. `RT-S6-004` follows `RT-S6-002` because Level 2/3 enforcement needs point-in-time market-state/Kaipan binding. Task Matrix combinations are allowed only as separate sequential acceptance batches, never combined acceptance.

## 18. Task Cards

### RT-S6-001 回测工作台

- Goal: implement formal normal-user backtest workbench foundation.
- Current facts: current UI submits raw `backtest-run`; current request is trader/strategy based; canonical RuleVersion/RuleFamily/DatasetSnapshot/MarketSnapshot exist.
- Reusable disposition: UI shell reuse; `/rules/backtests` refactor; BacktestService refactor; raw Job reject from formal path.
- Frozen contract: RuleVersion primary, RuleFamily optional, dependency check before immutable BacktestRun, mandatory snapshot-only formal path.
- Allowed files: Stage 6 docs/logs, new/refactored backend service/schema/repo/model/API/tests, `/rules/backtests` UI/client/types/tests, migrations only in implementation session.
- Forbidden paths: Stage 7, strategy publication, CLI/Workflow/Pipeline/compat views/file snapshots/EvidencePack/live Provider/config_path, technical user-facing terms.
- Canonical inputs: RuleVersion/RuleFamily, DatasetSnapshot, MarketSnapshot when needed, market-state records, benchmark.
- Immutable bindings: request/rule/family/snapshot/engine/code/policy fingerprints.
- Point-in-time: dependency check proves `available_at <= simulated decision time`; missing proof is unavailable/insufficient_coverage.
- Level behavior: collect requested level, compute runnable/downgradeable/repair-needed/not runnable, no silent downgrade.
- Schema/API/UI/runtime: dependency check, create run, status, result read, user states.
- Permission/audit: viewer checks, operator creates, all mutations audited.
- Compatibility isolation: old `/backtest` and raw Jobs not formal.
- Tests: service dependency check, API permissions, migration if Schema changes, frontend states, no technical terms, raw Job not formal entry.
- Completion: user can check dependencies and create immutable BacktestRun or truthful unavailable state; no formal config/file/EvidencePack/live Provider path.
- Stop/escalation: ambiguous RuleVersion/RuleFamily identity, unsafe Schema, Stage 5 contract change, second writer/source needed.
- Out of scope: full market-state execution and profile publication.
- Handoff: `RT-S6-002` after acceptance only.

### RT-S6-002 分市场状态回测

- Goal: implement point-in-time market-state-aware execution/results.
- Current facts: existing regime metrics are legacy and point-in-time proof is partial.
- Reusable disposition: engine primitives refactor; market-state records refactor; old report UI refactor.
- Frozen contract: select market-state from canonical MarketSnapshot-derived records with availability proof; persist per-market-state immutable metrics.
- Allowed files: service/engine/result schemas, market-state repository query additions, `/rules/results` UI/types, tests/migrations.
- Forbidden paths: file artifacts, EvidencePack, compatibility views, live Provider, old JSON, raw Job source.
- Canonical inputs: BacktestRun, DatasetSnapshot, MarketSnapshot IDs, market-state model/source version.
- Immutable bindings: MarketSnapshot IDs/fingerprints, market-state result version, decision-time policy.
- Point-in-time: `available_at <= decision_time`; missing market-state is unavailable/insufficient_coverage.
- Level behavior: implements Level 2; Level 1 explicitly has no split; Level 3 waits for RT-S6-004.
- Schema/API/UI/runtime: per-market-state metrics and sample status counts; UI coverage/warnings/limitations.
- Permission/audit: same run/result permissions and audit.
- Compatibility isolation: legacy `regime_metrics` read-only compatibility only.
- Tests: future leakage rejection, missing market-state not false, immutable metric persistence, no `Regime` in product UI.
- Completion: formal results show market-state split and reproducibility identity includes market-state source.
- Stop/escalation: no availability proof from Stage 5 facts or Stage 5 MarketSnapshot contract must change.
- Out of scope: profile generation/publish.
- Handoff: `RT-S6-004` after acceptance.

### RT-S6-004 回测分级

- Goal: enforce Level 1/2/3 requirements and downgrade/reject policy.
- Current facts: formal level contract is not implemented; missing Kaipan must remain limitation.
- Reusable disposition: DatasetSnapshot/MarketSnapshot reuse; RT-S6-001 dependency check refactor; RT-S6-002 market-state result reuse after acceptance.
- Frozen contract: Level 1 OHLCV; Level 2 OHLCV + 市场状态; Level 3 OHLCV + 市场状态 + Kaipan; requested/effective level persisted; no silent downgrade.
- Allowed files: level policy module, schema/model/migration for level fields, API/UI/tests.
- Forbidden paths: silent downgrade; missing Kaipan as false/no signal/loss/success; live Provider/config_path fill.
- Canonical inputs: DatasetSnapshot, MarketSnapshot slot/fingerprint, market-state version, RuleVersion dependencies.
- Immutable bindings: requested/effective level, level policy version, coverage state.
- Point-in-time: Level 3 Kaipan slot observable before decision time; pre/post slots cannot be swapped.
- Schema/API/UI/runtime: persist level fields; dependency check returns runnable/downgradeable/repair-needed/not runnable.
- Permission/audit: explicit downgrade acceptance records actor/reason.
- Compatibility isolation: old results without level fields are not formal evidence.
- Tests: Level 1 success, Level 2 missing market-state rejection, Level 3 missing Kaipan rejection/explicit downgrade, missing Kaipan not false, RuleFamily mixed-level behavior.
- Completion: all formal runs persist levels and communicate data limits.
- Stop/escalation: rule dependencies cannot determine minimum level; Kaipan limitation cannot be represented truthfully.
- Out of scope: profile publish, daily selection.
- Handoff: `RT-S6-003` after acceptance.

### RT-S6-003 规则适用性画像

- Goal: generate versioned, auditable applicability profile drafts from immutable BacktestRun/BacktestResult.
- Current facts: existing service reads Job payloads/files and can auto-classify profiles.
- Reusable disposition: existing profile model/repo refactor; scoring ideas refactor; Job/file loader reject.
- Frozen contract: immutable BacktestRun/Result source only; output draft/versioned profile; reviewed profiles never overwritten; human review boundary explicit.
- Allowed files: profile service, model/repo migration, review API/UI, tests.
- Forbidden paths: Job payload/file artifact source, RuleVersion content mutation, RuleFamily membership mutation, bypass insufficient_sample, auto-publish.
- Canonical inputs: BacktestRun IDs, BacktestResult IDs, frozen RuleVersion/RuleFamily IDs, market-state version, requested/effective level.
- Immutable bindings: result fingerprints, policy version, review status, supersession chain.
- Point-in-time: inherited from BacktestResult; profile cannot strengthen beyond source coverage.
- Level behavior: records data level and requested/effective level; Level 3 limitations remain visible.
- Schema/API/UI/runtime: generate draft, list/detail profiles, review/publish/invalidate, show sample/coverage/confidence/recommendation/limitations/review.
- Permission/audit: operator drafts; reviewer/operator approves/rejects/invalidates; all review writes audited.
- Compatibility isolation: existing legacy profiles read-only until migrated and not formal accepted profiles.
- Tests: immutable source only, insufficient sample, no overwrite of reviewed profile, draft/supersession on new run, human review required, no RuleVersion/RuleFamily mutation.
- Completion: user can generate/review traceable draft; recommendation/sample/review separated.
- Stop/escalation: unsafe profile migration/preservation; requires Stage 7 redesign.
- Out of scope: author profile update and strategy publication.
- Handoff: Stage 6 Gate only after all four Tasks accepted.

## 19. Stage Gate Evidence Matrix

Stage 6 Gate must verify accepted Tasks, canonical data-only formal runs, no formal raw Job/dual source, mandatory snapshot-only formal path, point-in-time tests, non-mutating indicator behavior, Level 1/2/3 persistence, missing Kaipan limitation, profile no-overwrite/human review, business Chinese UI, PostgreSQL migration evidence, and compatibility-only legacy surfaces.

## 20. Risks

Blocking: none identified during Bootstrap.

Non-blocking:

- Legacy internal tooling retirement remains deferred.
- Emergency canonical-writer-disabled code paths remain present but are not active formal runtime.
- Readiness coverage persistence may be shallow for historical Stage 6 audit queries.
- Historical Kaipan availability depends on provider credentials/network/upstream availability.
- Current backtest implementation is legacy-heavy and must not be preserved as formal architecture.

External evidence limitations:

- Bootstrap did not run full test suites.
- Bootstrap did not run PostgreSQL migration replay.
- Provider-backed Kaipan evidence cannot be proven without credentials/network.

## 21. First Executable Task

Next executable Task:

```text
RT-S6-001 回测工作台
```

Recommended Parent model: `gpt-5.5`.

`RT-S6-001` may share a Parent session with `RT-S6-002` only as separate sequential acceptance batches. It has not been started.
