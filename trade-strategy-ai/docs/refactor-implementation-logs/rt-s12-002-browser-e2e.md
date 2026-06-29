# RT-S12-002 Browser E2E Acceptance

## Status

`RT_S12_002_BROWSER_E2E_ACCEPTED`

## Scope

- Task: `RT-S12-002 Browser E2E Acceptance`
- Execution path used formal UI routes plus formal UI/API endpoints.
- `RT-S12-003`, Stage 12 Gate, user documentation generation, broad live provider refresh, article recrawl, broad market backfill, and LLM execution were not started.
- Reference-chain records remain setup/comparison evidence only. They were not counted as final Browser E2E pass evidence.

## Formal route sequence

- `/research/add`
- `/research/articles`
- `/research/results`
- `/rules/review`
- `/rules/backtests`
- `/rules/results`
- `/authors`
- `/strategies`
- `/daily/pre-market`
- `/daily/after-close`

The Browser E2E test checked these formal routes through Playwright and rejected user-visible legacy terms including `Job`, `Workflow`, `Pipeline`, `Artifact`, and `config_path` on the visited formal pages.

## Separate final E2E evidence

- E2E run id: `rt-s12-002-e2e-1782743876308`
- ArticleRevision: `b64a3c51-bf32-562c-8a86-849eac28ad72`
- Prompt version: `article_analysis_v1`
- Schema version: `article_analysis_v1`
- RuleVersion: `8d15ae78-4abb-40ef-9a6e-184bb7289d0c`
- BacktestRun: `f6a90723-3d8c-472b-b057-cc58238974b8`
- BacktestResult: `3fd98591-c9b4-4959-b1e5-598f9db979d7`
- DatasetSnapshot: `b534d59d-851a-4a78-a32d-af6e71a4e71f`
- Pre-market MarketSnapshot: `88aa0f65-0fb8-41fb-aee8-cb8bbdb33a6f`
- Post-close MarketSnapshot: `9646ace9-a755-485d-89f4-4900602bde30`
- Pre-market MarketState: `a8c2d82f-8db9-41ad-aec7-4c79f42c701f`
- Post-close MarketState: `f9084b48-020a-4493-84a0-f2994e7dbccf`
- RuleApplicabilityProfile stable id: `d4e78900-7326-42a1-b28e-1f83583ee358`
- RuleApplicabilityProfile row id: `54f553dd-9f79-4fdd-9067-128e3fa67671`
- AuthorMethodProfileVersion: `878294da-85b8-46b1-ada7-a66287468526`
- AuthorRuleProfileVersion: `99b44c67-77f5-40b4-99c9-5fa17b88dad8`
- AuthorValidatedProfileVersion: `04327d22-1c64-4604-9477-8ef9786b9162`
- StrategyVersion: `b0ef4ad1-3753-4115-966a-4e816a591f42`
- Strategy validation state: `passed`
- Current published strategy pointer: `b0ef4ad1-3753-4115-966a-4e816a591f42`
- DailyRuleSelection: `65e08166-a346-4b3e-bed7-96cfe156c078`
- DailyStrategyInstance: `539023df-cfba-484f-9fe7-be7a8723e5ef`
- TradingDayPlan: `66b87fa8-f3a8-454f-8e06-c1dbd6b71ee2`
- PostMarketReview: `afc638fa-fb22-4d11-96df-38ebe5949aac`
- OptimizationProposal records:
  - RuleOptimizationProposal: `2b675c91-3014-471b-97e5-24609e0d0b38`
  - AuthorProfileRevisionProposal: `a005dd39-78fe-4dac-bec2-947b2c3ad19c`
  - StrategyRevisionProposal: `1420a163-7625-4066-977f-14c2998cdd0a`

## Boundary review

- Reference-chain StrategyVersion `6bbaf1a0-0b97-4254-a9b2-b7d696260849`, DailyRuleSelection `8db45d9a-d944-4686-a1ab-d2564552ba85`, TradingDayPlan `ce6dd260-c916-4151-bb33-4361837b19fa`, PostMarketReview `4249b5b2-6e9a-4c93-88c8-d76c4fa47429`, and its proposal records were not counted as final Browser E2E pass evidence.
- Final E2E generated new BacktestRun, BacktestResult, RuleApplicabilityProfile, AuthorProfileVersion, StrategyVersion, DailyRuleSelection, DailyStrategyInstance, TradingDayPlan, PostMarketReview, and OptimizationProposal IDs listed above.
- Strategy publication evidence includes a separate publish transition and a current published pointer to the final E2E StrategyVersion.
- Browser E2E did not directly insert database rows. It used formal UI routes and formal UI/API endpoints.

## Review and bounded fix loop

- Loop 1:
  - Finding: no true Playwright Browser E2E existed for the formal product journey.
  - Fix: added `web/tests/e2e/stage12-browser-acceptance.spec.ts` and changed Playwright webServer to start the formal local API/frontend server.
  - Rerun: `pnpm build` passed after lint fixes; E2E then exposed missing browser runtime.
- Loop 2:
  - Finding: Chromium runtime was missing.
  - Fix: ran `pnpm e2e:install` for this authorized Browser E2E task.
  - Rerun: Browser launched and reached the formal applicability publish step.
- Loop 3:
  - Finding: formal API had review/generate applicability endpoints but no publish endpoint.
  - Fix: added `/api/ui/v1/rules/backtests/applicability-profiles/{profile_id}/publish`, `BacktestApplicationService.publish_applicability_profile`, and OpenAPI/API tests.
  - Rerun: focused formal backtest API tests and OpenAPI contract passed.
- Loop 4:
  - Finding: repeated E2E attempts exposed non-idempotent RuleApplicabilityProfile generation and a conflict with the existing unique `applicability_profile_id` contract.
  - Fix: reuse existing profile for the same formal run/result evidence; generate a new stable applicability id for new evidence and keep supersession on row ids.
  - Rerun: rule applicability service tests and formal backtest API tests passed.
- Loop 5:
  - Finding: formal applicability API responses did not expose lifecycle state required as publish evidence.
  - Fix: included `lifecycle_state` in `RuleApplicabilityProfile.to_dict()`.
  - Rerun: rule applicability service and formal backtest API tests passed.
- Loop 6:
  - Finding: E2E strategy evidence used row `profile_id` instead of stable `applicability_profile_id`, and used singular `backtest_run_id` / `backtest_result_id` fields.
  - Fix: E2E now binds strategy evidence to stable applicability ids and formal plural backtest evidence fields.
  - Rerun: web typecheck passed; E2E advanced through strategy validation and publish.
- Loop 7:
  - Finding: Strategy publish allowed multiple current strategy pointers while pre-market readiness requires one global current formal strategy.
  - Fix: `StrategyRepository.set_current_published_version` now clears other current strategy pointers in the same formal publish transaction.
  - Rerun: strategy, pre-market, daily rule selection, and daily trading plan focused tests passed; final Browser E2E passed.

## Verification

- `python -m scripts.web_local env-check`: pass.
- `python -m cli.main db-check --config config/app.template.yaml`: pass.
- `python -m alembic -c src/db/migrations/alembic.ini current`: pass, current/head `2026_06_20_0001`.
- `python -m pytest tests/unit/services/test_rule_applicability_service.py tests/api/routers/test_formal_backtests.py tests/api/test_ui_openapi_contract.py tests/unit/services/test_strategy_center_service.py tests/api/routers/test_strategies.py tests/unit/services/test_pre_market_readiness_service.py tests/unit/services/test_daily_rule_selection_service.py tests/unit/services/test_daily_trading_plan_service.py -q`: pass in focused groups during the fix loop.
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm typecheck`: pass.
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm test -- src/app/route-config.test.tsx`: pass, `12 passed`.
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm e2e`: pass, `1 passed`.
- `git diff --check`: pass.
- Changed-files secret scan: pass, no secret values found.

## Known risks

- Browser E2E installed Chromium runtime under the local Playwright cache for this authorized task. Runtime cache files are not committed.
- Several failed E2E attempts created non-final formal rows before the accepted run. They are not counted as final evidence.
- Post-close and proposal records reflect the available partial post-close evidence truthfully; no missing, partial, invalid, degraded, or unavailable state was rewritten to success.

## Decision

`RT_S12_002_BROWSER_E2E_ACCEPTED`

Next allowed task is `RT-S12-003 用户文档`, only after explicit user authorization. Stage 12 Gate remains not started.
