# Stage Gate 有界自动修复补充协议

> 本文档用于补充 `AI-Conversation-Templates.md` 中的 Stage Gate Review 规则。
> 在后续整理主模板时，应将本协议合并进 `11.6 Parent 5.5：Stage Gate Review`，并同步调整升级门禁。

## 1. 目的

Stage Gate 不应因为可在冻结契约内修复的实现缺陷而立即结束。

Gate 应执行：

```text
Review
→ 分类发现
→ 有界修复
→ 重跑受影响证据
→ 完整 Re-Review
→ 最终 Gate 决策
```

该机制不放宽验收标准，也不取消合同级升级门禁。

## 2. 发现分类

### 2.1 AUTO_REPAIRABLE

在冻结契约内可修复的问题，包括：

- 普通实现 Bug；
- repository、adapter、application-service routing 缺陷；
- 已冻结字段、FK、索引、约束或 metadata 的漏实现；
- 测试、验证、backup manifest 或日志缺失；
- 文档与运行事实不一致，但正确事实明确；
- legacy writer 未按既定 single-writer 合同被限制；
- feature flag 或 cutover guard 已冻结但未真正接入运行路径；
- 不需要改变正式事实源、Schema 设计或数据解释的兼容修复。

### 2.2 CONTRACT_SENSITIVE

必须停止并输出 `ESCALATION_REQUIRED` 的问题，包括：

- 需要改变冻结的核心对象、稳定 ID、版本关系或生命周期；
- 需要重新设计 Schema 或 migration 策略；
- 需要重新决定正式事实源、writer ownership 或是否允许 dual-write；
- 需要重新解释历史数据、正式状态或人工审批语义；
- 需要破坏性迁移，且原 rollback/recovery 合同不足；
- 只能跨 Stage 或引入后续 Stage 行为才能解决；
- 修复会形成第二套正式 Schema、事实源、writer 或 Alembic branch。

## 3. Single-writer 判断规则

发现多个写入入口时，不得机械地全部升级。

### 可自动修复

当冻结合同已经明确：

```text
Application Service
→ canonical repository
→ PostgreSQL
```

而实际代码只是没有落实该合同，例如：

- legacy writer 仍可写；
- router、CLI、Job、Workflow 绕过 application service；
- cutover flag 只记录报告，没有控制实际 writer；
- repository guard 或测试缺失。

这些属于冻结合同内的实现缺陷，应归类为 `AUTO_REPAIRABLE`。

### 必须升级

只有在以下情况才升级：

- 冻结合同未明确唯一 writer；
- 现有业务必须保留多个正式 writer；
- 修复要求修改 writer ownership、cutover 模型或 dual-write 规则；
- 单一 writer 无法满足现有 Schema、运行或恢复要求。

## 4. Gate 修复循环

发现 `AUTO_REPAIRABLE` 问题后，Parent 5.5 必须：

1. 标注问题所属 Task；
2. 创建内部有界 Repair Task Card；
3. 保持冻结合同不变；
4. 实施最小修复；
5. 检查完整 repair diff；
6. 重跑直接受影响测试和专项验证；
7. 重新运行被修复影响的 Gate 证据；
8. 更新 Stage 日志和主实施日志；
9. 从修复后的最终状态重新执行完整 Stage Gate Review。

Repair Task Card 至少包含：

```text
Owning Task
Finding and evidence
Root cause
Frozen contracts
Allowed paths
Forbidden paths
Exact repair
Focused tests
Specialized verification
Completion conditions
Stop / escalation conditions
```

不得因为仍有可执行修复项而只返回 handoff。

以下情况不是停止理由：

- 测试失败但原因已定位且可修；
- 代码漏实现；
- migration、adapter、repository 或 guard 不完整；
- 日志或文档错误；
- 需要补跑当前环境可执行的验证。

修复循环持续到：

1. 所有 Gate 条件通过；或
2. 只剩明确、不阻塞下一 Stage 的外部证据限制；或
3. 命中 `CONTRACT_SENSITIVE`、真实外部 blocker 或升级条件。

## 5. 委派限制

- final Gate 判断不得委派；
- Parent 5.5 负责问题分类、修复范围、合同合规、最终 diff 和验收；
- 最多使用一个 mini Executor 处理机械且不重叠的修复；
- 不允许多个 writer 同时修改 ORM、migration chain、migration state 或 canonical contract；
- 不委派 writer ownership、事实源或数据解释决定。

## 6. 修复后的证据规则

最终 Gate 决策必须基于修复后的代码、数据库和日志状态。

修复前证据只有在以下条件全部满足时才能复用：

- 修复未影响对应代码路径或数据结构；
- fixture、Schema、migration 和运行配置未变化；
- 证据仍覆盖最终 diff；
- 日志明确说明复用原因。

否则必须重跑。

## 7. 最终决策

### ACCEPTED

- 所有 material findings 已修复并重新验证；
- Stage 出口条件全部通过；
- 无未解决合同级风险；
- 日志与运行事实一致；
- 下一 Stage 可以开始。

### CONDITIONAL

仅用于：

- 剩余项依赖当前环境不可获得的外部证据；
- 剩余项不影响架构、数据完整性、迁移安全或下一 Stage；
- 必须列明限制、责任和下一 Stage 是否仍被阻塞。

不得仅因为仍有可修复实现工作而返回 `CONDITIONAL`。

### BLOCKED

- 修复失败；
- material implementation defect 仍存在；
- 数据完整性、兼容、恢复或 writer enforcement 仍不满足；
- 下一 Stage 不得开始。

### ESCALATION_REQUIRED

仅当必须改变冻结合同或需要新的高风险决策时使用。

## 8. 推荐输出

```text
- Gate delegation decision
- verified repository/database/runtime facts
- initial findings by severity and classification
- repairs performed by owning Task
- files changed
- frozen-contract compliance
- exact post-repair verification results
- remaining findings or ESCALATION_REQUIRED
- final Gate decision
- whether the next Stage may begin
- logs/documents updated
- concise handoff
```
