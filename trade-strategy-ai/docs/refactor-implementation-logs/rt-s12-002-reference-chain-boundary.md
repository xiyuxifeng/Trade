# RT-S12-002 Reference Chain Boundary

Date: 2026-06-25

Status: `BOUNDARY_DOCUMENTED`

Scope:

- This document records the boundary between RT-S12-002 pre-E2E repair evidence and final browser E2E acceptance evidence.
- This is a documentation-only repair.
- No production code, database schema, business evidence, browser E2E, RT-S12-003 user documentation, or Stage 12 Gate work was started by this document.

## 1. Current Stage 12 state

The latest RT-S12-002 Minimal Canonical Evidence Repair Resume on the original data device ended as `STILL_BLOCKED`.

The current blocker is no longer the earlier `BacktestRun.status` schema mismatch. That mismatch has been repaired by mapping `BacktestRun.status` to the migration-backed `String(32)` schema while keeping `BacktestRunStatus` as a Python/service-layer allowed-value constant.

The current blocker is:

```text
StrategyCenterService.validate_version returned insufficient_coverage
```

The validation blocker is caused by missing/insufficient strategy validation coverage evidence, specifically:

```text
backtest.out_of_sample_state = unavailable
sample_coverage.state = unknown
```

Because of this, the current StrategyVersion remains a draft and cannot be published without bypassing the formal validation contract.

## 2. Evidence already created by repair

The repair/resume work has already created or advanced a reference evidence chain through:

- selected 5-article subset
- selected symbols `002104.SZ` and `603280.SH`
- bounded OHLCV window for selected symbols
- ready DatasetSnapshots
- selected-symbol MarketSnapshots / MarketRegimes with partial quality
- `BacktestRun`
- `BacktestResult`
- `RuleApplicabilityProfile`
- canonical author
- `RuleVersion` published through the lifecycle service
- method/rule/validated `AuthorProfileVersion` records
- `StrategyVersion` draft

Important: this chain is reference evidence only. It is not final browser E2E pass evidence.

## 3. Boundary decision

RT-S12-002 will use Strategy B:

```text
Repair generates a reference chain.
Browser E2E generates a separate final E2E chain through formal routes.
```

This means:

- Repair may continue to complete a full reference chain after fixing `insufficient_coverage`.
- Repair-generated objects prove that backend/service contracts and canonical evidence plumbing can work.
- Browser E2E must not pass merely by reading or displaying repair-generated reference objects.
- Browser E2E must create or lifecycle-transition its own E2E evidence through formal user-facing routes or their formally authorized page actions.

## 4. What repair may do next

The next repair should be named:

```text
RT-S12-002 Reference Chain Completion Repair
```

Its goal is to finish the reference chain only:

```text
fix Strategy validation coverage evidence
→ publish reference StrategyVersion
→ generate reference DailyRuleSelection
→ generate reference DailyStrategyInstance
→ generate reference TradingDayPlan
→ generate reference PostMarketReview
→ generate reference OptimizationProposal
→ mark READY_FOR_RT_S12_002_IMPLEMENTATION only if the reference chain is complete
```

The repair must record that all generated objects are `reference_chain` evidence, not final E2E acceptance evidence.

## 5. What browser E2E must do later

RT-S12-002 Browser E2E Acceptance must generate or transition a separate chain. It must not count the reference chain as final pass evidence.

Browser E2E must record new IDs and/or new lifecycle transitions for at least:

- E2E StrategyVersion validation
- E2E StrategyVersion publish transition
- current published strategy pointer after E2E publish
- E2E DailyRuleSelection
- E2E DailyStrategyInstance
- E2E TradingDayPlan
- E2E PostMarketReview
- E2E OptimizationProposal

If the E2E uses a previously prepared draft, it must still prove that the E2E itself performed the publish transition and downstream daily/post-close/proposal generation.

## 6. Recommended strategy scope for E2E

To avoid reference-chain and E2E-chain collisions, prefer one of these patterns:

1. Different strategy scopes/business keys:
   - reference chain: `rt-s12-002-reference`
   - browser E2E chain: `rt-s12-002-e2e`
2. Same strategy scope but new version:
   - reference chain publishes v1
   - browser E2E creates and publishes v2
   - E2E must verify `current_published_version_id` moved from v1 to v2 and that an audited transition exists

Do not let browser E2E simply reuse the reference StrategyVersion as final evidence.

## 7. Browser E2E pass criteria

A valid RT-S12-002 Browser E2E pass must prove:

```text
formal route entry
→ formal user-visible action or authorized page action
→ new object or new lifecycle transition
→ immutable/audited evidence binding
→ final object IDs recorded in the E2E report
```

At minimum, the E2E report must include:

| Step | Required proof |
| --- | --- |
| strategy validation | validation was executed during E2E and result is `passed` |
| strategy publish | StrategyVersion was published during E2E, with audit/lifecycle evidence |
| current strategy | current published pointer points to E2E-published version |
| pre-market | new DailyRuleSelection / DailyStrategyInstance / TradingDayPlan IDs |
| post-close | new PostMarketReview ID |
| optimization | new OptimizationProposal ID |

## 8. Explicit non-goals

The following are not valid final RT-S12-002 pass evidence by themselves:

- pre-existing BacktestRun / BacktestResult from repair
- pre-existing RuleApplicabilityProfile from repair
- pre-existing AuthorProfileVersion from repair
- pre-existing published RuleVersion from repair
- pre-existing StrategyVersion draft from repair
- future reference-chain published StrategyVersion generated by repair
- future reference-chain DailyRuleSelection / TradingDayPlan / PostMarketReview / OptimizationProposal generated by repair

They may be used as setup, smoke evidence, or comparison evidence only.

## 9. Documentation consistency requirement

Before starting RT-S12-002 Browser E2E Acceptance, the controlling prompt must read this document in addition to:

- `docs/Refactor-Implementation-Log.md`
- `docs/refactor-implementation-logs/stage-12.md`
- `docs/refactor-implementation-logs/rt-s12-002-preflight.md`

If those longer logs contain older wording such as generic OHLCV/DatasetSnapshot/BacktestRun blockers, this document clarifies the current boundary decision:

```text
Current blocker: Strategy validation insufficient_coverage.
Current boundary: repair chain is reference evidence only; browser E2E must generate a separate final E2E chain.
```

## 10. Next allowed action

Next allowed task:

```text
RT-S12-002 Reference Chain Completion Repair
```

Do not start:

- RT-S12-002 Browser E2E Acceptance
- RT-S12-003 user documentation
- Stage 12 Gate

until the reference chain is complete and the final decision is `READY_FOR_RT_S12_002_IMPLEMENTATION`.
