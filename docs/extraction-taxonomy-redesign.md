# Extraction Taxonomy Redesign

Date: 2026-07-09  
Status: Draft  
Scope: Step 2 design document only  
Target path: `docs/extraction-taxonomy-redesign.md`

---

## 1. Purpose

This document redesigns the extraction taxonomy / extraction ontology for `trade-strategy-ai`.

The goal is to stop treating all extracted trading-related text as `rule_candidate`. The new extraction contract must distinguish between:

1. `executable_rule`
2. `rule_candidate`
3. `research_hypothesis`
4. `semantic_experience`
5. `risk_control_hint`
6. `data_requirement_hint`
7. `unusable_noise`

This document does not implement code, database migrations, prompts, services, UI changes, or schema changes. It defines the target ontology and validation plan before implementation.

---

## 2. Source Audit Reference

This redesign is based on Step 1: `docs/rule-extraction-output-audit.md`.

The audit recommendation was:

```text
Recommendation: D. Redesign extraction before either path.
Status: ACCEPTED.
Confidence: High for the direction decision, medium for exact semantic-category proportions.
```

Key audit facts:

| Metric | Value |
| --- | ---: |
| Existing `rule_candidates` | 488 |
| Existing `rule_versions` | 0 |
| Persisted `executable` candidates | 34 |
| Persisted `partially_executable` candidates | 441 |
| Persisted `not_executable` candidates | 13 |
| Derived `pending_backtest` | 40 |
| Derived `needs_human_review` | 435 |
| Candidates with `ambiguous_terms` | 455 / 488 |
| Candidates with `missing_fields` | 188 / 488 |

The audit found that conditions and actions are often syntactically present, but semantically non-executable. The database showed zero candidates with missing condition/action, while most conditions still depended on custom market states, sentiment, repair, divergence, strength, popularity, or cycle phase.

The audit estimated that true or near-true executable rules are a small minority, while semantic experience dominates the extracted population.

---

## 3. Problem Statement

The current extraction contract failed because it used `rule_candidate` as the default output bucket.

That caused the extractor to convert many trading-related statements into rule-shaped rows even when the source text was actually:

- market interpretation,
- trader language,
- cycle description,
- subjective judgment,
- risk discipline,
- data requirement,
- research idea,
- or non-operational commentary.

The result is false structure:

- `condition` exists, but depends on ambiguous terms like `退潮`, `回暖`, `分歧`, `主线`, `龙头`, `弱转强`, `冰点`, `高潮`, `承接`.
- `action` exists, but is often only “select”, “observe”, “avoid”, “lower position”, or “wait”.
- `backtestability_status` appears meaningful, but many rows are not actually backtestable.
- human review becomes overloaded because reviewers are asked to repair content that was never a rule.
- relaxing review or backtest eligibility would move fuzzy content into backtests instead of fixing the ontology.

The core issue is not simply a bug in review policy. It is an extraction ontology error.

---

## 4. Design Principles

### 4.1 Executable rule is a narrow type

`executable_rule` must not be the default target. It is a strict, narrow output type.

A text span should become `executable_rule` only when it contains enough information to be executed without unresolved semantic interpretation, future knowledge, or unbounded human judgment.

### 4.2 Top-level type must be mutually exclusive

Each extracted item must have exactly one primary output type:

```text
primary_type:
  executable_rule
  rule_candidate
  research_hypothesis
  semantic_experience
  risk_control_hint
  data_requirement_hint
  unusable_noise
```

Secondary tags may exist for cross-cutting meaning, but they must not override the primary type.

Example:

```text
primary_type: semantic_experience
secondary_tags: [risk_control_hint, data_requirement_hint]
```

This prevents a fuzzy experience from being promoted as a rule merely because it also implies risk control or data needs.

### 4.3 Backtest eligibility must come from type, not optimism

Only `executable_rule` may directly enter backtest.

`rule_candidate` may enter repair / completion workflow, but not direct backtest.

`research_hypothesis` may enter research validation design, but not strategy backtest.

`semantic_experience`, `risk_control_hint`, and `data_requirement_hint` are useful, but they are not trading rules.

### 4.4 Preserve source evidence

Every extracted item must preserve source article evidence, including text span, article ID, prompt run, and rationale.

The old 488 `rule_candidates` should not be deleted. They should remain as audit evidence and migration input.

### 4.5 Separate meaning from execution

The system should preserve trader language like `退潮`, `主线`, `龙头`, and `弱转强`, but it must not pretend these terms are executable until they are mapped to observable indicators with timestamp-safe data.

### 4.6 Timestamp availability is mandatory

Any rule or hypothesis that uses data must declare when that data is available.

If the condition depends on data that would only be known after the trading decision, the output cannot be executable.

### 4.7 Data requirements are first-class outputs

A data need such as `kaipan_pre_market_bid`, `market_breadth`, `sector_strength`, or `market_cycle_label` is not a rule.

It should be extracted as `data_requirement_hint`.

---

## 5. Output Type Policy Matrix

| Output type | Direct backtest? | Rule promotion? | Human review? | Main destination |
| --- | --- | --- | --- | --- |
| `executable_rule` | Yes | Yes, after validation | Optional / sampled | Backtest and rule governance |
| `rule_candidate` | No | Not directly | Yes | Rule repair / completion |
| `research_hypothesis` | No | No | Research review | Hypothesis validation |
| `semantic_experience` | No | No | Optional research review | Semantic dictionary / hypothesis generation |
| `risk_control_hint` | No | No as standalone strategy | Optional risk review | Risk design backlog |
| `data_requirement_hint` | No | No | Data/platform review | Data contract backlog |
| `unusable_noise` | No | No | Usually no | Reject / retain source reference only |

---

## 6. Output Type Definitions

---

## 6.1 `executable_rule`

### Definition

An `executable_rule` is a complete, timestamp-safe trading rule that can be converted into deterministic execution logic and backtested without unresolved core ambiguity.

It must define what to trade, when to enter, how to enter, when to exit, how to control risk, what data is required, and when that data is known.

`executable_rule` is not the default extraction target.

### Minimum admission criteria

An item may be classified as `executable_rule` only if it contains all of the following:

1. instrument universe
2. entry condition
3. entry timing
4. entry price reference
5. exit condition
6. exit timing
7. stop loss or invalidation condition
8. position sizing or sizing boundary
9. data dependencies
10. timestamp availability
11. no unresolved core ambiguous terms
12. no future-function / lookahead dependency

### Required minimum fields

| Field | Required | Description |
| --- | --- | --- |
| `primary_type` | Yes | Must be `executable_rule` |
| `instrument_universe` | Yes | What instruments are eligible |
| `entry_condition` | Yes | Deterministic condition |
| `entry_timing` | Yes | When entry is evaluated |
| `entry_price_reference` | Yes | Open, close, VWAP, limit price, auction price, etc. |
| `exit_condition` | Yes | Deterministic exit condition |
| `exit_timing` | Yes | When exit is evaluated |
| `exit_price_reference` | Yes | Price used for exit simulation |
| `stop_loss_or_invalidation` | Yes | Loss boundary or rule invalidation |
| `position_sizing` | Yes | Exact size or bounded sizing rule |
| `data_dependencies` | Yes | Required datasets and fields |
| `timestamp_availability` | Yes | When each dependency becomes available |
| `ambiguous_terms` | Yes | Must be empty or non-core only |
| `lookahead_check` | Yes | Must explicitly pass |
| `source_evidence` | Yes | Article/span evidence |
| `confidence` | Yes | Extraction confidence |

### Admission example

Source meaning:

```text
If the index breaks below the low of the resonance day, exit.
```

Possible classification:

```text
primary_type: executable_rule
instrument_universe: positions opened by the resonance-day strategy
entry_condition: inherited from upstream resonance strategy
exit_condition: index low < resonance_day_low
exit_timing: daily close or intraday break, must be specified
exit_price_reference: next executable price after trigger
stop_loss_or_invalidation: same as exit condition
data_dependencies: index OHLCV, resonance_day_low
timestamp_availability: index OHLCV available by evaluation time
```

This can be executable only if `resonance_day` is already defined upstream.

### Rejection criteria

Reject `executable_rule` classification if any of the following is true:

1. Core condition depends on unresolved terms such as `回暖`, `退潮`, `分歧`, `龙头`, `主线`, `弱转强`, `高潮`, `冰点`, `承接`.
2. Entry timing is missing.
3. Exit condition is missing.
4. Exit timing is missing.
5. Entry or exit price reference is missing.
6. Position sizing is missing or only says “轻仓”, “重仓”, “试错仓”, “娱乐仓” without numeric boundary.
7. Stop loss or invalidation is missing.
8. Required data is unavailable or undefined.
9. Timestamp availability is unclear.
10. The rule uses future knowledge, such as next-day strength, later confirmation, final board status, or later sector sustainability.
11. The action is only “select”, “observe”, “wait”, “avoid”, or “pay attention” without complete trade mechanics.
12. The output is primarily a market interpretation rather than a deterministic rule.

---

## 6.2 `rule_candidate`

### Definition

A `rule_candidate` is a near-rule. It has a clear trading-rule skeleton but lacks a small number of bounded, repairable fields.

It is not directly backtestable.

A `rule_candidate` should be used only when the missing pieces can plausibly be completed from:

1. source evidence,
2. explicit project convention,
3. bounded human review,
4. or a small parameter search that is clearly declared as research, not source fact.

### Minimum admission criteria

An item may be classified as `rule_candidate` only if:

1. the main idea is clearly a trading rule,
2. it has a concrete instrument universe or a recoverable one,
3. it has at least one deterministic entry or exit skeleton,
4. it is missing only a small number of bounded fields,
5. the missing fields are explicitly listed,
6. the missing fields can be repaired without inventing source meaning,
7. ambiguous terms are not the core of the rule, or can be replaced by source-grounded observable indicators,
8. no direct backtest is allowed before repair.

### Required minimum fields

| Field | Required | Description |
| --- | --- | --- |
| `primary_type` | Yes | Must be `rule_candidate` |
| `candidate_rule_summary` | Yes | Short description of the possible rule |
| `known_components` | Yes | Present rule fields |
| `missing_fields` | Yes | Bounded list of missing fields |
| `repair_source` | Yes | Source text, project convention, or human input |
| `repairability` | Yes | high / medium / low |
| `data_dependencies` | Yes | Known or probable datasets |
| `timestamp_availability_risk` | Yes | Known timestamp risks |
| `not_directly_backtestable` | Yes | Must be true |
| `source_evidence` | Yes | Article/span evidence |

### Admission example

Source meaning:

```text
Breakout is only valid when volume expands.
```

Possible classification:

```text
primary_type: rule_candidate
candidate_rule_summary: breakout with volume confirmation
known_components:
  - breakout condition exists
  - volume expansion is required
missing_fields:
  - exact volume expansion threshold
repair_source:
  - source text if threshold exists
  - project convention if explicitly defined
not_directly_backtestable: true
```

This is a `rule_candidate` only if the rest of the rule skeleton is concrete.

### Rejection criteria

Do not classify as `rule_candidate` if:

1. it is mostly semantic market language,
2. it only says “退潮期不要接高位” without defining retreat phase or high-position stock,
3. it is only a risk discipline,
4. it is only a data requirement,
5. it requires a new research design before becoming testable,
6. it needs many major fields invented,
7. it cannot identify entry, exit, or instrument universe,
8. it depends on unresolved subjective judgment.

---

## 6.3 `research_hypothesis`

### Definition

A `research_hypothesis` is a testable market claim derived from source experience.

It is not a trading rule. It cannot directly enter backtest or rule promotion.

It should be used when the source text expresses a market relationship, tendency, risk pattern, or behavioral claim that may be tested after defining observable variables.

### Required minimum fields

| Field | Required | Description |
| --- | --- | --- |
| `primary_type` | Yes | Must be `research_hypothesis` |
| `hypothesis_statement` | Yes | Testable claim |
| `source_experience` | Yes | Original experience text |
| `dependent_variables` | Yes | Outcomes to measure |
| `independent_variables` | Yes | Explanatory variables |
| `candidate_observable_indicators` | Yes | Possible measurable proxies |
| `required_data` | Yes | Data needed |
| `validation_method` | Yes | Event study, cross-sectional test, regression, grouped return study, etc. |
| `timestamp_availability_assumptions` | Yes | When variables are known |
| `not_directly_backtestable` | Yes | Must be true |
| `source_evidence` | Yes | Article/span evidence |

### Example

Original experience:

```text
退潮期不要接高位。
```

Incorrect extraction:

```text
primary_type: executable_rule
condition: market is in retreat phase and stock is high-position
action: avoid buying
```

Correct extraction:

```text
primary_type: research_hypothesis
source_experience: 退潮期不要接高位
hypothesis_statement: 当市场处于退潮阶段时，高位股次日回撤风险显著高于低位股或核心股。
dependent_variables:
  - next-day return
  - max drawdown
  - limit-down probability
  - failed-board probability
independent_variables:
  - market retreat phase indicator
  - stock height / board count / recent涨幅
candidate_observable_indicators:
  - limit-up/down breadth deterioration
  - red/green stock count deterioration
  - high-board failure rate
  - sector continuation rate
required_data:
  - OHLCV
  - limit-up/down statistics
  - market breadth
  - board height
  - sector classification
timestamp_availability_assumptions:
  - all independent variables must be known before entry decision
validation_method: grouped event study comparing high-position vs low-position stocks during retreat-like states
not_directly_backtestable: true
```

### Admission criteria

Classify as `research_hypothesis` when:

1. the source contains a directional or causal market claim,
2. the claim can be converted into measurable variables,
3. it lacks complete trade execution logic,
4. it requires research validation before becoming a rule,
5. it can produce future rule candidates only after validation.

### Rejection criteria

Do not classify as `research_hypothesis` if:

1. no measurable dependent variable can be defined,
2. no plausible observable indicators exist,
3. the text is pure motivational or philosophical commentary,
4. the claim is too vague to test,
5. it is already a complete executable rule.

---

## 6.4 `semantic_experience`

### Definition

A `semantic_experience` is trader language, market interpretation, cycle description, or subjective trading experience that is useful to preserve but not directly executable.

Examples:

```text
回暖
退潮
分歧
弱转强
主线
龙头
冰点
高潮
承接
赚钱效应
亏钱效应
强分歧
修复延续
超预期
预期差
混沌期
```

`semantic_experience` must not directly enter backtest.

It may feed:

1. semantic dictionary,
2. hypothesis generation,
3. indicator candidate generation,
4. human research review.

### Required minimum fields

| Field | Required | Description |
| --- | --- | --- |
| `primary_type` | Yes | Must be `semantic_experience` |
| `term_or_phrase` | Yes | Extracted semantic term |
| `source_context` | Yes | How the term was used |
| `plain_language_interpretation` | Yes | Meaning in normal language |
| `possible_observable_proxies` | Optional | Candidate indicators, if any |
| `related_market_state` | Optional | cycle, sentiment, liquidity, sector, breadth, etc. |
| `not_directly_backtestable` | Yes | Must be true |
| `source_evidence` | Yes | Article/span evidence |

### Example

Source expression:

```text
情绪开始回暖，可以低位试错。
```

Correct extraction:

```text
primary_type: semantic_experience
term_or_phrase: 情绪回暖
source_context: author describes a possible improvement in short-term market emotion
plain_language_interpretation: market participation and risk appetite may be improving
possible_observable_proxies:
  - red stock count increase
  - limit-up count increase
  - limit-down count decrease
  - failed-board rate decrease
  - previous-day limit-up performance improvement
not_directly_backtestable: true
```

### Admission criteria

Classify as `semantic_experience` when:

1. the source uses subjective market language,
2. the concept may be useful for human understanding,
3. the concept may later become a dictionary term or research hypothesis,
4. it does not contain complete execution logic.

### Rejection criteria

Do not classify as `semantic_experience` if:

1. the text is already a complete executable rule,
2. the text is a pure data requirement,
3. the text is a standalone risk-control instruction,
4. the text has no trading meaning.

---

## 6.5 `risk_control_hint`

### Definition

A `risk_control_hint` is a useful risk-management or discipline statement that affects future system design but is not a complete trading strategy.

Examples:

```text
退潮期降低仓位
连续亏损后暂停
高潮后不追高
弱市只低仓位试错
最猛退潮后只做一次低位试错
亏钱效应扩散时空仓
```

A `risk_control_hint` must not be promoted as a standalone executable rule unless it is later integrated into a complete strategy with defined entry, exit, sizing, and timestamp-safe market-state logic.

### Required minimum fields

| Field | Required | Description |
| --- | --- | --- |
| `primary_type` | Yes | Must be `risk_control_hint` |
| `risk_context` | Yes | When risk control applies |
| `risk_action` | Yes | Reduce, pause, avoid, cap, stop, etc. |
| `sizing_boundary` | Optional | Numeric boundary if present |
| `trigger_terms` | Yes | Terms that activate the hint |
| `missing_definitions` | Yes | Undefined terms or thresholds |
| `system_design_use` | Yes | How this may affect future design |
| `not_directly_backtestable` | Yes | Must be true |
| `source_evidence` | Yes | Article/span evidence |

### Example

Source expression:

```text
退潮期降低仓位。
```

Correct extraction:

```text
primary_type: risk_control_hint
risk_context: 退潮期
risk_action: lower position size
missing_definitions:
  - retreat phase definition
  - target position size
  - reset condition
system_design_use:
  - future portfolio-level risk throttle
  - future market-state dependent sizing module
not_directly_backtestable: true
```

### Admission criteria

Classify as `risk_control_hint` when:

1. the main meaning is risk reduction, exposure control, pause, avoidance, or discipline,
2. it does not define a full entry/exit strategy,
3. it can inform future portfolio or risk module design.

### Rejection criteria

Do not classify as `risk_control_hint` if:

1. it has no risk-management meaning,
2. it is actually a complete executable rule,
3. it is mainly a data requirement,
4. it is too vague to preserve.

---

## 6.6 `data_requirement_hint`

### Definition

A `data_requirement_hint` is an extracted need for data, feature, label, or timestamped market input.

It is not a rule and not a hypothesis.

Examples:

```text
kaipan_pre_market_bid
market_breadth
limit_up_down_stats
sector_fund_flow
sector_strength
auction_volume
market_cycle_label
yesterday_limit_up_performance
red_green_stock_count
failed_board_rate
sector_continuity
convertible_bond_mapping
```

### Required minimum fields

| Field | Required | Description |
| --- | --- | --- |
| `primary_type` | Yes | Must be `data_requirement_hint` |
| `data_name` | Yes | Name of required data or feature |
| `data_description` | Yes | What it means |
| `needed_by` | Optional | Rule, hypothesis, semantic term, or risk hint |
| `timestamp_requirement` | Yes | When the data must be available |
| `granularity` | Yes | tick, auction, daily, intraday, sector-level, market-level |
| `source_or_provider` | Optional | Known provider if any |
| `availability_status` | Yes | available / unavailable / unknown |
| `not_directly_backtestable` | Yes | Must be true |
| `source_evidence` | Yes | Article/span evidence |

### Example

Source expression:

```text
弱转强需要看竞价是否超预期。
```

Correct extraction:

```text
primary_type: data_requirement_hint
data_name: kaipan_pre_market_bid
data_description: pre-market auction bid/opening indication used to evaluate weak-to-strong behavior
needed_by:
  - semantic term: 弱转强
  - possible hypothesis: auction strength predicts continuation
timestamp_requirement: must be available before market open decision
granularity: auction / pre-market
availability_status: unknown
not_directly_backtestable: true
```

### Admission criteria

Classify as `data_requirement_hint` when:

1. the extracted content primarily identifies a needed dataset or feature,
2. execution cannot be evaluated without this data,
3. the data has timestamp or availability implications.

### Rejection criteria

Do not classify as `data_requirement_hint` if:

1. the text is primarily a trading rule,
2. the text is a risk discipline,
3. the text is pure semantic experience without identifiable data need,
4. the data need is hallucinated and unsupported by source text.

---

## 6.7 `unusable_noise`

### Definition

`unusable_noise` is content that should not enter rule, hypothesis, semantic, risk, or data lanes.

It may be discarded or retained only as source reference.

### Admission criteria

Classify as `unusable_noise` when the content is:

1. without trading meaning,
2. impossible to structure,
3. inconsistent with source text,
4. likely LLM hallucination,
5. overly abstract and cannot form a hypothesis,
6. duplicated without independent value,
7. contradictory without enough context,
8. motivational, promotional, or rhetorical only.

### Required minimum fields

| Field | Required | Description |
| --- | --- | --- |
| `primary_type` | Yes | Must be `unusable_noise` |
| `reason` | Yes | Why it is unusable |
| `source_evidence` | Optional | Required if retained |
| `retain_source_reference_only` | Yes | Usually true |

### Example

Source expression:

```text
理解力才是复利的本质。
```

Possible extraction:

```text
primary_type: unusable_noise
reason: motivational statement; no measurable hypothesis or trading operation
retain_source_reference_only: true
```

### Rejection criteria

Do not classify as `unusable_noise` if:

1. the text can become a research hypothesis,
2. the text preserves useful semantic trading language,
3. the text identifies a data requirement,
4. the text is a risk-control hint.

---

## 7. Handling Ambiguous Terms

Ambiguous terms are not automatically bad. They are bad only when the extractor pretends they are executable.

The new system should handle them as follows:

| Term type | Example | Correct treatment |
| --- | --- | --- |
| Market cycle | `退潮`, `冰点`, `回暖` | `semantic_experience` or `research_hypothesis` |
| Strength ranking | `龙头`, `最强`, `主线` | semantic dictionary / hypothesis / data requirement |
| Behavior pattern | `弱转强`, `承接`, `超预期` | semantic experience + data requirement |
| Sentiment state | `分歧`, `修复`, `高潮` | semantic experience / hypothesis |
| Risk language | `低仓位`, `娱乐仓`, `不追高` | risk control hint |

A rule may use these terms only after they are converted into timestamp-safe observable indicators.

---

## 8. Backtest and Promotion Policy

### 8.1 Direct backtest allowed

Only:

```text
executable_rule
```

Conditions:

1. all strict fields are present,
2. timestamp availability passes,
3. no unresolved core ambiguous terms,
4. data dependencies are available or explicitly simulated in a safe way,
5. lookahead check passes.

### 8.2 Repair before backtest

Only:

```text
rule_candidate
```

A `rule_candidate` must first become `executable_rule` through a repair workflow.

Repair must record:

1. what was missing,
2. who or what supplied it,
3. whether it came from source text, project convention, or human input,
4. whether parameter search was used,
5. whether the repaired version is still source-faithful.

### 8.3 Research validation before possible rule creation

Only:

```text
research_hypothesis
```

A hypothesis may produce future rule candidates only after validation.

It must not be directly backtested as a strategy.

### 8.4 Never directly backtest

The following types must not directly enter strategy backtest:

```text
semantic_experience
risk_control_hint
data_requirement_hint
unusable_noise
```

---

## 9. Human Review Policy

| Output type | Review policy |
| --- | --- |
| `executable_rule` | Review optional but recommended for early rollout; sample review after confidence improves |
| `rule_candidate` | Review required before repair/promotion |
| `research_hypothesis` | Research review required before validation work |
| `semantic_experience` | Optional review for dictionary quality |
| `risk_control_hint` | Optional review by risk/system design owner |
| `data_requirement_hint` | Review by data/platform owner |
| `unusable_noise` | No review unless debugging extractor quality |

Human review should not be used as a dumping ground for every fuzzy extraction. The taxonomy should route fuzzy content to the correct non-rule lane first.

---

## 10. Migration From Old `rule_candidates`

### 10.1 Migration principle

The existing 488 `rule_candidates` should be treated as audit evidence and reclassification input.

They should not be deleted.

They should not be mass-promoted.

They should not be mass-backtested.

They should be mapped into the new taxonomy through a read-only reclassification pass first.

### 10.2 Suggested old-to-new mapping

| Existing signal | Likely new type |
| --- | --- |
| `backtestability_status = executable` with complete entry/exit/risk/timing/data | `executable_rule` |
| `backtestability_status = executable` but action is only select/observe/avoid | `research_hypothesis` or `risk_control_hint` |
| `partially_executable` with one narrow missing parameter | `rule_candidate` |
| `partially_executable` with core ambiguous terms | `semantic_experience` |
| `partially_executable` with market relationship claim | `research_hypothesis` |
| `partially_executable` with risk action only | `risk_control_hint` |
| any row dominated by Kaipan/sector/breadth/cycle data need | `data_requirement_hint` |
| `not_executable` but useful market claim | `research_hypothesis` or `semantic_experience` |
| `not_executable` with no useful structure | `unusable_noise` |

### 10.3 Expected reclassification shape

Based on Step 1 audit estimates:

| New type | Expected share |
| --- | ---: |
| `executable_rule` | 4-7% |
| `rule_candidate` | 1-3% |
| `research_hypothesis` | 10-15% |
| `semantic_experience` | 60-75% |
| `risk_control_hint` | 5-8% |
| `data_requirement_hint` | 3-6% |
| `unusable_noise` | 2-4% |

These are starting estimates, not final labels.

A human-labeled gold sample is required before using these as model-quality metrics.

---

## 11. Preserve Old Data as Audit Evidence

The old extracted rows should be preserved because they provide:

1. evidence of the previous extraction failure mode,
2. representative examples for taxonomy design,
3. regression data for future extractor comparison,
4. source-linked samples for human labeling,
5. migration evidence if the project continues in `trade-strategy-ai`.

Recommended policy:

```text
Do not delete old rule_candidates.
Do not overwrite old canonical_payload.
Do not silently mutate old backtestability_status.
Create a separate reclassification output when implementation begins.
Preserve source article, prompt run, candidate ID, and original payload.
```

---

## 12. Human-Labeled Gold Sample

A small human-labeled gold sample should be built before full implementation.

### 12.1 Purpose

The gold sample should answer:

1. Can humans consistently distinguish the seven output types?
2. Are the definitions too strict or too loose?
3. Does the taxonomy reduce false `rule_candidate` outputs?
4. Does it preserve useful semantic experience instead of discarding it?
5. Does it identify research hypotheses and data requirements cleanly?

### 12.2 Suggested sample size

Start with:

```text
50-80 old candidates from the existing 488
```

Sampling should include:

1. persisted `executable`,
2. persisted `partially_executable`,
3. persisted `not_executable`,
4. derived `pending_backtest`,
5. derived `needs_human_review`,
6. derived `suggested_reject`,
7. high-frequency ambiguous terms,
8. high-frequency missing fields,
9. Kaipan/data-heavy rows,
10. risk/sizing rows.

### 12.3 Minimum label fields

Each labeled sample should include:

| Field | Description |
| --- | --- |
| `old_candidate_id` | Existing candidate ID |
| `source_article_id` | Existing article ID |
| `old_status` | Existing backtestability/review status |
| `new_primary_type` | One of seven taxonomy types |
| `secondary_tags` | Optional |
| `label_rationale` | Why this label was chosen |
| `backtest_allowed` | Yes/no |
| `promotion_allowed` | Yes/no |
| `needs_human_review` | Yes/no |
| `missing_contract_fields` | If any |
| `lookahead_or_timestamp_risk` | If any |

---

## 13. Small-Sample Re-Extraction Validation

Before implementation, run the redesigned taxonomy on 10-20 representative articles.

The goal is not to maximize `executable_rule` count. The goal is to classify outputs correctly.

### 13.1 Article coverage

The validation set should cover:

1. 情绪周期类文章
2. 弱转强类文章
3. 龙头 / 主线类文章
4. 退潮 / 冰点类文章
5. 放量 / 共振类文章
6. 风控纪律类文章
7. 纯市场复盘类文章

### 13.2 Validation questions

For each article, evaluate:

1. Did the extractor avoid forcing fuzzy language into `rule_candidate`?
2. Did true executable rules remain extractable?
3. Were semantic terms preserved?
4. Were hypotheses separated from rules?
5. Were risk hints separated from strategies?
6. Were data requirements explicitly captured?
7. Were timestamp and lookahead risks surfaced?
8. Did the output remain source-faithful?

### 13.3 Pass criteria

The small-sample validation passes only if:

1. `executable_rule` outputs satisfy the strict contract.
2. No `semantic_experience` enters direct backtest.
3. No `research_hypothesis` enters direct backtest.
4. No `risk_control_hint` is treated as a full strategy.
5. No `data_requirement_hint` is treated as a rule.
6. `rule_candidate` contains only bounded, repairable gaps.
7. All output items include source evidence.
8. Timestamp availability is declared for every rule and hypothesis.
9. Lookahead risks are explicitly flagged.
10. Human review load is reduced by correct routing, not by weaker standards.

### 13.4 Failure criteria

The validation fails if any of the following happens:

1. fuzzy terms are again wrapped into condition/action fields as executable rules,
2. most outputs still become `rule_candidate`,
3. risk hints are promoted as strategies,
4. data requirements are hidden inside rule fields,
5. hypotheses are directly backtested,
6. source evidence is missing,
7. timestamp availability is not captured,
8. output categories are inconsistent across similar articles.

---

## 14. Decision After Validation

After the taxonomy is validated on the small sample, choose one of the following routes.

### A. Continue inside `trade-strategy-ai`

Choose this if:

1. existing schema/service boundaries can be adapted cleanly,
2. old data can be preserved as audit evidence,
3. new taxonomy can be implemented without excessive compatibility hacks,
4. backtest and rule promotion can be guarded by type.

### B. New hypothesis-first project

Choose this if:

1. current project structure forces everything through rule/backtest lanes,
2. implementing the taxonomy creates too many legacy compatibility patches,
3. hypothesis and semantic research become the primary product direction,
4. clean architecture is cheaper than retrofitting.

### C. Keep `trade-strategy-ai` as data and backtest reference

Choose this if:

1. the current project is useful as evidence, database, crawler, and backtest harness,
2. new extraction should be prototyped outside the main project,
3. old implementation should not be expanded until taxonomy quality is proven.

### D. Redesign extraction prompt/runtime first

Choose this if:

1. the taxonomy is accepted,
2. implementation impact is unclear,
3. current prompts still force rule-shaped outputs,
4. small-sample extraction cannot be judged until prompt/runtime output shape changes.

Recommended immediate route after this document:

```text
Do Codex impact audit first.
Do not implement schema or migration yet.
Do not continue old rule promotion path yet.
Do not decide new project yet.
```

---

## 15. Implementation Impact Areas To Audit Later

A later impact audit should inspect how this taxonomy affects:

1. database schema,
2. SQLAlchemy models,
3. Pydantic schemas,
4. extraction prompts,
5. prompt runtime output parsing,
6. review policy,
7. backtest eligibility,
8. rule promotion,
9. job workflow,
10. article UI,
11. rule pool UI,
12. research/hypothesis UI,
13. data requirement tracking,
14. audit evidence preservation,
15. migration strategy for existing 488 candidates.

No code changes should be made until this impact report exists.

---

## 16. Non-Goals

This document does not:

1. write code,
2. modify GitHub beyond saving this design document,
3. create migrations,
4. change database tables,
5. reclassify all 488 rows,
6. decide to start a new project,
7. continue the old extraction -> review -> backtest route,
8. relax manual review,
9. lower backtest eligibility,
10. force more candidates into backtest.

---

## 17. Follow-Up Codex Impact Audit Prompt

Use this prompt in Codex after this document is accepted.

```text
# Extraction Taxonomy Redesign Impact Audit

Repo: xiyuxifeng/Trade
Project: trade-strategy-ai

Task:
Read docs/extraction-taxonomy-redesign.md and inspect the current trade-strategy-ai codebase to produce an implementation impact report.

Do not implement code.
Do not modify files except the final report.
Do not create migrations.
Do not change schema.
Do not change prompts.
Do not change services.
Do not change UI.
Do not reclassify production data.

Required reading:
1. docs/extraction-taxonomy-redesign.md
2. docs/rule-extraction-output-audit.md
3. trade-strategy-ai/prompts/article_analysis_v1.md
4. trade-strategy-ai/src/models/stage2_canonical.py
5. trade-strategy-ai/src/rule_pool/models.py
6. trade-strategy-ai/src/rule_pool/schemas.py
7. trade-strategy-ai/src/models/rule_applicability.py
8. trade-strategy-ai/src/models/article_metadata.py
9. trade-strategy-ai/src/services/article_review_policy.py
10. trade-strategy-ai/config/settings.py
11. trade-strategy-ai/config/database.py
12. trade-strategy-ai/src/db/session.py
13. Any current extraction, rule promotion, backtest eligibility, article review, job, and UI files that depend on rule_candidates.

Audit goals:
1. Identify every schema/model/service/prompt/review policy/database/job/UI area affected by the new taxonomy.
2. Identify where the current system assumes every extracted output is a rule_candidate.
3. Identify where backtest eligibility currently depends on old fields such as backtestability_status, review_state, quality_status, missing_fields, ambiguous_terms, or canonical_payload.
4. Identify where rule promotion assumes rule_candidate as the only upstream extraction type.
5. Identify where semantic experience, research hypothesis, risk hint, and data requirement would need separate storage or routing.
6. Identify whether existing tables can be extended safely or whether new tables are cleaner.
7. Identify migration options for the existing 488 rule_candidates while preserving audit evidence.
8. Identify UI impact for article extraction review, rule pool, backtest, research review, semantic dictionary, and data requirement backlog.
9. Identify job/workflow impact for extraction, re-extraction, reclassification, review, validation, and backtest.
10. Identify risks of continuing inside trade-strategy-ai versus creating a new hypothesis-first project.

Output:
Create a report at:

docs/extraction-taxonomy-implementation-impact-report.md

Report structure:
1. Executive summary
2. Current assumptions that conflict with the new taxonomy
3. Affected database tables and models
4. Affected Pydantic schemas and API contracts
5. Affected extraction prompts and runtime parsing
6. Affected review policy and human review queues
7. Affected backtest eligibility and rule promotion
8. Affected jobs and workflow orchestration
9. Affected UI pages and user flows
10. Existing 488 rule_candidates migration options
11. Options analysis:
   A. implement inside trade-strategy-ai
   B. build new hypothesis-first project
   C. keep trade-strategy-ai as data/backtest reference
   D. redesign extraction prompt/runtime first
12. Recommended implementation sequence
13. Risks and blockers
14. Open questions requiring user decision

Acceptance criteria:
1. No code changes.
2. No migrations.
3. No prompt changes.
4. No UI changes.
5. The report cites concrete files and current assumptions.
6. The report clearly separates must-change, should-change, and optional-change areas.
7. The report recommends the smallest safe next step after taxonomy design.
8. The report does not recommend forcing fuzzy outputs into backtest.
9. The report preserves the audit conclusion that executable_rule is a narrow type, not the default extraction target.
```

---

## 18. Recommended Next Step

After this document is accepted:

1. run the Codex impact audit prompt,
2. review the generated impact report,
3. then decide whether Step 3 should be:
   - prompt/runtime redesign,
   - schema design,
   - small-sample re-extraction,
   - human-labeled gold sample,
   - or project route decision.

Do not proceed to implementation before the impact audit.
