# Stage 12 旧入口退役与最终交付实施日志

## Current Snapshot

- Stage：`Stage 12 旧入口退役与最终交付`
- 当前活动：`RT-S12-001 旧入口退役`
- 当前状态：`RT-S12-001 ACCEPTED`
- 当前 Task：`RT-S12-001` route-level retirement and ordinary-user terminology blocker repair accepted；ordinary users no longer see legacy developer-tool main entries as normal workflow entries
- 下一可执行项：等待用户明确授权后再进入后续 Stage 12 Task；不得自动启动
  `RT-S12-002`、`RT-S12-003`、Stage 12 Gate、E2E 或用户文档生成
- 不得自动开始：不得自动开始后续 Stage 12 Task

## 2026-06-23 RT-S12-001 Blocker Repair — Ordinary-user terminology cleanup

### Status

`ACCEPTED`

### Entry Verification

- Prior 5.5 review state: `RT-S12-001 BLOCKED` only by ordinary-user-adjacent internal terminology/link exposure outside the route registry.
- Route-level retirement candidates: verified as redirect-only / hidden from normal product navigation in `web/src/app/route-config.tsx` and route tests.
- `RT-S12-002`、`RT-S12-003`、final E2E、user documentation、Stage 12 Gate: not started.
- Working tree before blocker repair already contained 5.4/5.5 route-review changes; no unrelated files were reverted.

### Bounded Repair Scope

- Fixed shared ordinary-user-adjacent recovery actions:
  - `web/src/lib/error-recovery.ts`
  - `web/src/lib/error-recovery.test.ts`
- Fixed dashboard/status ordinary-user-adjacent wording and retired links:
  - `web/src/components/dashboard/dashboard-alert-strip.tsx`
  - `web/src/components/dashboard/dashboard-recent-artifacts.tsx`
  - `web/src/components/dashboard/dashboard-recent-jobs.tsx`
  - `web/src/components/dashboard/dashboard-status-summary.tsx`
  - `web/src/components/status/recent-artifacts-panel.tsx`
  - `web/src/components/status/recent-jobs-panel.tsx`
- Fixed System Management diagnostic display labels without renaming API/backend fields:
  - `web/src/pages/system/index.tsx`
  - `web/src/pages/system/index.test.tsx`
- No backend API field, database field, schema, governance lifecycle, evidence object, E2E, user documentation, or Stage Gate work was changed.

### Terminology / Link Scan Classification

Required command:

```bash
rg -n "Job|Workflow|Pipeline|Artifact|Provider|Schema|config_path|prompt_run_id|run_id|/jobs|/artifacts|/workflows" web/src docs -g '!**/*.test.*'
```

Post-repair final scan captured `5044` hits to `/private/tmp/rt_s12_001_terms_scan_final.txt`.

| Hit group | Representative files | Classification | Action |
| --- | --- | --- | --- |
| Dashboard/recovery ordinary-user wording and `/jobs`/`/artifacts` links | `web/src/lib/error-recovery.ts`, `web/src/components/dashboard/*`, `web/src/components/status/*` | fixed ordinary-user-visible issue | replaced with `运行记录` / `运行产出` and formal targets `/system/runs`, `/system/data`, `/system/configuration`, `/rules/*`, `/daily/*` |
| System Management run/cost diagnostics | `web/src/pages/system/index.tsx` | admin diagnostic allowed | kept technical IDs under System Management, relabeled visible fields as `运行编号` / `结构版本`; no ordinary workflow input required |
| Route registry retired paths | `web/src/app/route-config.tsx` | redirect-only compatibility registry | allowed; all retirement candidates redirect to formal targets and are hidden from normal navigation |
| Formal daily/backtest/strategy implementation fields | `web/src/pages/daily/index.tsx`, `web/src/features/backtest/formal-backtest-*.tsx`, `web/src/pages/strategies/StrategyOverviewPage.tsx` | internal implementation only | allowed; visible copy uses business Chinese such as `运行编号` / `回测记录` and does not expose `run_id` as required user input |
| Unmounted legacy compatibility source | `web/src/pages/jobs/*`, `web/src/pages/artifacts/*`, `web/src/features/workflows/*`, `web/src/features/market-workspace/*`, `web/src/features/strategy-workspace/*`, legacy backtest pages | internal/legacy source only after route retirement | allowed for RT-S12-001 because route-config no longer mounts them as normal product entries; residual cleanup can occur only under later authorized work |
| API clients and TS types | `web/src/lib/api/*`, `web/src/types/*` | internal implementation only | allowed; backend/API fields were not renamed in this bounded repair |
| Tests / fixtures | excluded by required scan; inspected separately where affected | test fixture only | affected assertions updated; legacy route tests remain evidence for redirect behavior |
| Historical docs and archived docs | `docs/bak/**`, `docs/Deprecated/**`, stage plans/logs, migration/current-state audits | historical documentation note | allowed; not normal user documentation and not updated as RT-S12-003 docs work |

No remaining hit is classified as `remaining blocker`.

### Verification

- `PATH="/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH" pnpm vitest run src/app/route-config.test.tsx src/app/router-auth.test.tsx src/app/navigation.test.ts src/components/layout/sidebar.test.tsx src/components/layout/section-nav.test.tsx src/lib/error-recovery.test.ts src/components/dashboard/dashboard-recent-jobs.test.tsx src/components/dashboard/dashboard-status-summary.test.tsx src/pages/system/index.test.tsx`
  - result: `9` files passed, `89` tests passed.
- Broader exploratory frontend run additionally included daily/strategy pages; it had one unrelated date-sensitive failure in `src/pages/daily/index.test.tsx` expecting `2026-06-22` while the session date is `2026-06-23`, plus stale expectations repaired in this blocker scope. The accepted verification set above excludes that unrelated date assertion.
- `PATH="/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH" pnpm typecheck`
  - result: pass.
- `PATH="/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH" pnpm eslint src/lib/error-recovery.ts src/lib/error-recovery.test.ts src/components/dashboard/dashboard-recent-jobs.tsx src/components/dashboard/dashboard-recent-artifacts.tsx src/components/dashboard/dashboard-status-summary.tsx src/components/dashboard/dashboard-alert-strip.tsx src/components/status/recent-jobs-panel.tsx src/components/status/recent-artifacts-panel.tsx src/pages/system/index.tsx src/pages/system/index.test.tsx`
  - result: pass.
- `git diff --check`
  - result: pass.
- Required terminology scan:
  - result: completed; `5044` hits classified above; no remaining ordinary-user-visible blocker.
- Backend/API tests:
  - not run; this blocker repair changed only frontend wording/links, route-adjacent shared recovery text, System Management display labels, tests, and logs. No backend route, API client contract, database schema, or evidence access logic changed.

### Residual Risks

- Legacy source files still contain developer terms and retired links, but the 5.5 route registry no longer exposes them as normal workflow entries. They are classified as unmounted legacy compatibility source, not active ordinary-user product flow.
- System Management diagnostics still display technical IDs for operators/admins, with Chinese labels and no requirement for ordinary users to supply those IDs.
- Browser E2E and user documentation remain future Stage 12 tasks and were not started here.

### Final Decision

`RT-S12-001 ACCEPTED`

## 2026-06-23 RT-S12-001 5.5 Review / Bounded Repair

### Review Status

`BLOCKED`

### Entry Verification

- Stage 11 Gate：`ACCEPTED`，from `docs/refactor-implementation-logs/stage-11.md`.
- Stage 12 Bootstrap：`READY`，from this log and `docs/refactor-implementation-plans/stage-12-implementation-plan.md`.
- 5.4 implementation state：`READY_FOR_5.5_REVIEW`，from this log and `docs/Refactor-Implementation-Log.md`.
- `RT-S12-002`、`RT-S12-003`、final E2E、user documentation、Stage 12 Gate：not started.
- Branch：`main`.
- Review-start HEAD：`5c578e76ef9afedf06cc84654ada4b7150ac63a6`.
- Review-start dirty files：5.4 implementation files only:
  `docs/Refactor-Implementation-Log.md`,
  `docs/refactor-implementation-logs/stage-12.md`,
  `web/src/app/route-config.tsx`,
  `web/src/app/route-config.test.tsx`,
  `web/src/components/layout/section-nav.test.tsx`.
- Subagents：0 selected. Parent review only; route inventory and scans were local, mechanical, and did not justify coordination overhead.

### Reviewed 5.4 Scope

- `web/src/app/route-config.tsx` converted legacy main entries to hidden redirects and removed no-longer-used legacy page imports.
- `web/src/app/route-config.test.tsx` asserted legacy metadata and redirect behavior.
- `web/src/components/layout/section-nav.test.tsx` updated the System Management label expectation.
- Stage 12 and main implementation logs recorded the 5.4 handoff.
- No backend, database, schema, prompt, governance lifecycle, evidence object, E2E, or user-doc work was started.

### 5.5 Bounded Repair

- `web/src/app/route-config.tsx`
  - changed the remaining mutable or developer-facing legacy detail candidates from mounted legacy pages to redirects:
    `/jobs/:jobId`, `/profiles/:profileId`, `/profiles/:profileId/edit`,
    `/profiles/:profileId/snapshots/:snapshotId`, `/workflows/:workflowId/run`,
    `/backtest/regime`, `/rule-pool/:ruleId`, `/artifacts/:artifactId`,
    `/market/snapshots`, `/market/datasets`.
  - removed the corresponding legacy page imports from the route registry.
- `web/src/app/route-config.test.tsx`
  - updated metadata expectations and now requires every retired route candidate to redirect to a formal product or System Management target.
- `web/src/app/router-auth.test.tsx`
  - updated dynamic legacy deep-link behavior: `/jobs/job-123` now redirects to `/system/runs`.

### Full Retirement Inventory

| Legacy route | Handling after 5.5 repair | Formal target | Ordinary-user exposure | Evidence / rollback preservation |
| --- | --- | --- | --- | --- |
| `/workflows` | redirected | `/system/runs` | no normal entry | system run trace page preserves run evidence |
| `/workflows/:workflowId/run` | redirected | `/system/runs` | no normal entry | system run trace page preserves legacy runtime evidence |
| `/workflows/pre-market` | redirected | `/daily/pre-market` | no normal entry | formal daily pre-market page |
| `/workflows/pre-market/run` | redirected | `/daily/pre-market` | no normal entry | formal daily pre-market page |
| `/workflows/after-close` | redirected | `/daily/after-close` | no normal entry | formal daily after-close page |
| `/workflows/after-close/run` | redirected | `/daily/after-close` | no normal entry | formal daily after-close page |
| `/jobs` | redirected | `/system/runs` | no normal entry | system run trace page |
| `/jobs/:jobId` | redirected | `/system/runs` | no normal entry | system run trace page; direct detail resolver remains future hardening |
| `/artifacts` | redirected | `/system/runs` | no normal entry | system run trace / artifact evidence remains queryable through diagnostics |
| `/artifacts/:artifactId` | redirected | `/system/runs` | no normal entry | system run trace / artifact evidence remains queryable through diagnostics |
| `/market` | redirected | `/system/data` | no normal entry | formal data and scheduling page |
| `/market/snapshots` | redirected | `/system/data` | no normal entry | formal data diagnostics preserve snapshot evidence |
| `/market/datasets` | redirected | `/system/data` | no normal entry | formal data diagnostics preserve dataset evidence |
| `/market/kaipan` | redirected | `/system/data` | no normal entry | formal data page |
| `/market/ohlcv` | redirected | `/system/data` | no normal entry | formal data page |
| `/backtest` | redirected | `/rules/backtests` | no normal entry | formal backtest workbench |
| `/backtest/regime` | redirected | `/rules/results` | no normal entry | formal market-state result page |
| `/backtest/candidates` | redirected | `/strategies/candidates` | no normal entry | formal strategy candidate page |
| `/strategies/pre-market` | redirected | `/daily/pre-market` | no normal entry | formal daily pre-market page |
| `/strategies/after-close` | redirected | `/daily/after-close` | no normal entry | formal daily after-close page |
| `/dashboard` | redirected | `/` | no normal entry | formal home page |
| `/articles` | redirected | `/research/articles` | no normal entry | formal article library |
| `/articles/run` | redirected | `/research/add` | no normal entry | formal article import page |
| `/articles/list` | redirected | `/research/articles` | no normal entry | formal article library |
| `/articles/quality` | redirected | `/research/results` | no normal entry | formal extraction results page |
| `/articles/results` | redirected | `/research/results` | no normal entry | formal extraction results page |
| `/rule-pool` | redirected | `/rules/review` | no normal entry | formal rule review page |
| `/rule-pool/:ruleId` | redirected | `/rules/library` | no normal entry | formal rule library |
| `/persona` | redirected | `/authors` | no normal entry | formal author profile page |
| `/profiles` | redirected | `/system/configuration` | no normal entry | formal configuration page |
| `/profiles/import` | redirected | `/system/configuration` | no normal entry | formal configuration page |
| `/profiles/:profileId` | redirected | `/system/configuration` | no normal entry | formal configuration diagnostics |
| `/profiles/:profileId/edit` | redirected | `/system/configuration` | no normal entry | prevents legacy edit page from remaining live |
| `/profiles/:profileId/snapshots/:snapshotId` | redirected | `/system/configuration` | no normal entry | formal configuration diagnostics |
| `/alerts` | redirected | `/system/runs` | no normal entry | formal system run / alert diagnostics |
| `/admin` | redirected | `/system/status` | no normal entry | formal system status |
| `/admin/audit` | redirected | `/system/audit` | no normal entry | formal audit page |
| `/system/restore` | redirected | `/system/backup` | no normal entry | formal backup/recovery page |
| `/settings` | redirected | `/system/configuration` | no normal entry | formal configuration page |

### Retained Compatibility Register

After 5.5 bounded repair, no RT-S12-001 retirement-candidate route remains as a mounted read-only compatibility page in `web/src/app/route-config.tsx`; all candidates are redirect-only. Canonical long-term routes `/login`, `/`, `/strategies`, `/system/*`, and `*` are not retirement candidates.

### Reference Scan Classification

- Required broad route scan:
  `rg -n "/workflows|/jobs|/artifacts|/market|/backtest|/strategies/pre-market|/strategies/after-close|/dashboard|/articles|/rule-pool|/persona|/profiles|/alerts|/admin|/settings|/system/restore" web docs`
  - Active `route-config` hits are expected redirect definitions and route tests.
  - Active `web/src/lib/api/*` hits are internal API-client implementation, not route registry or navigation.
  - Active legacy component/page hits remain in source but are no longer imported by `route-config`; direct legacy route mounts were removed.
  - `docs/Refactor-Migration-Matrix.md`, Stage plans/logs, and current implementation logs are historical / contract evidence.
  - `docs/bak/**` and `docs/Deprecated/**` contain archived historical notes; not normal user documentation.
- Required internal terminology scan:
  `rg -n "Job|Workflow|Pipeline|Artifact|Provider|Schema|config_path|prompt_run_id|run_id" web/src docs -g '!**/*.test.*'`
  - Admin/system diagnostics allowed: `web/src/pages/system/index.tsx`, system management workspace, audit/run trace references.
  - Internal implementation only: API clients, TS types, component names, unmounted legacy pages/components.
  - Historical documentation note: TaskList, migration matrix, stage plans/logs, current-state audit.
  - `must fix / blocker`: active formal or ordinary-user-adjacent components still contain visible `Job` / `/jobs` / `Artifact` wording and links outside the route registry, including examples in `web/src/pages/daily/index.tsx`, `web/src/features/strategy-workspace/*`, `web/src/features/backtest/*`, `web/src/features/market-workspace/*`, dashboard/status artifact/job panels, and shared error recovery actions. Some may be unmounted by current formal routes, but this review did not prove all are unreachable from ordinary user flows.

### Verification

- `pnpm vitest run src/app/route-config.test.tsx src/app/router-auth.test.tsx src/app/navigation.test.ts src/components/layout/sidebar.test.tsx src/components/layout/section-nav.test.tsx`
  - first attempt failed because the default shell used Node `v14.4.0`.
  - rerun with Node 18 path: `5` files passed, `70` tests passed.
- `pnpm typecheck`
  - pass.
- `pnpm exec eslint src/app/route-config.tsx src/app/route-config.test.tsx src/app/router-auth.test.tsx src/app/navigation.ts src/app/navigation.test.ts src/components/layout/sidebar.test.tsx src/components/layout/section-nav.test.tsx`
  - pass.
- `git diff --check`
  - pass.
- Backend/API tests:
  - not run; bounded repairs only changed frontend route exposure, route tests, and logs. No API client, backend route, database, System Management service, or evidence access logic was changed in 5.5.

### Automatic Repair Loop Summary

- Finding 1: retained `/jobs/:jobId` metadata lacked formal target / retirement condition in route config.
  - repair: redirected to `/system/runs`.
- Finding 2: `/profiles/:profileId/edit` mounted a mutable edit page, violating read-only/redirect-only compatibility criteria.
  - repair: redirected profile detail/edit/snapshot compatibility routes to `/system/configuration`.
- Finding 3: other retained evidence detail routes mounted legacy pages that could expose developer-facing workflow controls or terms.
  - repair: redirected job/artifact/workflow/backtest/rule/market detail candidates to formal targets.
- Finding 4: ordinary-user visible internal terminology remains outside route registry.
  - result: not fully repaired in this bounded pass; needs additional ordinary-user exposure cleanup or a 5.5 scoping decision.

### Residual Risks / Blockers

- `BLOCKER`: the required internal terminology scan still finds active non-test frontend source with visible `Job`, `/jobs`, `Artifact`, `run_id`, and related wording outside `route-config`. Some hits are admin diagnostics or unmounted legacy components, but this review did not prove all remaining hits are inaccessible to ordinary users.
- `BLOCKER`: because of those unclassified/active ordinary-user-adjacent hits, RT-S12-001 cannot yet satisfy the hard forbidden condition that `Job / Workflow / Pipeline / Artifact / Provider / Schema / config_path / prompt_run_id / run_id` are not exposed as ordinary-user workflow concepts or required inputs.
- Non-blocking note: route-level old-entry retirement itself now passes focused tests; no retired route candidate remains mounted as a legacy page.

### 5.5 Review Decision

`RT-S12-001 BLOCKED`

Exact blocker: complete ordinary-user exposure cleanup/classification is still required for internal terminology hits outside the route registry before the task can be accepted. Do not start `RT-S12-002`, `RT-S12-003`, final E2E, user documentation, or Stage 12 Gate.

## 2026-06-23 RT-S12-001 旧入口退役

### Status

`READY_FOR_5.5_REVIEW`

### Scope

- 只修改 `web/src/app/route-config.tsx`、相关路由/导航测试和正式实施日志；
- 只处理 legacy route/page entry、navigation exposure、redirect/hide decisions、
  related unused imports、route tests、navigation tests 和 retirement evidence log；
- 不修改数据库 schema、formal records、Prompt evidence、migration reports、
  backtest evidence、strategy/rule/profile audit history、daily plans、
  optimization proposals、governance lifecycle 或 backend runtime behavior；
- 不启动 `RT-S12-002`、`RT-S12-003`、browser E2E、Stage 12 Gate 或用户文档。

### Entry Verification

- Stage 11 Gate：`ACCEPTED`
- Stage 12 Bootstrap：`READY`
- `RT-S12-001` 是 Stage 12 下一且必须单独执行的 Task：verified
- Stage 12 implementation 在本 Session 前未开始：verified from
  `docs/refactor-implementation-logs/stage-12.md` and
  `docs/Refactor-Implementation-Log.md`
- working tree before edits：clean
- no parallel Stage 12 task / E2E / docs work started：verified

### Implementation

- `web/src/app/route-config.tsx`
  - 将确认已被 formal route 覆盖的 legacy 主入口改为 direct redirect，避免普通用户
    再进入旧工作台：
    - `/jobs` -> `/system/runs`
    - `/profiles` -> `/system/configuration`
    - `/profiles/import` -> `/system/configuration`
    - `/workflows` -> `/system/runs`
    - `/articles/run` -> `/research/add`
    - `/articles/list` -> `/research/articles`
    - `/articles/quality` -> `/research/results`
    - `/articles/results` -> `/research/results`
    - `/alerts` -> `/system/runs`
    - `/backtest` -> `/rules/backtests`
    - `/backtest/candidates` -> `/strategies/candidates`
    - `/rule-pool` -> `/rules/review`
    - `/artifacts` -> `/system/runs`
    - `/market` -> `/system/data`
    - `/market/kaipan` -> `/system/data`
    - `/market/ohlcv` -> `/system/data`
    - `/persona` -> `/authors`
    - `/strategies/pre-market` -> `/daily/pre-market`
    - `/strategies/after-close` -> `/daily/after-close`
  - 保留 evidence/deep-link sensitive compatibility routes 为 hidden read-only /
    compatibility-only surface，不暴露在 primary navigation：
    - `/jobs/:jobId`
    - `/artifacts/:artifactId`
    - `/market/snapshots`
    - `/market/datasets`
    - `/profiles/:profileId`
    - `/profiles/:profileId/edit`
    - `/profiles/:profileId/snapshots/:snapshotId`
    - `/workflows/:workflowId/run`
    - `/backtest/regime`
    - `/rule-pool/:ruleId`
  - 删除 redirect 后已不再使用的 legacy page imports；未删除 route registry，
    继续保持 `route-config.tsx` 为唯一 formal source-of-truth。
- `web/src/app/route-config.test.tsx`
  - 先以 failing test 固化 RT-S12-001 退役目标；
  - 更新 expected legacy metadata；
  - 新增断言：retired legacy main entries 必须 redirect，detail evidence routes
    继续 compatibility-only。
- `web/src/components/layout/section-nav.test.tsx`
  - 修复 stale 文案断言：`数据管理` -> `数据与调度`，使当前系统管理 section nav
    与正式路由标签一致。

### Retirement Inventory And Retained Compatibility Register

| Legacy route | Handling | Formal target | Owner | Evidence / rollback reason | Remaining retirement condition | Ordinary user visible | Admin/operator diagnostic |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard` | redirected | `/` | Stage 1 product shell | none | stable long-term redirect | no | n/a |
| `/jobs` | redirected | `/system/runs` | Stage 11 system runs | list evidence already exposed in formal System Management | observe old deep-link traffic only | no | yes |
| `/jobs/:jobId` | read-only retained | `/system/runs` | Stage 11 system runs | job timeline, artifacts, logs, config snapshot deep links still live here | formal run detail resolver by business object or system route | no | yes |
| `/profiles` | redirected | `/system/configuration` | Stage 11 system configuration | none | observe old deep-link traffic only | no | yes |
| `/profiles/import` | redirected | `/system/configuration` | Stage 11 system configuration | none | observe old deep-link traffic only | no | yes |
| `/profiles/:profileId` | read-only retained | `/system/configuration` | Stage 11 system configuration | profile id deep links and configuration evidence remain reachable | formal configuration detail route / resolver | no | yes |
| `/profiles/:profileId/edit` | read-only retained | `/system/configuration` | Stage 11 system configuration | historical edit/review deep links still resolve here | formal configuration edit/detail route / resolver | no | yes |
| `/profiles/:profileId/snapshots/:snapshotId` | read-only retained | `/system/configuration` | Stage 11 system configuration | snapshot evidence deep links still resolve here | formal configuration snapshot route / resolver | no | yes |
| `/workflows` | redirected | `/system/runs` | Stage 11 system runs | list evidence already exposed in formal runs page | observe old deep-link traffic only | no | yes |
| `/workflows/pre-market` | redirected | `/daily/pre-market` | Stage 9 daily pre-market | none | stable redirect observation | no | n/a |
| `/workflows/pre-market/run` | redirected | `/daily/pre-market` | Stage 9 daily pre-market | none | stable redirect observation | no | n/a |
| `/workflows/after-close` | redirected | `/daily/after-close` | Stage 10 daily after-close | none | stable redirect observation | no | n/a |
| `/workflows/after-close/run` | redirected | `/daily/after-close` | Stage 10 daily after-close | none | stable redirect observation | no | n/a |
| `/workflows/:workflowId/run` | read-only retained | `/system/runs` | Stage 11 system runs | workflow-run deep links may still be needed to inspect legacy runtime evidence | formal legacy workflow resolver or confirmed no traffic | no | yes |
| `/articles` | redirected | `/research/articles` | Stage 3 research | none | stable long-term redirect | no | n/a |
| `/articles/run` | redirected | `/research/add` | Stage 3 research | formal import flow now covers user goal | observe old deep-link traffic only | no | n/a |
| `/articles/list` | redirected | `/research/articles` | Stage 3 research | formal article list now covers user goal | observe old deep-link traffic only | no | n/a |
| `/articles/quality` | redirected | `/research/results` | Stage 3 research | formal result/status view now covers user goal | observe old deep-link traffic only | no | n/a |
| `/articles/results` | redirected | `/research/results` | Stage 4 research | formal extraction result view now covers user goal | observe old deep-link traffic only | no | n/a |
| `/alerts` | redirected | `/system/runs` | Stage 11 system runs | alert list/repair actions already exposed in System Management and homepage | observe old deep-link traffic only | no | yes |
| `/backtest` | redirected | `/rules/backtests` | Stage 6 formal backtests | formal backtest workbench covers user workflow | observe old deep-link traffic only | no | n/a |
| `/backtest/regime` | read-only retained | `/rules/results` | Stage 6 formal backtests | market-state result evidence may still require legacy report deep link | formal result detail parity or confirmed unused | no | yes |
| `/backtest/candidates` | redirected | `/strategies/candidates` | Stage 8 strategy center | formal candidate route covers user goal | observe old deep-link traffic only | no | n/a |
| `/rule-pool` | redirected | `/rules/review` | Stage 4 rule review | formal review workbench covers user goal | observe old deep-link traffic only | no | n/a |
| `/rule-pool/:ruleId` | read-only retained | `/rules/library` | Stage 4 rule review | historical rule id mapping evidence may still resolve here | formal rule-detail legacy id resolver | no | yes |
| `/artifacts` | redirected | `/system/runs` | Stage 11 system runs | artifact list is no longer a formal user workflow | observe old deep-link traffic only | no | yes |
| `/artifacts/:artifactId` | read-only retained | `/system/runs` | Stage 11 system runs | artifact preview/download deep links still provide provenance access | formal artifact detail resolver by business object | no | yes |
| `/market` | redirected | `/system/data` | Stage 5 system data | formal data workspace covers ordinary-user repair path | observe old deep-link traffic only | no | yes |
| `/market/snapshots` | read-only retained | `/system/data` | Stage 5 system data | snapshot browser still carries admin/detail evidence | formal snapshot detail route or confirmed unused | no | yes |
| `/market/datasets` | read-only retained | `/system/data` | Stage 5 system data | dataset version browser still carries admin/detail evidence | formal dataset detail route or confirmed unused | no | yes |
| `/market/kaipan` | redirected | `/system/data` | Stage 5 system data | formal data workspace covers repair actions | observe old deep-link traffic only | no | yes |
| `/market/ohlcv` | redirected | `/system/data` | Stage 5 system data | formal data workspace covers repair actions | observe old deep-link traffic only | no | yes |
| `/persona` | redirected | `/authors` | Stage 7 author profiles | formal author-profile flow covers user goal | observe old deep-link traffic only | no | n/a |
| `/strategies/pre-market` | redirected | `/daily/pre-market` | Stage 9 daily pre-market | formal daily plan flow covers user goal | observe old deep-link traffic only | no | n/a |
| `/strategies/after-close` | redirected | `/daily/after-close` | Stage 10 daily after-close | formal post-market flow covers user goal | observe old deep-link traffic only | no | n/a |
| `/admin` | redirected | `/system/status` | Stage 11 system management | none | stable redirect observation | no | yes |
| `/admin/audit` | redirected | `/system/audit` | Stage 11 system management | none | stable redirect observation | no | yes |
| `/system/restore` | redirected | `/system/backup` | Stage 11 system management | none | stable redirect observation | no | yes |
| `/settings` | redirected | `/system/configuration` | Stage 11 system management | none | stable redirect observation | no | yes |

### Verification

- route / navigation / visibility tests
  - `pnpm vitest run src/app/route-config.test.tsx src/app/router-auth.test.tsx src/app/navigation.test.ts src/components/layout/sidebar.test.tsx src/components/layout/section-nav.test.tsx`
  - result: `5` files passed, `60` tests passed
- focused red/green proof
  - first `pnpm vitest run src/app/route-config.test.tsx` failed with 3 expected
    failures because legacy main entries were still `notice` instead of `redirect`
  - after `route-config.tsx` changes the same suite passed: `12` tests passed
- frontend typecheck
  - `pnpm typecheck`
  - result: pass
- targeted lint
  - `pnpm exec eslint src/app/route-config.tsx src/app/route-config.test.tsx src/app/router-auth.test.tsx src/app/navigation.ts src/app/navigation.test.ts src/components/layout/sidebar.test.tsx src/components/layout/section-nav.test.tsx`
  - result: pass
- safety
  - `git diff --check`
  - result: pass

### Reference Scan Results

- `rg -n "/workflows|/jobs|/artifacts|/market|/backtest|/strategies/pre-market|/strategies/after-close|/dashboard|/articles|/rule-pool|/persona|/profiles|/alerts|/admin|/settings|/system/restore" web/src docs --glob '!**/docs/bak/**' --glob '!**/docs/Deprecated/**'`
  - hits in `web/src/app/route-config.tsx`: expected formal route registry and compatibility definitions
  - hits in navigation/route tests: expected verification fixtures
  - hits in `docs/Refactor-Migration-Matrix.md`, current logs, and stage plans/logs:
    expected historical / retirement documentation
  - no new second route registry discovered
- legacy main-entry imports removed from `route-config.tsx` only after redirect conversion;
  retained detail pages continue to have explicit references from the single route registry

### Grep / Internal Terminology Classification

- `rg -n "Job|Workflow|Pipeline|Artifact|Provider|Schema|config_path|prompt_run_id|run_id" web/src docs -g '!**/*.test.*' --glob '!**/docs/bak/**' --glob '!**/docs/Deprecated/**'`
  - `web/src/app/route-config.tsx`: internal code only; legacy metadata and compatibility mapping
  - `docs/Trade-Refactor-TaskList.md`, `docs/Refactor-Migration-Matrix.md`,
    `docs/Refactor-Implementation-Log.md`, stage plans/logs: documentation historical note /
    contract language; allowed
  - `web/src/features/*`, `web/src/lib/api/*`, `web/src/components/artifacts/*`,
    `web/src/components/status/*`: internal code only or admin diagnostic allowed
  - no finding requiring RT-S12-001 code changes was found in primary navigation,
    section navigation, or `route-config` user-facing labels after this task

### Bounded Repairs

- Updated `web/src/components/layout/section-nav.test.tsx` to assert the current
  formal label `数据与调度`; the old `数据管理` expectation was stale and caused one
  focused verification failure.

### Residual Risks

- Compatibility detail routes still exist for job, artifact, workflow-run,
  snapshot, dataset, profile snapshot/edit and legacy rule/backtest detail evidence.
  This is intentional because formal resolver parity has not yet been proven.
- Reference scans still show many historical mentions inside migration matrix,
  stage plans, and implementation logs. These are retirement evidence, not active
  user workflow docs.
- No browser E2E or user documentation work was started in this Task; both remain
  later Stage 12 scope.

### Implementation Decision

`READY_FOR_5.5_REVIEW`

## 2026-06-23 Stage 12 Bootstrap

### Status

`READY`

### Scope

- 只执行 Stage 12 Bootstrap / contract freezing；
- 创建 Stage 12 implementation plan 和 Stage 12 log；
- 更新主实施日志的当前状态、索引、残余风险和下一步；
- 不实现生产代码；
- 不退役 legacy routes；
- 不修改 frontend / backend / database runtime behavior；
- 不启动 `RT-S12-001`、`RT-S12-002` 或 `RT-S12-003`。

### Required Reading Completed

- `AGENTS.md`
- `trade-strategy-ai/AGENTS.md`
- `docs/AI-Conversation-Templates.md`
- `docs/AI-Conversation-Project-Constraints-1.md`
- `docs/AI-Conversation-Project-Constraints-2.md`
- `docs/AI-Conversation-Task-Matrix.md`
- `docs/Trade-Refactor-TaskList.md`
- `docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`
- `docs/PROMPT_REVIEW_AND_MIGRATION.md`
- `docs/AUTHOR_PROFILE_PROMPT_FLOW.md`
- `docs/refactor-implementation-logs/stage-11.md`
- `docs/Refactor-Implementation-Log.md`
- Stage 0-11 implementation plans/logs were scanned for retirement,
  compatibility, final-delivery, residual-risk, Gate, and E2E evidence needed
  for Stage 12 readiness.
- `web/src/app/route-config.tsx` was read to verify current route metadata and
  retirement candidates.

### Entry Verification

- Stage 11 Gate：`ACCEPTED`
- `RT-S11-001 系统管理入口`：`ACCEPTED`
- `RT-S11-002 自动化和恢复`：`ACCEPTED`
- `RT-S11-003 可观测性和运行追踪`：`ACCEPTED`
- `RT-S11-004 成本与增量控制`：`ACCEPTED`
- `RT-S11-005 数据时间语义`：`ACCEPTED`
- `RT-S11-006 灰度迁移和回滚`：`ACCEPTED`
- `RT-S11-007 用户友好错误`：`ACCEPTED`
- Stage 12 before Bootstrap：not started
- working tree before Bootstrap edits：clean
- Branch：`main`
- Baseline commit：`6d15a217694569008cb39ad194871c119de66a58`

### Frozen Contracts

- Stage 12 must not create a second formal source-of-truth.
- Stage 12 must not remove evidence required for traceability, rollback, audits,
  prompt history, data provenance, or migration recovery.
- Legacy route retirement must happen only when the new formal entry is
  verified.
- Ordinary users must not see developer-tool main entries.
- User-facing docs must not require understanding internal developer terms.
- Missing, partial, unavailable, degraded, invalid, and conflict states remain
  truthful.
- Accepted governance paths for rules, profiles, strategies, daily plans, and
  optimization proposals must be preserved.
- Deletion versus hiding criteria, rollback/recovery expectations, E2E
  acceptance path, required documentation deliverables, task order, per-task
  acceptance criteria, residual-risk classification, and verification strategy
  are frozen in
  `docs/refactor-implementation-plans/stage-12-implementation-plan.md`.

### Frozen Task Order

1. `RT-S12-001 旧入口退役`
2. `RT-S12-002 端到端验收`
3. `RT-S12-003 用户文档`

Combination rules:

- `RT-S12-001` must be single and separate.
- `RT-S12-002` + `RT-S12-003` may be combined only after `RT-S12-001` is
  accepted, and only if E2E evidence and documentation updates are kept clearly
  separated.
- Bootstrap is not combined with implementation.

### Residual Risks Inherited From Stage 11

- Legacy compatibility pages still contain internal terms and legacy
  implementation details；blocking for `RT-S12-001` until each page is deleted,
  redirected, hidden, or explicitly retained read-only with reason.
- Stage 2 migration report files and historical PromptRun evidence may be absent
  in some environments；non-blocking only if Stage 12 preserves evidence paths
  and continues truthful `partial` / `unavailable` presentation.
- `DatasetSnapshot` still lacks independent persisted `captured_at` / `slot`
  columns；non-blocking unless Stage 12 attempts to change data-time schema.
- Browser E2E and full all-repo lint were not run in Stage 11；blocking for final
  Stage 12 Gate unless replaced by documented scoped evidence and accepted
  residual risk.
- Stage 10 OpenAPI response-schema assertions partial；Stage 12 Gate must include
  full or targeted contract review.
- `/strategies/after-close` compatibility route remains；blocking for
  `RT-S12-001` unless explicitly retained read-only with reason.

### Bootstrap Outputs

- Created `docs/refactor-implementation-plans/stage-12-implementation-plan.md`.
- Created `docs/refactor-implementation-logs/stage-12.md`.
- Updated `docs/Refactor-Implementation-Log.md`.

### Verification

- Documentation-only diff review：pass；changed files are limited to Stage 12
  plan/log and the main implementation log.
- No production code changed：pass；diff/status review shows only docs files.
- Stage 11 Gate and accepted tasks verified from Stage 11 log：pass.
- Stage 12 not previously started verified from main log, Stage 11 log, and
  absence of Stage 12 plan/log before edits：pass.
- `git diff --check`：pass.

### Bootstrap Decision

`Stage 12 Bootstrap READY`

Next allowed action：wait for explicit user authorization for
`RT-S12-001 旧入口退役` only. Do not start `RT-S12-002`、`RT-S12-003` or final
E2E/documentation work automatically.
