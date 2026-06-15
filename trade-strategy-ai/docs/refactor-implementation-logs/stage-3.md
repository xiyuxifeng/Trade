# Stage 3 Prompt 与文章处理链路实施日志

## 当前状态

- Stage：`Stage 3 Prompt 与文章处理链路`
- 状态：`[-] 进行中`
- 当前活动：Bootstrap 与合同冻结完成，未实施任何 Stage 3 Task。
- 下一可执行 Task：`RT-S3-001 接入版本化 Prompt 套件`
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
