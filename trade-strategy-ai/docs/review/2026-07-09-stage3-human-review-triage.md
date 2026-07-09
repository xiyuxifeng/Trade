# Stage 3 Human Review Triage

## Purpose

本文整理当前 `needs_human_review` 的文章规则候选，目标不是重复展示自动审核结果，而是帮助后续人工决定：

- 哪些可以优先补量化后进入回测
- 哪些更适合直接驳回
- 哪些问题最值得回到抽取层或审核层继续收敛

数据口径基于 2026-07-09 本地数据库只读统计，范围为当前 `trade_strategy_ai` 库中的 `RuleCandidate`。

## Current Snapshot

PR #3 修复后，自动审核分布如下：

| Status | Count |
| --- | ---: |
| `pending_backtest` | 40 |
| `needs_human_review` | 435 |
| `suggested_reject` | 13 |

人工审核主队列只看 `needs_human_review`，当前共 `435` 条。

## Operational Conclusion

这 `435` 条里，没有一条属于“人工点批准后即可直接正确回测”。

按后续处理价值拆分：

| Bucket | Count | Meaning |
| --- | ---: | --- |
| `approve_then_can_backtest` | 0 | 不存在这种样本 |
| `needs_human_edit_before_backtest` | 4 | 主要缺核心量化字段，人工补全后可考虑回测 |
| `should_reject_or_major_rewrite` | 431 | 存在强阻塞项，批准本身没有意义 |

结论非常明确：

1. 当前人工主队列不是“审批队列”，而是“补量化/驳回队列”。
2. 真正值得优先人工处理的，是那 `4` 条可修复样本。
3. 剩余 `431` 条如果不改文本或不重抽，人工批准不会把它们变成可稳定回测规则。

## Why They Are Blocked

### A. Recoverable by Human Edit: 4

这 4 条都没有 Kaipan 依赖，也没有重度模糊词或主观风险控制，问题集中在“核心字段缺失”：

| Problem | Count |
| --- | ---: |
| `backtestability = partially_executable` | 4 |
| `core_missing_fields` | 4 |
| `manual_review_required = true` | 2 |

典型缺失：

- `volume_threshold`
- `具体触发条件`
- `具体仓位比例（原文提及 5 份，但未明确总基数）`

这类数据适合人工补录后再回测。

### B. Reject or Major Rewrite: 431

这部分是人工主队列的绝大多数，问题不是“缺一个字段”，而是规则本身不够程序化。

高频阻塞项：

| Problem | Count |
| --- | ---: |
| `heavy_ambiguous_terms` | 427 |
| `backtestability = partially_executable` | 426 |
| `manual_review_required = true` | 233 |
| `non_core_missing_fields` | 143 |
| `core_missing_fields` | 65 |
| `subjective_or_numberless_risk_controls` | 53 |
| `kaipan_dependency` | 31 |

这些样本里，最常见的实际语义是：

- 依赖“情绪修复 / 分歧延续 / 人气最佳 / 板块领涨”这类主观状态
- 风险控制不是数值边界，而是自然语言判断
- 需要盘前/Kaipan 数据才能执行
- 条件本身是复盘判断，不是固定历史回测规则

## Recommended Handling Order

### Priority 1: Manually Repair the 4 Recoverable Items

这 4 条最值得先处理，因为人工投入最小，且修完后最有机会进入回测。

建议动作：

1. 补核心量化字段
2. 明确触发阈值或仓位基数
3. 重新判断是否应改写为 `executable`
4. 只有补完后再批准

### Priority 2: Reject the Obvious Non-Programmable Rules

对出现以下特征的样本，建议默认走“驳回或重写”：

- 重度模糊词直接决定触发逻辑
- 主观风险控制没有数值边界
- Kaipan 依赖是核心判断条件
- 文章表达本质是方法论、节奏感知、复盘感受，不是固定规则

### Priority 3: Use the Sample Set to Improve Extraction

如果后续要继续降低人工量，重点不在人工批准，而在抽取和分类前置优化：

1. 对重复出现的重度模糊词建立更强的拒绝词表
2. 对“方法论文章”提前分流，避免形成正式规则候选
3. 对可修复字段缺失样本尝试做半自动补量化模板

## Representative Recoverable Samples

以下样本更适合“人工补字段后再回测”：

### 1. `020bd41b-976b-4e49-b3b9-ef8fef4286d2`

- Title: `周总结贴（11.17-11.21）`
- URL: `https://www.tgb.cn/a/2n89N8HF6A9`
- Status: `partially_executable`
- Current review reason:
  - `仍有核心缺失字段：具体仓位比例（原文提及5份，但未明确总基数）`
- Notes:
  - 有轻度模糊词 `持续放量`
  - 没有重度模糊词
  - 没有主观 risk control
  - 没有 Kaipan 依赖
- Suggested action:
  - 明确“5 份”的总仓位基数，再决定是否可回测

### 2. `358282ea-c84f-4fb0-bfb7-d0a85a24a6ef`

- Title: `1.2号复盘，指数开年绿的令人发慌！明天怎么看！！附交易思路！`
- URL: `https://www.tgb.cn/a/2evp7ztApP9`
- Status: `partially_executable`
- Current review reason:
  - `仍有核心缺失字段：具体触发条件`
- Notes:
  - 轻度模糊词 `博弈`
  - 主要问题是 entry trigger 未量化
- Suggested action:
  - 把“触发条件”改成可验证阈值后再考虑批准

### 3. `4836617e-adba-4938-81b5-8e4b00193bec`

- Title: `预判周期，定性指数反转！用理解力全程在公开区带队周赚50多个点，每周总结贴来了！`
- URL: `https://www.tgb.cn/a/2bUOBkkM5UI`
- Status: `partially_executable`
- Current review reason:
  - `仍有核心缺失字段：volume_threshold`
  - `抽取层标记需人工复核，但未命中强风险门禁，保留追踪`
- Notes:
  - 轻度模糊词 `放量`
  - 核心问题收敛在一个量化阈值
- Suggested action:
  - 定义放量阈值后重评

### 4. `23ca2407-9891-4acc-97e7-0aeb7031f3c3`

- Title: `11.13号复盘，监管和指数巨幅缩量的双重影响下，明天怎么看？`
- URL: `https://www.tgb.cn/a/2d9Jrv1tsWY`
- Status: `partially_executable`
- Current review reason:
  - `仍有核心缺失字段：volume_threshold`
  - `抽取层标记需人工复核，但未命中强风险门禁，保留追踪`
- Notes:
  - 轻度模糊词 `主动放量表态`
  - 仍然是一个阈值缺失问题
- Suggested action:
  - 明确 volume threshold 后再判断

## Representative Reject / Major Rewrite Samples

以下样本更适合直接驳回，或者作为“需要重写规则表达”的典型案例：

### 1. `e52acdc7-7b1e-40a1-bf64-59e772d2f676`

- Title: `教你什么是短线“确定性”小资金做大的秘密！淘县九年义务教育！`
- URL: `https://www.tgb.cn/a/2gOFSgwjnLF`
- Blockers:
  - 重度模糊词：`低位试错`、`最猛的那波退潮杀跌已经结束`
  - 主观 risk control：`低位试错只能试一次，错了收手等待右侧放量大阳线修复`
- Why not approve:
  - 触发条件和风险控制都依赖主观判断，批准后仍无法稳定回测

### 2. `7d3e040a-9d08-45c6-8df7-271e80dc3995`

- Title: `教你什么是短线“确定性”小资金做大的秘密！淘县九年义务教育！`
- URL: `https://www.tgb.cn/a/2gOFSgwjnLF`
- Blockers:
  - 重度模糊词：`情绪的分歧延续`、`情绪的修复延续`
  - 主观 risk control：`卖在情绪的修复延续`
- Why not approve:
  - 情绪状态不可程序化，risk control 也没有硬边界

### 3. `021d0999-f593-4ee8-bfb9-00efd8030d1c`

- Title: `教你什么是短线“确定性”小资金做大的秘密！淘县九年义务教育！`
- URL: `https://www.tgb.cn/a/2gOFSgwjnLF`
- Blockers:
  - 重度模糊词：`情绪预期修复`、`板块领涨修复`
  - 主观 risk control：`若情绪分歧则避免参与左侧竞价弱转强`
- Why not approve:
  - 核心逻辑依赖主观情绪语义，不是补字段能解决的问题

### 4. `fbc17d48-68c4-46c3-ab7e-f9d782ccf096`

- Title: `新！教你短线如何“选股”下篇~淘县九年义务教育`
- URL: `https://www.tgb.cn/a/2gCEOsKueZu`
- Blockers:
  - 重度模糊词：`最超预期`、`最强`、`最先`、`最主动`、`最正宗`、`最大市值`、`最抗跌`
  - `Kaipan` dependency
- Why not approve:
  - 即使人工批准，也无法脱离盘前增强数据和主观排序语义

### 5. `b03b78f5-6e68-42d9-869b-68dd3b6db513`

- Title: `教你短线实战如何理解与运用龙虎榜~淘县九年义务教育`
- URL: `https://www.tgb.cn/a/2hlXJrLV76n`
- Blockers:
  - 重度模糊词：`高位`、`豪华龙虎榜`、`多路大佬`
  - 主观 risk control：`买点应滞后，等游资打完再考虑进场`
- Why not approve:
  - 核心执行依赖主观盘面理解和行为判断

## What To Do Next

如果后续要高效处理这批数据，建议按下面的顺序推进：

1. 先人工处理上面的 `4` 条 recoverable 样本
2. 把 `431` 条默认视为“驳回或重写池”，不要再走普通批准流程
3. 从高频重度模糊词中抽词表，回灌到抽取或审核前置规则
4. 对常见可修复缺失项建立人工补录模板，例如：
   - `volume_threshold`
   - `具体触发条件`
   - `仓位比例基数`

## Human Action Table

下面这 4 条是当前最值得人工处理的明确待办。处理原则不是“先批准”，而是“先补量化，再重判是否可回测”。

| Priority | Candidate ID | Title | Core Gap | Human Action | Approve Condition |
| --- | --- | --- | --- | --- | --- |
| P1 | `020bd41b-976b-4e49-b3b9-ef8fef4286d2` | 周总结贴（11.17-11.21） | `具体仓位比例（原文提及 5 份，但未明确总基数）` | 明确“5 份”对应的总仓位基数，改写成固定仓位比例或区间 | 仓位字段可直接落成数值边界，且不再依赖口语解释 |
| P1 | `358282ea-c84f-4fb0-bfb7-d0a85a24a6ef` | 1.2号复盘，指数开年绿的令人发慌！明天怎么看！！附交易思路！ | `具体触发条件` | 把 entry trigger 改成可验证阈值，例如价格、成交量、时间窗口或市场条件组合 | 条件字段能独立复现，`condition` 不再是抽象表述 |
| P1 | `4836617e-adba-4938-81b5-8e4b00193bec` | 预判周期，定性指数反转！用理解力全程在公开区带队周赚50多个点，每周总结贴来了！ | `volume_threshold` | 为“放量”补具体阈值，例如相对均量倍数、绝对成交量门槛或连续天数定义 | `volume_threshold` 被补齐，且放量定义可程序化验证 |
| P1 | `23ca2407-9891-4acc-97e7-0aeb7031f3c3` | 11.13号复盘，监管和指数巨幅缩量的双重影响下，明天怎么看？ | `volume_threshold` | 为“主动放量表态”补具体量化标准，并明确比较基准 | 放量判断有固定指标和基准，不再依赖人工解读 |

### Suggested Workflow

每条都按同一个流程处理：

1. 先回看原文证据，确认作者是否给出了可补成数值的线索。
2. 如果只能靠主观理解补字段，直接转入驳回或重写池，不要强行批准。
3. 如果能补成硬边界，先编辑候选规则，再重新判定 `backtestability_status`。
4. 只有在候选变成可程序化规则后，才进入批准和待回测链路。

### Recommended Review Notes Template

人工处理这 4 条时，建议统一记录下面几项，避免后续再次回到模糊状态：

| Field | What to record |
| --- | --- |
| `补录字段` | 具体补了哪个核心字段 |
| `补录依据` | 来自原文哪一句证据 |
| `量化定义` | 最终写成什么阈值、比例或条件 |
| `是否仍有主观项` | `yes / no` |
| `处理结论` | `补后可回测` / `转驳回` / `需重写` |

## Short Checklist

适合逐条勾选执行：

### `020bd41b-976b-4e49-b3b9-ef8fef4286d2`

- [ ] 回看原文，确认“5 份”是否能映射成固定总仓位基数
- [ ] 如果能，补成明确仓位比例或区间
- [ ] 复查是否还存在主观触发条件
- [ ] 若无主观项，转入“补后可回测”
- [ ] 若仍依赖主观理解，转入“驳回/重写”

### `358282ea-c84f-4fb0-bfb7-d0a85a24a6ef`

- [ ] 回看原文，定位缺失的具体触发条件
- [ ] 将触发条件改写为可验证阈值或条件组合
- [ ] 复查 `condition` 是否可以独立复现
- [ ] 若可复现，转入“补后可回测”
- [ ] 若仍是抽象表达，转入“驳回/重写”

### `4836617e-adba-4938-81b5-8e4b00193bec`

- [ ] 回看原文，确认“放量”是否有明确比较基准
- [ ] 补充 `volume_threshold`
- [ ] 写清楚阈值类型：倍数 / 绝对量 / 连续天数
- [ ] 若阈值明确，转入“补后可回测”
- [ ] 若无法量化，转入“驳回/重写”

### `23ca2407-9891-4acc-97e7-0aeb7031f3c3`

- [ ] 回看原文，确认“主动放量表态”的量化定义
- [ ] 补充 `volume_threshold` 和比较基准
- [ ] 复查是否仍依赖情绪或主观盘感
- [ ] 若无主观依赖，转入“补后可回测”
- [ ] 若仍依赖主观判断，转入“驳回/重写”

## Bottom Line

当前人工主队列里：

- 不是“批准积压”，而是“程序化不足积压”
- 真正可救回测的只有 `4` 条
- 其余 `431` 条更适合直接驳回或要求重写为可量化规则

如果后续目标是继续减少人工量，最有效的方向不是扩大批准，而是提前识别并拦截这类非程序化规则。
