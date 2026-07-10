# Extraction Taxonomy Storage/API Spec

## 1. Executive Summary

This document defines the proposed storage and API contract for a new taxonomy-first extraction layer in `trade-strategy-ai`.

The accepted direction is:

- Continue implementation planning inside `trade-strategy-ai`.
- Do not continue the old `rule_candidates` path as the default extraction product path.
- Add a new `extraction_items` layer before rule governance and backtest.
- Preserve the existing 488 old `rule_candidates` unchanged as historical audit evidence and append-only reclassification input.
- Do not overload `rule_candidates` with the new taxonomy.

The core storage object is `extraction_items`. Each item has exactly one `primary_type`:

```text
executable_rule
rule_candidate
research_hypothesis
semantic_experience
risk_control_hint
data_requirement_hint
unusable_noise
```

`executable_rule` is intentionally narrow. It is not the default extraction target. Only `executable_rule` may directly enter rule governance and formal backtest, and only after strict validation. `rule_candidate` is a repair/completion object, not a directly backtestable object. All other types are non-rule outputs and must not enter rule promotion or formal backtest.

This document is a design/spec document only. It does not define an executable migration, does not change prompt schemas, does not modify runtime services, does not modify UI, and does not reclassify production data.

## 2. Design Decisions

| Decision | Spec |
| --- | --- |
| New product storage path | Add a future `extraction_items` layer rather than extending `rule_candidates`. |
| Old candidate handling | Keep the existing 488 `rule_candidates` unchanged as audit evidence. |
| Primary taxonomy | Every extraction item must have exactly one `primary_type` from the seven allowed values. |
| Secondary meaning | Cross-cutting labels belong in `secondary_tags`; they must not override `primary_type`. |
| Rule promotion gate | Only `primary_type = executable_rule` may directly enter rule governance/backtest. |
| Repair gate | `rule_candidate` must enter repair/completion before any backtest or `RuleVersion` creation. |
| Non-rule lanes | `research_hypothesis`, `semantic_experience`, `risk_control_hint`, `data_requirement_hint`, and `unusable_noise` must not be promoted as rules. |
| Evidence model | Every retained item must preserve article, article structure, prompt run, source quote/span, and provenance. |
| Reclassification model | Old 488 candidate reclassification must be append-only and must not mutate old rows. |
| Runtime order | Prompt/runtime changes must happen after this storage/API spec is accepted. |

The current codebase assumes that `article_analysis_v1.rule_extraction.strategy_rules[]` becomes `RuleCandidate[]`. The future implementation must replace that assumption with an extraction-item writer before any taxonomy prompt rollout.

## 3. New Storage Layer: extraction_items

### 3.1 Proposed table purpose

`extraction_items` is the canonical storage layer for article-derived extraction outputs after taxonomy redesign.

It is not a rule table. It stores rule-like and non-rule extraction outputs with a shared evidence/provenance envelope and a type-specific `taxonomy_payload`.

### 3.2 Proposed identity and references

Recommended logical storage shape:

| Field | Purpose |
| --- | --- |
| `extraction_item_id` | Stable item UUID. |
| `article_id` | Source article ID, matching `blog_articles.id`. |
| `article_revision_id` | Source revision used during extraction, when available. |
| `article_structure_id` | Parent article structure output. |
| `prompt_run_id` | Prompt run that produced the item. |
| `item_index` | Stable order within the prompt run or article structure. |
| `item_fingerprint` | Stable content/evidence fingerprint for idempotency and duplicate detection. |
| `taxonomy_version` | Version of the seven-type taxonomy contract. |
| `schema_version` | Version of the extraction item schema. |
| `primary_type` | One of the seven allowed values. |
| `secondary_tags` | Optional cross-cutting tags. |
| `taxonomy_payload` | Type-specific payload. |
| `source_evidence` | Source span, quote, and evidence details. |
| `confidence` | Extractor confidence and optional calibration metadata. |
| `quality_state` | Storage/review quality state. |
| `review_destination` | Minimal routing destination. |
| `review_state` | Current review state for the item lane. |
| `provenance` | Model, prompt, reclassification, and lineage metadata. |
| `created_at` / `updated_at` | Timestamps. |
| `created_by` / `updated_by` | Actor or service. |

### 3.3 Recommended constraints

- `primary_type` must be required.
- `primary_type` must be exactly one of the seven allowed values.
- `taxonomy_payload` must validate against the contract for `primary_type`.
- `secondary_tags` may include taxonomy-related tags but must not create additional primary classifications.
- `review_destination` must be derived from `primary_type` unless explicitly overridden by a human reviewer.
- `item_fingerprint` should include taxonomy version, source quote/span, primary type, normalized payload summary, article revision, and prompt run identity.
- Future `RuleVersion` links must point back to the source `extraction_item_id`, not require mutation of old `rule_candidates`.

### 3.4 Relationship to existing `ArticleStructure` and `PromptRun`

The current `ArticleStructure` remains the article-level prompt output parent. The new item layer should reference it rather than replacing it.

`PromptRun` remains the prompt execution trace. A taxonomy extraction item must preserve the prompt run that produced it, including prompt name/version, schema version, model, validation state, retry count, token/cost metadata, and raw output trace through the existing prompt-run record.

## 4. Common Field Contract

### 4.1 Required common fields

| Field | Required | Description |
| --- | --- | --- |
| `extraction_item_id` | Yes | UUID for the taxonomy item. |
| `article_id` | Yes | Source article ID. |
| `article_revision_id` | Strongly recommended | Source revision used for extraction. Required when revision data exists. |
| `article_structure_id` | Yes | Parent article structure generated by the prompt/runtime path. |
| `prompt_run_id` | Yes | Prompt run that generated or reclassified the item. |
| `item_index` | Yes | Stable item order within the extraction result. |
| `source_span` | Yes for retained items | Structured source location when available. |
| `source_quote` | Yes for retained items except pure rejected noise | Verbatim source quote or short quote fragment. |
| `evidence` | Yes | Evidence list/rationale tying payload to source text. |
| `primary_type` | Yes | Exactly one of the seven allowed values. |
| `secondary_tags` | Yes | Empty list allowed. Cross-cutting labels only. |
| `taxonomy_payload` | Yes | Type-specific payload contract. |
| `confidence` | Yes | Numeric confidence plus reason/calibration metadata. |
| `quality_state` | Yes | Storage quality and review quality state. |
| `review_destination` | Yes | Minimal review lane. |
| `review_state` | Yes | Review state within that lane. |
| `created_at` / `updated_at` | Yes | Storage timestamps. |
| `provenance` | Yes | Extraction/reclassification lineage. |

### 4.2 `primary_type` enum

Allowed values:

```text
executable_rule
rule_candidate
research_hypothesis
semantic_experience
risk_control_hint
data_requirement_hint
unusable_noise
```

No other values are allowed in the first implementation slice.

### 4.3 `secondary_tags`

`secondary_tags` are optional descriptors for cross-cutting meaning. They may include values such as:

- `market_state`
- `risk`
- `data_dependency`
- `auction`
- `sector`
- `breadth`
- `sentiment`
- `position_sizing`
- `exit_logic`
- `semantic_term`
- `duplicate_theme`

`secondary_tags` must not be used to bypass the primary-type gate. For example, an item with `primary_type = semantic_experience` and `secondary_tags = [risk, data_dependency]` remains non-backtestable and non-promotable.

### 4.4 `confidence`

Recommended shape:

| Field | Required | Description |
| --- | --- | --- |
| `score` | Yes | Decimal in `[0, 1]`. |
| `level` | Yes | `high`, `medium`, or `low`. |
| `rationale` | Yes | Short reason for confidence. |
| `requires_human_confirmation` | Yes | Boolean. |

Low confidence must not be hidden. It should either route to a review lane or be retained as low-quality evidence.

### 4.5 `quality_state`

Recommended values:

```text
valid
partial
invalid
needs_review
rejected
superseded
```

`valid` means the item satisfies the storage contract for its type. It does not mean it is a valid trading rule. For example, a valid `semantic_experience` remains non-backtestable.

### 4.6 `review_state`

Recommended values:

```text
unreviewed
queued
in_review
accepted
rejected
repaired
promoted
archived
```

`promoted` is only valid for `executable_rule` after formal rule governance creates or links a `RuleVersion`. `rule_candidate` should become `repaired` or produce a new validated `executable_rule`; it should not be marked `promoted` directly.

## 5. Type-Specific Payload Contracts

### 5.1 `executable_rule`

`executable_rule` is a complete, timestamp-safe trading rule that can be converted into deterministic execution logic and backtested without unresolved core ambiguity.

Required payload fields:

| Field | Required | Description |
| --- | --- | --- |
| `title` | Yes | Human-readable rule title. |
| `rule_type` | Yes | Entry, exit, filter, risk, sizing, selection, or project-approved rule type. |
| `instrument_universe` | Yes | What instruments are eligible. |
| `entry_condition` | Yes | Deterministic entry condition. |
| `entry_timing` | Yes | When the entry condition is evaluated. |
| `entry_price_reference` | Yes | Price used for simulated entry. |
| `exit_condition` | Yes | Deterministic exit condition. |
| `exit_timing` | Yes | When exit is evaluated. |
| `exit_price_reference` | Yes | Price used for simulated exit. |
| `stop_loss_or_invalidation` | Yes | Loss boundary or invalidation logic. |
| `position_sizing` | Yes | Exact sizing or bounded sizing rule. |
| `holding_period` | Required if applicable | Maximum/minimum holding rule. |
| `data_dependencies` | Yes | Required datasets and fields. |
| `timestamp_availability` | Yes | When every dependency is available relative to decision time. |
| `lookahead_check` | Yes | Explicit result proving no future data is used. |
| `ambiguous_terms` | Yes | Must be empty or explicitly non-core and bounded. |
| `parameterization` | Yes | Parameters with units, allowed ranges, defaults, and source. |
| `rule_version_candidate` | Yes | Mapping preview for future `RuleVersion` fields. |
| `not_directly_backtestable` | Yes | Must be `false` only if all admission criteria pass. |

Admission criteria:

- Complete instrument universe.
- Complete entry, exit, risk, sizing, timing, and price-reference mechanics.
- Required data and timestamp availability are explicit.
- No unresolved core ambiguous terms.
- No lookahead or future-function dependency.
- Evidence supports the rule mechanics.

Rejection criteria:

- Depends on unresolved terms such as `退潮`, `回暖`, `分歧`, `弱转强`, `主线`, `龙头`, `冰点`, `高潮`, or `承接`.
- Uses actions like observe, wait, avoid, select, or pay attention without full trade mechanics.
- Lacks entry timing, exit timing, price reference, position sizing, stop loss/invalidation, or timestamp availability.

### 5.2 `rule_candidate`

`rule_candidate` is a near-rule. It has a clear trading-rule skeleton but lacks bounded fields that must be repaired before any formal backtest.

Required payload fields:

| Field | Required | Description |
| --- | --- | --- |
| `candidate_rule_summary` | Yes | Short description of the possible rule. |
| `known_components` | Yes | Present rule fields. |
| `missing_fields` | Yes | Bounded list of missing fields. |
| `repair_tasks` | Yes | Concrete tasks required before validation. |
| `repair_source` | Yes | Source text, project convention, parameter search, or human input. |
| `repairability` | Yes | `high`, `medium`, or `low`. |
| `instrument_universe_status` | Yes | Complete, partial, missing, or not applicable. |
| `entry_exit_status` | Yes | Which entry/exit mechanics are present or absent. |
| `data_dependencies` | Yes | Known or probable datasets. |
| `timestamp_availability_risk` | Yes | Known timing risks. |
| `ambiguous_terms` | Yes | Ambiguous terms and whether they are core. |
| `not_directly_backtestable` | Yes | Must be `true`. |

Routing rule:

`rule_candidate` must enter repair/completion. It may later produce a new `executable_rule` item or a formal rule proposal only after missing fields are resolved and strict executable-rule validation passes.

It must not directly create a `RuleVersion` and must not enter formal backtest.

### 5.3 `research_hypothesis`

`research_hypothesis` is a testable market claim derived from source experience. It is not a trading rule.

Required payload fields:

| Field | Required | Description |
| --- | --- | --- |
| `hypothesis_statement` | Yes | Testable market claim. |
| `source_experience` | Yes | Original experience or market-language statement. |
| `dependent_variables` | Yes | Outcomes to measure. |
| `independent_variables` | Yes | Explanatory variables. |
| `candidate_observable_indicators` | Yes | Possible measurable proxies. |
| `required_data` | Yes | Data required to test the claim. |
| `validation_method` | Yes | Event study, grouped return study, regression, or other research method. |
| `timestamp_availability_assumptions` | Yes | When variables are known relative to decisions. |
| `research_status` | Yes | Proposed, accepted, rejected, tested, or archived. |
| `not_directly_backtestable` | Yes | Must be `true`. |

Routing rule:

`research_hypothesis` may enter research review. It may produce future indicators, semantic mappings, or rule candidates after validation. It must not directly enter strategy backtest or `RuleVersion` promotion.

### 5.4 `semantic_experience`

`semantic_experience` preserves trader language, market interpretation, cycle description, or subjective trading experience.

Required payload fields:

| Field | Required | Description |
| --- | --- | --- |
| `term_or_phrase` | Yes | Extracted semantic term or phrase. |
| `source_context` | Yes | How the term was used. |
| `plain_language_interpretation` | Yes | Normal-language interpretation. |
| `related_market_state` | Optional | Cycle, sentiment, liquidity, sector, breadth, or other market state. |
| `possible_observable_proxies` | Optional | Candidate indicators if the source supports them. |
| `semantic_dictionary_action` | Yes | Add, merge, clarify, reject, or observe. |
| `ambiguity_level` | Yes | High, medium, or low. |
| `not_directly_backtestable` | Yes | Must be `true`. |

Routing rule:

`semantic_experience` may enter semantic dictionary review or later inspire research hypotheses. It must not be promoted as a rule.

### 5.5 `risk_control_hint`

`risk_control_hint` is a risk-management or discipline statement that may inform future system design but is not a complete trading strategy.

Required payload fields:

| Field | Required | Description |
| --- | --- | --- |
| `risk_context` | Yes | When the risk control applies. |
| `risk_action` | Yes | Reduce, pause, avoid, cap, stop, or similar action. |
| `sizing_boundary` | Optional | Numeric boundary if present. |
| `trigger_terms` | Yes | Source terms activating the hint. |
| `missing_definitions` | Yes | Undefined terms or thresholds. |
| `system_design_use` | Yes | Future risk module, portfolio throttle, or review backlog usage. |
| `data_dependencies` | Optional | Data needed to evaluate the risk context. |
| `not_directly_backtestable` | Yes | Must be `true`. |

Routing rule:

`risk_control_hint` enters the risk backlog. It must not be promoted as a standalone rule. It can only influence a future executable rule if integrated into complete entry/exit/sizing/timestamp-safe mechanics.

### 5.6 `data_requirement_hint`

`data_requirement_hint` identifies a needed dataset, feature, label, or timestamped market input.

Required payload fields:

| Field | Required | Description |
| --- | --- | --- |
| `data_name` | Yes | Name of required data or feature. |
| `data_description` | Yes | Meaning of the data. |
| `needed_by` | Optional | Related rule, hypothesis, semantic term, or risk hint. |
| `timestamp_requirement` | Yes | When the data must be available. |
| `granularity` | Yes | Tick, auction, intraday, daily, sector, market, or article-level. |
| `source_or_provider` | Optional | Known source/provider if any. |
| `availability_status` | Yes | Available, unavailable, unknown, or partial. |
| `data_contract_gap` | Yes | Missing field, provider, timestamp, coverage, or quality issue. |
| `not_directly_backtestable` | Yes | Must be `true`. |

Routing rule:

`data_requirement_hint` enters the data requirement backlog. It must not be promoted as a rule or used as a substitute for an executable condition.

### 5.7 `unusable_noise`

`unusable_noise` is content that should not enter rule, hypothesis, semantic, risk, or data lanes.

Required payload fields:

| Field | Required | Description |
| --- | --- | --- |
| `reason` | Yes | Why the content is unusable. |
| `noise_category` | Yes | Motivational, duplicate, hallucinated, contradictory, non-trading, too vague, or unsupported. |
| `retain_source_reference_only` | Yes | Usually `true`. |
| `dedupe_key` | Optional | If rejected as duplicate. |

Routing rule:

`unusable_noise` enters noise rejection. It must not enter repair, rule governance, research validation, or backtest.

## 6. Source Evidence And Provenance Contract

### 6.1 Source evidence

Recommended `source_evidence` shape:

| Field | Required | Description |
| --- | --- | --- |
| `article_id` | Yes | Source article ID. |
| `article_revision_id` | Strongly recommended | Revision used for extraction. |
| `article_structure_id` | Yes | Parent structure. |
| `prompt_run_id` | Yes | Prompt run that produced the item. |
| `source_url` | Optional | Source URL for user traceability. |
| `quote` | Yes for retained items | Short source quote. |
| `span` | Recommended | Start/end offsets when available. |
| `section` | Optional | Article section or paragraph index. |
| `evidence_kind` | Yes | Explicit quote, inferred from context, reclassification of old candidate, or human annotation. |
| `rationale` | Yes | Why the evidence supports the taxonomy item. |

Evidence must be source-grounded. If source evidence is missing, the item must be `invalid`, `needs_review`, or `unusable_noise`; it must not be treated as valid.

### 6.2 Provenance

Recommended `provenance` shape:

| Field | Required | Description |
| --- | --- | --- |
| `origin` | Yes | New taxonomy extraction, old candidate reclassification, human annotation, or repair output. |
| `source_object_type` | Yes | Article, article structure, prompt run, rule candidate, or manual review. |
| `source_object_id` | Yes when applicable | ID of the source object. |
| `prompt_name` | Yes for model output | Prompt name. |
| `prompt_version` | Yes for model output | Prompt version. |
| `schema_version` | Yes | Schema version used for validation. |
| `taxonomy_version` | Yes | Taxonomy version. |
| `model` | Yes for model output | Model used. |
| `classifier` | Optional | Reclassification model or human reviewer. |
| `lineage` | Yes | Parent item IDs or old candidate IDs if derived. |
| `created_by_process` | Yes | Runtime, reclassification job, reviewer, or migration job. |

Provenance must make it possible to answer:

- Which article text produced this item?
- Which prompt/model/schema produced it?
- Was it a new taxonomy extraction or an old `rule_candidate` reclassification?
- Which old candidate, if any, was used as input?
- Was the item human-edited, repaired, or superseded?

## 7. Relationship To Existing rule_candidates

The existing `rule_candidates` table is rule-shaped and currently contains fields such as `rule_type`, `canonical_payload`, `evidence_json`, `missing_fields`, `data_dependencies`, `backtestability_status`, `review_state`, and `quality_status`.

That shape is not suitable as the new taxonomy store because:

- The table name and relationships imply every row is a candidate rule.
- Existing review/governance code can fingerprint and promote candidate payloads as rule-shaped objects.
- Existing API and UI schemas expose `candidates[]`, automatic review status, governance eligibility, and backtestability status as if all outputs are rule candidates.
- Non-rule taxonomy outputs would remain reachable by old rule review/governance paths if stored in `rule_candidates`.

Future implementation should treat old `rule_candidates` as:

- historical extraction output,
- audit evidence,
- input to append-only reclassification,
- source lineage for future taxonomy items,
- not the ordinary product path for new taxonomy extraction.

New taxonomy outputs must not be stored by mutating old `rule_candidates`.

## 8. Append-Only Reclassification Design For Old 488 Candidates

### 8.1 Requirements

The existing 488 old `rule_candidates` must remain unchanged.

Reclassification must:

- Create new append-only records.
- Preserve the old candidate ID and old payload as source evidence.
- Store the new taxonomy label separately.
- Store confidence, rationale, reviewer/model provenance, and source evidence.
- Allow multiple reclassification runs without overwriting prior results.
- Avoid changing old `backtestability_status`, `review_state`, `quality_status`, or `canonical_payload`.

### 8.2 Recommended reclassification run model

Recommended logical run object:

| Field | Purpose |
| --- | --- |
| `reclassification_run_id` | Stable UUID. |
| `taxonomy_version` | Taxonomy version used. |
| `schema_version` | Reclassification schema version. |
| `source_population` | Example: old 488 `rule_candidates`. |
| `input_query_fingerprint` | Fingerprint of source population selection. |
| `classifier` | Model, script, human labeling batch, or mixed mode. |
| `started_at` / `completed_at` | Run timing. |
| `status` | Pending, running, completed, failed, cancelled. |
| `created_by` | Actor or service. |

Recommended logical run item:

| Field | Purpose |
| --- | --- |
| `reclassification_item_id` | Stable UUID. |
| `reclassification_run_id` | Parent run. |
| `old_rule_candidate_id` | Source old candidate. |
| `extraction_item_id` | New taxonomy item created from reclassification, when accepted. |
| `proposed_primary_type` | One of the seven values. |
| `proposed_secondary_tags` | Optional cross-cutting tags. |
| `proposed_taxonomy_payload` | Type-specific payload. |
| `confidence` | Reclassification confidence. |
| `rationale` | Why this classification was selected. |
| `review_state` | Unreviewed, accepted, rejected, superseded. |
| `evidence_snapshot` | Snapshot of old candidate evidence and relevant source article references. |

### 8.3 Reclassification output policy

Reclassifying an old `rule_candidate` should create a new taxonomy `extraction_item` only after the reclassification item validates against the new common and type-specific contracts.

If validation fails, the reclassification record may remain as a failed/proposed label, but it must not become the product-path taxonomy item.

Old candidates that appear executable under the old `backtestability_status` still require strict `executable_rule` validation before rule governance/backtest. The old status is evidence, not authority.

## 9. Relationship To RuleVersion And Backtest

### 9.1 `executable_rule` to `RuleVersion`

`executable_rule` can eventually become `RuleVersion` only after:

- Type contract validation passes.
- Source evidence is present and aligned.
- Strict executable-rule admission criteria pass.
- Governance fingerprinting is run on the normalized executable rule payload.
- Duplicate/conflict checks pass or are resolved.
- A lifecycle event records the promotion decision.

Future mapping from `executable_rule.taxonomy_payload` to `RuleVersion`:

| `RuleVersion` field | Source from `executable_rule` |
| --- | --- |
| `title` | `taxonomy_payload.title` |
| `description` | Rule summary and source rationale |
| `rule_type` | `taxonomy_payload.rule_type` |
| `instrument_scope` | `taxonomy_payload.instrument_universe` |
| `condition_json` | Entry/exit condition model as accepted by rule schema |
| `action_json` | Entry/exit action model as accepted by rule schema |
| `parameter_json` | Timing, holding period, sizing, risk controls, market-state definitions |
| `data_dependencies` | Data dependencies and timestamp availability |
| `evidence_json` | `source_evidence` plus provenance |
| `schema_version` | Future formal rule schema version |

The future formal source link should reference `extraction_item_id`. If compatibility with existing `RuleVersion.source_candidate_id` is still needed during transition, that compatibility must be read-only and must not require storing new taxonomy outputs inside old `rule_candidates`.

### 9.2 `rule_candidate` repair before backtest

`rule_candidate` must follow this path:

```text
rule_candidate
-> repair/completion review
-> resolved executable payload
-> new executable_rule item or formal rule proposal
-> strict executable validation
-> governance
-> RuleVersion
-> formal backtest
```

Repair may use source text, explicit project convention, bounded human input, or declared parameter search. It must not invent source meaning silently.

Until repair is complete, `rule_candidate` must have:

```text
not_directly_backtestable = true
review_destination = rule_candidate_repair
```

### 9.3 Why non-rule types must not enter promotion/backtest

`research_hypothesis` lacks complete trade mechanics and requires a research validation method before it can become a rule candidate or executable rule.

`semantic_experience` preserves language and interpretation, not deterministic conditions.

`risk_control_hint` may influence future risk modules but is not a standalone trading strategy without complete entry/exit/timing/sizing logic.

`data_requirement_hint` identifies missing data; it is not a condition or action.

`unusable_noise` is explicitly rejected or retained only as source reference.

Allowing these types into rule promotion would recreate the old failure mode: fuzzy market language becomes rule-shaped payload and enters governance/backtest with false structure.

## 10. Review Routing And Destinations

Minimal review routing:

| `primary_type` | `review_destination` | Purpose | Direct backtest? | Rule promotion? |
| --- | --- | --- | --- | --- |
| `executable_rule` | `executable_rule_validation` | Validate strict rule completeness and evidence. | Yes, after validation and governance. | Yes, after validation. |
| `rule_candidate` | `rule_candidate_repair` | Repair bounded missing fields before validation. | No. | No direct promotion. |
| `research_hypothesis` | `research_hypothesis_review` | Decide research design and validation priority. | No. | No. |
| `semantic_experience` | `semantic_dictionary_review` | Add, merge, clarify, or reject semantic terms. | No. | No. |
| `risk_control_hint` | `risk_backlog` | Preserve risk design ideas for future modules. | No. | No. |
| `data_requirement_hint` | `data_requirement_backlog` | Track data/platform requirements. | No. | No. |
| `unusable_noise` | `noise_rejection` | Reject or retain source reference only. | No. | No. |

Review actions should be lane-specific. For example, `approve` in executable-rule validation means the item may proceed to governance, while `accept` in semantic dictionary review means the term may enter the dictionary. Those actions are not equivalent and must not share old rule-candidate lifecycle semantics.

## 11. API Contract Proposal

### 11.1 Article extraction result shape

Future article extraction responses should expose `extraction_items[]` as the primary taxonomy result list.

Recommended top-level response additions:

| Field | Description |
| --- | --- |
| `taxonomy_version` | Taxonomy contract version. |
| `extraction_summary` | Counts by primary type, destination, quality state, and review state. |
| `extraction_items` | Mixed taxonomy output list. |

Recommended item response shape:

| Field | Description |
| --- | --- |
| `item_id` | `extraction_item_id`. |
| `item_index` | Stable item order. |
| `article_id` | Source article. |
| `article_revision_id` | Source revision. |
| `article_structure_id` | Parent structure. |
| `prompt_run_id` | Prompt run. |
| `primary_type` | One of seven values. |
| `secondary_tags` | Cross-cutting tags. |
| `display_title` | User-facing title/summary. |
| `display_summary` | User-facing explanation. |
| `source_evidence` | Source quote/span/evidence. |
| `taxonomy_payload` | Type-specific payload. |
| `confidence` | Confidence object. |
| `quality_state` | Item quality state. |
| `review_destination` | Lane destination. |
| `review_state` | Lane review state. |
| `backtest_eligibility` | Explicit eligibility object. |
| `promotion_eligibility` | Explicit promotion object. |
| `provenance` | Extraction/reclassification lineage. |
| `created_at` / `updated_at` | Timestamps. |

### 11.2 Backtest eligibility object

Recommended shape:

| Field | Description |
| --- | --- |
| `eligible` | Boolean. |
| `reason` | Human-readable reason. |
| `required_next_step` | Validation, repair, research review, semantic review, risk backlog, data backlog, rejection, or none. |

Policy:

- `eligible = true` is only possible for validated `executable_rule`.
- `rule_candidate` must return `eligible = false` with required next step `repair`.
- All non-rule types must return `eligible = false`.

### 11.3 Promotion eligibility object

Recommended shape:

| Field | Description |
| --- | --- |
| `eligible_for_rule_version` | Boolean. |
| `reason` | Human-readable reason. |
| `blocked_by` | Missing fields, ambiguity, data requirement, non-rule type, evidence failure, governance conflict, or validation not run. |

Policy:

- Only `executable_rule` may be eligible for `RuleVersion`.
- `rule_candidate` can become eligible only by producing a separate validated `executable_rule` or formal rule proposal after repair.
- Non-rule items are never eligible for `RuleVersion`.

### 11.4 Relationship to current API

The current article-analysis response exposes:

```text
candidates[]
```

The future taxonomy response should expose:

```text
extraction_items[]
```

During implementation planning, the old `candidates[]` response may remain as historical display only, but it must not be the product path for new taxonomy extraction. The future UI should not depend on old candidate IDs for non-rule types.

## 12. UI Contract Implications

The UI must display mixed taxonomy outputs without implying that every item is a rule candidate.

Required UI contract implications:

- The article analysis detail view should render `extraction_items[]`, grouped or filterable by `primary_type` and `review_destination`.
- The label "candidate rules" must not be used for non-rule types.
- Only `executable_rule` items may expose a path toward validation, governance, and backtest.
- `rule_candidate` items should expose repair/completion workflow, not backtest actions.
- `research_hypothesis` should route to research review.
- `semantic_experience` should route to semantic dictionary review.
- `risk_control_hint` should route to the risk backlog.
- `data_requirement_hint` should route to the data requirement backlog.
- `unusable_noise` should show rejection/retention reason and no promotion action.
- Low confidence, partial, invalid, unavailable, and evidence-missing states must be visible.

Ordinary users must not need internal terms such as prompt run ID, raw JSON, schema name, table name, or local path to understand the extraction result. Those details may exist in trace/provenance panels for operators.

## 13. Job/Workflow Contract Implications

Future jobs/workflows should separate taxonomy extraction from old Stage 3 rule-candidate extraction.

Recommended workflow concepts:

| Workflow | Purpose |
| --- | --- |
| Taxonomy extraction | Run taxonomy prompt/runtime and write `extraction_items`. |
| Taxonomy re-extraction | Re-run extraction with a new taxonomy/prompt/schema version. |
| Old-candidate reclassification | Append-only reclassification of the 488 old candidates. |
| Executable-rule validation | Validate strict executable-rule criteria. |
| Rule-candidate repair | Complete bounded missing fields and produce an executable output if valid. |
| Research hypothesis review | Prioritize and design research validation. |
| Semantic dictionary review | Add/merge/reject semantic terms. |
| Risk backlog review | Triage risk-control hints. |
| Data requirement backlog review | Triage required datasets/features. |
| Noise rejection | Retain or discard unusable outputs. |

Job identity should include:

- taxonomy version,
- prompt/schema version,
- model,
- article revision or source population,
- input hash,
- reclassification run ID when applicable.

Prompt-only changes are not safe before this storage/API contract exists because the current runtime only persists `RuleCandidate` rows.

## 14. First Implementation Slice

The first implementation slice after this spec is accepted should be narrow and evidence-preserving.

Recommended first slice:

1. Add future schema/migration for `extraction_items` and append-only old-candidate reclassification records.
2. Add backend schema types for the seven `primary_type` values and common item response shape.
3. Add a read-only article extraction API shape that can return `extraction_items[]`.
4. Add strict eligibility helpers that return `eligible = false` for all non-`executable_rule` types.
5. Add fixed fixtures for representative old candidates across all seven taxonomy types.
6. Add append-only reclassification writer for a small test subset, not the full production 488.
7. Validate that old `rule_candidates` remain unchanged.
8. Only after storage/API acceptance, update prompt/runtime to produce taxonomy output.

The first slice should not attempt to build every review UI surface. It should establish the data contract, eligibility gates, and append-only lineage first.

## 15. Non-Goals

This spec does not:

- create migrations,
- modify SQLAlchemy models,
- modify Pydantic schemas,
- modify prompts,
- modify runtime parsing,
- modify services,
- modify UI,
- run reclassification on production data,
- reclassify the 488 old candidates,
- delete or mutate old `rule_candidates`,
- relax backtest eligibility,
- create `RuleVersion` rows,
- build semantic dictionary UI,
- build research review UI,
- build data backlog UI,
- decide final provider/source for missing market datasets.

Prompt/runtime changes must come after this storage/API spec is accepted.

## 16. Risks And Open Questions

### 16.1 Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Overloading `rule_candidates` anyway | Recreates old false-rule path. | Use `extraction_items` as the new product path. |
| Prompt changes before storage | Taxonomy output cannot be persisted safely. | Implement storage/API first. |
| Non-rule items enter promotion | Fuzzy outputs become `RuleVersion`. | Enforce type-based promotion/backtest gates. |
| Old candidates are mutated | Audit evidence is lost. | Append-only reclassification only. |
| UI keeps old candidate language | Users interpret all outputs as rules. | Render by `primary_type` and destination. |
| `executable_rule` becomes default target | Extractor overclassifies fuzzy language again. | Keep strict admission criteria and validation fixtures. |
| Data timestamp assumptions are hidden | Backtests may use future data. | Require timestamp availability in rule/hypothesis/data payloads. |

### 16.2 Open questions

Open user decisions after this spec:

1. Whether the first implementation slice should include all seven review destinations in API shape, or only storage plus eligibility gates.
2. Whether old 488 candidate reclassification should start with model-assisted labeling plus sampled human review, or a full human labeling pass.
3. Whether future `RuleVersion` source links should add a new direct `extraction_item_id` link table immediately, or stage it after `extraction_items` exists.
4. Whether semantic dictionary review should be a dedicated UI surface in the first product phase or remain backend/API-only initially.

The core storage decision is not open in this spec: the recommended path is a new `extraction_items` layer, not mutation of old `rule_candidates`.

## 17. Acceptance Criteria For Future Implementation

Future implementation should be accepted only if all criteria below are true:

- New taxonomy outputs are stored in `extraction_items`, not by mutating old `rule_candidates`.
- `primary_type` allows exactly the seven specified values.
- Every extraction item has article, article structure, prompt run, source evidence, confidence, quality state, review destination, timestamps, and provenance.
- Type-specific payload validation exists for all seven primary types.
- `executable_rule` is narrow and requires complete entry, exit, risk, sizing, timing, data, timestamp, evidence, and lookahead checks.
- Only validated `executable_rule` may directly enter rule governance/backtest.
- `rule_candidate` is blocked from direct backtest and routed to repair/completion.
- `research_hypothesis` is blocked from direct backtest and routed to research review.
- `semantic_experience`, `risk_control_hint`, `data_requirement_hint`, and `unusable_noise` cannot be promoted as rules.
- The old 488 `rule_candidates` remain unchanged.
- Reclassification of old candidates is append-only and preserves old candidate IDs, evidence, confidence, rationale, and provenance.
- Article extraction API exposes `extraction_items[]` as the future product path.
- Review routing supports executable rule validation, rule candidate repair, research hypothesis review, semantic dictionary review, risk backlog, data requirement backlog, and noise rejection.
- Tests or fixtures prove that non-rule types cannot reach `RuleVersion` creation or formal backtest.
- Prompt/runtime changes are introduced only after storage/API acceptance.
