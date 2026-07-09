# Extraction Taxonomy Implementation Impact Report

Date: 2026-07-09
Scope: implementation impact audit only
Source design: `docs/extraction-taxonomy-redesign.md`
Source audit: `docs/rule-extraction-output-audit.md`

## 1. Executive Summary

The Step 2 taxonomy can be implemented inside `trade-strategy-ai`, but not as a small field addition to the existing `rule_candidates` workflow. The current formal extraction path treats every persisted extraction item as a `RuleCandidate`, and downstream review/governance code assumes that a candidate has rule-shaped fields such as `condition`, `action`, `rule_type`, `quantification.status`, `missing_fields`, and `ambiguous_terms`.

The clean implementation boundary is a new extraction item layer that stores mutually exclusive `primary_type` values before rule promotion. `executable_rule` must stay a narrow type, not the default extraction target. Only `executable_rule` should be eligible for direct rule governance/backtest. `rule_candidate` should route to repair/completion. `research_hypothesis`, `semantic_experience`, `risk_control_hint`, `data_requirement_hint`, and `unusable_noise` need separate queues or destinations.

Must-change:

- Replace the runtime assumption that `article_analysis_v1.rule_extraction.strategy_rules[]` becomes `RuleCandidate[]`.
- Add a first-class output taxonomy contract before review/governance/backtest.
- Prevent non-`executable_rule` outputs from entering rule promotion or formal backtest.
- Preserve the existing 488 old `rule_candidates` as audit evidence and migration input.

Should-change:

- Introduce new storage around extracted items instead of overloading `rule_candidates`.
- Split human review queues by output type.
- Add re-extraction/reclassification jobs that write new taxonomy results without rewriting old evidence.

Optional-change:

- Keep `rule_pool` and old `article_metadata.strategy_rules` as read-only compatibility/evidence paths until explicitly retired.
- Add semantic dictionary and data requirement backlog UI after the new storage contract is accepted.

Smallest safe next step: decide the storage route, then write a schema/API implementation spec for a new `extraction_items` layer plus type-specific review destinations. Do not change prompts, migrations, services, UI, or production data before that decision.

## 2. Current Assumptions That Conflict With The New Taxonomy

Must-change:

- Prompt contract: `trade-strategy-ai/prompts/article_analysis_v1.md` defines `rule_extraction.strategy_rules[]` as the only extracted trading-rule item list. It allows incomplete rules but still represents them as strategy rules with `condition`, `action`, and `quantification.status`.
- Runtime persistence: `trade-strategy-ai/src/services/stage3_prompt_runtime_service.py:117-127` collects evidence from `rule_extraction.strategy_rules[]`; `:130-141` derives missing/ambiguous fields from those rules; `:312-334` creates one `RuleCandidate` per strategy rule.
- Canonical model: `trade-strategy-ai/src/models/stage2_canonical.py:361-389` defines `RuleCandidate` as the persisted extracted output with `rule_type`, `canonical_payload`, `missing_fields`, `data_dependencies`, `backtestability_status`, `review_state`, and `quality_status`.
- Review policy: `trade-strategy-ai/src/services/article_review_policy.py:138-219` assumes candidate payloads have `condition`, `action`, `evidence`, `market_state_applicability`, `risk_controls`, `data_dependencies`, and `quantification`.
- Governance fingerprinting: `trade-strategy-ai/src/services/rule_governance_service.py:74-183` normalizes any candidate payload as a rule-shaped object for exact/family fingerprints.
- Rule promotion: `trade-strategy-ai/src/services/rule_lifecycle_service.py:511-557` converts `candidate.canonical_payload` directly into `RuleVersion.condition_json`, `action_json`, `parameter_json`, and `data_dependencies`.

Should-change:

- Stage 3 journey models name the output `candidates: list[RuleCandidate]` and derive automatic review/governance per candidate in `trade-strategy-ai/src/services/stage3_single_article_service.py:45-58` and `:204-220`.
- API response schemas expose only candidate-rule fields in `trade-strategy-ai/api/schemas/article_analysis.py:63-114`.
- Web types mirror that contract in `trade-strategy-ai/web/src/types/article-analysis.ts:18-69`.

Optional-change:

- The legacy adapter in `trade-strategy-ai/src/agents/data_agent/skills/extract_article_metadata.py:458-517` projects `article_analysis_v1` into old `ArticleMetadata.strategy_rules`. It is not the formal Stage 3 writer, but it remains a source of rule-shaped compatibility output.

## 3. Affected Database Tables And Models

Must-change:

- `rule_candidates` / `RuleCandidate`: currently the only formal extracted item table. It has no `primary_type`, no type-specific payload contract, and no destination separation. See `trade-strategy-ai/src/models/stage2_canonical.py:361-389`.
- `rule_versions` / `RuleVersion`: assumes a formal rule comes from a `source_candidate_id` linked to `rule_candidates`. See `trade-strategy-ai/src/models/stage2_canonical.py:406-436`.
- `rule_version_source_links`: only links `rule_versions` to `rule_candidates`, not to general extraction items. See `trade-strategy-ai/src/models/stage2_canonical.py:488-506`.
- `lifecycle_events`: uses `CanonicalObjectType.rule_candidate` for candidate review events; new output types need either a new object type or a common extraction item object type.

Should-change:

- `prompt_runs` and `article_structures` can still preserve prompt trace and article-level structure, but `ArticleStructure.missing_fields` and `evidence_json` currently aggregate rule-only missing/ambiguous fields from `strategy_rules[]`.
- `article_metadata.strategy_rules` remains legacy/compatibility storage in `trade-strategy-ai/src/models/article_metadata.py:27-44`. It should not become the new taxonomy store.
- `rule_applicability_profiles` points to formal rule versions/families and backtest outputs, not extracted ideas. It should remain downstream of `RuleVersion`, not accept fuzzy output types. See `trade-strategy-ai/src/models/rule_applicability.py:61-143`.
- Migration support tables (`migration_runs`, `migration_run_items`, `migration_conflicts`, `migration_quality_reports`) in `stage2_canonical.py` can preserve audit evidence for old 488-row reclassification runs.
- Database config/session files are low direct-impact but important for future migration/reclassification execution boundaries: `trade-strategy-ai/config/settings.py:8-18`, `trade-strategy-ai/config/database.py:17-45`, and `trade-strategy-ai/src/db/session.py:9-21`.

Optional-change:

- `rule_pool` is a separate older pool model with `source_type`, `extraction_layer`, `mapping_status`, `review_status`, and backtest summary fields in `trade-strategy-ai/src/rule_pool/models.py:13-86`. Its Pydantic schemas likewise center on `RulePoolItem`, `RuleSourceType`, `ExtractionLayer`, and `RuleBacktestResult` in `trade-strategy-ai/src/rule_pool/schemas.py:10-82`. It can be kept as a reference/backtest legacy path, but it is not a clean home for the seven-type taxonomy because its schema is still rule-centric.

Existing table extension vs new tables:

- Extending `rule_candidates` is technically possible with `primary_type` and type payload fields, but it is semantically unsafe: the table name, foreign keys, review states, governance source links, and UI labels all imply "candidate rule".
- Cleaner path: add a general `extraction_items` table keyed by article structure/prompt run/source span with `primary_type`, `secondary_tags`, `source_evidence`, `taxonomy_payload`, `quality_state`, and review routing fields. Add type-specific tables or typed payload schemas only where execution semantics require strict fields, especially `executable_rules` and `data_requirement_hints`.

## 4. Affected Pydantic Schemas And API Contracts

Must-change:

- `api/schemas/article_analysis.py:63-114` only exposes `AutomaticReviewResponse`, `HumanReviewResponse`, `CandidateGovernanceResponse`, and `CandidateRuleResponse`. It lacks `primary_type`, `secondary_tags`, taxonomy-specific fields, and non-rule destinations.
- `api/routers/ui/article_analysis.py:167-202` serializes every item as a candidate with `rule_type`, `backtestability_status`, `market_state_declaration_status`, `automatic_review`, `human_review`, and `governance`.
- `web/src/types/article-analysis.ts:18-69` constrains automatic review status to `pending_backtest | needs_human_review | suggested_reject` and has no way to represent research/semantic/risk/data/noise outputs.

Should-change:

- Article analysis detail responses should expose `extraction_items[]` with a stable `primary_type`, destination, review status, source evidence, and type-specific summary. `candidate` should be reserved for `rule_candidate`.
- Rule review API (`api/routers/ui/rule_review.py:68-140`) should only list reviewable rule candidates/executable rules, not semantic or data backlog items.
- Rule review types (`web/src/types/rule-review.ts:1-75`) should not be used for non-rule output types.

Optional-change:

- Existing `ArticleMetadataSelection` and article metadata UI counters that use `strategy_rules_count` can remain for old metadata selection, but should not be reused as taxonomy metrics.

## 5. Affected Extraction Prompts And Runtime Parsing

Must-change:

- `article_analysis_v1.md` must eventually replace `rule_extraction.strategy_rules[]` as the default trading-output list with a taxonomy list where each item has exactly one `primary_type`.
- Runtime parsing in `Stage3PromptRuntimeService` must stop enumerating only `final_payload["rule_extraction"]["strategy_rules"]` into `RuleCandidate` rows at `trade-strategy-ai/src/services/stage3_prompt_runtime_service.py:312-334`.
- Fingerprinting during extraction must not call `fingerprint_rule_payload()` for non-rule outputs. Current extraction uses `_fingerprint(rule)` at `stage3_prompt_runtime_service.py:159-160` and `:317`.

Should-change:

- Repair prompt/runtime should repair taxonomy schema validity and evidence alignment, not force missing fields until a semantic experience becomes rule-shaped.
- Prompt output should carry timestamp availability and data-dependency readiness for `executable_rule` and `research_hypothesis`.
- Source evidence must preserve article ID, article revision, prompt run, span/quote, and rationale for every type.

Optional-change:

- Keep the old prompt version as read-only historical provenance. Do not rewrite old prompt runs or raw outputs.

## 6. Affected Review Policy And Human Review Queues

Must-change:

- `article_review_policy.determine_automatic_review()` currently uses `backtestability_status`, presence of evidence/condition/action, `ambiguous_terms`, `missing_fields`, and `risk_controls` to return `pending_backtest`, `needs_human_review`, or `suggested_reject`. See `trade-strategy-ai/src/services/article_review_policy.py:138-219`.
- `rule_review_service._classify_candidate()` treats non-`executable` `backtestability_status` as not backtestable, then uses `manual_review_required`, `ambiguous_terms`, `candidate.missing_fields`, inferred fields, Kaipan dependencies, and governance conflicts. See `trade-strategy-ai/src/services/rule_review_service.py:153-251`.
- Human review actions in `rule_review_service.py:467-649` are rule-candidate actions (`edit`, `approve`, `approve_after_edit`, `merge`, `hold`, `reject`) and should not apply to semantic/data/noise items.

Should-change:

- Create separate queues:
  - `executable_rule`: validation sampling or direct governance gate.
  - `rule_candidate`: repair/completion review.
  - `research_hypothesis`: research design review.
  - `semantic_experience`: semantic dictionary review or optional research mining.
  - `risk_control_hint`: risk design backlog.
  - `data_requirement_hint`: data/platform backlog.
  - `unusable_noise`: reject/retain evidence only.
- Article extraction review UI should show a mixed taxonomy result list, not only "候选规则与审核".

Optional-change:

- Keep current rule review workbench for formal rule candidates while adding new review surfaces gradually.

## 7. Affected Backtest Eligibility And Rule Promotion

Must-change:

- Current Stage 3 automatic review can mark `partially_executable` as `pending_backtest` when heavy gates do not fire. `article_review_policy.py:205-217` explicitly allows `partially_executable` into `pending_backtest`. This conflicts with Step 2: only `executable_rule` may directly enter backtest.
- Rule review service blocks non-`executable` candidates in `rule_review_service.py:183-194`, but the article analysis review path calls lifecycle approval separately and the promotion service itself does not validate taxonomy type or full executable admission criteria.
- Rule promotion assumes `candidate.canonical_payload` contains formal rule fields. `rule_lifecycle_service.py:530-557` maps payload fields directly into `RuleVersion`.
- Governance assessment marks candidates `eligible_for_formal_version` and `eligible_for_backtest` based only on duplicate status in `rule_governance_service.py:311-318`, not extraction type or executability completeness.

Should-change:

- Move direct backtest eligibility to `primary_type == executable_rule` plus strict admission criteria: complete trade mechanics, no core ambiguous terms, timestamp-safe data, no lookahead, and deterministic dependencies.
- `rule_candidate` should be ineligible for direct backtest until it is repaired into a new `executable_rule` or formal `RuleVersion`.
- `research_hypothesis` should produce a research validation plan, not a `RuleVersion`.

Optional-change:

- Existing formal backtest service can remain downstream of `RuleVersion` because `BacktestSelection` accepts `rule_version_id` or `rule_family_id`, not `rule_candidate_id` (`trade-strategy-ai/src/services/backtest_application_service.py:58-75`). Its main impact is the upstream gate that creates `RuleVersion`.

## 8. Affected Jobs And Workflow Orchestration

Must-change:

- Extraction: `Stage3PromptRuntimeService.analyze_article()` persists only rule candidates. It needs an extraction-item writer before any taxonomy prompt can be safely used.
- Re-extraction: current cache key is prompt/schema/model/input hash in `stage3_prompt_runtime_service.py:63-78` and repository lookup in `stage3_prompt_runtime_repository.py:10-53`. Taxonomy version must be part of identity and provenance.
- Reclassification: no current first-class job exists to reclassify old `rule_candidates` into taxonomy types without rewriting them.
- Review: current article review and rule review workflows assume candidate-rule actions and lifecycle.
- Validation/backtest: promotion to `RuleVersion` is the boundary that backtest consumes; the taxonomy must block non-executable items before that boundary.

Should-change:

- Add job/workflow types for taxonomy extraction, taxonomy re-extraction, old-candidate reclassification, research review, semantic dictionary review, and data requirement backlog review.
- Stage 3 batch currently counts automatic review statuses (`stage3_batch_service.py:123-160`); it should count taxonomy output types and destinations.
- Job registry has backtest and rule-pool jobs (`job_registry.py:825-944`) and candidate/rule review jobs (`:948-1015`), but no taxonomy reclassification or research/data backlog job.

Optional-change:

- Keep existing `stage3-article-batch` as a historical workflow name for old prompt runs, but avoid routing new taxonomy extraction through old status names.

## 9. Affected UI Pages And User Flows

Must-change:

- Article extraction review: `web/src/pages/articles/ArticleResultsJourneyPage.tsx:405-485` is explicitly "候选规则与审核"; it renders `rule_type`, `backtestability_status`, Kaipan dependency, market-state declaration, and approve/reject actions for every candidate.
- Article-analysis labels treat `pending_backtest` as success at `ArticleResultsJourneyPage.tsx:80-89`.
- Article-analysis API/types cannot represent non-rule output types, as noted in sections 4 and 6.

Should-change:

- Rule pool: `api/routers/ui/rule_pool.py:145-194` lists `RulePool` rows and filters by `review_status`, `rule_type`, `mapping_status`, `source_type`, and `instrument_focus`. New taxonomy output types should not be pushed into this rule pool unless they are actual rule artifacts.
- Rules review page: `web/src/pages/rules/index.tsx:42-57` describes confirming article-extracted candidate rules for validation, and `:179-283` renders candidate detail/actions. It should stay a rule-candidate/executable-rule workbench only.
- Backtest: `web/src/pages/rules/index.tsx:305-317` and `BacktestApplicationService` are formal-rule paths. UI impact is mostly to ensure only formal executable rules appear as choices.
- Research review: new page/queue needed for `research_hypothesis`.
- Semantic dictionary: new page or module needed for `semantic_experience` with source term, normalized term, evidence, and mapping status.
- Data requirement backlog: new page/queue needed for `data_requirement_hint`, including required dataset, timestamp availability, owner, and readiness.

Optional-change:

- `web/src/features/backtest/backtest-candidates-page.tsx` is a strategy-version candidate workflow, not the article extraction `rule_candidates` path. It can remain separate but should avoid terminology confusion if the taxonomy adds "rule_candidate".

## 10. Existing 488 Rule Candidates Migration Options

Must-change:

- Preserve all 488 old `rule_candidates` unchanged as audit evidence. Step 1 found 488 candidates, 0 rule versions, 34 persisted `executable`, 441 `partially_executable`, 13 `not_executable`, 455 with ambiguous terms, and 188 with missing fields.
- Do not delete, overwrite, or silently reclassify old rows.
- Do not use relaxed eligibility to move old fuzzy rows into backtest.

Option 1: append-only reclassification table

- Add `extraction_reclassification_runs` and `extraction_reclassification_items` or use existing migration run tables with a typed payload.
- Each old `rule_candidate_id` gets a new taxonomy label, confidence, rationale, evidence refs, and reviewer/model provenance.
- Best for preserving audit evidence and comparing old vs new taxonomy without mutating old rows.

Option 2: new `extraction_items` table with legacy links

- Create new taxonomy items linked to old `rule_candidate_id`, `article_structure_id`, `prompt_run_id`, and source evidence.
- Old rows remain frozen; new rows become the product path.
- Best long-term model if implementation continues inside `trade-strategy-ai`.

Option 3: extend `rule_candidates` in place

- Add `primary_type`, `taxonomy_payload`, and routing fields to old rows.
- Lowest table count, but highest semantic risk because non-rule types would live in a table named `rule_candidates` and continue to be reachable by old rule review/governance code.

Recommended migration approach: Option 2 with an append-only reclassification run. It preserves old evidence, creates the new product path, and avoids changing old row meaning.

## 11. Route Options Analysis

### A. Continue Inside trade-strategy-ai

Must-change:

- Add the taxonomy storage/API/review layer before changing prompt/runtime.
- Keep formal backtest downstream of strict `RuleVersion`.
- Retire or isolate old rule-candidate flows from ordinary navigation when the new path is ready.

Pros:

- Reuses article storage, prompt trace, source revisions, rule governance, dataset snapshots, and formal backtest infrastructure.
- Best if the desired final product still includes executable-rule validation and backtest.

Cons:

- Requires careful removal or isolation of old assumptions across Stage 3/4 UI, services, API contracts, and jobs.
- More risk of accidental old-path fallback unless the implementation enforces a single formal taxonomy path.

Assessment: feasible, but only clean if the taxonomy becomes a first-class layer instead of a wrapper around `rule_candidates`.

### B. Build New Hypothesis-First Project

Must-change:

- Define new storage and workflows around hypotheses, semantic terms, risk hints, and data requirements first.
- Treat `trade-strategy-ai` as an external evidence/backtest source, not the owner of the ontology.

Pros:

- Cleaner mental model if most extracted content is semantic/research rather than executable.
- Avoids fighting existing rule-candidate, rule-pool, and review wording.

Cons:

- Duplicates article ingestion/provenance unless deliberately shared.
- Backtest/governance integration still has to reconnect to `trade-strategy-ai` or be rebuilt.

Assessment: may be better if the near-term product goal is research knowledge mining rather than executable strategy governance.

### C. Keep trade-strategy-ai As Data/Backtest Reference

Must-change:

- Freeze old extraction route as reference evidence.
- Expose or export formal data/backtest capabilities to a new taxonomy/research system.

Pros:

- Reduces risk to the current delivery-stage product.
- Lets taxonomy work proceed without destabilizing formal backtest/data services.

Cons:

- Does not solve article extraction UX inside `trade-strategy-ai`.
- Requires boundary/API work between systems.

Assessment: useful if implementation risk inside the current repo is considered too high, or if taxonomy work should move faster than product stabilization allows.

### D. Redesign Extraction Prompt/Runtime First

Must-change:

- Redesign runtime storage and parsing before running a new taxonomy prompt on production articles.
- Keep Step 1 conclusion: `executable_rule` is narrow and not the default extraction target.

Pros:

- Directly addresses the ontology failure found in Step 1.
- Prevents fuzzy outputs from continuing through review/backtest as rule candidates.

Cons:

- If done as prompt-only, it will fail at persistence because current runtime only writes `RuleCandidate`.
- Needs storage/API contract before prompt rollout.

Assessment: still the correct direction, but "prompt/runtime first" must mean "taxonomy contract and runtime storage first", not just prompt text changes.

## 12. Recommended Implementation Sequence

1. User decision: choose whether taxonomy implementation stays inside `trade-strategy-ai` or moves to a new hypothesis-first project.
2. Storage/API spec: define `extraction_items`, type-specific payload contracts, evidence links, review destinations, and old-candidate reclassification records.
3. Fixed regression fixtures: define expected taxonomy labels for a small representative set from the old 488 candidates, including semantic-heavy, risk-only, data-requirement, hypothesis, and truly executable examples.
4. Runtime writer: add an append-only taxonomy writer that stores new output items without touching old `rule_candidates`.
5. Prompt/schema update: only after storage exists, update extraction schema to output seven mutually exclusive primary types.
6. Review routing: add type-specific queues and keep rule promotion limited to `executable_rule`.
7. Migration/reclassification: run old 488 candidates through append-only reclassification and sample human review.
8. UI updates: replace article extraction review with taxonomy results; keep rule review/backtest pages downstream of executable/formal rules.
9. Backtest guard: enforce that formal backtest only sees `RuleVersion` created from `executable_rule` or human-approved repaired rules with complete strict criteria.

## 13. Risks And Blockers

Must-change risks:

- Existing rule promotion can create `RuleVersion` from rule-shaped payloads without checking a taxonomy primary type.
- Existing automatic review can mark some `partially_executable` candidates as `pending_backtest`, which conflicts with the new taxonomy policy.
- Overloading `rule_candidates` would keep misleading names, foreign keys, and UI labels in the ordinary product path.

Should-change risks:

- New taxonomy output requires additional UI surfaces; otherwise useful non-rule outputs will be hidden or misrouted.
- Old 488 candidates need evidence-preserving reclassification, not in-place relabeling.
- Prompt-only redesign would create outputs the current Pydantic/runtime/API contracts cannot store or display.

Optional risks:

- Keeping both `rule_pool` and formal `rule_candidates` visible may confuse users unless navigation and wording are tightened.
- A separate project reduces ontology risk but adds integration and provenance duplication risk.

Blockers before implementation:

- Storage route decision: extend existing table vs new extraction item tables.
- Product route decision: implement inside `trade-strategy-ai` vs new hypothesis-first project.
- Review destination decision for `semantic_experience`, `risk_control_hint`, and `data_requirement_hint`.

## 14. Open Questions Requiring User Decision

1. Should the taxonomy be implemented inside `trade-strategy-ai`, or should a new hypothesis-first project own semantic/research outputs while `trade-strategy-ai` remains the data/backtest reference?
2. If inside `trade-strategy-ai`, should the product path use a new `extraction_items` table as recommended, with old `rule_candidates` preserved as historical evidence?
3. Should old 488 candidates be reclassified by an append-only model-assisted run plus sampled human review, or by full human labeling?
4. Which output destinations are in scope for the first implementation slice: only `executable_rule`/`rule_candidate`, or also `research_hypothesis`, `semantic_experience`, and `data_requirement_hint` queues?
5. What is the minimum admission checklist for `executable_rule` in implementation: exactly the Step 2 criteria, or a stricter project-specific subset for the first rollout?
