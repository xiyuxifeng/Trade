# Plan

## 规划目标

本计划用于说明 `trade-strategy-ai` 从当前最小闭环演进到最终系统目标的实施路径。

唯一执行主清单是 `docs/TaskList.md`。本文件只保留阶段规划与实施原则。

---

## 总体实施策略

不是一次性切到完整新系统，而是按下面顺序渐进迁移：

1. 先统一主线与文档。
2. 先把私有接口和第三方数据沉淀成可回放快照资产。
3. 先补配置、契约、模型、migration。
4. 再补 provider 与市场候选池。
5. 再做 per-trader 策略版本。
6. 再升级盘前主链路。
7. 再补盘后评估、归因和 ranking。
8. 最后统一回测与自主优化。

---

## 分阶段计划

### Stage 0：统一主线与文档收敛

目标：

- 统一唯一主清单。
- 保留最终版 `Project.md` / `Plan.md` / `需求.md`。
- 把历史方案文档和失效文档迁移到 `docs/bak` 或 `docs/Deprecated`。
- 明确 Agent 与 module/service 的边界。

### Stage 1：数据契约与模型打底

目标：

- 扩展配置、契约、模型和 migration。
- 为后续 provider、快照、回测、ranking 提供统一基础。

### Stage 1.5：Agent 边界收敛

目标：

- 保留少数长期稳定 Agent。
- 把知识抽取、行为分析、回测等能力收敛到模块层。
- 冻结旧 Alignment 主线。

### Stage 2：provider 与市场候选池

目标：

- 让系统具备 `hot_topics`、`topic_constituents`、`strong_symbols` 三类正式能力。
- 让 `DataAgent` 从 `last_price` 提供者升级为 capability router。

### Stage 3：策略版本库

目标：

- 把文章、画像、证据、门禁聚合为每日 per-trader `released` 版本。

### Stage 4：盘前主链路升级

目标：

- 让盘前建议真正消费策略版本、候选池、画像和记忆。

### Stage 5：盘后学习闭环

目标：

- 统一评分、ranking、Evidence Pack、postmortem、记忆写回。

### Stage 6：回测与规则验真

目标：

- 使用同一套快照和评分口径完成离线验证。
- 优先做规则验真和筛选，而不是直接做复杂参数优化。

### Stage 7：自主优化

目标：

- 基于 ranking、回测、postmortem 进行 trader 和策略版本的滚动优化。

---

## 关键原则

- 优先快照，不优先实时调用。
- 优先标准化契约，不优先堆功能。
- 优先少数稳定 Agent，不优先继续扩 Agent 数量。
- 优先主链路，不优先外围功能。
- 优先规则验真，不优先过早优化。

---

## 当前最推荐的下一步

直接从以下任务开始：

1. `New-TaskList` 中 `Stage 0` 的数据资产任务。
2. `Stage 1` 的配置、契约、模型、migration。
3. `Stage 1.5` 的 Agent 边界收敛。

在这之前，不建议继续扩展旧的 `watchlist + last_price` 逻辑。
