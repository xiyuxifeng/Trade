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
- [Stage 8 日志](refactor-implementation-logs/stage-8.md)
- [Stage 9 日志](refactor-implementation-logs/stage-9.md)

## 当前状态

- 当前 Stage：`Stage 9 每日盘前`
- Stage 状态：`[-] 进行中`
- 当前已接受 Task：`RT-S7-004 画像版本与时间分段`、`RT-S7-001 作者方法画像`、`RT-S7-002 作者规则画像`、`RT-S7-003 作者验证画像`、`RT-S8-001 策略草稿与发布`、`RT-S8-002 策略验证和回滚`、`RT-S8-003 策略优化建议`、`RT-S9-001 自动前置检查`、`RT-S9-002 每日规则选择`
- 当前已接受 Stage Bootstrap：`Stage 8 Bootstrap`、`Stage 9 Bootstrap`
- 当前未开始 Task：`RT-S9-003 每日策略实例和盘前计划`
- 当前计划：[Stage 9 实施计划](refactor-implementation-plans/stage-9-implementation-plan.md)
- 详细日志：[Stage 9](refactor-implementation-logs/stage-9.md)
- 下一步：仅可在用户明确授权后开始 `RT-S9-003 每日策略实例和盘前计划`；不得自动启动 Stage 10。

## 当前硬约束

- 后续 Task 不得自动开始；每个 Stage / Task / Gate 都需要用户明确授权。
- legacy internal tooling / Job / Workflow / Pipeline / Artifact / file JSON / `config_path` / live Provider / mutable latest records 不得成为后续 Stage 的 formal data input。
- Stage 6 formal backtest 和 rule applicability 只能消费 canonical DatasetSnapshot、MarketSnapshot、BacktestRun、BacktestResult、RuleApplicabilityProfile 及其 immutable IDs/fingerprints/versions/provenance/availability timestamps。
- Stage 7 正式作者画像分为：`AuthorMethodProfile`、`AuthorRuleProfile`、`AuthorValidatedProfile`。
- Stage 7 三类作者画像必须共享版本、生命周期、审核、审计、证据指纹、画像指纹、supersession 和时间分段规则。
- 正式作者验证画像只能消费 formal `RuleApplicabilityProfile`、formal `BacktestRun`、formal `BacktestResult` 和 Stage 6 level/市场状态/sample evidence。
- 新证据只能生成草稿/修订，不得自动覆盖已发布画像。
- Formal Stage 8 strategy source-of-truth is canonical `StrategyVersion` in `strategy_versions`, scoped by canonical `Strategy` in `strategies`; `TraderStrategyVersion` is compatibility-only.
- Formal Stage 8 strategy contents must include rule pool, rule base weights, author profile versions, risk policy, position constraints, target universe, market-state selection policy, degradation policy and evidence bindings.
- `StrategyVersion` is not regenerated daily.
- `DailyStrategyInstance` is runtime-only and cannot become a formal strategy.
- `StrategyRevisionProposal` is proposal-only and cannot directly modify a published/current strategy.
- Only one current strategy per strategy scope unless a later explicit contract changes the scope rule.
- Rollback must create/audit a version transition and cannot silently mutate history.
- Stage 9 Bootstrap 已冻结：`DailyRuleSelection` 是每日规则选择输出，不是正式策略；`DailyStrategyInstance` 是运行时对象，不是 `StrategyVersion`；`TradingDayPlan` 是用户可见每日计划。
- Stage 9 current formal strategy must be read from canonical `Strategy.current_published_version_id` and its `StrategyVersion` / `StrategyRuleMembership` records.
- Stage 9 formal inputs must be canonical `DatasetSnapshot`、`MarketSnapshot`、`BacktestRun`、`BacktestResult`、`RuleApplicabilityProfile`、`AuthorProfileVersion` and validated data-quality state.
- Stage 9 formal flow must not consume legacy Job / Workflow / Pipeline / Artifact / file JSON / `config_path` / live Provider / mutable latest records / legacy strategy service / legacy backtest service / `strategy-studio` / `optimize` / compatibility views.
- Stage 9 must not modify `StrategyVersion`、published/current strategy pointers、author profiles、rule versions、rule applicability profiles or proposal status.
- `AI-Conversation-Project-Constraints.md` 单文件不存在；当前权威约束以 `AI-Conversation-Project-Constraints-1.md` 和 `AI-Conversation-Project-Constraints-2.md` 为准。

## 当前残余风险

- Stage 8 Gate 最终 `ACCEPTED`；`RT-S8-001/002/003` 已接受，策略中心 Stage 已完成。
- Stage 9 Bootstrap 最终 `READY`；`RT-S9-001/002` 已接受，`RT-S9-003` 尚未实现，未生成每日策略实例或盘前计划。
- `RT-S9-001` 已建立 formal pre-market readiness repository/service/API/client/page；`RT-S9-002` 已建立 formal daily rule selection repository/service/API/client/UI；`RT-S9-003` 仍未实现。
- `RT-S7-004/001/002/003` 的来源版本绑定仍为 JSON 字段并由服务层约束，不是 FK 明细表；Stage 7 Gate 判定为当前 frozen contract 下可接受，后续可作为 hardening 评估。
- `RT-S7-001` 的结构化文章来源绑定仍为 JSON source bindings 加 `prompt_run_id`，不是独立明细表；这是在 frozen Stage 7 contract 下避免第二 formal source 的折中。
- 当前最小正式生命周期为 `draft/pending_review/published/archived`，支持 diff 和 supersession metadata；`rejected/invalidated/superseded` 显式操作与更强前端审核工作流记录为后续 hardening，不阻塞 Stage 8。
- legacy `/backtest*`、`/backtest_results`、legacy `BacktestService`、`SnapshotLoader`、raw jobs、pipeline specs 和 legacy profile UI 仍为 compatibility-only；formal `/rules/*` 与 Stage 7 formal author profiles 不得使用它们作为正式事实源。
- `RT-S8-001/002/003` 已建立 canonical strategy repository/service/API/UI、验证摘要、当前版对比、版本 diff、审计回滚、proposal-only strategy revision surface 和当前指针安全切换；Gate 修复后发布/current 必须先通过正式验证。
- `/strategies/candidates` 仍为 compatibility notice page，后续退役工作未完成。
- Stage 8 未运行浏览器级 E2E；Gate 判定为非阻塞，当前依赖 focused API/frontend/OpenAPI/typecheck/migration verification。
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
| RT-S7-002 | `[x]` | reviewed RuleVersion / RuleFamily 生成 formal AuthorRuleProfile draft 已接受 | [Stage 7](refactor-implementation-logs/stage-7.md) |
| RT-S7-003 | `[x]` | formal Stage 6 validation evidence 生成 AuthorValidatedProfile draft 已接受 | [Stage 7](refactor-implementation-logs/stage-7.md) |
| Stage 8 Bootstrap | `[x]` | Stage 8 strategy contracts 和 task order 已冻结 | [Stage 8](refactor-implementation-logs/stage-8.md) |
| RT-S8-001 | `[x]` | canonical draft/review/publish foundation、正式策略中心、migration 和 focused verification 已接受 | [Stage 8](refactor-implementation-logs/stage-8.md) |
| RT-S8-002 | `[x]` | canonical validation summary、current-vs-candidate comparison、version diff、audited rollback 和 focused verification 已接受 | [Stage 8](refactor-implementation-logs/stage-8.md) |
| RT-S8-003 | `[x]` | canonical proposal service/API/UI、accept-to-draft traceability 和 focused verification 已接受 | [Stage 8](refactor-implementation-logs/stage-8.md) |
| Stage 9 Bootstrap | `[x]` | Stage 9 pre-market contracts 和 task order 已冻结 | [Stage 9](refactor-implementation-logs/stage-9.md) |
| RT-S9-001 | `[x]` | formal pre-market readiness check、正式 API/UI 和 focused verification 已接受 | [Stage 9](refactor-implementation-logs/stage-9.md) |
| RT-S9-002 | `[x]` | formal daily rule selection、traceability、正式 API/UI 和 focused verification 已接受 | [Stage 9](refactor-implementation-logs/stage-9.md) |
| RT-S9-003 | `[ ]` | 每日策略实例和盘前计划未开始 | [Stage 9](refactor-implementation-logs/stage-9.md) |

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
| Stage 7 | `[x]` | Gate 最终 `ACCEPTED` | [stage-7.md](refactor-implementation-logs/stage-7.md) |
| Stage 8 | `[x]` | Gate 最终 `ACCEPTED` | [stage-8.md](refactor-implementation-logs/stage-8.md) |
| Stage 9 | `[-]` | `RT-S9-001/002 ACCEPTED`；`RT-S9-003` 未开始 | [stage-9.md](refactor-implementation-logs/stage-9.md) |

## 下一步建议

建议下一次用户明确授权后开始：

```text
RT-S9-003 每日策略实例和盘前计划
```

执行前应读取：

- [Stage 9 实施计划](refactor-implementation-plans/stage-9-implementation-plan.md)
- [Stage 9 日志](refactor-implementation-logs/stage-9.md)
- 本文件的“当前硬约束”和“当前残余风险”

不得自动开始 `RT-S9-003` 实现；必须等待用户明确授权，且不得启动 Stage 10。
