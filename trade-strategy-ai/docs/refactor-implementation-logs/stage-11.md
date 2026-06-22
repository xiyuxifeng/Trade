# Stage 11 系统管理、自动化与告警实施日志

## Current Snapshot

- Stage：`Stage 11 系统管理、自动化与告警`
- 当前活动：`RT-S11-001 系统管理入口`
- 当前状态：`RT-S11-001 已接受；Stage 11 仍在进行中`
- 当前 Task：`RT-S11-001 系统管理入口` 已接受
- 下一可执行项：等待用户明确授权 `RT-S11-007 用户友好错误`
- 不得自动开始：不得自动启动 `RT-S11-002` 及后续 Stage 11 task、scheduler、automation、alerting、recovery runtime、cost-control runtime、route retirement 或 Stage 12

## 2026-06-22 RT-S11-001 系统管理入口

### Status

`ACCEPTED`

### Scope

将 `/system` 从跳转页调整为系统管理分组落地页，并保持普通业务页面留在系统管理之外。新的落地页按角色展示常用状态/修复入口与完整系统管理分类，覆盖：

- `Profile 配置`
- `数据源`
- `数据与调度`
- `任务运行`
- `失败与告警`
- `数据库与备份`
- `权限与审计`

同时更新相关页面文案与测试，确保普通用户只看到状态和修复入口，管理员/操作员可看到更完整的管理分类说明。

本次未实现 `RT-S11-002`、`RT-S11-003`、`RT-S11-004`、`RT-S11-005`、`RT-S11-006`、`RT-S11-007`，未新增 scheduler、automation、alerting、recovery runtime、cost-control runtime，未退役 legacy routes，未修改 formal strategy/rule/profile/current pointers，未引入新的 canonical run source-of-truth。

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定委派 1 个 bounded frontend `refactor_executor_mini`：

- `Executor Gamma`：限定在 `route-config`、`/system` hub、`system-management workspace` 和 focused frontend tests 范围内完成实现草稿。

Parent 保留 contract review、compatibility mapping 判断、focused verification、bounded repair、文档更新和最终 acceptance decision。

### Entry Verification

- Stage 10 Gate：`ACCEPTED`。
- Stage 11 Bootstrap：`READY`。
- `RT-S11-001`：是下一个允许执行的 Task。
- Stage 12：未开始。
- 本次实现前 working tree：clean。
- 本次实现前完整 diff：empty。
- 未发现需要新的 authorization policy、legacy route retirement、formal data input 变更、canonical run source-of-truth 变更或 Stage 12 work。

### Implementation Notes

- `web/src/app/route-config.tsx`：`/system` 改为渲染 `SystemPage`，不再立即跳转到 `/system/status`。
- `web/src/pages/system/SystemHubPage.tsx`：重建系统管理落地页，加入常用入口、使用说明和按角色分层的分类卡片。
- `web/src/pages/system/DatabaseMigrationPage.tsx`：移除面向普通用户的 `Job` 文案。
- `web/src/features/system-management/system-management-workspace.tsx`：系统管理页面文案改为业务化表达，保持后台任务与运行审计的分区说明。
- `web/src/pages/system/index.test.tsx`：新增管理员、操作员和普通用户可见性断言。
- `web/src/app/route-config.test.tsx`：更新 `/system` 与 `/market/datasets` 的 legacy 元数据期望。
- `web/src/app/router-auth.test.tsx`：验证 viewer/operator 可直接访问正式 `/system` 入口。

### Contract Checklist

- System Management 七类分组：pass。
- profile / market / jobs / workflows / artifacts / alerts / existing system pages 均有明确系统管理 placement 或 compatibility mapping：pass。
- business pages 仍保持在 System Management 之外：pass。
- primary navigation 仍为 business-first 七项：pass。
- ordinary-user / operator / admin visibility 有 focused tests：pass。
- 未把 `config_path` 作为 Web formal input 暴露：pass。
- 未把 Job / Workflow / Pipeline / Artifact 记录变成 formal business input：pass。
- 未新增 scheduler / automation / alert runtime：pass。
- 未退役 legacy routes：pass。
- 未变更既有 role policy，仅在现有 `viewer/operator/admin` 权限上做入口可见性分层：pass。

### Verification

- `pnpm vitest run src/app/route-config.test.tsx src/app/router-auth.test.tsx src/components/layout/sidebar.test.tsx src/pages/system/index.test.tsx src/pages/system/system-pages.test.tsx src/features/system-management/system-management-workspace.test.tsx`
- `pnpm typecheck`
- `rg -n "Job|Workflow|Pipeline|Artifact|Provider|config_path|prompt_run_id|run_id" web/src/pages/system web/src/features/system-management web/src/app/route-config.tsx`
- `git diff --check`

### Result

- Targeted Vitest: passed (`6` files, `49` tests).
- Typecheck: passed.
- diff --check: passed.
- grep: still reports internal import symbols in `route-config.tsx` and `system-management` test/helper imports, but no new user-facing `/system` hub copy or button labels expose those terms.

未运行：

- backend/API tests：本次未修改 backend 或 API contract
- browser E2E：本次未运行；当前为 focused frontend regrouping task

### Residual Risks

- 兼容页面如 `/jobs`、`/workflows`、`/artifacts`、`/market/*` 仍保留 legacy implementation 和部分技术标识；本次仅要求它们具备系统管理归属，不在 `RT-S11-001` 内退役。
- `Profile 配置` 作为冻结分组标题保留中英混合写法；当前符合 bootstrap contract，但后续若要统一为纯中文，应在不改 contract 语义前提下单独评估。
- `/system/runs` 目前仍承载运行、告警和附件兼容入口；更细粒度 observability/run-trace separation 仍属于 `RT-S11-003`。

### Acceptance Conclusion

`RT-S11-001` is `ACCEPTED` under the frozen Stage 11 contract.

Current conclusion：

- 低频管理能力现已通过正式 `/system` 入口聚合；
- daily business pages 仍保持业务优先，不要求普通用户依赖系统管理完成日常工作；
- 管理分组、兼容映射和可见性边界满足当前 Stage 11 frozen acceptance criteria；
- Stage 11 仍为 `[-] 进行中`；仅 `RT-S11-001` 已接受。

Next allowed action：wait for explicit user authorization for `RT-S11-007 用户友好错误`，或按冻结顺序执行 `RT-S11-003 可观测性和运行追踪`。Do not start `RT-S11-002`、`RT-S11-003`、`RT-S11-004`、`RT-S11-005`、`RT-S11-006`、`RT-S11-007` automatically, and do not start Stage 12.

## 2026-06-22 Stage 11 Bootstrap / Planning

### Status

`READY`

### Scope

本次只执行 Stage 11 bootstrap / contract freezing：

- verify Stage 10 entry state;
- map existing Stage 11-relevant code and tests;
- freeze Stage 11 source-of-truth contracts;
- split `RT-S11-001` through `RT-S11-007` into safe implementation order;
- define per-task acceptance criteria;
- classify Stage 10 residual risks;
- create Stage 11 implementation plan and log;
- update the main implementation log.

本次未实现生产代码、未新增 scheduler、未新增 automation runtime、未新增 alerting runtime、未新增 recovery runtime、未新增 cost-control runtime、未修改 UI 代码、未变更业务数据、未退役 legacy routes、未启动 Stage 12。

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定委派 2 个 read-only `refactor_explorer_mini`，因为 Stage 11 bootstrap 是跨后端和前端的 read-heavy mapping：

- Backend Explorer：system/config/ops、scheduler/recovery、job/workflow/prompt run、cost、data time semantics、backup/restore、audit、tests。
- Frontend Explorer：route/navigation/visibility、system pages、API clients/types、error components、business pages、legacy terms、tests。

未委派 Executor。Bootstrap 禁止生产代码实现。Parent 保留契约冻结、Task order、risk classification、acceptance criteria 和 bootstrap decision。

### Entry Verification

- Stage 10 Gate：`ACCEPTED`。
- `RT-S10-001`：accepted。
- `RT-S10-002`：accepted。
- `RT-S10-003`：accepted。
- `RT-S10-004`：accepted。
- Stage 11：本次 bootstrap 前未开始。
- Stage 12：未开始。
- Bootstrap 前 working tree：clean。
- Bootstrap 前完整 diff：empty。
- Baseline commit：`351e58581d62850d4155800ad38935fad05cb3a2`。

### Existing Code Map

#### System Management / Profile / Config

- `web/src/app/route-config.tsx` already defines canonical `/system` routes and hidden compatibility routes.
- `web/src/pages/system/*` and `web/src/features/system-management/*` are existing system/admin UI surfaces.
- `api/routers/ui/system.py`, `api/routers/ui/settings.py`, `api/routers/ui/profiles.py`, `api/routers/ui/ops.py`, `api/routers/ui/system_data.py`, `api/routers/ui/security_audit.py`, `api/routers/ui/job_audits.py`, and `api/routers/ui/data_audits.py` expose system-facing APIs.
- `src/services/system_service.py`, `src/services/config_profile_service.py`, `src/services/runtime_config.py`, and `src/services/config_migration_service.py` are current profile/config/service entry points.

#### Automation / Recovery / Scheduling

- `src/services/data_scheduling_service.py` defines the formal `system-data-operation` lane.
- `src/services/job_service.py` persists job state, retry fields, stale-job recovery, heartbeat, progress, runtime state, and audit events.
- `src/services/ops_service.py` exposes backup/restore/stale-job recovery wrappers.
- `src/services/article_pipeline_schedule_service.py` remains an in-memory scheduler compatibility path and is not frozen as the Stage 11 durable scheduler contract.

#### Observability / Run Tracking

- `jobs` / `job_audit_events`, `workflow_runs` / `workflow_run_steps`, `prompt_runs`, `backtest_runs`, `backtest_results`, and daily business objects already contain partial run/provenance fields.
- No unified Stage 11 run-trace query contract is currently implemented.

#### Cost / Incremental Control

- `ArticleRevision.content_hash`, prompt runtime cache lookup, `PromptRun.token_usage`, `PromptRun.cost_amount`, backtest request/result fingerprints, and snapshot fingerprints are existing primitives.
- No dedicated Stage 11 LLM cost/budget summary or cache-state UI contract is currently implemented.

#### Data Time Semantics

- `MarketSnapshot` has the strongest current time contract: `trade_date`, `slot`, `captured_at`, `available_at`, `effective_at`, source/provider-like fields, and quality status.
- `DatasetSnapshot` has immutable fingerprints and `available_at` / `frozen_at`, but does not uniformly carry all Stage 11 required time fields.
- Backtest service already enforces point-in-time snapshot binding in Stage 6 paths.

#### Error Handling

- Backend `ServiceResult` and frontend `BusinessPageShell` / `ProductPageAdapter` / `ErrorState` provide a base for user-friendly errors.
- Compatibility pages can still expose technical terms and internal categories.

### Frozen Contracts

Stage 11 global contracts are frozen in:

- [Stage 11 implementation plan](../refactor-implementation-plans/stage-11-implementation-plan.md)

Key frozen points:

- Low-frequency management belongs under System Management; daily business pages remain simple.
- Ordinary users do not need System Management for normal daily work.
- Admins can locate and repair data, scheduling, runtime, backup/restore, permission, audit, and failure issues.
- Legacy `Job` / `Workflow` / `Pipeline` / `Artifact` records do not become formal business inputs.
- `config_path` must not return as a Web formal input.
- Missing data remains unavailable/partial/conflict/invalid/degraded.
- Automation cannot silently publish, overwrite, approve, or execute user-impacting decisions.
- Stage 11 does not retire legacy routes unless explicitly scoped later.
- Stage 12 does not start from this bootstrap.

### Task Order

1. `RT-S11-001 系统管理入口`
2. `RT-S11-007 用户友好错误`
3. `RT-S11-003 可观测性和运行追踪`
4. `RT-S11-002 自动化和恢复`
5. `RT-S11-005 数据时间语义`
6. `RT-S11-004 成本与增量控制`
7. `RT-S11-006 灰度迁移和回滚`

### Task Combination Rules

- `RT-S11-001 + RT-S11-007`：可以，同 Session，前提是只涉及入口、文案、错误展示和 focused tests。
- `RT-S11-002 + RT-S11-003`：有条件，同 Session 串行，必须先实现 observability。
- `RT-S11-004 + RT-S11-005`：有条件，同 Parent Session 多批次，必须先完成 time semantics。
- `RT-S11-006`：单独且最后。
- 不得组合 Stage 11 与 Stage 12。

### Per-Task Acceptance Criteria

#### RT-S11-001

- System Management groups Profile 配置、数据源、数据与调度、任务运行、失败与告警、数据库与备份、权限与审计.
- Existing profile/data/runtime/failure/backup/audit pages have clear System Management placement or compatibility mapping.
- Business pages remain outside System Management.
- Ordinary-user and admin-user visibility is tested.
- `config_path` and internal Job/Workflow/Pipeline/Artifact concepts are not formal Web inputs for ordinary business flows.

#### RT-S11-002

- Scheduled tasks, retry, resume, backfill, LLM batch recovery, night jobs, and health checks have bounded behavior.
- Retry/resume/backfill is idempotent and bounded.
- Notify-only / automatic retry / admin approval boundaries are explicit.
- Automation cannot publish, overwrite, approve, or execute user-impacting decisions.

#### RT-S11-003

- Every formal business run exposes stable `run_id`.
- Steps record status, start/end time, error, retry count, and repair guidance.
- Prompt/data/backtest provenance is visible with user/admin separation.
- Normal users see business status; admins see technical details.

#### RT-S11-004

- Article hash/dedupe, prompt cache, concurrency, retry caps, incremental profile updates, backtest reuse, metric cache, and LLM cost stats have explicit contracts.
- Cache invalidation includes required fingerprints/versions.
- Stale/unavailable cache states are not hidden as success.

#### RT-S11-005

- Required time fields are present or explicitly mapped for relevant objects.
- Pre-market, post-market, and backtest enforce point-in-time availability.
- Later-filled data does not become earlier-available data.
- Missing/late data shows impact and repair guidance.

#### RT-S11-006

- Rollout path follows 新旧链路对照 → 新链路只读展示 → 小范围启用 → 新链路成为默认 → 旧入口只读 → 最终退役.
- Database, Prompt, and batch article processing have rollback or recovery evidence.
- Legacy routes are not retired unless separately authorized.

#### RT-S11-007

- Errors include happened, affected, and repair_guidance.
- Normal users receive business explanations; admins may see trace IDs and technical detail.
- No raw exception-only UI and no `Job failed`-only message.

### Residual Risks And Classification

- execution supplement missing：future execution supplement task; Stage 11 automation/recovery may observe/repair evidence but must keep execution-specific fields unavailable rather than false/success.
- caller-supplied `post_close_market_state_id`：Stage 11 observability/time-semantics hardening should validate/resolve canonical identity and preserve unavailable/invalid states.
- OpenAPI response-schema assertions partial：Stage 11 hardening for system/observability APIs; final Stage 12 Gate still requires full contract review.
- `/strategies/after-close` compatibility route remains：Stage 12 retirement follow-up; Stage 11 may surface compatibility visibility but must not retire it.
- browser E2E not run：final Stage 12 E2E unless a focused Stage 11 UI task changes relevant UI and requires targeted browser verification.

### Recommended Model / Session For RT-S11-001

- Recommended: `gpt-5.4` Task Implementation session.
- Use 0-1 mini Executor only for bounded frontend route/page grouping and focused tests.
- Escalate to `gpt-5.5` if implementation needs authorization-policy changes, route retirement, canonical run source-of-truth changes, or formal data input changes.

### Verification

Read-only / documentation verification completed:

- `AGENTS.md`
- `trade-strategy-ai/AGENTS.md`
- `docs/AI-Conversation-Templates.md`
- Stage 11-relevant sections of `docs/AI-Conversation-Project-Constraints-1.md`
- Stage 11-relevant sections of `docs/AI-Conversation-Project-Constraints-2.md`
- Stage 11 row/constraints from `docs/AI-Conversation-Task-Matrix.md`
- `docs/Trade-Refactor-TaskList.md`
- `docs/refactor-implementation-logs/stage-10.md`
- `docs/Refactor-Implementation-Log.md`
- current git status and full diff
- existing Stage 11-relevant code/tests listed above

No production tests were run because this bootstrap only updates planning/log documentation and does not change production code.

### Bootstrap Decision

`Stage 11 Bootstrap READY`

Next allowed action：wait for explicit user authorization for `RT-S11-001 系统管理入口`, or a permitted combined `RT-S11-001 + RT-S11-007` Task Session. Do not start implementation, scheduler, automation, alerting, recovery runtime, cost-control runtime, route retirement, or Stage 12 automatically.
