# Taxonomy-First Extraction Delivery Report

Date: 2026-07-11

Project: `trade-strategy-ai`
Decision: **ACCEPTED**

## 1. Final architecture

The ordinary product route is now:

```text
article revision
→ article_taxonomy_v1
→ ArticleStructure + extraction_items
→ fixed type-specific review destination
→ strict executable validation or bounded rule-candidate repair
→ RuleVersion with source_extraction_item_id
→ formal backtest source-lineage validation
```

`primary_type` accepts exactly `executable_rule`, `rule_candidate`, `research_hypothesis`, `semantic_experience`, `risk_control_hint`, `data_requirement_hint`, and `unusable_noise`. `rule_candidates` is not written by the ordinary taxonomy runtime.

## 2. Components changed

- Added taxonomy schemas, seven discriminated payload contracts, evidence/confidence/provenance contracts, and fixed routing.
- Added `ExtractionItem`, `ExtractionReclassificationRun`, and `ExtractionReclassificationItem` models and repositories.
- Added taxonomy runtime writer, strict eligibility service, bounded repair, promotion, and append-only reclassification service.
- Added taxonomy prompt/schema registration; retained the old analysis prompt only as `test_special_only`.
- Changed the article API and UI to expose and display mixed `extraction_items[]`.
- Retired old-candidate mutation endpoints and service mutations; legacy reads remain isolated for audit.
- Added direct `RuleVersion.source_extraction_item_id` lineage and formal-backtest checks for both individual versions and every rule-family member.
- Added deterministic seven-type fixtures, integration/regression tests, and bounded validation scripts.

## 3. Migration and rollback

Migration `2026_07_11_0001_extraction_taxonomy` creates the three append-only taxonomy tables, exact seven-value constraints, indexes, and RuleVersion lineage. PostgreSQL `upgrade → downgrade → upgrade` passed and finished at head. Downgrade refuses to erase non-empty taxonomy evidence; the empty-table rollback path is verified.

The full historical SQLite migration chain remains unable to pass an older pre-existing constraint-alter migration (`20260407_0001`); this is outside the new migration and PostgreSQL delivery path.

## 4. Old-data preservation

The development database contained 488 old `rule_candidates` before and after migration. The full-table ordered snapshot SHA-256 remained:

```text
4db57864b4fff7584a2f0fb820ba80aa4d2d4021437b5f2bce8db3b79ecddaec
```

No old candidate was updated or deleted. Reclassification writes only new run/item records with the old candidate ID and frozen source snapshot as lineage.

## 5. Prompt/runtime behavior

`article_taxonomy_v1` validates the common contract and the type-specific discriminated payload before persistence. Invalid output gets at most one targeted `article_taxonomy_repair_v1` attempt. Cache identity includes article revision/content, prompt, schema, model, and source. The runtime writes `ArticleStructure + ExtractionItem[]`; tests assert zero new ordinary-path `RuleCandidate` rows.

## 6. Review and routing

Every type has one fixed destination. `rule_candidate` can only enter repair. Repair creates a new prompt run and a new executable extraction item with parent lineage; it does not mutate or relabel the candidate. Non-rule items remain in research, semantic, risk, data, or rejection lanes.

## 7. Promotion and formal-backtest gates

Promotion requires all of the following: `primary_type=executable_rule`, complete executable mechanics, traceable evidence, accepted review, valid quality, explicit timestamp availability, passed lookahead check, no unresolved ambiguity, and `not_directly_backtestable=false`. The resulting `RuleVersion` has `source_candidate_id=NULL` and `source_extraction_item_id=<accepted item>`.

Formal backtest independently reloads and revalidates that source item. Old-candidate lineage, missing extraction lineage, unavailable source items, non-executable types, invalid evidence, timestamp risk, and lookahead risk are blocked. Rule-family selection applies this check to every frozen member.

## 8. Bounded old-candidate reclassification

Seven known audit examples were read without mutation. Evidence supported this distribution:

| Type | Count |
|---|---:|
| rule_candidate | 2 |
| research_hypothesis | 1 |
| semantic_experience | 1 |
| risk_control_hint | 1 |
| data_requirement_hint | 1 |
| unusable_noise | 1 |

No sampled old record proved the full executable mechanics/timestamp/lookahead contract, so no `executable_rule` label was invented. The append-only writer itself is validated with all seven fixture types and repeatable run identity. The selected-source snapshot SHA-256 is `9ed943b444d88da84f19eabb752d1d99d8210002def4981bb8e7051923072f61`.

## 9. Representative article validation

Fourteen existing articles were selected: two each for 情绪周期, 弱转强, 龙头/主线, 退潮/冰点, 放量/共振, 风控纪律, and 纯市场复盘. All retained source quotes were present. Deterministic reviewed labels produced:

| Type | Count |
|---|---:|
| semantic_experience | 10 |
| research_hypothesis | 6 |
| risk_control_hint | 4 |
| data_requirement_hint | 2 |
| rule_candidate | 2 |
| unusable_noise | 2 |
| executable_rule | 0 |

Multi-label totals exceed article count. All formal routes were blocked. Zero executable rules is intentional: none of the sampled prose proved the complete strict contract, and fuzzy language was not forced into rule-shaped output.

## 10. Tests and commands

- PostgreSQL Alembic current/downgrade/upgrade/current: passed at `2026_07_11_0001`.
- Taxonomy/backend/API/reclassification/promotion/backtest/regression set: `72 passed, 1 skipped`.
- Earlier focused core set: `46 passed`; final backtest unit set: `15 passed`.
- Backend smoke E2E: `2 passed`.
- Relevant frontend Vitest: `22 passed`; TypeScript typecheck, ESLint, and Vite production build passed.
- Changed Python files: Ruff passed; `git diff --check` passed.
- Representative article and old-candidate validation scripts passed with the results above.
- Full backend checkpoint: `2400 passed, 40 failed, 21 skipped, 2 errors`. Twelve taxonomy/route-related failures were then fixed and covered by the final 72-test set. Remaining failures are existing unrelated modules (agent integration mocks, backup/repository writer-routing assumptions, rule-pool legacy writes, runtime registry, services export inventory, and similar).
- Full frontend checkpoint: three unrelated lifecycle tests still expect retired `/jobs` URLs while the product correctly emits `/system/jobs`; relevant tests and build pass.

## 11. Unavailable validations and residual risks

- No live model/provider call was claimed: external credentials were not required for delivery. Runtime behavior is validated with fixed model-assisted-equivalent fixtures and deterministic reviewed labels.
- The frozen regression manifest cannot run against the current local database because its historical article revision IDs are absent; deterministic fixture regression and a separate 14-real-article read-only validation passed.
- Existing repository-wide Ruff and mypy baselines contain substantial unrelated failures. Changed Python files pass Ruff; frontend typecheck passes. Backend mypy cannot isolate these modules without importing the failing baseline.
- The old read-only candidate views and stored compatibility projection remain only for evidence access. They do not write, promote, or backtest.

## 12. Final decision

**ACCEPTED** — the taxonomy-first route is canonical, old candidate evidence is unchanged, append-only lineage is verified, and only a strictly validated executable extraction item can create a RuleVersion or enter formal backtest.

## 13. Follow-up ingestion repair (2026-07-11)

After delivery, a real crawl produced 137 `raw_articles` but only 136 `blog_articles`. The new raw row was not missing taxonomy classification; it had never reached formal article storage. Database-mode clean and validate reused stale JSONL artifacts, so store generated no pending task and process reported an empty success.

The repair makes database clean select only unprocessed raw rows that have no matching `BlogArticle` or whose content hash differs, regenerates database-mode validation output, carries `raw_article_id` through clean/validate/store, and marks that exact raw row processed only after a successful store. A standalone process step now rejects an empty pending queue instead of reporting a misleading success.

Live repair evidence: the affected row was stored as a new `BlogArticle` with one revision and one pending taxonomy task (`stored_read_records=1`, `inserted_articles=1`, `generated_tasks=1`, `processed_raw_articles=1`). Its taxonomy invocation is truthfully pending retry because this environment has no configured LLM API key; no extraction item was fabricated. Follow-up tests: `66 passed` across storage, database-pipeline refresh, process prerequisites, taxonomy runtime, single-article, and taxonomy contracts.
