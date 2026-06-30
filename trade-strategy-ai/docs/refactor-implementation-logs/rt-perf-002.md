# RT-PERF-002 Shared Market Context Cache for Rule Pool Backtest

## Status

`RT_PERF_002_ACCEPTED`

## Scope

- Post-delivery performance hardening after `STAGE_12_GATE_ACCEPTED`.
- This is not a Stage 12 repair and does not change accepted Stage 12 route, governance, lifecycle, data-source, schema, UI, API, or result semantics.
- No database schema migration was added.

## Implementation Summary

- Added a rule-pool backtest shared market context cache keyed by trade date.
- `run_rules_backtest()` still preloads shared OHLCV `forward_bars`, then preloads market context / fallback indicators once per trade date before entering the per-rule loop.
- `_backtest_single_rule()` now accepts optional `market_contexts_by_date`; when provided, it reads indicators, market state, and source feature version from the cache and does not call `loader.load_market_context()` or `_derive_indicators_from_bars()`.
- Direct `_backtest_single_rule()` calls without the new optional parameter keep the previous loader / no-loader behavior.
- Cache debug evidence records `shared_context_cache_enabled`, `trade_dates_count`, `cached_context_dates_count`, `loader_context_load_count`, `derived_context_dates_count`, and `missing_context_dates_count`.

## Performance Shape

- Before: each rule loaded or derived market context for each trade date, producing up to `rules x trade_dates` loader calls or indicator derivations.
- After: `run_rules_backtest()` loads or derives market context once per trade date, producing `trade_dates` loader calls or derivations, then all rules share the cached context.

## Checkpoint And Resume Compatibility

- Existing outer checkpoint fields remain unchanged: `rule_index`, `rule_results`, and `current_rule_state`.
- Existing per-rule checkpoint fields remain unchanged: `trade_date_index`, `hit_returns`, `hit_count`, `total_checks`, `regime_returns`, and `source_feature_version`.
- Resume still skips completed rules and can continue the current rule from its trade-date checkpoint.

## Review And Fix Loop

- Loop 1:
  - Finding: current implementation still called `loader.load_market_context()` and `_derive_indicators_from_bars()` `rules x trade_dates`.
  - Fix: added RED tests proving expected per-date call count.
  - Rerun: RED tests failed with call count `6 != 3`.
- Loop 2:
  - Finding: shared cache needed to preserve old `_backtest_single_rule()` compatibility.
  - Fix: added `_preload_rule_backtest_market_contexts()` and optional `market_contexts_by_date`; old path remains when the argument is omitted.
  - Rerun: focused tests passed after correcting a test fixture to use existing `op/field/value` condition format.
- Loop 3:
  - Finding: cache debug metric should count attempted loader date loads even when a date fails.
  - Fix: moved `loader_context_load_count` increment before awaiting the loader.
  - Rerun: affected focused test aggregate passed.

## Verification

- `python -m pytest tests/unit/backtest/test_rule_pool_backtest.py::TestBacktestEngineRulePool::test_run_rules_backtest_loads_market_context_once_per_trade_date tests/unit/backtest/test_rule_pool_backtest.py::TestBacktestEngineRulePool::test_run_rules_backtest_derives_indicators_once_per_trade_date_without_loader -q`: initial RED failed with `6 != 3`; final rerun passed, `2 passed`.
- `python -m pytest tests/unit/backtest/test_rule_pool_backtest.py::TestBacktestEngineRulePool::test_backtest_single_rule_cache_keeps_core_statistics_compatible tests/unit/backtest/test_rule_pool_backtest.py::TestBacktestEngineRulePool::test_run_rules_backtest_resumes_from_rule_index tests/unit/backtest/test_rule_pool_backtest.py::TestBacktestEngineRulePool::test_backtest_single_rule_returns_result -q`: `3 passed`.
- `python -m pytest tests/unit/backtest/test_rule_pool_backtest.py -q`: `16 passed`.
- `python -m pytest tests/unit/backtest/test_rule_pool_backtest.py tests/unit/backtest/test_reproducibility.py tests/unit/services/test_backtest_service.py tests/unit/services/test_job_runner.py::test_submit_backtest_jobs_write_progress_to_job_record tests/unit/services/test_job_runner.py::test_submit_rule_pool_backtest_binds_regime_artifacts tests/unit/services/test_job_runner.py::test_submit_rule_pool_backtest_prefers_rule_ids_over_legacy_rule_id tests/unit/services/test_job_runner.py::test_submit_rule_pool_backtest_keeps_all_rules_behavior_when_no_rule_id -q`: `24 passed`.
- `python -m pytest tests/unit/backtest/test_engine.py tests/unit/backtest/test_engine_regime_context.py tests/unit/backtest/test_rule_pool_backtest.py tests/unit/backtest/test_reproducibility.py -q`: `38 passed`.
- `python -m scripts.web_local env-check`: passed with redacted output.
- `python -m cli.main db-check --config config/app.template.yaml`: `DB OK: 1`.
- `python -m alembic -c src/db/migrations/alembic.ini current`: `2026_06_30_0001 (head)`.
- `python -m alembic -c src/db/migrations/alembic.ini heads`: `2026_06_30_0001 (head)`.
- Source scan for `ThreadPoolExecutor`, `ProcessPoolExecutor`, `multiprocessing`, `asyncio.gather`, and `create_task` in `src/backtest/engine.py`: no matches.

## Pending Verification

- Full backend suite was not run; focused backtest engine, reproducibility, BacktestService, and JobRunner rule-pool tests covered the changed runtime path.
- Frontend tests were not run because this task changed no frontend source, route, API contract, or user-facing text.
- Browser E2E was not run because this post-delivery hardening task changed no ordinary-user route or accepted Stage 12 product journey.
- Prompt regression was not run because no prompts, prompt loader, or schema contracts changed.

## Residual Risks

- Real-data runtime speedup still depends on actual rule count, trading date range, and loader latency; small-batch timing should be observed separately.
- Cache is per `run_rules_backtest()` invocation and intentionally not persisted across jobs.

## Acceptance Conclusion

`RT_PERF_002_ACCEPTED`
