# Stage 12 Gate

Date: 2026-06-30

Status: `STAGE_12_GATE_BLOCKED`

## Scope

- Gate review for `Stage 12 旧入口退役与最终交付`.
- Parent performed final Gate judgment; no subagent was used.
- No route, schema, governance, data-source, lifecycle, prompt, or product contract was changed.
- One bounded E2E harness repair was made in `web/playwright.config.ts` so localhost readiness checks bypass proxy settings.
- Local Playwright dependency and Chromium runtime were restored for verification only; runtime/cache files were not committed.

## Gate Review Summary

- `RT-S12-001`: accepted task evidence remains valid. Retired ordinary-user legacy routes are redirect-only in the single route registry, and primary navigation exposes only formal product entries plus allowed System Management.
- `RT-S12-002`: accepted evidence remains documented in `rt-s12-002-browser-e2e.md`, including separate final E2E IDs and explicit reference-chain boundary. Fresh Gate E2E rerun is blocked by current local authentication environment.
- `RT-S12-003`: accepted documentation evidence remains valid. Delivered user/admin/deployment docs are under `docs/stage-12-user-docs/` and indexed from `docs/README.md`.
- Global contract: no second route/schema/governance/data-source/documentation source of truth was found in the reviewed Stage 12 diff. Truthful missing/partial/unavailable/degraded/invalid/conflict language remains documented.

## Findings

### Finding 1: local DB current is not migration head

Severity: `BLOCKER` for fresh Gate acceptance in this environment.

Evidence:

- `python -m cli.main db-check --config config/app.template.yaml`: `DB OK: 1`.
- `python -m alembic -c src/db/migrations/alembic.ini current`: `2026_06_14_0006`.
- `python -m alembic -c src/db/migrations/alembic.ini heads`: `2026_06_20_0001 (head)`.
- Bounded migration attempt with `python -m cli.main db-migrate --config config/app.template.yaml` failed at `2026_06_17_0008` with `InsufficientPrivilegeError: must be owner of table ohlcv_bars`.
- Recheck after the failed attempt still reported `current=2026_06_14_0006`; the attempted migration did not advance Alembic state.

Classification:

- This is a local database ownership/permission blocker, not a Stage 12 code contract change.
- Gate cannot mark Stage 12 accepted while the current verification database is not at head and cannot be upgraded by the configured user.

Minimum repair:

- Run migrations using the owner or a migration role that owns the existing tables, or repair table ownership in the local database with explicit administrator authorization.
- Re-run `db-check`, `alembic current`, `alembic heads`, and the Stage 12 E2E after the database reaches head.

### Finding 2: fresh Browser E2E cannot authenticate in current environment

Severity: `BLOCKER` for fresh Gate acceptance in this environment.

Evidence:

- `python -m scripts.web_local env-check` reported `ADMIN_API_KEY` unset and did not print any sensitive values.
- After Playwright dependency/runtime repair, `pnpm e2e` started the local server and ran the browser test.
- The browser test failed on the first formal route because the app remained on the login page, proving the test did not reach the formal product journey in this environment.

Classification:

- The accepted RT-S12-002 E2E record remains historical accepted evidence.
- Fresh Gate E2E cannot be counted as passing until the environment provides a valid admin API key or an approved test authentication path.

Minimum repair:

- Provide `ADMIN_API_KEY` through the approved local environment mechanism.
- Re-run `python -m scripts.web_local env-check` and `pnpm e2e`.

### Finding 3: Playwright harness was sensitive to proxy and stale local dependencies

Severity: fixed within bounded Gate scope.

Evidence:

- Initial `pnpm e2e` resolved to a non-test Playwright CLI because local `@playwright/test` was not installed in `web/node_modules`.
- `corepack pnpm install --frozen-lockfile` restored `@playwright/test 1.61.1`.
- Initial webServer readiness checks timed out because localhost requests were routed through proxy configuration; direct localhost probing with proxy disabled returned HTTP 200 for `/` and `/health`.

Fix:

- Updated `web/playwright.config.ts` to add `127.0.0.1`, `localhost`, and `::1` to `NO_PROXY` / `no_proxy`.
- Installed the Playwright Chromium runtime locally for verification; no runtime files were committed.

Rerun:

- `pnpm typecheck`: pass.
- `pnpm test -- src/app/route-config.test.tsx`: pass, `12 passed`.
- `pnpm e2e`: no longer times out on webServer readiness; now fails at the expected environment authentication blocker.

## Verification

Backend / DB:

- `python -m scripts.web_local env-check`: pass; redacted output only. `ADMIN_API_KEY` and `DATABASE_URL` were unset in this shell, `DASHSCOPE_API_KEY` was set and redacted.
- `python -m cli.main db-check --config config/app.template.yaml`: pass, `DB OK: 1`.
- `python -m alembic -c src/db/migrations/alembic.ini current`: pass, current `2026_06_14_0006`.
- `python -m alembic -c src/db/migrations/alembic.ini heads`: pass, head `2026_06_20_0001`.
- `python -m cli.main db-migrate --config config/app.template.yaml`: failed; configured DB user is not owner of `ohlcv_bars`.
- Focused backend/API/service tests for Stage 12 path: pass, `69 passed`.

Frontend / E2E:

- `pnpm typecheck`: pass.
- `pnpm test -- src/app/route-config.test.tsx`: pass, `12 passed`.
- `pnpm build`: pass.
- `pnpm e2e`: failed after harness repair because the app remained on the login page; `ADMIN_API_KEY` was unavailable.

Docs / safety:

- `git diff --check`: pass before log update.
- Delivered-doc terminology grep for `Job|Workflow|Pipeline|Artifact|Provider|Schema|config_path|prompt_run_id|run_id`: no matches.
- Delivered-doc safety grep for local absolute paths and sensitive configuration terms: no matches.
- Markdown link validation for Stage 12 user docs and docs index: pass.
- Route/docs consistency checked against `web/src/app/route-config.tsx` and `rt-s12-002-browser-e2e.md`.

Unrun full suites:

- Full backend suite was not run; replacement evidence is the Stage 12 focused backend/API/service aggregate plus previously accepted RT-S12-002 evidence. Residual risk remains until the database can reach head.
- Full frontend suite beyond route-config was not run; replacement evidence is `typecheck`, `build`, route-config test, and attempted browser E2E. Residual risk remains because fresh E2E did not authenticate.

## Review And Fix Loop

- Loop 1:
  - Finding: local database was behind migration head.
  - Bounded fix attempted: run committed migration chain to head.
  - Result: blocked by table ownership; no code fix made.
- Loop 2:
  - Finding: `pnpm e2e` resolved the wrong Playwright CLI because local dependencies were incomplete.
  - Bounded fix: restored `@playwright/test` from lockfile and installed Chromium runtime.
  - Rerun: Playwright test launched.
- Loop 3:
  - Finding: Playwright webServer readiness was routed through proxy instead of localhost.
  - Bounded fix: added localhost no-proxy protection in `web/playwright.config.ts`.
  - Rerun: `pnpm e2e` reached the browser test.
- Loop 4:
  - Finding: browser test remained on login page because `ADMIN_API_KEY` was unavailable.
  - Result: not repairable without a valid authentication environment or approved test-auth path.

## Residual Risks

Accepted residuals:

- Local Playwright browser runtime is installed in the machine cache only and is not committed.
- Test-result screenshots/videos from failed E2E attempts are ignored by git and are not formal evidence.

Blocking residuals:

- Local database current/head mismatch: `current=2026_06_14_0006`, `head=2026_06_20_0001`.
- Local migration cannot advance because the configured DB user does not own `ohlcv_bars`.
- Fresh Gate Browser E2E cannot authenticate because `ADMIN_API_KEY` is unset in the current environment.

## Decision

`STAGE_12_GATE_BLOCKED`

Stage 12 is not finally accepted in this Gate run. Minimum next action is an environment repair session: provide a DB migration role/owner capable of reaching Alembic head and provide a valid admin API key through the approved local environment mechanism, then rerun the Stage 12 Gate verification commands and fresh Browser E2E.
