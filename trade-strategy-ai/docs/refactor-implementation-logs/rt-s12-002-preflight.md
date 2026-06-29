# RT-S12-002 Preflight — Tooling, Config, Data, and E2E Readiness

## 0C. 2026-06-29 Reference chain completion repair

- Status: `READY_FOR_RT_S12_002_IMPLEMENTATION`
- Scope remained bounded to reference-chain completion. Final `RT-S12-002`
  Browser E2E Acceptance, `RT-S12-003`, Stage 12 Gate, user documentation,
  broad live provider refresh, article recrawl, broad market backfill, and LLM
  execution were not started.
- Boundary: this repair/reference chain is pre-E2E smoke/contract evidence
  only. Browser E2E Acceptance must still generate or lifecycle-transition a
  separate final E2E chain and record new object IDs or new audit/lifecycle
  transitions.
- DB recheck: reference IDs recorded by the prior repair still existed. The
  prior StrategyVersion remained `6bbaf1a0-0b97-4254-a9b2-b7d696260849`;
  the DB is now the source of truth for the additional reference-chain IDs
  below.

Validation repair:

- Root cause: `StrategyCenterService.validate_version` expected flat sample
  coverage fields, while formal `BacktestResult.coverage_json` stores nested
  sample coverage under `samples`. The real result evidence had sample count
  `40` and sample state `ready`; it was not being read by the validation
  summary.
- Repair: validation now reads nested `BacktestResult.coverage_json`, uses
  `BacktestResult.status` as execution evidence, and reports level-1
  market-state coverage as `not_required` when formal result coverage records
  market-state checks as not required.
- Strategy validation result:
  - Strategy `15416124-5087-4cbc-998b-ca107423c74b`
  - StrategyVersion `6bbaf1a0-0b97-4254-a9b2-b7d696260849`
  - validation state `passed`
  - `out_of_sample_state=not_required`
  - `sample_coverage.state=sufficient`
  - `sample_count=40`
  - evidence source: BacktestRun `ec58660b-7a34-46e3-8744-b2cec0436655`,
    BacktestResult `46f17a5c-5895-427f-8b6b-19d309aeafac`
- Published reference strategy evidence:
  - `current_published_version_id=6bbaf1a0-0b97-4254-a9b2-b7d696260849`
  - audit/lifecycle transitions include `submitted_for_review`, `validated`,
    and `published`

Additional bounded repairs:

- `BacktestRunRepository.find_dataset_snapshot` now rejects future dataset
  snapshots for requested backtest end dates to avoid point-in-time leakage.
- Pre-market readiness accepts snapshot-unbound level-1 global applicability
  profiles while retaining exact snapshot binding for snapshot-bound profiles.
- Post-close actual comparisons normalize naive database datetimes as
  Asia/Shanghai timestamps before cutoff comparison.

Reference chain generated:

- Dataset-bound BacktestRun `cd19b7bc-ff03-47ae-8183-79bd36258a51`
- Dataset-bound BacktestResult `8571385f-1a3a-40d5-82fb-3cd7c205aa55`
- RuleApplicabilityProfile stable id `e49756c0-21c1-4558-a57f-aabd7c91f94d`
- RuleApplicabilityProfile row id `ea020370-e641-41ea-9791-69688a72a38e`
- DailyRuleSelection `8db45d9a-d944-4686-a1ab-d2564552ba85`
- DailyStrategyInstance `9a8858ec-70c1-4348-bc41-b969dd131d40`
- TradingDayPlan `ce6dd260-c916-4151-bb33-4361837b19fa`
- PostMarketReview `4249b5b2-6e9a-4c93-88c8-d76c4fa47429`
- RuleOptimizationProposal `0d82c843-0130-435d-af0e-9b507c228de8`
- AuthorProfileRevisionProposal `f328e549-8be8-4ab1-b07b-fb287872a806`
- StrategyRevisionProposal `0cad8dc4-a2b6-4961-9e8e-2d356df67fca`

Verification:

- `python -m scripts.web_local env-check`: pass.
- `python -m cli.main db-check --config config/app.template.yaml`: pass.
- `python -m alembic -c src/db/migrations/alembic.ini current`: pass,
  current/head `2026_06_20_0001`.
- Focused backend aggregate: pass, `73 passed`.
- `web` typecheck with Node 18: pass.
- `web` route-config test: pass, `12 passed`.
- `git diff --check`: pass.
- Changed-files secret scan: pass, no matches.

Residual:

- Browser E2E Acceptance remains unstarted.
- The reference chain does not satisfy final E2E pass evidence. Final E2E must
  use a separate chain or new lifecycle/audit transitions.
- Post-close review/proposal evidence states reflect the available partial or
  invalid actuals truthfully; they were not overwritten to ready.

## 0A. 2026-06-25 BacktestRun schema compatibility repair

- Status: `BACKTESTRUN_SCHEMA_REPAIR_ACCEPTED_WITH_RESIDUALS`
- Scope remained code/schema compatibility only; `RT-S12-002` browser E2E,
  `RT-S12-003`, Stage 12 Gate, live provider refresh, live crawl, LLM execution,
  market backfill, and business evidence repair were not started by this repair.
- No articles, OHLCV, DatasetSnapshot, MarketSnapshot, MarketRegime,
  RuleVersion, BacktestRun, BacktestResult, RuleApplicabilityProfile, author
  profile, strategy, daily plan, or optimization-proposal evidence was imported,
  seeded, recreated, supplemented, or counted as current RT-S12-002 evidence.
- Root cause: ORM mapped `BacktestRun.status` through
  `SAEnum(BacktestRunStatus, name="backtest_run_status")`, while committed
  migration `2026_06_18_0010_stage6_backtest_run_foundation.py` creates
  `backtest_runs.status` as `String(32)`.
- Repair: `BacktestRun.status` now maps to `String(32)` in
  `src/models/stage2_canonical.py`; `BacktestRunStatus` remains a Python
  `StrEnum` / service-layer allowed-value constant.
- Verification: focused metadata plus requested service tests passed
  (`23 passed`); broader touched model metadata tests passed (`5 passed`);
  `git diff --check` passed; changed-files secret scan had no matches.
- Residual: canonical downstream evidence and data-readiness blockers recorded
  in this preflight remain separate from this schema compatibility repair.

## 0B. 2026-06-25 Minimal canonical evidence repair resume on original data device

- Status: `STILL_BLOCKED`
- Latest pulled schema repair commit: `85ea013 fix(backtest): align run status schema`
- Entry decision accepted: `BACKTESTRUN_SCHEMA_REPAIR_ACCEPTED_WITH_RESIDUALS`
- Scope remained bounded to resuming canonical evidence repair from `BacktestRun`; final RT-S12-002 browser E2E, RT-S12-003 user documentation, and Stage 12 Gate were not started.
- Original data-device confirmation: the prior repaired selected articles, executable candidate, OHLCV rows, DatasetSnapshots, MarketSnapshots, MarketRegimes, and in-review RuleVersion were present before continuing.
- LLM actions: no LLM call was made. Deterministic minimal author profile generation was sufficient because the selected structured article/candidate, formal rule, backtest result, and applicability evidence already existed; generated profile records explicitly store `llm_called=false` where applicable.
- Live provider actions: no article recrawl, broad OHLCV backfill, Kaipan refresh, or market-state live refresh was run.

Reused baseline evidence:

- Articles: selected subset count `5`.
- Executable article/candidate:
  - article `84558067-1ba1-4248-9700-fd4225be8593`
  - revision `b64a3c51-bf32-562c-8a86-849eac28ad72`
  - prompt run `b5289dd7-8a5e-4d89-9c83-7555f8cc45a5`
  - candidate `af289b09-d9f1-44e1-8ce3-dfd87c84322d`
  - fingerprint `32db69f061d899626664245410ce67879746788effbe3a0bd83bfa4e72d704b8`
- OHLCV:
  - `002104.SZ`: 20 rows, `2024-05-06` to `2024-05-31`
  - `603280.SH`: 20 rows, `2024-05-06` to `2024-05-31`
- DatasetSnapshots:
  - `680a9e4a-8cb4-4131-8ef0-785031cb670b`, ready, fingerprint `9f56b30c66ca0ca11f53fe0452dd4e31e31ef4826cece9cd071561c2839f7538`
  - `b534d59d-851a-4a78-a32d-af6e71a4e71f`, ready, fingerprint `62bc2a46401cb6ffdf0f734443618079d0fc211c3bafded9e8393de19171d64c`
- MarketSnapshots:
  - pre-market `88aa0f65-0fb8-41fb-aee8-cb8bbdb33a6f`, quality `partial`, fingerprint `f59b3f131f253f120f8bae0cc25127b1b4aec5cc82932631d65eecb14ab3b5dc`
  - post-close `9646ace9-a755-485d-89f4-4900602bde30`, quality `partial`, fingerprint `611772f990a6eb57b70ae633045dbd851a411c4cf8f4acbd8934eb8d44d60c3c`
- MarketRegimes:
  - pre-market `a8c2d82f-8db9-41ad-aec7-4c79f42c701f`, label `selected_symbol_resilient`, confidence `0.35`, quality `partial`
  - post-close `f9084b48-020a-4493-84a0-f2994e7dbccf`, label `selected_symbol_resilient`, confidence `0.35`, quality `partial`

Records created or advanced:

- `BacktestRun` reused/created through `BacktestApplicationService`:
  - id `ec58660b-7a34-46e3-8744-b2cec0436655`
  - dataset `b534d59d-851a-4a78-a32d-af6e71a4e71f`
  - requested/effective level `level_1`
  - request fingerprint `5ec4d56e9a98e453743679adda8ae87686f74f3c367e9320109bc9978ccbeeae`
  - reproducibility fingerprint `58eb40747331614450dd7fd6163b3564914b5cadfde9f5412f827510d48660fe`
- `BacktestResult`:
  - id `46f17a5c-5895-427f-8b6b-19d309aeafac`
  - status `completed_valid`
  - result fingerprint `899d0793eb34dd6815ffd2b287811e875f8fdb17de01cca060400e88de0664e1`
  - reproducibility fingerprint `market-state-unbound:unavailable:899d0793eb34dd6815ffd2b287811e875f8fdb17de01cca060400e88de0664e1`
  - sample count `40`, coverage `ready`, total return `-0.028026`, win rate `0.475`, max drawdown `-0.12141497958111092`
- `RuleApplicabilityProfile`:
  - profile id `012a2a09-ea6a-4e3c-97e6-41a164e01eab`
  - stable applicability id `33a32c99-31df-4e97-9995-7eb31866812d`
  - review/lifecycle `published`
  - quality `partial`, recommendation `limited`
- Canonical author:
  - `4166623f-1689-42c2-bd90-c32dc7804391`
  - source `tgb`, source author key `10461311`, display name `javxsp`
- `RuleVersion`:
  - `8d15ae78-4abb-40ef-9a6e-184bb7289d0c`
  - transitioned through formal lifecycle service to `published` / display state `可用`
- `AuthorProfileVersion`:
  - method `03167004-d590-463d-837b-07b6ef22e19f`, published, quality `partial`
  - rule `b685bc3d-8ef7-4639-8aa7-32e03fb7c0eb`, published, quality `partial`
  - validated `5eda537a-e772-4df3-8986-4d646ebf3e23`, published, quality `unresolved`, source status `insufficient_evidence`
- `StrategyVersion`:
  - strategy `15416124-5087-4cbc-998b-ca107423c74b`
  - version `6bbaf1a0-0b97-4254-a9b2-b7d696260849`
  - lifecycle `draft`, not published
  - validation state `insufficient_coverage`

Readiness matrix:

| Evidence step | Status | Notes |
| --- | --- | --- |
| BacktestRun | READY | Formal service path, snapshot-only, no live provider |
| BacktestResult | READY | Completed with limited level-1 evidence |
| RuleApplicabilityProfile | READY | Published, but quality remains `partial` |
| AuthorProfileVersion | PARTIAL | Published method/rule profiles; validated profile is `unresolved` / `insufficient_evidence` |
| RuleVersion lifecycle | READY | Published through lifecycle service after fixed-set gate |
| Strategy / StrategyVersion | BLOCKED | Draft exists, but validation is `insufficient_coverage` |
| Published Strategy | BLOCKED | Not published; current published pointer is null |
| DailyRuleSelection | BLOCKED | Not generated because no published StrategyVersion |
| DailyStrategyInstance | BLOCKED | Not generated because no published StrategyVersion |
| TradingDayPlan | BLOCKED | Not generated because no DailyStrategyInstance |
| PostMarketReview | BLOCKED | Not generated because no TradingDayPlan |
| OptimizationProposal | BLOCKED | Not generated because no PostMarketReview |

Blocker:

- `StrategyCenterService.validate_version` truthfully returned `insufficient_coverage`.
- The validation summary shows dataset and market snapshots ready, backtest and applicability ready, but `backtest.out_of_sample_state=unavailable` and `sample_coverage.state=unknown`.
- Publishing the strategy, generating daily pre-market chain, and generating post-close/proposal evidence would require bypassing the formal validation contract, so the repair stopped.

Code/schema compatibility repairs made during the resume:

- `RuleApplicabilityRepository.record_audit`, `AuthorProfileRepository.record_audit`, and `StrategyRepository.record_audit` now set explicit `created_at` / `updated_at` values for audit rows because the current local DB columns are NOT NULL without usable server defaults.
- `RuleApplicabilityService.review_formal_profile` serializes the profile before session close and refreshes only persistent ORM rows.
- `RuleApplicabilityService.publish_formal_profile` adds an audited publish transition required by downstream strategy/daily consumers.

Verification:

- `python -m scripts.web_local env-check`: pass
- `python -m cli.main db-check --config config/app.template.yaml`: pass
- `python -m alembic -c src/db/migrations/alembic.ini current`: pass, current/head `2026_06_20_0001`
- `python -m pytest tests/unit/services/test_strategy_center_service.py::test_strategy_audit_writer_sets_explicit_timestamps tests/unit/services/test_author_profile_service.py::test_author_profile_audit_writer_sets_explicit_timestamps tests/unit/services/test_rule_applicability_service.py::test_rule_applicability_audit_writer_sets_explicit_timestamps tests/unit/services/test_rule_applicability_service.py::test_publish_formal_profile_marks_published_for_downstream_consumers -q`: pass, `4 passed`
- `cd web && PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH pnpm typecheck`: pass
- `cd web && PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH pnpm test -- src/app/route-config.test.tsx`: pass, `12 passed`
- `git diff --check`: pass
- changed-files secret scan: pass, no matches

Next allowed action:

- Repair the strategy validation evidence contract for this bounded RT-S12-002 chain, specifically the missing out-of-sample/sample coverage fields required by `StrategyCenterService` for publish.
- Do not start final RT-S12-002 browser E2E, RT-S12-003 user documentation, or Stage 12 Gate until the strategy can publish and the daily/post-close/proposal chain exists.

## 0. 2026-06-24 readiness repair result

- Updated preflight status: `PARTIAL_READY`
- Scope remained bounded to readiness repair only; `RT-S12-002` implementation still did not start
- Fixed blockers:
  - browser E2E tooling is now present in `web`
  - local helper now forces Node 18 PATH when available
  - local helper now provides `python -m scripts.web_local env-check` so `.env` no longer needs to be shell-sourced
- Remaining blockers:
  - no current formal reviewed canonical downstream evidence chain for the selected article subset
  - OHLCV still covers only one trade date; current `DatasetSnapshot` remains `partial`
  - `MarketSnapshot` / `MarketRegime` evidence remains missing
  - no truthful offline local seed payloads were available to repair those data blockers without live provider / LLM execution

Selected article subset for future RT-S12-002 implementation:

| Article ID | Revision ID | PromptRun ID | Title | Current candidate count |
| --- | --- | --- | --- | --- |
| `be0d68bd-8fc3-445c-8510-8b01a43185d6` | `7fde0824-b12c-56b5-be39-b4d45c91c49b` | `0e71cd75-8f45-4084-a7e7-beddedebefeb` | `量化风格下的轮动行情该如何实战思考，上周总结以及下周应对思路看这里！` | `1` |
| `fb673d83-bfb7-4a88-a804-c60ad2f8d8a2` | `b351d6e2-c780-5a26-b607-026182a60db4` | `684cc061-7d23-49cf-b83c-b1b8e4fb3cea` | `教你短线模式之一字首开！淘县九年义务教育！` | `1` |
| `8856f8f8-2441-492a-9292-981f0b3e1672` | `2f2589a2-2689-5b66-a6f1-cb687e0abcc1` | `cf2757bd-4a08-4435-8b6d-0f476e776159` | `教你恒宝股份短线逻辑全拆解！` | `1` |
| `84558067-1ba1-4248-9700-fd4225be8593` | `b64a3c51-bf32-562c-8a86-849eac28ad72` | `b5289dd7-8a5e-4d89-9c83-7555f8cc45a5` | `南方路机，短线逻辑全拆解！` | `1` |
| `fc461ca7-ff28-4c81-ba58-e4bc69ec8461` | `9dd9e1cd-62ab-5708-8d9d-ca9bad93c739` | `651a7bc9-86b8-4f30-b7a5-e1e82bb793cc` | `教你什么是短线跨年龙模式~淘县九年义务教育！` | `1` |

## 1. Entry verification

- Preflight date: `2026-06-24`
- Scope: `RT-S12-002` preflight only
- Parent model requested by user: `5.4`
- Stage 11 Gate: `ACCEPTED`
- Stage 12 Bootstrap: `READY`
- `RT-S12-001`: `ACCEPTED`
- `RT-S12-002`: not started
- `RT-S12-003`: not started
- Stage 12 Gate: not started
- Working tree before checks: clean
- Production code: modified only for bounded readiness repair tooling/runtime helpers
- Browser E2E: not started
- Live crawl / live backfill / live LLM / live browser E2E: not executed

## 2. Config template readiness

Config baseline used: `config/app.template.yaml`

### 2.1 Contract summary

- Required env vars in template baseline:
  - `DATABASE_URL`
  - `ADMIN_API_KEY`
- Optional env vars present in template:
  - `TGB_COOKIE`
  - `DASHSCOPE_API_KEY`
  - `KAIPAN_TOKEN`
  - `KAIPAN_USER_ID`
- Database URL placeholder:
  - `database.url: "${DATABASE_URL}"`
- API auth expectation:
  - `api.auth.enabled: true`
  - `api.auth.api_keys: ["${ADMIN_API_KEY}"]`
- LLM expectation:
  - `llm.provider: "qwen"`
  - `llm.model: ["qwen-flash"]`
  - `llm.url: "https://dashscope.aliyuncs.com/compatible-mode/v1"`
  - `llm.api_key: "${DASHSCOPE_API_KEY}"`
- Kaipan expectation:
  - `kaipan.token: "${KAIPAN_TOKEN}"`
  - `kaipan.user_id: "${KAIPAN_USER_ID}"`
- Crawl cookie expectation:
  - `crawl.auth.tgb.cn.cookie: "${TGB_COOKIE}"`
- Trader expectation:
  - template includes at least one enabled trader entry
  - sample trader id: `trader_a`
- Schedule / timezone expectation:
  - `timezone: Asia/Shanghai`
  - `schedule.pre_market_time: "09:25"`
  - `schedule.after_close_time: "18:00"`
- Output / storage expectation:
  - `storage.output_dir: data/processed/phase0`
  - `data.market_universe_snapshot_dir: data/market_universe/snapshots`
  - `kaipan.data_dir: data/kaipan`

### 2.2 Redacted local env status

| Key | Status | Classification | Safe source note |
| --- | --- | --- | --- |
| `DATABASE_URL` | set | set | `.env` parsed directly |
| `ADMIN_API_KEY` | set | set | `.env` parsed directly |
| `DASHSCOPE_API_KEY` | set | set | `.env` parsed directly |
| `TGB_COOKIE` | set | set | `.env` parsed directly |
| `KAIPAN_TOKEN` | set | set | `.env` parsed directly |
| `KAIPAN_USER_ID` | set | set | `.env` parsed directly |

### 2.3 Contract mismatches

- Existing local tooling still hard-codes `config/app.yaml` in multiple places:
  - many `cli.main` command defaults
  - several services and compatibility helpers
- `scripts/web_local.py` is now aligned to `config/app.template.yaml` for local migrate/worker helpers, but broader CLI/service defaults still point to `config/app.yaml`.
- `.env` is still not shell-source-safe in raw shell form because the cookie value contains raw semicolons, but `python -m scripts.web_local env-check` now parses it safely without `source .env`.

### 2.4 Safest local command pattern

- Keep `config/app.template.yaml` as the baseline contract.
- For local execution, prefer one of:
  - export required env vars from a shell/direnv/IDE without `source .env`
  - create an uncommitted `config/app.local.yaml` copied from `config/app.template.yaml`
- Do not commit any local config file containing secrets.

## 3. Tooling readiness

### 3.1 Observed tooling state

| Item | Result | Notes |
| --- | --- | --- |
| Python version | pass | `Python 3.13.10`, satisfies `>=3.11` |
| Backend imports | pass | `fastapi`, `sqlalchemy`, `asyncpg`, `alembic`, `pytest` import |
| `pytest` available | pass | import succeeded |
| Node default | fail | default `node` is `v14.4.0` |
| `pnpm` default | fail | still requires Node `>=18.12` when shell PATH is untouched |
| Node 18 path available | pass | local Node 18 bin directory exists |
| Web dependencies installed | pass | `web/node_modules` exists |
| `pnpm typecheck` under Node 18 | pass | completed successfully |
| frontend relevant test under Node 18 | pass | `src/app/route-config.test.tsx` passed |
| `pnpm test` under Node 18 | partial | broader suite still has unrelated failures outside this readiness repair scope |
| `@playwright/test` in `web/package.json` | pass | added as devDependency |
| `pnpm exec playwright --version` | pass | `Version 1.61.1` |
| Playwright Chromium readiness | partial | install command documented as `pnpm e2e:install`; browser binary not installed in this task |
| Backend/web start commands | pass | local launcher now prefers Node 18 and uses `config/app.template.yaml` for migrate/worker helpers |

### 3.2 Exact command results

- `python --version`
  - result: `Python 3.13.10`
- `python -m scripts.web_local env-check`
  - pass
  - `.env` parsed safely without shell-sourcing; all sensitive values remained redacted
- `python -m cli.main db-migrate --config config/app.template.yaml`
  - not executed in preflight
  - version table and migration head were checked read-only instead
- `cd web && pnpm install`
  - not executed; `node_modules` already exists
- `cd web && pnpm typecheck`
  - pass when executed with Node 18 in `PATH`
- `cd web && pnpm test`
  - command runs under Node 18, but suite currently has failures in legacy/non-formal test areas and date-sensitive tests
- `cd web && pnpm exec playwright --version`
  - pass
  - result: `Version 1.61.1`

### 3.3 Tooling blockers for RT-S12-002

- No tooling blocker remains for future RT-S12-002 implementation, provided local runs use:
  - `python -m scripts.web_local env-check` for redacted env validation
  - Node 18 PATH or the updated `scripts.web_local.py` helper for frontend commands
  - `pnpm e2e:install` before the later browser E2E task if Chromium is not yet installed

## 4. Secret readiness, redacted

| Capability | Ready? | Classification | Reason |
| --- | --- | --- | --- |
| Database access | yes | ready | `DATABASE_URL` set; read-only DB connection succeeded |
| Admin/operator API access | yes | ready | `ADMIN_API_KEY` set; one admin user exists in DB |
| Fresh LLM extraction | yes | available but not yet exercised | `DASHSCOPE_API_KEY` set |
| Live article crawl | yes | optional | `TGB_COOKIE` set, but existing DB articles already available |
| Live Kaipan fetch | yes | optional | `KAIPAN_TOKEN` and `KAIPAN_USER_ID` set |
| Live market data fetch | yes | optional | template uses `akshare`; no secret required |

### Live dependency classification

- `TGB_COOKIE`
  - optional for this preflight
  - existing DB articles mean live crawl is not required to start evidence repair
- `DASHSCOPE_API_KEY`
  - effectively blocking for final canonical extraction evidence
  - current DB has only 12 `article_analysis_v1` prompt runs and no downstream canonical rule/backtest/profile/strategy chain
- `KAIPAN_TOKEN` / `KAIPAN_USER_ID`
  - optional as credentials
  - current formal `MarketSnapshot` evidence is missing, so RT-S12-002 will still need either deterministic snapshot seed/refresh or explicitly authorized live refresh later

## 5. Database connectivity and migration readiness

### 5.1 Connectivity

- Read-only local PostgreSQL connection: succeeded
- Database appears to be a local/dev database, not a protected production endpoint:
  - local host in `DATABASE_URL`
  - repo-local usage pattern
  - simple dev credentials

### 5.2 Migration readiness

- `alembic_version.version_num`: `2026_06_20_0001`
- Alembic script head discovered from migration directory: `2026_06_20_0001`
- Conclusion: database schema appears to be at head

### 5.3 Alembic execution caveat

- Direct `alembic current` in the current Python 3.13 environment is flaky because importing the migration environment triggers heavier scientific/runtime imports.
- This did not block the read-only version check because DB version table and migration head matched.

### 5.4 Admin/operator readiness

- `users` count: `1`
- latest user role: `admin`
- Conclusion: admin/operator access exists; no seed action is required for preflight

## 6. Database-first canonical data readiness

| Object | Current evidence | Classification |
| --- | --- | --- |
| users / admin user | `1`, admin present | sufficient for preflight |
| articles | `131` | sufficient for preflight input pool |
| article revisions | `131` | sufficient for preflight input pool |
| article structures | `274`, all draft/partial | present but insufficient |
| prompt runs | `274`, only `12` current `article_analysis_v1` | present but insufficient |
| rule candidates | `495`, all extracted | present but insufficient |
| rule versions | `14`, all `legacy_unknown`, none published | present but insufficient |
| rule review states | only candidate `extracted`; no accepted formal review chain | present but insufficient |
| backtest runs | `0` | missing |
| backtest results | `0` | missing |
| legacy backtest result runs | `14`, all `legacy_import` / unresolved | historical only |
| applicability profiles | `0` | missing |
| author profile versions | `0` | missing |
| strategies | `0` | missing |
| strategy versions | `0` | missing |
| published strategy | `0` | missing |
| daily rule selections | `0` | missing |
| daily strategy instances | `0` | missing |
| trading day plans | `0` | missing |
| post-market reviews | `0` | missing |
| optimization proposals | `0` | missing |
| ohlcv bars | `84` rows, one trade date only | present but insufficient |
| dataset snapshots | `1`, lifecycle `partial` | present but insufficient |
| market snapshots | `0` | missing |
| market snapshot sections | `0` | missing |
| market snapshot items | `0` | missing |
| market state / market regime | `0` | missing |
| system runs / jobs | `8` job rows | sufficient for preflight diagnostics |

## 7. LLM-derived artifact provenance review

### 7.1 Current canonical evidence

- `prompt_runs`
  - total: `274`
  - current canonical-looking runs:
    - `prompt_name = article_analysis_v1`
    - `prompt_version = article_analysis_v1`
    - `schema_version = article_analysis_v1`
    - `validation_state = valid`
    - count: `12`
- `article_structures`
  - total: `274`
  - revision binding present: `274`
  - prompt run binding present: `274`
  - all are still `lifecycle_state = draft`
  - all are `quality_status = partial`

### 7.2 Historical / pre-refactor evidence

- `prompt_runs`
  - `legacy_article_analysis` dominates:
    - `legacy_unknown / v2 / valid`: `125`
    - `legacy_unknown / v1 / valid`: `125`
    - older variant rows: `12`
- `rule_versions`
  - total: `14`
  - `schema_version = legacy_unknown`: `14`
  - none published
  - quality only `legacy_only` or `unresolved`
- `backtest_result_runs`
  - total: `14`
  - latest rows classified `status = legacy_import`
  - `dataset_snapshot_id = NULL`
  - `strategy_version_id = NULL`

### 7.3 Missing evidence

Missing canonical downstream evidence for the frozen RT-S12-002 path:

- formal reviewed `RuleVersion` chain based on current canonical prompt output
- formal `BacktestRun`
- formal `BacktestResult`
- formal `RuleApplicabilityProfile`
- formal `AuthorProfileVersion`
- formal `Strategy` / `StrategyVersion`
- formal `DailyRuleSelection`
- formal `DailyStrategyInstance`
- formal `TradingDayPlan`
- formal `PostMarketReview`
- formal `OptimizationProposal`

### 7.4 Provenance conclusion

- Current DB contains reusable canonical article input and a small amount of current prompt evidence.
- Current DB does **not** contain a complete current-provenance chain for RT-S12-002 final pass evidence.
- Legacy rows are usable as historical context only and must not be counted as final acceptance evidence.

## 8. Existing article subset recommendation

Fresh LLM evidence is required.

Recommended initial subset: use a small representative set from existing `article_analysis_v1` articles, not the whole corpus.

Suggested 5-article pool:

1. `量化风格下的轮动行情该如何实战思考，上周总结以及下周应对思路看这里！`
2. `教你短线模式之一字首开！淘县九年义务教育！`
3. `教你恒宝股份短线逻辑全拆解！`
4. `手把手教你如何看竞价~淘县九年义务教育~`
5. `5.21号复盘！市场下跌早有征兆！退潮行情接下来如何应对！`

Reason:

- all are already in DB
- all have current `article_analysis_v1` prompt runs with `validation_state = valid`
- they cover:
  - pattern/mode articles
  - single-stock logic article
  - auction/opening process article
  - market-state / post-close style article

Constraint:

- final subset lock should happen only after confirming the selected symbols can be backed by deterministic OHLCV coverage and refreshed snapshot evidence

## 9. OHLCV / DatasetSnapshot / MarketSnapshot readiness

### 9.1 OHLCV

- total `ohlcv_bars`: `84`
- observed identity fields present in DB rows:
  - `symbol`
  - `source_symbol`
  - `exchange`
  - `asset_type`
  - `frequency`
  - `adjustment_policy`
  - `source`
  - `trade_date`
  - `captured_at`
  - `available_at`
- coverage problem:
  - only one trade date: `2026-04-20`
  - each inspected symbol has `1` row
- conclusion:
  - insufficient for even a minimal `10–30` trading day backtest window

### 9.2 DatasetSnapshot

- total snapshots: `1`
- latest snapshot:
  - `dataset_type: ohlcv_partial`
  - `lifecycle_state: partial`
  - `trade_date/date_from/date_to: 2026-04-20`
  - `symbol_manifest.count: 84`
  - `ohlcv_manifest.row_count: 84`
  - `ohlcv_manifest.trade_dates: ["2026-04-20"]`
  - `content_fingerprint`: present
  - `frozen_at`: present
- conclusion:
  - traceable but insufficient

### 9.3 MarketSnapshot / MarketState

- `market_snapshots`: `0`
- `market_snapshot_sections`: `0`
- `market_snapshot_items`: `0`
- `market_regimes`: `0`
- conclusion:
  - missing for both pre-market and post-close frozen path steps

### 9.4 Data conclusion

- Current DB data is not sufficient for snapshot-bound RT-S12-002 execution.
- Do not fetch or backfill during preflight.
- Minimal repair should prefer deterministic/local canonical snapshot preparation over broad live backfill.

## 10. Formal route readiness

### 10.1 Verified formal route entries

`web/src/app/route-config.tsx` contains the required formal routes:

- `/research/add`
- `/research/articles`
- `/research/results`
- `/rules/review`
- `/rules/library`
- `/rules/backtests`
- `/rules/results`
- `/authors`
- `/strategies`
- `/strategies/candidates`
- `/daily/pre-market`
- `/daily/after-close`
- `/system/runs`
- `/system/data`

Additional evidence:

- product journey tests encode the formal chain:
  - `/research/articles -> /rules/review -> /rules/backtests -> /authors -> /strategies -> /daily/pre-market -> /daily/after-close`

### 10.2 Retired route status

- retired routes remain registered only as compatibility redirects in route config
- broad reference scan still finds retired paths in:
  - legacy page source files
  - compatibility/admin surfaces
  - tests
- preflight conclusion:
  - no frozen RT-S12-002 step requires a retired route as the ordinary-user formal entry
  - retired-route references remain cleanup/hardening residue, not the formal E2E entry path

## 11. RT-S12-002 step-by-step readiness matrix

| Step | Formal UI/API entry | Required DB object | Current DB evidence | Provenance class | Required token | Required snapshot / version evidence | Status | Missing item | Minimal repair action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. 文章导入 | `/research/add`, `/research/articles` | `blog_articles`, `article_revisions` | `131` articles, `131` revisions | current input pool | no | article revision binding exists | PARTIAL | formal import run evidence for chosen subset | reuse existing DB articles; no new crawl required |
| 2. 提取规则 | `/research/results` | `prompt_runs`, `article_structures`, `rule_candidates` | `12` current `article_analysis_v1`, `274` structures, `495` candidates | partial current + mostly historical | yes if regenerating subset | prompt run id/version/schema/model/input hash/validation | PARTIAL | downstream-ready current subset evidence | regenerate only `3–5` existing articles through current runtime if needed |
| 3. 审核规则 | `/rules/review`, `/rules/library` | `rule_versions` | `14` rule versions, all `legacy_unknown`, none published | historical / legacy only | no | source candidate linkage, canonical schema/version | BLOCKED | current formal reviewed rule versions | create reviewed canonical rule evidence from subset |
| 4. 回测 | `/rules/backtests`, `/rules/results` | `backtest_runs`, `backtest_results`, `dataset_snapshots` | `0` / `0`; only one partial dataset snapshot | missing | no | immutable dataset snapshot + fingerprint | BLOCKED | backtest runs/results and enough OHLCV | seed/import minimal deterministic OHLCV window and create canonical snapshot |
| 5. 生成规则适用性 | `/rules/results` | `rule_applicability_profiles` | `0` | missing | no | bound backtest + dataset + market-state evidence | BLOCKED | applicability profiles | generate after canonical backtest exists |
| 6. 生成作者画像 | `/authors` | `author_profile_versions` | `0` | missing | yes | prompt run + rule/applicability/backtest bindings | BLOCKED | author profile versions | create method/rule/validated profile drafts from repaired subset |
| 7. 发布策略 | `/strategies`, `/strategies/candidates` | `strategies`, `strategy_versions` | `0` / `0` | missing | no | strategy version evidence + review/publish trace | BLOCKED | strategy publication evidence | create draft then publish canonical strategy |
| 8. 生成盘前计划 | `/daily/pre-market` | `daily_rule_selections`, `daily_strategy_instances`, `trading_day_plans`, `market_snapshots`, `market_regimes` | all `0` | missing | no | pre-market snapshot + market state + current strategy | BLOCKED | pre-market snapshot/state and daily objects | create/refresh market snapshot + market regime + daily plan chain |
| 9. 完成盘后复盘 | `/daily/after-close` | `post_market_reviews`, post-close `market_snapshots`, `market_regimes` | `0` | missing | conditional | post-close snapshot + actuals + traceability | BLOCKED | post-close review evidence | create post-close snapshot/state and review |
| 10. 生成优化建议 | `/daily/after-close` | `optimization_proposals` | `0` | missing | conditional | linked post-market review + proposal evidence | BLOCKED | proposal evidence | generate proposal lane after post-close review |

## 12. Missing items and minimal repair actions

1. Stabilize local execution baseline
   - use Node 18 when running `pnpm`
   - do not `source .env` directly in shell
   - keep `config/app.template.yaml` as contract baseline
   - prefer uncommitted `config/app.local.yaml` or explicit env injection
2. Prepare browser runtime only when the later browser E2E task is explicitly authorized
   - `@playwright/test` and package scripts are present
   - Chromium install remains deferred; run `pnpm e2e:install` only before the authorized browser E2E task
3. Reuse existing DB articles; do not crawl the corpus again
4. Select a `3–5` article subset from existing current `article_analysis_v1` runs
5. Regenerate only the missing current formal evidence for that subset
   - current prompt/runtime provenance if needed
   - current rule review evidence
6. Prepare minimal deterministic OHLCV coverage
   - enough for selected symbols and `10–30` trading days
   - no broad backfill
7. Create or refresh canonical `DatasetSnapshot`
8. Create or refresh canonical pre-market and post-close `MarketSnapshot`
9. Create or refresh canonical `MarketRegime` rows
10. Generate canonical:
   - `BacktestRun`
   - `BacktestResult`
   - `RuleApplicabilityProfile`
   - `AuthorProfileVersion`
   - `StrategyVersion` / published `Strategy`
   - `DailyRuleSelection`
   - `DailyStrategyInstance`
   - `TradingDayPlan`
   - `PostMarketReview`
   - `OptimizationProposal`

## 13. Can RT-S12-002 start?

Current decision after the 2026-06-29 reference-chain completion repair:

`READY_FOR_RT_S12_002_IMPLEMENTATION`

Boundary:

- This means the next authorized work may be `RT-S12-002 Browser E2E
  Acceptance`.
- It does not mean Browser E2E passed.
- It does not allow starting `RT-S12-003`, Stage 12 Gate, or user
  documentation without explicit authorization.
- It does not allow counting the reference-chain repair records as Browser E2E
  final pass evidence.

Historical initial preflight reason before the 2026-06-24 to 2026-06-29 repairs:

Reason:

- browser E2E tooling is ready in the web workspace, but Chromium install is still deferred to the later browser task
- current DB has no canonical backtest/applicability/profile/strategy/daily/post-close/proposal evidence
- OHLCV coverage is only one trade date
- canonical `MarketSnapshot` / `MarketRegime` evidence is completely missing
- existing legacy rule/backtest rows cannot be counted as final RT-S12-002 pass evidence

## 14. Exact next actions before RT-S12-002 implementation

Current next action after the 2026-06-29 repair:

1. Wait for explicit user authorization before starting `RT-S12-002 Browser E2E
   Acceptance`.
2. During Browser E2E, generate or lifecycle-transition a separate final E2E
   chain and record new object IDs or new audit/lifecycle transitions.
3. Do not use the reference-chain repair records as final E2E pass evidence.
4. Do not start `RT-S12-003`, user documentation, or Stage 12 Gate.

Historical initial preflight actions before the 2026-06-24 to 2026-06-29
repairs:

1. Fix local runtime commands

```bash
cd trade-strategy-ai/web
pnpm typecheck  # run with Node 18 PATH
pnpm test       # run with Node 18 PATH
```

2. Use explicit env injection or a local uncommitted config file instead of `source .env`

```bash
cd trade-strategy-ai
../.venv/bin/python -m cli.main db-check --config config/app.template.yaml
```

This command should be run only after env vars are injected safely or a local uncommitted config copy is prepared.

3. Before the later browser E2E task, install Chromium if the local browser binary is absent

```bash
cd trade-strategy-ai/web
pnpm e2e:install  # run with Node 18 PATH
```

4. Repair only the minimum required data/evidence set

- choose `3–5` existing current `article_analysis_v1` articles
- generate current formal rule review evidence
- prepare minimal deterministic OHLCV window and canonical snapshot/state evidence
- then generate the canonical downstream chain through proposal generation

## Record summary

- preflight status: `READY_FOR_RT_S12_002_IMPLEMENTATION`
- config baseline used: `config/app.template.yaml`
- database-first decision: reuse existing DB articles; do not recrawl or bulk-regenerate
- next allowed action: wait for explicit authorization to start `RT-S12-002 Browser E2E Acceptance`; Browser E2E must create or transition a separate final E2E chain

## 15. Minimal canonical evidence repair 5.5

Date: 2026-06-24

Status: `STILL_BLOCKED`

Scope:

- selected subset kept at the five existing DB articles:
  - `be0d68bd-8fc3-445c-8510-8b01a43185d6`
  - `fb673d83-bfb7-4a88-a804-c60ad2f8d8a2`
  - `8856f8f8-2441-492a-9292-981f0b3e1672`
  - `84558067-1ba1-4248-9700-fd4225be8593`
  - `fc461ca7-ff28-4c81-ba58-e4bc69ec8461`
- selected symbols:
  - `002104.SZ` from selected article title `恒宝股份` and existing `stock_info`
  - `603280.SH` from selected article title `南方路机` and existing `stock_info`
- no corpus recrawl
- no all-article regeneration
- no final browser E2E
- no RT-S12-003 documentation
- no Stage 12 Gate

Entry verification:

- Stage 11 Gate: `ACCEPTED`
- Stage 12 Bootstrap: `READY`
- RT-S12-001: `ACCEPTED`
- RT-S12-002 implementation: not started
- RT-S12-003: not started
- Stage 12 Gate: not started
- latest readiness repair review: `READINESS_REPAIR_ACCEPTED_WITH_RESIDUAL_BLOCKERS`
- current preflight status before repair: `PARTIAL_READY`
- git status before repair: clean
- baseline HEAD before repair: `e67d39841a29c0ab5ac81796db53bf7e30b62b56`

Article evidence recheck:

- all five selected articles have existing `article_analysis_v1` prompt runs and candidates
- selected executable OHLCV-backed candidate used for formal rule repair:
  - article `84558067-1ba1-4248-9700-fd4225be8593`
  - revision `b64a3c51-bf32-562c-8a86-849eac28ad72`
  - prompt run `b5289dd7-8a5e-4d89-9c83-7555f8cc45a5`
  - candidate `af289b09-d9f1-44e1-8ce3-dfd87c84322d`
  - candidate fingerprint `32db69f061d899626664245410ce67879746788effbe3a0bd83bfa4e72d704b8`
  - title `强势股临盘承接后跟随`
  - dependency `ohlcv_1d`

Live provider / LLM actions:

- LLM: not called
- article recrawl: not called
- Kaipan: not called
- AkShare/OHLCV: bounded selected-symbol refresh only
  - symbols: `002104.SZ`, `603280.SH`
  - date window: `2024-05-06` to `2024-05-31`
  - result: 20 daily rows per symbol
  - secret values were not printed

Repaired canonical evidence:

- OHLCV:
  - `002104.SZ`: 20 rows, `2024-05-06` to `2024-05-31`
  - `603280.SH`: 20 rows, `2024-05-06` to `2024-05-31`
- DatasetSnapshot:
  - pre-market snapshot `680a9e4a-8cb4-4131-8ef0-785031cb670b`
    - trade date `2024-05-30`
    - lifecycle `ready`
    - selected rows `38`
    - fingerprint `9f56b30c66ca0ca11f53fe0452dd4e31e31ef4826cece9cd071561c2839f7538`
  - post-close snapshot `b534d59d-851a-4a78-a32d-af6e71a4e71f`
    - trade date `2024-05-31`
    - lifecycle `ready`
    - selected rows `40`
    - fingerprint `62bc2a46401cb6ffdf0f734443618079d0fc211c3bafded9e8393de19171d64c`
- MarketSnapshot / MarketRegime:
  - pre-market MarketSnapshot `88aa0f65-0fb8-41fb-aee8-cb8bbdb33a6f`
    - snapshot id `rt-s12-002:2024-05-31:09-25:selected-symbols`
    - quality `partial`
    - fingerprint `f59b3f131f253f120f8bae0cc25127b1b4aec5cc82932631d65eecb14ab3b5dc`
  - pre-market MarketRegime `a8c2d82f-8db9-41ad-aec7-4c79f42c701f`
    - regime id `rt-s12-002:2024-05-31:09-25:selected_symbol_resilient`
    - quality `partial`
  - post-close MarketSnapshot `9646ace9-a755-485d-89f4-4900602bde30`
    - snapshot id `rt-s12-002:2024-05-31:17-30:selected-symbols`
    - quality `partial`
    - fingerprint `611772f990a6eb57b70ae633045dbd851a411c4cf8f4acbd8934eb8d44d60c3c`
  - post-close MarketRegime `f9084b48-020a-4493-84a0-f2994e7dbccf`
    - regime id `rt-s12-002:2024-05-31:17-30:selected_symbol_resilient`
    - quality `partial`
- RuleVersion:
  - `8d15ae78-4abb-40ef-9a6e-184bb7289d0c`
  - source candidate `af289b09-d9f1-44e1-8ce3-dfd87c84322d`
  - lifecycle `in_review`
  - fixed-set gate passed before mutation
  - not published, because downstream backtest evidence could not be created

Remaining blocker:

- canonical `BacktestRun` cannot be inserted in the current DB:
  - Alembic reports current/head `2026_06_20_0001`
  - PostgreSQL type `backtest_run_status` is absent
  - ORM maps `BacktestRun.status` to enum type `backtest_run_status`
  - committed migration `2026_06_18_0010_stage6_backtest_run_foundation.py` creates `backtest_runs.status` as `String`, while current ORM expects the enum
  - creating the enum manually would be an unapproved schema change, not an existing committed migration application
- because `BacktestRun` is blocked, the following were not generated:
  - `BacktestResult`
  - `RuleApplicabilityProfile`
  - `AuthorProfileVersion`
  - `StrategyVersion` / published `Strategy`
  - `DailyRuleSelection`
  - `DailyStrategyInstance`
  - `TradingDayPlan`
  - `PostMarketReview`
  - `OptimizationProposal`

Readiness recheck matrix:

| Evidence | Status | Notes |
| --- | --- | --- |
| selected article subset | READY | 5 existing current `article_analysis_v1` articles retained |
| selected symbols | READY | `002104.SZ`, `603280.SH` derived from selected article titles and `stock_info` |
| current reviewed RuleVersion | PARTIAL | RuleVersion exists and is `in_review`; not published because backtest evidence is blocked |
| OHLCV 10-30 day coverage | READY | 20 rows per selected symbol |
| DatasetSnapshot | READY | two ready snapshots with selected-symbol manifests and fingerprints |
| pre/post MarketSnapshot | PARTIAL | exists with explicit selected-symbol-only partial provenance |
| MarketRegime | PARTIAL | exists with selected-symbol-only partial provenance |
| BacktestRun | BLOCKED | missing DB enum type `backtest_run_status` |
| BacktestResult | BLOCKED | depends on BacktestRun |
| RuleApplicabilityProfile | BLOCKED | depends on BacktestResult |
| AuthorProfileVersion | BLOCKED | depends on applicability/backtest evidence |
| StrategyVersion / published Strategy | BLOCKED | depends on published rule/profile/applicability/backtest evidence |
| Daily pre-market chain | BLOCKED | depends on published strategy |
| Post-close / proposal chain | BLOCKED | depends on daily plan and post-close review |

Verification:

- `python -m scripts.web_local env-check`: pass, redacted output only
- `python -m cli.main db-check --config config/app.template.yaml`: pass, `DB OK: 1`
- `python -m alembic -c src/db/migrations/alembic.ini current`: pass, current/head `2026_06_20_0001`
- targeted backend tests:
  - `python -m pytest tests/unit/services/test_backtest_application_service.py tests/unit/services/test_rule_applicability_service.py -q`
  - pass, `22 passed`
- web typecheck:
  - `PATH="/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH" pnpm typecheck`
  - pass
- web route test:
  - `PATH="/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH" pnpm test -- src/app/route-config.test.tsx`
  - pass, `12 passed`
- `git diff --check`: pass

Readiness decision:

`STILL_BLOCKED`
