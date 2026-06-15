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
