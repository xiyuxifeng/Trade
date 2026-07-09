# Rule Extraction Output Audit

Date: 2026-07-09

## Decision Summary

Recommendation: **D. Redesign extraction before either path.**

Confidence level: **High for the direction decision, medium for exact semantic-category proportions.**

Reason: the live database contains 488 extracted `rule_candidates`, but 0 promoted `rule_versions`. The candidate layer is dominated by fuzzy market-language outputs rather than executable trading rules. The current queue is therefore not mainly a software-fix backlog; it is an extraction/classification problem.

Do not continue by loosening eligibility. Do not add a Research/Hypothesis layer as a patch on top of the current extractor output shape. First redesign extraction so it explicitly separates executable rules, rule candidates, research hypotheses, semantic experience, risk hints, and data requirements.

## Sampling Method

Primary source of truth: live local PostgreSQL database `trade_strategy_ai`.

Read-only methods used:

```sql
SELECT current_database(), count(*) AS rule_candidates
FROM rule_candidates;

SELECT backtestability_status, review_state, quality_status, count(*)
FROM rule_candidates
GROUP BY 1,2,3
ORDER BY 1,2,3;

SELECT count(*) AS rule_versions, count(source_candidate_id) AS linked_to_candidate
FROM rule_versions;

SELECT canonical_payload->'quantification'->>'status' AS quant_status,
       backtestability_status,
       count(*)
FROM rule_candidates
GROUP BY 1,2
ORDER BY 1,2;

SELECT COUNT(*) FILTER (WHERE canonical_payload->'quantification'->'ambiguous_terms' <> '[]'::jsonb) AS with_ambiguous,
       COUNT(*) FILTER (WHERE canonical_payload->'quantification'->'missing_fields' <> '[]'::jsonb) AS with_missing,
       COUNT(*) FILTER (WHERE canonical_payload->>'condition' IS NULL OR canonical_payload->'condition' = '{}'::jsonb) AS no_condition,
       COUNT(*) FILTER (WHERE canonical_payload->>'action' IS NULL OR canonical_payload->'action' = '{}'::jsonb) AS no_action,
       COUNT(*) FILTER (WHERE lower(data_dependencies::text) LIKE '%kaipan%') AS kaipan_dependency
FROM rule_candidates;
```

I also ran the existing read-only automatic review classifier from `src/services/article_review_policy.py` against stored `RuleCandidate` rows joined to `blog_articles` to reproduce derived queue statuses:

- `pending_backtest`
- `needs_human_review`
- `suggested_reject`

Sampling was stratified across:

- Persisted `backtestability_status`: `executable`, `partially_executable`, `not_executable`
- Derived review status: `pending_backtest`, `needs_human_review`, `suggested_reject`
- Rule types: `entry`, `exit`, `filter`, `risk`, `selection`, `sizing`
- Representative high-frequency ambiguous/missing-field patterns

The category proportions below are estimates from the inspected database population, the complete status counts, the automatic-review distribution, the high-frequency blockers, and representative samples. They are not a substitute for a full row-by-row human label pass.

## Required Reading Inspected

- `AGENTS.md`
- `trade-strategy-ai/docs/review/2026-07-09-stage3-human-review-triage.md`
- `trade-strategy-ai/prompts/article_analysis_v1.md`
- `trade-strategy-ai/docs/superpowers/specs/2026-07-08-article-review-relaxation-strategy-design.md`
- `trade-strategy-ai/src/models/stage2_canonical.py`
- `trade-strategy-ai/src/rule_pool/models.py`
- `trade-strategy-ai/src/rule_pool/schemas.py`
- `trade-strategy-ai/src/models/rule_applicability.py`
- `trade-strategy-ai/src/models/article_metadata.py`
- `trade-strategy-ai/src/services/article_review_policy.py`
- `trade-strategy-ai/config/settings.py`
- `trade-strategy-ai/config/database.py`
- `trade-strategy-ai/src/db/session.py`

## Database Tables And Models Inspected

Primary extracted-rule tables:

| Table/model | Finding |
| --- | --- |
| `rule_candidates` / `RuleCandidate` | Primary extracted output. Stores `canonical_payload`, `evidence_json`, `missing_fields`, `data_dependencies`, `backtestability_status`, `review_state`, `quality_status`. |
| `blog_articles` / `BlogArticle` | Source title, URL, author, content linkage. Used to ground examples. |
| `article_structures` / `ArticleStructure` | Prompt-derived article structure parent for candidates. |
| `prompt_runs` / `PromptRun` | Prompt execution record and raw outputs. |
| `rule_versions` / `RuleVersion` | Formal rule version target. Count is 0 in inspected DB. |
| `rule_version_source_links` | Formal source link table. No linked rows because no `rule_versions`. |
| `rules`, `rule_families`, `rule_family_memberships` | Formal governance layer. No evidence of promoted extracted candidates. |
| `rule_applicability_profiles` | Backtest/applicability profile layer. Not populated from extracted candidates in this inspected path. |
| `rule_pool` | Legacy/earlier rule pool model. Relevant historically, but `RuleCandidate` is the current extracted-output table for this audit. |

## Database Snapshot

Live database access succeeded.

Database: `trade_strategy_ai`

Total candidates:

| Metric | Count |
| --- | ---: |
| `rule_candidates` | 488 |
| `rule_versions` | 0 |
| `rule_versions.linked_to_candidate` | 0 |

Persisted candidate statuses:

| `backtestability_status` | `review_state` | `quality_status` | Count |
| --- | --- | --- | ---: |
| `executable` | `extracted` | `partial` | 34 |
| `partially_executable` | `extracted` | `partial` | 441 |
| `not_executable` | `extracted` | `partial` | 13 |

Derived automatic review statuses from current policy:

| Derived status | Count | Share |
| --- | ---: | ---: |
| `pending_backtest` | 40 | 8.2% |
| `needs_human_review` | 435 | 89.1% |
| `suggested_reject` | 13 | 2.7% |

Payload-level blockers:

| Metric | Count | Share |
| --- | ---: | ---: |
| Candidates with `ambiguous_terms` | 455 | 93.2% |
| Candidates with `missing_fields` | 188 | 38.5% |
| Candidates with no condition | 0 | 0.0% |
| Candidates with no action | 0 | 0.0% |
| Candidates with Kaipan dependency | 32 | 6.6% |

Important implication: the extractor usually produces a syntactic condition and action, but the semantic content is often not executable.

## Classification Criteria

| Category | Criteria |
| --- | --- |
| `executable_rule` | Has concrete condition, action, timing/price reference, parameters, data source, and no core ambiguous term controlling execution. |
| `rule_candidate` | Has useful rule skeleton, but needs bounded parameter repair, symbol universe definition, or minor field completion before formal backtest. |
| `research_hypothesis` | Expresses a testable market idea, but needs a new hypothesis/spec formulation before it can become a rule. |
| `semantic_experience` | Encodes trader language, market feel, cycle interpretation, or subjective state such as 回暖, 退潮, 分歧, 弱转强, 主线, 高潮, 冰点. |
| `risk_control_hint` | Useful position/risk guidance but not a standalone entry/exit rule. |
| `data_requirement_hint` | Mainly exposes missing data source/feature requirements, such as Kaipan auction data, market sentiment, sector flow, limit-up/down stats. |
| `unusable_noise` | Too vague, contradictory, or non-operational to preserve except as source text. |

## Classification Results

Estimated category proportions over the 488 stored candidates:

| Category | Estimated share | Estimated count | Evidence basis |
| --- | ---: | ---: | --- |
| `executable_rule` | 4-7% | 20-35 | 34 persisted `executable`; several are still questionable due domain semantics or custom data. |
| `rule_candidate` | 1-3% | 5-15 | Existing triage found only 4 clearly recoverable human-edit cases in `needs_human_review`; some pending-backtest partials may also fit. |
| `research_hypothesis` | 10-15% | 49-73 | Market breadth, liquidity, resonance, and cycle claims can be reformulated into testable studies. |
| `semantic_experience` | 60-75% | 293-366 | 455/488 have ambiguous terms; high-frequency terms are mostly subjective market semantics. |
| `risk_control_hint` | 5-8% | 24-39 | Sizing/risk outputs with advice like reduce, avoid, position limit, but without full executable context. |
| `data_requirement_hint` | 3-6% | 15-29 | Kaipan, market sentiment, sector flow, auction, limit-up/down, and breadth dependencies dominate some outputs. |
| `unusable_noise` | 2-4% | 10-20 | 13 persisted `not_executable`, plus some non-operational partials. |

These categories are not mutually exclusive at the semantic level. For project direction, the key fact is that likely executable or near-executable rules are a small minority.

## Representative Examples From Stored Records

### Executable Or Near-Executable

`b0379061-a73f-489c-8bca-b93f4572368f`

- Title: `教你什么是短线“确定性”小资金做大的秘密！淘县九年义务教育！`
- URL: `https://www.tgb.cn/a/2gOFSgwjnLF`
- Stored status: `executable`
- Derived status: `pending_backtest`
- Condition: red stocks count <= 1000 or limit-up count decreases for 2 consecutive days.
- Action: select / wait for emotion repair.
- Classification: `research_hypothesis` or weak `executable_rule`.
- Reason: breadth metrics are concrete, but action is not a complete buy/sell rule.

`9ba650ef-3722-4455-a3fc-b523020bdbcb`

- Title: `[红包]教你什么是短线“共振”淘县九年义务教育`
- URL: `https://www.tgb.cn/a/2j3QPunumuA`
- Stored status: `executable`
- Derived status: `pending_backtest`
- Condition: volume increase >= 20% and index change >= 1%.
- Action: select.
- Classification: `research_hypothesis`.
- Reason: the numeric condition is testable, but the action remains selection/filter, not complete execution.

`5b56a870-f864-4563-a69f-810351071aea`

- Title: `[红包]教你什么是短线“共振”淘县九年义务教育`
- URL: `https://www.tgb.cn/a/2j3QPunumuA`
- Stored status: `executable`
- Derived status: `pending_backtest`
- Condition: index breaks below the low of resonance day.
- Action: sell / exit.
- Classification: `executable_rule`.
- Reason: exit condition and action are concrete enough if resonance day is defined upstream.

`1e03e61c-9e82-4297-b912-86c65e884516`

- Title: `短线利刃~从实战角度教你可转债的理解与运用~淘县九年义务教学！`
- URL: `https://www.tgb.cn/a/2em0ApstXrg`
- Stored status: `executable`
- Derived status: `pending_backtest`
- Condition: stocks with convertible bonds and limit-up main stock.
- Action: avoid.
- Classification: `risk_control_hint`.
- Reason: actionable as a filter/risk constraint, not a standalone trading strategy.

### Recoverable Rule Candidates

These are consistent with the existing triage document and were checked against stored candidate IDs.

`4836617e-adba-4938-81b5-8e4b00193bec`

- Title: `预判周期，定性指数反转！用理解力全程在公开区带队周赚50多个点，每周总结贴来了！`
- URL: `https://www.tgb.cn/a/2bUOBkkM5UI`
- Stored status: `partially_executable`
- Gap: `volume_threshold`
- Classification: `rule_candidate`
- Reason: if the volume threshold is grounded in source text or a formal project convention, it can become testable.

`23ca2407-9891-4acc-97e7-0aeb7031f3c3`

- Title: `11.13号复盘，监管和指数巨幅缩量的双重影响下，明天怎么看？`
- URL: `https://www.tgb.cn/a/2d9Jrv1tsWY`
- Stored status: `partially_executable`
- Gap: `volume_threshold`
- Classification: `rule_candidate`
- Reason: narrow missing quantitative boundary, not a wholesale semantic failure.

`358282ea-c84f-4fb0-bfb7-d0a85a24a6ef`

- Title: `1.2号复盘，指数开年绿的令人发慌！明天怎么看！！附交易思路！`
- URL: `https://www.tgb.cn/a/2evp7ztApP9`
- Stored status: `partially_executable`
- Gap: `具体触发条件`
- Classification: `rule_candidate`
- Reason: potentially repairable only if source evidence supports a concrete trigger.

### Semantic Experience Dominant Cases

`e52acdc7-7b1e-40a1-bf64-59e772d2f676`

- Title: `教你什么是短线“确定性”小资金做大的秘密！淘县九年义务教育！`
- URL: `https://www.tgb.cn/a/2gOFSgwjnLF`
- Stored status: `partially_executable`
- Derived status: `needs_human_review`
- Ambiguous terms: `低位试错`, `最猛的那波退潮杀跌已经结束`
- Risk control: low-position trial only once, stop and wait for repair.
- Classification: `semantic_experience` plus `risk_control_hint`.
- Reason: execution depends on subjective cycle/repair judgment.

`7d3e040a-9d08-45c6-8df7-271e80dc3995`

- Title: `教你什么是短线“确定性”小资金做大的秘密！淘县九年义务教育！`
- URL: `https://www.tgb.cn/a/2gOFSgwjnLF`
- Stored status: `partially_executable`
- Derived status: `needs_human_review`
- Ambiguous terms: `情绪的分歧延续`, `情绪的修复延续`, `强势混沌`
- Classification: `semantic_experience`.
- Reason: core condition and exit depend on subjective market emotion states.

`47fbfc6d-5f86-449d-8a81-55da78b81488`

- Title: `10.22号复盘，情绪带指数，当情绪出现拐点信号的时候我们该如何思考？`
- URL: `https://www.tgb.cn/a/2czcsC35ha8`
- Stored status: `partially_executable`
- Derived status: `needs_human_review`
- Missing fields: `强分歧的量化标准`, `低吸的具体位置`
- Ambiguous terms: `强分歧`, `低吸`
- Classification: `semantic_experience` or `research_hypothesis`.
- Reason: can become a research question, but is not an executable rule.

`ac562719-87eb-4b6b-a864-ce72d44ea039`

- Title: `短线超预期（弱转强）的理解与实战运用，淘县九年义务教育`
- URL: `https://www.tgb.cn/a/2fGZV5bpnQD`
- Stored status: `partially_executable`
- Derived status: `needs_human_review`
- Ambiguous terms: `大高开`, `赚钱效应的修复`, `同预期竞争对手`, `最强`
- Data dependency: `kaipan_pre_market_bid`
- Classification: `semantic_experience` plus `data_requirement_hint`.
- Reason: needs auction data and subjective competitive-strength definition.

### Suggested Reject / Non-Executable

`e720b0de-0de8-4fa7-8911-e94c28039a69`

- Title: `周总结贴！用游资视野教你如何去复盘！如何复盘！淘县九年义务教学课程`
- URL: `https://www.tgb.cn/a/2cikVDS5Bk8`
- Stored status: `not_executable`
- Derived status: `suggested_reject`
- Missing fields: trend-up definition, concrete trading action.
- Ambiguous terms: `行情是向上的`, `低开高走`, `高开低走`
- Classification: `research_hypothesis` or `unusable_noise`.
- Reason: macro/market narrative without a bounded rule.

`7a408ed8-72cb-4cfb-8bef-18586f617b27`

- Title: `10.17号复盘！混沌期出现分歧？是不是要变盘了？我们该如何应对？`
- URL: `https://www.tgb.cn/a/2cqMfR8nxzv`
- Stored status: `not_executable`
- Derived status: `suggested_reject`
- Ambiguous terms: `混沌期`, `分歧`, `预期差`
- Classification: `semantic_experience`.
- Reason: the output is a trading interpretation, not a backtestable input.

`62f40fea-aa09-4cc6-82d2-6f7ec37d43fe`

- Title: `复利的本质~选择大于努力！`
- URL: `https://www.tgb.cn/a/2r48EB1kcRU`
- Stored status: `not_executable`
- Derived status: `suggested_reject`
- Missing fields: concrete position ratio, quant definition of one-sided decline.
- Ambiguous terms: `单边下跌`, `确定性`, `娱乐仓`, `盲目重仓`
- Classification: `risk_control_hint` or `semantic_experience`.
- Reason: useful discipline, not executable rule logic.

## Common Failure Modes

1. Ambiguous market terms are core logic, not decoration.

High-frequency terms from stored records include:

- `分歧延续` 18
- `水下` 10
- `强分歧` 9
- `分歧` 8
- `修复延续` 8
- `符合预期` 8
- `放量` 7
- `高位` 7
- `超预期` 7
- `弱转强` 5
- `退潮期` 5
- `冰点` 3

2. Missing entry/exit timing and price references are common.

Frequent missing fields include:

- `仓位` 11
- `止损条件` 10
- `具体入场价格` 7
- `买入时机` 6
- `具体买入时机` 5
- `volume_threshold` 3
- `entry_price` 3
- `exit_price` 3
- `position_sizing` 3

3. Conditions and actions are present syntactically but often not semantically executable.

The DB reports 0 candidates with missing condition/action, but most conditions contain custom fields like market state, sentiment, repair, divergence, strength, core popularity, or cycle phase.

4. Data-source assumptions are under-specified.

Examples include `kaipan_pre_market_bid`, `market_sentiment`, `sector_fund_flow`, `short-term sentiment indicators`, `龙虎榜数据`, `limit_up_down_stats`, `market_breadth`, and `market_cycle`.

5. Future-function and lookahead risks are real.

Many outputs use language such as next-day repair probability, strongest competitor, board continuity, or whether a sector "has sustainability". Without strict timestamp/data-availability contracts, backtests can accidentally use future knowledge.

6. LLM misclassification risk is structural.

The extractor often turns an educational statement or market narrative into a candidate rule because it can fill `condition` and `action` fields. This creates false confidence: the row looks structured, but the content remains subjective.

7. Duplicate and conflicting themes recur.

Multiple candidates are extracted from the same article and repeat similar concepts such as emotion repair/divergence, cycle stage, resonance, weak-to-strong, low-position trial, and sector core selection. They are not deduplicated into stable rule families because no `rule_versions` or `rule_families` are populated.

8. Backtest blockage is usually "not actually a rule".

The dominant blocker is not missing one parameter. Most candidates need reclassification as experience/hypothesis/hint before they can be safely used.

## Discovered Data Requirements

The extraction outputs imply these data contracts, none of which should be silently assumed:

- Market breadth: red/green stock counts, limit-up count, limit-down count, consecutive changes.
- OHLCV and index features: daily bars, moving averages, volume change, index return, box high/low, resonance-day low.
- Auction/Kaipan data: pre-market bid, auction volume, order-book style panic/absorption signals.
- Sector data: sector ranking, sector fund flow, sector strength, sector continuity, sector rotation.
- Sentiment/cycle labels: market cycle, mixed phase, retreat phase, repair phase, emotion divergence, emotion repair.
- Instrument metadata: convertible bond mapping, limit-up status, stock-sector membership.
- Risk metadata: position sizing base, stop-loss definition, take-profit definition, max loss boundary.

These requirements should become explicit extraction outputs or blockers. They should not be implied by terms like `主线`, `龙头`, `退潮`, `弱转强`, or `承接`.

## Route Recommendation

Recommended route: **D. Redesign extraction before either path.**

Why not A, continue with targeted fixes:

- Only 34/488 are persisted as `executable`.
- Only 40/488 enter derived `pending_backtest`.
- 0 rows have reached `rule_versions`.
- Most blocked rows are semantically not rules, so targeted code fixes would optimize the wrong layer.

Why not B immediately, add Research/Hypothesis Layer first:

- A research layer is likely needed, but adding it before extraction redesign risks dumping all fuzzy outputs into a new bucket without improving quality.
- The extractor must first label whether a text span is a rule, hypothesis, experience, risk hint, data requirement, or noise.

Why not C, freeze and start a clean new project:

- The database, schema, and review evidence are useful. The failure is not only legacy code; it is the extraction contract.
- Starting clean without redesigning the extraction ontology would reproduce the same fuzzy-rule problem.

What D means:

- Redefine extraction output types before formal rule promotion.
- Make "executable trading rule" a narrow type, not the default target.
- Preserve semantic experience and hypotheses in separate, non-backtestable lanes.
- Require data dependency declarations and timestamp availability for any rule/hypothesis.
- Keep current `trade-strategy-ai` as evidence and evaluation harness while redesigning extraction.

## Risks

- Exact semantic proportions require a full human labeling pass. The current estimates are enough for project-direction choice, not for model evaluation metrics.
- Some `pending_backtest` records may still be overclassified as executable because selection/filter actions are not complete strategy actions.
- Some `semantic_experience` rows may be transformable into hypotheses, but not without a new intermediate ontology and explicit data contracts.
- Current `review_state = extracted` for all candidates means manual review lifecycle is not persisted in the inspected rows; derived statuses come from current policy code.
- No formal `rule_versions` exist, so the audit cannot evaluate end-to-end backtest promotion quality.

## Follow-Up Tasks

1. Design a new extraction taxonomy with mutually exclusive top-level output types.
2. Add a strict executable-rule contract requiring entry, exit, risk, timing, instrument universe, data dependencies, and timestamp availability.
3. Add a hypothesis contract separate from executable rules.
4. Add semantic-experience and risk-hint storage contracts that are explicitly non-backtestable.
5. Re-run extraction on a small representative article set and compare category distribution before touching production eligibility.
6. Build a human-labeled gold sample from the 488 existing candidates.
7. Only after the taxonomy is validated, decide whether the implementation continues in `trade-strategy-ai` or moves into a clean project.

## Final Decision

The stored outputs are sufficient to decide direction.

Status: **ACCEPTED**

Recommendation: **D. Redesign extraction before either path.**

Confidence: **High** that continuing with targeted fixes or eligibility loosening is the wrong next move. **Medium** on exact category percentages until a full human labeling pass is completed.
