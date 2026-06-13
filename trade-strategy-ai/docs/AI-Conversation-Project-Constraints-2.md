# Trade Strategy AI 项目专用 Prompt 约束库（二）

### 11.8 数据时间语义与调度

```text
Data and scheduling constraints:
- Preserve trade_date, available_at, captured_at, effective_at, source, and slot.
- Separate pre-market and post-market Kaipan data.
- Backfill and daily incremental update are independently testable.
- Tasks are idempotent, resumable, and retryable.
- Missing data remains unavailable, not false or zero.
- Backtests do not call live Providers during execution.
```

### 11.9 回测安全

```text
Backtest safety constraints:
- Bind every run to DatasetSnapshot, rule version, market-state model version,
  and code version.
- Prevent future-data leakage and live Provider calls.
- Separate Level 1 OHLCV, Level 2 OHLCV + market state, and Level 3 including
  Kaipan.
- Missing Kaipan is a coverage limitation.
- Mark insufficient_sample instead of producing strong conclusions.
- Include replay and reproducibility evidence.
```

### 11.10 作者画像边界

```text
Author profile constraints:
- Keep AuthorMethodProfile, AuthorRuleProfile, and AuthorValidatedProfile separate.
- Do not describe results as the author's real trading performance.
- Separate article expression, rule statistics, and backtest validation.
- Every conclusion has evidence and confidence.
- New evidence creates drafts/revisions and does not overwrite published profiles.
- Batch method profiles use 10–20 structured articles.
```

### 11.11 策略版本与 Proposal

```text
Strategy constraints:
- StrategyVersion is formal and is not regenerated daily.
- DailyStrategyInstance is a runtime object.
- StrategyRevisionProposal cannot directly modify a published strategy.
- Freeze lifecycle, validation, publication, current-use, archive, and rollback
  behavior.
```

### 11.12 每日盘前

```text
Pre-market constraints:
- Complete data, market-state, strategy, and applicability checks before selection.
- Generate DailyRuleSelection, DailyStrategyInstance, and TradingDayPlan, not a
  formal strategy version.
- Explain enabled, reduced, and suspended rules.
- Trace every result to input versions and data-quality states.
- Missing inputs require repair or explicit degradation.
```

### 11.13 每日盘后归因

```text
Post-market constraints:
- Program facts calculate trigger, execution, MFE, MAE, return, and
  market-state change.
- LLM validates or explains but does not recompute program metrics.
- Use llm_attribution_v1 only for low confidence, conflict, or important signals.
- Use llm_postmortem_notes_v1 conditionally or once for daily summary.
- Keep rule, author, and strategy proposals separate.
- A single day never directly modifies formal objects.
```

### 11.14 运行保障与系统管理

```text
Operations constraints:
- Separate normal-user status/actions from administrator technical details.
- Use stable run_id and record steps, duration, errors, and retries.
- Record Prompt model/version/Schema/tokens/cost and data
  range/coverage/time semantics.
- Recovery supports resume, retry limits, and visible actions.
- User errors explain what happened, impact, and remediation.
- Freeze rollout stages and provide rollback/recovery.
```

### 11.15 最终退役与交付

```text
Final retirement constraints:
- Before deletion, verify target migration, data migration, reference scan,
  observation period, and rollback evidence.
- Do not retire legacy paths merely because a new page exists.
- Run the full real-data journey.
- Run E2E, frontend, backend, migration, and Prompt regression suites.
- Verify user/admin documentation against the actual UI.
```
