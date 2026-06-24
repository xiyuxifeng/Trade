# RT-S12-002 Preflight Residual Risk Triage

## 1. Purpose

This document decides whether `RT-S12-002` can start based on all currently effective residual risks and known risks recorded in `docs/Refactor-Implementation-Log.md` and the stage implementation logs.

It is a preflight classification only. It does not start browser E2E, user documentation, Stage 12 Gate, or any backend/frontend/runtime/schema/governance work.

## 2. Sources Read

| Source | Risk information extracted |
| --- | --- |
| `docs/Refactor-Implementation-Log.md` | Current-state index, hard constraints, currently effective residual risks, accepted repairs, next-step authorization limits. |
| `docs/refactor-implementation-plans/stage-12-implementation-plan.md` | Frozen Stage 12 contract, RT-S12-002 acceptance criteria, stop/escalation rules, inherited Stage 11 residual-risk handling. |
| `docs/refactor-implementation-logs/stage-12.md` | Latest RT-S12-001 state, route retirement result, terminology blocker repair, retained residual risks after acceptance. |
| `docs/refactor-implementation-logs/stage-0.md` | Historical audit and migration-matrix baseline; no currently effective RT-S12-002 blocker found beyond later indexed risks. |
| `docs/refactor-implementation-logs/stage-1.md` | Historical navigation/page-state findings; later accepted, with no current blocker beyond Stage 12 ordinary-user route constraints. |
| `docs/refactor-implementation-logs/stage-2.md` | Migration/schema-convergence and recovery evidence history; current relevant risk is possible absent migration reports in some environments. |
| `docs/refactor-implementation-logs/stage-3.md` | Prompt registry, provenance, regression, batch recovery, and PromptRun evidence history; current relevant risk is truthful absence/partial evidence handling. |
| `docs/refactor-implementation-logs/stage-4.md` | Rule review/governance, duplicate/conflict, lifecycle, and legacy rule-pool compatibility history; current relevant risks are governance preservation and truthful unavailable states. |
| `docs/refactor-implementation-logs/stage-5.md` | OHLCV/Kaipan DatasetSnapshot/MarketSnapshot contracts and system data facade history; current relevant risks are data readiness and snapshot evidence verification. |
| `docs/refactor-implementation-logs/stage-6.md` | Formal backtest/result/applicability provenance and legacy backtest isolation; current relevant risks are snapshot-bound E2E proof and compatibility-only legacy paths. |
| `docs/refactor-implementation-logs/stage-7.md` | Author profile versioning/provenance and JSON source binding compromise; current relevant risks are traceability verification and future FK hardening. |
| `docs/refactor-implementation-logs/stage-8.md` | Canonical strategy source, publication/rollback, proposal-only revision flow, and Stage 8 E2E gap; current relevant risks are strategy governance proof and browser E2E evidence. |
| `docs/refactor-implementation-logs/stage-9.md` | Pre-market readiness, daily rule selection, trading plan, unavailable/degraded handling, and daily traceability JSON compromise. |
| `docs/refactor-implementation-logs/stage-10.md` | Post-close actuals, attribution, separated proposal lanes, formal after-close page, execution supplement and market-state identity residuals. |
| `docs/refactor-implementation-logs/stage-11.md` | System Management, recovery, observability, time semantics, cost control, rollout/recovery, user-friendly error handling, and residual-risk classification. |

Additional project-required context read before classification:

- `docs/Trade-Refactor-TaskList.md`
- `docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`
- `docs/PROMPT_REVIEW_AND_MIGRATION.md`
- `docs/AUTHOR_PROFILE_PROMPT_FLOW.md`
- `docs/LLM-Prompt-Orchestration.md`

## 3. RT-S12-002 Blocking Rules

A risk blocks `RT-S12-002` before E2E if it satisfies any of these rules:

1. The formal E2E journey still requires ordinary users to use legacy `Job`, `Workflow`, `Pipeline`, `Artifact`, `Provider`, `Schema`, `config_path`, `prompt_run_id`, or `run_id` as a normal workflow concept or required input.
2. A required formal route, UI/API entry, or next action is missing for the RT-S12-002 path.
3. Required real data, access token configuration, OHLCV/Kaipan data, browser tooling, or E2E seed data is missing and cannot be truthfully represented as `partial` or `unavailable`.
4. A required traceability ID/version/fingerprint cannot be captured at all during E2E.
5. Missing, partial, unavailable, degraded, invalid, or conflict states are hidden or converted into fake success.
6. The risk prevents RT-S12-002 from producing usable evidence.
7. The risk would force RT-S12-002 to change frozen governance, lifecycle, schema, route, or data-source contracts.

## 4. Summary Decision

No currently effective residual risk satisfies the pre-E2E blocking rules. `RT-S12-001` is accepted, route-level legacy main entries are redirect-only, the ordinary-user terminology blocker was repaired and classified, and the current-state index records no active blocker. The remaining risks are E2E evidence obligations, Stage 12 Gate hardening, accepted frozen-contract compromises, historical fixed items, or no-action compatibility/history items.

`READY_TO_START_RT_S12_002`

## 5. Must Fix Before RT-S12-002

| Risk | Source stage/log | Why it blocks RT-S12-002 | Required fix | Owner / likely area | Verification required before E2E |
| --- | --- | --- | --- | --- | --- |
| None currently identified. | `Refactor-Implementation-Log.md`; `stage-12.md` | No current risk satisfies the blocking rules after `RT-S12-001` blocker repair acceptance. | No pre-E2E fix required. | N/A | Confirm this document remains aligned with latest logs before starting E2E. |

## 6. Must Verify During RT-S12-002

| Risk | Source stage/log | Why it must be verified during E2E | Evidence to capture | Expected truthful state if unavailable/partial | Stop condition during E2E |
| --- | --- | --- | --- | --- | --- |
| Complete formal journey must use formal routes and not legacy normal-user entries. | Stage 12 plan; `stage-12.md`; `Refactor-Implementation-Log.md` | RT-S12-002 acceptance explicitly requires the formal path from article import through optimization proposals without developer-tool routes. | Browser screenshots/logs for each formal route and next action: `/research/add`, `/research/results`, `/rules/review`, `/rules/backtests`, `/rules/results`, `/authors`, `/strategies`, `/daily/pre-market`, `/daily/after-close`. | If a step lacks data, the page must show unavailable/partial with happened/impact/remediation guidance, not send users to legacy pages as required workflow. | Stop if a required user action depends on `/jobs`, `/workflows`, `/artifacts`, `/backtest*`, legacy profile pages, `config_path`, `prompt_run_id`, or raw `run_id` as user input. |
| Traceability IDs/version/fingerprints must be captured across the path. | Stage 12 plan; Stage 3-10 logs; `Refactor-Implementation-Log.md` | E2E must prove article revision, prompt/schema version, rule version, dataset snapshot, market snapshot/state model, backtest run/result, applicability profile, author profile versions, strategy version, daily objects, review, and proposal IDs. | A traceability checklist with captured values or page/API evidence for every required object. | If an older record lacks evidence, UI/API must show `partial` or `unavailable` and explain impact. | Stop if any required traceability value cannot be captured at all and cannot be truthfully marked unavailable. |
| Data readiness for OHLCV, Kaipan, DatasetSnapshot, MarketSnapshot, and market-state status. | Stage 5, Stage 9, Stage 10, Stage 11 logs | E2E depends on formal data snapshots and time semantics; missing data is acceptable only if truthfully represented. | Data-readiness API/UI evidence, snapshot IDs, content fingerprints, cutoff/slot evidence, missing ranges, and repair guidance. | `unavailable`, `partial`, `degraded`, `invalid`, `conflict`, or `insufficient_coverage` with visible impact and remediation. | Stop if missing data becomes false/0/success, or if backtest/daily/post-close flow calls live Provider or mutable latest rows as formal evidence. |
| Browser E2E has not yet been run. | Stage 8, Stage 9, Stage 11, Stage 12 plan/logs | The browser journey is the core purpose of RT-S12-002 and previous stages relied on focused tests. | Browser run output, screenshots or trace, route sequence, failures, and replacement evidence for any skipped full suite. | If browser tooling is unavailable, record the exact tooling issue and replacement evidence; escalate if usable E2E evidence cannot be produced. | Stop if browser tooling cannot run and no accepted replacement evidence can prove the formal path. |
| Backend/API focused suites must be selected and run for formal journey APIs. | Stage 12 plan; Stage 5-11 logs | E2E evidence needs API contract confidence without changing contracts. | Commands and results for article/prompt, rules, backtest, applicability, profiles, strategies, daily, system data/run, and post-market APIs as applicable. | Any unrun full suite must have reason, replacement focused suite, and residual risk recorded. | Stop if an API required by the formal path fails and the failure cannot be represented as an accepted unavailable/partial state. |
| Frontend focused suites must cover route replacement, navigation, states, and formal pages. | Stage 12 plan; `stage-12.md` | RT-S12-001 route cleanup must remain true during E2E. | Route/navigation/auth/visibility tests plus page-state tests for formal product routes. | If non-critical visual/responsive issues remain, record them as non-blocking only if text/actions remain usable. | Stop if primary navigation or formal journey exposes retired developer-tool entries as ordinary-user workflow concepts. |
| Prompt regression scope must be identified when prompt-dependent flows are exercised. | Stage 3 logs; Prompt docs; Stage 12 plan | Article extraction and author/profile flows depend on versioned prompts and schema validation. | Fixed prompt regression command/results or reason if using existing persisted prompt evidence only. | Prompt/data absence must show unavailable/manual-review/recovery state rather than fabricated extraction success. | Stop if E2E requires modifying prompt contracts or if prompt output bypasses schema/governance validation. |
| Migration/recovery evidence paths must remain preserved. | Stage 2, Stage 3, Stage 11, Stage 12 plan/logs | Stage 12 must not remove evidence required for migration recovery, prompt history, data provenance, audit, or rollback. | System Management recovery/rollout/run evidence screenshots/API payloads showing migration report state and prompt batch checkpoint state where available. | Missing reports or old PromptRun evidence may be `partial`/`unavailable`, with no forged proof. | Stop if E2E evidence requires a deleted legacy page as the only recovery/provenance path. |
| System Management diagnostics still display technical IDs for operators/admins. | `stage-12.md`; Stage 11 logs | Allowed only as diagnostics; E2E should prove ordinary users are not required to understand them. | Role/audience evidence showing ordinary-user business wording and admin/operator diagnostic separation. | Admin-only technical IDs may remain with Chinese labels; ordinary-user flow must use business labels. | Stop if ordinary-user steps require entering or interpreting raw technical IDs. |
| Stage 10 execution supplement missing. | Stage 10, Stage 11, `Refactor-Implementation-Log.md` | Non-blocking only if execution-specific fields remain unavailable instead of false/success. | Post-market review evidence showing program facts, actual source binding, and execution supplement state. | Execution supplement fields remain `unavailable` or equivalent with impact/remediation. | Stop if execution-specific fields are fabricated or used as required proof. |
| Caller-supplied `post_close_market_state_id` identity hardening. | Stage 10, Stage 11, `Refactor-Implementation-Log.md` | E2E must ensure canonical market-state identity is resolved or truthfully invalid/unavailable. | Post-close review evidence showing market-state ID/source/version and validation result. | `unavailable` or `invalid` if identity cannot be proven. | Stop if unknown market state is silently treated as valid. |
| `/strategies/candidates` compatibility notice page remains. | Stage 8; `Refactor-Implementation-Log.md` | It does not block E2E if formal strategy publication/revision path works, but E2E must not rely on it as the only strategy route. | Strategy publish/revision evidence from formal `/strategies` flow; note whether `/strategies/candidates` is touched. | If visited, it should be a compatibility notice, not required workflow. | Stop if strategy publication or revision requires a compatibility-only page as the only route. |

## 7. Can Fix After RT-S12-002 / Before Stage 12 Gate

| Risk | Source stage/log | Why it does not block E2E | Required handling before Gate | Suggested verification |
| --- | --- | --- | --- | --- |
| Stage 10 OpenAPI response-schema assertions are partial. | Stage 10 Gate; Stage 11 residual classification; Stage 12 plan | Formal E2E can collect focused API evidence first; Gate still needs contract review coverage. | Run full or targeted OpenAPI/response-schema contract review before Stage 12 Gate. | API contract tests for RT-S12-002 touched endpoints plus OpenAPI diff/validation. |
| Browser E2E and full all-repo lint were not run in Stage 11. | Stage 11 residual classification; Stage 12 plan | RT-S12-002 is the planned browser E2E point. Full all-repo lint can be recorded as run or intentionally scoped with replacement evidence. | Run browser E2E and record any unrun full suite with reason and replacement evidence. | Browser E2E trace/screenshots; focused lint/typecheck/test results; explicit full-suite decision. |
| Stage 2 migration reports and historical PromptRun evidence may be absent in some environments. | Stage 12 inherited risks; Stage 11 rollout/recovery log | Absence can be truthfully displayed as `partial`/`unavailable`; it does not preclude E2E if not needed as complete proof. | Gate evidence must show absence is visible and does not remove recovery/provenance paths. | System rollout/recovery API/UI evidence for present and missing report states. |
| User documentation remains unstarted. | `Refactor-Implementation-Log.md`; Stage 12 plan/log | User docs are RT-S12-003, not a prerequisite for RT-S12-002. | Complete RT-S12-003 before Stage 12 Gate. | Documentation terminology/link scan and final UI consistency review. |
| Full Stage 12 Gate has not started. | `Refactor-Implementation-Log.md`; Stage 12 plan | Gate is after RT-S12-002/003 evidence. | Run Gate only after E2E and user docs are complete and reviewed. | Stage 12 Gate checklist and recorded verification. |

## 8. Future Hardening / After Stage 12

| Risk | Source stage/log | Why it can be deferred | Potential future improvement | Contract escalation needed? yes/no |
| --- | --- | --- | --- | --- |
| Stage 7 source-version bindings remain JSON/service constrained rather than FK detail tables. | `Refactor-Implementation-Log.md`; Stage 7 Gate | Accepted under frozen Stage 7 contract; traceability still exists and can be captured during E2E. | Add stronger FK detail tables for source versions/evidence bindings. | yes |
| Stage 7 structured article source bindings include `prompt_run_id` in JSON rather than a separate detail table. | `Refactor-Implementation-Log.md`; Stage 7 logs | Accepted compromise to avoid a second formal source; not a normal-user workflow input. | Normalize prompt/source bindings into queryable detail tables. | yes |
| Minimal lifecycle remains `draft/pending_review/published/archived`; richer `rejected/invalidated/superseded` UI workflow is deferred. | `Refactor-Implementation-Log.md`; Stage 8 logs | Current governance paths are accepted and do not block formal journey evidence. | Add richer lifecycle operations and stronger frontend workflow audit. | yes |
| Daily traceability is stored in canonical JSON payload rather than top-level columns. | Stage 9 logs; `Refactor-Implementation-Log.md` | Accepted under frozen contract; E2E can capture JSON traceability evidence. | Promote required daily traceability fields to indexed columns if SQL-level filtering becomes necessary. | yes |
| DailyRuleSelection write guard can be strengthened. | `Refactor-Implementation-Log.md`; Stage 9 Gate | Non-blocking hardening; current services accepted with focused verification. | Add stricter write guards or lifecycle constraints for daily selection mutation. | yes |
| DatasetSnapshot lacks independent persisted `captured_at`/`slot` columns. | Stage 11/12 residual classification | Non-blocking unless Stage 12 changes data-time schema; current contract requires truthful unknown/null handling. | Add explicit captured-at and slot columns with migration/backfill semantics. | yes |
| Execution supplement is missing for execution-specific post-market fields. | Stage 10/11 logs; `Refactor-Implementation-Log.md` | Formal post-close actuals are sufficient for signal outcome metrics; execution-specific data remains unavailable. | Add approved imported actuals/execution supplement contract that covers all required execution fields. | yes |
| Direct legacy detail resolvers for old job/artifact/profile IDs are not fully built. | `stage-12.md` | Route candidates redirect to formal targets and are not ordinary-user workflow entries; evidence can be queried through system diagnostics. | Add formal detail resolvers by business object or diagnostic ID. | no |
| UI visual consistency, non-critical responsive details, and copy polish remain backlog. | `Refactor-Implementation-Log.md`; Stage 8 logs | Does not block E2E if formal actions and states are usable. | Design polish pass after final delivery evidence. | no |

## 9. Already Fixed

| Former risk | Source stage/log | Fix recorded | Verification recorded | Current status |
| --- | --- | --- | --- | --- |
| RT-S12-001 internal terminology blocker in ordinary-user-adjacent frontend source. | `stage-12.md`; `Refactor-Implementation-Log.md` | Shared error recovery, dashboard/status panels, System Management labels, and retired links cleaned up; remaining 5044 hits classified. | Focused frontend suite `89 passed`, `pnpm typecheck`, targeted eslint, `git diff --check`, terminology scan classification. | Fixed; no remaining blocker. |
| Retirement-candidate legacy routes mounted as legacy pages. | `stage-12.md` | All RT-S12-001 retirement candidates changed to redirect-only or formal targets. | Route/navigation tests passed; dynamic redirect test added. | Fixed for RT-S12-001. |
| `/strategies/after-close` compatibility route remained as inherited Stage 11 risk. | Stage 12 plan; `stage-12.md` | RT-S12-001 redirects `/strategies/after-close` to `/daily/after-close`. | Route-config and navigation focused tests passed. | Fixed as normal-user route blocker. |
| `/daily/pre-market` previously delegated to legacy pre-market workspace. | Stage 9 logs; `Refactor-Implementation-Log.md` | Formal pre-market readiness, daily rule selection, daily strategy instance, and trading plan services/API/UI implemented. | Stage 9 focused backend/API/frontend/typecheck verification; Gate accepted. | Fixed. |
| Stage 9 deterministic applicability selection, OHLCV filtering, user-language leakage, Chinese state mapping, and duplicate router error branch. | Stage 9 Gate; `Refactor-Implementation-Log.md` | Gate bounded repairs completed. | Stage 9 Gate accepted. | Fixed. |
| Stage 10 schema drift, row/dataset binding, baseline policy, and matched-rule evidence issues. | Stage 10 logs; `Refactor-Implementation-Log.md` | RT-S10-001 bounded repairs completed. | Parent acceptance review accepted. | Fixed. |
| Post-market page was legacy/compatibility route. | Stage 10 logs; `Refactor-Implementation-Log.md` | `/daily/after-close` replaced with formal post-market page and aggregation API/client/types. | Focused API/frontend verification and `pnpm typecheck`; RT-S10-004 accepted. | Fixed. |
| System data compatibility mapping for `/market/datasets` missing visible target. | Stage 11 logs; `Refactor-Implementation-Log.md` | `/system/data` added visible `数据源兼容入口` mapping. | Focused frontend tests and `pnpm typecheck`; accepted. | Fixed. |
| User-friendly error contract gaps. | Stage 11 logs; `Refactor-Implementation-Log.md` | Shared contract now requires happened/impact/remediation and separates ordinary-user text from admin diagnostics. | Focused Vitest/typecheck/targeted eslint/grep/diff-check; accepted. | Fixed. |
| Missing run trace visibility for Prompt/data/backtest evidence. | Stage 11 logs; `Refactor-Implementation-Log.md` | `/system/runs` exposes bounded run trace, prompt calls, data fetch, backtest evidence, rule/code versions. | Focused pytest/vitest/typecheck/diff-check; accepted. | Fixed. |
| Late data could appear decision-time available. | Stage 11 logs; `Refactor-Implementation-Log.md` | Pre-market and post-market cutoff enforcement added; late data remains truthful. | Parent acceptance review accepted. | Fixed. |
| Migration/rollback evidence absent from system UI. | Stage 11 logs; `Refactor-Implementation-Log.md` | Rollout/recovery service and UI expose report presence, counts, rejected/conflicted rows, recovery export, and partial state if absent. | Parent acceptance review accepted. | Fixed. |

## 10. No Action Needed

| Item | Source stage/log | Reason no action is needed | Any caveat |
| --- | --- | --- | --- |
| Historical blockers in Stage 1, Stage 3, Stage 4, and early Stage 12 review entries. | Stage 1, Stage 3, Stage 4, Stage 12 logs | Later accepted repairs supersede them; current-state index records no active blocker from those entries. | Do not cite old blocked states as current blockers unless a newer log reopens them. |
| Developer terms in `docs/bak/**`, `docs/Deprecated/**`, historical stage logs, migration matrix, and old implementation notes. | Stage 12 scan classification | These are historical or archived evidence, not normal user documentation. | RT-S12-003 user docs still need a fresh terminology/link scan. |
| Internal TypeScript types, API clients, backend fields, and unmounted legacy source containing `Job`, `Artifact`, `run_id`, `prompt_run_id`, or similar names. | `stage-12.md` terminology classification | Classified as internal implementation only or unmounted legacy source; not ordinary-user workflow concepts after route retirement. | E2E must still verify visible ordinary-user routes do not expose them as required inputs. |
| System Management admin/operator diagnostics showing technical IDs. | Stage 11 logs; `stage-12.md` | Allowed diagnostic-only surface with Chinese labels and user/admin separation. | Ordinary-user journey must not require these IDs. |
| Compatibility-only legacy services or CLI paths that are rejected/read-only/non-formal. | Stage 4, Stage 6, Stage 9, Stage 10 logs | They are not formal sources of truth and are not normal user workflow entries. | Stop if E2E unexpectedly depends on them. |
| Stage 8 and Stage 9 prior browser E2E gaps. | Stage 8, Stage 9 logs | These are historical gaps whose planned closure is RT-S12-002 itself. | Must verify during RT-S12-002. |

## 11. RT-S12-002 Start Checklist

- [ ] Formal route path does not require legacy normal-user entries.
- [ ] Data readiness / OHLCV / Kaipan / DatasetSnapshot / MarketSnapshot status known.
- [ ] Required access tokens and external data dependencies known or truthfully unavailable.
- [ ] Browser E2E tooling available.
- [ ] Backend/API focused suites identifiable.
- [ ] Frontend focused suites identifiable.
- [ ] Migration/recovery evidence paths preserved.
- [ ] Prompt regression scope identified.
- [ ] Traceability IDs/version/fingerprints to capture listed:
  - article revision ID/content hash
  - prompt name/version and schema version
  - prompt run evidence or truthful unavailable state
  - rule version ID/fingerprint/family
  - DatasetSnapshot ID/content fingerprint
  - MarketSnapshot ID/content fingerprint and market-state model/version
  - BacktestRun ID and BacktestResult ID/result fingerprint
  - RuleApplicabilityProfile ID/version/fingerprint
  - AuthorMethodProfile, AuthorRuleProfile, and AuthorValidatedProfile version IDs/fingerprints
  - StrategyVersion ID/fingerprint and current strategy pointer/audit evidence
  - DailyRuleSelection ID/traceability payload
  - DailyStrategyInstance ID
  - TradingDayPlan ID/review state
  - PostMarketReview ID/actual snapshot binding
  - RuleOptimizationProposal, AuthorProfileRevisionProposal, and StrategyRevisionProposal IDs
- [ ] Any unrun full-suite test will be recorded with reason and replacement evidence.

## 12. Final Recommendation

Start `RT-S12-002` now, after the normal explicit authorization to begin that task.

There are no exact pre-E2E blockers currently identified. Do not include broad hardening as a blocker unless E2E discovers one of the blocking-rule conditions above.
