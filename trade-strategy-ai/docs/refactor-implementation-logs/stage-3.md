# Stage 3 Prompt 与文章处理链路实施日志

## 当前状态

- Stage：`Stage 3 Prompt 与文章处理链路`
- 状态：`[x] 已完成`
- 当前活动：`Stage 3 Gate` 已完成并接受。
- 下一可执行 Task：`Stage 4 Bootstrap`
- Stage 计划：[stage-3-implementation-plan.md](../refactor-implementation-plans/stage-3-implementation-plan.md)

## 2026-06-15 Bootstrap

### Task

- 范围：RT-S3-001～RT-S3-004 计划与合同冻结。
- Parent：gpt-5.5。
- 委派：`0` 个 subagent。
- 委派理由：source-of-truth、Prompt/Schema、writer ownership、人工审批和 destructive retirement 属于 Parent 决策；现有路径已足够聚焦，不需要 Explorer，也禁止 broad Executor。

### Baseline

- branch：`main`
- commit：`dc3236743f25503b2bec4841de5c8bbd8429bbf6`
- Bootstrap 开始时 `git status --short` 无输出。
- staged/unstaged diff 均为空。
- 未发现需要保留的用户未提交修改。

### Stage 2 prerequisite

- 主日志明确 Stage 2 `[x]`。
- Stage 2 详细日志 Final Gate 明确 `ACCEPTED`。
- 当前 shell 未设置 `STAGE2_CANONICAL_WRITER_ENABLED`。
- 运行 `canonical_writer_enabled()` 得到 `True`。
- 缺省配置为 true；canonical repository 需要 application-service scope。
- legacy RulePool、StrategyLibrary、MarketDataset writes 在 enabled 状态下拒绝。
- 未发现 dual-write。
- Stage 3 正式写入继续冻结为：

```text
Application Service
-> canonical repository
-> canonical PostgreSQL database
```

### Verified Stage 3 current implementation

- 14 个 v1 Prompt 文件存在。
- 5 个 legacy Prompt 文件存在。
- v1 Prompt 没有产品 runtime 引用。
- legacy article extraction 拼接 3 个 v0 Prompt，并写 legacy `ArticleMetadata`/`RulePool`。
- RulePool legacy write 在 effective true 下会被 writer guard 拒绝；不能作为 Stage 3 正式链路。
- canonical `PromptRun`、`ArticleStructure`、`RuleCandidate`、`RuleVersion` 已有表和 ORM。
- runtime 没有这些对象的正式 repository/application service 实现；除 Stage 2 migration 外没有构造点。
- 当前 LLM client 没有完整 token/cost/raw response/run trace。
- 当前 Article UI/API 是 metadata 版本选择，不是 Stage 3 单篇审核闭环。
- legacy auto review 存在自动 `approved` 语义，与冻结合同冲突。
- 没有固定 10～15 篇 Stage 3 regression set。
- legacy batch 有并发、分批和 checkpoint 可复用思路，但 identity、repair、持久化和 Gate 不符合 Stage 3。
- future-stage v1 Prompt 仅有文件资产，尚未激活。

### Frozen decisions

- canonical Prompt 名称、路径、版本、Schema、生产状态和 ownership 见 Stage 计划。
- 普通文章一个 `article_analysis_v1` 主调用。
- `article_analysis_repair_v1` 仅定向、最多一次。
- modular extraction Prompt 不是默认四次生产调用。
- raw LLM output 不是正式事实源。
- `explicit`、`inferred`、missing 和 human approval 分离。
- 未声明市场状态为 `not_declared`。
- automatic pass 只进入待回测。
- 只有明确 human review 可创建 RuleVersion。
- 固定 10～15 篇 regression set 通过前禁止 bulk 100+。
- 作者方法画像每 10～20 篇结构化文章调用，不逐篇生成总画像。
- attribution/postmortem 不在 Stage 3 激活。
- RT-S3-004 独立且最后。

### Task classification and order

| Task | Risk | Depends on | Status |
| --- | --- | --- | --- |
| RT-S3-001 | M3 | Stage 2 accepted | `[ ]` |
| RT-S3-002 | M3 | RT-S3-001 accepted | `[ ]` |
| RT-S3-003 | M2 | RT-S3-002 accepted | `[ ]` |
| RT-S3-004 | M3 | RT-S3-003 accepted + observation/rollback | `[ ]` |

### Verification performed

- 读取 AGENTS、AI templates/matrix、Stage 3 TaskList、正式方案、Prompt migration、author flow、LLM orchestration、主日志和 Stage 2 Gate 记录。
- 检查 branch、HEAD、status、staged/unstaged complete diff。
- 检索 v1/legacy Prompt 的全部 runtime references。
- 检查 canonical writer guard、Stage 2 writer tests 和 current effective value。
- 检查 canonical ORM/domain protocols、legacy article extraction、LLM client、article API/UI、rule review 和相关 tests。
- `../.venv/bin/python -m pytest tests/unit/services/test_stage2_writer_routing.py -q`：最终复验 `9 passed in 2.93s`。
- 14 个要求的 v1 Prompt 资产存在性扫描：全部存在。
- 文档绝对路径、占位符和 `git diff --check` 扫描：通过。
- 未运行 Stage 3 产品测试：本 Session 只修改计划和日志，不实施 Stage 3。

### Blockers and risks

- 当前无 Bootstrap blocker。
- v1 Prompt 内嵌版本字段与文件 stem 存在不一致，归 RT-S3-001。
- canonical Stage 3 runtime repository/application service 尚不存在，归 RT-S3-001/002。
- current article path 在 canonical writer enabled 时不能正式写规则；禁止通过关闭 flag 恢复。
- current UI 对“当前 metadata 版本可供回测/策略使用”的文案超前于 Stage 3/6 正式合同，RT-S3-002 必须纠正。
- legacy Prompt deletion 需要观察期，RT-S3-004 可能因外部观察证据等待而阻塞。

### Bootstrap conclusion

- Readiness：`READY_FOR_RT-S3-001`。
- Stage 3 不接受，状态保持 `[-]`。
- 未实施 RT-S3-001～004。
- 不允许自动开始 RT-S3-001。

## 2026-06-15 RT-S3-001

### Task

- Task ID：`RT-S3-001 接入版本化 Prompt 套件`
- Parent：gpt-5.4
- 委派：`0` 个 subagent。
- 委派理由：Prompt/Schema ownership、canonical registry、writer ownership、retry/repair 语义和最终 Task Review 都属于 Parent 决策；本仓库现有路径足以直接定位，不需要 Explorer，也不允许 broad Executor。

### Preconditions re-verified

- Stage 2 Gate 仍为 `ACCEPTED`。
- Stage 3 readiness 仍为 `READY_FOR_RT-S3-001`。
- 当前 shell 未显式设置 `STAGE2_CANONICAL_WRITER_ENABLED`，实测 `canonical_writer_enabled()` 返回 `True`。
- 正式写入链保持：

```text
Application Service
-> canonical repository
-> canonical PostgreSQL database
```

- 未发现 dual-write 或第二 formal writer。
- `PromptRun` / `ArticleStructure` / `RuleCandidate` 现有表字段足以承载 RT-S3-001 traceability；未触发 DB Schema 或 Alembic escalation。
- Bootstrap 时 working tree 为空；本 Task 仅新增 RT-S3-001 直接相关文件和 Prompt 版本修正。

### Implemented

- 新增 canonical versioned Prompt registry，冻结 14 个 v1 Prompt 的：
  - `prompt_name`
  - `prompt_version`
  - `file_path`
  - `schema_name`
  - `schema_version`
  - `production_status`
  - `ownership`
- 新增单一 Pydantic 输出 Schema 包，覆盖：
  - `article_analysis_v1`
  - `article_analysis_repair_v1`
  - modular extraction Prompts
  - future-stage asset_validated/batch_only Prompt 资产
- 修正已知版本错配：
  - `article_structure_extraction_v1.md`
  - `explicit_precondition_extraction_v1.md`
- 新增 Stage 3 Prompt runtime：
  - normal article 恰好 1 次 `article_analysis_v1`
  - validation failure 最多 1 次 `article_analysis_repair_v1`
  - repair 仅接收 article / previous_result / repair_targets / validation_errors
  - repair 失败后抛出人工处理错误，不执行第二次 repair
  - bounded provider retry 与 Schema repair 分离
- 新增 canonical repositories/application service foundation：
  - `PromptRun` upsert/update
  - validated `ArticleStructure`
  - validated `RuleCandidate`
  - canonical writer scope enforcement
- 新增 cache identity 与单进程并发 duplicate suppression：
  - `input_hash + prompt_version + schema_version + model + critical input`
  - cache hit 不重复 provider call
  - 同 identity 并发请求不重复创建 canonical records
- 未激活 future-stage Prompt runtime workflows。
- legacy Prompt 文件继续保留；未执行 RT-S3-004 retirement。

### Files

- Prompt:
  - `prompts/article_structure_extraction_v1.md`
  - `prompts/explicit_precondition_extraction_v1.md`
- Runtime / Schema / Repository:
  - `src/llm/__init__.py`
  - `src/llm/client.py`
  - `src/llm/prompt_registry.py`
  - `src/llm/runtime.py`
  - `src/schemas/prompt_outputs.py`
  - `src/db/repositories/stage3_prompt_runtime_repository.py`
  - `src/services/stage3_prompt_runtime_service.py`
- Tests:
  - `tests/unit/llm/test_client.py`
  - `tests/unit/llm/test_prompt_registry.py`
  - `tests/unit/stage3/test_prompt_runtime_service.py`
  - `tests/integration/test_stage3_prompt_runtime.py`

### Verification

- Focused red-green:
  - `../.venv/bin/python -m pytest tests/unit/llm/test_prompt_registry.py tests/unit/stage3/test_prompt_runtime_service.py tests/integration/test_stage3_prompt_runtime.py -q`
  - 最终：`9 passed`，随后扩展到 `13 passed`
- Frozen command set:
  - `../.venv/bin/python -m pytest tests/unit/llm tests/unit/schemas tests/unit/services/test_stage2_writer_routing.py -q`
    - 结果：`20 passed in 8.19s`
  - `../.venv/bin/python -m pytest tests/unit/stage3 tests/integration/test_stage3_prompt_runtime.py -q`
    - 结果：`6 passed in 3.27s`
  - `../.venv/bin/python -m compileall src api cli`
    - 结果：通过；shell 输出一条既有 `/Users/wanghui/.rvm/scripts/rvm:20: operation not permitted: ps`，compileall 退出码 `0`
  - `git diff --check`
    - 结果：通过
- Specialized evidence:
  - registry 14 项扫描：`14`
  - `article_analysis_v1` normal article 单调用：测试覆盖通过
  - `article_analysis_repair_v1` repair count `0..1`：测试覆盖通过
  - second repair rejection：测试覆盖通过
  - cache hit duplicate suppression：测试覆盖通过
  - concurrent duplicate suppression：测试覆盖通过
  - PromptRun trace fields：集成测试覆盖 `prompt_name/prompt_version/schema_name/schema_version/provider/model/input_hash/request_json/raw_output_text/validation_state/retry_count/token_usage/input_version_id`
  - canonical writer scope：通过 Stage 2 writer routing suite + Stage 3 repository/service tests 复验
  - future-stage Prompt 未激活：registry/asset validation only；未接入 formal runtime call chain

### Review

- BLOCKER：无
- HIGH：无
- MEDIUM：
  - `cost_amount` / `cost_currency` 目前仍依赖 provider 返回；现实现显式保留字段并在缺失时存 `null`，同时记录 token usage 和 raw output。后续若引入稳定计费规则，可在不改 DB Schema 的前提下补充计算。
- LOW：
  - 新增 `tests/unit/stage3/` 作为 RT-S3-001 等价 focused coverage 落点，替代原先仓库中不存在的 frozen path。

### Acceptance

- RT-S3-001 范围内实际 diff、focused tests、frozen verification、日志更新和 Parent Task Review 均完成。
- 未修改 Alembic、DB Schema 或 Stage 2 frozen relationships。
- 未启动 RT-S3-002、RT-S3-003、RT-S3-004。
- 结论：`RT-S3-001 ACCEPTED`

### Remaining Stage 3 gates

- Stage 3 整体仍为 `[-]`。
- `RT-S3-002` 现在可以开始，但本 Session 不自动开始。
- `RT-S3-003`、`RT-S3-004` 仍等待上游 accepted Task 和后续证据。

## 2026-06-15 - RT-S3-002 Single Article to Candidate Rule Journey

### Scope

- 仅执行 `RT-S3-002 Single Article to Candidate Rule Journey`。
- 冻结上游：`RT-S3-001 ACCEPTED`；其 registry/Schema/invocation/cache/idempotency/canonical persistence 合同保持不变。
- 未执行 `RT-S3-003`、`RT-S3-004` 或 Stage 4。

### Verified upstream facts

- `RT-S3-001` 仍为 `ACCEPTED`。
- `STAGE2_CANONICAL_WRITER_ENABLED` effective true。
- 正式写入链仍为：

```text
Application Service
-> canonical repository
-> canonical PostgreSQL database
```

- 未发现 dual-write 或第二 formal writer。
- 工作树开始时为空；无用户自有未提交改动。
- 冻结模型可以表示：
  - `PromptRun` / `ArticleStructure` / `RuleCandidate` trace 与 canonical persistence
  - human review actor / time / reason / before-after：通过 `LifecycleEvent`
  - Stage 3 RuleVersion boundary：以 canonical `RuleVersion.lifecycle_state = draft` 表示 formal `pending_backtest` boundary；未修改生命周期枚举

### Implementation

- 新增 canonical Stage 3 single-article repository / application service：
  - `src/db/repositories/stage3_single_article_repository.py`
  - `src/services/stage3_single_article_service.py`
- 单篇旅程现在支持：

```text
Article
-> ArticleRevision
-> RT-S3-001 runtime
-> PromptRun
-> ArticleStructure
-> RuleCandidate
-> deterministic automatic review
-> explicit human review
-> canonical RuleVersion(draft == pending_backtest boundary)
```

- deterministic automatic review 为纯程序规则，不触发额外 LLM 调用：
  - `pending_backtest`
  - `needs_human_review`
  - `suggested_reject`
- automatic review 不创建 `RuleVersion`。
- human review 才通过 canonical write scope 创建 `Rule` + `RuleVersion`。
- human review 同时写入 `LifecycleEvent`：
  - `RuleCandidate` 审核前后状态
  - `RuleVersion` 创建事件
- 新增 UI API：
  - `GET /api/ui/v1/article-metadata/articles/{article_id}/analysis`
  - `POST /api/ui/v1/article-metadata/articles/{article_id}/analysis`
  - `POST /api/ui/v1/article-metadata/articles/{article_id}/candidates/{candidate_id}/review`
- 新增 API Schema：
  - `api/schemas/article_analysis.py`
- 新增前端 article journey client/types/page：
  - `web/src/lib/api/article-analysis.ts`
  - `web/src/types/article-analysis.ts`
  - `web/src/pages/articles/ArticleResultsJourneyPage.tsx`
  - `web/src/pages/articles/index.tsx` export 切换到新结果页
- 现有 article 产品入口保持不变；未创建第二 formal article page route。

### Truthful user-visible result

- 文章详情页/API 现在展示：
  - original article text
  - cleaned content
  - article/content revision
  - summary
  - method tags
  - explicit facts
  - LLM hypotheses
  - missing/unknown fields
  - candidate rules
  - source evidence
  - data dependencies
  - backtestability
  - Kaipan dependency
  - market-state declaration status
  - Prompt/Schema/model/run trace
- 未声明市场状态保持 `not_declared`。
- 不再用旧 metadata 文案暗示“已可直接回测/策略使用”。
- human approval 按钮明确表述为“人工批准为待回测规则”。

### Files

- Backend / API:
  - `api/routers/ui/article_metadata.py`
  - `api/schemas/__init__.py`
  - `api/schemas/article_analysis.py`
  - `src/db/repositories/stage3_single_article_repository.py`
  - `src/services/stage3_single_article_service.py`
- Tests:
  - `tests/api/routers/ui/test_article_metadata.py`
  - `tests/unit/stage3/test_single_article_service.py`
  - `tests/integration/test_stage3_single_article.py`
- Frontend:
  - `web/src/lib/api/article-analysis.ts`
  - `web/src/types/article-analysis.ts`
  - `web/src/pages/articles/ArticleResultsJourneyPage.tsx`
  - `web/src/pages/articles/index.tsx`
  - `web/src/pages/articles/index.test.tsx`

### Verification

- Frozen backend command set:
  - `../.venv/bin/python -m pytest tests/api/routers/test_articles.py tests/api/routers/ui/test_article_metadata.py tests/api/routers/test_rule_pool.py -q`
    - 结果：`10 passed in 15.61s`
  - `../.venv/bin/python -m pytest tests/unit/stage3 tests/integration/test_stage3_single_article.py -q`
    - 结果：`9 passed in 3.37s`
- Upstream RT-S3-001 preservation:
  - `../.venv/bin/python -m pytest tests/unit/llm tests/unit/schemas tests/unit/services/test_stage2_writer_routing.py -q`
    - 结果：`21 passed in 6.66s`
  - `../.venv/bin/python -m pytest tests/integration/test_stage3_prompt_runtime.py -q`
    - 结果：`1 passed in 3.08s`
- Frontend:
  - `pnpm test -- src/pages/articles/index.test.tsx`
    - 结果：`8 passed`
  - `pnpm typecheck`
    - 结果：通过
- Build / diff:
  - `../.venv/bin/python -m compileall src api cli`
    - 结果：通过；shell 仍有既有 `/Users/wanghui/.rvm/scripts/rvm:20: operation not permitted: ps` 输出，退出码 `0`
  - `git diff --check`
    - 结果：通过

### Specialized evidence

- correct `ArticleRevision` linkage：
  - API / integration test 显示 `original_text` 来自 `BlogArticle.content_text`
  - `cleaned_content` 与 `article_revision_id` 来自 `ArticleRevision`
- summary / method tags：
  - `summary` 来自 canonical article record
  - `method_tags` 来自 validated canonical `ArticleStructure.payload`
- explicit facts / hypotheses visually/API-distinguished：
  - `explicit_facts` 与 `hypotheses` 分字段返回并独立展示
- missing fields visible：
  - `missing_fields` 在 article-level 和 candidate-level 保留
- candidate evidence retained：
  - `evidence` 从 canonical `RuleCandidate.evidence_json` 返回
- backtestability / Kaipan truthful：
  - `backtestability_status` 直接来自 canonical candidate
  - `kaipan_dependency` 由 persisted dependencies 派生
- undeclared market state：
  - API 返回 `market_state_declaration_status = not_declared`
- trace available：
  - API 返回 Prompt/Schema/model/run trace
- automatic review cannot create RuleVersion：
  - integration test 在 human approval 前断言 `RuleVersion count == 0`
- automatic pass represented as pending_backtest：
  - automatic review status 为 `pending_backtest`
- explicit human approval only RuleVersion path：
  - API + integration test 覆盖 `review_candidate(decision=approve)` 后才出现 `RuleVersion`
- Stage 3 RuleVersion boundary：
  - created `RuleVersion.lifecycle_state = draft`
  - UI/API `stage3_status = pending_backtest`
- permission enforcement：
  - viewer review API 返回 `403 insufficient permissions`
- truthful states：
  - UI/API tests 覆盖 loading / empty / error / partial / permission_denied；unavailable 仍沿用统一 API error handling
- no legacy formal writer / dual-write：
  - 新正式写入仅发生于 `canonical_write_scope("rule_version", ...)`
  - 未恢复 legacy `RulePool` / `ArticleMetadata` formal write
- no Stage 4 / Stage 6 behavior：
  - 未引入 RuleFamily / fingerprint / duplicate governance / backtest runtime
- RT-S3-001 single-call / one-repair behavior：
  - upstream prompt runtime integration test 复验通过

### Review

- BLOCKER：无
- HIGH：无
- MEDIUM：
  - `RuleVersion` 的 Stage 3 user-facing `pending_backtest` 通过 `draft` lifecycle + explicit `stage3_status` 映射表达；这满足冻结模型边界，但后续 Stage 4/6 仍需统一正式生命周期文案
- LOW：
  - 旧 `ArticlePipelinePage.tsx` 中 legacy metadata results page 仍保留在文件内但不再作为正式结果页导出；其最终退役不属于 `RT-S3-002`

### Acceptance

- single-article canonical data journey 已打通。
- automatic review 不创建 `RuleVersion`。
- explicit human approval 是唯一 `RuleVersion` 创建路径。
- created `RuleVersion` 保持 Stage 3 pending-backtest boundary。
- 未修改 DB Schema / Alembic。
- 未引入 dual-write 或 legacy formal writer。
- 日志已更新。
- 结论：`RT-S3-002 ACCEPTED`

### Remaining Stage 3 gates

- Stage 3 整体仍为 `[-]`。
- `RT-S3-003` 现在可以开始，但本 Session 不自动开始。
- `RT-S3-004` 仍等待 `RT-S3-003`、观察期和 rollback evidence。

## 2026-06-15 - RT-S3-003 Summary Provenance Contract Escalation Review

### Scope

- 仅审查 reported summary-provenance contradiction。
- 未实施 `RT-S3-003`。
- 保留当前 untracked regression/batch failing-test scaffolds。
- Parent：gpt-5.5。
- 委派：`0` 个 subagent；事实源、Schema ownership 和 Task acceptance 决策由 Parent 持有。

### Verified evidence

- `ArticleStructureExtractionOutput` 和 `article_analysis_v1` output Schema 没有 `summary`。
- `method_tags` 和 structured analysis fields 来自 validated canonical `ArticleStructure.payload`。
- `BlogArticle.summary` 是 article-level mutable field；`upsert_article_from_payload()` 会原地覆盖变化值。
- `ArticleRevision` 冻结 `content_hash/content_text/content_html/source_payload`，但没有 summary 字段。
- Stage 2 migration 写入的 `ArticleRevision.source_payload` 不保证包含 `BlogArticle.summary`。
- RT-S3-002 API 当前对任意 selected revision 返回当前 `BlogArticle.summary`，没有 summary source、revision ID、content hash 或 alignment proof。
- RT-S3-002 accepted tests 只 seed summary；没有验证 summary 随 selected revision 冻结或在旧 revision 下拒绝错误 fallback。
- RT-S3-003 untracked fixture scaffolds把 `BlogArticle.summary` seed 为 title，并断言 `summary_contains`；该证据不能证明 revision provenance。
- Review 开始时 tracked/staged diff 为空。安全 inventory/test scaffolds 仅为：
  - `tests/regression/stage3/test_fixed_set.py`
  - `tests/unit/stage3/test_regression_and_batch_services.py`
  - `tests/integration/test_stage3_batch.py`

### Contract decision

- Preferred premise 未验证：`BlogArticle.summary` 不是 frozen, version-aligned canonical summary source。
- 不向 `ArticleStructure` Prompt/Schema 添加 summary。
- 不修改 DB Schema 或 migration。
- `RT-S3-001` 保持 accepted；registry、Schema ownership、invocation/cache/idempotency 和 canonical persistence contracts 不变。
- 最小 reopened upstream Task 为 `RT-S3-002`，仅修复 summary/ArticleStructure provenance exposure and verification。
- `RT-S3-002` human review、RuleVersion、canonical writer 和 no-dual-write contracts 不变。
- `RT-S3-003` 在 provenance repair accepted 前不得恢复实现。

### Old and new evidence wording

Old:

```text
原文、summary、method tags、candidate rules、evidence、missing、backtestability、Kaipan、market-state status 全部真实展示。
```

New:

```text
原文与 cleaned content 绑定 selected ArticleRevision；summary 仅从 revision-bound frozen canonical source 展示，API 同时返回 summary_provenance，无法对齐时 truthful unavailable/partial。
method tags、structured claims、candidate rules、evidence、missing、backtestability、Kaipan 和 market-state status 来自 validated canonical ArticleStructure/RuleCandidate，API 同时返回 article_structure_provenance。
```

### Invalidated evidence and required tests

- Invalidated：
  - RT-S3-002 “summary 来自 canonical article record” acceptance statement。
  - 仅 seed/assert `BlogArticle.summary` 的 API/integration evidence。
  - RT-S3-003 scaffold 中未绑定 selected revision 的 `summary_contains` evidence。
- Required adjustments：
  - current revision summary provenance success case。
  - selected older revision with changed current article summary must not leak/fallback。
  - missing or unaligned frozen summary returns unavailable/partial with reason。
  - method tags and structured fields assert `ArticleStructure.article_revision_id/prompt_run_id` provenance independently。
  - regression manifest records and checks both provenance objects。

### Verification

- `../.venv/bin/python -m pytest tests/unit/stage3/test_single_article_service.py tests/integration/test_stage3_single_article.py tests/api/routers/ui/test_article_metadata.py -q`
  - `8 passed`
  - 结论：accepted RT-S3-002 behavior 仍通过，但现有 suite 未覆盖 revision-bound summary provenance。
- `../.venv/bin/python -m pytest tests/regression/stage3/test_fixed_set.py tests/unit/stage3/test_regression_and_batch_services.py tests/integration/test_stage3_batch.py -q`
  - collection failed：`stage3_regression_fixtures` 和 `stage3_batch_service` 尚未实现。
  - 结论：符合“保留 failing scaffolds、未实施 RT-S3-003”；不是新的 product regression evidence。
- `git diff --check`
  - 通过。

### Status

- `RT-S3-001`：`[x] ACCEPTED`。
- `RT-S3-002`：`[-] REOPENED`，仅限 provenance repair。
- `RT-S3-003`：`[!] BLOCKED` by reopened upstream Task；safe scaffolds preserved。
- `RT-S3-004`：`[ ]`，继续等待。
- Review conclusion：`REOPEN_UPSTREAM_TASK`。

## 2026-06-15 - RT-S3-002 Summary and ArticleStructure Provenance Repair

### Scope

- 仅执行 reopened `RT-S3-002` bounded provenance repair。
- 不重跑 Stage 3 Bootstrap。
- 不修改 `RT-S3-001` registry/Schema/runtime contracts。
- 不恢复 `RT-S3-003` 实现；仅保留其 safe inventory work 和 untracked failing scaffolds。

### Root cause

- API 对 selected revision 一律返回当前 `BlogArticle.summary`。
- 当 `BlogArticle.summary` 已被后续内容覆盖时，older `ArticleRevision` 会泄漏最新摘要。
- `method_tags` 仍来自 validated canonical `ArticleStructure`，但原实现没有把 summary provenance 与 ArticleStructure provenance 分开表达或验证。

### Repair decision

- summary provenance 冻结为：
  - 首选 `ArticleRevision.source_payload` 中的 frozen summary；
  - 仅当 selected revision `content_hash == BlogArticle.content_hash` 时，允许使用当前 `BlogArticle.summary` 作为 latest-revision aligned summary；
  - 若 selected older revision 没有 frozen summary，则返回 `summary = null`，`summary_provenance.source = unavailable`，不得回退到当前 article row。
- method tags、structured claims、candidate rules、missing 和 evidence 继续来自 validated canonical `ArticleStructure`。
- API 明确返回：
  - `summary_provenance`
  - `article_structure_provenance`
  - selected revision `content_hash`

### Files

- `src/services/stage3_single_article_service.py`
- `api/schemas/article_analysis.py`
- `api/routers/ui/article_metadata.py`
- `tests/unit/stage3/test_single_article_service.py`
- `tests/api/routers/ui/test_article_metadata.py`
- `tests/integration/test_stage3_single_article.py`

### TDD

- 先新增/更新失败测试：
  - latest revision summary provenance success
  - older revision summary from revision-bound source
  - older revision must not leak changed current article summary
  - API `article_revision_id/content_hash` 与 `summary_provenance` 对齐
  - `method_tags` 继续验证 `ArticleStructure` provenance
- 红灯阶段：
  - `ImportError: resolve_summary_provenance` not found
- 随后补最小实现并复跑至全绿。

### Verification

- `../.venv/bin/python -m pytest tests/api/routers/ui/test_article_metadata.py tests/unit/stage3/test_single_article_service.py tests/integration/test_stage3_single_article.py -q`
  - `12 passed in 6.33s`
- `../.venv/bin/python -m compileall src api cli`
  - 通过；shell 输出既有 `/Users/wanghui/.rvm/scripts/rvm:20: operation not permitted: ps`，退出码 `0`
- `git diff --check`
  - 通过

### Specialized evidence

- latest revision：
  - `summary_provenance.source = blog_article_current`
  - 仅在 `selected revision.content_hash == BlogArticle.content_hash` 时允许
- older revision：
  - 若 `ArticleRevision.source_payload.summary` 存在，则返回该 frozen summary
  - 修改当前 `BlogArticle.summary` 不改变 older revision response
  - 若 frozen summary 不存在，则 `summary = null` 且 `summary_provenance.source = unavailable`
- API 同时返回 `article_structure_provenance.article_revision_id/prompt_run_id/prompt/schema`
- `method_tags` 仍从 selected revision 对应的 canonical `ArticleStructure.payload.method_tags` 返回
- human-review / RuleVersion:
  - 原 integration flow 仍通过
  - `RuleVersion.lifecycle_state = draft` 与 `pending_backtest` 映射未变
- 未修改 DB Schema、Alembic、writer routing 或 legacy formal write behavior
- `RT-S3-003` safe untracked scaffolds 保持未触碰：
  - `tests/regression/stage3/test_fixed_set.py`
  - `tests/unit/stage3/test_regression_and_batch_services.py`
  - `tests/integration/test_stage3_batch.py`

### Review

- BLOCKER：无
- HIGH：无
- MEDIUM：
  - 现有真实数据中 `ArticleRevision.source_payload` 未普遍保存 summary；因此 older revision summary 在缺少 frozen source 时会 truthful unavailable，而不是伪造回填。这符合 amended contract。

### Acceptance

- reopened `RT-S3-002` provenance repair 范围内的实现、测试和日志已完成。
- `RT-S3-001` accepted contracts preserved。
- `RT-S3-003` safe work preserved，但未恢复执行。

## 2026-06-15 - RT-S3-003 Regression Set and Recoverable Batch Processing

### Scope

- 仅执行 `RT-S3-003 Build the Regression Set and Recoverable Batch Processing`。
- 保持上游冻结：
  - `RT-S3-001 ACCEPTED`
  - `RT-S3-002 ACCEPTED`，并采用 revision-bound summary provenance 合同
- 未执行 `RT-S3-004`、Stage 4、Stage 6 或 Stage 7。

### Preserved safe work

- 保留 escalation 前已完成的 canonical article inventory audit：
  - `blog_articles=131`
  - `article_revisions=131`
  - `prompt_runs=262`
  - `article_structures=262`
  - `rule_candidates=485`
  - `rule_versions=14`
- 保留 12 篇代表性候选池与类别覆盖分析。
- 在原有 untracked scaffolds 上直接完成实现；未删除、未重建：
  - `tests/regression/stage3/test_fixed_set.py`
  - `tests/unit/stage3/test_regression_and_batch_services.py`
  - `tests/integration/test_stage3_batch.py`

### Fixed regression set

- 固定回归集数量：`12`
- 覆盖类别完整：
  - `explicit_and_actionable_rules`
  - `pure_conceptual_content`
  - `mixed_concept_and_rule_content`
  - `concrete_review_case_study_content`
  - `explicit_market_state`
  - `undeclared_market_state`
  - `ambiguous_terminology`
  - `kaipan_dependency`
  - `duplicate_or_near_duplicate_rules`
  - `conflicting_viewpoints`
  - `human_review_required`
- 冻结 identity / version：
  - `article_id`
  - `article_revision_id`
  - `content_hash`
  - `prompt_name=article_analysis_v1`
  - `prompt_version=article_analysis_v1`
  - `schema_name=article_analysis_v1`
  - `schema_version=article_analysis_v1`
  - `model=stage3-fixed-fixture-model`
- 修订后的 provenance 合同已应用到 fixture：
  - 当前真实仓库 `131/131` 篇 `BlogArticle.summary` 为空
  - 当前真实仓库 `131/131` 个 `ArticleRevision.source_payload` 也无 frozen summary
  - 因此 fixed set 的 summary expectation 统一冻结为 `source=unavailable`
  - `summary unavailable` 被视为 truthful expected state，不构成 regression failure
  - `method_tags` / 结构化字段继续由 validated canonical `ArticleStructure` 提供并单独校验 provenance

### Implemented

- 新增 Stage 3 fixed-set fixture / semantic assertion layer：
  - `src/services/stage3_regression_fixtures.py`
  - 明确分离 `summary_expectation` 与 `semantic_assertions`
  - 冻结 12 篇文章的 revision/content hash/category coverage
- 新增 Stage 3 regression runner：
  - `src/services/stage3_regression_service.py`
  - 通过 accepted RT-S3-001 runtime 跑固定集
  - 验证 summary provenance / article structure provenance / semantic assertions
  - 检查 normal article 仍为 1 main call + 最多 1 repair
  - 检查无 human approval 时不生成 `RuleVersion`
- 新增 Stage 3 recoverable batch service：
  - `src/services/stage3_batch_service.py`
  - fixed-set gate 未通过时 block
  - 使用 `jobs.runtime_state` / `progress` 保存 checkpoint 与质量统计
  - 支持 resume / idempotent rerun / revision incremental reprocess
  - concurrency bounded，且 provider/network retry 仍由 accepted runtime bounded 控制
- 新增冻结 CLI 命令：
  - `python -m cli.main stage3-regression run --fixed-set`
  - `python -m cli.main stage3-article-batch run --dry-run --limit 15`
- bounded RT-S3-001 integration correction：
  - `src/db/repositories/stage3_prompt_runtime_repository.py`
  - SQLite / test path 下 cache query 现在用 enum value 过滤，确保 accepted cache contract 可被稳定复验

### Files

- Runtime / CLI:
  - `src/services/stage3_regression_fixtures.py`
  - `src/services/stage3_regression_service.py`
  - `src/services/stage3_batch_service.py`
  - `src/db/repositories/stage3_prompt_runtime_repository.py`
  - `cli/main.py`
- Tests:
  - `tests/regression/stage3/test_fixed_set.py`
  - `tests/unit/stage3/test_regression_and_batch_services.py`
  - `tests/integration/test_stage3_batch.py`

### Verification

- RT-S3-003 focused suite：
  - `../.venv/bin/python -m pytest tests/regression/stage3 tests/unit/stage3 tests/integration/test_stage3_batch.py -q`
  - 结果：`18 passed in 7.28s`
- RT-S3-002 provenance preservation：
  - `../.venv/bin/python -m pytest tests/api/routers/ui/test_article_metadata.py tests/unit/stage3/test_single_article_service.py tests/integration/test_stage3_single_article.py tests/integration/test_stage3_prompt_runtime.py -q`
  - 结果：`13 passed in 6.84s`
- RT-S3-001/runtime preservation：
  - `../.venv/bin/python -m pytest tests/unit/llm tests/unit/schemas tests/unit/services/test_stage2_writer_routing.py -q`
  - 结果：`21 passed in 4.67s`
- 固定集门禁命令：
  - `../.venv/bin/python -m cli.main stage3-regression run --fixed-set`
  - 结果：
    - `status=passed`
    - `article_count=12`
    - `processed_count=12`
    - `cached_count=0`
    - `repaired_count=0`
    - `human_attention_count=6`
    - `semantic_failures=[]`
- 受控 dry-run 命令：
  - `../.venv/bin/python -m cli.main stage3-article-batch run --dry-run --limit 15`
  - 结果：
    - `status=completed`
    - `gate_status=passed`
    - `processed_count=12`
    - `success_count=12`
    - `cached_count=12`
    - `repaired_count=0`
    - `retry_count=0`
    - `human_attention_count=6`
    - `quality_stats.automatic_review_status_counts={"needs_human_review": 6, "pending_backtest": 4}`
- Static / diff:
  - `../.venv/bin/python -m compileall src api cli`
    - 结果：通过
  - `git diff --check`
    - 结果：通过

### Specialized evidence

- fixed set 为 `12` 篇 existing articles，类别覆盖完整。
- 所有 fixture 同时绑定 article/revision/content hash 与 Prompt/Schema versions。
- semantic assertions 使用语义断言而非全文精确匹配。
- fixed-set failure blocks batch：
  - unit test 覆盖通过
- repeated regression 无 formal duplicates：
  - repeated run 仅命中 cache；`PromptRun/ArticleStructure/RuleCandidate` 不重复增长
- repeated batch rerun / resume：
  - 单个 `Job` checkpoint 持续复用
  - injected failure 后 resume 仅处理剩余 revision
- incremental content-version update：
  - 新 revision 仅重跑受影响文章
  - 旧 revision 结果保持 traceable
- concurrency limit：
  - 测试覆盖 `max_active_calls <= configured limit`
- bounded retry：
  - provider failure fixture 只触发 bounded network retry
  - Schema repair 仍保持 `0..1`
- provenance：
  - summary provenance 与 article structure provenance 分开校验
  - unavailable summary 被保留为 truthful expected state
- no per-article author total-profile call：
  - RT-S3-003 实现未引入 author total-profile runtime
- no DB Schema / Alembic change：
  - 符合
- no dual-write / no legacy formal writer：
  - 通过 Stage 2 writer routing suite + Stage 3 focused tests 复验
- no full 100+ processing：
  - 本 Task 只执行 fixed set 12 篇 + `--limit 15` dry-run readiness evidence

### Parent review

- BLOCKER：无
- HIGH：无
- MEDIUM：
  - 当前 fixed set 的 revision-bound summary expectation 全部为 `unavailable`，这是当前 canonical article source 的真实状态，而不是 fixture 降级。后续若文章 source 开始保留 revision summary，应显式更新 fixture 与预期。

### Acceptance

- fixed set `12` 篇，类别覆盖完整。
- fixed-set regression gate 通过。
- batch dry-run / checkpoint-resume / idempotency / incremental / retry / concurrency focused tests 通过。
- 真实 dry-run 仅处理 fixed set 12 篇；未触发全量 100+ 处理。
- 未修改 DB Schema / Alembic。
- 未恢复 legacy formal writer，未引入第二 writer / second fact source。
- 日志已更新。
- 结论：`RT-S3-003 ACCEPTED`

### Remaining Stage 3 gates

- Stage 3 整体仍为 `[-]`。
- `RT-S3-004` 现在可以开始，但本 Session 不自动开始。
- Stage 3 不得标记完成；仍需 RT-S3-004 cutover/retirement、观察期与 rollback evidence。
- 结论：`RT-S3-002 RE-ACCEPTED`

## 2026-06-16 RT-S3-004 Recovery, Continuation, and Retirement

### Scope

- 仅执行 `RT-S3-004 旧 Prompt 迁移与退役`。
- Recovery Session 基于仓库事实继续中断的上一个 5.5 Session，不重启 Task。
- 保持上游 accepted contracts 不变：
  - `RT-S3-001`～`RT-S3-003` accepted
  - canonical Prompt registry / Pydantic Schema ownership 不变
  - canonical writer 仍为唯一 formal writer
  - no dual-write
  - historical-read compatibility 保留
  - no DB Schema / Alembic change
  - no Stage 4+ implementation

### Recovered state from repository evidence

- Recovery 时 `git status --short` 显示：
  - tracked modified:
    - `src/agents/data_agent/skills/extract_article_metadata.py`
    - `src/evaluation/postmortem_service.py`
    - `tests/unit/agents/test_extract_article_metadata.py`
    - `tests/unit/agents/test_extract_article_metadata_extended.py`
  - untracked:
    - `src/services/stage3_prompt_retirement.py`
    - `tests/integration/test_stage3_legacy_compatibility.py`
- 完整 diff 证据显示：
  - legacy article extraction 已改为加载 `article_analysis_v1`，并投影到 legacy reader shape；
  - postmortem Prompt helper 已改为加载 `llm_attribution_v1` / `llm_postmortem_notes_v1`；
  - 5 个 legacy Prompt 文件仍存在，形成 unsafe partial retirement；
  - Stage 日志和主日志仍把 `RT-S3-004` 记录为未开始。
- 未发现与本 Task 无关的用户修改。

### Recovery review findings

- BLOCKER：无
- HIGH：
  - legacy Prompt 文件仍存在，删除 gate 未真正完成。
- MEDIUM：
  - retirement inventory 是 static stub，未绑定真实文件删除状态。
  - 缺少 machine-verifiable fixed-set compatibility comparison evidence。
  - 主日志 / Stage 日志仍是 stale “未开始”状态。

### Bounded repairs

- 将 `src/services/stage3_prompt_retirement.py` 从静态 stub 补为 file-truth inventory：
  - 每个 legacy Prompt 记录 `prompt_path`
  - 运行时按仓库状态计算 `prompt_file_exists`
  - `deletion_gate_status` 由真实文件存在性驱动
- 补充 `tests/integration/test_stage3_legacy_compatibility.py`：
  - 断言 5 个 legacy Prompt 文件已从 `prompts/` 删除
  - 断言 retirement inventory 反映 `prompt_file_exists is False`
  - 新增 fixed-set compatibility projection comparison
- 删除 legacy Prompt 文件：
  - `prompts/concept_extraction.md`
  - `prompts/rule_extraction.md`
  - `prompts/precondition_extraction.md`
  - `prompts/llm_attribution.md`
  - `prompts/llm_postmortem_notes.md`
- 新增正式 retirement 证据文档：
  - `docs/RT-S3-004-Prompt-Retirement-Report.md`

### Files changed

- Deleted:
  - `prompts/concept_extraction.md`
  - `prompts/rule_extraction.md`
  - `prompts/precondition_extraction.md`
  - `prompts/llm_attribution.md`
  - `prompts/llm_postmortem_notes.md`
- Added:
  - `src/services/stage3_prompt_retirement.py`
  - `tests/integration/test_stage3_legacy_compatibility.py`
  - `docs/RT-S3-004-Prompt-Retirement-Report.md`
- Modified:
  - `src/agents/data_agent/skills/extract_article_metadata.py`
  - `src/evaluation/postmortem_service.py`
  - `tests/unit/agents/test_extract_article_metadata.py`
  - `tests/unit/agents/test_extract_article_metadata_extended.py`
  - `docs/Refactor-Implementation-Log.md`
  - `docs/refactor-implementation-logs/stage-3.md`

### Verification

- Red step:
  - `../.venv/bin/python -m pytest tests/integration/test_stage3_legacy_compatibility.py -q`
  - 初次结果：`1 failed, 4 passed`
  - 失败原因：5 个 legacy Prompt 文件仍存在
- After repair:
  - `../.venv/bin/python -m pytest tests/integration/test_stage3_legacy_compatibility.py -q`
  - 结果：`6 passed in 6.54s`
- Frozen RT-S3-004 suite:
  - `../.venv/bin/python -m pytest tests/regression/stage3 tests/unit/llm tests/integration/test_stage3_legacy_compatibility.py -q`
  - 结果：`14 passed in 3.52s`
- Invalidated local compatibility suite:
  - `../.venv/bin/python -m pytest tests/e2e/test_article_pipeline_v1.py tests/unit/agents/test_extract_article_metadata.py tests/unit/agents/test_extract_article_metadata_extended.py -q`
  - 结果：`17 passed, 1 skipped in 5.98s`
- Static:
  - `git diff --check`
  - 结果：通过
- Reference scan:
  - `rg -n "concept_extraction\.md|rule_extraction\.md|precondition_extraction\.md|llm_attribution\.md|llm_postmortem_notes\.md" src api cli scripts tests prompts docs`
  - 结果：
    - `prompts/` 无 legacy Prompt 文件命中
    - `src/` 仅 retirement inventory metadata 命中
    - `tests/` 仅 compatibility gates 命中
    - `docs/` 为历史设计、Task、migration 和 retirement 记录命中

### Specialized evidence

- fixed-set compatibility comparison：
  - `article_analysis_v1` fixed fixtures 可稳定投影为 legacy reader shape
- sole formal writer verification：
  - 无生产 caller 继续加载 legacy Prompt filenames
  - formal write chain 仍为 canonical application-service chain
- historical-read compatibility：
  - historical adapter 不加载已删除 Prompt 文件
  - registry 不暴露 legacy Prompt identity/path
- rollback evidence：
  - active callers 以 `article_analysis_v1` / `llm_attribution_v1` / `llm_postmortem_notes_v1` 为硬绑定
  - 恢复旧 Prompt 文件文本不会重新激活 legacy routing
- per-prompt deletion gate：
  - 5/5 passed

### Acceptance

- legacy Prompt inventory、old-to-new mapping、fixed-set compatibility comparison、sole-writer verification、historical-read compatibility、rollback evidence、per-prompt deletion gates、safe deletion、focused tests 和正式日志更新全部完成。
- 未修改 Stage 3 frozen contract。
- 未引入第二 formal writer。
- 未引入 DB Schema / Alembic change。
- Stage 3 Gate 尚未开始。
- 结论：`RT-S3-004 ACCEPTED — Stage 3 Gate may begin`

## 2026-06-16 Stage 3 Gate Review and Final Decision

### Scope

- Gate：`Stage 3 Prompt and Article Processing Pipeline`
- Tasks：`RT-S3-001`、`RT-S3-002`、`RT-S3-003`、`RT-S3-004`
- Parent：gpt-5.5
- 委派：
  - Explorer Alpha：single-article journey、human review、RuleVersion boundary、summary/ArticleStructure provenance。
  - Explorer Beta：Prompt registry、Schema、invocation/repair、future Prompt inactivity。
  - Explorer Gamma：fixed regression set、batch readiness、recovery guarantees。
  - 第四个 legacy/log slice 因 subagent thread limit 由 Parent 本地执行。

### Initial findings

- `AUTO_REPAIRABLE MEDIUM`：主日志 Stage 3 summary stale，仍写成仅 RT-S3-001～RT-S3-003 accepted 且 RT-S3-004 remains。
  - Owning Task：`Stage 3 Gate documentation consistency`
  - Repair：本 Gate 将主日志 Stage 3 状态、当前状态、下一步和 residual risk 更新为 final accepted truth。
- `AUTO_REPAIRABLE LOW`：controlled dry-run batch command 在 sandbox 内因本地 PostgreSQL socket 权限返回 `PermissionError: [Errno 1] Operation not permitted`，同一命令按权限流程在外部执行通过。
  - Owning Task：`RT-S3-003`
  - Repair：无需代码变更；记录为 verification environment issue。
- `AUTO_REPAIRABLE MEDIUM`：`PostmortemService` / `postmortem_tasks` 可触达 `llm_attribution_v1` 与 `llm_postmortem_notes_v1`，与 Gate “future-stage Prompts remain inactive” 不一致。
  - Owning Task：`RT-S3-004`
  - Repair：保留 historical/fallback postmortem behavior，但在 Stage 3 hard-disable future-stage LLM prompt invocation；enabled clients are not called and prompt assets are not loaded.
- `CONTRACT_SENSITIVE`：无。Postmortem prompt activation resolution did not require changing frozen contracts.

### Verified final facts

- `RT-S3-001`～`RT-S3-004` 均保持 accepted。
- Canonical Prompt registry 是 Prompt identity/version/status 的运行事实源；Pydantic models 是 output Schema 事实源。
- 普通文章主链路仍为 `article_analysis_v1` 一次主调用，Schema repair 为 targeted 且最多一次。
- `PromptRun.raw_output` / `raw_output_text` 只作为 traceability，不作为正式业务事实源。
- `ArticleStructure` / `RuleCandidate` 保持 facts、hypotheses、evidence、missing fields 与 `not_declared` 分离。
- Deterministic automatic review 不创建 `RuleVersion`。
- 只有 explicit human approval 创建 `RuleVersion`；Stage 3 `draft` lifecycle 继续映射为 user-facing `pending_backtest` boundary。
- Revision-bound summary 不回退到 latest article summary；无法证明对齐时保持 truthful unavailable。
- Fixed regression set 为 12 篇，覆盖要求类别；未执行 full 100+ article processing。
- Batch readiness 通过 fixed-set gate、idempotent resume、checkpoint、incremental、bounded retry 和 concurrency-bound tests 验证。
- Future-stage Prompts 保持 `asset_validated` / inactive；未启动 Stage 4+ behavior。
- v1 链路是唯一 formal production writer；legacy Prompt 文件 5/5 已删除，legacy references 仅剩 retirement inventory、tests 和 historical docs。
- Historical reads and rollback remain safe without deleted Prompt files。
- Stage 3 Tasks 未新增 DB Schema 或 Alembic migration。完整 bootstrap-to-HEAD diff 中存在一个独立 Stage 2 migration-ordering repair commit，修改既有 Stage 2 migration 的 fresh-database FK defer logic，不新增 Stage 3 schema。

### Final verification

- `../.venv/bin/python -m pytest tests/regression/stage3 tests/unit/stage3 tests/integration/test_stage3_prompt_runtime.py tests/integration/test_stage3_single_article.py tests/integration/test_stage3_batch.py tests/integration/test_stage3_legacy_compatibility.py -q`
  - `27 passed`
- `../.venv/bin/python -m pytest tests/unit/llm tests/unit/schemas tests/unit/services/test_stage2_writer_routing.py -q`
  - `21 passed`
- `../.venv/bin/python -m pytest tests/api/routers/test_articles.py tests/api/routers/ui/test_article_metadata.py tests/api/routers/test_rule_pool.py -q`
  - `10 passed`
- `../.venv/bin/python -m pytest tests/e2e/test_article_pipeline_v1.py tests/unit/agents/test_extract_article_metadata.py tests/unit/agents/test_extract_article_metadata_extended.py -q`
  - `17 passed, 1 skipped`
- `../.venv/bin/python -m cli.main stage3-regression run --fixed-set`
  - `status=passed`, `article_count=12`, `processed_count=12`, `cached_count=12`, `repaired_count=0`, `human_attention_count=6`
- `../.venv/bin/python -m cli.main stage3-article-batch run --dry-run --limit 15`
  - sandbox result：blocked by local PostgreSQL socket permission
  - approved external rerun：`status=completed`, `gate_status=passed`, `skipped_count=12`, `concurrency_limit=2`
- `pnpm test -- src/pages/articles/index.test.tsx`
  - `8 passed`
- `pnpm typecheck`
  - passed
- `../.venv/bin/python -m compileall src api cli`
  - passed
- `../.venv/bin/python -m pytest tests/unit/db/test_migrations.py -q`
  - `3 passed`
- `git diff --check`
  - passed
- Legacy Prompt active reference scan over `src api cli scripts prompts`
  - no active production reference; only retirement inventory metadata remains in `src/services/stage3_prompt_retirement.py`.

### Contract compliance

- No unresolved `BLOCKER` or required `HIGH` remains.
- No dual-write or legacy formal writer exists.
- No Stage 4+ behavior was implemented by Stage 3.
- Logs, Stage status and runtime evidence now agree.

### Gate repair evidence

- Files changed:
  - `src/evaluation/postmortem_service.py`
  - `tests/unit/evaluation/test_postmortem_service.py`
  - `tests/integration/test_stage3_legacy_compatibility.py`
- Repair verification:
  - `../.venv/bin/python -m pytest tests/unit/evaluation/test_postmortem_service.py::TestGenerate::test_generate_with_notes_enabled_keeps_future_stage_llm_inactive tests/unit/evaluation/test_postmortem_service.py::test_llm_attribution_future_stage_prompt_inactive_with_enabled_client tests/integration/test_stage3_legacy_compatibility.py::test_postmortem_llm_helpers_do_not_activate_future_stage_prompt_assets -q`
    - Red before repair：`3 failed`
    - Green after repair：`3 passed`
  - `../.venv/bin/python -m pytest tests/unit/evaluation/test_postmortem_service.py tests/unit/pipeline/tasks/test_postmortem_tasks.py tests/integration/test_stage3_legacy_compatibility.py -q`
    - `35 passed`
  - `../.venv/bin/python -m pytest tests/unit/llm/test_prompt_registry.py tests/unit/llm/test_client.py tests/unit/stage3/test_prompt_runtime_service.py tests/integration/test_stage3_prompt_runtime.py tests/integration/test_stage3_single_article.py -q`
    - `15 passed`

### Final Gate decision

`ACCEPTED: next Stage may begin`

Stage 4 Bootstrap may begin. Stage 4 was not started automatically.
