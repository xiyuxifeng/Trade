# Article Review Relaxation Strategy Design

## Purpose

当前文章链路里，候选规则大量落入人工审核，主要原因不是单点故障，而是抽取层和审核层都对 `ambiguous_terms`、`missing_fields`、`manual_review_required` 和非 `executable` 状态采取了保守策略。

本设计只定义“如何放宽人工分流”，目标是先把人工量从 400+ 压下来，同时保留真正高风险规则的人工门禁。

## Current State

现有链路分两层：

1. 抽取层把文章结构化为规则候选，并保留 `quantification.status`、`missing_fields`、`ambiguous_terms`、`manual_review_required`。
2. 审核层根据这些字段把候选规则分流为待回测、需要人工确认、建议拒绝。

当前行为偏保守：

- `ambiguous_terms` 只要非空，通常就会进入人工。
- `manual_review_required = true` 会直接推动人工。
- `backtestability_status != executable` 也会进入人工。

数据库样本显示，当前大量规则都卡在 `partially_executable` 和 `needs_human_review`。

## Design Goal

把人工审核从“硬门禁”改成“分层门禁”：

- 真正缺信息、不可回测、冲突、依赖高风险数据的规则继续人工。
- 只有轻度语义模糊、但条件和动作完整的规则，可以自动进入待回测。

## Recommended Policy

### 1. Keep hard gates

以下情况仍然必须人工或直接拒绝：

- 原文证据缺失
- 规则条件缺失
- 规则动作缺失
- `backtestability_status = not_executable`
- 需要补核心参数，例如止损、止盈、仓位、明确阈值
- 依赖 Kaipan 数据且没有替代验证路径
- 规则冲突、重复、相近但不可区分
- 人工编辑过的规则回写后存在不一致风险

### 2. Split ambiguous terms into two buckets

将 `ambiguous_terms` 拆分为两档：

- `light_ambiguous_terms`
- `heavy_ambiguous_terms`

建议放行的轻度模糊词包括：

- `强势`
- `明显放量`
- `企稳`
- `附近`
- `偏强`
- `博弈`

建议继续拦截的重度模糊词包括：

- 涉及止损边界但没有数值
- 涉及止盈边界但没有数值
- 涉及仓位但没有数值
- 涉及市场状态依赖但没有明确条件
- 依赖主观判断才能执行的表达

### 3. Reclassify review outcomes

建议将自动审核结果改成三类：

- `pending_backtest`：可直接进入待回测
- `needs_human_review`：保留人工，但仅用于强风险项
- `suggested_reject`：信息不足或明显不可执行

其中 `ambiguous_terms` 只要属于轻度模糊词，就不应单独触发 `needs_human_review`。

### 4. Preserve uncertainty, do not hide it

即使放行，也不要删除 `ambiguous_terms`。

正确做法是：

- 继续保留字段
- 在 UI 中显示“含轻度模糊词”
- 只是不再把它当成人工门禁

这样可以保留可追溯性，也方便后续回看误判样本。

## Policy Table

| Condition | Result | Reason |
| --- | --- | --- |
| evidence/condition/action 缺失 | `suggested_reject` | 不可执行 |
| `backtestability_status = not_executable` | 人工或拒绝 | 不能回测 |
| 轻度 `ambiguous_terms`，其余完整 | `pending_backtest` | 允许自动放行 |
| 重度 `ambiguous_terms` | `needs_human_review` | 仍需确认 |
| `missing_fields` 涉及核心参数 | `needs_human_review` | 需要补量化定义 |
| Kaipan 依赖 | `needs_human_review` | 外部数据门槛高 |
| 规则冲突/重复/相近但不清晰 | `needs_human_review` | 避免错误合并 |

## Impact on Backtest

放宽后不会改变回测引擎本身的计算公式，但会改变哪些规则能进入回测队列。

正面影响：

- 待回测数量会增加
- 人工处理压力会下降
- 更多规则可以尽快得到统计结果

负面影响：

- 回测集合会包含更多语义不够硬的规则
- 某些结果的可复现性会下降
- 可能引入更高的假阳性

因此，放宽只适合在“条件和动作完整”的前提下使用，不能把所有 `ambiguous_terms` 一刀切放掉。

## Re-extraction Rule

如果只改审核层，不需要重新提取。

如果改 prompt 或抽取规则，必须重新提取，并且建议同步升级 prompt 版本，避免旧缓存继续命中。

## Implementation Scope

这次策略落地建议只改以下两个层：

- 审核层分类逻辑
- UI 展示文案和状态说明

暂不建议同时改：

- 回测引擎
- 数据模型大改
- 文章抽取 prompt 的语义边界

## Verification Plan

验证必须覆盖三件事：

1. 人工数量是否显著下降，尤其是轻度模糊词样本。
2. 重度风险规则是否仍然被拦住。
3. 回测结果是否仍然保留可追溯性和审核理由。

建议检查的指标：

- `needs_human_review` 数量
- `pending_backtest` 数量
- `suggested_reject` 数量
- 轻度模糊词样本的人工命中率
- 回测后被驳回的比例

## Open Questions

- 哪些词应该算“轻度模糊词”，是否需要按词表配置？
- 是否允许“部分字段缺失但可推导补全”的规则自动进入待回测？
- UI 是否要区分“建议人工”和“强制人工”两种状态？

