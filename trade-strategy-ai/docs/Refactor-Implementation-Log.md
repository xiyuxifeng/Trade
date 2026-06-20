# Trade Strategy AI 重构实施状态

本文件是重构工作的**当前状态总入口**，只保存当前状态、下一步、硬约束、仍有效风险、Task/Stage 索引和详细日志链接。

详细历史、测试输出、迁移证据、修复记录和 Task 级实施细节请查看：

- [重构实施日志目录](refactor-implementation-logs/README.md)
- [Stage 0 日志](refactor-implementation-logs/stage-0.md)
- [Stage 1 日志](refactor-implementation-logs/stage-1.md)
- [Stage 2 日志](refactor-implementation-logs/stage-2.md)
- [Stage 3 日志](refactor-implementation-logs/stage-3.md)
- [Stage 4 日志](refactor-implementation-logs/stage-4.md)
- [Stage 5 日志](refactor-implementation-logs/stage-5.md)
- [Stage 6 日志](refactor-implementation-logs/stage-6.md)
- [Stage 7 日志](refactor-implementation-logs/stage-7.md)

## 当前状态

- 当前 Stage：`Stage 7 作者画像`
- Stage 状态：`[-] 进行中`
- 当前已接受 Task：`RT-S7-004 画像版本与时间分段`、`RT-S7-001 作者方法画像`
- 当前未开始 Task：`RT-S7-002 作者规则画像`、`RT-S7-003 作者验证画像`
- 当前计划：[Stage 7 实施计划](refactor-implementation-plans/stage-7-implementation-plan.md)
- 详细日志：[Stage 7](refactor-implementation-logs/stage-7.md)
- 下一步：可开始 `RT-S7-002 作者规则画像`；不得自动开始，需用户明确授权。

## 当前硬约束

- 后续 Task 不得自动开始；每个 Stage / Task / Gate 都需要用户明确授权。
- legacy internal tooling / Job / Workflow / Pipeline / Artifact / file JSON / `config_path` / live Provider / mutable latest records 不得成为后续 Stage 的 formal data input。
- Stage 6 formal backtest 和 rule applicability 只能消费 canonical DatasetSnapshot、MarketSnapshot、BacktestRun、BacktestResult、RuleApplicabilityProfile 及其 immutable IDs/fingerprints/versions/provenance/availability timestamps。
- Stage 7 正式作者画像分为：`AuthorMethodProfile`、`AuthorRuleProfile`、`AuthorValidatedProfile`。
- Stage 7 三类作者画像必须共享版本、生命周期、审核、审计、证据指纹、画像指纹、supersession 和时间分段规则。
- 正式作者验证画像只能消费 formal `RuleApplicabilityProfile`、formal `BacktestRun`、formal `BacktestResult` 和 Stage 6 level/市场状态/sample evidence。
- 新证据只能生成草稿/修订，不得自动覆盖已发布画像。
- `RT-S7-004` 已先行冻结版本、生命周期、审核、审计和时间分段合同；后续 `RT-S7-001/002/003` 必须复用该 foundation。
- `AI-Conversation-Project-Constraints.md` 单文件不存在；当前权威约束以 `AI-Conversation-Project-Constraints-1.md` 和 `AI-Conversation-Project-Constraints-2.md` 为准。

## 当前残余风险

- Stage 7 仍未完成作者规则画像、作者验证画像和 Stage 7 Gate。
- `RT-S7-004` 的来源版本绑定仍为 JSON 字段并由服务层约束，不是 FK 明细表；这是 frozen RT-S7-004 范围内的折中。完成 `RT-S7-001/002/003` 后可再评估是否需要独立明细表。
- `RT-S7-001` 的结构化文章来源绑定仍为 JSON source bindings 加 `prompt_run_id`，不是独立明细表；这是在 frozen Stage 7 contract 下避免第二 formal source 的折中。
- `RT-S7-004` 未扩展 `invalidated` 生命周期；当前最小正式生命周期为 `draft/review-pending/published/archived`。如后续 Task 需要失效语义，应在新 Task 中显式设计。
- legacy `/backtest*`、`/backtest_results`、legacy `BacktestService`、`SnapshotLoader`、raw jobs、pipeline specs 和 legacy profile UI 仍为 compatibility-only；formal `/rules/*` 与 Stage 7 formal author profiles 不得使用它们作为正式事实源。
- UI 视觉一致性、非关键响应式细节和文案润色进入 backlog，不阻塞当前 Stage。

## Task 状态索引

| Task | 状态 | 简短结论 | 详细记录 |
| --- | --- | --- | --- |
| RT-S0-001 | `[x]` | 现状审计已接受 | [Stage 0](refactor-implementation-logs/stage-0.md) |
| RT-S0-002 | `[x]` | 迁移矩阵已接受 | [Stage 0](refactor-implementation-logs/stage-0.md) |
| RT-S1-001 | `[x]` | 导航和路由实现已接受 | [Stage 1](refactor-implementation-logs/stage-1.md) |
| RT-S1-002 | `[x]` | 统一页面体验和真实能力接入已接受 | [Stage 1](refactor-implementation-logs/stage-1.md) |
| RT-S1-003 | `[x]` | 首页实现已接受 | [Stage 1](refactor-implementation-logs/stage-1.md) |
| RT-S2-001 | `[x]` | canonical domain contracts 已接受 | [Stage 2](refactor-implementation-logs/stage-2.md) |
| RT-S2-002 | `[x]` | schema convergence 和 migration/recovery 已接受 | [Stage 2](refactor-implementation-logs/stage-2.md) |
| RT-S2-003 | `[x]` | canonical writer routing 与 legacy write rejection 已接受 | [Stage 2](refactor-implementation-logs/stage-2.md) |
| RT-S3-001 | `[x]` | versioned Prompt registry 与 canonical persistence foundation 已接受 | [Stage 3](refactor-implementation-logs/stage-3.md) |
| RT-S3-002 | `[x]` | provenance repair 已接受 | [Stage 3](refactor-implementation-logs/stage-3.md) |
| RT-S3-003 | `[x]` | fixed regression set 和 recoverable dry-run batch 已接受 | [Stage 3](refactor-implementation-logs/stage-3.md) |
| RT-S3-004 | `[x]` | legacy Prompt migration / retirement 已接受 | [Stage 3](refactor-implementation-logs/stage-3.md) |
| RT-S4-001 | `[x]` | automatic review 与 human-review workbench 已接受 | [Stage 4](refactor-implementation-logs/stage-4.md) |
| RT-S4-002 | `[x]` | fingerprint/family/runtime 与 duplicate/conflict detection 已接受 | [Stage 4](refactor-implementation-logs/stage-4.md) |
| RT-S4-003 | `[x]` | canonical rule lifecycle 已接受 | [Stage 4](refactor-implementation-logs/stage-4.md) |
| Stage 5 Bootstrap | `[x]` | Stage 5 data contracts 和 task order 已冻结 | [Stage 5](refactor-implementation-logs/stage-5.md) |
| RT-S5-001 | `[x]` | OHLCV DatasetSnapshot canonical contract 已接受 | [Stage 5](refactor-implementation-logs/stage-5.md) |
| RT-S5-002 | `[x]` | Kaipan/MarketSnapshot canonical contract 已接受 | [Stage 5](refactor-implementation-logs/stage-5.md) |
| RT-S5-003 | `[x]` | 系统管理数据与调度门面已接受 | [Stage 5](refactor-implementation-logs/stage-5.md) |
| Stage 6 Bootstrap | `[x]` | Stage 6 backtest/applicability contracts 已冻结 | [Stage 6](refactor-implementation-logs/stage-6.md) |
| RT-S6-001 | `[x]` | formal backtest workbench foundation 已接受 | [Stage 6](refactor-implementation-logs/stage-6.md) |
| RT-S6-002 | `[x]` | point-in-time market-state results 已接受 | [Stage 6](refactor-implementation-logs/stage-6.md) |
| RT-S6-003 | `[x]` | RuleApplicabilityProfile 草稿/版本和审核已接受 | [Stage 6](refactor-implementation-logs/stage-6.md) |
| RT-S6-004 | `[x]` | Level 1/2/3 backtest levels 已接受 | [Stage 6](refactor-implementation-logs/stage-6.md) |
| Stage 7 Bootstrap | `[x]` | Stage 7 author profile contracts 和 task order 已冻结 | [Stage 7](refactor-implementation-logs/stage-7.md) |
| RT-S7-004 | `[x]` | 作者画像版本、生命周期、审核审计和时间分段 foundation 已接受 | [Stage 7](refactor-implementation-logs/stage-7.md) |
| RT-S7-001 | `[x]` | 结构化文章批次生成 formal AuthorMethodProfile draft 已接受 | [Stage 7](refactor-implementation-logs/stage-7.md) |
| RT-S7-002 | `[ ]` | 未开始 | [Stage 7](refactor-implementation-logs/stage-7.md) |
| RT-S7-003 | `[ ]` | 未开始 | [Stage 7](refactor-implementation-logs/stage-7.md) |

## Stage 状态索引

| Stage | 状态 | 结论 | 详细记录 |
| --- | --- | --- | --- |
| Stage 0 | `[x]` | 已完成并接受 | [stage-0.md](refactor-implementation-logs/stage-0.md) |
| Stage 1 | `[x]` | 功能、契约、自动验证和用户 UI 检查已接受 | [stage-1.md](refactor-implementation-logs/stage-1.md) |
| Stage 2 | `[x]` | Gate 最终 `ACCEPTED` | [stage-2.md](refactor-implementation-logs/stage-2.md) |
| Stage 3 | `[x]` | Gate 最终 `ACCEPTED` | [stage-3.md](refactor-implementation-logs/stage-3.md) |
| Stage 4 | `[x]` | Gate 最终 `ACCEPTED` | [stage-4.md](refactor-implementation-logs/stage-4.md) |
| Stage 5 | `[x]` | Gate 最终 `ACCEPTED` | [stage-5.md](refactor-implementation-logs/stage-5.md) |
| Stage 6 | `[x]` | Gate 最终 `ACCEPTED` | [stage-6.md](refactor-implementation-logs/stage-6.md) |
| Stage 7 | `[-]` | `RT-S7-004`、`RT-S7-001` 已接受；`RT-S7-002/003` 和 Stage 7 Gate 未开始 | [stage-7.md](refactor-implementation-logs/stage-7.md) |

## 下一步建议

建议下一次用户明确授权后开始：

```text
RT-S7-002 作者规则画像
```

执行前应读取：

- [Stage 7 实施计划](refactor-implementation-plans/stage-7-implementation-plan.md)
- [Stage 7 日志](refactor-implementation-logs/stage-7.md)
- 本文件的“当前硬约束”和“当前残余风险”

不得跳过 `RT-S7-002` 直接实现 `RT-S7-003` 或 Stage 7 Gate，除非用户明确重新冻结 Stage 7 task order。
