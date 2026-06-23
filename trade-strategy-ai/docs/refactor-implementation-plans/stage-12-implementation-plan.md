# Stage 12 Bootstrap / Implementation Plan

## Status

- Stage: `Stage 12 旧入口退役与最终交付`
- Bootstrap status: `[x] 已完成`
- Implementation status: `[ ] 未开始`
- Bootstrap date: `2026-06-23`
- Parent model requested by user: `gpt-5.5`

This plan freezes Stage 12 contracts only. It does not authorize production code
implementation, legacy route retirement, frontend/backend/database runtime
behavior changes, E2E execution, or user documentation generation.

## Entry Verification

- Stage 11 Gate: `ACCEPTED`.
- `RT-S11-001` / `RT-S11-002` / `RT-S11-003` / `RT-S11-004` / `RT-S11-005` / `RT-S11-006` / `RT-S11-007`: accepted.
- Stage 12 before this bootstrap: not started.
- Working tree before bootstrap edits: clean.
- Branch: `main`.
- Baseline commit: `6d15a217694569008cb39ad194871c119de66a58`.
- Bootstrap allowed edits: this plan, Stage 12 log, and main implementation log only.

## Delegation

No subagent is required for Bootstrap. Optional read-only helpers may be used in
later Stage 12 tasks for route inventory, E2E evidence collection, or
documentation review, but Parent remains responsible for retirement scope,
task order, risk classification, acceptance decisions, and final Stage 12 Gate.

## Stage 12 Goal

Complete old-entry retirement, full end-to-end acceptance, and user delivery for
the formal product flow:

```text
文章导入
→ 提取规则
→ 审核规则
→ 回测
→ 生成规则适用性
→ 生成作者画像
→ 发布策略
→ 生成盘前计划
→ 完成盘后复盘
→ 生成优化建议
```

## Existing Retirement Inventory

The current route source of truth is `web/src/app/route-config.tsx`.

Formal retained product entries:

- `/`
- `/research`, `/research/articles`, `/research/add`, `/research/results`
- `/rules`, `/rules/review`, `/rules/library`, `/rules/backtests`, `/rules/results`
- `/authors`
- `/strategies`, `/strategies/candidates`
- `/daily`, `/daily/overview`, `/daily/pre-market`, `/daily/after-close`
- `/system`, `/system/status`, `/system/configuration`, `/system/data`,
  `/system/runs`, `/system/audit`, `/system/users`, `/system/health`,
  `/system/db-migrate`, `/system/backup`

Stage 12 retirement candidates:

- Old workflow main entries:
  - `/workflows`
  - `/workflows/:workflowId/run`
  - compatibility redirects `/workflows/pre-market`,
    `/workflows/pre-market/run`, `/workflows/after-close`,
    `/workflows/after-close/run`
- Developer-facing job main entries:
  - `/jobs`
  - `/jobs/:jobId`
- Independent artifact main entries:
  - `/artifacts`
  - `/artifacts/:artifactId`
- Duplicate market data entries:
  - `/market`
  - `/market/snapshots`
  - `/market/datasets`
  - `/market/kaipan`
  - `/market/ohlcv`
- Duplicate strategy/backtest entries:
  - `/backtest`
  - `/backtest/regime`
  - `/backtest/candidates`
  - `/strategies/pre-market`
  - `/strategies/after-close`
- Migrated legacy pages:
  - `/dashboard`
  - `/articles`, `/articles/run`, `/articles/list`, `/articles/quality`,
    `/articles/results`
  - `/rule-pool`, `/rule-pool/:ruleId`
  - `/persona`
  - `/profiles`, `/profiles/import`, `/profiles/:profileId`,
    `/profiles/:profileId/edit`, `/profiles/:profileId/snapshots/:snapshotId`
  - `/alerts`
  - `/admin`, `/admin/audit`, `/system/restore`, `/settings`

Long-term retained canonical or compatibility states:

- `/login`, `/`, `/system/*` canonical admin pages, and `*` 404 are not
  retirement candidates.
- Deep-link detail pages may remain read-only only when deletion would remove
  evidence required for traceability, rollback, audits, prompt history, data
  provenance, or migration recovery.

## Frozen Stage 12 Contracts

### Global Contract

- Stage 12 must not create a second formal source of truth for routes, rules,
  schemas, profiles, strategies, prompt history, data provenance, backtest
  results, daily plans, proposals, or documentation.
- Legacy route retirement may happen only after the new formal entry is verified
  for the same user action and evidence access.
- Ordinary users must not see developer-tool main entries.
- User-facing docs must not require understanding `Job`, `Workflow`, `Pipeline`,
  `Artifact`, `Provider`, `Schema`, `config_path`, `prompt_run_id`, or `run_id`.
- Missing, partial, unavailable, degraded, invalid, and conflict states remain
  truthful in product UI, E2E evidence, logs, and documentation.
- Stage 12 must preserve accepted governance paths for rules, author profiles,
  strategies, daily plans, and optimization proposals.
- Stage 12 must not remove evidence required for traceability, rollback, audits,
  prompt history, data provenance, or migration recovery.
- Stage 12 must not change formal object lifecycle semantics unless a separate
  gpt-5.5 contract escalation explicitly freezes the change.

### Deletion Versus Hiding Criteria

Delete a legacy route or page only when all are true:

- The formal replacement route covers the same user goal with business Chinese
  labels, clear inputs, processing state, outputs, next action, and truthful
  error states.
- Historical records remain reachable from the formal page or system-management
  diagnostics without making the legacy page a main entry.
- Existing tests or new tests prove the old path no longer appears in primary
  navigation, section navigation, normal user journeys, or documentation.
- Reference scans prove imports, links, tests, and docs have been migrated or
  intentionally removed.
- Rollback/recovery evidence does not depend on the route component being
  deleted.

Hide or keep read-only compatibility instead of deleting when any are true:

- The route is needed to inspect historical run evidence, prompt output, data
  migration evidence, backtest provenance, audit history, or rollback recovery.
- External links or stored records still point to the route and no formal
  resolver exists yet.
- Deletion would obscure a partial, conflict, invalid, or degraded state.
- The new formal entry does not yet expose equivalent evidence or repair action.

Compatibility pages that remain after `RT-S12-001` must be:

- hidden from ordinary navigation,
- read-only or redirect-only,
- clearly marked as compatibility/admin diagnostics,
- excluded from user-facing documentation as a normal workflow,
- listed with explicit remaining retirement condition in the Stage 12 log.

### Rollback And Recovery Expectations

- Route removal must be reversible by restoring the previous route entry and
  tests without data migration or data loss.
- Deleted route components may be removed only after import/reference scans pass.
- Historical IDs must resolve through formal pages or system diagnostics before
  any detail page is deleted.
- Stage 12 must preserve Stage 2 migration reports, Stage 3 prompt run evidence,
  Stage 6 backtest/result provenance, Stage 7 profile evidence, Stage 8 strategy
  audit history, Stage 9 daily plan traceability, Stage 10 post-market review
  evidence, and Stage 11 rollout/recovery evidence.

## Task Order And Combination Rules

1. `RT-S12-001 旧入口退役`
2. `RT-S12-002 端到端验收`
3. `RT-S12-003 用户文档`

Combination rules:

- `RT-S12-001` must be single and separate.
- `RT-S12-002` and `RT-S12-003` may be combined only after `RT-S12-001` is
  accepted, and only if E2E evidence and documentation updates are kept clearly
  separated in commits, logs, and acceptance review.
- Bootstrap must not be combined with any implementation task.

## Task Cards

### RT-S12-001 旧入口退役

**Risk:** M3.

**Goal:** Remove, hide, or read-only-retain legacy main entries so ordinary users
only see the formal product flow and System Management.

**Frozen contract:**

- Retire only route/page entry points, navigation exposure, redirects, imports,
  tests, and documentation references in this task.
- Do not delete databases, canonical records, prompt evidence, migration reports,
  backtest evidence, strategy/profile/rule audit history, daily plans, or
  optimization proposals.
- Do not change frontend/backend/database runtime behavior beyond route/page
  exposure required for retirement.
- Do not mutate formal governance state.

**Allowed paths:**

- Edit `web/src/app/route-config.tsx`, related route tests, legacy page imports,
  and documentation references.
- Convert candidates to redirects, hidden read-only diagnostics, or deletion
  according to the deletion/hiding criteria above.
- Add route tests proving primary navigation and normal user journeys do not
  expose developer-tool main entries.

**Forbidden paths:**

- Creating a second route registry.
- Replacing formal pages with compatibility pages.
- Removing evidence objects or migration/recovery logs.
- Retiring a legacy path when the formal replacement is unverified.
- Starting E2E acceptance or user docs as part of this task.

**Acceptance criteria:**

- Old workflow main entry, developer-facing Job main entry, independent Artifact
  main entry, duplicate market data entry, duplicate strategy/backtest entry, and
  migrated legacy pages are deleted, redirected, hidden, or explicitly retained
  read-only with a logged reason.
- Primary navigation and section navigation show only formal product entries and
  System Management entries allowed by role.
- Ordinary user routes no longer expose `Job`, `Workflow`, `Pipeline`,
  `Artifact`, `Provider`, `Schema`, `config_path`, `prompt_run_id`, or `run_id`
  as workflow concepts or required inputs.
- Every retained compatibility/read-only route has a formal target, owner,
  remaining retirement condition, and rollback/evidence reason in the Stage 12
  log.
- Focused route/navigation/frontend tests pass.
- Backend/API tests pass if route changes affect API clients or system
  diagnostics.
- `git diff --check` passes.

**Stop and escalate if:**

- A legacy route is the only way to view required audit/provenance evidence.
- A formal replacement route lacks equivalent evidence or repair action.
- Deletion would require changing formal schemas, lifecycle states, governance
  paths, or data recovery contracts.

### RT-S12-002 端到端验收

**Risk:** M3.

**Goal:** Prove the complete formal product journey works with real data and no
legacy formal inputs.

**Frozen path:**

```text
文章导入
→ 提取规则
→ 审核规则
→ 回测
→ 生成规则适用性
→ 生成作者画像
→ 发布策略
→ 生成盘前计划
→ 完成盘后复盘
→ 生成优化建议
```

**Acceptance criteria:**

- The E2E path starts from formal UI/API entries and does not require ordinary
  users to navigate to developer-tool routes.
- Each step records or displays the relevant formal ID/version/fingerprint:
  article revision, prompt/schema version, rule version, dataset snapshot,
  market snapshot/state model version, backtest run/result, applicability
  profile, author profile versions, strategy version, daily rule selection,
  daily strategy instance, trading day plan, post-market review, and proposal
  IDs.
- Backtests remain snapshot-bound and do not call live Providers during
  execution.
- Missing/partial/unavailable/degraded/invalid/conflict states are displayed as
  such, with happened/impact/remediation guidance.
- Strategy, rule, author-profile, daily-plan, and proposal governance paths are
  preserved; daily or single-day results do not overwrite formal assets.
- Browser E2E, backend/API tests, frontend tests, migration verification, prompt
  regression tests, typecheck, lint or targeted lint, and `git diff --check`
  complete with recorded results.
- Any unrun full-suite test is listed with reason, replacement evidence, and
  residual risk.

**Stop and escalate if:**

- The formal journey still depends on a legacy Job/Workflow/Artifact page as a
  required user action.
- A required traceability ID/version/fingerprint cannot be proven.
- E2E requires changing frozen governance or data-source contracts.

### RT-S12-003 用户文档

**Risk:** M2, elevated to M3 if docs reveal or depend on internal tooling.

**Goal:** Deliver user-facing documentation that matches the final UI and does
not require developer terminology.

**Required deliverables:**

- 快速开始
- 完整使用手册
- 首次初始化指南
- 每日盘前说明
- 每日盘后说明
- 数据不足和失败处理说明
- 管理员运维指南

**Documentation location contract:**

- Formal user documents must be placed under `docs/`.
- Documentation must not contain local absolute paths.
- Documentation must not create a second formal TaskList, schema source,
  governance source, or route source.

**Acceptance criteria:**

- Documents use business Chinese and describe what the user should do, what the
  system does, what output is produced, and what the next action is.
- Ordinary-user docs avoid `Job`, `Workflow`, `Pipeline`, `Artifact`,
  `Provider`, `Schema`, `config_path`, `prompt_run_id`, and `run_id`.
- Admin docs may mention technical diagnostics only as administrator-facing
  details and must not make them normal-user prerequisites.
- Docs describe missing, partial, unavailable, degraded, invalid, and conflict
  states truthfully, including impact and repair actions.
- Docs match the final Stage 12 route/navigation state after `RT-S12-001`.
- Documentation review includes terminology grep and link/path validation.

**Stop and escalate if:**

- Documentation requires an ordinary user to follow retired or developer-facing
  routes.
- Documentation contradicts accepted governance paths or formal data-source
  contracts.

## Residual Risks Inherited From Stage 11

| Risk | Stage 12 classification | Required handling |
| --- | --- | --- |
| Legacy compatibility pages still contain internal terms and legacy implementation details. | Blocking for `RT-S12-001` until each page is deleted, redirected, hidden, or explicitly retained read-only with a reason. | Route inventory, terminology grep, navigation tests, retained-compatibility register. |
| Stage 2 migration report files and historical PromptRun evidence may be absent in some environments. | Non-blocking if displayed as `partial` / `unavailable`; blocking if retirement removes the only evidence path or docs imply proof exists. | Preserve recovery evidence paths; E2E/docs must state truthful unavailable states. |
| `DatasetSnapshot` lacks independent persisted `captured_at` / `slot` columns. | Non-blocking unless Stage 12 attempts to change data-time schema. | Keep unknown fields truthful; do not forge history; record any E2E limitation. |
| Browser E2E and full all-repo lint were not run in Stage 11. | Blocking for final Stage 12 Gate unless replaced by documented scoped evidence and accepted residual risk. | Run final E2E and affected suites during `RT-S12-002`; document any unrun full suite. |
| Stage 10 OpenAPI response-schema assertions were partial. | Stage 12 Gate hardening item. | Include full or targeted contract review in E2E verification. |
| `/strategies/after-close` compatibility route remains. | Blocking for `RT-S12-001` unless explicitly retained read-only with reason. | Retire or retain according to formal `/daily/after-close` verification. |

## Verification Strategy

Bootstrap verification:

- Documentation-only diff review.
- Confirm Stage 11 Gate and all Stage 11 tasks are accepted.
- Confirm Stage 12 was not previously started.
- Confirm production code is unchanged.
- Confirm Stage 12 task order and acceptance criteria are explicit.
- Run `git diff --check`.

Implementation verification for later tasks:

- Backend/API: focused pytest for affected UI APIs, canonical services, route
  diagnostics, E2E setup helpers, and governance guards.
- Frontend: route-config, navigation, auth/visibility, formal page, retired-route,
  and state-display tests.
- Migration/recovery: verify no evidence required for Stage 2-11 traceability is
  deleted; run migration checks if any migration-related code is touched.
- Prompt regression: run fixed prompt regression set when E2E exercises or
  documents prompt-dependent flows; do not modify prompts in Stage 12 unless a
  separate task freezes that change.
- Browser E2E: execute the complete formal journey in `RT-S12-002`, capturing
  evidence for inputs, processing state, outputs, next actions, and traceability.
- Documentation: terminology grep, route/link validation, user/admin audience
  separation, and consistency check against final UI.

## Bootstrap Decision

`Stage 12 Bootstrap READY`

Next allowed action: `RT-S12-001 旧入口退役` only, as a separate task after user
authorization. Do not start `RT-S12-002` or `RT-S12-003` until `RT-S12-001` is
accepted.
