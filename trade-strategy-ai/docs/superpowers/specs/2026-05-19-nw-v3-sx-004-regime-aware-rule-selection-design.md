# NW-V3-SX-004 Regime-aware Rule Selection Design

## 1. 目标

`NW-V3-SX-004` 的目标不是再造一套策略生成逻辑，而是把盘前策略生成收敛为一个可解释、可复现、可审计的 **Regime-aware Rule Selection** 流程。

核心目标：

1. 盘前策略生成时，必须结合当前 `Market Regime` 选择适用规则。
2. 默认剔除 `blocked_regimes` 对应的 rule。
3. `applicable_regimes` 优先，`neutral_regimes` 作为低权重补充。
4. 规则选择结果必须可解释、可复现、可回溯。
5. 不破坏原有 `StrategyVersion` 机制，不新增第二套策略事实源。

本任务服务于：

- `UI-V3-013 Regime-aware Rule Selection View`
- 盘前策略工作台
- 盘后归因与审计

---

## 2. 设计决策

### 2.1 选择策略

本任务采用 **白名单优先 + 权重排序 + neutral 兜底** 的策略：

- `applicable_regimes` 进入主候选池。
- `neutral_regimes` 可以进入候选池，但带惩罚权重。
- `blocked_regimes` 默认不进入候选池。
- 只有用户显式 override 时，blocked rule 才可进入候选池，且必须记录审计信息。

### 2.2 选择入口

不新增独立的前端选择入口，不让前端自行决定 rule。

规则选择发生在后端的盘前流程中，作为 `run-pre-market` 的内部阶段：

```text
current snapshot
  -> current market regime
  -> strategy version / rules snapshot
  -> rule applicability profiles
  -> regime rule selection
  -> selection artifact
  -> pre-market result / UI
```

### 2.3 数据存储策略

本任务不新增数据库表。

结果落地分两层：

1. **完整 selection artifact**
   - 以 JSON artifact 形式保存。
2. **摘要引用**
   - 复制到相关 `StrategyVersion.strategy_payload` 或对应 job result payload 中，便于 Web 读取和回溯。

### 2.4 可解释性要求

每条 rule 的结论必须能回答：

- 为什么被选中
- 为什么被跳过
- 为什么被阻断
- 依据来自哪些 regime / profile / strategy 版本

---

## 3. 术语

### 3.1 Regime-aware Rule Selection

基于当前 `Market Regime`、`Rule Applicability Profile`、`TraderProfile`、`StrategyVersion` 对规则进行过滤和排序的过程。

### 3.2 Selected Rule

被纳入最终盘前策略结果的规则。

### 3.3 Skipped Rule

本次被跳过，但并非 blocked 的规则，常见原因包括：

- 没有匹配 applicability profile
- 仅命中 neutral，且综合分数不足
- 样本不足
- trader profile 不匹配

### 3.4 Blocked Rule

命中 `blocked_regimes` 的规则，默认不得进入 selected rules。

### 3.5 Override

由用户显式授权的人工覆盖动作。只有在需要强制启用 blocked rule 时才允许出现。

---

## 4. 架构边界

### 4.1 新增服务

建议新增：

- `src/services/regime_rule_selection_service.py`

职责：

1. 读取当前 snapshot / regime / strategy / applicability 数据。
2. 计算规则选择结果。
3. 生成 selection artifact。
4. 返回可供策略工作台和盘后归因使用的结构化结果。

### 4.2 复用现有服务

本任务复用：

- `MarketRegimeService`
- `RuleApplicabilityService`
- `StrategyService`
- `RulePoolService`
- `StrategyVersion` / `TraderStrategyVersion`

### 4.3 不新增的内容

本任务不做：

- 不新增第二套策略版本 schema
- 不把 rule selection 放到前端执行
- 不引入 LLM 做最终规则筛选
- 不新增数据库表

---

## 5. 输入与输出契约

### 5.1 输入

规则选择至少需要以下输入：

| 输入 | 来源 | 说明 |
|---|---|---|
| `snapshot_id` | Market Snapshot | 当前交易日的唯一事实源 |
| `market_regime` | Market Regime | 当前市场状态 |
| `trader_profile` | TraderProfile | 交易员偏好与风险画像 |
| `strategy_version_id` | StrategyVersion | 当前盘前使用的策略版本 |
| `rules_snapshot` | StrategyVersion | 待选择的规则池 |
| `rule_applicability_profiles` | RuleApplicabilityProfile | 每条规则在不同 regime 下的适用性画像 |

### 5.2 输出

输出建议定义为 `RegimeRuleSelectionResult`，至少包含：

| 字段 | 说明 |
|---|---|
| `selection_id` | 规则选择记录 ID |
| `strategy_version_id` | 所属策略版本 |
| `snapshot_id` | 当前 snapshot |
| `market_regime_version` | 使用的 regime 版本 |
| `source_feature_version` | 生成 regime 时使用的 feature 版本 |
| `applicability_profile_version` | 使用的适用性画像版本 |
| `selected_rules` | 最终选中规则 |
| `skipped_rules` | 被跳过规则 |
| `blocked_rules` | 被阻断规则 |
| `selection_reason` | 整体选择原因 |
| `evidence` | 全局证据列表 |
| `override` | override 审计信息 |
| `confidence` | 整体置信度 |
| `quality_status` | `ok / partial / low_confidence` |
| `warnings` | 结构化告警 |
| `created_at` | 生成时间 |

### 5.3 Rule 级结果

每条规则建议保存以下字段：

| 字段 | 说明 |
|---|---|
| `rule_id` | 规则 ID |
| `decision` | `selected / skipped / blocked` |
| `score` | 综合分数 |
| `reason` | 可读解释 |
| `evidence` | 证据列表 |
| `regime_version` | 命中时使用的 regime 版本 |
| `applicability_profile_version` | 对应画像版本 |
| `sample_count` | 样本数 |
| `profile_confidence` | 画像置信度 |
| `override_applied` | 是否被 override |
| `rule_applicability_profile_id` | 实际命中的画像记录 ID |

---

## 6. 选择规则

### 6.1 候选池规则

1. `blocked_regimes` 默认排除。
2. `applicable_regimes` 进入主候选池。
3. `neutral_regimes` 可以进入补充候选池，但带惩罚权重。
4. 没有 profile 的规则默认进入 `skipped_rules`，原因必须明确。

### 6.2 分数模型

首版选择器应使用可解释、确定性的分数模型，不依赖 LLM。

建议综合以下因子：

- `applicability_decision`
- `profile_confidence`
- `sample_reliability`
- `regime_alignment`
- `trader_profile_match`

建议权重原则：

- `applicable` 最高
- `neutral` 次之
- `blocked` 为 0，除非 override

可采用简单的固定权重，不必上复杂模型。重点是稳定和可解释。

### 6.3 画像版本解析

如果同一条 rule 存在多个 `RuleApplicabilityProfile` 记录，选择器必须采用确定性解析顺序，避免结果漂移：

1. 优先匹配当前 `market_regime_version` 的画像。
2. 同版本下优先 `review_status = active`。
3. 其次 `review_status = reviewed`。
4. 再其次 `review_status = draft`。
5. 同状态下优先最新 `created_at`。
6. 仍然相同则按 `profile_version` / `profile_id` 做稳定兜底排序。

如果没有任何可用画像：

- 规则进入 `skipped_rules`
- `reason` 必须明确说明缺少可用 profile

### 6.4 排序规则

排序优先级建议：

1. `decision` 优先级：`applicable > neutral > skipped`
2. `score`
3. `profile_confidence`
4. `sample_count`
5. `rule_id` 作为稳定性兜底

### 6.5 Override 规则

仅允许显式 override。

override 必须记录：

- `operator`
- `reason`
- `timestamp`
- `risk_level`

override 不得隐式发生，不得只在日志里出现。

---

## 7. 总体数据流

```text
Market Snapshot
  -> Market Regime
  -> StrategyVersion / rules_snapshot
  -> RuleApplicabilityProfile
  -> RegimeRuleSelectionService
  -> RegimeRuleSelectionResult
  -> selection artifact
  -> run-pre-market result / strategy workspace / UI-V3-013
```

说明：

- selection 只负责“选什么、为什么选、为什么不选”。
- selection 不改变原始规则定义。
- selection 结果是策略运行的一部分，不是新的一套策略库。

---

## 8. 持久化与 Artifact

### 8.1 Artifact 位置

建议为 selection 结果生成独立 JSON artifact。

artifact 应至少包含：

- selection 主体
- 计算时使用的 snapshot / regime / strategy / applicability 版本
- override 审计信息
- warnings

### 8.2 写回策略版本

`StrategyVersion.strategy_payload` 仅保存摘要引用，不保存全部大对象。

建议保存：

```text
strategy_payload.regime_selection = {
  selection_id,
  snapshot_id,
  market_regime_version,
  applicability_profile_version,
  selected_rule_ids,
  blocked_rule_ids,
  artifact_ref
}
```

这样可以：

- 保留可回溯能力
- 避免把策略版本记录塞成大 JSON
- 让 Web/UI 和后续归因更容易读取

### 8.3 不新增表的原因

本次不新增表的原因：

- 现有 `StrategyVersion` / `TraderStrategyVersion` 已经能承载摘要引用
- selection 结果更像运行时 artifact，而不是长期主数据
- 避免为首版引入不必要的 schema 迁移

---

## 9. UI 暴露方式

### 9.1 UI 形态

`UI-V3-013` 应作为 Strategy Workspace 的一个明确子视图，展示 selection 结果，而不是让用户在前端手工选 rule。

页面要显示：

- selected rules
- skipped rules
- blocked rules
- selection reason
- evidence
- override 审计
- `market_regime_version`
- `applicability_profile_version`

### 9.2 UI 不做的事

- 不在前端执行选择逻辑
- 不隐藏 blocked rules
- 不提供无审计 override
- 不生成第二套规则视图

### 9.3 UI 数据来源

UI 优先读取：

1. 选择 artifact
2. 策略工作台的 job result / strategy payload 摘要
3. 必要时通过后端详情接口补充完整 artifact

---

## 10. 错误处理

### 10.1 缺失 snapshot

如果 `snapshot_id` 缺失或找不到：

- 直接返回 error
- 不做静默 fallback
- UI 应明确显示无法选择的原因

### 10.2 缺失 market regime

如果 regime 不存在：

- 返回 error
- 不允许用旧 regime 隐式替代

### 10.3 缺失 applicability profile

如果某些规则没有 profile：

- 该规则进入 `skipped_rules`
- 原因必须写明
- 不影响其他规则的选择

### 10.4 regime quality 较差

如果 regime 处于 `partial` 或 `low_confidence`：

- 允许继续选择
- 结果状态标记为 `partial` 或 `low_confidence`
- artifact 中记录 warnings

如果 regime 完全不可用，则中止。

### 10.5 override 失败

override 必须经过权限校验和审计校验：

- 无权限则拒绝
- 无 reason 则拒绝
- 无风险等级则拒绝

---

## 11. 测试策略

### 11.1 单元测试

建议新增：

- `tests/services/test_regime_rule_selection_service.py`

覆盖场景：

- `strong_bull`
- `weak_bear`
- `theme_hot`
- `blocked rule excluded`
- `neutral fallback`
- `override audit`
- `missing profile`
- `missing regime`

### 11.2 集成测试

需要验证：

- `run-pre-market` 的结果里可以拿到 selection summary
- selection artifact 可以持久化并回读
- 盘后归因可以回溯 `market_regime_version` 和 `applicability_profile_version`

### 11.3 UI 测试

`UI-V3-013` 需要覆盖：

- loading
- empty
- error
- selected/skipped/blocked 展示
- override 审计展示

---

## 12. 验收标准

本任务完成必须满足：

1. 不同 `market_regime` 下，同一 trader 可以得到不同的 rule set。
2. `blocked_regimes` 对应规则默认不会进入 `selected_rules`。
3. selection artifact 可以解释每条 rule 为什么被选择或跳过。
4. 盘后归因能回溯当时使用的 `market_regime_version` 和 `applicability_profile_version`。
5. `strong_bull / weak_bear / theme_hot` 至少三类场景有测试覆盖。
6. UI 可以展示 selected / skipped / blocked / evidence / override。
7. 不新增第二套策略事实源。

---

## 13. 兼容性与收口

### 13.1 保留原有策略版本机制

本任务不改变 `StrategyVersion` 作为策略版本主记录的角色。

### 13.2 不删除旧链路

现有 `strategy-build`、`run-pre-market`、`run-after-close` 保留。

本任务只是把盘前规则选择收敛进 `run-pre-market` 的内部流程。

### 13.3 未来扩展

如果后续要做更复杂的调参或候选集扩展，可以在本设计之上加：

- selection override 工作流
- 历史聚合 profile 的二级加权
- 更细粒度的 rule ranking report

但这些不属于首版必须项。

---

## 14. 结论

首版 `NW-V3-SX-004` 的正确实现方式是：

**在盘前策略流程中，以当前 Market Regime 和 Rule Applicability Profile 为依据，对原始 rules_snapshot 做可解释、可审计的过滤和排序，默认剔除 blocked，applicable 优先，neutral 低权重补充，并把结果输出为 selection artifact。**
