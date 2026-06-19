# Stage 7 作者画像实施计划

## 1. Stage Scope and Exclusions

Stage 7 freezes and implements the formal author-profile foundation:

```text
Article / ArticleRevision / ArticleStructure evidence
-> reviewed RuleVersion / RuleFamily evidence
-> formal RuleApplicabilityProfile evidence
-> AuthorMethodProfile
-> AuthorRuleProfile
-> AuthorValidatedProfile
-> versioned / reviewed / archived author profile states
```

Bootstrap only freezes contracts and Task Cards. It does not implement production code, create migrations, modify Prompt files, start `RT-S7-001`, start Stage 8, publish strategies, generate daily trading decisions, or mark any Stage 7 Task accepted.

Author profiles are research summaries and method-evidence profiles only. They must never be described as the author's real trading performance.

## 2. Entry-Gate Evidence

- Stage 0 is accepted.
- Stage 1 is accepted.
- Stage 2 is accepted.
- Stage 3 is accepted.
- Stage 4 is accepted.
- Stage 5 Gate is accepted.
- Stage 6 Gate is accepted.
- Stage 7 had not started before this Bootstrap.
- Stage 8 has not started.
- Stage 0-6 Cross-Stage Alignment Review conclusion is inherited: Stage 0-6 are `READY_WITH_CONSTRAINTS` for Stage 7 Bootstrap, with no blocker before Stage 7.

Repository baseline at Bootstrap:

- Branch: `main`
- HEAD: `634d5be0f55abb3376683f95b46136184f372d50`
- Working tree before Bootstrap edits: clean
- User-owned changes before Bootstrap edits: none found
- Complete diff before Bootstrap edits: empty

## 3. Current Implementation Audit

Current implementation is mixed between canonical storage, accepted Stage 6 formal evidence, and legacy compatibility surfaces.

- Canonical storage exists for `AuthorProfileVersion` in `stage2_canonical.py`, with `profile_kind`, `version_no`, lifecycle, source IDs, prompt run, evidence and time segment fields.
- Canonical `AuthorProfileKind` has `method`, `rule`, and `validated`.
- Formal Stage 6 source exists: `BacktestApplicationService -> BacktestRun / BacktestResult -> RuleApplicabilityProfile`.
- Formal `RuleApplicabilityProfile` persists source run/result IDs, result fingerprints, RuleVersion/RuleFamily identity, DatasetSnapshot/MarketSnapshot fingerprints, requested/effective level, sample/coverage/confidence/recommendation, review status and audit.
- Existing `/authors` is the formal product route name, but currently renders a transitional page that falls back to legacy persona behavior rules.
- Existing `/persona`, persona services, behavior rules, config/profile pages, legacy rule-pool profile UI, legacy backtest results and file/job-backed profile generation are compatibility or migration inputs only.
- No dedicated Stage 7 author-profile runtime service/API/UI has been accepted yet.

## 4. Existing-Component Disposition Matrix

| Component | Disposition | Reason |
| --- | --- | --- |
| `Authors`, `ArticleRevision`, `ArticleStructure` | `REUSE_AS_IS` | Canonical article/source evidence and revision-bound structure. |
| `PromptRun` | `REUSE_AS_IS` | Canonical prompt/schema/version provenance. |
| `RuleCandidate` | `REFACTOR_AND_REUSE` | May be used only for provenance where RuleVersion source links still need candidate evidence. |
| `RuleVersion`, `RuleVersionSourceLink` | `REUSE_AS_IS` | Reviewed rule source and evidence link. |
| `RuleFamily`, `RuleFamilyMembership` | `REUSE_AS_IS` | Canonical duplicate/family evidence and frozen memberships. |
| `BacktestRun`, `BacktestResult` | `REUSE_AS_IS` | Accepted immutable Stage 6 validation source. |
| Formal `RuleApplicabilityProfile` generated from immutable runs/results | `REUSE_AS_IS` | Accepted Stage 6 source for validated author profiles. |
| `RuleApplicabilityService.generate_formal_draft()` / `review_formal_profile()` | `REFACTOR_AND_REUSE` | Formal Stage 6 source path can be consumed; Stage 7 must not call legacy methods. |
| `AuthorProfileVersion` | `REFACTOR_AND_REUSE` | Canonical storage exists but Stage 7 must verify fields, constraints, lifecycle, audit and time segmentation before runtime use. |
| Prompt registry and author-profile prompt assets | `REFACTOR_AND_REUSE` | Versioned assets exist; Stage 7 must bind runtime, schema validation and regression before use. |
| `/authors` route and page shell | `REFACTOR_AND_REUSE` | Correct formal surface name, currently backed by persona fallback. |
| `BusinessPageShell`, `ProductPageAdapter` | `REUSE_AS_IS` | Fits normal-user loading/empty/error/partial/unavailable states. |
| `/persona` route, persona UI and persona service | `COMPATIBILITY_ONLY` | Legacy behavior/profile tooling; not a formal author-profile source. |
| `/profiles` route and `ConfigProfileService` | `COMPATIBILITY_ONLY` | Runtime configuration profile, not author profile. |
| Legacy `RuleApplicabilityService.build_profile()` / `review_profile()` | `REJECT_FROM_FORMAL_PATH` | Job/file-backed and mutable legacy profile behavior. |
| Legacy rule-pool profile UI/API | `REJECT_FROM_FORMAL_PATH` | Legacy rule-pool profile output cannot become Stage 7 evidence. |
| `backtest_result_runs`, `regime_metrics` | `REJECT_FROM_FORMAL_PATH` | Legacy summary/adaptor data, not final formal truth. |
| Job / Workflow / Pipeline / Artifact / file JSON / SnapshotLoader / `config_path` / EvidencePack / live Provider paths | `REJECT_FROM_FORMAL_PATH` | Explicitly forbidden formal sources. |
| Legacy persona/profile pages and file artifacts | `RETIRE_LATER` | Retire only after Stage 7 replacement, migration report, compatibility observation and rollback evidence. |

Unknown, ambiguous, or unverified components do not default to reuse.

## 5. Canonical Stage 7 Sources

Formal Stage 7 sources may include only canonical facts:

- `Article`
- `ArticleRevision`
- `ArticleStructure`
- `RuleCandidate` only where still needed for provenance
- reviewed `RuleVersion`
- `RuleFamily`
- formal `BacktestRun`
- formal `BacktestResult`
- formal `RuleApplicabilityProfile`
- `DatasetSnapshot` / `MarketSnapshot` fingerprints inherited from Stage 6
- prompt version / schema version / source evidence

Formal Stage 7 must not use:

- legacy `/persona` page
- legacy persona/profile services
- legacy rule-pool profile UI
- legacy `RuleApplicabilityService.build_profile()` output
- Job payloads
- Workflow results
- Pipeline artifacts
- file artifacts
- old JSON result files
- `SnapshotLoader`
- `config_path`
- EvidencePack
- live Provider
- mutable latest records
- `backtest_result_runs` as final formal truth
- `regime_metrics` as final formal truth

## 6. Frozen Profile Separation Contract

### AuthorMethodProfile

Source:

- `ArticleStructure`
- article evidence
- author-declared methods
- LLM extraction with prompt/schema version

Must include:

- trading style
- analysis framework
- stock selection preferences
- entry/exit preferences
- risk expression
- holding-period preference
- data dependencies
- market-state assumptions
- evidence
- confidence
- limitations

Must not include:

- backtest-derived recommendation as author fact
- strategy publication
- real trading performance claim

### AuthorRuleProfile

Source:

- reviewed `RuleVersion`
- `RuleFamily`
- rule governance evidence
- rule dependencies
- duplicate/conflict evidence

Must include:

- rule type distribution
- rule families
- quantifiability
- data dependencies
- repeat/conflict summary
- representative rules
- evidence
- limitations

Must not mutate:

- `RuleVersion`
- `RuleFamily` membership
- rule lifecycle

### AuthorValidatedProfile

Source:

- formal `RuleApplicabilityProfile`
- formal `BacktestRun`
- formal `BacktestResult`
- Stage 6 level / market-state / sample evidence

Must include:

- strong rule types
- weak rule types
- strong market states
- weak market states
- common failure modes
- data coverage
- sample count
- confidence
- limitations

Must not:

- overstate insufficient sample
- treat missing Kaipan as failure
- convert low confidence into hard rejection
- auto-publish strategy
- overwrite official author profile
- claim author real trading performance

## 7. Evidence Separation Contract

Stage 7 API/UI must keep these evidence lanes separate:

- article expression evidence
- structured rule evidence
- backtest / applicability evidence
- LLM interpretation
- human review status
- data coverage / limitation

LLM output is draft evidence, not final truth. Every important profile conclusion must keep traceable source IDs, source versions and evidence fingerprints. New article evidence or new backtest evidence may create a new draft, new profile version or superseding draft, but must not silently overwrite a reviewed or published author profile.

## 8. Lifecycle and Review Contract

Stage 7 profile lifecycle states must support at minimum:

- `draft`
- `pending_review` or `in_review`
- `approved`
- `published` if product semantics require a published public state
- `rejected`
- `invalidated`
- `archived`
- `superseded`

All review and publication transitions must record:

- actor
- role
- time
- reason
- source surface
- before state
- after state
- affected profile version

LLM cannot approve, publish, invalidate, replace or overwrite official author profiles by itself.

## 9. Version and Time-Segment Contract

Every profile version must bind:

- author profile ID
- profile type
- profile version number
- source article revision IDs
- source `RuleVersion` IDs
- source `RuleFamily` IDs
- source `RuleApplicabilityProfile` IDs
- prompt version
- schema version
- evidence fingerprint
- profile fingerprint
- review status
- supersession chain
- validity period / time segment where applicable

RT-S7-004 must define time-segment rules before Stage 7 is accepted. Do not mix different author phases silently. New articles must not rewrite old time periods without explicit versioning and reviewer-visible supersession.

## 10. UI / API Expectations

Formal product surface:

- `/authors`

Legacy surface:

- `/persona` remains compatibility-only until Stage 7 replacement and retirement evidence.

Normal-user UI must show:

- profile purpose
- inputs
- evidence sources
- current status
- limitations
- next action
- review status
- version/time segment

Normal-user UI must not expose:

- Job
- Workflow
- Pipeline
- Artifact
- Provider
- `config_path`
- database table names
- internal function names
- Schema names
- file paths
- legacy persona terms as formal source

Use business Chinese and “市场状态”, not `Regime`.

## 11. Permissions and Audit

Expected minimum permissions:

- view author profile list/detail: viewer
- generate method/rule/validated drafts: operator
- request review: operator
- approve/reject/invalidate/archive/supersede: reviewer/operator with admin override policy
- view technical provenance details: admin or operator detail surface

Every mutation must write auditable transition evidence with actor, role, time, reason, source surface, before state, after state and profile version.

## 12. Schema and Migration Plan

Bootstrap creates no migrations.

Stage 7 implementation must first audit whether existing `AuthorProfileVersion` can satisfy all frozen requirements. If it cannot preserve reviewed profiles, source bindings, evidence separation, fingerprints, supersession and time segments safely, the task must stop with `ESCALATION_REQUIRED` instead of creating an unsafe migration.

Any later schema change must provide:

- one linear Alembic branch
- metadata registration
- safe upgrade
- safe rerun where applicable
- existing-data preservation
- explicit rejected/partial mapping
- downgrade or recovery plan
- PostgreSQL upgrade/downgrade/re-upgrade evidence

## 13. Final Task Order and Risk

Stage 7 is M3.

Final order:

1. `RT-S7-004 画像版本与时间分段` - M3.
2. `RT-S7-001 作者方法画像` - M3.
3. `RT-S7-002 作者规则画像` - M3.
4. `RT-S7-003 作者验证画像` - M3.

Rationale: versioning, lifecycle, review, fingerprints, supersession and time segmentation are shared by all three profile types. Implementing them first reduces the risk that method/rule/validated profiles invent separate draft/review/version rules. RT-S7-004 must not generate profile content; it only establishes the shared author-profile foundation.

Task Matrix combinations are not approved by Bootstrap. Each Task requires separate acceptance.

## 14. Task Cards

### RT-S7-004 画像版本与时间分段

- Goal: establish the shared author-profile version, lifecycle, review, audit and time-segment foundation.
- Current facts: `AuthorProfileVersion` exists; no dedicated Stage 7 runtime service/API/UI is accepted; `/authors` exists but currently falls back to legacy persona content.
- Reusable components: `AuthorProfileVersion`, `AuthorProfileKind`, `FormalLifecycleState`, `LifecycleEvent` concepts, `PromptRun`, `Authors`, `BusinessPageShell`, `ProductPageAdapter`.
- Rejected legacy paths: `/persona`, persona services, `/profiles` config profiles, Job/Workflow/Pipeline/Artifact/file outputs, legacy profile files.
- Canonical inputs: author identity, profile kind, source IDs, prompt/schema versions, review actor, evidence fingerprints.
- Immutable bindings: profile ID, kind, version number, source IDs, evidence fingerprint, profile fingerprint, lifecycle, supersession chain, validity period.
- LLM boundary: no LLM approval or overwrite; LLM output can only create draft evidence.
- Review boundary: human review transitions are required for official status changes.
- Schema/API/UI/runtime scope: audit current `AuthorProfileVersion`; add/refactor only if implementation session proves gaps; expose list/detail/review foundation under `/authors`; keep compatibility notices truthful.
- Permission/audit: viewer reads; operator drafts; reviewer/operator approves/rejects/invalidates/archives/supersedes; admin override audited.
- Tests: model/repository lifecycle, migration if schema changes, no overwrite of reviewed profiles, supersession, time-segment overlap/conflict, API permissions, UI state text, no technical terms.
- Completion criteria: shared version/lifecycle/time segment contract works and all three profile types can use it without duplicate rules.
- Stop/escalation conditions: existing schema cannot preserve reviewed profiles; unsafe migration needed; second formal author-profile table/source is required; strategy publication or daily behavior appears necessary.
- Out of scope: generating method/rule/validated profile content; Stage 8 strategy publication.
- Handoff: `RT-S7-001` after acceptance only.

### RT-S7-001 作者方法画像

- Goal: generate and review AuthorMethodProfile drafts from article structure and author-declared method evidence.
- Current facts: article structures and prompt runs are canonical; author-profile prompt assets exist but Stage 7 runtime is not accepted; current `/authors` page is transitional.
- Reusable components: `ArticleRevision`, `ArticleStructure`, `PromptRun`, author method prompt/schema assets after validation, shared Stage 7 profile foundation from RT-S7-004.
- Rejected legacy paths: persona clusters, behavior rules, file artifacts, old article summary fallback, full-text bulk prompt over all articles.
- Canonical inputs: ArticleStructure IDs, ArticleRevision IDs, article evidence snippets, prompt/schema version, author ID and time segment.
- Immutable bindings: source article revision IDs, structure IDs, prompt run ID, evidence fingerprint, profile fingerprint, profile version.
- LLM boundary: LLM may summarize author-declared method and clearly marked inference; it cannot invent unmentioned stop-loss/profit/holding/market-state facts or approve official profile.
- Review boundary: generated profile is draft; human review required before approved/published state.
- Schema/API/UI/runtime scope: method draft generation, list/detail/evidence display, limitations, review transitions, `/authors` method section.
- Permission/audit: operator drafts; reviewer/operator reviews; all transitions audited.
- Tests: prompt schema validation, fixed sample regression if Prompt is connected, article evidence traceability, no real-performance claims, no overwrite, UI loading/empty/error/partial/permission/unavailable states.
- Completion criteria: user can create/review a method profile draft from structured article evidence with source traceability and no legacy persona source.
- Stop/escalation conditions: missing ArticleStructure provenance; Prompt/schema mismatch; need to reread all article full text in one prompt; reviewed profile would be overwritten.
- Out of scope: rule statistics, backtest validation, strategy publication, daily trading decisions.
- Handoff: `RT-S7-002` after acceptance only.

### RT-S7-002 作者规则画像

- Goal: generate and review AuthorRuleProfile drafts from reviewed RuleVersion/RuleFamily structure and governance evidence.
- Current facts: RuleVersion/RuleFamily governance is accepted; Stage 4 lifecycle must not be mutated by profile generation.
- Reusable components: `RuleVersion`, `RuleVersionSourceLink`, `RuleFamily`, `RuleFamilyMembership`, rule governance repository/service read paths, shared Stage 7 profile foundation.
- Rejected legacy paths: rule-pool profile UI, legacy rule_pool records as formal truth, Job/pipeline results, mutable latest family membership without frozen source IDs.
- Canonical inputs: reviewed RuleVersion IDs, RuleFamily IDs, family memberships, rule evidence, rule dependencies, duplicate/conflict evidence.
- Immutable bindings: source RuleVersion IDs/fingerprints, RuleFamily IDs/fingerprints, membership snapshot, evidence/profile fingerprints.
- LLM boundary: program statistics are source facts; LLM may explain distribution/conflict but cannot change rules, families, lifecycle or dependencies.
- Review boundary: draft only until human review.
- Schema/API/UI/runtime scope: rule-profile statistics service, draft generation, evidence display, limitations, `/authors` rule section.
- Permission/audit: viewer reads; operator drafts; reviewer/operator reviews.
- Tests: statistics determinism, no RuleVersion/RuleFamily mutation, duplicate/conflict evidence, representative rules, UI source separation, no legacy rule-pool source.
- Completion criteria: user can view/review a rule profile draft with distribution, families, quantifiability, dependencies, conflicts and representative rules.
- Stop/escalation conditions: RuleFamily membership cannot be frozen; profile generation requires changing Stage 4 lifecycle; legacy rule-pool is the only source.
- Out of scope: backtest validation, applicability recommendation, strategy publication.
- Handoff: `RT-S7-003` after acceptance only.

### RT-S7-003 作者验证画像

- Goal: generate and review AuthorValidatedProfile drafts from formal Stage 6 applicability/backtest evidence.
- Current facts: Stage 6 Gate accepted formal `BacktestRun`, `BacktestResult` and `RuleApplicabilityProfile`; legacy `build_profile()` remains compatibility-only.
- Reusable components: formal `RuleApplicabilityProfile`, `BacktestRun`, `BacktestResult`, Stage 6 result API/service read paths, shared Stage 7 profile foundation.
- Rejected legacy paths: legacy `RuleApplicabilityService.build_profile()`, `review_profile()`, `backtest_result_runs`, `regime_metrics`, `/backtest_results`, legacy rule-pool profile UI, old JSON/file artifacts, SnapshotLoader, EvidencePack, live Provider.
- Canonical inputs: reviewed or reviewable formal RuleApplicabilityProfile IDs, source BacktestRun IDs, source BacktestResult IDs, source result fingerprints, sample/coverage/level/market-state evidence.
- Immutable bindings: RuleApplicabilityProfile IDs, run/result IDs, result fingerprints, DatasetSnapshot and MarketSnapshot fingerprints, level policy, market-state model/source versions.
- LLM boundary: LLM may summarize observed evidence and limitations; it must not calculate metrics, overstate insufficient samples, treat missing Kaipan as failure, or convert low confidence into hard rejection.
- Review boundary: draft only until human review; cannot auto-publish strategy or overwrite official author profile.
- Schema/API/UI/runtime scope: validated draft aggregation, evidence separation, limitations/sample display, `/authors` validated section.
- Permission/audit: operator drafts; reviewer/operator reviews; all transitions audited.
- Tests: immutable formal source only, insufficient sample semantics, missing Kaipan limitation, no real-performance claims, no strategy publication, no overwrite, UI separates backtest/applicability evidence.
- Completion criteria: user can create/review a validated profile draft from formal Stage 6 evidence and see strong/weak rule types, strong/weak market states, failure modes, coverage, samples, confidence and limitations.
- Stop/escalation conditions: formal RuleApplicabilityProfile cannot be identified; Stage 6 contract must change; old artifacts are the only available source; strategy publication is required to pass.
- Out of scope: daily pre-market/post-market behavior, official strategy updates, live Provider calls.
- Handoff: Stage 7 Gate only after all four Tasks are accepted.

## 15. Stage Gate Evidence Matrix

Stage 7 Gate must verify:

- all four RT-S7 Tasks accepted;
- `/authors` is the formal product surface;
- `/persona` and legacy profile/persona paths are compatibility-only;
- no formal Job/Workflow/Pipeline/Artifact/file/config_path/EvidencePack/live Provider source;
- ArticleStructure, RuleVersion/RuleFamily and RuleApplicabilityProfile evidence lanes are separated;
- author profiles are not represented as author real trading performance;
- LLM output remains draft evidence;
- human review and audit transitions are enforced;
- reviewed profiles are not overwritten;
- version/time-segment and supersession behavior is tested;
- UI uses business Chinese and “市场状态”;
- migration/recovery evidence exists if schema changes;
- Stage 8 strategy publication and daily behavior have not started.

## 16. Risks

Blocking:

- None identified during Bootstrap.

Non-blocking:

- No dedicated Stage 7 runtime service/API/UI is accepted yet.
- Existing `/authors` page still falls back to legacy persona content.
- Existing `AuthorProfileVersion` may need schema or repository repair before it satisfies all Stage 7 version/time/audit requirements.
- `RuleApplicabilityService` contains both formal and legacy methods; Stage 7 must call only formal paths.
- Legacy `/persona`, `/profiles`, rule-pool profile, backtest results and file/job-backed paths remain reachable as compatibility/admin surfaces.

External evidence limitations:

- Bootstrap did not run full tests because this was documentation-only.
- Bootstrap did not run migration replay because no migration was created.

## 17. First Executable Task

Next executable Task:

```text
RT-S7-004 画像版本与时间分段
```

Recommended model:

```text
gpt-5.5 for RT-S7-004
```

Reason: RT-S7-004 is M3 and freezes shared version, lifecycle, time-segment, review and migration-sensitive contracts for the rest of Stage 7.

`RT-S7-004` has not been started.
