# New Web Rule Applicability Profile

## 1. 目标

`Rule Applicability Profile` 用于描述“某条 rule 在什么市场环境下更适用、在哪些市场环境下应避免使用”。

首版实现原则：

- 以单次 `Regime-aware Backtest` 结果为事实源
- 保持可解释、可版本化、可回溯
- 不覆盖原始 rule 定义
- 不把适用性写成人工主观标签

## 2. 数据事实源

首版 profile 只消费单次回测结果中的 `rule_regime_metrics`。

输入最少需要：

- `rule_id`
- `source_backtest_id`
- `profile_version`
- `min_sample_count`
- regime metrics 列表

其中 regime metrics 至少包含：

- `regime_label`
- `sample_count`
- `win_rate`
- `avg_return`
- `max_drawdown`
- `profit_factor`
- `confidence`

## 3. 字段定义

### 3.1 主对象 `RuleApplicabilityProfile`

- `profile_id`：主键
- `rule_id`：规则 ID
- `profile_version`：画像版本
- `source_backtest_id`：事实源回测结果 ID
- `source_rule_version`：预留字段，首版可为空
- `market_regime_version`：回测引用的 regime 版本
- `source_feature_version`：回测引用的 feature 版本
- `review_status`：`draft / reviewed / active / archived`
- `min_sample_count`：样本阈值
- `confidence`：画像整体置信度
- `applicable_regimes[]`：适用环境
- `blocked_regimes[]`：禁用环境
- `neutral_regimes[]`：中性环境
- `best_market_conditions`：最佳环境摘要
- `worst_market_conditions`：最差环境摘要
- `summary`：聚合摘要
- `storage_ref`：存储引用
- `reviewed_by` / `reviewed_at`：审核信息

### 3.2 regime 明细记录

每个 regime 记录至少包含：

- `regime_label`
- `decision`
- `score`
- `sample_count`
- `win_rate`
- `avg_return`
- `avg_win_return`
- `avg_loss_return`
- `max_drawdown`
- `profit_factor`
- `confidence`
- `low_sample`
- `reason`
- `evidence[]`

## 4. 规则设计

### 4.1 首版分类逻辑

每个 regime metric 先计算一个综合分数，再分类为：

- `applicable`
- `blocked`
- `neutral`

判定原则：

- `sample_count < min_sample_count` 时，默认保留为 `neutral`
- 综合表现明显偏强时进入 `applicable`
- 综合表现明显偏弱时进入 `blocked`
- 接近均衡时进入 `neutral`

### 4.2 分数计算口径

首版综合分数由以下因素构成：

- `win_rate`
- `avg_return`
- `profit_factor`
- `max_drawdown`
- `sample_count`
- `confidence`

要求：

- 分数必须可解释
- 不引入黑盒模型
- 每条 regime 记录都要带证据说明

### 4.3 置信度

整体 `confidence` 不应该只看单条 regime，而要结合：

- 有效样本覆盖率
- 各 regime 的样本质量
- 应用 / 禁用 / 中性分布是否过于单一

## 5. API / UI 约定

### 5.1 API

首版支持：

- 列出指定 rule 的 profiles
- 查看单个 profile
- 从 backtest 结果生成 profile
- 更新 review status

### 5.2 UI

Rule Pool 页面需要展示：

- profile version
- source_backtest_id
- review status
- confidence
- applicable_regimes
- blocked_regimes
- neutral_regimes
- best_market_conditions
- worst_market_conditions

并支持：

- 从规则详情页生成 profile
- 标记 reviewed / active / archived

## 6. 版本扩展

首版只做单次 profile。

后续扩展任务 `NW-V3-SX-003A` 预留聚合画像能力：

- 多个历史 profile 聚合
- 保留来源 backtest 追踪
- 不覆盖单次 profile 的可复现性

## 7. 验收边界

首版完成后，必须满足：

- 可以基于指定回测结果生成 profile
- 可以在 Web UI 中查看适用 / 禁用 / 中性环境
- blocked_regimes 必须有证据
- profile 修改不影响历史 backtest result

