# Stage 4 Rule Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `refactor-orchestrator` for every Task session and Stage Gate. Use `superpowers:test-driven-development` during implementation. Do not execute more than one Task Card as one acceptance unit unless the Parent explicitly freezes a shared contract for RT-S4-002 + RT-S4-003 in the same session.

**Goal:** Turn Stage 3 revision-bound rule candidates into auditable, deduplicated, versioned rule assets without reintroducing legacy writers or fabricating unavailable summaries.

**Architecture:** Stage 4 uses the canonical Stage 2 rule graph (`RuleCandidate`, `Rule`, `RuleVersion`, `RuleFamily`, `RuleFamilyMembership`, `LifecycleEvent`) as the only formal governance source. Legacy `rule_pool` remains compatibility/history only and must not become a normal write path. Governance mutations must be blocked until the Stage 3 fixed regression gate passes.

**Tech Stack:** Python, FastAPI, SQLAlchemy/Alembic, Pydantic, Typer CLI, React, TypeScript, Vitest, pytest.

---

## 1. Stage 4 Objective

Stage 4 establishes rule governance:

- automatic review and human review workbench;
- deterministic rule fingerprinting, duplicate/conflict detection, parameter variants, and RuleFamily membership;
- a user-understandable rule lifecycle from candidate through retired states;
- complete audit/provenance for automatic decisions, human edits, merges, approvals, lifecycle transitions, and retirements.

Stage 4 does not implement Stage 5 data foundations, Stage 6 backtest execution, Stage 7 author profiles, Stage 8 strategy publication, or daily pre/post-market workflows.

## 2. Authoritative Sources Reviewed

- `docs/Trade-Refactor-TaskList.md`
- `docs/AI-Conversation-Templates.md`
- `docs/AI-Conversation-Project-Constraints-1.md`
- `docs/AI-Conversation-Project-Constraints-2.md`
- `docs/AI-Conversation-Task-Matrix.md`
- `docs/Refactor-Implementation-Log.md`
- `docs/refactor-implementation-logs/stage-3.md`
- `docs/refactor-implementation-plans/stage-3-implementation-plan.md`
- `docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`
- `docs/PROMPT_REVIEW_AND_MIGRATION.md`
- `docs/AUTHOR_PROFILE_PROMPT_FLOW.md`
- `docs/LLM-Prompt-Orchestration.md`

The prompt named `docs/AI-Conversation-Project-Constraints.md` is not present as a current file. Current repository authority is split into `AI-Conversation-Project-Constraints-1.md` and `AI-Conversation-Project-Constraints-2.md`, as referenced by `AI-Conversation-Templates.md`.

The current product plan contains an older stage-numbering section where its "Stage 4" means daily pre-market. For this plan, Stage 4 scope is taken from `Trade-Refactor-TaskList.md`; the product plan is used only for matching rule-governance semantics.

## 3. Accepted Stage 3 Entry Conditions

Stage 3 Gate is recorded as:

```text
ACCEPTED: next Stage may begin
```

Accepted Stage 3 invariants carried forward:

- canonical writer is the only normal production write path;
- no dual-write behavior may be reintroduced;
- `STAGE2_CANONICAL_WRITER_ENABLED=true` remains the required normal mode;
- `STAGE2_CANONICAL_WRITER_ENABLED=false` is emergency rollback only;
- future-stage Prompt behavior remains inactive unless a later-stage contract activates it;
- summary data remains bound to the immutable `ArticleRevision` used to generate it;
- older revisions without frozen summaries remain truthfully unavailable;
- missing historical summaries must not be synthesized from newer revisions or current article state;
- fixed-set gate must pass before Stage 4 rule-governance mutations;
- downstream pages, APIs, services, jobs, CLI paths, exports, and workflows must preserve truthful unavailable semantics;
- retired legacy Prompt or writer paths must not be restored as fallbacks;
- database constraints, provenance, lineage, idempotency, and auditability from Stages 2 and 3 must not be weakened.

## 4. Repository And Working-Tree Baseline

- Repository remote: `git@github.com:xiyuxifeng/Trade.git`
- Git root: repository root containing `trade-strategy-ai`
- Project root: `trade-strategy-ai`
- Branch: `main`
- HEAD: `77dba41a3149c03daa82cfbc72b9b83cd70b6881` (`Stage 3 Review`)
- Working tree at Bootstrap start: clean (`git status --short --branch --untracked-files=all` returned only `## main...origin/main`)
- Staged diff: none
- Uncommitted Stage 3 Gate repairs mentioned in the user handoff were not present as dirty files; repository evidence shows the Stage 3 review and repairs are already incorporated in HEAD.
- Bootstrap documentation changes are limited to this plan and the Stage 4 logs.

## 5. Exact Stage 4 Tasks

### RT-S4-001 Automatic Review And Human Review Workbench

Build a two-level review mechanism:

```text
LLM candidate rules
-> deterministic automatic review and risk classification
-> low-risk rules enter pending backtest
-> ambiguous or high-risk rules enter human review
-> backtest validation
-> human confirmation before formal strategy use
```

Automatic review statuses must be:

```text
auto_pass
recommend_pass
manual_review
not_backtestable
recommend_reject
```

Human review must support source/evidence inspection, automatic review reasons, risk, missing fields, data dependencies, duplicate/conflict findings, editing, approve, approve-after-edit, merge, hold, reject, low-risk batch approve, invalid batch reject, and filtering for human-review-needed items.

### RT-S4-002 Rule Fingerprint And RuleFamily

Implement deterministic rule fingerprints, similar-rule detection, duplicate merge, parameter variants, conflict detection, `RuleFamily`, and source-article linkage. The runtime implementation must use the canonical rule graph, not legacy `rule_pool`, as the formal governance source.

### RT-S4-003 Rule Lifecycle

Expose and enforce the user-facing lifecycle:

```text
候选 -> 待审核 -> 已批准 -> 待回测 -> 验证中 -> 可用 -> 限定使用 -> 已停用
```

This lifecycle must be mapped to canonical persisted state without weakening Stage 2 `FormalLifecycleState` contracts. Every transition records actor, time, reason, before/after values, and correlation id.

## 6. In Scope And Out Of Scope

In scope:

- canonical rule-governance service and repository layer;
- fixed-set gate enforcement before governance mutations;
- deterministic automatic review rule set;
- candidate review queue and human review actions;
- rule fingerprint, duplicate/conflict, RuleFamily, and membership runtime;
- lifecycle transition service and audit events;
- user-facing API and Web surfaces under business Chinese labels;
- compatibility freezing/retirement rules for legacy rule-pool write paths;
- focused backend, API, migration, frontend, and regression tests;
- Stage 4 implementation logs and user-facing documentation updates in `docs/`.

Out of scope:

- OHLCV/Kaipan data foundation and DatasetSnapshot buildout from Stage 5;
- full reproducible backtest engine and market-state validation from Stage 6;
- author profile generation and publication from Stage 7;
- strategy version publication from Stage 8;
- daily pre-market and post-market workflows from Stages 9 and 10;
- activating future-stage LLM attribution/postmortem Prompts;
- restoring legacy Prompt or legacy writer fallback.

## 7. Current-State Findings

Canonical foundation exists:

- `src/models/stage2_canonical.py` defines `RuleCandidate`, `Rule`, `RuleVersion`, `RuleFamily`, `RuleFamilyMembership`, `LifecycleEvent`, and downstream rule-related models.
- `src/db/migrations/versions/2026_06_14_0003_stage2_domain_schema.py` creates the canonical domain tables and enums.
- `src/db/migrations/versions/2026_06_14_0005_stage2_gate_schema_repair.py` repairs downstream canonical FKs.
- `src/services/stage3_prompt_runtime_service.py` writes canonical `PromptRun`, `ArticleStructure`, and `RuleCandidate`.
- `src/services/stage3_single_article_service.py` computes deterministic Stage 3 automatic review and supports candidate approve/reject.
- `src/db/repositories/stage3_single_article_repository.py` creates `Rule` and `RuleVersion` under canonical write scope.

Gaps:

- no active canonical RuleFamily governance service;
- no active runtime duplicate/conflict/merge service;
- no complete Stage 4 lifecycle transition service;
- no dedicated public rule-family UI/API;
- automatic review currently has only three Stage 3 statuses: `pending_backtest`, `needs_human_review`, `suggested_reject`;
- direct review APIs/CLI do not visibly enforce the Stage 3 fixed-set gate before governance mutation;
- legacy `rule_pool`, `strategy_studio`, job, CLI, and pipeline paths still expose review/backtest concepts and may conflict with a single governance ledger if treated as formal.

User-facing gaps:

- some live pages still expose `Job`, `Pipeline`, `Schema`, `Regime`, or internal field names in normal-user surfaces;
- `web/src/pages/rules/index.tsx` currently delegates to the older `RulePoolPage`;
- `web/src/features/backtest/regime-backtest-report.tsx` still uses Regime wording.

These are Stage 4 implementation findings, not Bootstrap blockers.

## 8. Required Architecture And Data-Flow Changes

Target Stage 4 data flow:

```text
ArticleRevision
-> PromptRun / ArticleStructure / RuleCandidate
-> fixed-set gate check
-> RuleGovernanceAutomaticReview
-> fingerprint / duplicate / conflict / RuleFamily proposal
-> HumanReviewAction
-> Rule / RuleVersion / RuleFamilyMembership
-> LifecycleEvent audit trail
-> pending backtest boundary
```

Rules:

- automatic review never makes a rule formally usable;
- low-risk automatic pass only moves a candidate to pending backtest;
- any parameter edit, high-risk field, ambiguity, conflict, inferred market state, Kaipan dependency, or strategy entry requires human approval;
- formal rule facts are canonical `RuleVersion` plus audit/provenance, not LLM raw output and not legacy `RulePool`;
- UI can show legacy history only as compatibility/history with explicit unavailable/limited semantics.

## 9. Revision, Summary, Fixed-Set, Rule, And Provenance Contracts

- Stage 4 input candidates must trace to `RuleCandidate.article_structure_id`.
- `ArticleStructure` must trace to `PromptRun` and `ArticleRevision`.
- Summary display must use Stage 3 summary provenance: frozen `ArticleRevision.source_payload.summary`, or current article summary only when content hash aligns, otherwise unavailable.
- The fixed regression set must pass before any Stage 4 governance mutation.
- Rule fingerprints must be deterministic from normalized rule semantics, not from mutable display text.
- Rule provenance must distinguish explicit article facts, LLM inference, program review, backtest observation, and human approval.
- Lifecycle and review actions must record actor, time, reason, before/after values, and correlation id.

## 10. Database And Migration Impact

Expected:

- reuse existing canonical `RuleCandidate`, `Rule`, `RuleVersion`, `RuleFamily`, `RuleFamilyMembership`, and `LifecycleEvent`;
- add migrations only if current columns cannot durably represent automatic-review result details, conflict records, merge decisions, source links, or lifecycle/audit requirements;
- add uniqueness constraints where needed to prevent duplicate `RuleVersion` creation from one `RuleCandidate` if app-layer idempotency is insufficient;
- preserve safe upgrade, safe rerun, observability, and recovery reports.

Forbidden:

- dropping or overwriting legacy `rule_pool` data silently;
- introducing another Alembic branch;
- weakening Stage 2 constraints;
- adding a second formal rule schema.

## 11. Backend/API Impact

Expected backend areas:

- `src/services/stage3_single_article_service.py`: reuse or extract deterministic review logic; do not expand it into a second formal governance writer.
- `src/db/repositories/stage3_single_article_repository.py`: keep Stage 3 candidate approval behavior compatible while routing Stage 4 formal transitions through the new governance service.
- New likely files: `src/services/rule_governance_service.py`, `src/db/repositories/rule_governance_repository.py`, `api/routers/ui/rule_governance.py`, `api/schemas/rule_governance.py`, with exact names confirmed during implementation.
- `api/routers/ui/rule_pool.py` and `api/routers/ui/strategy_studio.py`: freeze or route compatibility paths so they cannot form a second formal governance path.
- `cli/main.py`: direct `rule-pool review` commands must not bypass fixed-set gate or canonical governance.

## 12. Web UI Impact

Expected Web areas:

- `/rules/review` becomes the Stage 4 review workbench.
- `/rules/library` shows formal rule versions and lifecycle state.
- Rule-family grouping and duplicate/conflict display are introduced under the rule-governance surface.
- Normal-user text must use Chinese business terms:
  - `开始回测`
  - `查看本次结果`
  - `补齐缺失数据`
  - `查看失败原因`
  - `市场状态`
- Normal-user text must not expose `Job`, `Workflow`, `Pipeline`, `Artifact`, `Provider`, `Schema`, `Regime`, internal function names, database names, or file paths.
- Loading, empty, error, partial, permission denied, and unavailable states must explain what happened, impact, and remediation.

## 13. Job, Worker, Scheduler, And CLI Impact

Current code exposes `rule-pool-backtest`, `candidate-review`, and `rule-review` job semantics plus `cli rule-pool review` and `review-batch`.

Stage 4 must decide per path:

- route through canonical governance service with fixed-set gate; or
- freeze as compatibility/read-only/history; or
- mark for later retirement with explicit conditions.

No direct worker, scheduler, or CLI path may mutate formal rule governance outside canonical write scope.

## 14. Compatibility And Retirement Rules

- Legacy `rule_pool` is not a formal Stage 4 source of truth.
- `strategy_studio` rule-pool endpoints remain compatibility only until explicitly retired.
- Compatibility reads may preserve historical evidence, but must not synthesize formal Stage 4 status.
- Compatibility writes must remain rejected in normal canonical-writer mode unless routed through canonical governance service.
- Retirement must include reference scan, migration/compatibility report, rollback/recovery evidence, and observation criteria.

## 15. Task Dependency Graph And Execution Order

Recommended execution order:

1. `RT-S4-002` - freeze and implement fingerprint, duplicate/conflict, RuleFamily runtime contracts.
2. `RT-S4-003` - freeze and implement lifecycle mapping and transition audit using the fingerprint/family contracts.
3. `RT-S4-001` - build automatic/human review workbench on top of dedupe/conflict/lifecycle foundations.
4. Stage 4 Gate - full evidence review and bounded repair only if needed.

Rationale:

- RT-S4-001 requires duplicate/conflict findings from RT-S4-002 and lifecycle transitions from RT-S4-003.
- `AI-Conversation-Task-Matrix.md` allows RT-S4-002 + RT-S4-003 in one session serially; RT-S4-001 is recommended later and separate.

## 16. Per-Task Implementation Boundaries

### RT-S4-002 Boundary

Allowed:

- deterministic fingerprint normalization;
- RuleFamily repository/service;
- duplicate/similar/conflict detection;
- source article and evidence linkage;
- focused API/schema for family and conflict results;
- tests for idempotency and no duplicate backtest candidates.

Forbidden:

- publishing rules;
- running full backtests;
- strategy selection;
- author profile updates;
- legacy writer fallback.

### RT-S4-003 Boundary

Allowed:

- lifecycle mapping for user-facing states;
- transition service;
- lifecycle event audit;
- retirement/limited-use states if represented safely;
- compatibility state display mapping.

RT-S4-003 frozen implementation contract:

- `候选` and `待审核` are candidate states; `已批准` / `待回测` / `验证中` / `可用` / `限定使用` / `已停用` are formal lifecycle views derived from canonical `RuleVersion` state plus auditable lifecycle metadata.
- `draft` may truthfully display as either `已批准` or `待回测` only when supported by lifecycle evidence; `draft` without such proof remains unavailable.
- `published` becomes `可用` only when promoted as the current usable version; `published` with a restriction marker or without current-use promotion displays `限定使用`.
- `FormalLifecycleState.approved` is not auto-mapped to `可用` during Stage 4.
- no new migration is required if audit metadata, source action, evidence refs, and restriction flags fit durably in `LifecycleEvent.after_json` and `RuleVersion.evidence_json`, and stale-write protection can use existing timestamps.
- legacy `rule_pool` / `strategy_studio` review writes must be routed to canonical lifecycle service or rejected as compatibility-only.

Forbidden:

- changing Stage 2 formal lifecycle enum without a migration and compatibility proof;
- treating automatic review as formal usability;
- accepting strategy-entry rules without human approval.

### RT-S4-001 Boundary

Allowed:

- automatic-review service with five statuses;
- human review queue/workbench;
- edit/approve/approve-after-edit/merge/hold/reject/batch actions;
- evidence, risk, missing field, dependency, duplicate, conflict, and backtestability display;
- permission and unavailable handling;
- audit records for every operation.

Forbidden:

- automatic formal publication;
- fabricating missing data or summaries;
- direct mutation through legacy rule-pool repository;
- starting Stage 5/6/8 behavior.

## 17. Per-Task Acceptance Criteria

RT-S4-002:

- deterministic fingerprints are stable across reruns;
- equivalent rules map to the same family or explicit parameter variants;
- conflicts are detected and visible;
- family membership records preserve source articles and evidence;
- duplicate rules are not repeatedly sent to backtest;
- fixed-set gate is enforced before mutation;
- canonical writer tests remain green.

RT-S4-003:

- every lifecycle transition is validated;
- user-facing states map clearly to persisted canonical states;
- every transition records actor, time, reason, before/after, and correlation id;
- retired/limited-use states do not appear as normal usable rules;
- compatibility state mapping does not fabricate formal status.

RT-S4-001:

- automatic review can classify low-risk, human-review-needed, not-backtestable, and reject-recommended candidates;
- low-risk rules can bulk enter pending backtest but cannot become formally usable automatically;
- high-risk, ambiguous, conflicting, parameter-edited, and strategy-entry rules require human confirmation;
- review UI shows evidence, automatic-review reasons, missing fields, data dependencies, duplicate/conflict info, and backtestability;
- all human actions are audited;
- user-facing error states are truthful and actionable.

RT-S4-001 frozen implementation refinements from repository evidence:

- `auto_pass` is reserved for low-risk non-entry rules with complete evidence and no duplicate/conflict/manual-review findings;
- `recommend_pass` is used for low-risk entry rules and exact-duplicate reuse cases that still require human confirmation or batch approval;
- `manual_review` is forced by conflict, similar/parameter-variant findings, ambiguity, inference, missing fields, Kaipan dependency, or post-edit review;
- `not_backtestable` and `recommend_reject` remain blocked/unavailable until human action and do not fabricate pending-backtest or usable states;
- `approve` / `approve_after_edit` / `merge` must propagate the caller correlation id through canonical `LifecycleEvent` audit rows, including duplicate reuse and new `RuleVersion` creation.
- `approve_low_risk` must pre-check the whole batch before mutation; eligible new low-risk RuleVersions move to `待回测`, while exact duplicates reuse the existing RuleVersion and do not create repeated backtest eligibility.

## 18. Test Strategy And Commands

Before every Stage 4 implementation Task:

```bash
../.venv/bin/python -m cli.main stage3-regression run --fixed-set
```

Focused backend/API tests to add or run as relevant:

```bash
../.venv/bin/python -m pytest tests/unit/services/test_stage2_writer_routing.py -q
../.venv/bin/python -m pytest tests/regression/stage3 tests/unit/stage3 tests/integration/test_stage3_single_article.py tests/integration/test_stage3_batch.py -q
../.venv/bin/python -m pytest tests/unit/rule_governance tests/integration/test_rule_governance.py -q
../.venv/bin/python -m pytest tests/api/routers/ui/test_rule_governance.py tests/api/routers/test_rule_pool.py tests/api/routers/ui/test_strategy_studio.py -q
../.venv/bin/python -m pytest tests/unit/db/test_migrations.py -q
```

Focused Web tests to add or run as relevant:

```bash
pnpm test -- src/pages/rules src/pages/articles/index.test.tsx src/pages/rule-pool/index.test.tsx
pnpm typecheck
```

Gate-level verification:

```bash
../.venv/bin/python -m compileall src api cli
git diff --check
```

If sandbox PostgreSQL socket access blocks a required CLI batch verification, rerun through the approved external path and record the sandbox limitation separately. Do not classify that sandbox-only restriction as a product defect without new evidence.

## 19. Migration, Rollback, And Data-Integrity Verification

Migration requirements:

- inspect existing tables and row counts before adding migrations;
- preserve existing canonical and legacy data;
- reject or report rows that cannot be safely mapped;
- record pre/post counts and conflict counts;
- make upgrades safe to rerun;
- provide downgrade/recovery rules that do not silently drop canonical rows;
- test fresh upgrade, existing-data upgrade, and downgrade/recovery path.

Rollback:

- normal rollback cannot turn `STAGE2_CANONICAL_WRITER_ENABLED=false` into supported operation;
- emergency rollback must be time-limited and explicitly authorized;
- no rollback path may restore retired legacy Prompt or writer fallback as formal.

## 20. Stage 4 Gate Evidence Requirements

Gate must include:

- Stage 3 fixed-set gate passing immediately before Stage 4 governance evidence;
- canonical writer and legacy write rejection evidence;
- migration upgrade/downgrade/recovery evidence if migrations are added;
- deterministic fingerprint/idempotency proof;
- duplicate/conflict/family test evidence;
- lifecycle transition and audit test evidence;
- automatic/human review API and UI test evidence;
- Web wording scan for affected Stage 4 surfaces;
- no active legacy writer fallback or dual-write path;
- no future-stage Prompt activation;
- truthful unavailable behavior for historical summaries and missing data;
- implementation logs updated with task status and residual risks.

## 21. Risks, Mitigations, And Explicit Non-Blocking Risks

Risks:

- legacy `rule_pool` and `strategy_studio` remain active compatibility surfaces;
- direct CLI/job review paths can bypass fixed-set gate unless guarded;
- `RuleFamilyMembership` may need additional durable audit or merge metadata;
- current Web surfaces contain stale technical terminology;
- `RuleVersion.source_candidate_id` duplicate prevention is app-layer only.

Mitigations:

- freeze canonical governance contracts before code changes;
- enforce fixed-set gate in every mutation entry point;
- use `LifecycleEvent` and add migration only if current schema cannot represent required audit data;
- convert legacy write paths to canonical service routing or read-only compatibility;
- add tests for all direct API, job, and CLI mutation paths.

Accepted non-blocking risks:

- sandbox cannot open the local PostgreSQL socket for the batch CLI; approved external rerun passed in Stage 3;
- older revisions without frozen summaries remain unavailable by design;
- no uncommitted Stage 3 Gate repair changes are present locally; accepted repairs are in HEAD.

## 22. Decisions Made During Bootstrap

- Stage 4 scope is RT-S4-001, RT-S4-002, and RT-S4-003 only.
- Execute RT-S4-002 before RT-S4-003, then RT-S4-001.
- Existing `RuleVersion`/`RuleFamily` tables are the canonical starting point; do not create a parallel formal rule schema.
- `rule_pool` and `strategy_studio` are compatibility/history surfaces, not Stage 4 formal governance authorities.
- Fixed-set gate must precede all Stage 4 governance mutations, including API, jobs, workers, scheduler, and CLI paths.
- Missing `AI-Conversation-Project-Constraints.md` is resolved by current split constraint files and does not require escalation.
- Product-plan older stage numbering is non-authoritative for Stage 4 task scope.

## 23. Unresolved Issues Requiring Escalation

None.

No `ESCALATION_REQUIRED` issue was found. The remaining gaps can be resolved through safe implementation choices consistent with accepted contracts.

## 24. Recommended Prompt And Model Strategy

Bootstrap and Stage Gate should use Parent `gpt-5.5`.

Implementation should use Parent `gpt-5.4` with at most one bounded `gpt-5.4-mini` executor for well-scoped mechanical implementation after contracts are frozen.

Recommended first implementation prompt:

```text
You are the Parent Orchestrator for trade-strategy-ai Stage 4.

Execute RT-S4-002 only: Rule fingerprint and RuleFamily.

Before coding, read:
1. docs/Trade-Refactor-TaskList.md
2. docs/AI-Conversation-Templates.md
3. docs/AI-Conversation-Project-Constraints-1.md
4. docs/AI-Conversation-Project-Constraints-2.md
5. docs/AI-Conversation-Task-Matrix.md
6. docs/Refactor-Implementation-Log.md
7. docs/refactor-implementation-logs/stage-4.md
8. docs/refactor-implementation-plans/stage-4-implementation-plan.md
9. Stage 3 plan/log only as needed for accepted invariants

Preserve all Stage 3 invariants: canonical writer only, no dual-write, fixed-set gate before rule-governance mutation, revision-bound summaries, truthful unavailable semantics, no legacy fallback.

Scope:
- implement deterministic rule fingerprints;
- implement duplicate/similar/conflict detection;
- implement RuleFamily and membership runtime using canonical tables;
- preserve source article, ArticleRevision, evidence, PromptRun, and RuleCandidate provenance;
- prevent repeated backtest of duplicate rules;
- add focused backend/API tests and any required safe migration tests;
- update docs/Refactor-Implementation-Log.md and docs/refactor-implementation-logs/stage-4.md.

Do not implement RT-S4-001 workbench or RT-S4-003 lifecycle beyond what is required to preserve existing contracts.
Do not commit or push unless explicitly instructed.
```
