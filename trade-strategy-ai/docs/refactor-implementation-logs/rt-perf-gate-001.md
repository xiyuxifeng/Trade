# RT-PERF-GATE-001 Rule Pool Batch Backtest and Shared Cache Gate Review

Date: 2026-07-01

Status: `RT_PERF_GATE_001_ACCEPTED`

## Scope

- Gate review for `RT-PERF-001 Rule Pool Backtest Batch Selection and Result Merge` and `RT-PERF-002 Shared Market Context Cache for Rule Pool Backtest`.
- This Gate did not change the accepted Stage 12 route, governance, lifecycle, data-source, documentation, prompt, schema, or result semantics contracts.
- Formal user entry remains `/rules/backtests`; formal result entry remains `/rules/results`.
- No ordinary-user Workflow / Job / Pipeline / Artifact main entry was added.

## Review Summary

- `RT-PERF-001`: accepted after bounded repairs. Batch run create/split/start/status/merge and `/rules/results?batch_run_id=...` are usable. Merge rejects incomplete/failed/missing/conflicting batches and now accepts the real `JobRunner` `ServiceResult.payload` shape.
- `RT-PERF-002`: accepted. `run_rules_backtest()` still shares preloaded OHLCV `forward_bars`, preloads market context / fallback indicators once per trade date, keeps `_backtest_single_rule()` old behavior when no cache is passed, and does not introduce engine parallelism.
- Backward compatibility: `rule_id`, `rule_ids`, and no-rule-id all-approved + min-confidence behavior are covered by focused tests.
- Stage 12 contract: route-config, formal rule pages, result pages, System Management separation, and ordinary-user terminology boundary remain unchanged.

## Findings And Bounded Fixes

### Finding 1: profile runtime config branch referenced `loaded.config_path`

- Evidence: bounded real-data smoke created two `rule-pool-backtest` jobs, but execution failed after secret injection with `UnboundLocalError: cannot access local variable 'loaded'`.
- Root cause: `_default_engine_factory(config=..., base_dir=...)` is used by `profile_id` runtime config, but still passed `str(loaded.config_path)` to `SnapshotLoader`; `loaded` only exists in the config-file branch.
- Fix: preserve `loaded_config_path` only when loading from a file and pass `None` for runtime config.
- Regression: `tests/unit/services/test_backtest_service.py::test_default_engine_factory_accepts_runtime_config_without_loaded_config`.

### Finding 2: merge validator did not accept real JobRunner result payloads

- Evidence: bounded real-data smoke completed both batch jobs, but merge rejected both batches as parameter conflicts.
- Root cause: `RulePoolBacktestBatchService` expected top-level `request` / `result`, while real completed jobs store a serialized `ServiceResult` with request/result fields under `payload`.
- Fix: normalize batch `result_json` through helper extraction, validate parameters from `payload` when top-level `request` is absent, and build merge summaries from `payload.result` / `payload.summary`.
- Regression: `tests/unit/services/test_rule_pool_backtest_batch_service.py::test_batch_service_merges_job_service_result_payload_and_keeps_rule_provenance`.

### Finding 3: no-trade completed batches lost rule-level provenance

- Evidence: real small batch produced truthful zero-trade summaries, so `rule_regime_metrics` was empty and merged `rule_results` would have been empty.
- Fix: when completed batch metrics are empty, populate rule-level provenance from the batch `rule_ids`, preserving `batch_run_id`, `batch_id`, `batch_index`, `job_id`, and `source_result_reference`.

### Finding 4: targeted E2E locators were ambiguous

- Evidence: first targeted E2E run reached the page but strict locators matched duplicate text for `创建批次计划`; the second reached the merged result page but matched the batch id twice.
- Fix: target the button role for `创建批次计划` and the exact `批次计划：<batch_run_id>` text on the result page.

## Small Real-Data Smoke

Scope:

- 3 approved rules.
- Date range: `2024-05-27` to `2024-05-31`.
- `batch_size=2`.
- `profile_id=default`.
- Current DB data only; no live provider fetch, broad backfill, article recrawl, or LLM call.

Evidence:

- Preflight counts: approved rules `7`; OHLCV rows `124`, date range `2024-05-06` to `2026-04-20`, distinct symbols `86`; dataset snapshots `3`; market snapshots `2`; market states `2`; no existing batch runs before smoke.
- Accepted smoke batch run: `rpbt-82b08f0f6f6449938306451eaf33f6bb`.
- Created 2 batches from 3 rules.
- Started jobs: `900df7e9-f664-4e03-bbe3-c7a3c53b4701`, `64f6e86a-abca-437b-8b4f-fdf80026c2d9`.
- Both jobs completed with status `success`.
- Batch run refreshed to `completed`, then merged to `merged-rpbt-82b08f0f6f6449938306451eaf33f6bb`.
- Merged summary: `total_days=0`, `total_trades=0`, `valid_trades=0`, `skipped_trades=0`.
- Merged rule provenance count: `3`, with each selected rule bound to its `batch_index`, `job_id`, and source result reference.

Residual risk:

- The smoke proves the batch chain and merge/provenance path on real DB objects, but the selected rules/date window produced zero trades. This is accepted as a truthful no-sample result, not performance evidence for non-empty trading samples.

## Targeted E2E

Spec:

- `web/tests/e2e/rule-pool-batch-backtest-smoke.spec.ts`

Command:

- `cd web && PATH=<Node 18 bin>:$PATH pnpm exec playwright test tests/e2e/rule-pool-batch-backtest-smoke.spec.ts`

Result:

- Final rerun passed: `1 passed`.
- Covered `/rules/backtests` UI visit, batch tab switch, current DB approved-rule selection via API, batch create, batch start, local worker execution for the created jobs, status refresh, merge, and `/rules/results?batch_run_id=...` result view.

Notes:

- `cd web && PATH=<Node 18 bin>:$PATH pnpm e2e -- rule-pool-batch-backtest-smoke` did not filter as intended and also ran the Stage 12 E2E; Stage 12 E2E passed in that run.
- A sandboxed E2E attempt failed to bind the local API port; elevated rerun was required for local webServer startup.

## RT-PERF-001 Review Result

- `/rules/backtests` remains the formal backtest entry.
- `/rules/results` remains the formal result entry.
- UI separates `单次正式回测` and `规则池批量回测`.
- Multi-rule selection, `batch_size`, batch plan creation, split, start, status tracking, merge, and result-page viewing are implemented and verified.
- Batch start creates existing `rule-pool-backtest` jobs with `rule_ids`.
- Merge rejects incomplete/failed/missing/conflicting batches and now supports real job result payloads.
- Merge preserves provenance at rule level, including `batch_run_id`, `batch_id`, `job_id`, `rule_id`, and source result reference.

Merge validation coverage:

- Verified: `start_date`, `end_date`, `min_confidence`, `market_regime_version`, `profile_id`.
- Not separately present in `rule-pool-backtest` job payload: scoring profile, dataset snapshot id, and dataset fingerprint. This Gate did not change result semantics to invent unavailable fields.

## RT-PERF-002 Review Result

- `run_rules_backtest()` preloads shared OHLCV `forward_bars`.
- Market context with loader is loaded once per trade date.
- Fallback indicators without loader are derived once per trade date.
- `_backtest_single_rule()` without `market_contexts_by_date` preserves old loader/no-loader behavior.
- Checkpoint fields remain unchanged: `rule_index`, `rule_results`, `current_rule_state`, `trade_date_index`, `hit_returns`, `hit_count`, `total_checks`, `regime_returns`, `source_feature_version`.
- Cached/uncached core result equivalence is covered for total trades, hit trades, hit rate, average return, market-state metrics, and source feature version.
- Source scan found no `ThreadPoolExecutor`, `ProcessPoolExecutor`, `multiprocessing`, `asyncio.gather`, or `create_task` in `src/backtest/engine.py`.

## Verification

Backend / DB:

- `python -m scripts.web_local env-check`: pass, redacted output only.
- `python -m cli.main db-check --config config/app.template.yaml`: pass, `DB OK: 1`.
- `python -m alembic -c src/db/migrations/alembic.ini current`: pass, `2026_06_30_0001 (head)`.
- `python -m alembic -c src/db/migrations/alembic.ini heads`: pass, `2026_06_30_0001 (head)`.
- Focused backend aggregate: pass, `14 passed`.
- `python -m pytest tests/unit/db/test_migrations.py -q`: pass, `11 passed`.

Frontend / E2E:

- `cd web && PATH=<Node 18 bin>:$PATH pnpm typecheck`: pass.
- `cd web && PATH=<Node 18 bin>:$PATH pnpm test -- src/app/route-config.test.tsx src/lib/api/backtests.test.ts src/features/backtest/backtest-center.stage6.test.tsx`: pass, `20 passed`.
- `cd web && PATH=<Node 18 bin>:$PATH pnpm build`: pass.
- Targeted E2E command above: pass, `1 passed`.

Safety:

- `git diff --check`: pass.
- `src/backtest/engine.py` parallelism source scan: no matches.
- Changed-files secret/local-path scan: no real secret or local absolute path matches after removing generated runtime directories.
- Formal ordinary-user docs terminology grep was not rerun against all historical logs because historical logs intentionally contain old technical terms; Stage 12 delivered ordinary-user docs remain unchanged by this Gate.

Migration downgrade:

- Downgrade/upgrade was not rerun after the real smoke because the local DB now contains completed/merged rule-pool batch data and the migration intentionally refuses unsafe downgrade when result-linked batch data exists. Replacement evidence: current/head at `2026_06_30_0001 (head)`, migration unit tests `11 passed`, and RT-PERF-001 prior empty-data downgrade/upgrade evidence.

## Review And Fix Loop

- Loop 1: reviewed RT-PERF-001/002 docs, code, tests, route config, UI, services, models, API routers, and recent commits.
- Loop 2: ran environment and DB preflight; confirmed current/head, approved rules, OHLCV, snapshots, market states, auth readiness, and no pre-existing batch runs.
- Loop 3: real smoke exposed profile runtime config bug; added RED test, fixed, reran test.
- Loop 4: real smoke exposed merge payload-shape/provenance bug; added RED test, fixed, reran batch service tests.
- Loop 5: completed real smoke merge and verified result provenance.
- Loop 6: added targeted E2E; fixed two locator issues; reran targeted spec to pass.
- Loop 7: reran focused backend/frontend/migration/build/safety verification.

## Accepted Residual Risks

- Real smoke produced zero trades because the selected rules/date range had no eligible triggered samples; the Gate accepts this as truthful no-sample evidence for chain correctness, not as performance timing evidence for non-empty samples.
- Full backend and full frontend suites were not run; replacement evidence is focused runtime/service/API/migration/frontend/build/E2E coverage for this Gate surface.
- Prompt regression was not run because this Gate changed no prompt, prompt loader, or prompt schema contract.

## Decision

`RT_PERF_GATE_001_ACCEPTED`

`RT-PERF-001` and `RT-PERF-002` pass this Gate. Do not automatically start Backtest Performance Instrumentation or Parallel Rule Executor.
