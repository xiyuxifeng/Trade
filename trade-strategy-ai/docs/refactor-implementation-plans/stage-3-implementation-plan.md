# Stage 3 Prompt 与文章处理链路实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `refactor-orchestrator` for every Task session and Stage Gate. Use `superpowers:test-driven-development` during implementation. Do not execute more than one Task Card as one acceptance unit.

**Goal:** 在不进入 Stage 4 规则治理的前提下，建立唯一、版本化、可追溯的 Prompt 与文章处理正式链路，完成单篇文章到人工审核后 RuleVersion、固定回归集、可恢复批处理和旧 Prompt 退役。

**Architecture:** `ArticleRevision -> versioned Prompt registry/Schema -> PromptRun -> ArticleStructure -> RuleCandidate -> deterministic automatic review -> explicit human review -> RuleVersion`。所有正式写入必须经过 application service 和 canonical repository，落入 canonical PostgreSQL；legacy 结果仅用于读取、对照和迁移。

**Tech Stack:** Python 3.11、Pydantic 2、SQLAlchemy async、PostgreSQL、FastAPI、React/TypeScript、Vitest、Pytest。

---

## 1. Bootstrap 决定

- 日期：2026-06-15
- 分支：`main`
- 基线：`dc3236743f25503b2bec4841de5c8bbd8429bbf6`
- 工作树：Bootstrap 开始时 clean，未发现用户未提交修改。
- 委派：`0` 个 subagent。
- 原因：本次工作是事实源、Prompt/Schema、正式写入、人工审批和退役合同冻结，均由 Parent 持有；已知路径足以完成调查，没有收益高于上下文传递成本的独立只读域。
- Stage 3 readiness：`READY_FOR_RT-S3-001`。
- 本文只冻结合同和 Task Cards；未实施 RT-S3-001～004。

## 2. 权威来源与冲突处理

优先级：

```text
AGENTS.md
> Trade-Refactor-TaskList.md
> trade-strategy-ai-web-refactor-plan-market-state-v2.md
> Stage 3 专项 Prompt 文档
> 当前实现
```

已识别冲突：

- `trade-strategy-ai-web-refactor-plan-market-state-v2.md` 的旧实施阶段编号与主 TaskList 不一致；Stage 3 范围以 `Trade-Refactor-TaskList.md` 的 RT-S3-001～004 为准。
- 部分 v1 Prompt 内嵌 `prompt_version` 与文件 stem 不一致，例如 `article_structure_extraction_v1.md` 输出 `article_structure_v1`、`explicit_precondition_extraction_v1.md` 输出 `explicit_precondition_v1`。RT-S3-001 必须按本文 canonical registry 修正，不能让文件、loader、Schema 和 fixture 各自解释版本。
- `PROMPT_REVIEW_AND_MIGRATION.md` 的早期“并行验证”只允许保存对照结果，不允许 legacy 与新链路同时产生正式业务数据。

## 3. 已验证仓库与运行事实

### 3.1 Stage 2 Gate 与单写者

- `Refactor-Implementation-Log.md` 和 `refactor-implementation-logs/stage-2.md` 均明确记录 Stage 2 Gate `ACCEPTED`。
- `STAGE2_CANONICAL_WRITER_ENABLED` 当前 shell 未设置；`canonical_writer_enabled()` 实测返回 `True`。
- `src/common/stage2_writer_routing.py` 缺省为 `true`。
- canonical repository 写入在启用状态下要求匹配的 `canonical_write_scope`。
- legacy RulePool、StrategyLibrary、MarketDataset writer 在启用状态下拒绝写入。
- 正式写入合同为：

```text
Application Service
-> canonical repository
-> canonical PostgreSQL database
```

- 未发现 Stage 3 runtime 对 `PromptRun`、`ArticleStructure`、`RuleCandidate`、`RuleVersion` 的构造或保存；这些 canonical 对象目前只在 Stage 2 migration 中生成。
- 未发现 dual-write。现有 legacy article extraction 会尝试写 `ArticleMetadata` 和 `RulePool`，但 RulePool 正式写入在有效配置下被拒绝，因此该链路不可作为 Stage 3 正式实现。

### 3.2 Prompt、Schema 和调用链

- 14 个要求的 v1 Prompt 文件均已存在。
- 5 个 legacy Prompt 文件仍存在：`concept_extraction.md`、`rule_extraction.md`、`precondition_extraction.md`、`llm_attribution.md`、`llm_postmortem_notes.md`。
- 产品代码没有引用 v1 Prompt。
- 当前文章 LLM 路径在 `src/agents/data_agent/skills/extract_article_metadata.py` 中拼接三个 legacy Prompt，默认每模型最多重试 3 次并可模型降级。
- 当前 `LLMClient` 只返回 JSON 和 model，不返回 token、cost、raw text、provider response metadata 或统一 run trace。
- 当前没有 canonical Prompt registry、运行时 PromptRun repository/application service 或由 Pydantic 生成的共享 JSON Schema。
- 当前没有固定 10～15 篇 Stage 3 回归 fixture。

### 3.3 单篇文章与 UI

- canonical 表已具备 `ArticleRevision`、`PromptRun`、`ArticleStructure`、`RuleCandidate`、`RuleVersion` 和必要 traceability 字段。
- 当前 Article UI/API 以 legacy `ArticleMetadata` 版本选择为中心。
- 当前页面不完整展示原文、结构化摘要、方法标签、候选规则证据、缺失信息、可回测性、Kaipan 依赖和声明市场状态。
- 当前 legacy auto review 可把高置信度且可映射的规则直接标记 `approved`，与“自动通过仅进入待回测、只有人工审核可创建 RuleVersion”冲突。
- 当前没有 canonical RuleVersion 创建 application service。

### 3.4 批处理与后续边界

- legacy article metadata 批处理已有并发上限、分批查询和失败 checkpoint，但其身份键、持久化目标、repair 语义和正式状态不符合 Stage 3 合同。
- 作者画像 v1 Prompt 已存在，但没有 runtime 调用链。
- `llm_attribution_v1`、`llm_postmortem_notes_v1` 和策略修订 Prompt 已存在但未激活；Stage 3 只验证资产与 Schema，不启用 Stage 8/10 工作流。

## 4. 冻结合同

### 4.1 Prompt registry 与 Schema

Prompt 文件、registry/loader、Pydantic 输出模型、导出的 JSON Schema 和 regression fixture 是一个不可分割的版本化合同。

Canonical 标识：

| prompt_name / prompt_version | 路径 | schema_version | Stage 3 生产状态 |
| --- | --- | --- | --- |
| `article_analysis_v1` | `prompts/article_analysis_v1.md` | `article_analysis_v1` | active，普通文章唯一主调用 |
| `article_analysis_repair_v1` | `prompts/article_analysis_repair_v1.md` | `article_analysis_repair_v1` | conditional，最多一次 |
| `concept_extraction_v1` | `prompts/concept_extraction_v1.md` | `concept_v1` | test/special_only |
| `article_structure_extraction_v1` | `prompts/article_structure_extraction_v1.md` | `article_structure_v1` | test/special_only |
| `rule_extraction_v1` | `prompts/rule_extraction_v1.md` | `rule_v1` | test/special_only |
| `explicit_precondition_extraction_v1` | `prompts/explicit_precondition_extraction_v1.md` | `explicit_precondition_v1` | test/special_only |
| `author_method_profile_batch_v1` | `prompts/author_method_profile_batch_v1.md` | `author_method_profile_batch_v1` | batch_only，10～20 篇结构化文章 |
| `author_rule_profile_summary_v1` | `prompts/author_rule_profile_summary_v1.md` | `author_rule_profile_summary_v1` | asset_validated，Stage 7 前不启用正式画像 |
| `author_validated_profile_v1` | `prompts/author_validated_profile_v1.md` | `author_validated_profile_v1` | asset_validated，Stage 6/7 前不启用 |
| `author_profile_merge_v1` | `prompts/author_profile_merge_v1.md` | `author_profile_merge_v1` | asset_validated，Stage 7 前不启用 |
| `author_profile_revision_v1` | `prompts/author_profile_revision_v1.md` | `author_profile_revision_v1` | asset_validated，Stage 7/10 前不启用 |
| `llm_attribution_v1` | `prompts/llm_attribution_v1.md` | `llm_attribution_v1` | asset_validated，Stage 10 前不启用 |
| `strategy_revision_proposal_v1` | `prompts/strategy_revision_proposal_v1.md` | `strategy_revision_proposal_v1` | asset_validated，Stage 8/10 前不启用 |
| `llm_postmortem_notes_v1` | `prompts/llm_postmortem_notes_v1.md` | `llm_postmortem_notes_v1` | asset_validated，Stage 10 前不启用 |

规则：

- registry 是 canonical Prompt 名称、路径、版本、Schema class、状态和 ownership 的唯一事实源。
- Prompt 输出中的 `prompt_version` 必须与 registry 完全相同。
- Schema 由 Pydantic 单一事实源导出；Prompt 示例和 fixture 不得复制另一套宽松定义。
- 每次调用记录 `run_id`、`prompt_name`、`prompt_version`、`schema_name`、`schema_version`、provider、model、`input_hash`、request、raw output/raw text、validation state/errors、retry count、tokens、cost、start/end time。
- 重要结论必须保留 article revision 和 evidence reference。
- `explicit`、`inferred`、missing/unknown、program observation、human approval 必须可区分。
- 文章未声明市场状态统一保存 `not_declared`。
- LLM 不计算正式回测指标。
- raw LLM output 永远不是正式业务事实源。

### 4.2 LLM invocation

- 普通文章：恰好一个 `article_analysis_v1` 主调用。
- JSON/Schema/证据或目标字段错误：最多一个 `article_analysis_repair_v1` 定向修复调用。
- repair 只包含原文、上一结果、目标字段和 validation errors；不得重生成未指定字段。
- 网络/服务重试与 Schema repair 分离。网络重试必须有界、指数退避并记录 retry count；业务证据不足不重试。
- 相同 `input_hash + prompt_version + schema_version + model + critical parameters` 命中成功 cache，不重复计费。
- 同一身份的并发请求必须幂等，不能产生重复 PromptRun、ArticleStructure 或 RuleCandidate。
- repair 失败后进入人工处理，不允许第二次 repair 或无界模型轮换。
- 作者方法画像只接收 10～20 篇结构化文章，不接收全部全文，不逐篇调用总画像。
- attribution 只在低置信度、冲突或重要信号触发。
- postmortem notes 只按条件或每日汇总一次。

### 4.3 单篇文章

正式流程：

```text
Article + ArticleRevision
-> cleaned content
-> PromptRun
-> validated ArticleStructure
-> RuleCandidate(s)
-> deterministic automatic review
-> explicit human review
-> RuleVersion
```

必须保留和展示：

- 原文与 cleaned content，且关联 article/content revision。
- 摘要、方法标签、明确事实、LLM hypotheses、missing fields。
- 每条候选规则及 evidence。
- data dependencies、backtestability、Kaipan dependency。
- market-state status：`explicit` 或 `not_declared`；推断只在 hypotheses。
- Prompt/Schema/model/run trace。

状态边界：

- automatic pass 只表示 `pending_backtest`，不是 formally usable。
- automatic review 不得创建 RuleVersion。
- 只有明确的人类审核动作可调用 canonical Rule application service 创建 RuleVersion。
- Stage 3 创建的 RuleVersion 初始状态不得越过待回测边界。
- 不在 Stage 3 实现 fingerprint governance、RuleFamily、完整规则生命周期、正式适用性或发布。

### 4.4 Regression 与 batch

- 固定 10～15 篇代表文章后才能运行 bulk。
- 覆盖：明确规则、概念、混合、复盘、声明/未声明市场状态、模糊、Kaipan 依赖、重复、冲突和需要人工审核。
- fixture 固定 `article_id`、article revision/content hash、Prompt/Schema version、raw output、validation、automatic review、human conclusion 和 expected semantic assertions。
- 回归必须使用语义断言，不以完整文本逐字相等作为唯一标准。
- 在 fixed set 未通过前，禁止处理全部现有 100+ 篇文章。
- batch 必须 resumable、idempotent、incremental、concurrency-bounded、bounded retry，并记录 checkpoint/cursor、成功/失败/跳过和质量统计。
- 不得在一个请求中发送全部文章正文。
- 批次作者方法画像只读取 10～20 篇结构化结果。

### 4.5 Cutover 与 retirement

- new/legacy 对照只写 comparison evidence；legacy 不得写 canonical formal records。
- 新 Prompt 链成为唯一正式生产写路径后，legacy Prompt 才能从 `deprecated` 进入 `compatibility_only`。
- cutover 后 legacy Prompt 不得产生新的正式数据。
- 冻结映射：

| Legacy | New | Historical read |
| --- | --- | --- |
| `concept_extraction.md` | `article_analysis_v1` / `concept_extraction_v1` | legacy ArticleMetadata adapter |
| `rule_extraction.md` | `article_analysis_v1` / `rule_extraction_v1` | legacy RulePool/ArticleMetadata adapter |
| `precondition_extraction.md` | `article_analysis_v1` / `explicit_precondition_extraction_v1` | legacy preconditions adapter |
| `llm_attribution.md` | `llm_attribution_v1` | existing historical postmortem read |
| `llm_postmortem_notes.md` | `llm_postmortem_notes_v1` | existing historical postmortem read |

- deletion 前必须扫描 code、tests、scripts、Jobs、Workflows 和 docs，完成观察期和 rollback evidence。
- RT-S3-004 独立、最后执行；不得与 RT-S3-001 合并。

### 4.6 Later-stage boundaries

禁止在 Stage 3：

- 实现 Stage 4 fingerprint、RuleFamily、冲突治理或完整规则生命周期。
- 实现 Stage 6 回测、分市场状态表现或正式 applicability。
- 发布 Stage 7 validated author profile。
- 激活 Stage 8 strategy proposal/正式策略流程。
- 激活 Stage 10 attribution、postmortem 或每日修订流程。

Future-stage Prompt 仅允许完成 registry、Schema 和 fixture validation。

## 5. Task 顺序

| Task | 风险 | Agent 默认 | Depends on | 并行 |
| --- | --- | --- | --- | --- |
| RT-S3-001 接入版本化 Prompt 套件 | M3 | Parent 5.4，最多 1 bounded Executor | Stage 2 ACCEPTED | 否 |
| RT-S3-002 单篇文章到候选规则闭环 | M3 | Parent 5.4，最多 1 bounded Executor | RT-S3-001 accepted | 否 |
| RT-S3-003 回归样本与可恢复批处理 | M2 | Parent 5.4，最多 1 bounded Executor | RT-S3-002 accepted | 否 |
| RT-S3-004 旧 Prompt 迁移与退役 | M3 | Parent-led，最多 1 mechanical Executor | RT-S3-003 accepted + observation evidence | 否，最后 |

RT-S3-001 与 RT-S3-002 可共享一个 Parent Session，但必须严格串行、分别 Review 和接受。任何 Task 不得自动开始下一 Task。

## 6. Task Cards

### RT-S3-001 接入版本化 Prompt 套件

**Objective:** 建立 Prompt registry、单一 Pydantic Schema、可追溯调用和 canonical PromptRun/ArticleStructure/RuleCandidate 写入基础，并保证普通文章一个主调用、最多一次 repair。

**Risk:** M3。

**Prerequisites:** Stage 2 Gate accepted；canonical writer effective true；本文合同未被修改。

**Allowed paths:**

- `prompts/*_v1.md`
- `src/llm/**`
- `src/schemas/**` 或现有最接近的 canonical Schema package
- Stage 3 专用 canonical repositories/application services
- `src/models/stage2_canonical.py` 仅做不改变 DB Schema 的 mapping 使用
- Stage 3 focused tests/fixtures
- 本 Stage plan/log 和主日志

**Forbidden paths:**

- Alembic migrations、表结构和 Stage 2 frozen domain relationships
- legacy Prompt 删除
- article review UI 和 RuleVersion human approval flow
- bulk 100+ processing
- RuleFamily/fingerprint/backtest/applicability/author publication/strategy/daily flows

**Focused verification:**

```bash
../.venv/bin/python -m pytest tests/unit/llm tests/unit/schemas tests/unit/services/test_stage2_writer_routing.py -q
../.venv/bin/python -m pytest tests/unit/stage3 tests/integration/test_stage3_prompt_runtime.py -q
../.venv/bin/python -m compileall src api cli
git diff --check
```

不存在的 Stage 3 test path 应在实现时按实际落点替换并记录，不得省略对应覆盖。

**Specialized evidence:**

- registry 全量 14 项名称/路径/version/Schema/status 一致。
- normal article exactly one main call。
- targeted repair count `0..1`。
- cache identity 和 duplicate suppression。
- PromptRun trace fields 完整。
- legacy writer rejection/no dual-write。
- future-stage Prompt 未被激活。

**Completion:** RT-S3-001 自身测试、实际 diff 和日志通过；legacy Prompt 仍保留且不能成为正式写路径。

**Escalate when:** 需要改 DB Schema/migration、无法用现有 PromptRun 表表达 trace、必须引入第二 writer/Schema、v1 Prompt contract 无法在一次主调用内表达，或需要改变人工审批语义。

### RT-S3-002 单篇文章到候选规则闭环

**Objective:** 让普通用户从单篇文章查看完整分析、执行明确人工审核，并仅由该审核创建 canonical RuleVersion。

**Risk:** M3。

**Depends on:** RT-S3-001 accepted。

**Allowed paths:**

- Stage 3 article/rule application services 和 canonical repositories
- `api/routers`、`api/schemas` 中文章分析与审核接口
- `web/src/pages/articles/**`、对应 feature/API/type/test
- 直接相关 article pipeline integration
- focused backend/frontend/E2E tests
- Stage 3/main logs

**Forbidden paths:**

- legacy writer 恢复或 dual-write
- migration/DB Schema 变更，除非先 `ESCALATION_REQUIRED`
- Stage 4 fingerprint、RuleFamily、冲突工作台和完整治理
- Stage 6 回测/适用性实现
- 作者画像发布和策略流程

**Focused verification:**

```bash
../.venv/bin/python -m pytest tests/api/routers/test_articles.py tests/api/routers/ui/test_article_metadata.py tests/api/routers/test_rule_pool.py -q
../.venv/bin/python -m pytest tests/unit/stage3 tests/integration/test_stage3_single_article.py -q
pnpm test -- src/pages/articles/index.test.tsx
pnpm typecheck
git diff --check
```

前端命令从 `web/` 执行；正式日志不得记录本机绝对路径。

**Specialized evidence:**

- 原文、summary、method tags、candidate rules、evidence、missing、backtestability、Kaipan、market-state status 全部真实展示。
- loading/empty/error/partial/permission denied/unavailable 完整。
- automatic pass 显示为待回测。
- 未经 human review 不存在 RuleVersion。
- human review 通过 application service -> canonical repository 创建 RuleVersion。
- Stage 3 创建的 RuleVersion 未越过待回测边界。

**Completion:** 单篇真实数据路径和 critical E2E 通过；RT-S3-002 单独 Review/accept。

**Escalate when:** 需要改变 RuleVersion lifecycle、审批角色/权限、canonical relationship、公共 DTO 的冻结语义，或必须依赖 Stage 4/6 才能完成。

### RT-S3-003 回归样本与可恢复批处理

**Objective:** 固定 10～15 篇代表文章和期望结果，并建立只有在固定集通过后才能启动的可恢复、幂等、增量批处理。

**Risk:** M2。

**Depends on:** RT-S3-002 accepted。

**Allowed paths:**

- Stage 3 regression fixtures 和 semantic assertions
- Stage 3 batch service/job/CLI/script
- checkpoint/cursor、concurrency、retry、quality reporting
- 回归/批处理 API 或管理员运行详情的最小必要接口
- directly affected tests 和日志

**Forbidden paths:**

- Bootstrap/实施期间直接处理全部 100+ 文章
- 全文合并为单一 LLM request
- RuleFamily/fingerprint 正式实现
- per-article author total-profile call
- Stage 6 回测、Stage 7 正式画像
- legacy Prompt 删除

**Focused verification:**

```bash
../.venv/bin/python -m pytest tests/regression/stage3 tests/unit/stage3 tests/integration/test_stage3_batch.py -q
../.venv/bin/python -m cli.main stage3-regression run --fixed-set
../.venv/bin/python -m cli.main stage3-article-batch run --dry-run --limit 15
git diff --check
```

以上 CLI 名称属于本 Task 冻结的管理员接口；若现有 Typer 命名约束无法承载，必须升级而不是静默改名。

**Specialized evidence:**

- fixed set 数量 10～15 且类别覆盖完整。
- regression 未通过时 bulk gate 拒绝。
- injected failure 后 resume、重复执行 no duplicate、content version change 增量更新。
- concurrency 上限和网络 retry 上限可测试。
- 每篇一个主调用、最多一次 repair。
- 作者 batch 输入为 10～20 篇结构化文章。
- 质量统计和失败影响可见。

**Completion:** fixed set 通过；仅以 dry-run/受控小批次证明 bulk readiness，不在本 Task 自动处理全部历史文章。

**Escalate when:** 代表样本无法从现有数据确定、需要用户裁决冲突 expected outcome、checkpoint 需要新 DB Schema、幂等身份无法由冻结字段表达，或 fixed set 失败暴露 Prompt contract 问题。

### RT-S3-004 旧 Prompt 迁移与退役

**Objective:** 完成新旧对照、唯一正式写路径 cutover、兼容读取和满足条件后的 legacy Prompt 删除。

**Risk:** M3。

**Depends on:** RT-S3-003 accepted；固定集通过；新链路观察期和 rollback evidence 完整。

**Allowed paths:**

- legacy Prompt loaders/callers/tests/scripts/Jobs/Workflows/docs
- old-to-new adapter 和 historical read compatibility
- legacy Prompt 文件删除，仅在全部 deletion gate 通过后
- retirement report、Stage 3/main logs

**Forbidden paths:**

- 改变 v1 Prompt/Schema contract
- 让 legacy 和 new 同时写正式数据
- 删除历史 canonical/legacy 结果
- 跳过观察期、rollback 或 reference scan
- Stage 4+ 行为

**Focused verification:**

```bash
rg -n "concept_extraction\\.md|rule_extraction\\.md|precondition_extraction\\.md|llm_attribution\\.md|llm_postmortem_notes\\.md" src api cli scripts tests prompts docs
../.venv/bin/python -m pytest tests/regression/stage3 tests/unit/llm tests/integration/test_stage3_legacy_compatibility.py -q
../.venv/bin/python -m pytest tests/e2e/test_article_pipeline_v1.py -q
git diff --check
```

**Specialized evidence:**

- fixed set 上 new/legacy comparison 已归档。
- new chain 是唯一正式 production writer。
- legacy historical results 可读。
- code/tests/scripts/Jobs/Workflows/current docs 无使用引用。
- observation 和 rollback 验证通过。
- 若删除条件有一项未通过，只能停在 `deprecated`/`compatibility_only`，Task 与 Stage 不得完成。

**Completion:** deletion gate 全部通过并完成删除，或明确 `BLOCKED`；RT-S3-004 单独 Review。

**Escalate when:** 历史读取依赖 legacy 文件本身、删除会破坏 rollback、存在未知运行入口、需要重解释历史结果，或必须改 Stage 3 frozen contract。

## 7. Stage 3 Gate 证据

| Gate | 必须提供的证据 |
| --- | --- |
| Prompt/Schema/loader/fixture consistency | registry snapshot、Schema export test、Prompt embedded version test、fixture validation |
| Traceability | PromptRun DB assertions for version/model/hash/raw/validation/tokens/cost/run_id/time |
| Invocation count | fake provider/call ledger proving one main and at most one targeted repair |
| Fact/inference/evidence/not_declared | representative semantic assertions and UI/API payload |
| Single-article journey | real DB integration + critical E2E through human review to RuleVersion |
| Regression set | 10～15 article manifest, category coverage, expected outcomes and results |
| Recoverable batch | failure injection/resume, idempotent rerun, incremental update, concurrency/retry tests |
| No premature bulk | bulk gate rejection before regression pass; no full-history run evidence |
| Author batching | 10～20 structured inputs; no per-article total-profile call |
| Conditional later prompts | call ledger proving no unconditional attribution/postmortem |
| Single formal writer | runtime flag true, application-service scope tests, legacy rejection, no dual-write |
| Legacy retirement | mapping, reference scan, observation, rollback, historical read and deletion report |
| Backend/frontend | affected Pytest, Vitest, typecheck, static compile and API tests |
| Critical E2E | article -> analysis -> review -> RuleVersion with real persistence |
| Documentation truth | Prompt docs、plan、Stage log、main log、runtime registry and UI wording agree |
| Diff hygiene | `git status` ownership review and `git diff --check` |

## 8. Stage 3 Gate completion conditions

- RT-S3-001～004 分别 accepted。
- fixed regression set 通过。
- 真实单篇闭环可用。
- bulk readiness 可恢复、幂等、增量、有界；未在 Gate 前无控制重跑全部文章。
- new Prompt chain 是唯一正式写链。
- legacy Prompt 满足删除验收并删除；否则 Stage 3 不得完成。
- 无 Stage 4+ 越界实现。
- 日志与最终 runtime truth 一致。

## 9. Stage 级升级条件

立即返回 `ESCALATION_REQUIRED` 或 `BLOCKED`：

- Stage 2 Gate 状态被撤销，或 effective canonical writer 不再为 true。
- 发现 legacy formal writer、dual-write 或绕过 application service 的 canonical write。
- 现有 DB Schema 无法表达冻结 traceability 或单篇关系，需要 migration。
- Prompt、Schema、runtime 和 fixture 无法收敛到一个权威合同。
- human review 到 RuleVersion 的审批语义需要改变。
- fixed set expected outcome 存在无法由文档和文章证据解决的产品歧义。
- legacy deletion 缺少引用、观察期、historical read 或 rollback evidence。
- 需要引入 Stage 4/6/7/8/10 行为才能通过当前 Task。

## 10. Baseline preservation

- Bootstrap 前工作树 clean。
- 后续 Task 开始时必须重新检查 branch、HEAD、`git status` 和完整 diff。
- 用户拥有的修改不得回退、覆盖或吸收到 Stage 3 acceptance 中。
- 每个 Task 只更新当前 Stage 详细日志；主日志只更新状态、阻塞、计划路径和下一可执行 Task。
