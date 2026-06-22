# Stage 11 Bootstrap / Implementation Plan

## Status

- Stage: `Stage 11 系统管理、自动化与告警`
- Bootstrap status: `[x] 已完成`
- Implementation status: `[ ] 未开始`
- Bootstrap date: `2026-06-22`
- Parent model requested by user: `gpt-5.5`

This plan freezes Stage 11 contracts only. It does not authorize production code
implementation, scheduler jobs, automation runtime, alerting runtime, UI changes,
legacy route retirement, business data mutation, or Stage 12 work.

## Entry Verification

- Stage 10 Gate: `ACCEPTED`.
- `RT-S10-001` / `RT-S10-002` / `RT-S10-003` / `RT-S10-004`: accepted.
- Stage 11 before this bootstrap: not started.
- Stage 12 before this bootstrap: not started.
- Working tree before bootstrap edits: clean.
- Baseline commit: `351e58581d62850d4155800ad38935fad05cb3a2`.
- Bootstrap allowed edits: this plan, Stage 11 log, and main implementation log only.

## Delegation

The Parent used `refactor-orchestrator` and explicitly delegated two read-only
Explorer lanes because Stage 11 is read-heavy and crosses independent backend and
frontend surfaces:

- Backend Explorer: system/config/ops, scheduler/recovery, job/workflow/prompt
  runs, cost, data-time semantics, backup/restore, audit, tests.
- Frontend Explorer: route/navigation/visibility, system pages, API clients/types,
  error state components, business pages, legacy terminology, tests.

No Executor was used. Stage 11 contracts, task order, acceptance criteria, risk
classification, and final bootstrap decision remain Parent-owned.

## Existing Code Map

### System Management / Profile / Config

- `web/src/app/route-config.tsx` already defines canonical `/system` routes and
  hides compatibility routes from primary navigation.
- `web/src/pages/system/*` and `web/src/features/system-management/*` provide
  existing system/admin surfaces.
- `api/routers/ui/system.py`, `api/routers/ui/settings.py`,
  `api/routers/ui/profiles.py`, `api/routers/ui/ops.py`,
  `api/routers/ui/system_data.py`, `api/routers/ui/security_audit.py`,
  `api/routers/ui/job_audits.py`, and `api/routers/ui/data_audits.py` expose
  existing system-facing APIs.
- `src/services/system_service.py`, `src/services/config_profile_service.py`,
  `src/services/runtime_config.py`, and `src/services/config_migration_service.py`
  are current profile/config/service entry points.

### Automation / Recovery / Scheduling

- `src/services/data_scheduling_service.py` defines the formal
  `system-data-operation` lane and data operation windows.
- `src/services/job_service.py` persists jobs, retries, stale-job recovery,
  runtime state, heartbeat, progress, and audit events.
- `src/services/ops_service.py` exposes backup/restore/stale-job recovery wrappers.
- `src/services/article_pipeline_schedule_service.py` is still an in-memory
  scheduler compatibility path and must not become the Stage 11 durable scheduler
  contract without an explicit implementation task.

### Observability / Run Tracking

- `jobs` and `job_audit_events` track legacy/compat operational runs.
- `workflow_runs` and `workflow_run_steps` track workflow-level runs and step
  status/timing/error.
- `prompt_runs` tracks prompt/model/schema/input hash/tokens/cost/retry metadata.
- `backtest_runs` and `backtest_results` track snapshot-bound backtest provenance.
- Daily business records carry `source_run_id` in selected places, but no unified
  cross-surface run trace contract is currently formalized.

### Cost / Incremental Control

- `ArticleRevision.content_hash` and prompt-runtime cache lookup support article
  dedupe and prompt-result reuse.
- `PromptRun.token_usage`, `PromptRun.cost_amount`, and `PromptRun.cost_currency`
  persist call-level cost data.
- Backtest request/result fingerprints and dataset/market snapshot fingerprints
  support reuse, but no formal Stage 11 cost/budget summary or warning surface is
  currently frozen.

### Data Time Semantics

- `MarketSnapshot` has `trade_date`, `slot`, `captured_at`, `available_at`,
  `effective_at`, source/provider fields, and quality status.
- `MarketSnapshotSection` has section-level `trade_date`, `slot`, `provider`,
  `source_time`, `captured_at`, `available_at`, and quality status.
- `DatasetSnapshot` has `trade_date`, date range, manifests, `available_at`,
  `frozen_at`, fingerprints, and lifecycle state; it does not yet uniformly carry
  all Stage 11 required fields such as `captured_at`, `effective_at`, and `slot`.
- `BacktestApplicationService` already enforces snapshot binding and decision-time
  availability in Stage 6 paths.

### Error Handling

- Backend services commonly return `ServiceResult(status, message, payload,
  warnings)`.
- Frontend `BusinessPageShell`, `ProductPageAdapter`, and `ErrorState` already
  support happened/impact/guidance-style display in many pages.
- Remaining compatibility pages can still expose internal terms such as `Job`,
  `Workflow`, `Pipeline`, `Artifact`, `Provider`, `Schema`, `config_path`,
  `run_id`, or `prompt_run_id`.

## Frozen Stage 11 Contracts

### Global Stage Contract

- Stage 11 goal: concentrate low-frequency management capabilities under System
  Management while keeping daily business pages simple.
- Ordinary users must not need System Management for normal daily pre-market,
  post-market, research, rule, author-profile, or strategy work.
- Admin users must be able to locate and repair data, scheduling, runtime,
  backup/restore, permission, audit, and failure issues.
- Stage 11 must not make legacy `Job` / `Workflow` / `Pipeline` / `Artifact`
  records new formal business inputs.
- `config_path` must not return as a Web formal input. It may remain a hidden
  compatibility/CLI field until retirement conditions are met.
- Missing data remains `unavailable`, `partial`, `conflict`, `invalid`, or
  `degraded`; it must not become success, false, zero, or an empty success state.
- Stage 11 must not mutate formal strategy, rule, profile, or current pointers
  except through already accepted governance paths.
- Automation must not silently publish, overwrite, approve, or execute
  user-impacting decisions.
- Stage 11 must not retire legacy routes unless explicitly scoped by a later task.
- Stage 12 must not start from Stage 11 implementation sessions.

### RT-S11-001 System Management Entry

System Management groups these categories:

- `Profile 配置`
- `数据源`
- `数据与调度`
- `任务运行`
- `失败与告警`
- `数据库与备份`
- `权限与审计`

Existing pages to move or consolidate under System Management:

- Profile compatibility pages: `/profiles`, `/profiles/import`,
  `/profiles/:profileId`, `/profiles/:profileId/edit`,
  `/profiles/:profileId/snapshots/:snapshotId`.
- Data/source pages: `/market`, `/market/kaipan`, `/market/ohlcv`,
  `/market/snapshots`, `/market/datasets`.
- Runtime pages: `/jobs`, `/jobs/:jobId`, `/workflows`,
  `/workflows/:workflowId/run`, `/artifacts`, `/artifacts/:artifactId`,
  `/alerts`.
- Existing system/admin pages: `/system/status`, `/system/configuration`,
  `/system/data`, `/system/runs`, `/system/audit`, `/system/users`,
  `/system/health`, `/system/db-migrate`, `/system/backup`.
- Legacy redirects: `/admin`, `/admin/audit`, `/settings`, `/system/restore`.

Business pages that must stay outside System Management:

- `/`, `/research`, `/rules`, `/authors`, `/strategies`, `/daily`,
  `/daily/pre-market`, `/daily/after-close`.

Visibility contract:

- Ordinary authenticated users may see business status and simple repair entry
  points when the repair affects their workflow.
- Admin/operator users may see System Management details according to existing
  role policy.
- Admin-only details include user management, security audit, system health,
  database migration, backup/restore, raw trace IDs, prompt cost details, and
  technical recovery actions.

### RT-S11-002 Automation And Recovery

Freeze boundaries only; do not implement scheduling in bootstrap.

Covered automation domains:

- Scheduled tasks.
- Failure retry.
- Resumable runs.
- Data backfill.
- LLM batch recovery.
- Night low-priority jobs.
- Health checks.

Safe retry/idempotency rules:

- Every retried operation must have a stable idempotency key or fingerprint.
- Retry must not create duplicate formal rules, profiles, strategies, daily
  plans, reviews, or proposals.
- Retry must preserve prior failed evidence and append new attempt evidence.
- Retry upper bounds and backoff policy must be visible to admins.
- Resume must start from the last safely completed step and must not skip
  validation of upstream data availability.
- Backfill must write immutable snapshot/revision evidence and must not rewrite
  historical availability times.
- LLM batch recovery must reuse `input_hash`, prompt version, schema version,
  model, and retry count; stale cache states must remain visible.

Automation action levels:

- Notify only: user-impacting decisions, missing formal data, governance review,
  pointer changes, publish/approve/archive/reject actions.
- Automatic retry: transient provider/network/runtime failures with stable
  idempotency and no formal asset mutation.
- Admin approval required: data backfill, restore, migration, bulk LLM recovery,
  scheduler enable/disable, retry after max retry reached, and any action that
  could alter future business outputs.

### RT-S11-003 Observability And Run Tracking

`run_id` contract:

- Every business run must have a stable `run_id`.
- A business run may link to legacy job IDs, workflow run IDs, prompt run IDs,
  backtest run IDs, dataset snapshot IDs, and daily object IDs, but none of those
  legacy IDs become the user-facing formal business input.
- `run_id` must be stable across resume/retry attempts; attempt IDs or retry
  counts distinguish attempts.

Step contract:

- Each step records `step_id`, business label, status, started_at, finished_at,
  duration, error, retry_count, input references, output references, and repair
  guidance.
- Ordinary users see business status and next action.
- Admins see technical details, linked records, trace IDs, payload fingerprints,
  and raw diagnostic metadata.

Prompt-call contract:

- Prompt calls record `run_id`, model, provider, prompt version, schema version,
  input hash, validation state, retry count, tokens, cost, started/completed time,
  and linked business object/version.

Data-fetch contract:

- Data fetch records source, provider, date range, trade date, slot, coverage,
  captured_at, available_at, effective_at, quality status, missing ranges, and
  repair guidance.

Backtest contract:

- Backtests record dataset snapshot, data fingerprints, rule version/fingerprint,
  market-state model version, code/engine version, decision-time policy,
  reproducibility fingerprint, coverage, and limitations.

### RT-S11-004 Cost And Incremental Control

Contracts:

- Article content hash and dedupe use canonical content hash/version evidence.
- Prompt result cache key includes prompt name, prompt version, schema version,
  model, input hash, and retry count.
- Batch concurrency limits must be explicit per task type and visible to admins.
- Retry upper bounds must be enforced and displayed.
- Incremental profile updates process only changed article/revision/evidence
  groups and must not overwrite published profile versions directly.
- Rule-family backtest reuse requires rule family fingerprint, rule version
  fingerprint, dataset fingerprint, market-state model version, engine version,
  and decision-time policy match.
- Metric cache requires input fingerprint, result fingerprint, calculation
  version, and stale/unavailable state.
- LLM cost statistics aggregate from persisted prompt runs and expose budget
  warnings without blocking already accepted governance flows unless a later task
  defines an enforcement policy.

Cache invalidation:

- Invalidate on content hash change, prompt/schema/model change, validation
  policy change, market-state model version change, dataset/snapshot fingerprint
  change, rule/profile/strategy version change, or code/engine version change
  when the calculation depends on it.
- Stale, missing, partial, or unavailable cache states must be displayed as such,
  never as successful reuse.

### RT-S11-005 Data Time Semantics

Required fields for relevant core data objects:

- `trade_date`
- `available_at`
- `captured_at`
- `effective_at`
- `source`
- `slot`

Point-in-time contract:

- Pre-market may use only data whose `available_at` is at or before the
  pre-market decision cutoff.
- Post-market may use only data whose `available_at` is at or before the
  post-market review cutoff.
- Backtest may use only immutable snapshots and point-in-time availability
  allowed by its decision-time policy.
- Later-filled data must retain its true `captured_at` / `available_at` and must
  not be treated as if it was available earlier.
- Missing or late data must surface as unavailable/partial/degraded with impact
  and repair guidance.

Validation/UI/admin visibility:

- Business users see whether data was available for the decision and what is
  affected.
- Admins see source, slot, captured_at, available_at, effective_at, coverage,
  missing ranges, and linked snapshot/fingerprint details.

### RT-S11-006 Gray Migration And Rollback

Rollout path:

```text
新旧链路对照
→ 新链路只读展示
→ 小范围启用
→ 新链路成为默认
→ 旧入口只读
→ 最终退役
```

Rollback safe means:

- Database: migration has upgrade evidence, recovery/rollback path, pre/post
  counts, rejected/conflicted rows, and no silent data loss.
- Prompt: prompt/schema versions and raw outputs are preserved; rollback can
  select the previous prompt/schema contract without deleting new evidence.
- Batch article processing: idempotent item state, input hash, prompt run,
  validation state, retry count, rejected/conflicted items, and resume point are
  preserved.
- UI/routes: legacy routes remain compatibility-only until Stage 12 or an
  explicitly scoped retirement task.

### RT-S11-007 User-Friendly Errors

Error contract fields:

- `happened`: what happened.
- `affected`: what is affected.
- `repair_guidance`: what to do next.

Display contract:

- Normal users see actionable business explanations, impact, and next action.
- Admin users may additionally see technical details, trace IDs, linked run IDs,
  raw payload references, and stack traces only inside admin diagnostic detail.
- No raw exception-only UI.
- No `Job failed` as the only user-facing message.
- Internal terms are allowed only in admin technical detail where they are
  necessary for repair and not presented as ordinary business inputs.

## RT-S11 Task Order

1. `RT-S11-001 系统管理入口`
2. `RT-S11-007 用户友好错误`
3. `RT-S11-003 可观测性和运行追踪`
4. `RT-S11-002 自动化和恢复`
5. `RT-S11-005 数据时间语义`
6. `RT-S11-004 成本与增量控制`
7. `RT-S11-006 灰度迁移和回滚`

Reasoning:

- Entry and error contracts should be visible before adding more admin detail.
- Observability must precede automation so recovery and scheduler behavior is
  traceable from the start.
- Time semantics should be hardened before cost/cache reuse can be trusted.
- Gray migration/rollback is last because it depends on the chosen system,
  observability, automation, time, and cache contracts.

## Task Combination Rules

- `RT-S11-001` + `RT-S11-007` may be implemented in one Task Session if changes
  are scoped to route grouping, copy, error display, and tests.
- `RT-S11-002` + `RT-S11-003` may be implemented in one Task Session only
  serially, with observability contracts implemented first.
- `RT-S11-004` + `RT-S11-005` may be implemented in one Parent Session across
  multiple batches, but time-semantics hardening must precede cache/cost reuse.
- `RT-S11-006` must be implemented separately and last.
- Do not combine gray migration with the behavior being migrated.
- Do not combine Stage 11 with Stage 12.

## Per-Task Acceptance Criteria

### RT-S11-001

- System Management groups all required categories.
- Existing profile/data/runtime/failure/backup/audit pages have a clear System
  Management home or compatibility route.
- Business pages remain outside System Management and primary navigation remains
  business-first.
- Ordinary-user and admin-user visibility is tested.
- `config_path`, Job/Workflow/Pipeline/Artifact terms are not exposed as ordinary
  business inputs.
- No production scheduler/automation/alert runtime is introduced.

### RT-S11-002

- Boundaries for scheduled tasks, retry, resume, backfill, LLM batch recovery,
  low-priority jobs, and health checks are implemented only after observability.
- Retry/resume/backfill operations are idempotent and bounded.
- Automation action level is explicit: notify-only, auto-retry, or admin approval.
- Automation cannot publish, overwrite, approve, or execute user-impacting
  decisions.
- Tests cover retry limits, resume points, stale/failed state, and admin approval
  requirements.

### RT-S11-003

- Every formal business run has or exposes stable `run_id`.
- Steps record status, start/end time, error, retry count, and repair guidance.
- Prompt calls expose model, prompt/schema versions, tokens, cost, retry, and
  linked business object.
- Data fetches expose source/date range/coverage/time fields.
- Backtests expose snapshot/rule/market-state/code-version provenance.
- Normal users see business status; admins see technical details.

### RT-S11-004

- Content hash/dedupe, prompt cache, batch concurrency, retry upper bounds,
  incremental profile updates, rule-family backtest reuse, metric cache, and LLM
  cost statistics have explicit contracts and tests.
- Cache keys and invalidation include all required fingerprints/versions.
- Stale/unavailable/partial cache states remain visible and are not displayed as
  success.
- Budget warnings are visible to admins and do not silently block or mutate
  governance flows unless explicitly configured.

### RT-S11-005

- Required time fields are present or explicitly mapped for relevant core data
  objects.
- Pre-market, post-market, and backtest flows enforce point-in-time availability.
- Later-filled data is not treated as earlier available data.
- Missing/late data shows unavailable/partial/degraded impact and repair guidance.
- Admin UI/API exposes source, slot, coverage, timestamps, and snapshot details.

### RT-S11-006

- Rollout states are represented and visible for applicable migrations.
- Database, Prompt, and batch article processing have rollback or recovery paths.
- Legacy routes remain compatibility-only and are not retired unless separately
  authorized.
- Tests cover upgrade/recovery evidence, read-only legacy state, and no duplicate
  formal source-of-truth.

### RT-S11-007

- User-facing errors include happened, affected, and repair guidance.
- Admin diagnostics may include trace IDs and technical detail.
- Raw stack traces and `Job failed`-only messages are absent from normal UI.
- Permission denied, unavailable, partial, degraded, invalid, and conflict states
  are tested.
- Business pages do not require users to understand internal developer terms.

## Stage 10 Residual Risk Classification

- Execution supplement missing: Stage 11 automation/recovery observes and may
  repair/resume execution evidence, but execution supplement itself remains a
  future execution supplement task unless explicitly authorized. Stage 11 must
  keep execution-specific fields unavailable rather than false/success.
- Caller-supplied `post_close_market_state_id`: belongs to Stage 11
  observability/time-semantics hardening. Stage 11 should resolve or validate
  canonical market-state identity and preserve unavailable/invalid states.
- OpenAPI response-schema assertions partial: Stage 11 hardening for system and
  observability APIs; final Stage 12 Gate should still run full contract review.
- `/strategies/after-close` compatibility route remains: Stage 12 retirement
  follow-up. Stage 11 may show compatibility visibility in System Management but
  must not retire the route.
- Browser E2E not run: final Stage 12 E2E unless a focused Stage 11 UI task
  changes the relevant page and requires targeted browser verification.

## Recommended Model / Session For RT-S11-001

- Recommended session: `gpt-5.4` Task Implementation session.
- Use 0-1 mini Executor only if the write scope is bounded to frontend route/page
  grouping plus focused tests.
- Escalate to `gpt-5.5` if RT-S11-001 needs new authorization policy, route
  retirement, canonical run source-of-truth changes, or changes to formal data
  inputs.

## Bootstrap Decision

`READY`

Stage 11 implementation may start only after explicit user authorization for
`RT-S11-001` or a permitted combined `RT-S11-001 + RT-S11-007` Task Session.
