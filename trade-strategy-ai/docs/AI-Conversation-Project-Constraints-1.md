# Trade Strategy AI 项目专用 Prompt 约束库

本文件只在当前 Task 需要时读取。每个 Task 通常选择一个主约束，最多两个，不要把整个文件复制进 Prompt。

项目专用约束放在通用 Prompt 的“当前 Task/范围”之后、“执行和验证规则”之前。

### 11.1 Stage 1 产品页面

```text
Stage 1 constraints:
- Preserve trade-strategy-ai/web/src/app/route-config.tsx as the single route,
  navigation, permission, metadata, and compatibility fact source.
- Formal pages use business Chinese and do not expose Job, Workflow, Pipeline,
  Artifact, Provider, force, config_path, database names, or internal paths.
- Every formal page represents 页面用途、输入、处理状态、输出、下一步。
- Support loading, empty, error, partial, permission_denied, and unavailable
  truthfully.
- Do not convert unavailable data into false, zero, an empty list, or success.
- Legacy pages remain compatibility-only until retirement conditions pass.
- Do not enter Stage 2 before the Stage 1 exit Review.
```

### 11.2 领域契约冻结

```text
Domain contract constraints:
- Freeze stable IDs, version relationships, lifecycle states, source references,
  and audit fields before implementation.
- Produce object relationships and old-to-new mappings before changing ORM,
  API, or frontend types.
- Distinguish formal versions, daily runtime instances, proposals, and
  compatibility objects.
- Do not delegate unresolved source-of-truth decisions.
```

### 11.3 数据库迁移安全

```text
Database migration constraints:
- Inspect ORM models, metadata imports, Alembic heads, existing tables, and
  actual data first.
- Freeze target Schema and migration order before delegation.
- Migrations must be safely rerunnable, observable, and recoverable.
- Never silently drop or overwrite legacy data.
- Produce pre/post counts, rejected rows, and quality reports.
- Test upgrade, transformation, and rollback/recovery paths.
- Only one writer modifies a migration chain or shared ORM contract.
```

### 11.4 Prompt 迁移与退役

```text
Prompt migration constraints:
- Treat Prompt files, loader code, Schema, and regression fixtures as one contract.
- Record prompt_version, schema_version, model, input_hash, raw output,
  validation, tokens, and cost.
- Compare new and legacy results on the fixed regression set before cutover.
- New Prompt becomes the only formal write path before legacy becomes
  compatibility_only.
- Do not delete legacy Prompt until all references, observation, and rollback
  checks pass.
```

### 11.5 单篇文章闭环

```text
Single-article constraints:
- A normal article uses article_analysis_v1 as one main call.
- article_analysis_repair_v1 is targeted and used at most once.
- Modular extraction Prompts are Schema/test tools, not four default production
  calls.
- Preserve original text, evidence, explicit facts, hypotheses, missing fields,
  dependencies, and backtestability.
- Automatic pass means pending backtest, not formally usable.
- Only human-reviewed results may create a formal RuleVersion.
- Summary and other version-bound fields must be tied to the selected
  ArticleRevision/content version.
- Prefer a summary frozen in ArticleRevision source data.
- The current article summary may be used only when its content hash matches
  the selected ArticleRevision content hash.
- If revision alignment cannot be proven, summary must be unavailable.
- Never fall back to the latest article summary for an older revision.
- Summary provenance and validated ArticleStructure provenance must be exposed
  and verified separately.
- Do not fabricate or backfill historical summaries without evidence.
```

### 11.6 回归样本与批处理

```text
Batch processing constraints:
- Freeze 10–15 representative articles and expected outcomes first.
- Do not process all 100+ articles before the fixed set passes.
- Record article/content versions, Prompt/Schema versions, raw output,
  automatic review, and human conclusion.
- Support resume, bounded retry, idempotency, concurrency limits, and
  incremental updates.
- Do not send all article bodies in one LLM request.
```

### 11.7 规则治理

```text
Rule governance constraints:
- Automatic review cannot make a rule formally usable.
- High-risk, ambiguous, conflicting, parameter-edited, and strategy-entry rules
  require human approval.
- Freeze fingerprint, RuleFamily, parameter variant, conflict, and lifecycle
  semantics.
- Every transition records actor, time, reason, and before/after values.
```
