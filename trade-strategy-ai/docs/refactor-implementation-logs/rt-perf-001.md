# RT-PERF-001 Rule Pool Backtest Batch Selection and Result Merge

## Status

`RT_PERF_001_ACCEPTED`

## Scope

- Post-delivery performance/usability hardening after `STAGE_12_GATE_ACCEPTED`.
- This is not a Stage 12 repair and does not change accepted Stage 12 route retirement, governance, data-source, or formal result contracts.
- Formal user entry remains `/rules/backtests`; formal result entry remains `/rules/results`.

## Implementation Summary

- `rule-pool-backtest` keeps legacy `rule_id` compatibility and now accepts `rule_ids`.
- Added persistent rule pool batch run and batch records.
- Added batch service and formal UI API under `/rules/backtests/batch-runs`.
- Extended `/rules/backtests` with `单次正式回测` and `规则池批量回测`.
- Extended `/rules/results?batch_run_id=...` to show merged rule pool results and batch provenance.

## Database Migration

- Added migration `2026_06_30_0001_rule_pool_backtest_batches.py`.
- New tables:
  - `rule_pool_backtest_batch_runs`
  - `rule_pool_backtest_batches`
- Downgrade refuses to drop data when running, completed, merged, or result-linked batch runs exist.

## Review And Fix Loop

- Loop 1: Added failing tests for `rule_ids` compatibility, batch persistence/service/API, frontend API, and page/result wording.
- Loop 2: Implemented models, migration, repository, service, API, and UI.
- Loop 3: Fixed job parameter validation for `rule_ids` and `profile_id`; preserved old `rule_id` fallback and no-rule all-rules behavior.
- Loop 4: Fixed async SQLAlchemy serialization and UUID handling in service tests.

## Verification

- `python -m scripts.web_local env-check`: passed with redacted output.
- `python -m cli.main db-check --config config/app.template.yaml`: `DB OK: 1`.
- `python -m alembic -c src/db/migrations/alembic.ini heads`: `2026_06_30_0001 (head)`.
- `python -m alembic -c src/db/migrations/alembic.ini current`: `2026_06_30_0001 (head)` after migration verification.
- `python -m alembic -c src/db/migrations/alembic.ini upgrade head`: passed.
- `python -m alembic -c src/db/migrations/alembic.ini downgrade 2026_06_20_0001`: passed on local database with no batch run data.
- `python -m alembic -c src/db/migrations/alembic.ini upgrade head`: passed again, returning database to head.
- `python -m pytest tests/unit/services/test_job_runner.py::test_submit_rule_pool_backtest_prefers_rule_ids_over_legacy_rule_id tests/unit/services/test_job_runner.py::test_submit_rule_pool_backtest_keeps_all_rules_behavior_when_no_rule_id tests/unit/db/repositories/test_rule_pool_backtest_batch_repository.py tests/unit/services/test_rule_pool_backtest_batch_service.py tests/api/routers/test_formal_backtests.py::test_operator_can_create_start_and_merge_rule_pool_batch_run -q`: `7 passed`.
- `python -m pytest tests/unit/services/test_job_runner.py::test_submit_rule_pool_backtest_binds_regime_artifacts tests/unit/services/test_job_runner.py::test_submit_rule_pool_backtest_prefers_rule_ids_over_legacy_rule_id tests/unit/services/test_job_runner.py::test_submit_rule_pool_backtest_keeps_all_rules_behavior_when_no_rule_id tests/unit/db/repositories/test_rule_pool_backtest_batch_repository.py tests/unit/services/test_rule_pool_backtest_batch_service.py tests/api/routers/test_formal_backtests.py -q`: `19 passed`, one pre-existing asyncpg cleanup warning.
- `python -m pytest tests/unit/db/test_migrations.py -q`: `11 passed`.
- `cd web && PATH=<Node 18 bin>:$PATH pnpm test -- src/lib/api/backtests.test.ts src/features/backtest/backtest-center.stage6.test.tsx`: `8 passed`.
- `cd web && PATH=<Node 18 bin>:$PATH pnpm typecheck`: passed.
- `cd web && PATH=<Node 18 bin>:$PATH pnpm test -- src/app/route-config.test.tsx src/lib/api/backtests.test.ts src/features/backtest/backtest-center.stage6.test.tsx`: `20 passed`.
- `cd web && PATH=<Node 18 bin>:$PATH pnpm build`: passed.
- `git diff --check`: passed.
- Ordinary-user docs terminology grep: no matches.
- Changed-files sensitive value / local path scan: no matches.

## Pending Verification

- Full backend suite not run; targeted service/repository/API/migration coverage plus migration upgrade/downgrade verification covered this task surface.
- Full frontend suite not run; targeted API/page/route tests, typecheck, and build covered the changed frontend surface.
- Browser E2E not run for this post-delivery hardening task; no new ordinary-user route was added, and focused route/API/UI tests verified the accepted route boundary remains intact.

## Acceptance Conclusion

`RT_PERF_001_ACCEPTED`
